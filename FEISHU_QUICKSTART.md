# 飞书版 Gateway 快速启动指南

本指南帮助您快速配置和运行飞书版 WeChat-HA-Gateway。

## 前置准备

您需要准备：
1. ✅ 飞书应用的 **App ID**
2. ✅ 飞书应用的 **App Secret**  
3. ✅ 飞书应用的 **Verification Token**

如果还没有这些信息，请按以下步骤获取：

### 获取飞书应用凭证

1. 访问 [飞书开放平台](https://open.feishu.cn)
2. 登录并选择您的团队
3. 进入"开发者后台" → 选择您的应用
4. **App ID & App Secret**:
   - 点击"凭证与基础信息"
   - 复制 `App ID` 和 `App Secret`
5. **Verification Token**:
   - 点击"事件订阅" → "加密策略"
   - 生成或查看 `Verification Token`

## 第一步：配置环境变量

### 1.1 复制配置模板

```bash
cp .env.example .env
```

### 1.2 编辑配置文件

打开 `.env` 文件，填入您的配置：

```bash
# 通道类型（固定为 feishu）
CHANNEL_TYPE=feishu

# Gateway 服务器配置
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8099

# 可选：API 访问令牌（增强安全性）
GATEWAY_TOKEN=

# 飞书应用凭证（必填）
FEISHU_APP_ID=cli_你的AppID
FEISHU_APP_SECRET=你的AppSecret
FEISHU_VERIFICATION_TOKEN=你的VerificationToken
```

**示例配置：**
```bash
CHANNEL_TYPE=feishu
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8099
GATEWAY_TOKEN=my_secure_token_123

FEISHU_APP_ID=cli_a1b2c3d4e5f6g7h8
FEISHU_APP_SECRET=ABC123xyz789SecretKeyHere
FEISHU_VERIFICATION_TOKEN=v1_my_token_xyz789
```

## 第二步：安装依赖

### Windows:

```powershell
# 安装依赖
pip install -r requirements.txt
```

### Linux/Mac:

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 第三步：本地测试（推荐）

在配置飞书 Webhook 前，先本地测试。

### 3.1 启动 Gateway

```bash
python app.py
```

**预期输出：**
```
[2025-11-07 18:00:00] INFO - __main__: Gateway using channel: feishu
[2025-11-07 18:00:00] INFO - gateway.feishu_client: [Feishu] Client initialized with app_id: cli_a1b2c3...
[2025-11-07 18:00:00] INFO - gateway.manager: Gateway manager started with channel: feishu
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8099 (Press CTRL+C to quit)
```

### 3.2 测试健康检查

打开另一个终端：

```bash
curl http://localhost:8099/health
```

应该返回：
```json
{"status":"ok"}
```

### 3.3 使用内网穿透（必需）

飞书需要公网可访问的 Webhook URL。本地测试可使用内网穿透工具。

**推荐使用 ngrok：**

1. 下载 ngrok: https://ngrok.com/download
2. 启动内网穿透：
   ```bash
   ngrok http 8099
   ```
3. 复制 Forwarding URL（例如：`https://a1b2-c3d4-e5f6.ngrok-free.app`）

## 第四步：配置飞书事件订阅

### 4.1 配置 Webhook URL

1. 访问 [飞书开放平台](https://open.feishu.cn)
2. 进入您的应用 → "事件订阅"
3. 选择"将事件发送至 开发者服务器"
4. 填写请求地址：
   ```
   https://your-ngrok-url.ngrok-free.app/feishu/webhook
   ```
   或（部署到 AWS 后）：
   ```
   http://your-aws-ip:8099/feishu/webhook
   ```
5. 填写 Verification Token（与 .env 中的一致）
6. 点击"保存"

**Gateway 日志应该显示：**
```
[2025-11-07 18:05:00] INFO - [Feishu] URL verification request received
[2025-11-07 18:05:00] INFO - [Feishu] URL verification successful
```

### 4.2 添加订阅事件

在"事件订阅"页面：
1. 点击"添加事件"
2. 搜索"接收消息"
3. 勾选 **"接收消息 v2.0"** (`im.message.receive_v1`)
4. 点击"确定"

### 4.3 发布应用版本

**重要：** 配置完成后必须发布应用！

1. 返回应用首页
2. 点击"版本管理与发布"
3. 点击"创建版本" → 填写说明 → "保存"
4. 点击"申请发布"
5. 进入"管理后台"审核并通过
6. 应用状态变为"已启用"

## 第五步：测试消息功能

### 5.1 测试接收消息

1. 在飞书中搜索您的机器人名称
2. 发送消息："你好"
3. 查看 Gateway 日志：

**应该看到：**
```
[2025-11-07 18:10:00] INFO - gateway.feishu_client: [Feishu] Received message from ou_xxxxx: 你好
[2025-11-07 18:10:00] DEBUG - gateway.manager: Incoming message event: IncomingMessageEvent(...)
```

### 5.2 测试发送消息

```bash
# 获取用户 open_id
# 方法：在飞书中给机器人发消息，从日志中复制 "sender" 字段的值

curl -X POST http://localhost:8099/send_message \
  -H "Content-Type: application/json" \
  -d '{
    "target": "ou_xxxxx你的open_id",
    "content": "测试回复消息"
  }'
```

应该收到回复消息！

### 5.3 测试群聊功能

1. 创建飞书群聊
2. 添加您的机器人到群聊
3. 在群聊中@机器人："测试群聊"
4. 查看日志确认收到

**获取群聊 chat_id:**
从日志中的 "room_id" 字段复制

**发送群聊消息：**
```bash
curl -X POST http://localhost:8099/send_message \
  -H "Content-Type: application/json" \
  -d '{
    "target": "oc_xxxxx群聊chat_id",
    "content": "群聊测试消息"
  }'
```

## 第六步：配置 Home Assistant 集成

您现有的 HA 集成应该无需修改即可工作，只需更新连接配置：

### 6.1 更新 HA 集成配置

在 Home Assistant 的配置中：
- **Base URL**: `http://your-gateway-address:8099`
- **Access Token**: 如果设置了 `GATEWAY_TOKEN`，填入相同值

### 6.2 测试 HA 集成

1. 重启 Home Assistant
2. 检查集成状态是否正常
3. 查看 Sensor 是否显示最新消息
4. 测试 Notify 服务

## 常见问题

### Q1: 飞书 URL 验证失败

**检查：**
1. Gateway 是否正在运行？
2. Verification Token 是否正确？
3. URL 是否可以从公网访问？

**测试：**
```bash
curl -X POST http://localhost:8099/feishu/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test123","token":"your_token"}'
```

应该返回：`{"challenge":"test123"}`

### Q2: 收不到消息

**检查清单：**
- [ ] 应用版本已发布且审核通过
- [ ] 事件"接收消息 v2.0"已添加
- [ ] 权限包含 `im:message`（在"权限管理"中）
- [ ] 群聊中已@机器人
- [ ] Gateway 日志无错误

### Q3: 发送消息失败

**常见原因：**
1. `target` 不正确（open_id 或 chat_id）
2. Access Token 过期（会自动刷新）
3. 权限不足

**查看详细错误：**
查看 Gateway 日志中的错误信息

## 生产部署

本地测试成功后，部署到 AWS：

**详细步骤请参考：** [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)

**快速步骤：**
1. 上传代码到 EC2
2. 安装依赖
3. 配置 .env
4. 使用 systemd 运行服务
5. 配置安全组开放端口
6. 更新飞书 Webhook URL

## 下一步

- ✅ 配置完成，开始使用！
- 📊 监控 Gateway 日志
- 🔐 启用 HTTPS（生产环境）
- 🏠 配置 Home Assistant 自动化
- 📱 邀请家人加入飞书团队

## 获取帮助

- 查看 Gateway 日志：检查错误信息
- 查看飞书开放平台文档：https://open.feishu.cn/document
- 检查网络连接：确保端口开放
- 验证配置：确认所有凭证正确

---

**🎉 恭喜！** 您的飞书 Gateway 已经配置完成！

现在您可以通过飞书控制 Home Assistant 了！
