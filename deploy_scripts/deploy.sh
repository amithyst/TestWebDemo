#!/bin/bash

# 定义变量
PROJECT_DIR="/var/www/TestWebDemo"
VENV_DIR="$PROJECT_DIR/venv"
GUNICORN_SOCK="$PROJECT_DIR/gunicorn.sock"
GUNICORN_SERVICE_FILE="/etc/systemd/system/gunicorn.service"
NGINX_SITE_AVAILABLE="/etc/nginx/sites-available/testwebdemo.conf"
NGINX_SITE_ENABLED="/etc/nginx/sites-enabled/testwebdemo.conf"
NGINX_PROXY_PARAMS="/etc/nginx/proxy_params"
VM_IP="192.168.71.100" # 替换为你的虚拟机IP地址
DJANGO_PROJECT_NAME="mysite" # 替换为你的Django项目名，例如如果settings.py在TestWebDemo/TestWebDemo/settings.py，则为TestWebDemo

# --- 1. Git 克隆或拉取项目 ---

if ! pacman -Qs git &> /dev/null; then
    sudo pacman -S --noconfirm git
fi

echo "--- 1. Git 克隆或拉取项目 ---"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR" || { echo "无法进入项目目录，退出。"; exit 1; }

if [ -d ".git" ]; then
    echo "项目已存在，执行 git pull..."
    git pull origin main
else
    echo "克隆项目..."
    # 假设你的Gitea仓库URL
    git clone http://$VM_IP:3000/dkj/TestWebDemo.git .
fi

# --- 2. 设置 Python 虚拟环境和依赖 ---
echo "--- 2. 设置 Python 虚拟环境和依赖 ---"
# 安装 virtualenv (如果尚未安装)
if ! pacman -Qs python-virtualenv &> /dev/null; then
    sudo pacman -S --noconfirm python-pip python-virtualenv
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    virtualenv "$VENV_DIR"
fi

echo "激活虚拟环境并安装依赖..."
source "$VENV_DIR/bin/activate"
# 设置pip镜像源
mkdir -p ~/.pip
cat <<EOF > ~/.pip/pip.conf
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF

pip install -r requirements.txt
deactivate

# --- 3. 配置 Django settings.py ---
echo "--- 3. 配置 Django settings.py ---"
# 这里假设你使用sed来修改ALLOWED_HOSTS，但这可能不够健壮
# 更好的做法是在settings.py中设置一个环境变量，然后脚本设置该环境变量
echo "请手动检查并修改 $PROJECT_DIR/$DJANGO_PROJECT_NAME/settings.py 中的 ALLOWED_HOSTS"
echo "例如：ALLOWED_HOSTS = ['$VM_IP', 'localhost', '127.0.0.1']"
# 示例：使用sed替换，但请谨慎使用，因为如果格式不完全匹配可能失效
# sed -i "s/ALLOWED_HOSTS = \[\]/ALLOWED_HOSTS = \['$VM_IP', 'localhost', '127.0.0.1'\]/" "$PROJECT_DIR/$DJANGO_PROJECT_NAME/settings.py"

# 收集静态文件
echo "收集 Django 静态文件..."
source "$VENV_DIR/bin/activate"
python manage.py collectstatic --noinput
deactivate

# --- 4. 安装 Gunicorn 并创建 Systemd 服务 ---
echo "--- 4. 安装 Gunicorn 并创建 Systemd 服务 ---"
source "$VENV_DIR/bin/activate"
pip install gunicorn
deactivate

echo "创建 Gunicorn Systemd 服务文件..."
sudo bash -c "cat <<EOF > $GUNICORN_SERVICE_FILE
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
EOF"

sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn

# --- 5. 安装 Nginx 并配置反向代理 ---
echo "--- 5. 安装 Nginx 并配置反向代理 ---"
if ! pacman -Qs nginx &> /dev/null; then
    sudo pacman -S --noconfirm nginx
fi

echo "创建 Nginx 代理参数文件..."
sudo bash -c "cat <<EOF > $NGINX_PROXY_PARAMS
proxy_set_header Host \$http_host;
proxy_set_header X-Real-IP \$remote_addr;
proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto \$scheme;
EOF"

echo "创建 Nginx 站点配置文件..."
sudo mkdir -p /etc/nginx/sites-available
sudo bash -c "cat <<EOF > $NGINX_SITE_AVAILABLE
server {
    listen 80;
    server_name $VM_IP;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        alias $PROJECT_DIR/staticfiles/; # 确保这里是你的 collectstatic 收集的目录
    }

    location / {
        include $NGINX_PROXY_PARAMS;
        proxy_pass http://unix:$GUNICORN_SOCK;
    }
}
EOF"

echo "创建 Nginx 站点配置软链接..."
sudo mkdir -p /etc/nginx/sites-enabled
sudo ln -sf "$NGINX_SITE_AVAILABLE" "$NGINX_SITE_ENABLED"

echo "检查并更新 Nginx 主配置文件..."
# 检查是否已包含，如果未包含则添加
if ! grep -q "include /etc/nginx/sites-enabled/\*.conf;" /etc/nginx/nginx.conf; then
    sudo sed -i '/http {/a \    include /etc/nginx/sites-enabled/*.conf;' /etc/nginx/nginx.conf
fi

sudo nginx -t
if [ $? -eq 0 ]; then
    echo "Nginx 配置语法检查通过，重启 Nginx 服务..."
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    sudo systemctl status nginx
else
    echo "Nginx 配置语法错误，请检查！"
    exit 1
fi

echo "部署完成！你可以尝试访问 http://$VM_IP"