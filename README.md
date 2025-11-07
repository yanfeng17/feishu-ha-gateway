# Feishu Home Assistant Gateway

高性能飞书（Feishu/Lark）消息网关，用于连接飞书和 Home Assistant。

## ✨ 特性

- ✅ **实时消息接收** - 飞书 Webhook 推送
- ✅ **消息发送** - 支持文本和图片（规划中）
- ✅ **WebSocket 推送** - 实时推送到 Home Assistant
- ✅ **REST API** - 完整的 HTTP API
- ✅ **高性能** - 优化的异步架构，端到端延迟 < 150ms
- ✅ **易部署** - 支持本地运行和云端部署

## 📋 版本

**当前版本：v0.2.1**

### 性能优化
- 移除不必要的线程池执行器（减少 50-100ms）
- 异步并行发布机制（提升 3-4倍并发能力）
- 优化消息处理链路（总延迟降低 60-75%）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入飞书应用凭证
```

### 3. 启动服务

```bash
python app.py
```

服务将运行在 `http://0.0.0.0:8099`

## 📖 文档

- [快速启动指南](./FEISHU_QUICKSTART.md)
- [AWS 部署指南](./AWS_DEPLOYMENT.md)
- [性能优化说明](./PERFORMANCE.md)
- [更新日志](./CHANGELOG.md)

## 🔌 API 端点

### 健康检查
```
GET /health
```

### 发送消息
```
POST /send_message
{
  "target": "ou_xxxxx",
  "content": "Hello"
}
```

### 飞书 Webhook
```
POST /feishu/webhook
```

### WebSocket 连接
```
WS /ws
```

## 🏗️ 架构

```
飞书 ←→ Gateway (FastAPI) ←→ Home Assistant
         │
         ├─ WebSocket 推送
         ├─ REST API
         └─ Webhook 接收
```

## 📊 性能指标

- **延迟**: 30-80ms（Gateway 内部处理）
- **吞吐**: 20+ msg/s
- **并发**: 支持多订阅者并行推送
- **资源**: CPU < 5%, 内存 < 100MB

## 🔧 配置

所有配置通过环境变量设置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CHANNEL_TYPE` | 通道类型 | `feishu` |
| `GATEWAY_HOST` | 监听地址 | `0.0.0.0` |
| `GATEWAY_PORT` | 监听端口 | `8099` |
| `GATEWAY_TOKEN` | API 访问令牌（可选） | - |
| `FEISHU_APP_ID` | 飞书应用 ID | **必填** |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | **必填** |
| `FEISHU_VERIFICATION_TOKEN` | 飞书验证令牌 | **必填** |

## 🌐 部署

### 本地运行

适合开发和测试，配合 ngrok 使用。

### AWS EC2

完整的生产环境部署方案，参考 [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)

### Docker（规划中）

```bash
docker run -d -p 8099:8099 \
  -e FEISHU_APP_ID=xxx \
  -e FEISHU_APP_SECRET=xxx \
  feishu-ha-gateway
```

## 🤝 配套项目

- [feishu-ha-integration](https://github.com/yanfeng17/feishu-ha-integration) - Home Assistant 自定义集成

## 📝 许可证

MIT License

## 🙏 致谢

基于 Home Assistant 生态构建，感谢开源社区。

---

**享受您的智能家居飞书集成！** 🏠📱
