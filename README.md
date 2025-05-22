# 智能异常检测配置Agent (Intelligent Anomaly Detection Configuration Agent)

## Project Title and Overview

The Intelligent Anomaly Detection Configuration Agent is a project designed to automate the configuration of anomaly detection systems. It leverages a Large Language Model (LLM)-based agent to understand user requirements specified in natural language and generate appropriate configurations. The primary goal is to simplify and accelerate the setup of anomaly detection, making it more accessible to users without deep technical expertise in anomaly detection systems.

## Features

*   **Natural Language Queries:** Users can specify their anomaly detection needs using natural language.
*   **Automated Configuration Generation:** The agent automatically generates anomaly detection configurations based on user input and dataset characteristics.
*   **LLM-Driven Reasoning:** The agent utilizes LLM capabilities for reasoning and decision-making throughout the configuration process.
*   **Dataset-Specific Knowledge:** The agent can incorporate knowledge about specific datasets, including their schemas and potential anomaly causes for various domains (e.g., Telecom, Banking).
*   **Step-by-Step Execution Trajectory:** The agent's execution process, including decisions and generated configurations, is logged to a Jupyter notebook for transparency and review.
*   **Langfuse Integration:** Detailed tracing of the agent's operations is available through integration with Langfuse.
*   **Web Interface:** A user-friendly web interface allows for easy interaction with the agent.
*   **Command-Line Interface (CLI):** A CLI is available for direct execution and scripting of agent tasks.

## How it Works (Architecture)

The system is composed of several key components that interact to provide an automated anomaly detection configuration experience:

*   **Flask Web Server (`server.py`):** This is the main entry point for user interaction. It serves the web interface, receives user queries in natural language, and orchestrates the communication flow with the `Detection Agent`.
*   **Detection Agent (`agent/` directory):** This is the core of the intelligent configuration system.
    *   **`Detect_Agent` class:** Acts as the primary interface to the agent's functionalities. It initializes and manages the different parts of the agent.
    *   **`controller.py`:** Implements the central control loop. It utilizes a Large Language Model (LLM), referred to as the Controller, which iteratively guides the anomaly detection configuration process. The Controller makes decisions based on user input, dataset characteristics, and its internal knowledge.
    *   **`executor.py`:** This component receives natural language instructions (e.g., "analyze column X for outliers") from the Controller. It translates these instructions into executable Python code, primarily leveraging the `pandas` library for data analysis, and then runs this code.
    *   **Prompting System:** The behavior and knowledge of the LLM Controller are shaped by a structured prompting system:
        *   `agent_prompt.py`: Defines general rules, strategies, and constraints applicable to anomaly detection tasks. This provides the Controller with a foundational understanding of how to approach these problems.
        *   Dataset-specific prompts (e.g., `basic_prompt_Telecom.py`, `basic_prompt_Bank.py`): These files contain specialized information for different datasets. This includes data schemas (column names, types), lists of candidate root causes for anomalies common in that domain (e.g., network failures in Telecom, fraudulent transactions in Banking), and other contextual details that help the Controller generate more relevant and effective configurations.
*   **Langfuse Integration:** The system is integrated with Langfuse, a tracing and observability platform for LLM applications. This allows for detailed logging of the agent's execution, including every interaction with the LLM (prompts and responses), the Python code generated and executed by the `executor.py`, and the intermediate results. This is invaluable for debugging, understanding the agent's decision-making process, and evaluating its performance.
*   **Data Handling:** The agent is designed to process telemetry data, which can include metrics and traces. This data is expected to be in CSV format. Typically, datasets are organized by their specific domain (e.g., Telecom, Banking) and further subdivided by date.

## Project Structure

The project repository is organized as follows:

*   `agent/`: Contains the core logic for the detection agent. This includes the `Detect_Agent` class, the `controller.py` (LLM-driven control loop), `executor.py` (code generation and execution), and the various prompt files (`agent_prompt.py`, `basic_prompt_Telecom.py`, etc.).
*   `dataset/`: This directory is intended to store the datasets used for anomaly detection. It includes a `README.md` file that provides a link or instructions on how to download the necessary datasets.
*   `evaluate/`: This directory likely holds scripts and resources related to evaluating the performance of the anomaly detection agent. For instance, `evaluate/evaluate.py` probably contains code to run these evaluations.
*   `main/`: This directory appears to contain main scripts or utility functions. `main/evaluate.py` might be an alternative or supplementary script for running evaluations, while `main/generate.py` could be a utility for generating configurations or other artifacts (its exact purpose might require further inspection but is likely a helper script).
*   `server.py`: The Flask web server application that handles the user interface and orchestrates the agent's operations.
*   `templates/`: Contains HTML templates (e.g., `index.html`) used by the Flask web server to render the web interface.
*   `requirements.txt`: Lists all the Python dependencies required to run the project.
*   `README.md`: This document, providing an overview and guide to the project.

## Setup and Installation

Follow these steps to set up and install the Intelligent Anomaly Detection Configuration Agent:

*   **Prerequisites:**
    *   Python 3.x
    *   Access to a terminal or command line.
