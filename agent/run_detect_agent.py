import os
import sys
import json
import argparse
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from main.evaluate import evaluate
from agent.api_router import configs

from datetime import datetime
from loguru import logger
from nbformat import v4 as nbf
import pandas as pd
import signal

from langfuse import Langfuse

langfuse = Langfuse(
    secret_key="sk-lf-68a99e2d-b6d2-4386-bd8c-9b32f257ae1b",
    public_key="pk-lf-9a5d5405-9865-4f4a-97b6-38fc010d4753",
    host="http://9.134.214.7:8080"
)


def handler(signum, frame):
    raise TimeoutError("Loop execution exceeded the time limit")



# 只跑单个语句
def run_single_query(query, dataset,output_path):

    from agent.detect_agent.detect_agent import Detect_Agent
    import agent.detect_agent.prompt.agent_prompt as ap
    if dataset == "Telecom":
        import agent.detect_agent.prompt.basic_prompt_Telecom as bp
    elif dataset == "Bank":
        import agent.detect_agent.prompt.basic_prompt_Bank as bp
    elif dataset == "Market/cloudbed-1" or dataset == "Market/cloudbed-2":
        import agent.detect_agent.prompt.basic_prompt_Market as bp

    now_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
    obs_path = os.path.join(output_path, configs['MODEL'].split('/')[-1],now_time)

    if not os.path.exists(obs_path):
        os.makedirs(obs_path)


    nb = nbf.new_notebook()
    nbfile = f"{obs_path}/trajectory.ipynb"
    promptfile = f"{obs_path}/prompt.json"
    logfile = f"{obs_path}/history.log"
    
    logger.remove()
    logger.add(sys.stdout, colorize=True, enqueue=True, level="INFO")
    logger.add(logfile, colorize=True, enqueue=True, level="INFO")
    
    print(f"obs_path: {obs_path}")
    


    agent = Detect_Agent(ap, bp)
    prediction, trajectory, prompt, trace_id, returned_obs_path = agent.run(query,
                                                                          logger,
                                                                          obs_path,
                                                                          max_step=25,
                                                                          max_turn=5)


    for step in trajectory:
        code_cell = nbf.new_code_cell(step['code'])
        result_cell = nbf.new_markdown_cell(f"```\n{step['result']}\n```")
        nb.cells.append(code_cell)
        nb.cells.append(result_cell)
    with open(nbfile, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=4)
    logger.info(f"Trajectory has been saved to {nbfile}")

    with open(promptfile, 'w', encoding='utf-8') as f:
        json.dump({"messages": prompt}, f, ensure_ascii=False, indent=4)
    logger.info(f"Prompt has been saved to {promptfile}")
    
    return trace_id, returned_obs_path




if __name__ == "__main__":
    
    # uid = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--dataset", type=str, default="Market/cloudbed-1")
    # parser.add_argument("--sample_num", type=int, default=1)
    # parser.add_argument("--start_idx", type=int, default=0)
    # parser.add_argument("--end_idx", type=int, default=150)
    # parser.add_argument("--controller_max_step", type=int, default=25)
    # parser.add_argument("--controller_max_turn", type=int, default=5)
    # parser.add_argument("--timeout", type=int, default=600)
    # parser.add_argument("--tag", type=str, default='rca')
    # parser.add_argument("--auto", type=bool, default=False)

    # args = parser.parse_args()

    # if args.auto:
    #     print(f"Auto mode is on. Model is fixed to {configs['MODEL']}")
    #     datasets = ["Market/cloudbed-1", "Market/cloudbed-2", "Bank", "Telecom"]
    #     for dataset in datasets:
    #         main(args, uid, dataset)
    # else:
    #     dataset = args.dataset
    #     main(args, uid, dataset)

    output_path = "/data/NAB/OpenRCA/test"
    dataset = "Bank"

    ### bank
    # query = "对apache01的指标配置异常检测方案 CPU 利用率（OSLinux-CPU_CPU_CPUCpuUtil）、内存使用率（OSLinux-OSLinux_MEMORY_MEMORY_MEMUsedMemPerc）、非缓存内存使用率（OSLinux-OSLinux_MEMORY_MEMORY_NoCacheMemPerc）和 Apache 文件系统容量使用率（OSLinux-OSLinux_FILESYSTEM_-apache_FSCapacity）"
    
    ### telecom
    # query = "对redis_009的指标配置异常检测方案 "
    # query = "level,reason,component,timestamp,datetime service,db close,db_007,1590256020,2020-05-24 01:47:00,对于那些指标制定合理的异常检测方案，能够发现告警该问题"
    # query = "监控所有容器的CPU、内存使用，以及是否存活"
    # query = "监控所有物理机/虚拟机的CPU、内存、磁盘、网络基础状态"
    query = " 监控数据库服务的指标 db_007 （CPU_Used_Pct、MEM_Used_Pct、Tbs_Used_Pct）配置异常检测算法"
    # query = "监控关键中间件（如Redis）的连接数、队列等"


    # bank
#     query = """
#     level,component,timestamp,datetime,reason
# pod,Mysql02,1614841020.0,2021-03-04 14:57:00,high memory usage

# 对于哪些指标制定合理的异常检测方案能够发现此类问题
#     """
#     query = """
#     level,component,timestamp,datetime,reason
# pod,Tomcat02,1614856920.0,2021-03-04 19:22:00,network latency

# 对于哪些指标制定合理的异常检测方案能够发现此类问题
#     """
#     query = """
#     level,component,timestamp,datetime,reason
# pod,MG02,1615048320.0,2021-03-07 00:32:00,network packet loss

# 对于哪些指标制定合理的异常检测方案能够发现此类问题
#     """
    query = "对Mysql02的指标配置异常检测方案"
    run_single_query(query, dataset, output_path)