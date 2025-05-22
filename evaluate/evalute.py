# Imports
import os
import math
import json
from langfuse import Langfuse
from datetime import datetime, timedelta
import openai
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams, LLMTestCase
import time
# --- Configuration ---
# Langfuse Configuration (from instruction.md)
LANGFUSE_SECRET_KEY = "sk-lf-68a99e2d-b6d2-4386-bd8c-9b32f257ae1b"
LANGFUSE_PUBLIC_KEY = "pk-lf-9a5d5405-9865-4f4a-97b6-38fc010d4753"
LANGFUSE_HOST = "http://9.134.214.7:8080"

# LLM Configuration (from instruction.md)
# Available Models
AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gpt-4.1", 
    "gemini-2.5-pro",
    "claude-3.7-sonnet-20250219",
    "gemini-2.0-flash"
]

MODEL_NAME = AVAILABLE_MODELS[2]
OPENAI_API_KEY = "D6apCSNBgPVQF3r2kBhdsda1@4033"
OPENAI_API_BASE = "http://v2.open.venus.oa.com/llmproxy"

# Evaluation Parameters
BATCH_SIZE = 10
TOTAL_TRACES = 50


# Set OpenAI environment variables for libraries like deepeval
# This helps deepeval pick up the correct custom endpoint if it relies on OpenAI env vars
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_API_BASE"] = OPENAI_API_BASE
# If deepeval's GEval needs a specific model name via an environment variable,
# you might need to set it here as well, e.g., os.environ["DEEPEVAL_MODEL_NAME"] = MODEL_NAME
# However, GEval can often take a 'model' parameter directly.
# The example in instruction.md does not pass a model to GEval.

# --- Initialize Clients ---
# Langfuse Client
langfuse_client = Langfuse(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_HOST
)

# OpenAI Client (for tone evaluation)
openai_client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)

# --- Evaluation Prompt Templates ---
template_tone_eval = """
You're an expert in human emotional intelligence. You can identify with ease the
 tone in human-written text. Your task is to identify the tones present in a
 piece of <text/> with precission. Your output is a comma separated list of three
 tones. PRINT THE LIST ALONE, NOTHING ELSE.
 
<possible_tones>
neutral, confident, joyful, optimistic, friendly, urgent, analytical, respectful
</possible_tones>
 
<example_1>
Input: Citizen science plays a crucial role in research by involving everyday
people in scientific projects. This collaboration allows researchers to collect
vast amounts of data that would be impossible to gather on their own. Citizen
scientists contribute valuable observations and insights that can lead to new
discoveries and advancements in various fields. By participating in citizen
science projects, individuals can actively contribute to scientific research
and make a meaningful impact on our understanding of the world around us.
 
Output: respectful,optimistic,confident
</example_1>
 
<example_2>
Input: Bionics is a field that combines biology and engineering to create
devices that can enhance human abilities. By merging humans and machines,
bionics aims to improve quality of life for individuals with disabilities
or enhance performance for others. These technologies often mimic natural
processes in the body to create seamless integration. Overall, bionics holds
great potential for revolutionizing healthcare and technology in the future.
 
Output: optimistic,confident,analytical
</example_2>
 
<example_3>
Input: Social media can have both positive and negative impacts on mental
health. On the positive side, it can help people connect, share experiences,
and find support. However, excessive use of social media can also lead to
feelings of inadequacy, loneliness, and anxiety. It's important to find a
balance and be mindful of how social media affects your mental well-being.
Remember, it's okay to take breaks and prioritize your mental health.
 
Output: friendly,neutral,respectful
</example_3>
 
<text>
{text}
</text>
"""

# --- Evaluation Functions ---
def get_tone_score(trace_output: str):
    """
    Evaluates the tone of the trace output using the configured LLM.
    """
    try:
        completion = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": template_tone_eval.format(text=trace_output),
                }
            ],
            model=MODEL_NAME,
            temperature=0
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in get_tone_score for output '{trace_output[:50]}...': {e}")
        return "error_evaluating_tone"

def get_joyfulness_score(trace_input_obj: any, trace_output_str: str):
    """
    Evaluates the joyfulness of the trace output using Deepeval.
    """
    actual_input_for_eval = ""
    if isinstance(trace_input_obj, dict) and "args" in trace_input_obj:
        args_content = trace_input_obj["args"]
        if isinstance(args_content, list):
            actual_input_for_eval = " ".join(str(x) for x in args_content)
        else:
            actual_input_for_eval = str(args_content)
    elif isinstance(trace_input_obj, str):
        actual_input_for_eval = trace_input_obj
    else: # Fallback for other types
        actual_input_for_eval = str(trace_input_obj)

    try:
        # Note: GEval might require specific model configuration if the default
        # (often OpenAI via env vars) isn't suitable for the custom LLM endpoint.
        # The 'model' parameter can be passed to GEval, e.g., model=MODEL_NAME.
        # For now, following instruction.md which doesn't specify it here.
        joyfulness_metric = GEval(
            name="Joyfulness", # instruction.md used "Correctness", changed for clarity
            criteria="Determine whether the output is engaging and fun.",
            # Added INPUT as it's relevant for "engaging and fun"
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            # model=MODEL_NAME # Potentially add this if deepeval doesn't pick up the custom model
        )
        test_case = LLMTestCase(
            input=actual_input_for_eval,
            actual_output=trace_output_str
        )
        joyfulness_metric.measure(test_case)
        return {"score": joyfulness_metric.score, "reason": joyfulness_metric.reason}
    except Exception as e:
        print(f"Error in get_joyfulness_score for output '{trace_output_str[:50]}...': {e}")
        # Provide a default score and include the error in the reason
        return {"score": 0.0, "reason": f"Error evaluating joyfulness: {str(e)}"}

