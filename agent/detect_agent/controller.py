import json
import re
from IPython.terminal.embed import InteractiveShellEmbed

from agent.detect_agent.executor import execute_act

from agent.api_router import get_chat_completion

system = """您是DevOps助手系统的管理员,负责指标数据的异常检测。为了解决每个给定的问题，您应逐步指导执行者编写并执行Python代码，对目标系统的遥测指标文件进行数据分析。通过分析执行结果，您应该能制定出最佳的异常检测方案。

以下是为您提供的一些领域知识：

{background}

{agent}

您将要解决的问题是：

{objective}

请逐步解决问题。在每一步中，您的回复应遵循以下JSON格式：

{format}

让我们开始吧。"""

format = """{
"analysis": (您对上一步执行者代码执行结果的分析，详细说明"已完成什么"和"可以推导出什么"。如果是第一步，则回复"None"。),
"completed": ("True" 如果您认为问题已解决，并且可以在"instruction"字段中得出答案；否则为"False"),
"instruction": (您对执行者的指导，说明下一步通过代码执行需要做什么。不要涉及复杂的多步骤指导。保持指导的原子性，明确提出"做什么"和"怎么做"的清晰要求。如果您认为问题已解决，请自行回复总结。如果您认为问题已解决，请自行回复总结。如果您认为问题已解决，请自行回复总结。)
}
(不要包含"json"和""标签。只包含带有大括号"{}"的JSON对象。如果您想在字符串中插入换行符，请使用"\n"而不是实际的换行字符，以确保JSON兼容性。)"""

summary = """现在，您已决定结束推理过程。您应该为问题提供最终答案。


请回忆问题为：{objective}


请首先回顾您之前的推理过程，以推断出问题的确切答案。如果在分析过程中生成并保存了任何图表，请在最终答案的JSON对象中，使用 `generated_plots` 字段列出所有这些图表的相对于 `plot` 目录的文件名 (例如, `["图表1.png", "图表2.png"])`。然后，在回复的末尾使用以下JSON格式总结您的最终答案,有多少个需要配置异常检测指标就有多少个：

```json
{{
    "1": {{
        "组件层级或者名称": "...",
        "指标名称": "...",
        "指标描述": "...",
        "指标类型": "...",
        "指标异常检测方案": "...",
        "异常检测方案的原因": "..."
    }},
    "2": {{
        "组件层级或者名称": "...",
        "指标名称": "...",
        "指标描述": "...",
        "指标类型": "...",
        "指标异常检测方案": "...",
        "异常检测方案的原因": "..."
    }},
    "generated_plots": ["示例图表1.png", "示例图表2.png"]
}}
```
(请使用"json"和""标签包裹JSON对象。您只需提供问题要求的内容，其他字段在JSON中省略。)
请注意，所有根本原因组件和原因必须从提供的候选中选择。不要在JSON中回复"未知"或"null"或"未找到"。在选择根本原因组件和原因时不要过于保守。基于您当前的观察，果断推断可能的答案。"""

################################################################ en chinese #######################################################################

system_en = """You are the Administrator of a DevOps Assistant system for failure diagnosis. To solve each given issue, you should iteratively instruct an Executor to write and execute Python code for data analysis on telemetry files of target system. By analyzing the execution results, you should approximate the answer step-by-step.

There is some domain knowledge for you:

{background}

{agent}

The issue you are going to solve is:

{objective}

Solve the issue step-by-step. In each step, your response should follow the JSON format below:

{format}

Let's begin."""

format = """{
    "analysis": (Your analysis of the code execution result from Executor in the last step, with detailed reasoning of 'what have been done' and 'what can be derived'. Respond 'None' if it is the first step.),
    "completed": ("True" if you believe the issue is resolved, and an answer can be derived in the 'instruction' field. Otherwise "False"),
    "instruction": (Your instruction for the Executor to perform via code execution in the next step. Do not involve complex multi-step instruction. Keep your instruction atomic, with clear request of 'what to do' and 'how to do'. Respond a summary by yourself if you believe the issue is resolved. Respond a summary by yourself if you believe the issue is resolved. Respond a summary by yourself if you believe the issue is resolved.)
}
(DO NOT contain "```json" and "```" tags. DO contain the JSON object with the brackets "{}" only. Use '\\n' instead of an actual newline character to ensure JSON compatibility when you want to insert a line break within a string.)"""

