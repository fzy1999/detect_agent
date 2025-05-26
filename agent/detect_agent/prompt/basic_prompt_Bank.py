schema = """## 遥测数据目录结构：

- 您可以通过以下路径访问我们微服务系统中的遥测目录：`/data/NAB/OpenRCA/dataset/Bank/telemetry/`。

- 此目录包含按日期组织的子目录（例如，`/data/NAB/OpenRCA/dataset/Bank/telemetry/2021_03_05/`）。

- 在每个特定日期的目录中，您会找到以下子目录：`metric`、`trace` 和 `log`（例如，`/data/NAB/OpenRCA/dataset/Bank/telemetry/2021_03_05/metric/`）。

- 这些子目录中的遥测数据以 CSV 格式存储（例如，`/data/NAB/OpenRCA/dataset/Bank/telemetry/2021_03_05/metric/metric_container.csv`）。

## 数据模式

1.  **指标文件 (Metric Files)**：
    
    1. `metric_app.csv`：

        ```csv
        timestamp,rr,sr,cnt,mrt,tc
        1614787440,100.0,100.0,22,53.27,ServiceTest1
        ```

    2. `metric_container.csv`：

        ```csv
        timestamp,cmdb_id,kpi_name,value
        1614787200,Tomcat04,OSLinux-CPU_CPU_CPUCpuUtil,26.2957
        ```

2.  **追踪文件 (Trace Files)**：

    1. `trace_span.csv`：

        ```csv
        timestamp,cmdb_id,parent_id,span_id,trace_id,duration
        1614787199628,dockerA2,369-bcou-dle-way1-c514cf30-43410@0824-2f0e47a816-17492,21030300016145905763,gw0120210304000517192504,19
        ```

3.  **日志文件 (Log Files)**：

    1. `log_service.csv`：

        ```csv
        log_id,timestamp,cmdb_id,log_name,value
        8c7f5908ed126abdd0de6dbdd739715c,1614787201,Tomcat01,gc,"3748789.580: [GC (CMS Initial Mark) [1 CMS-initial-mark: 2462269K(3145728K)] 3160896K(4089472K), 0.1985754 secs] [Times: user=0.59 sys=0.00, real=0.20 secs] "
        ```


## 遥测数据说明：

1.  此微服务系统是一个银行平台。

2.  `metric_app.csv` 文件仅包含四个 KPI：rr，sr，cnt 和 mrt。 相比之下，`metric_container.csv` 记录了各种 KPI，例如 CPU 使用率和内存使用率。 这些 KPI 的具体名称可以在 `kpi_name` 字段中找到。

3.  在不同的遥测文件中，时间戳单位和 cmdb_id 格式可能有所不同：

    *   指标 (Metric)：时间戳单位为秒（例如，1614787440）。
    *   追踪 (Trace)：时间戳单位为毫秒（例如，1614787199628）。
    *   日志 (Log)：时间戳单位为秒（例如，1614787201）。

4.  请在所有分析步骤中使用 UTC+8 时区，因为系统部署在中国/香港/新加坡。

5.  务必使用中文
 """