# --- Main Evaluation Script ---
def main():
    print("Starting Langfuse evaluation script...")

    now = datetime.now()
    five_am_today = datetime(now.year, now.month, now.day, 5, 0, 0)
    five_am_yesterday = five_am_today - timedelta(days=1)

    total_pages = math.ceil(TOTAL_TRACES / BATCH_SIZE)
    print(f"Target total traces: {TOTAL_TRACES}, Batch size: {BATCH_SIZE}, Calculated pages: {total_pages}")

    processed_traces_count = 0
    # Corrected loop to ensure it covers all pages if total_pages is an integer
    for page_number in range(1, int(total_pages) + 1):
        if processed_traces_count >= TOTAL_TRACES:
            print("Target number of traces processed. Exiting loop.")
            break

        print(f"\nFetching batch {page_number}/{int(total_pages)}...")
        
        # Calculate how many traces to fetch in this batch to not exceed TOTAL_TRACES
        remaining_traces_to_fetch = TOTAL_TRACES - processed_traces_count
        current_batch_limit = min(BATCH_SIZE, remaining_traces_to_fetch)

        if current_batch_limit <= 0:
            print("No more traces needed to reach total. Exiting loop.")
            break
            
        try:
            traces_batch_response = langfuse_client.fetch_traces(
                page=page_number,
                limit=current_batch_limit,
                # As per instruction.md, using specific time window
                from_timestamp=five_am_yesterday,
                to_timestamp=five_am_today # Fetches traces *up to* 5 AM today
            )
            traces_batch = traces_batch_response.data

            if not traces_batch:
                print(f"No traces found in batch {page_number} for the given filters and time window. May stop if this continues.")
                # If no traces are found on an intermediate page, it might mean no more traces match the criteria.
                # Depending on exact API behavior, we might want to break here or after a few empty batches.
                # For now, let it continue to try next pages if total_pages suggests more.
                if page_number < int(total_pages): # only break if not the last expected page potentially being empty
                    print("Stopping as no traces were returned on an intermediate page.")
                    break
                else:
                    print("Reached last expected page, and it's empty or all traces processed.")
                    break


            print(f"Fetched {len(traces_batch)} traces for batch {page_number}.")

        except Exception as e:
            print(f"Error fetching traces for batch {page_number}: {e}")
            continue # Skip to next page

        for trace in traces_batch:
            if processed_traces_count >= TOTAL_TRACES:
                break 

            trace_id_str = trace.id if trace.id else "N/A"
            trace_name_str = trace.name if trace.name else "N/A"
            print(f"\nProcessing Trace ID: {trace_id_str}, Name: {trace_name_str}")

            if trace.output is None:
                print(f"  Warning: Trace {trace_id_str} has no output. Skipping evaluation.")
                processed_traces_count +=1 # Count as processed to avoid infinite loop if all remaining traces have no output
                continue

            # 1. Tone Score
            print("  Evaluating tone...")
            tone_value = get_tone_score(trace.output)
            try:
                langfuse_client.score(
                    trace_id=trace.id,
                    name="tone", # As per instruction.md
                    value=tone_value, # Categorical score (string)
                    comment="Automated tone evaluation using LLM."
                )
                print(f"    Tone score '{tone_value}' uploaded for trace {trace.id}.")
            except Exception as e:
                print(f"    Error uploading tone score for trace {trace.id}: {e}")
            
            # 2. Joyfulness Score
            print("  Evaluating joyfulness...")
            # Pass trace.input (which can be a dict) and trace.output
            joyfulness_result = get_joyfulness_score(trace.input, trace.output)
            try:
                langfuse_client.score(
                    trace_id=trace.id,
                    name="joyfulness", # As per instruction.md
                    value=joyfulness_result["score"], # Numeric score
                    comment=str(joyfulness_result["reason"]) # Ensure comment is a string
                )
                print(f"    Joyfulness score {joyfulness_result['score']} (Reason: {joyfulness_result['reason']}) uploaded for trace {trace.id}.")
            except Exception as e:
                print(f"    Error uploading joyfulness score for trace {trace.id}: {e}")
            
            processed_traces_count += 1
        
        print(f"\nBatch {page_number} processed. Total traces processed so far: {processed_traces_count}.")

    print(f"\nEvaluation script finished. Processed {processed_traces_count} traces in total.")

case_list = [
    {
        "trace_id": "...",
        "scoring_records": "...",
        "evaluations": "..."
    }
]