summary_en = """Now, you have decided to finish your reasoning process. You should now provide the final answer to the issue. The candidates of possible root cause components and reasons are provided to you. The root cause components and reasons must be selected from the provided candidates.

{cand}

Recall the issue is: {objective}

Please first review your previous reasoning process to infer an exact answer of the issue. Then, summarize your final answer of the root causes using the following JSON format at the end of your response:

```json
{{
    "1": {{
        "root cause occurrence datetime": (if asked by the issue, format: '%Y-%m-%d %H:%M:%S', otherwise ommited),
        "root cause component": (if asked by the issue, one selected from the possible root cause component list, otherwise ommited),
        "root cause reason": (if asked by the issue, one selected from the possible root cause reason list, otherwise ommited),
    }}, (mandatory)
    "2": {{
        "root cause occurrence datetime": (if asked by the issue, format: '%Y-%m-%d %H:%M:%S', otherwise ommited),
        "root cause component": (if asked by the issue, one selected from the possible root cause component list, otherwise ommited),
        "root cause reason": (if asked by the issue, one selected from the possible root cause reason list, otherwise ommited),
    }}, (only if the failure number is "unknown" or "more than one" in the issue)
    ... (only if the failure number is "unknown" or "more than one" in the issue)
}}
```
(Please use "```json" and "```" tags to wrap the JSON object. You only need to provide the elements asked by the issue, and ommited the other fields in the JSON.)
Note that all the root cause components and reasons must be selected from the provided candidates. Do not reply 'unknown' or 'null' or 'not found' in the JSON. Do not be too conservative in selecting the root cause components and reasons. Be decisive to infer a possible answer based on your current observation."""


