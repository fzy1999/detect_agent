from flask import Flask, request, render_template, jsonify, Response
import os
import sys
import json
from datetime import datetime
import threading
import queue
import time

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# 导入检测代理函数
from agent.run_detect_agent import run_single_query

app = Flask(__name__)

# 存储日志的队列和结果
log_queue = queue.Queue()
result_dict = {"result": "", "trace_id": "", "plots": [], "obs_path": ""}

# 创建日志拦截器类
class LogInterceptor:
    def __init__(self, queue):
        self.queue = queue
        
    def write(self, message):
        if message.strip():  # 避免空消息
            self.queue.put(message)
        # 确保原始stdout也能接收到消息
        sys.__stdout__.write(message)
        
    def flush(self):
        sys.__stdout__.flush()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_query', methods=['POST'])
def run_query():
    query = request.form.get('query')
    dataset = 'Telecom'  # 固定使用Telecom数据集
    
    # 清空之前的日志队列和结果
    while not log_queue.empty():
        log_queue.get()
    result_dict["result"] = ""
    result_dict["trace_id"] = ""
    result_dict["plots"] = []
    result_dict["obs_path"] = ""
    
    # 创建输出目录
    output_path = os.path.join(project_root, "static", "output")
    os.makedirs(output_path, exist_ok=True)
    
    # 定义trace_id和obs_path变量
    # trace_id = "" # No longer needed here as it's set in run_task directly
    
    # 启动一个线程来执行查询
    def run_task():
        # 拦截标准输出并将其发送到队列
        old_stdout = sys.stdout
        sys.stdout = LogInterceptor(log_queue)
        
        try:
            # 运行查询
            # nonlocal trace_id, obs_path # No longer needed due to direct assignment to result_dict
            returned_trace_id, returned_obs_path = run_single_query(query, dataset, output_path)
            # 保存trace_id和obs_path
            result_dict["trace_id"] = returned_trace_id
            result_dict["obs_path"] = returned_obs_path
            
            # 获取结果（从prompt.json的最后一个响应中获取）
            # latest_output_dir = get_latest_output_dir(output_path) # obs_path is now the direct path
            if returned_obs_path:
                try:
                    with open(os.path.join(returned_obs_path, "prompt.json"), 'r', encoding='utf-8') as f:
                        prompt_data = json.load(f)
                        if prompt_data and 'messages' in prompt_data and len(prompt_data['messages']) > 0:
                            # 获取最后一个assistant的响应
                            for message in reversed(prompt_data['messages']):
                                if message['role'] == 'assistant':
                                    raw_result_content = message['content'].strip()
                                    # The raw_result_content is expected to be a JSON string
                                    try:
                                        final_answer_json = json.loads(raw_result_content)
                                        result_dict["result"] = json.dumps(final_answer_json, ensure_ascii=False, indent=4) # Store pretty printed JSON
                                        result_dict["plots"] = final_answer_json.get("generated_plots", [])
                                    except json.JSONDecodeError as je:
                                        # If it's not JSON, store as is, and log error for plots
                                        result_dict["result"] = raw_result_content
                                        result_dict["plots"] = []
                                        log_queue.put(f"Error parsing final result JSON for plots: {str(je)}")
                                    break
                except Exception as e:
                    result_dict["result"] = f"获取结果失败: {str(e)}"
                    log_queue.put(f"Error reading prompt.json or processing result: {str(e)}")
            else:
                result_dict["result"] = "执行完成，但未返回观测路径。"
                log_queue.put("Execution finished, but no observation path was returned.")

        except Exception as e:
            log_queue.put(f"Error: {str(e)}")
            result_dict["result"] = f"执行失败: {str(e)}"
        finally:
            # 恢复标准输出
            sys.stdout = old_stdout
    
    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()
    
    # Return initial status, trace_id will be updated by the thread and fetched by get_result
    return jsonify({"status": "started"})

def get_latest_output_dir(output_path):
    # 获取最新创建的输出目录
    try:
        model_dirs = [os.path.join(output_path, d) for d in os.listdir(output_path) if os.path.isdir(os.path.join(output_path, d))]
        if not model_dirs:
            return None
            
        latest_model_dir = max(model_dirs, key=os.path.getctime)
        time_dirs = [os.path.join(latest_model_dir, d) for d in os.listdir(latest_model_dir) if os.path.isdir(os.path.join(latest_model_dir, d))]
        if not time_dirs:
            return None
            
        return max(time_dirs, key=os.path.getctime)
    except Exception:
        return None

@app.route('/stream_logs')
def stream_logs():
    def generate():
        while True:
            if not log_queue.empty():
                log = log_queue.get()
                yield f"data: {json.dumps({'log': log})}\n\n"
            else:
                time.sleep(0.1)
               
    return Response(generate(), mimetype='text/event-stream')

@app.route('/get_result')
def get_result():
    return jsonify({
        "result": result_dict.get("result"), 
        "trace_id": result_dict.get("trace_id"),
        "plots": result_dict.get("plots", []),
        "obs_path": result_dict.get("obs_path")
    })

@app.route('/get_plots/<trace_id>')
def get_plots(trace_id):
    # Assuming result_dict holds the latest query's data and trace_id matches.
    # For a multi-user or historical scenario, you'd need a better way to store/retrieve this.
    if result_dict.get("trace_id") == trace_id:
        return jsonify({"plots": result_dict.get("plots", [])})
    return jsonify({"error": "Trace ID not found or no plots available"}), 404

from flask import send_from_directory

# ... (other app routes) ...

@app.route('/get_plot_file/<trace_id>/<path:plot_filename>')
def get_plot_file(trace_id, plot_filename):
    if result_dict.get("trace_id") == trace_id and result_dict.get("obs_path"):
        # obs_path is already absolute: project_root + "/static/output/model_name/timestamp"
        plot_dir = os.path.join(result_dict["obs_path"], "plot")
        # Security: Ensure plot_filename is just a filename and doesn't try to ../
        if ".." in plot_filename or plot_filename.startswith("/"):
            return "Invalid filename", 400
        try:
            # For send_from_directory, the directory path should be absolute.
            # project_root is absolute. obs_path is derived from project_root. So it should be absolute.
            return send_from_directory(plot_dir, plot_filename)
        except FileNotFoundError:
            return "Plot not found", 404
    return jsonify({"error": "Trace ID not found or obs_path missing"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5080, debug=True, threaded=True)