def build_score_standard(case_list: list) -> dict:
    """构建评分标准。

    构建评分标准用于评估模型输出质量。

    Args:
        case_list: CBS案例集合，包含示例案例及其评分。

    Returns:
        dict: 包含评分标准的提示词。
    """

    agent_conversation_records = []

    for case in case_list:
        case_content = {
            "agent_conversation_records": "",
            "scoring_records": case["score"],
            "evaluations": case["evaluations"]
        }
        trace = langfuse_client.fetch_trace(case["trace_id"])
        # Get the last GENERATION type observation
        generation_observations = [obs for obs in trace.data.observations if obs.type == "GENERATION"]
        records = generation_observations[0].input
        records.append({'role': 'assistant', 'content': generation_observations[0].output})
        case_content["agent_conversation_records"] = records

        agent_conversation_records.append(case_content)
    # 将case_content转换为字符串
    case_content_str = json.dumps(agent_conversation_records, ensure_ascii=False)
        

    System_prompt = """
    你是一位构建评分标准的专家，你的任务是根据给定的多组agent对话记录、评分记录和文本评价，生成对于此类agent对话的评分标准。
    以下是需要你分析的内容：
    <agent_conversation_records>
    {case_content_str}
    </agent_conversation_records>

    因爲你不知道正確的故障原因是啥 所以主要聚焦其他評分標準
    上面是非常粗略的评分标准，请根据实际情况进行调整，确保评分标准能够准确反映agent对话的质量。
    在生成评分标准时，请按照以下步骤进行：
    1. 仔细分析所有agent对话记录、评分记录和文本评价，找出与不同分数对应的对话特征和评价要点。
    2. 基于所有样本数据，总结出在什么情况下应该给予1 - 5分的评分。
    3. 确保每个评分标准清晰明确、具有可操作性。
    4. 注意评分标准需要能够适用于所有对话记录，保持一致性。
    5. systempromt  前置步骤引导越少 且能够准确定位，评分越高
    请在<scoring_criteria>标签内写下生成的评分标准,以及关注要点，格式如下： 
    5分: 请输入什么情况下是5分回答
    4分: 请输入什么情况下是4分回答
    3分: 请输入什么情况下是3分回答
    2分: 请输入什么情况下是2分回答
    1分: 请输入什么情况下是1分回答

    如对话记录5和6 请直接概述案例特征 不要想这样 
    """
    completion = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": System_prompt.format(case_content_str=case_content_str),
                },
                {
                    "role": "user",
                    "content": "let's do it"
                }
            ],
            model=MODEL_NAME,
            temperature=0
        )

    return completion.choices[0].message.content.strip()

def evalute_result(trace_id: str, scoring_criteria: str,right_answer:str):
    trace = langfuse_client.fetch_trace(trace_id)
    # Get the last GENERATION type observation
    generation_observations = [obs for obs in trace.data.observations if obs.type == "GENERATION"]
    records = generation_observations[0].input
    records.append({'role': 'assistant', 'content': generation_observations[0].output})

    System_prompt = """
    你是一个多轮对话agent质量评估专家 请根据评估策略对于对话记录进行评估，输出得分 以及原因 
    原因最好包含以下几点
    1. 好在哪里
    2. 坏在哪里

    该案例的正确答案是
    {right_answer}

    评估策略如下
    {scoring_criteria}

    输出 严格按照json格式输出 不要有这个
    
    {{
        "score": 0,
        "reason": "..."
    }}

    你需要评估的对话案例如下
    {records}
    """
    # print(System_prompt.format(records=records, scoring_criteria=scoring_criteria))
    completion = openai_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": System_prompt.format(records=records, scoring_criteria=scoring_criteria,right_answer=right_answer),
            },
            {
                "role": "user",
                "content": "let's do it"
            }
        ],
        model=MODEL_NAME,
        temperature=0
    )


    # 去掉```json
    result = completion.choices[0].message.content.strip().replace("```json", "").replace("```", "")
    return result


def evalute_result2(trace_id: str, scoring_criteria: str):
    trace = langfuse_client.fetch_trace(trace_id)
    # Get the last GENERATION type observation
    generation_observations = [obs for obs in trace.data.observations if obs.type == "GENERATION"]
    records = generation_observations[0].input
    records.append({'role': 'assistant', 'content': generation_observations[0].output})

    System_prompt = """
    你是一个多轮对话agent质量评估专家 请根据评估策略对于对话记录进行评估，输出得分 以及原因 
    原因最好包含以下几点
    1. 好在哪里
    2. 坏在哪里

  

    评估策略如下
    {scoring_criteria}

    输出 严格按照json格式输出 不要有这个
    
    {{
        "score": 0,
        "reason": "..."
    }}

    你需要评估的对话案例如下
    {records}
    """
    # print(System_prompt.format(records=records, scoring_criteria=scoring_criteria))
    completion = openai_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": System_prompt.format(records=records, scoring_criteria=scoring_criteria),
            },
            {
                "role": "user",
                "content": "let's do it"
            }
        ],
        model=MODEL_NAME,
        temperature=0
    )


    # 去掉```json
    result = completion.choices[0].message.content.strip().replace("```json", "").replace("```", "")
    return result

