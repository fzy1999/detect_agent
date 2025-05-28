rules = """## 指标数据异常检测规则：

================================================================ 0 前置准备（Inputs）
0.1 业务资产信息

 • 指标名称、单位、采样周期、归属服务 / 主机组 / 环境（prod / stag / dev）

 • 对应 SLO / SLA、故障分级（P1–P4）

0.2 技术环境

 • 监控链路（Prometheus/Grafana、Zabbix、Influx…）以及能否做 Recording Rule

 • 报警管道（Alertmanager、PagerDuty、飞书机器人…）

0.3 基准数据拉取脚本（必须可复用）

 promtool / curl → CSV → pandas，封装成一键工具，所有 Profiling 均调用此脚本。

================================================================ 1 语义解析 & 监控目标确认
1.1 名称拆解

 示例：OSLinux-CPU_CPU_CPUCpuUtil

 => Host-CPU → 资源利用率 → 0–100% → 越高越危险 → 上限型阈值

1.2 归类异常模式

 a. 阈值型

  • 上限：>阈值危险（CPUUtil、MemUsedPerc、DiskUsage）

  • 下限：<阈值危险（CpuIdle、CacheHitRate）

  • 双尾：上下都危险（P99 延迟、QPS）

 b. 形态型

  • Spike（单点尖刺）

  • Drift（平台抬升/下沉）

  • Trend（连续攀升/下降）

 c. 同环比型

  • 同比上周同时段

  • 环比前 N 点均值

1.3 预设报警等级

 | Grading | 影响范围 | 触发标准 | 当班响应 | 备注 |

 | P1 | 全局业务不可用 | 5 min 连续满足条件 | 7×24 on-call | ... |

 …（示例略）

================================================================ 2 数据摸底（Profiling）
脚本参数：metricName、start-30d、end-now、step=<采样周期>

2.1 统计量

 min / max / avg / p50 / p75 / p95 / p99，工作日-周末拆分两条曲线。

2.2 周期 & 趋势

 • 自相关（ACF≥0.5）判周期

 • STL-trend 斜率 > 0.5%/day 判趋势升/降

2.3 抖动幅度

 σ / mean > 0.3 判高波动 → 静态阈值可能误报，优先考虑动态阈值

2.4 采样完整性

 缺失点率 >5% → 只能做滑窗 IQR / EWMA，禁用需要等间隔的 Holt-Winters

================================================================ 3 规则优先（“能不用算法就别上算法”）
3.1 静态阈值

 • 参考 P95×安全系数、行业经验、安全红线

 • CPUUtil：>80% Warn, >90% Crit

 • DiskUsage：>70% Warn, >85% Crit

3.2 组合 / 分段阈值

 • CPUUtil > 80% 且 15 min 均值环比 +5% → P2

 • DiskUsage > 75% 且 1h 内增长 >2% → P2

3.3 周期化阈值（昼夜 / 周期）

 if hasStrongDailyCycle:

  为 24×7 小时槽分别计算 P95 → 上阈，P5 → 下阈

  Recording Rule 每天 02:00 滚动更新

3.4 去抖 / 合并

 • 触发窗口：连续 N 个点满足才报警（N=3）

 • 抑制窗口：告警恢复后 N 分钟内同类告警进入抑制（N=10）

================================================================ 4 轻量级动态算法
4.1 无缺失，稳定采样

 • EWMA(λ=0.3) + 3σ (上 / 下 / 双尾)

 • STL 分解 + residual 3σ → 解决非固定周期

4.2 有缺失 / 明显离散

 • 滑窗 IQR（N=20）：超出[Q1-1.5×IQR, Q3+1.5×IQR]

 • 计数类（error_cnt, 5xx）→ Poisson CUSUM (k=0.5, h=4)


DWT-MLEAD is an anomaly detection algorithm that uses the Discrete Wavelet Transform (DWT) and Maximum Likelihood Estimation (MLE) to detect anomalies in univariate time series. The algorithm performs mutli-level DWT using the Haar wavelet, slides windows over the DWT coefficients, and estimates the likelihood of each window using a Gaussian distribution. Anomalies are detected by comparing the likelihoods to a quantile boundary in each level and passing down the anomaly counts to the individual time points, which we use as anomaly scores. The original paper [1] subsequently clusters the anomalies to determine the anomaly centers. This step is not implemented in this version.

The k-Means anomaly detector uses k-Means clustering to detect anomalies in time series. The time series is split into windows of a fixed size, and the k-Means algorithm is used to cluster these windows. The anomaly score for each time point is the average Euclidean distance between the time point’s windows and the windows’ corresponding cluster centers.

LeftSTAMPi [1] calculates the left matrix profile of a time series, which is the distance to the nearest neighbor of all already observed subsequences (i.e. all preceding subsequences) in the time series, in an incremental manner. The matrix profile is then used to calculate the anomaly score for each time point. The larger the distance to the nearest neighbor, the more anomalous the time point is.

MERLIN is a discord discovery algorithm that uses a sliding window to find the most anomalous subsequence in a time series [1]. The algorithm is based on the Euclidean distance between subsequences of the time series.

This is based on STRAY (Search TRace AnomalY) [1], which is a modification of HDoutliers [2]. HDoutliers is a powerful algorithm for the detection of anomalous observations in a dataset, which has (among other advantages) the ability to detect clusters of outliers in multidimensional data without requiring a model of the typical behavior of the system. However, it suffers from some limitations that affect its accuracy. STRAY is an extension of HDoutliers that uses extreme value theory for the anomolous threshold calculation, to deal with data streams that exhibit non-stationary behavior.

参数全部用最近 7 d 数据滚动更新，落地成 Recording Rule 或 PromQL 内联表达式。

================================================================ 5 重算法（仅当 3 & 4 仍误报 / 漏报严重）
5.1 有明显季节性 + 长期趋势

 • Facebook Prophet（日+周季节 + changepoint_prior_scale=0.05）

5.2 噪声大但无季节性

 • ARIMA / SARIMA：订单量、交易额

5.3 多维耦合

 • IsolationForest (n_estimators=200, contamination=0.01)

 • One-Class SVM / AutoEncoder

 流程：日批离线训练 → 模型文件存 OSS → 线上推理微服务 → Prometheus remote-write 回系统


================================================================ 6 效果评估 & 闭环
7.1 回测

 • 选历史 N=60 d 已标注故障数据，计算 Precision/Recall/F1

 • F1<0.6 → 回到 Step 3–5 调参

7.2 Online A/B

 • 2 套规则，在线流量对半 → 7 d 统计误报/漏报

7.3 周期复盘

 • weekly review；指标退化 / 新指标 ↑ → 重走流程

================================================================ 思维导图式总览
理解指标 → 数据摸底 → 静态 & 周期阈值 → 去抖 / 抑制 → 轻量算法 → 重算法 → 报警编排 → 回测闭环

================================================================ 常见坑 & 经验贴
只做静态阈值却忘了 SLO：业务夜间低峰 CPU 30% 也可能是故障。
周期阈值必须跟随节假日：国庆 / 春节曲线会整体下移。
多维模型落地最大难点是线上推理与实时性，不要一开始就上深度学习。
“缺失值” 本身也是异常：采集器挂掉、网络抖动。要单独报警。
告警抑制与合并是控制噪音的第一生产力。

## 图表生成指南：

- 在分析过程中，如果认为生成图表有助于理解数据趋势、识别异常点或评估检测规则的效果，您可以指示执行者生成图表。
- 常用的图表类型可能包括：原始指标的时间序列曲线图、标记了检测到的异常点的曲线图、显示应用某种检测规则（如阈值、EWMA）后效果的对比图等。
- 指示执行者使用适当的Python库（如 Matplotlib 或 Seaborn）生成图表。
- 生成的图表应保存为图片文件（例如 PNG格式）。
- 图表文件必须保存到当前执行输出路径下的 `plot` 子目录中。完整的保存路径结构为 `{obs_path}/plot/文件名.png`。
- 在指示生成图表时，请尽量建议一个有意义的文件名，例如 `raw_metric_trend.png` 或 `cpu_util_with_anomalies_detected.png`。
- 执行者在完成图表生成后，应在其观察结果中报告已成功保存的图表文件名。您（作为控制者）应记录这些文件名以供后续使用。

您不应该做的事情：

不要在回复中包含任何编程语言（Python）。 相反，您应该用自然语言（中文）提供一个有序的步骤列表，并给出具体的描述。
不要自行将时间戳转换为日期时间或将日期时间转换为时间戳。 这些详细过程将由执行者处理。
不要使用本地数据（在特定时间段内过滤/缓存的序列）来计算聚合的“组件-KPI”时间序列的全局阈值。 始终使用指标文件中特定组件的整个KPI序列（通常包括一天的KPI）来计算阈值。为了获得全局阈值，您可以先聚合每个组件的每个KPI以计算其阈值，然后检索目标时间段的聚合“组件-KPI”以进行异常检测和尖峰过滤。
不要在给定时间段内过滤数据后再计算阈值。 始终在过滤给定时间段数据之前，使用指标文件中特定组件的整个KPI序列计算全局阈值。
不要在不知道有哪些KPI可用时查询特定KPI。 不同系统可能有完全不同的KPI命名约定。如果您想查询特定KPI，请首先确保您了解所有可用的KPI。
不要错误地将追踪中包含故障组件的下游端健康（非故障）服务识别为根本原因。 根本原因组件应是追踪调用链中出现的最下游故障服务，必须首先是通过指标分析识别出的故障组件。
不要在日志分析时仅关注警告或错误日志。许多信息日志包含有关服务操作和服务之间交互的关键信息，这些信息对根本原因分析非常有价值。
不要在回复中使用英文。 使用中文。
"""