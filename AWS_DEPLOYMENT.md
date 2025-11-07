# AWS 部署指南

本指南详细说明如何将 WeChat/Feishu HA Gateway 部署到 Amazon AWS 云服务器。

## 前提条件

- AWS 账号
- 已创建的 EC2 实例（推荐 Ubuntu 22.04 LTS）
- 飞书开放平台应用（App ID、App Secret、Verification Token）
- SSH 密钥对用于连接 EC2

## 第一步：准备 EC2 实例

### 1.1 创建 EC2 实例

推荐配置：
- **实例类型**: t2.micro 或 t3.micro（免费套餐可用）
- **操作系统**: Ubuntu Server 22.04 LTS
- **存储**: 8GB（默认）
- **安全组**: 需要开放以下端口
  - SSH: 22（用于管理）
  - Custom TCP: 8099（Gateway 端口）
  - HTTPS: 443（可选，如果使用 HTTPS）

### 1.2 配置安全组

在 AWS Console → EC2 → Security Groups 中添加入站规则：

```
Type            Protocol    Port Range    Source
SSH             TCP         22            My IP (或 0.0.0.0/0)
Custom TCP      TCP         8099          0.0.0.0/0
HTTPS           TCP         443           0.0.0.0/0 (可选)
```

### 1.3 分配弹性 IP（推荐）

为了保持固定的公网 IP 地址：
1. 进入 AWS Console → EC2 → Elastic IPs
2. 点击"Allocate Elastic IP address"
3. 将弹性 IP 关联到您的 EC2 实例

## 第二步：连接到 EC2 实例

### 方法 1: 使用 SSH（从 Windows）

```powershell
# 使用 PowerShell
ssh -i "your-key.pem" ubuntu@your-ec2-public-ip
```

### 方法 2: 使用 EC2 Instance Connect（浏览器）

在 AWS Console 中选择实例，点击"Connect" → "EC2 Instance Connect"

## 第三步：安装依赖

### 3.1 更新系统

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 安装 Python 3.11+

```bash
# Ubuntu 22.04 默认是 Python 3.10，升级到 3.11
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# 设置默认 Python 版本
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### 3.3 安装 pip 和虚拟环境

```bash
sudo apt install python3-pip python3-venv -y
```

### 3.4 安装 Git

```bash
sudo apt install git -y
```

## 第四步：部署应用

### 4.1 克隆代码

```bash
cd /home/ubuntu
git clone <your-repo-url> wechat-ha-gateway
cd wechat-ha-gateway
```

**或者**，如果从本地上传：

```powershell
# 在本地 Windows 上执行
scp -i "your-key.pem" -r "C:\AI Coding\weixin\wechat-ha-gateway" ubuntu@your-ec2-public-ip:/home/ubuntu/
```

### 4.2 创建虚拟环境

```bash
cd /home/ubuntu/wechat-ha-gateway
python3 -m venv venv
source venv/bin/activate
```

### 4.3 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.4 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

填入您的配置：

```bash
CHANNEL_TYPE=feishu
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8099
GATEWAY_TOKEN=your_secure_token_here

FEISHU_APP_ID=cli_xxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=your_verification_token_here
```

保存并退出（Ctrl+X, Y, Enter）

## 第五步：配置飞书 Webhook URL

### 5.1 获取 EC2 公网 IP

```bash
curl http://checkip.amazonaws.com
```

或在 AWS Console → EC2 → Instances 查看 Public IPv4 address

### 5.2 配置飞书开放平台

访问 https://open.feishu.cn

1. 进入您的应用
2. 点击"事件订阅"
3. 填写请求地址：
   ```
   http://your-ec2-public-ip:8099/feishu/webhook
   ```
4. 填写 Verification Token（与 .env 中的一致）
5. 添加事件："接收消息 v2.0"（im.message.receive_v1）
6. **保存前确保 Gateway 已启动！**

## 第六步：使用 Systemd 运行服务

### 6.1 创建 systemd 服务文件

```bash
sudo nano /etc/systemd/system/feishu-gateway.service
```

粘贴以下内容：

```ini
[Unit]
Description=Feishu HA Gateway Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/wechat-ha-gateway
Environment="PATH=/home/ubuntu/wechat-ha-gateway/venv/bin"
EnvironmentFile=/home/ubuntu/wechat-ha-gateway/.env
ExecStart=/home/ubuntu/wechat-ha-gateway/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

保存并退出（Ctrl+X, Y, Enter）

### 6.2 启动服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start feishu-gateway

# 查看状态
sudo systemctl status feishu-gateway

# 设置开机自启
sudo systemctl enable feishu-gateway
```

### 6.3 查看日志

```bash
# 实时查看日志
sudo journalctl -u feishu-gateway -f

