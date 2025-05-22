
MODEL:    "deepseek-v3-local-II"
API_KEY:  "D6apCSNBgPVQF3r2kBhdsda1@4033"
API_BASE: "http://v2.open.venus.oa.com/llmproxy"

langfuse = Langfuse(
    secret_key="sk-lf-68a99e2d-b6d2-4386-bd8c-9b32f257ae1b",
    public_key="pk-lf-9a5d5405-9865-4f4a-97b6-38fc010d4753",
    host="http://9.134.214.7:8080"
)

1. Fetch Your Traces
Fetching traces from Langfuse is straightforward. Just set up the Langfuse client and use one of its functions to fetch the data. We’ll take an incremental approach: first, we’ll fetch the initial 10 traces and evaluate them. After that, we’ll add our scores back into Langfuse and move on to the next batch of 10 traces. We’ll keep this cycle going until we’ve processed a total of 50 traces.

The function has arguments to filter the traces by tags, timestamps, and beyond. We can also choose the number of samples for pagination. You can find more about other methods to query traces in our docs.fetch_traces()

from langfuse import Langfuse
from datetime import datetime, timedelta
 
BATCH_SIZE = 10
TOTAL_TRACES = 50
 
langfuse = Langfuse(
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    host="https://cloud.langfuse.com"  # 🇪🇺 EU region
)
 
now = datetime.now()
five_am_today = datetime(now.year, now.month, now.day, 5, 0)
five_am_yesterday = five_am_today - timedelta(days=1)
 
traces_batch = langfuse.fetch_traces(page=1,
                                     limit=BATCH_SIZE,
                                     tags="ext_eval_pipelines",
                                     from_timestamp=five_am_yesterday,
                                     to_timestamp=datetime.now()
                                   ).data
 
print(f"Traces in first batch: {len(traces_batch)}")

Traces in first batch: 10

2. Run your evaluations
Langfuse can handle numerical, boolean and categorical () scores. Wrapping your custom evaluation logic in a function is often a good practice. Evaluation functions should take a as input and yield a valid score. Let’s begin with a simple example using a categorical score.stringtrace

2.1. Categoric Evaluations
When analyzing the outputs of your LLM applications, you may want to evaluate traits that are best defined qualitatively, such as sentiment, tonality or text complexity (Grade level).

We’re building a science educator LLM that should sound engaging and positive. To ensure it hits the right notes, we’ll evaluate the tone of its outputs to see if they match our intent. We’ll draft an evaluation prompt ourselves (no library) to identify the three main tones in each model output.

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
 
 
test_tone_score = openai.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": template_tone_eval.format(
                text=traces_batch[1].output),
        }
    ],
    model="gpt-4o",
 
    temperature=0
).choices[0].message.content
print(f"User query: {traces_batch[1].input['args'][0]}")
print(f"Model answer: {traces_batch[1].output}")
print(f"Dominant tones: {test_tone_score}")

Identifying human intents and tones can be tricky for language models. To handle this, we used a multi-shot prompt, which means giving the model several examples to learn from. Now let’s wrap our code in an evaluation function for convenience.

def tone_score(trace):
    return openai.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": template_tone_eval.format(text=trace.output),
            }
        ],
        model="gpt-4o",
        temperature=0
    ).choices[0].message.content
 
tone_score(traces_batch[1])

Great! Now let’s go ahead and create a numeric evaluation score.

2.2. Numeric Evaluations
In this cookbook, we’ll use the framework (docs) to handle our numeric evaluations. Deepeval provides scores ranging from zero to one for many common LLM metrics. Plus, you can create custom metrics by simply describing them in plain language. To ensure our app’s responses are joyful and engaging, we’ll define a custom ‘joyfulness’ score.Deepeval

You can use any evaluation library. These are popular ones:

OpenAI Evals (GitHub)
Langchain Evaluators
RAGAS for RAG applications
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams, LLMTestCase
 
def joyfulness_score(trace):
		joyfulness_metric = GEval(
		    name="Correctness",
		    criteria="Determine whether the output is engaging and fun.",
		    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
		)
		test_case = LLMTestCase(
    input=trace.input["args"],
    actual_output=trace.output)
 
		joyfulness_metric.measure(test_case)
 
		print(f"Score: {joyfulness_metric.score}")
		print(f"Reason: {joyfulness_metric.reason}")
 
		return {"score": joyfulness_metric.score, "reason": joyfulness_metric.reason}
 
joyfulness_score(traces_batch[1])

Under the hood, GEval uses chain of thought (CoT) prompting to formulate a set of criteria for scoring prompts. When developing your own metrics, it’s important to review the reasoning behind these scores. This helps ensure that the model evaluates the traces just as you intended when you wrote the evaluation prompt.

Our eval function returns a dictionary with both the score and the model’s reasoning. We do this as we’ll persist the reasoning with every langfuse score, ensuring interpretability.

Now we’re done with defining our evaluation functions. Let’s push those scores back to Langfuse!

3. Pushing Scores to Langfuse
Now that we have our evaluation functions ready, it’s time to put them to work. Use the Langfuse client to add scores to existing traces.

langfuse.score(
    trace_id=traces_batch[1].id,
    name="tone",
    value=joyfulness_score(traces_batch[1])["score"],
    comment=joyfulness_score(traces_batch[1])["reason"]
)

And thus, you’ve added your first externally-evaluated score to Langfuse! Just 49 more to go 😁. But don’t worry — our solutions are easy to scale.

4. Putting everything together
Until now, we went through each of the necessary steps to build an external evaluation pipeline: Fetching traces, running the evaluations, and persisting the scores to Langfuse. Let’s sum it up into a compact script that you could run in your evaluation pipeline.

We’ll fetch the data in batches of 10 traces and then iterate through each trace to score it and push the scores back to Langfuse. Note that this batch size is for demonstration purposes. In a production setup, you might want to process multiple batches in parallel to speed things up. Batching not only reduces the memory load on your system but also allows you to create checkpoints, so you can easily resume if something goes wrong.

import math
 
for page_number in range(1, math.ceil(TOTAL_TRACES/BATCH_SIZE)):
 
    traces_batch = langfuse.fetch_traces(
        tags="ext_eval_pipelines",
        page=page_number,
        from_timestamp=five_am_yesterday,
        to_timestamp=five_am_today,
        limit=BATCH_SIZE
    ).data
 
    for trace in traces_batch:
        print(f"Processing {trace.name}")
 
        if trace.output is None:
            print(f"Warning: \n Trace {trace.name} had no generated output, \
            it was skipped")
            continue
 
        langfuse.score(
            trace_id=trace.id,
            name="tone",
            value=tone_score(trace)
        )
 
        jscore = joyfulness_score(trace)
        langfuse.score(
            trace_id=trace.id,
            name="joyfulness",
            value=jscore["score"],
            comment=jscore["reason"]
        )
 
    print(f"Batch {page_number} processed 🚀 \n")

If your pipeline ran successfully, you should see your score in the Langfuse UI.Trace with RAGAS scores

And that’s it! You’re now ready to integrate these lines into your preferred orchestration tool to ensure they run at the right times.

To achieve our original goal of running the script every day at 5 am, simply schedule a Cron task in your chosen environment with the rule .cron(0 5 * * ? *)

Thanks for coding along! I hope you enjoyed the tutorial and found it helpful.


请从langfuse拉取trace数据并进行评估，将得分上传到langfuse 实现写在/data/NAB/OpenRCA/evaluate/evalute.py