def main2():
    # CBS 案例集合  分为good case 和 bad case
    cbs_case = [
        {
            "trace_id": "7c9f99bf-1eb9-40e5-a772-03d4601fa500",
            "model": "claude",
            "knowledge_base": "知识库+步骤",
            "focus": "对数字判断精准，比如1.18ms虽然比0.01飙升，但是没有超过20ms的阈值",
            "score": 1
        },
        {
            "trace_id": "f5c89af8-d793-48c4-ae86-b6eb40ec3627",
            "model": "gemini",
            "knowledge_base": "仅知识库",
            "focus": "仅基于知识库，做出专业分析和结论",
            "score": 0
        },
        {
            "trace_id": "598ac675-da83-4a6d-b41c-00d7c8385b85",
            "model": "cloud",
            "knowledge_base": "仅知识库",
            "focus": "查到局部指标异常就下结论，只看到表面现象。需要强化一下才能进行全面排查",
            "score": 0
        },
        {
            "trace_id": "78f8b228-d084-4787-811b-e371c174b2c9",
            "model": "claude",
            "knowledge_base": "仅知识库",
            "focus": "仅有知识库，定位出根因",
            "score": 0
        },
        {
            "trace_id": "7c039879-8e8c-4199-bef5-fde5c5c83e4a",
            "model": "deepseek",
            "knowledge_base": "知识库+步骤",
            "focus": "对数字判断有问题，在0.01飙升到1.18ms的情况下，会误判为超过20ms阈值",
            "score": 0
        },
        {
            "trace_id": "08adb766-8e1b-4c0a-9105-717a3991de33",
            "model": "deepseek",
            "knowledge_base": "知识库+步骤",
            "focus": "经过步骤拆分+任务拆分为小任务，deepseek解决了数字判断的问题",
            "score": 1
        },
        {
            "trace_id": "1367f87d-2af0-4fbd-897c-00b5edd3fca2",
            "model": "unknown",
            "knowledge_base": "知识库+步骤",
            "focus": "篡改了标准20ms阈值被改成0.2ms了",
            "score": 0
        }
    ]

    cbs_case = []







