cand = """

"""

schema = f"""## 遥测数据目录结构：

您可以访问的遥测数据目录：/data/NAB/OpenRCA/dataset/CBS


这些子目录中的遥测数据以 CSV 格式存储（例如，/data/NAB/OpenRCA/dataset/CBS/Avgqu.csv）。
一共包含多个个csv文件，文件名就是指标数据名称，每个文件包含一个指标的值，时间戳，ip_address

本目录下包含以下6个CSV文件，每个文件名即为指标名称：

- dpdkport_E_LB_SG_SVC.csv
- dpdkport_E_SVC_CC_OUT_OF_CONN.csv
- dpdkport_E_SVC_NOT_FOUND.csv
- netSocketTCP.csv
- stls_svc_deny_pkts.csv
- svc_not_found_pps.csv

每个文件包含该指标的值、时间戳。

数据模式
指标文件：



注意csv文件中的时间排列顺序是混乱的 请按照时间戳排序后进行进一步的分析
CSV
timestamp,value
2025-04-11 00:00,48.27
2025-04-11 00:01,48.07
2025-04-11 00:02,48.09
2025-04-11 00:03,48.15
2025-04-11 00:04,48.28
2025-04-11 00:05,48.41




遥测数据说明：

CBS云硬盘的指标数据




由于系统部署在中国/香港/新加坡，请在所有分析步骤中使用 UTC+8 时区。

class DWT_MLEAD(start_level: int = 3, quantile_boundary_type: str = 'percentile', quantile_epsilon: float = 0.01)[source]
DWT-MLEAD anomaly detector.

DWT-MLEAD is an anomaly detection algorithm that uses the Discrete Wavelet Transform (DWT) and Maximum Likelihood Estimation (MLE) to detect anomalies in univariate time series. The algorithm performs mutli-level DWT using the Haar wavelet, slides windows over the DWT coefficients, and estimates the likelihood of each window using a Gaussian distribution. Anomalies are detected by comparing the likelihoods to a quantile boundary in each level and passing down the anomaly counts to the individual time points, which we use as anomaly scores. The original paper [1] subsequently clusters the anomalies to determine the anomaly centers. This step is not implemented in this version.

Parameters:
start_levelint, default=3
The level at which to start the anomaly detection. Must be >= 0 and less than log_2(n_timepoints).

quantile_boundary_typestr, default=’percentile’
The type of boundary to use for the quantile. Must be ‘percentile’, ‘monte-carlo’ is not implemented yet.

quantile_epsilonfloat, default=0.01
The epsilon value for the quantile boundary. Must be in [0, 1].

Notes

Capabilities 
Missing Values

No

Multithreading

No

Univariate

Yes

Multivariate

No

This implementation does not exactly match the original paper [1]. We make the following changes:

We use window sizes for the DWT coefficients that decrease with the level number because otherwise we would have too few items to slide the window over.

We exclude the highest level coefficients because they contain only a single entry and are, thus, not suitable for sliding a window of length 2 over it.

We have not implemented the Monte Carlo quantile boundary type yet.

We do not perform the anomaly clustering step to determine the anomaly centers. Instead, we return the anomaly scores for each timestep in the original time series.

References

[1](1,2)
Thill, Markus, Wolfgang Konen, and Thomas Bäck. “Time Series Anomaly Detection with Discrete Wavelet Transforms and Maximum Likelihood Estimation.” In Proceedings of the International Conference on Time Series (ITISE). Granada, Spain, 2017.

Examples

import numpy as np
from aeon.anomaly_detection import DWT_MLEAD
X = np.array([1, 2, 3, 4, 1, 2, 3, 3, 2, 8, 9, 8, 1, 2, 3, 4], dtype=np.float64)
detector = DWT_MLEAD(
   start_level=1, quantile_boundary_type='percentile', quantile_epsilon=0.01
)
detector.fit_predict(X)
array([0., 0., 0., 0., 0., 0., 0., 0., 2., 2., 2., 2., 0., 0., 0., 0.])


class KMeansAD(n_clusters: int = 20, window_size: int = 20, stride: int = 1, random_state: int | None = None)[source]
KMeans anomaly detector.

The k-Means anomaly detector uses k-Means clustering to detect anomalies in time series. The time series is split into windows of a fixed size, and the k-Means algorithm is used to cluster these windows. The anomaly score for each time point is the average Euclidean distance between the time point’s windows and the windows’ corresponding cluster centers.

k-MeansAD supports univariate and multivariate time series. It can also be fitted on a clean reference time series and used to detect anomalies in a different target time series with the same number of dimensions.

Parameters:
n_clustersint, default=20
The number of clusters to use in the k-Means algorithm. The bigger the number of clusters, the less noisy the anomaly scores get. However, the number of clusters should not be too high, as this can lead to overfitting.

window_sizeint, default=20
The size of the sliding window used to split the time series into windows. The bigger the window size, the bigger the anomaly context is. If it is too big, however, the detector marks points anomalous that are not. If it is too small, the detector might not detect larger anomalies or contextual anomalies at all. If window_size is smaller than the anomaly, the detector might detect only the transitions between normal data and the anomalous subsequence.

strideint, default=1
The stride of the sliding window. The stride determines how many time points the windows are spaced appart. A stride of 1 means that the window is moved one time point forward compared to the previous window. The larger the stride, the fewer windows are created, which leads to noisier anomaly scores.

random_stateint, default=None
The random state to use in the k-Means algorithm.

Notes

Capabilities 
Missing Values

No

Multithreading

No

Univariate

Yes

Multivariate

Yes

This implementation is inspired by [1]. However, the original paper proposes a different kind of preprocessing and also uses advanced techniques to post-process the clustering.

References

[1]
Yairi, Takehisa, Yoshikiyo Kato, and Koichi Hori. “Fault Detection by Mining Association Rules from House-Keeping Data.” In Proceedings of the International Symposium on Artificial Intelligence, Robotics and Automation in Space (-SAIRAS), Vol. 6., 2001.

Examples

import numpy as np
from aeon.anomaly_detection import KMeansAD
X = np.array([1, 2, 3, 4, 1, 2, 3, 3, 2, 8, 9, 8, 1, 2, 3, 4], dtype=np.float64)
detector = KMeansAD(n_clusters=3, window_size=4, stride=1, random_state=0)
detector.fit_predict(X)
array([1.97827709, 2.45374147, 2.51929879, 2.36979677, 2.34826601,
       2.05075554, 2.57611912, 2.87642119, 3.18400743, 3.65060425,
       3.36402514, 3.94053744, 3.65448197, 3.6707922 , 3.70341266,
       1.97827709])



class LeftSTAMPi(window_size: int = 3, n_init_train: int = 3, normalize: bool = True, p: float = 2.0, k: int = 1)[source]
LeftSTAMPi anomaly detector.

LeftSTAMPi [1] calculates the left matrix profile of a time series, which is the distance to the nearest neighbor of all already observed subsequences (i.e. all preceding subsequences) in the time series, in an incremental manner. The matrix profile is then used to calculate the anomaly score for each time point. The larger the distance to the nearest neighbor, the more anomalous the time point is.

LeftSTAMPi supports univariate time series only.

Parameters:
window_sizeint, default=3
Size of the sliding window. Defaults to the minimal possible value of 3.

n_init_train: int, default=3
The number of points used to init the matrix profile. n_init_train must not be smaller than window_size. The discord will not be found in this segment.

normalizebool, default=True
Whether to normalize the windows before computing the distance.

pfloat, default=2.0
The p-norm to use for the distance calculation.

kint, default=1
The number of top distances to return.

Notes

Capabilities 
Missing Values

No

Multithreading

No

Univariate

Yes

Multivariate

No

References

[1]
Chin-Chia Michael Yeh, Yan Zhu, Liudmila Ulanova, Nurjahan Begum, Yifei Ding, Hoang Anh Dau, Diego Furtado Silva, Abdullah Mueen, and Eamonn Keogh: “Matrix Profile I: All Pairs Similarity Joins for Time Series: A Unifying View That Includes Motifs, Discords and Shapelets.”, In Proceedings of the International Conference on Data Mining (ICDM), 1317–1322. doi: 10.1109/ICDM.2016.0179

Examples

Calculate the anomaly score for the complete time series at once. Internally,this is applying the incremental approach outlined below.

import numpy as np 
from aeon.anomaly_detection import LeftSTAMPi  
X = np.random.default_rng(42).random((10))  
detector = LeftSTAMPi(window_size=3, n_init_train=3)  
detector.fit_predict(X)  
array([0.        , 0.        , 0.        , 0.07042306, 0.15989868,
       0.68912499, 0.75398303, 0.89696118, 0.5516023 , 0.69736132])


class MERLIN(min_length=5, max_length=50, max_iterations=500)[source]
MERLIN anomaly detector.

MERLIN is a discord discovery algorithm that uses a sliding window to find the most anomalous subsequence in a time series [1]. The algorithm is based on the Euclidean distance between subsequences of the time series.

Parameters:
min_lengthint, default=5
Minimum length of the subsequence to search for. Must be at least 4.

max_lengthint, default=50
Maximum length of the subsequence to search for. Must be at half the length of the time series or less.

max_iterationsint, default=500
Maximum number of DRAG iterations to find an anomalous sequence for each length. If no anomaly is found, the algorithm will move to the next length and reset r.

Notes

Capabilities 
Missing Values

No

Multithreading

No

Univariate

Yes

Multivariate

No

References

[1]
Nakamura, M. Imamura, R. Mercer and E. Keogh, “MERLIN: Parameter-Free Discovery of Arbitrary Length Anomalies in Massive Time Series Archives,” 2020 IEEE International Conference on Data Mining (ICDM), Sorrento, Italy, 2020, pp. 1190-1195.

Examples

import numpy as np
from aeon.anomaly_detection import MERLIN
X = np.array([1, 2, 3, 4, 1, 2, 3, 4, 2, 3, 4, 5, 1, 2, 3, 4])
detector = MERLIN(min_length=4, max_length=5)
detector.fit_predict(X)
array([False, False, False, False,  True,  True, False, False, False,
       False, False, False, False, False, False, False])




class STOMP(window_size: int = 10, ignore_trivial: bool = True, normalize: bool = True, p: float = 2.0, k: int = 1)[source]
STOMP anomaly detector.

STOMP calculates the matrix profile of a time series which is the distance to the nearest neighbor of each subsequence in the time series. The matrix profile is then used to calculate the anomaly score for each time point. The larger the distance to the nearest neighbor, the more anomalous the time point is.

STOMP supports univariate time series only.

Parameters:
window_sizeint, default=10
Size of the sliding window.

ignore_trivialbool, default=True
Whether to ignore trivial matches in the matrix profile.

normalizebool, default=True
Whether to normalize the windows before computing the distance.

pfloat, default=2.0
The p-norm to use for the distance calculation.

kint, default=1
The number of top distances to return.

Notes

Capabilities 
Missing Values

No

Multithreading

No

Univariate

Yes

Multivariate

No

References

[1]
Zhu, Yan and Zimmerman, Zachary and Senobari, Nader Shakibay and Yeh, Chin-Chia Michael and Funning, Gareth and Mueen, Abdullah and Brisk, Philip and Keogh, Eamonn. “Matrix Profile II: Exploiting a Novel Algorithm and GPUs to Break the One Hundred Million Barrier for Time Series Motifs and Joins.” In Proceedings of the 16th International Conference on Data Mining (ICDM), 2016.

Examples

import numpy as np
from aeon.anomaly_detection import STOMP  
X = np.random.default_rng(42).random((10, 2), dtype=np.float64)
detector = STOMP(X, window_size=2)  
detector.fit_predict(X, axis=0)  
array([1.02352234 1.00193038 0.98584441 0.99630753 1.00656619 1.00682081 1.00781515
       0.99709741 0.98878895 0.99723947])


class STRAY(alpha: float = 0.01, k: int = 10, knn_algorithm: str = 'brute', p: float = 0.5, size_threshold: int = 50, outlier_tail: str = 'max')[source]
STRAY: robust anomaly detection in data streams with concept drift.

This is based on STRAY (Search TRace AnomalY) [1], which is a modification of HDoutliers [2]. HDoutliers is a powerful algorithm for the detection of anomalous observations in a dataset, which has (among other advantages) the ability to detect clusters of outliers in multidimensional data without requiring a model of the typical behavior of the system. However, it suffers from some limitations that affect its accuracy. STRAY is an extension of HDoutliers that uses extreme value theory for the anomolous threshold calculation, to deal with data streams that exhibit non-stationary behavior.

Parameters:
alphafloat, default=0.01
Threshold for determining the cutoff for outliers. Observations are considered outliers if they fall in the (1 - alpha) tail of the distribution of the nearest-neighbor distances between exemplars.

kint, default=10
Number of neighbours considered.


(default=”brute”) Algorithm used to compute the nearest neighbors, from sklearn.neighbors.NearestNeighbors

pfloat, default=0.5
Proportion of possible candidates for outliers. This defines the starting point for the bottom up searching algorithm.

size_thresholdint, default=50
Sample size to calculate an emperical threshold.


Direction of the outlier tail.

Notes

Capabilities 
Missing Values

Yes

Multithreading

No

Univariate

Yes

Multivariate

Yes

References

[1]
Talagala, Priyanga Dilini, Rob J. Hyndman, and Kate Smith-Miles. “Anomaly detection in high-dimensional data.” Journal of Computational and Graphical Statistics 30.2 (2021): 360-374.

[2]
Wilkinson, Leland. “Visualizing big data outliers through distributed aggregation.” IEEE transactions on visualization and computer graphics 24.1 (2017): 256-266.

Examples

from aeon.anomaly_detection import STRAY
from aeon.datasets import load_airline
import numpy as np
X = load_airline()
detector = STRAY(k=3)
y = detector.fit_predict(X)
y[:5]
array([False, False, False, False, False])


"""