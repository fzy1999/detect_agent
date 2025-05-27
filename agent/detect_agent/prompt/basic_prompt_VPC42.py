cand = """

"""

schema = f"""## 遥测数据目录结构：

您可以访问的遥测数据目录：/data/NAB/OpenRCA/dataset/VPC42/csv


这些子目录中的遥测数据以 CSV 格式存储（例如，/data/NAB/OpenRCA/dataset/VPC42/csv/netSocketTCP.csv）。
一共包含6个csv文件，文件名就是指标数据名称，每个文件包含一个指标的值，时间戳，ip_address

本目录下包含以下6个CSV文件，每个文件名即为指标名称：

- dpdkport_E_LB_SG_SVC.csv
- dpdkport_E_SVC_CC_OUT_OF_CONN.csv
- dpdkport_E_SVC_NOT_FOUND.csv
- netSocketTCP.csv
- stls_svc_deny_pkts.csv
- svc_not_found_pps.csv

每个文件包含该指标的值、时间戳和ip_address字段。

数据模式
指标文件：

metric_app.csv：

由于数据存在多个`ip_address`，为了进行整体的周期性和趋势分析，请先按`time`对`value`进行聚合，计算每个时间点的均值，生成一个新的单变量时间序列
注意csv文件中的时间排列顺序是混乱的 请按照时间戳排序后进行进一步的分析
CSV
time,value,ip_address
2025-04-01 13:48,0,30.149.8.10
2025-04-01 13:49,0,30.149.8.10
2025-04-01 13:50,0,30.149.8.10
2025-04-01 13:51,0,30.149.8.10
2025-04-01 13:52,0,30.149.8.10




遥测数据说明：

是高性能网络产品中心 VPCGW应用的一些关键指标




由于系统部署在中国/香港/新加坡，请在所有分析步骤中使用 UTC+8 时区。"""