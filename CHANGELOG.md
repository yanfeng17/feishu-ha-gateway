# 更新日志

## v0.2.0 - 2025-11-07 - 飞书支持

### 新增功能

#### 1. 飞书通道支持 🎉
- 新增飞书客户端实现 (`gateway/feishu_client.py`)
- 支持飞书消息接收（文本消息）
- 支持飞书消息发送（文本和图片）
- 支持群聊和私聊
- 支持 @提醒功能
- 自动 access_token 管理和刷新

#### 2. 多通道架构
- 重构 `GatewayManager` 支持多通道切换
- 通过 `CHANNEL_TYPE` 环境变量选择通道（`wechat` 或 `feishu`）
- 保持与现有 WeChat 通道的完全兼容

#### 3. 新增 API 端点
- `POST /feishu/webhook` - 飞书事件订阅回调端点
- `POST /send_image` - 发送图片消息（飞书专用）

#### 4. 配置系统增强
- 新增飞书相关配置项
- 支持通过环境变量配置所有参数
- 提供 `.env.example` 配置模板

#### 5. 文档
- `FEISHU_QUICKSTART.md` - 飞书快速启动指南
- `AWS_DEPLOYMENT.md` - AWS 云服务器部署完整指南
- `CHANGELOG.md` - 更新日志

### 文件改动

#### 新增文件
- `gateway/feishu_client.py` - 飞书客户端实现
- `.env.example` - 环境变量配置模板
- `AWS_DEPLOYMENT.md` - AWS 部署文档
- `FEISHU_QUICKSTART.md` - 快速启动指南
- `CHANGELOG.md` - 本文件

#### 修改文件
- `gateway/config.py`
  - 新增 `channel_type` 配置
  - 新增飞书相关配置项（app_id, app_secret, verification_token）
  
- `gateway/manager.py`
  - 重构为支持多通道架构
  - 新增 `_start_feishu()` 和 `_start_wechat()` 方法
  - 新增 `send_image()` 方法
  - 新增 `handle_feishu_webhook()` 方法
  
- `app.py`
  - 更新标题和版本号
  - 新增 `SendImageSchema` 数据模型
  - 新增 `/send_image` 端点
  - 新增 `/feishu/webhook` 端点
  
- `requirements.txt`
  - 新增 `aiohttp==3.9.1`
  - 新增 `requests>=2.28.0`

### 技术亮点

1. **异步架构**
   - 飞书客户端完全异步实现
   - 使用 `aiohttp` 进行 HTTP 请求
   - 非阻塞的消息处理

2. **统一消息格式**
   - WeChat 和 Feishu 消息转换为统一的 `IncomingMessageEvent`
   - 确保 Home Assistant 集成无需修改

3. **云部署优化**
   - 环境变量配置
   - Systemd 服务配置
   - Nginx 反向代理支持
   - HTTPS/SSL 配置指南

4. **安全性**
   - Token 验证（飞书 Verification Token）
   - 可选的 Gateway API 访问令牌
   - 自动 access_token 刷新机制

### 升级指南

#### 从 v0.1.0 升级

1. **备份现有配置**
   ```bash
   # 如果有自定义配置，请备份
   ```

2. **更新代码**
   ```bash
   git pull
   ```

3. **安装新依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **创建配置文件**（如果使用飞书）
   ```bash
   cp .env.example .env
   # 编辑 .env 填入飞书配置
   ```

5. **重启服务**
   ```bash
   # 如果使用 systemd
   sudo systemctl restart feishu-gateway
   
   # 或直接运行
   python app.py
   ```

### 兼容性

- ✅ 向后兼容：现有 WeChat 通道功能完全保留
- ✅ Home Assistant 集成无需修改
- ✅ 现有 API 端点保持不变
- ✅ WebSocket 连接保持兼容

### 已知问题

1. **WeChat 版本限制**
   - WeChat 通道仍需要微信 3.9.5-3.9.8 旧版本
   - 新版微信不支持 wcferry

2. **飞书功能限制**
   - 暂不支持语音消息
   - 暂不支持文件发送（除图片外）
   - 用户名显示为 open_id（后续可增强）

### 性能

- ✅ 轻量级：运行内存 < 100MB
- ✅ 高性能：异步处理，支持并发
- ✅ 稳定性：自动重连和错误恢复

### 测试环境

- Python: 3.11+
- 操作系统: Windows 11, Ubuntu 22.04 LTS
- 飞书版本: 最新版
- Home Assistant: 2023.x+

---

## v0.1.0 - 初始版本

### 功能
- WeChat 通道实现（基于 wcferry）
- FastAPI REST API
- WebSocket 实时推送
- Home Assistant 集成

---

**完整文档：**
- [快速启动指南](./FEISHU_QUICKSTART.md)
- [AWS 部署指南](./AWS_DEPLOYMENT.md)
- [README](./README.md)