if __name__ == "__main__":
    # main()


    # 测试评分标准构建函数
    def test_build_score_standard():
        # 准备测试数据
        test_cases = [
            {
                "trace_id": "f5c89af8-d793-48c4-ae86-b6eb40ec3627",
                "evaluations": "仅知识库。仅基于知识库，做出专业分析和结论",
                "score": 5
            },
            {
                "trace_id": "598ac675-da83-4a6d-b41c-00d7c8385b85",
                "evaluations": "仅知识库。查到局部指标异常就下结论，只看到表面现象。需要强化一下才能进行全面排查",
                "score": 2
            },
            {
                "trace_id": "78f8b228-d084-4787-811b-e371c174b2c9",
                "evaluations": "仅知识库。仅有知识库，定位出根因",
                "score": 5
            },
            {
                "trace_id": "7c9f99bf-1eb9-40e5-a772-03d4601fa500",
                "evaluations": "知识库+步骤。对数字判断精准，比如1.18ms虽然比0.01飙升，但是没有超过20ms的阈值",
                "score": 4
            },
            {
                "trace_id": "7c039879-8e8c-4199-bef5-fde5c5c83e4a",
                "evaluations": "知识库+步骤。对数字判断有问题，在0.01飙升到1.18ms的情况下，会误判为超过20ms阈值",
                "score": 3
            },
            {
                "trace_id": "08adb766-8e1b-4c0a-9105-717a3991de33",
                "evaluations": "知识库+步骤。经过步骤拆分+任务拆分为小任务，deepseek解决了数字判断的问题",
                "score": 3
            }
        ]
        
        # 调用被测试函数
        result = build_score_standard(test_cases)
        

        
        print(result)

    # 运行测试
    # test_build_score_standard()

    
    def test_evaluate_result():
        # 准备测试数据
        trace_id = "7c9f99bf-1eb9-40e5-a772-03d4601fa500"
        right_answer = "磁盘 `1d040023-30e6-46f6-8cb6-9f05d85f49f1` 在 `2025-05-10 10:10` 至 `10:50` 期间的性能异常，**最主要的原因是其宿主机 `30.153.108.111` 与后端存储Set `WHOLE_DAILYBUILD_DEPOT_002` 的多个Cell IP之间发生了显著的网络丢包**。这个网络问题导致了IO延迟增大、吞吐量下降，并使得Set的服务时间也相应增加。"
        scoring_criteria = """
        <scoring_criteria>
        **5分: 非常优秀**
        *   **根本原因定位**：准确、高效地定位到问题的根本原因。
        *   **分析逻辑与效率**：分析逻辑清晰、严谨，遵循最少且必要的步骤。能够正确解读所有相关数据和指标，包括复杂场景下的细微差别。
        *   **工具使用**：工具调用准确无误，参数正确，没有冗余的工具调用。
        *   **自主性**：几乎无需人工干预或修正，能够独立完成高质量的分析。
        *   **沟通表达**：开场白和结论清晰、专业。
        *   **案例特征**：
            *   案例1：在没有预设步骤的情况下，通过多轮数据查询和分析，准确判断磁盘IO异常是由网络丢包引起。
            *   案例3：在没有预设步骤的情况下，通过查询磁盘IO指标和迁移任务，准确判断磁盘性能问题由迁移任务导致。

        **4分: 优秀**
        *   **根本原因定位**：准确找到根本原因。
        *   **分析逻辑与效率**：遵循了合理的分析流程（无论是自主的还是预设的）。对数据和阈值的判断基本准确，即使某些指标数值变化大，也能根据阈值做出正确判断（如案例4中Svctm从0.01ms飙升至1.18ms，但未超过20ms阈值，判断正确）。
        *   **工具使用**：工具调用基本准确，可能存在少量不影响结论的冗余步骤。
        *   **自主性**：需要的人工干预较少。
        *   **沟通表达**：开场白和结论清晰。
        *   **案例特征**：
            *   案例4：严格按照预设步骤执行，准确判断磁盘利用率超阈值，其他指标虽有变化但未超阈值，最终定位到迁移任务是原因。

        **3分: 普通**
        *   **根本原因定位**：最终能够定位到根本原因，或者提供了足够信息供人工判断得出正确结论。
        *   **分析逻辑与效率**：过程可能不顺畅或效率不高。分析步骤可能较多，或token消耗偏高。
        *   **工具使用**：可能出现工具调用错误（AI能自行修正或经用户提示修正），或者参数设置不完全正确导致需要重新调用。
        *   **自主性与数据解读**：可能对部分数据或阈值有初步误判（如案例6中将1.18ms误判为超过20ms阈值），或者在没有明确步骤指引时，需要用户提示才能进行更全面的排查。
        *   **沟通表达**：基本清晰，但可能在总结或建议上存在不足。
        *   **案例特征**：
            *   案例5：遵循预设步骤，但多次出现工具调用参数错误（如缺少region，cell_ips格式错误），需要AI自行修正或用户提示才能继续，最终定位到迁移任务。
            *   案例6：遵循用户指定的分步执行，找到了迁移任务这一关键信息，但在解读磁盘指标时对阈值判断有误，不过整体流程执行尚可。

        **2分: 有偏差**
        *   **根本原因定位**：分析逻辑大体合理，但结论错误或有明显偏差。
        *   **分析逻辑与效率**：对关键数据或阈值存在显著误读，导致偏离正确方向。
        *   **工具使用**：可能过早下结论，未能进行全面排查，或工具使用存在较多问题。
        *   **自主性**：需要用户大量干预才能引导至正确方向，或最终也未能准确定位。
        *   **沟通表达**：结论可能不准确或不完整。
        *   **案例特征**：
            *   案例2：初期仅凭磁盘IO指标异常就下结论，未能主动进行全面排查，需要用户明确指示后才补充了必要的排查步骤。

        **1分: 很差无法使用**
        *   **根本原因定位**：完全无法理解问题，或分析逻辑混乱、不相关。
        *   **分析逻辑与效率**：提供的结论完全错误或无任何参考价值，甚至产生误导。
        *   **工具使用**：无法有效使用工具，或工具调用完全错误。
        *   **自主性**：完全依赖用户纠错，无法独立完成分析。
        *   **沟通表达**：表达混乱，无法理解。

        **通用关注要点：**
        1.  **准确性**：能否准确找到根本原因，并正确解读各项指标和阈值。
        2.  **效率**：分析步骤是否简洁高效，有无冗余操作和不必要的token消耗。
        3.  **自主性**：在定位问题过程中，对用户提示和修正的依赖程度。前置引导越少且能准确定位，评分越高。
        4.  **工具使用熟练度**：能否正确、一次性地调用工具并获取所需信息。
        5.  **逻辑完整性**：是否进行了全面的排查，还是仅凭局部现象就下结论。
        6.  **遵循指示能力**：当有明确的排查流程或用户特定要求（如分步执行、独立分析）时，能否严格遵守。
        </scoring_criteria>
        """
        
        # 调用被测试函数
        result = evalute_result(trace_id, scoring_criteria,right_answer)
        print(result)
        # 验证返回结果格式
 

        case_list = [
            {
                "trace_id": "f5c89af8-d793-48c4-ae86-b6eb40ec3627",
                "right_answer": "最主要的原因是其宿主机 `30.153.108.111` 与后端存储Set `WHOLE_DAILYBUILD_DEPOT_002` 的多个Cell IP之间发生了显著的网络丢包"
            },
            {
                "trace_id": "598ac675-da83-4a6d-b41c-00d7c8385b85",
                "right_answer": "最主要的原因是其宿主机 `30.153.108.111` 与后端存储Set `WHOLE_DAILYBUILD_DEPOT_002` 的多个Cell IP之间发生了显著的网络丢包"
            },
            {
                "trace_id": "78f8b228-d084-4787-811b-e371c174b2c9",
                "right_answer": "磁盘性能异常是由于系统在 2025-04-11 15:22:24 启动了一个存储迁移任务，目的是进行存储利用率均衡。这种迁移过程会导致磁盘性能暂时下降"
            },
            {
                "trace_id": "7c9f99bf-1eb9-40e5-a772-03d4601fa500",
                "right_answer": "磁盘性能异常是由于系统在 2025-04-11 15:22:24 启动了一个存储迁移任务，目的是进行存储利用率均衡。这种迁移过程会导致磁盘性能暂时下降"
            },
            {
                "trace_id": "7c039879-8e8c-4199-bef5-fde5c5c83e4a",
                "right_answer": "磁盘性能异常是由于系统在 2025-04-11 15:22:24 启动了一个存储迁移任务，目的是进行存储利用率均衡。这种迁移过程会导致磁盘性能暂时下降"
            },
            {
                "trace_id": "08adb766-8e1b-4c0a-9105-717a3991de33",
                "right_answer": "磁盘性能异常是由于系统在 2025-04-11 15:22:24 启动了一个存储迁移任务，目的是进行存储利用率均衡。这种迁移过程会导致磁盘性能暂时下降"
            }
        ]

        for case in case_list:
            result = evalute_result(case["trace_id"], scoring_criteria,case["right_answer"])
            print(f"正确答案: {case['right_answer']}")
            print(f"评估结果: {result}")

    # 运行测试
    # test_evaluate_result()

    def test_evaluate_result2():
        # 准备测试数据
        trace_id = "7c9f99bf-1eb9-40e5-a772-03d4601fa500"
        right_answer = "磁盘 `1d040023-30e6-46f6-8cb6-9f05d85f49f1` 在 `2025-05-10 10:10` 至 `10:50` 期间的性能异常，**最主要的原因是其宿主机 `30.153.108.111` 与后端存储Set `WHOLE_DAILYBUILD_DEPOT_002` 的多个Cell IP之间发生了显著的网络丢包**。这个网络问题导致了IO延迟增大、吞吐量下降，并使得Set的服务时间也相应增加。"
        scoring_criteria = """
<scoring_criteria>

**关注要点 (Key Focus Areas for Evaluation):**

1.  **问题解决能力 (Problem Resolution Capability):**
    *   **分析过程有效性:** 分析过程是否逻辑清晰、步骤合理、全面？是否避免了过早下结论？
    *   **效率:** 是否在找到关键线索后能有效聚焦，避免不必要的步骤？

2.  **工具使用与数据解读 (Tool Usage & Data Interpretation):**
    *   **工具选择与参数:** 是否选择了合适的工具？工具调用的参数是否正确、完整？
    *   **数据提取与呈现:** 是否能有效提取关键数据并清晰呈现？
    *   **阈值判断与指标关联:** 是否能准确判断指标是否超阈值？是否能正确关联不同指标间的变化？

3.  **遵循指令与交互质量 (Adherence to Instructions & Interaction Quality):**
    *   **理解并遵循特定指令:** 是否能理解并遵循用户的特定指令（如“仅执行第X步”、“不要关联历史步骤”等）？
    *   **自主性与引导依赖:** Agent是自主推动排查，还是高度依赖用户引导和纠正？（自主性高且准确则加分）
    *   **沟通专业性:** 回复是否专业、条理清晰、易于理解？

4.  **对专家经验/排查流程的运用 (Application of Expert Knowledge/Procedures):**
    *   **“仅知识库”模式:** Agent是否能基于内置知识（无明确步骤指导）独立完成高质量排查？
    *   **“知识库+步骤”模式:** Agent是否能准确理解并执行预设的排查步骤？

---

**评分标准 (Scoring Rubric):**

**5分: 出色表现 (Excellent Performance)**
*   **工具与数据:** 工具使用完美无误，参数准确。数据提取精准，对各项指标（包括阈值判断）的解读深刻且完全正确。
*   **交互与指令:** 完全遵循用户指令，沟通清晰、专业。在“仅知识库”模式下展现出强大的自主排查能力。
*   **案例特征:**
    *   如对话记录1：在无明确步骤指导下，通过一系列逻辑连贯的工具调用，准确分析各项指标，最终定位到网络丢包这一根本原因，并给出清晰的综合分析和结论。
    *   如对话记录3：同样在“仅知识库”模式下，通过合理的排查顺序，在发现磁盘迁移任务这一明确根因后，高效地结束分析并给出正确结论。

**4分: 良好表现 (Good Performance)**
*   **工具与数据:** 工具使用基本正确，参数无大碍。数据提取和解读准确，特别是对阈值的判断精准。
*   **交互与指令:** 良好遵循用户指令，沟通清晰。
*   **案例特征:**
    *   如对话记录4：严格遵循了提供的10步排查流程，准确执行了每一步的工具调用，并对返回的指标数据（特别是磁盘迁移任务和各项性能阈值）做出了正确的解读，最终定位到根因。数字判断精准是其亮点。

**3分: 一般表现 (Average Performance)**
*   **工具与数据:** 工具使用或参数设置上可能出现一些小错误（如参数缺失、格式错误），需要修正后才能成功。数据解读基本正确，但可能在某些细节或复杂关联上出现偏差（如对阈值的判断出现失误）。
*   **交互与指令:** 基本遵循用户指令，但可能需要用户进行较多轮次的引导或澄清。在“知识库+步骤（分步执行）”模式下，能完成单步任务，但整体排查的连贯性和自主性不足。
*   **案例特征:**
    *   如对话记录5：虽然也遵循了10步排查流程，但在工具调用时出现参数错误（如region缺失，cell_ips格式错误），且在解读磁盘指标时对Svctm的阈值判断出现失误，尽管最终也找到了迁移任务这一根因。
    *   如对话记录6：用户明确要求分步执行，Agent在每一步都能正确响应并执行，但缺乏自主的全局分析和串联能力，高度依赖用户的指令驱动。通过拆分任务，避免了数字判断的错误。

**2分: 欠佳表现 (Below Average Performance)**
*   **工具与数据:** 工具使用频繁出错，或者对返回的数据进行错误的解读。
*   **交互与指令:** 可能难以理解复杂指令，或多次重复同样的错误，需要用户大量纠正。
*   **案例特征:**
    *   如对话记录2：在初步检查磁盘指标发现异常后，过早地给出了初步结论，未能主动进行更全面的排查。在用户提示后才继续进行更深入的分析，最终虽然也找到了网络丢包的根因，但初期的草率结论是主要扣分点。

**1分: 较差表现 (Poor Performance)**
*   **工具与数据:** 工具使用混乱，无法从数据中提取有效信息，或解读完全错误。
*   **交互与指令:** 无法遵循用户指令，沟通混乱，甚至可能提供误导性信息。
*   **(无对应案例，但可作为最低标准)**

</scoring_criteria>
        """
        
        # 调用被测试函数
        result = evalute_result2(trace_id, scoring_criteria)
        print(result)
        # 验证返回结果格式
 

        case_list = [
            {
                "trace_id": "f5c89af8-d793-48c4-ae86-b6eb40ec3627",
                "right_answer": "最主要的原因是其宿主机 `30.153.108.111` 与后端存储Set `WHOLE_DAILYBUILD_DEPOT_002` 的多个Cell IP之间发生了显著的网络丢包"
            },
            {
                "trace_id": "598ac675-da83-4a6d-b41c-00d7c8385b85",
                "right_answer": "最主要的原因是其宿主机 `30.153.108.111` 与后端存储Set `WHOLE_DAILYBUILD_DEPOT_002` 的多个Cell IP之间发生了显著的网络丢包"
            },
            {
                "trace_id": "78f8b228-d084-4787-811b-e371c174b2c9",
                "right_answer": "磁盘性能异常是由于系统在 2025-04-11 15:22:24 启动了一个存储迁移任务，目的是进行存储利用率均衡。这种迁移过程会导致磁盘性能暂时下降"
            },
            {
                "trace_id": "7c9f99bf-1eb9-40e5-a772-03d4601fa500",
                "right_answer": "磁盘性能异常是由于系统在 2025-04-11 15:22:24 启动了一个存储迁移任务，目的是进行存储利用率均衡。这种迁移过程会导致磁盘性能暂时下降"
            },
            {
                "trace_id": "7c039879-8e8c-4199-bef5-fde5c5c83e4a",
                "right_answer": "磁盘性能异常是由于系统在 2025-04-11 15:22:24 启动了一个存储迁移任务，目的是进行存储利用率均衡。这种迁移过程会导致磁盘性能暂时下降"
            },
            {
                "trace_id": "08adb766-8e1b-4c0a-9105-717a3991de33",
                "right_answer": "磁盘性能异常是由于系统在 2025-04-11 15:22:24 启动了一个存储迁移任务，目的是进行存储利用率均衡。这种迁移过程会导致磁盘性能暂时下降"
            }
        ]

        for case in case_list:
            result = evalute_result2(case["trace_id"], scoring_criteria)
            print(f"正确答案: {case['right_answer']}")
            print(f"评估结果: {result}")

    # test_evaluate_result2()


    def run_evaluate():


        scoring_criteria = """
<scoring_criteria>

**关注要点 (Key Focus Areas for Evaluation):**

1.  **问题解决能力 (Problem Resolution Capability):**
    *   **分析过程有效性:** 分析过程是否逻辑清晰、步骤合理、全面？是否避免了过早下结论？
    *   **效率:** 是否在找到关键线索后能有效聚焦，避免不必要的步骤？

2.  **工具使用与数据解读 (Tool Usage & Data Interpretation):**
    *   **工具选择与参数:** 是否选择了合适的工具？工具调用的参数是否正确、完整？
    *   **数据提取与呈现:** 是否能有效提取关键数据并清晰呈现？
    *   **阈值判断与指标关联:** 是否能准确判断指标是否超阈值？是否能正确关联不同指标间的变化？

3.  **遵循指令与交互质量 (Adherence to Instructions & Interaction Quality):**
    *   **理解并遵循特定指令:** 是否能理解并遵循用户的特定指令（如“仅执行第X步”、“不要关联历史步骤”等）？
    *   **自主性与引导依赖:** Agent是自主推动排查，还是高度依赖用户引导和纠正？（自主性高且准确则加分）
    *   **沟通专业性:** 回复是否专业、条理清晰、易于理解？

4.  **对专家经验/排查流程的运用 (Application of Expert Knowledge/Procedures):**
    *   **“仅知识库”模式:** Agent是否能基于内置知识（无明确步骤指导）独立完成高质量排查？
    *   **“知识库+步骤”模式:** Agent是否能准确理解并执行预设的排查步骤？

---

**评分标准 (Scoring Rubric):**

**5分: 出色表现 (Excellent Performance)**
*   **工具与数据:** 工具使用完美无误，参数准确。数据提取精准，对各项指标（包括阈值判断）的解读深刻且完全正确。
*   **交互与指令:** 完全遵循用户指令，沟通清晰、专业。在“仅知识库”模式下展现出强大的自主排查能力。
*   **案例特征:**
    *   如对话记录1：在无明确步骤指导下，通过一系列逻辑连贯的工具调用，准确分析各项指标，最终定位到网络丢包这一根本原因，并给出清晰的综合分析和结论。
    *   如对话记录3：同样在“仅知识库”模式下，通过合理的排查顺序，在发现磁盘迁移任务这一明确根因后，高效地结束分析并给出正确结论。

**4分: 良好表现 (Good Performance)**
*   **工具与数据:** 工具使用基本正确，参数无大碍。数据提取和解读准确，特别是对阈值的判断精准。
*   **交互与指令:** 良好遵循用户指令，沟通清晰。
*   **案例特征:**
    *   如对话记录4：严格遵循了提供的10步排查流程，准确执行了每一步的工具调用，并对返回的指标数据（特别是磁盘迁移任务和各项性能阈值）做出了正确的解读，最终定位到根因。数字判断精准是其亮点。

**3分: 一般表现 (Average Performance)**
*   **工具与数据:** 工具使用或参数设置上可能出现一些小错误（如参数缺失、格式错误），需要修正后才能成功。数据解读基本正确，但可能在某些细节或复杂关联上出现偏差（如对阈值的判断出现失误）。
*   **交互与指令:** 基本遵循用户指令，但可能需要用户进行较多轮次的引导或澄清。在“知识库+步骤（分步执行）”模式下，能完成单步任务，但整体排查的连贯性和自主性不足。
*   **案例特征:**
    *   如对话记录5：虽然也遵循了10步排查流程，但在工具调用时出现参数错误（如region缺失，cell_ips格式错误），且在解读磁盘指标时对Svctm的阈值判断出现失误，尽管最终也找到了迁移任务这一根因。
    *   如对话记录6：用户明确要求分步执行，Agent在每一步都能正确响应并执行，但缺乏自主的全局分析和串联能力，高度依赖用户的指令驱动。通过拆分任务，避免了数字判断的错误。

**2分: 欠佳表现 (Below Average Performance)**
*   **工具与数据:** 工具使用频繁出错，或者对返回的数据进行错误的解读。
*   **交互与指令:** 可能难以理解复杂指令，或多次重复同样的错误，需要用户大量纠正。
*   **案例特征:**
    *   如对话记录2：在初步检查磁盘指标发现异常后，过早地给出了初步结论，未能主动进行更全面的排查。在用户提示后才继续进行更深入的分析，最终虽然也找到了网络丢包的根因，但初期的草率结论是主要扣分点。

**1分: 较差表现 (Poor Performance)**
*   **工具与数据:** 工具使用混乱，无法从数据中提取有效信息，或解读完全错误。
*   **交互与指令:** 无法遵循用户指令，沟通混乱，甚至可能提供误导性信息。
*   **(无对应案例，但可作为最低标准)**

</scoring_criteria>
        """
        
        # 轮询监听时间 当敲好为整点时 执行任务
        last_run_hour = None
        while True:
            now = datetime.now()
            print(now.hour , last_run_hour)
            # 检查是否在整点前后5分钟内,且这个小时还未执行过
            if abs(now.minute - 30) <= 5 and now.hour != last_run_hour:
                print("整点执行任务")
                # 执行任务
                last_run_hour = now.hour

                # 获取上一个整点时刻的数据
                last_hour = now.replace(minute=30, second=0, microsecond=0) - timedelta(hours=1)
                now_hour = now.replace(minute=30, second=0, microsecond=0)
                # 获取traces数据
                traces_batch_response = langfuse_client.fetch_traces(
                    page=1,  # 从第1页开始
                    limit=100,  # 每页100条数据
                    from_timestamp=last_hour,  # 直接传入datetime对象
                    to_timestamp=now_hour  # 整点时刻
                )
                traces_batch = traces_batch_response.data

                # 从trace_batch中均匀采样选择10个 traceid 进行评估
                trace_ids = [trace.id for trace in traces_batch]
                # 如果总数不到10个则保留全部,否则均匀采样10个
                if len(trace_ids) <= 10:
                    trace_ids = trace_ids
                else:
                    # 均匀采样选择10个 traceid
                    trace_ids = trace_ids[::len(trace_ids)//10]


                print("评估trace个数",len(trace_ids))
                # 开始和结束时间
                print("开始时间",last_hour)
                print("结束时间",now_hour)
                print("last_run_hour",last_run_hour)
                # 对每个traceid 使用evalute_result2 进行评估 并将结果通langfuse上传评分
                for trace_id in trace_ids:
                    result = evalute_result2(trace_id, scoring_criteria)
                    # 将result 转换为json
                    try:
                        result_json = json.loads(result)
                        score = result_json["score"]
                        reason = result_json["reason"]
                    except:
                        score = 100000
                        reason = result


                    langfuse_client.score(
                        trace_id=trace_id,
                        name="quality_score",  # 质量评分
                        value=score,  # 评分结果
                        comment=reason  # 评分原因
                    )


            # print执行了多少条评估
                print(f"执行了{len(trace_ids)}条评估") 
    


            time.sleep(60)  # 每分钟检查一次
    run_evaluate()