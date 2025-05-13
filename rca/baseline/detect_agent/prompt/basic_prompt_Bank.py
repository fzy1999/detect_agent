cand = """## 可能的根本原因：

CPU 使用率高
内存使用率高
网络延迟
网络丢包
磁盘 I/O 读取使用率高
磁盘空间使用率高
JVM CPU 负载高
JVM 内存溢出 (OOM) 堆
可能的根本原因组件：
apache01
apache02
Tomcat01
Tomcat02
Tomcat04
Tomcat03
MG01
MG02
IG01
IG02
Mysql01
Mysql02
Redis01
Redis02"""



schema = f"""## 遥测数据目录结构：

您可以访问我们微服务系统中的遥测数据目录：dataset/Bank/telemetry/。


在分析的时候请读取dataset/Bank/telemetry/ 下面的所有日志的数据
该目录包含按日期组织的子目录（例如，dataset/Bank/telemetry/2021_03_05/）。

对于metric文件夹下面每一个文件都需要进行分析
在每个特定日期的目录中，您会找到以下子目录：metric（例如，dataset/Bank/telemetry/2021_03_05/metric/）。

这些子目录中的遥测数据以 CSV 格式存储（例如，dataset/Bank/telemetry/2021_03_05/metric/metric_container.csv）。

数据模式
指标文件：

metric_app.csv：

CSV
timestamp,rr,sr,cnt,mrt,tc
1614787440,100.0,100.0,22,53.27,ServiceTest1
metric_container.csv：

CSV
timestamp,cmdb_id,kpi_name,value
1614787200,Tomcat04,OSLinux-CPU_CPU_CPUCpuUtil,26.2957
追踪文件：

trace_span.csv：

CSV
timestamp,cmdb_id,parent_id,span_id,trace_id,duration
1614787199628,dockerA2,369-bcou-dle-way1-c514cf30-43410@0824-2f0e47a816-17492,21030300016145905763,gw0120210304000517192504,19
日志文件：

log_service.csv：

CSV
log_id,timestamp,cmdb_id,log_name,value
8c7f5908ed126abdd0de6dbdd739715c,1614787201,Tomcat01,gc,"3748789.580: [GC (CMS Initial Mark) [1 CMS-initial-mark: 2462269K(3145728K)] 3160896K(4089472K), 0.1985754 secs] [Times: user=0.59 sys=0.00, real=0.20 secs] "


遥测数据说明：
此微服务系统是一个银行平台。

metric_app.csv 文件仅包含四个 KPI：rr, sr, cnt 和 mrt。相比之下，metric_container.csv 记录了多种 KPI，例如 CPU 使用率和内存使用率。这些 KPI 的具体名称可以在 kpi_name 字段中找到。

在不同的遥测文件中，时间戳单位和 cmdb_id 格式可能不同：

指标：时间戳单位为秒（例如，1614787440）。

追踪：时间戳单位为毫秒（例如，1614787199628）。

日志：时间戳单位为秒（例如，1614787201）。

由于系统部署在中国/香港/新加坡，请在所有分析步骤中使用 UTC+8 时区。

务必使用中文"""