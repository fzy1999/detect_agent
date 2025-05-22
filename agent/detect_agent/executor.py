import re
import time
from datetime import datetime
from agent.api_router import get_chat_completion
import tiktoken
import traceback

system = """您是一个DevOps助手，负责编写Python代码来回答DevOps相关问题。对于每个问题，您需要编写Python代码，通过获取和处理目标系统的遥测数据来解决问题。您生成的Python代码将自动提交到IPython Kernel。IPython Kernel的执行结果输出将作为问题的答案。
10. 请勿在回复中使用英文。 使用中文。

## 图表生成指南：

- 在分析过程中，如果认为生成图表有助于理解数据趋势、识别异常点或评估检测规则的效果，您可以生成图表并保存到指定路径。
- 常用的图表类型可能包括：原始指标的时间序列曲线图、标记了检测到的异常点的曲线图、显示应用某种检测规则（如阈值、EWMA）后效果的对比图等。
- 使用适当的Python库（如 Matplotlib 或 Seaborn）生成图表。
- 生成的图表应保存为图片文件（例如 PNG格式） 图片的描述必须为英文。
- 图表文件必须保存到当前执行输出路径下的 `plot` 子目录中。完整的保存路径结构为 `{obs_path}/plot/文件名.png`。
- 在指示生成图表时，请尽量建议一个有意义的文件名，例如 `raw_metric_trend.png` 或 `cpu_util_with_anomalies_detected.png`。
- 完成图表生成后，应在其观察结果中报告已成功保存的图表文件名。


{rule}

以下是为您提供的一些领域知识：

{background}

您的回复应遵循以下Python代码块格式：

{format}"""

format = """```python
（您的代码在此处）
```"""

summary = """代码执行成功。执行结果如下所示：


{result}

请根据执行结果，用简洁的中文总结一个直接的答案。"""

conclusion = """{answer}

IPython Kernel的原始代码执行输出也提供如下供参考：

{result}"""

rule = """## Python代码编写规则：

1. 尽可能重用变量以提高执行效率，因为IPython Kernel是有状态的，即在前面步骤中定义的变量可以在后续步骤中使用。
2. 使用变量名而不是`print()`来显示执行结果，因为您的Python环境是IPython Kernel，而不是Python.exe。如果您想显示多个变量，请用逗号分隔，例如`var1, var2`。
3. 使用pandas DataFrame来处理和显示表格数据，以提高效率和简洁性。避免将DataFrame转换为list或dict类型进行显示。
4. 如果遇到错误或意外结果，请参考给定的IPython Kernel错误消息重写代码。
5. 不要模拟任何虚拟情况或假设未知内容。解决真实问题。
6. 不要将任何数据存储为磁盘上的文件。只能将数据作为变量缓存到内存中。
7. 不要通过Python可视化数据或绘制图片或图表。您只能提供基于文本的结果。代码中绝不包含`matplotlib`或`seaborn`库。
8. 除非指令明确要求'使用简洁的中文'，否则不要生成除Python代码块之外的任何内容。如果您发现输入指令是总结任务（通常发生在最后一步），您应该在代码中将结论综合总结为字符串并直接显示。
9. 不要在给定时间段内过滤数据后再计算阈值。始终在过滤给定时间段数据之前，使用指标文件中特定组件的整个KPI系列计算全局阈值。
10. 所有问题均使用**UTC+8**时间。然而，本地机器的默认时区未知。请使用`pytz.timezone('Asia/Shanghai')`明确将时区设置为UTC+8。
"""

#############################################################################

system_en = """You are a DevOps assistant for writing Python code to answer DevOps questions. For each question, you need to write Python code to solve it by retrieving and processing telemetry data of the target system. Your generated Python code will be automatically submitted to a IPython Kernel. The execution result output in IPython Kernel will be used as the answer to the question.
10. **DO NOT use English in your response.** Use Chinese.
{rule}

There is some domain knowledge for you:

{background}

Your response should follow the Python block format below:

{format}"""

format_en = """```python
(YOUR CODE HERE)
```"""

summary_en = """The code execution is successful. The execution result is shown below: 

{result}

Please summarize a straightforward answer to the question based on the execution results. Use plain English."""

conclusion_en = """{answer}

The original code execution output of IPython Kernel is also provided below for reference:

{result}"""

rule_en = """## RULES OF PYTHON CODE WRITING:

1. Reuse variables as much as possible for execution efficiency since the IPython Kernel is stateful, i.e., variables define in previous steps can be used in subsequent steps. 
2. Use variable name rather than `print()` to display the execution results since your Python environment is IPython Kernel rather than Python.exe. If you want to display multiple variables, use commas to separate them, e.g. `var1, var2`.
3. Use pandas Dataframe to process and display tabular data for efficiency and briefness. Avoid transforming Dataframe to list or dict type for display.
4. If you encounter an error or unexpected result, rewrite the code by referring to the given IPython Kernel error message.
5. Do not simulate any virtual situation or assume anything unknown. Solve the real problem.
6. Do not store any data as files in the disk. Only cache the data as variables in the memory.
7. Do not visualize the data or draw pictures or graphs via Python. You can only provide text-based results. Never include the `matplotlib` or `seaborn` library in the code.
8. Do not generate anything else except the Python code block except the instruction tell you to 'Use plain English'. If you find the input instruction is a summarization task (which is typically happening in the last step), you should comprehensively summarize the conclusion as a string in your code and display it directly.
9. Do not calculate threshold AFTER filtering data within the given time duration. Always calculate global thresholds using the entire KPI series of a specific component within a metric file BEFORE filtering data within the given time duration.
10. All issues use **UTC+8** time. However, the local machine's default timezone is unknown. Please use `pytz.timezone('Asia/Shanghai')` to explicityly set the timezone to UTC+8.
"""

