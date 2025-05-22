cand = """## POSSIBLE ROOT CAUSE REASONS:
        
- CPU fault
- network delay
- network loss 
- db connection limit 
- db close

## POSSIBLE ROOT CAUSE COMPONENTS:

(if the root cause is at the node level, i.e., the root cause is a specific node)

- os_001
- os_002
- os_003
- os_004
- os_005
- os_006
- os_007
- os_008
- os_009
- os_010
- os_011
- os_012
- os_013
- os_014
- os_015
- os_016
- os_017
- os_018
- os_019
- os_020
- os_021
- os_022

(if the root cause is at the pod level, i.e., the root cause is a specific container)

- docker_001
- docker_002
- docker_003
- docker_004
- docker_005
- docker_006
- docker_007
- docker_008

(if the root cause is at the service level, i.e., if all pods of a specific service are faulty, the root cause is the service itself)

- db_001
- db_002
- db_003
- db_004
- db_005
- db_006
- db_007
- db_008
- db_009
- db_010
- db_011
- db_012
- db_013"""

schema = f"""## 遥测数据目录结构：

您可以访问我们微服务系统中的遥测数据目录：dataset/Telecom/telemetry/

在分析的时候请读取dataset/Telecom/telemetry/ 下面的所有日志的数据
该目录包含按日期组织的子目录（例如，dataset/Telecom/telemetry/2020_04_11/）。

对于metric文件夹下面每一个文件都需要进行分析
在每个特定日期的目录中，您会找到以下子目录：metric 和 trace（例如，dataset/Telecom/telemetry/2020_04_11/metric/）。

这些子目录中的遥测数据以 CSV 格式存储（例如，dataset/Telecom/telemetry/2020_04_11/metric/metric_container.csv）。

数据模式
指标文件：

metric_app.csv：

CSV
serviceName,startTime,avg_time,num,succee_num,succee_rate
osb_001,1586534400000,0.333,1,1,1.0
metric_container.csv：

CSV
itemid,name,bomc_id,timestamp,value,cmdb_id
999999996381330,container_mem_used,ZJ-004-060,1586534423000,59.000000,docker_008
metric_middleware.csv：

CSV
itemid,name,bomc_id,timestamp,value,cmdb_id
999999996508323,connected_clients,ZJ-005-024,1586534672000,25,redis_003
metric_node.csv：

CSV
itemid,name,bomc_id,timestamp,value,cmdb_id
999999996487783,CPU_iowait_time,ZJ-001-010,1586534683000,0.022954,os_017
metric_service.csv：

CSV
itemid,name,bomc_id,timestamp,value,cmdb_id
999999998650974,MEM_Total,ZJ-002-055,1586534694000,381.902264,db_003
追踪文件：



遥测数据说明：
此服务系统是一个电信数据库系统。

metric_app.csv 文件仅包含五个 KPI：startTime, avg_time, num, succee_num, succee_rate。相比之下，其他指标文件记录了多种 KPI，例如 CPU 使用率和内存使用率。这些 KPI 的具体名称可以在 name 字段中找到。

在所有遥测文件中，时间戳单位和 cmdb_id 格式保持一致：

指标：时间戳单位为毫秒（例如，1586534423000）。
追踪：时间戳单位为毫秒（例如，1586534400335）。
由于系统部署在中国/香港/新加坡，请在所有分析步骤中使用 UTC+8 时区。"""