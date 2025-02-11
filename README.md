# WeChat Backend Service

这是一个基于 Flask 的微信公众号后端服务，用于处理微信公众号的消息收发。目前已实现基础的消息接收和回复功能，后续计划接入智能体实现更多高级功能。

## 功能特性

### 已实现
- [x] 微信服务器验证（支持 GET 请求验证）
- [x] 消息加解密（支持安全模式，AES-CBC-256）
- [x] 基本的消息接收和回复
- [x] 完整的日志系统（支持文件和控制台输出）
- [x] Docker 容器化部署
- [x] access_token 的获取和管理

### TODO
- [ ] 消息推送功能
- [ ] 智能体接入
- [ ] 更多类型的消息处理（图片、语音等）
- [ ] 自定义菜单
- [ ] 用户管理

## 快速开始

1. 配置环境变量
创建 `.env` 文件并设置以下配置：

```env
# WeChat配置
WECHAT_TOKEN=your_token
WECHAT_AES_KEY=your_encoding_aes_key
WECHAT_APPID=your_appid
WECHAT_APPSECRET=your_appsecret

# 日志配置
LOG_LEVEL=INFO
LOG_FILE_SIZE=50M
LOG_BACKUP_COUNT=5
```

2. 使用 Docker Compose 启动服务
```bash
docker-compose up -d
# 或
docker-up.sh -d
```

3. 服务将在 5080 端口启动，可通过 `http://your_domain:5080/wechat` 访问

4. 通过[微信公众平台接口调试工具](https://mp.weixin.qq.com/debug/)测试

## 项目结构

```
wx-backend/
├── app/
│ ├── init.py
│ ├── config.py
│ ├── routes.py
│ ├── wechat/
│ │ ├── crypto.py # 消息加解密
│ │ └── handler.py # 消息处理
│ └── utils/
│ └── logger.py # 日志工具
├── logs/ # 日志目录
├── .env # 环境变量
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── run.py
```


## 配置说明

### 微信公众号配置
- `WECHAT_TOKEN`: 用于验证消息真实性
- `WECHAT_AES_KEY`: 消息加解密密钥
- `WECHAT_APPID`: 公众号的 AppID
- `WECHAT_APPSECRET`: 公众号的 AppSecret
- `EXTERNAL_SERVICE_TYPE`: 外部服务类型（default/openai/ollama/custom）

### 日志配置
- `LOG_LEVEL`: 日志级别（DEBUG/INFO/WARNING/ERROR）
- `LOG_FILE_SIZE`: 单个日志文件大小限制
- `LOG_BACKUP_COUNT`: 日志文件备份数量

## 开发计划

1. 第一阶段（已完成）
   - 基础消息收发功能
   - 安全模式下的消息加解密
   - 日志系统
   - Docker 部署

2. 第二阶段（进行中）
   - access_token 管理
   - 消息推送功能
   - 更多类型消息支持

3. 第三阶段（计划中）
   - 智能体接入
   - 自定义菜单
   - 用户管理

## 注意事项

1. 安全性
   - 所有配置信息都通过环境变量注入
   - 支持安全模式下的消息加解密
   - 日志系统避免敏感信息泄露

2. 部署
   - 推荐使用 Docker Compose 部署
   - 需要配置 URL（微信服务器要求）
   - 建议使用反向代理（如 Nginx）

## 贡献指南

欢迎提交 Issue 和 Pull Request。在提交代码前，请确保：
1. 代码风格符合 PEP 8 规范
2. 添加必要的注释和文档
3. 更新 README 中的功能列表

## License

MIT License