def execute_act(instruction:str, background:str, history, attempt, kernel, logger, obs_path:str, langfuse_trace=None, step_id=None) -> str:

    logger.debug("Start execution")
    t1 = datetime.now()
    if history == []:
        history = [
                {'role': 'system', 'content': system.format(obs_path=obs_path, rule=rule, background=background, format=format)},
            ]
    code_pattern = re.compile(r"```python\n(.*?)\n```", re.DOTALL)
    code = ""
    result = ""
    retry_flag = False
    status = False
    history.extend([{'role': 'user', 'content': instruction}])
    prompt = history.copy()
    note = [{'role': 'user', 'content': f"Continue your code writing process following the rules:\n\n{rule}\n\nResponse format:\n\n{format}"}]
    tokenizer = tiktoken.encoding_for_model("gpt-4")
    
    for i in range(2):
        try:
            # 创建langfuse跟踪
            if langfuse_trace:
                Code_generation_llm_generation = langfuse_trace.generation(
                    name=f"Code_Generation" if not retry_flag else f"Code_Generation_Retry",
                    input=prompt + note if retry_flag else prompt
                )
                
            if not retry_flag:
                response = get_chat_completion(
                    messages=prompt + note,
                )
            else:
                response = get_chat_completion(
                    messages=prompt
                )
                retry_flag = False
                
            # 记录生成的代码
            if langfuse_trace:
                Code_generation_llm_generation.end(output=response)
                
            if re.search(code_pattern, response):
                code = re.search(code_pattern, response).group(1).strip()
            else:
                code = response.strip()
            logger.debug(f"Raw Code:\n{code}")
            
            # if "import matplotlib" in code or "import seaborn" in code:
            #     logger.warning("The generated visualization code detected.")
            #     prompt.append({'role': 'assistant', 'content': code})
            #     prompt.append({'role': 'user', 'content': "You are not permitted to generate visualizations. If the instruction requires visualization, please provide the text-based results."})
                
            #     if langfuse_trace:
            #         Code_generation_llm_generation.end(
            #             output="Visualization code detected and rejected",
            #             status="error"
            #         )
            #     continue
                
            # 创建执行跟踪
            if langfuse_trace:
                execution_span = langfuse_trace.span(
                    name=f"Code_Execution",
                    input=code
                )
                
            exec = kernel.run_cell(code)
            status = exec.success
            
            if status:
                result = str(exec.result).strip()
                tokens_len = len(tokenizer.encode(result))
                
                if tokens_len > 16384:
                    logger.warning(f"Token length exceeds the limit: {tokens_len}")
                    
                    if langfuse_trace:
                        execution_span.end(
                            output="Token length exceeded",
                            status="error"
                        )

                    continue
                    
                t2 = datetime.now()
                row_pattern = r"\[(\d+)\s+rows\s+x\s+\d+\s+columns\]"
                match = re.search(row_pattern, result)
                if match:
                    rows = int(match.group(1))
                    if rows > 10:
                        result += f"\n\n**Note**: The printed pandas DataFrame is truncated due to its size. Only **10 rows** are displayed, which may introduce observation bias due to the incomplete table. If you want to comprehensively understand the details without bias, please ask Executor using `df.head(X)` to display more rows."
                logger.debug(f"Execution Result:\n{result}")
                logger.debug(f"Execution finished. Time cost: {t2-t1}")
                
                # 记录执行结果
                if langfuse_trace:
                    execution_span.end(
                        output=result,
                        status="success",
                        metadata={
                            "execution_time": (t2-t1).total_seconds()
                        }
                    )
                
                history.extend([
                    {'role': 'assistant', 'content': code},
                    {'role': 'user', 'content': summary.format(result=result)},
                ])
                
                # 创建总结跟踪
                if langfuse_trace:
                    summary_llm_generation = langfuse_trace.generation(
                        name=f"Executor_Summary",
                        input=history
                    )
                
                answer = get_chat_completion(
                    messages=history,
                )
                
                # 记录总结结果
                if langfuse_trace:
                    summary_llm_generation.end(output=answer)
                
                logger.debug(f"Brief Answer:\n{answer}")
                history.extend([
                    {'role': 'assistant', 'content': answer},
                ])
                result = conclusion.format(answer=answer, result=result)
                
                return code, result, status, history
            else:
                result = ''.join(traceback.format_exception(type(exec.error_in_exec), exec.error_in_exec, exec.error_in_exec.__traceback__))
                t2 = datetime.now()
                logger.warning(f"Execution failed. Error message: {result}")
                logger.debug(f"Execution finished. Time cost: {t2-t1}")
                
                # 记录执行失败
                if langfuse_trace:
                    execution_span.end(
                        output=result,
                        status="error",
                        metadata={
                            "execution_time": (t2-t1).total_seconds()
                        }
                    )
                
                prompt.append({'role': 'assistant', 'content': code})
                prompt.append({'role': 'user', 'content': f"Execution failed:\n{result}\nPlease revise your code and retry."})
                retry_flag = True
                

            
        except Exception as e:
            logger.error(e)
            
            # 记录异常
            if langfuse_trace:
                if 'execution_span' in locals():
                    execution_span.end(
                        output=str(e),
                        status="error"
                    )

            
            time.sleep(1)
    
    t2 = datetime.now()
    logger.error(f"Max try reached. Please check the history. Time cost: {t2-t1}")
    err = "The Executor failed to complete the instruction, please re-write a new instruction for Executor."
    history.extend([{'role': 'assistant', 'content': err}])
    return err, err, True, history