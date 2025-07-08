import subprocess
import traceback
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/hooks/django-deploy', methods=['POST'])
def handle_webhook():
    if not request.is_json:
        return jsonify({"msg": "Request must be JSON"}), 400

    data = request.get_json()
    target_branch = 'refs/heads/main'
    
    print(f"Received request for ref: {data.get('ref')}")

    if data.get('ref') == target_branch:
        try:
            script_path = '/home/dkj/deploy_scripts/deploy.sh'
            payload_data_string = request.get_data(as_text=True)
            
            print(f"Target branch matched. Starting script in background: {script_path}")
            
            # --- 核心优化 ---
            # 使用 Popen 在后台启动脚本，不再等待它完成
            subprocess.Popen([script_path, payload_data_string])
            
            # 立即返回成功消息给 Gitea
            return jsonify({"msg": "Deployment script started successfully in background."}), 200

        except Exception as e:
            # 如果启动脚本本身就失败了，记录错误
            print("An unexpected error occurred while trying to start the script. See traceback below:")
            traceback.print_exc()
            return jsonify({"msg": "Failed to start deployment script."}), 500
    
    else:
        print("Branch did not match target. Nothing to do.")
        return jsonify({"msg": "Branch did not match target. Nothing to do."}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)