# 查看最近 100 行日志
sudo journalctl -u feishu-gateway -n 100
```

## 第七步：配置飞书事件订阅

### 7.1 验证服务运行

```bash
# 检查健康状态
curl http://localhost:8099/health

# 应该返回: {"status":"ok"}
```

### 7.2 在飞书开放平台保存配置

现在可以点击"保存"按钮，飞书会发送 URL 验证请求。

查看日志确认：
```bash
sudo journalctl -u feishu-gateway -f
```

应该看到：
```
[2025-11-07 18:00:00] INFO - [Feishu] URL verification request received
[2025-11-07 18:00:00] INFO - [Feishu] URL verification successful
```

### 7.3 发布应用版本

1. 在飞书开放平台创建版本
2. 提交审核
3. 自己审核通过（您是管理员）
4. 应用状态变为"已启用"

## 第八步：测试

### 8.1 测试消息接收

1. 在飞书中搜索您的机器人
2. 发送消息："你好"
3. 查看 Gateway 日志：
   ```bash
   sudo journalctl -u feishu-gateway -f
   ```

应该看到：
```
[2025-11-07 18:10:00] INFO - [Feishu] Received message from ou_xxxxx: 你好
```

### 8.2 测试消息发送

```bash
# 从服务器测试
curl -X POST http://localhost:8099/send_message \
  -H "Content-Type: application/json" \
  -d '{
    "target": "ou_xxxxx",
    "content": "测试消息"
  }'
```

### 8.3 测试图片发送

```bash
curl -X POST http://localhost:8099/send_image \
  -H "Content-Type: application/json" \
  -d '{
    "target": "ou_xxxxx",
    "image_url": "https://example.com/image.jpg"
  }'
```

## 第九步：配置 HTTPS（可选但推荐）

### 9.1 安装 Nginx

```bash
sudo apt install nginx -y
```

### 9.2 配置 Nginx 反向代理

```bash
sudo nano /etc/nginx/sites-available/feishu-gateway
```

粘贴以下内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 或使用 IP

    location / {
        proxy_pass http://127.0.0.1:8099;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8099/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/feishu-gateway /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 9.3 配置 SSL（使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取 SSL 证书
sudo certbot --nginx -d your-domain.com

# 自动续期已配置，可以测试：
sudo certbot renew --dry-run
```

现在飞书 Webhook URL 改为：
```
https://your-domain.com/feishu/webhook
```

## 第十步：监控和维护

### 10.1 查看服务状态

```bash
sudo systemctl status feishu-gateway
```

### 10.2 重启服务

```bash
sudo systemctl restart feishu-gateway
```

### 10.3 更新代码

```bash
cd /home/ubuntu/wechat-ha-gateway
git pull  # 或重新上传文件
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart feishu-gateway
```

### 10.4 查看资源使用

```bash
# 查看 CPU 和内存使用
htop

# 如果没有安装 htop
sudo apt install htop -y
```

## 故障排查

### 问题 1: 无法连接到服务器

**检查：**
```bash
# 1. 检查服务是否运行
sudo systemctl status feishu-gateway

# 2. 检查端口是否监听
sudo netstat -tulpn | grep 8099

# 3. 检查防火墙
sudo ufw status
```

### 问题 2: 飞书 URL 验证失败

**检查：**
```bash
# 1. 查看日志
sudo journalctl -u feishu-gateway -n 50

# 2. 手动测试端点
curl -X POST http://localhost:8099/feishu/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test"}'

# 应该返回: {"challenge":"test"}
```

### 问题 3: 收不到消息

**检查：**
1. 应用版本是否已发布且审核通过
2. 事件"接收消息 v2.0"是否已添加
3. 权限是否正确配置（im:message）
4. 在群聊中是否@了机器人

## 成本估算

### AWS EC2 成本

- **t2.micro**: $0.0116/小时 ≈ $8.5/月（免费套餐前 12 个月免费）
- **t3.micro**: $0.0104/小时 ≈ $7.6/月
- **弹性 IP**: 关联到运行实例时免费
- **流量**: 1GB 出站/月免费，之后 $0.09/GB

**预计月成本**: $8-10/月（超出免费套餐后）

## 安全建议

1. **使用强密码**: 为 GATEWAY_TOKEN 设置复杂密码
2. **限制 SSH 访问**: 安全组仅允许特定 IP 访问 SSH
3. **定期更新**: 定期更新系统和依赖包
4. **启用 HTTPS**: 生产环境必须使用 HTTPS
5. **备份**: 定期备份 .env 配置文件

## 下一步

- 配置 Home Assistant 集成连接到 AWS Gateway
- 设置监控告警（CloudWatch）
- 配置自动备份
- 考虑使用 AWS Lambda + API Gateway 部署（无服务器）

---

**完成！** 您的飞书 HA Gateway 现在已经部署在 AWS 上并运行。
