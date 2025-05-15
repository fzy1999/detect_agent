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
from rca.run_detect_agent import run_single_query

app = Flask(__name__)

# 存储日志的队列和结果
log_queue = queue.Queue()
result_dict = {"result": ""}

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
    dataset = request.form.get('dataset', 'Telecom')  # 默认为Telecom
    
    # 清空之前的日志队列和结果
    while not log_queue.empty():
        log_queue.get()
    result_dict["result"] = ""
    
    # 创建输出目录
    output_path = os.path.join(project_root, "static", "output")
    os.makedirs(output_path, exist_ok=True)
    
    # 启动一个线程来执行查询
    def run_task():
        # 拦截标准输出并将其发送到队列
        old_stdout = sys.stdout
        sys.stdout = LogInterceptor(log_queue)
        
        try:
            # 运行查询
            run_single_query(query, dataset, output_path)
            
            # 获取结果（假设结果在trajectory.ipynb中的最后一个单元格）
            latest_output_dir = get_latest_output_dir(output_path)
            if latest_output_dir:
                try:
                    with open(os.path.join(latest_output_dir, "trajectory.ipynb"), 'r', encoding='utf-8') as f:
                        notebook = json.load(f)
                        if notebook and 'cells' in notebook and len(notebook['cells']) > 0:
                            # 获取最后一个Markdown单元格的内容
                            for cell in reversed(notebook['cells']):
                                if cell['cell_type'] == 'markdown':
                                    result = cell['source'].replace('```', '').strip()
                                    result_dict["result"] = result
                                    break
                except Exception as e:
                    result_dict["result"] = f"获取结果失败: {str(e)}"
        except Exception as e:
            log_queue.put(f"Error: {str(e)}")
            result_dict["result"] = f"执行失败: {str(e)}"
        finally:
            # 恢复标准输出
            sys.stdout = old_stdout
    
    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()
    
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
    return jsonify({"result": result_dict["result"]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
