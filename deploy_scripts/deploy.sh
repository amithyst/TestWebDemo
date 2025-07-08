#!/bin/bash
set -e

# --- 日志记录设置 ---
LOG_FILE="/home/dkj/deploy_scripts/deployment.log"
# 将此脚本的所有标准输出和错误输出都重定向到日志文件，同时也显示在控制台
exec > >(tee -a "$LOG_FILE") 2>&1

echo "<<------------ 脚本开始执行 $(date) ------------>>"

# 接收从 webhook 传来的第一个参数（完整的 JSON Payload）
PAYLOAD=$1

# 检查 PAYLOAD 是否为空
if [ -z "$PAYLOAD" ]; then
  echo "Payload is empty. Exiting."
  exit 1
fi

# 使用 jq 工具从 Payload 中提取 ref 字段的值
# jq 的 -r 参数可以移除字符串的双引号
REF=$(echo "$PAYLOAD" | jq -r '.ref')

# 定义我们期望部署的目标分支
TARGET_BRANCH="refs/heads/main"

echo "Received push event for branch: $REF"

# 判断收到的分支是否为目标分支
if [ "$REF" == "$TARGET_BRANCH" ]; then
  echo "Branch matches target ($TARGET_BRANCH). Starting deployment..."

  # 定义变量
  PROJECT_DIR="/var/www/TestWebDemo"
  VENV_DIR="$PROJECT_DIR/venv"
  GUNICORN_SOCK="$PROJECT_DIR/gunicorn.sock"
  GUNICORN_SERVICE_FILE="/etc/systemd/system/gunicorn.service"
  NGINX_SITE_AVAILABLE="/etc/nginx/sites-available/testwebdemo.conf"
  NGINX_SITE_ENABLED="/etc/nginx/sites-enabled/testwebdemo.conf"
  NGINX_PROXY_PARAMS="/etc/nginx/proxy_params"
  VM_IP="192.168.71.100"
  DJANGO_PROJECT_NAME="mysite"

  echo "--- 1. Git 克隆或拉取项目 ---"
  # 确保 git 命令在 PATH 中
  if ! command -v git &> /dev/null; then
    echo "git command not found!"
    exit 1
  fi

  mkdir -p "$PROJECT_DIR"
  cd "$PROJECT_DIR" || { echo "无法进入项目目录，退出。"; exit 1; }

  if [ -d ".git" ]; then
      echo "项目已存在，执行 git pull..."
      git fetch origin main
      git reset --hard origin/main
  else
      echo "克隆项目..."
      git clone http://$VM_IP:3000/dkj/TestWebDemo.git .
  fi

  echo "--- 2. 设置 Python 虚拟环境和依赖 ---"
  if [ ! -d "$VENV_DIR" ]; then
      echo "创建虚拟环境..."
      virtualenv "$VENV_DIR"
  fi

  echo "激活虚拟环境并安装依赖..."
  source "$VENV_DIR/bin/activate"
  
  mkdir -p /root/.pip
  cat <<EOF > /root/.pip/pip.conf
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF

  pip install -r requirements.txt
  deactivate

  echo "--- 3. 配置 Django settings.py ---"
  echo "收集 Django 静态文件..."
  source "$VENV_DIR/bin/activate"
  python manage.py collectstatic --noinput
  deactivate

  echo "--- 4. 安装 Gunicorn 并创建 Systemd 服务 ---"
  source "$VENV_DIR/bin/activate"
  pip install gunicorn
  deactivate

  echo "创建 Gunicorn Systemd 服务文件..."
  bash -c "cat > $GUNICORN_SERVICE_FILE" <<EOF
[Unit]
Description=Gunicorn daemon for TestWebDemo
After=network.target
[Service]
User=root
Group=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/gunicorn \\
        --workers 3 \\
        --bind unix:$GUNICORN_SOCK \\
        $DJANGO_PROJECT_NAME.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
Restart=on-failure
PrivateTmp=true
[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl restart gunicorn
  systemctl enable gunicorn

  echo "--- 5. 安装 Nginx 并配置反向代理 ---"
  echo "创建 Nginx 代理参数文件..."
  bash -c "cat > $NGINX_PROXY_PARAMS" <<EOF
proxy_set_header Host \$http_host;
proxy_set_header X-Real-IP \$remote_addr;
proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto \$scheme;
EOF

  echo "创建 Nginx 站点配置文件..."
  mkdir -p /etc/nginx/sites-available
  bash -c "cat > $NGINX_SITE_AVAILABLE" <<EOF
server {
    listen 80;
    server_name $VM_IP;
    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
    }
    location / {
        include $NGINX_PROXY_PARAMS;
        proxy_pass http://unix:$GUNICORN_SOCK;
    }
}
EOF

  echo "创建 Nginx 站点配置软链接..."
  mkdir -p /etc/nginx/sites-enabled
  ln -sf "$NGINX_SITE_AVAILABLE" "$NGINX_SITE_ENABLED"

  if ! grep -q "include /etc/nginx/sites-enabled/\*.conf;" /etc/nginx/nginx.conf; then
      sed -i '/http {/a \    include /etc/nginx/sites-enabled/*.conf;' /etc/nginx/nginx.conf
  fi

  echo "重启 Nginx 服务..."
  systemctl restart nginx
  systemctl enable nginx
  
  echo "--- DEPLOYMENT COMPLETED AT $(date) ---"

else
  echo "Branch does not match target. Nothing to do."
fi

exit 0