def control_loop(objective:str, plan:str, ap, bp, logger, obs_path:str, max_step = 15, max_turn = 3, langfuse_trace = None) -> str:
   
    agent_promt = ap.rules.format(obs_path=obs_path)
    prompt = [
            {'role': 'system', 'content': system.format(objective=objective,
                                                        format=format,
                                                        agent=agent_promt, 
                                                        background=bp.schema)},
            {'role': 'user', 'content': "Let's begin."}
        ]

    history = []
    trajectory = []
    observation = "Let's begin."
    status = False
    kernel = InteractiveShellEmbed()
    init_code = "import pandas as pd\n"+ \
            "pd.set_option('display.width', 427)\n"+ \
            "pd.set_option('display.max_columns', 10)\n"
    kernel.run_cell(init_code)

    # Define obs_path and plot_output_path in the kernel and create the plot directory
    plot_setup_code = f"import os\nobs_path = r'{obs_path}'\nplot_output_path = os.path.join(obs_path, 'plot')\nos.makedirs(plot_output_path, exist_ok=True)"
    kernel.run_cell(plot_setup_code)
    logger.info(f"Plots will be saved to: {kernel.user_ns['plot_output_path']}")


    for step in range(max_step):
        
        note = [{'role': 'user', 'content': f"Continue your reasoning process for the target issue:\n\n{objective}\n\nFollow the rules during issue solving:\n\n{ap.rules}.\n\nResponse format:\n\n{format}"}]
        attempt_actor = []
        try:
            # 创建一个新的span来跟踪每个步骤
            if langfuse_trace:
                step_span = langfuse_trace.span(
                    name=f"Step_{step+1}",
                    input=prompt[-1]['content']
                )
                llm_generation = step_span.generation(
                    name=f"Controller",
                    model=get_chat_completion.__globals__.get('configs', {}).get('MODEL', 'unknown-model'),
                    input=prompt + note
                )
            
            response_raw = get_chat_completion(
                messages=prompt + note,
            )
            
            if "```json" in response_raw:
                response_raw = re.search(r"```json\n(.*)\n```", response_raw, re.S).group(1).strip()
            logger.debug(f"Raw Response:\n{response_raw}")
            
            # 记录大模型响应
            if langfuse_trace:
                llm_generation.end(output=response_raw)
            
            if '"analysis":' not in response_raw or '"instruction":' not in response_raw or '"completed":' not in response_raw:
                logger.warning("Invalid response format. Please provide a valid JSON response.")
                prompt.append({'role': 'assistant', 'content': response_raw})
                prompt.append({'role': 'user', 'content': "Please provide your analysis in requested JSON format."})
                
                if langfuse_trace:
                    step_span.end(
                        output="Invalid response format",
                        status="error"
                    )
                continue
                
            response = json.loads(response_raw)
            analysis = response['analysis']
            instruction = response['instruction']
            completed = response['completed']
            logger.info('-'*80 + '\n' + f"### Step[{step+1}]\nAnalysis: {analysis}\nInstruction: {instruction}" + '\n' + '-'*80)

            if completed == "True":
                kernel.reset()
                prompt.append({'role': 'assistant', 'content': response_raw})
                prompt.append({'role': 'user', 'content': summary.format(objective=objective,
                                                                                cand=bp.cand)})
                
                # 记录最终答案请求
                if langfuse_trace:
                    final_answer_span = langfuse_trace.span(
                        name="Final_Answer",
                        input=summary.format(objective=objective, cand=bp.cand)
                    )
                    llm_generation = final_answer_span.generation(
                        name="Final_Answer_Summary",
                        model=get_chat_completion.__globals__.get('configs', {}).get('MODEL', 'unknown-model'),
                        input=prompt
                    )

                
                answer = get_chat_completion(
                    messages=prompt,
                )
                
                # 记录最终答案
                if langfuse_trace:
                    llm_generation.end(output=answer)
                    final_answer_span.end(output=answer, status="success")
                
                logger.debug(f"Raw Final Answer:\n{answer}")
                prompt.append({'role': 'assistant', 'content': answer})
                if "```json" in answer:
                    answer = re.search(r"```json\n(.*)\n```", answer, re.S).group(1).strip()
                return answer, trajectory, prompt

            # 执行代码
            if langfuse_trace:
                executor_span = step_span.span(
                    name=f"Executor",
                    input=instruction
                )
            
            code, result, status, new_history = execute_act(
                instruction, 
                bp.schema, 
                history, 
                attempt_actor, 
                kernel, 
                logger, 
                obs_path,
                langfuse_trace=executor_span, 
                step_id=f"Step_{step+1}"
            )
            
            # 记录执行结果
            if langfuse_trace:
                executor_span.end(
                    output=result,
                    status="success" if status else "error",
                    metadata={
                        "code": code
                    }
                )
            
            if not status:
                logger.warn(f'Self-Correction failed.')
                observation = "The Executor failed to execute the instruction. Please provide a new instruction."
            observation = f"{result}"
            history = new_history
            trajectory.append({'code': f"# In[{step+1}]:\n\n{code}", 'result': f"Out[{step+1}]:\n```\n{result}```"})
            logger.info('-'*80 + '\n' + f"Step[{step+1}]\n### Observation:\n{result}" + '\n' + '-'*80)
            prompt.append({'role': 'assistant', 'content': response_raw})
            prompt.append({'role': 'user', 'content': observation})
            
            # 结束当前步骤的span
            response["code_execution_result"] = result
            if langfuse_trace:
                step_span.end(
                    output=response,
                    status="success" if status else "error"
                )

        except Exception as e:
            logger.error(e)
            prompt.append({'role': 'assistant', 'content': response_raw})
            prompt.append({'role': 'user', 'content': f"{str(e)}\nPlease provide your analysis in requested JSON format."})
            
            # 记录异常
            if langfuse_trace and 'step_span' in locals():
                step_span.end(
                    output=str(e),
                    status="error"
                )
            
            if 'context_length_exceeded' in str(e):
                logger.warning("Token length exceeds the limit.")
                kernel.reset()
                return "Token length exceeds. No root cause found.", trajectory, prompt

    logger.warning("Max steps reached. Please check the history.")
    kernel.reset()
    final_prompt = {'role': 'user', 'content': summary.format(objective=objective,
                                                                    cand=bp.cand).replace('Now, you have decided to finish your reasoning process. ', 'Now, the maximum steps of your reasoning have been reached. ')}
    if prompt[-1]['role'] == 'user':
        prompt[-1]['content'] = final_prompt['content']
    else:
        prompt.append({'role': 'user', 'content': final_prompt['content']})
    
    # 记录最大步数达到后的最终请求
    if langfuse_trace:
        max_step_span = langfuse_trace.span(
            name="Max_Steps_Reached",
            input=final_prompt['content']
        )
    
    answer = get_chat_completion(
        messages=prompt,
    )
    
    # 记录最终结果
    if langfuse_trace and 'max_step_span' in locals():
        max_step_span.generation(
            name="Max_Steps_Answer",
            model=get_chat_completion.__globals__.get('configs', {}).get('MODEL', 'unknown-model'),
            input=prompt,
            output=answer
        )
        max_step_span.end(output=answer)
    
    logger.debug(f"Raw Final Answer:\n{answer}")
    prompt.append({'role': 'assistant', 'content': answer})
    if "```json" in answer:
        answer = re.search(r"```json\n(.*)\n```", answer, re.S).group(1).strip()
    return answer, trajectory, prompt