*   **1. Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/intelligent-anomaly-detection-agent.git # Replace with the actual URL
    # (Replace with the actual repository URL if different)
    cd intelligent-anomaly-detection-agent
    ```
*   **2. Install Dependencies:**
    The `requirements.txt` file lists all necessary Python dependencies. Install them using pip:
    ```bash
    pip install -r requirements.txt
    ```
*   **3. Obtain Datasets:**
    *   The datasets required for the agent are not included directly in this repository. Instructions for downloading them can be found in `dataset/README.md`. This typically involves a Google Drive link.
    *   Place the downloaded datasets into the `dataset/` directory, maintaining the specific subdirectory structure expected by the agent for each dataset (e.g., `dataset/Telecom/telemetry/` containing various CSV files like `metric_container.csv`, `metric_node.csv`, etc.).
*   **4. Langfuse Configuration (Optional):**
    *   The agent uses Langfuse for detailed tracing of LLM interactions and execution steps.
    *   Currently, Langfuse API keys and host information are embedded within `agent/run_detect_agent.py` and `agent/api_router.py`.
    *   For production deployments or if you are sharing the environment, it is highly recommended to externalize these sensitive details (e.g., by setting them as environment variables and modifying the code to read from them) instead of keeping them directly in the source code.

## How to Run

There are two main ways to run the agent:

*   **1. Running the Web Interface:**
    *   This is the recommended way for most users to interact with the agent.
    *   Start the Flask web server by running the following command from the root directory of the project:
        ```bash
        python server.py
        ```
    *   Once the server is running, open your web browser and navigate to `http://localhost:5079` (or `http://0.0.0.0:5079` if accessing from another machine on the network).
    *   You can then input your anomaly detection requirements in natural language through the web interface.
*   **2. Running via Command-Line (for single queries/advanced use):**
    *   For more direct execution, scripting, or advanced use cases, you can run the agent using the `agent/run_detect_agent.py` script.
    *   Here's an example command structure:
        ```bash
        python agent/run_detect_agent.py --query "Detect anomalies in the CPU utilization metric" --dataset "Telecom" --output_path "output_results/"
        ```
    *   **Key arguments:**
        *   `--query`: Your natural language query describing the anomaly detection task.
        *   `--dataset`: Specifies the target dataset. This should match one of the dataset names for which you have configured prompts and data (e.g., "Telecom", "Bank", "Market/cloudbed-1").
        *   `--output_path`: The directory where the agent will save its execution trajectory (e.g., `trajectory.ipynb`) and prompt logs (e.g., `prompt.json`). Ensure this path exists or the script has permissions to create it.

## Input/Output

*   **Input:**
    *   Primary input: A natural language query provided by the user (e.g., "对redis_009的指标配置异常检测方案" or "监控所有容器的CPU、内存使用，以及是否存活").
    *   Implicit input: The telemetry data for the specified dataset.
*   **Output:**
    *   **Primary Output (JSON):** A JSON object detailing the recommended anomaly detection configuration. This includes:
        *   Component/Metric identifier.
        *   Metric name and description.
        *   Metric type.
        *   The suggested anomaly detection scheme/algorithm.
        *   The reasoning behind the suggestion.
        (The exact structure is defined by the `summary` prompt format in `agent/detect_agent/controller.py`).
    *   **Trajectory Notebook:** A Jupyter notebook file (e.g., `trajectory.ipynb`) saved in the output directory. This notebook contains:
        *   The sequence of analysis steps taken by the agent.
        *   The Python code generated and executed by the Executor at each step.
        *   The results/observations from each code execution.
    *   **Prompt Log:** A JSON file (e.g., `prompt.json`) also saved in the output directory, logging the full interaction history with the LLM.
    *   **Langfuse Trace URL:** If Langfuse is configured, the `trace_id` (returned by the agent's execution functions and used by the server) can be used to construct a direct URL to view the execution trace in the Langfuse UI (e.g., `YOUR_LANGFUSE_HOST/trace/TRACE_ID`). The `trace_id` is also logged by `server.py` when a query is run.

## Extending the Agent

The agent's capabilities can be extended, primarily by adding knowledge about new datasets or by modifying its core behavior.

*   **1. Adding Support for New Datasets:**
    *   To enable the agent to work with a new dataset (e.g., "MyNewDataset"), you need to create a new Python prompt file in the `agent/detect_agent/prompt/` directory. For example, `basic_prompt_MyNewDataset.py`.
    *   This new prompt file must define at least two key string variables:
        *   `cand`: This string should list possible root cause analysis candidates and component names relevant to "MyNewDataset". This helps the agent understand what to look for and where.
        *   `schema`: This string must describe the telemetry data structure for "MyNewDataset". This includes details like the directory layout where the data is stored, CSV file naming conventions, column names within the CSVs, data types of these columns, any relevant timezones, etc.
    *   After creating the prompt file, you'll need to modify `agent/run_detect_agent.py` (for command-line usage) and `agent/api_router.py` (for the web interface) to recognize the new dataset name (e.g., "MyNewDataset") and import the corresponding `basic_prompt_MyNewDataset.py` file when that dataset is selected by the user.
*   **2. Modifying Agent Behavior/Knowledge:**
    *   The core knowledge base and operational guidelines for the LLM controller are defined in `agent/detect_agent/prompt/agent_prompt.py`.
    *   The `rules` variable within this file contains a set of instructions, heuristics, and constraints that the LLM uses to make decisions.
    *   Modifying these rules can significantly change how the agent approaches anomaly detection tasks, such as its preferred detection methods for certain types of data, how it interprets user queries, or its strategies for analyzing data.

## Evaluation

The project includes resources for evaluating the agent's performance:

*   The `evaluate/` directory contains scripts and instructions related to performance assessment.
*   `evaluate/evaluate.py`: This script is likely used for assessing the performance of the anomaly detection configurations generated by the agent. It might compare the agent's suggestions against a baseline or ground truth.
*   `evaluate/instruction.md`: This file probably contains detailed instructions or guidelines on how to set up and run the evaluation process, including any specific metrics or datasets to be used.
*   `main/evaluate.py`: This could be an alternative entry point for running evaluations or a helper script that supports the main evaluation process defined in `evaluate/evaluate.py`.
