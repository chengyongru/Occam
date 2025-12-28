# Feishu Bot Backend

飞书机器人后端服务，使用官方SDK实现长连接客户端。

## 配置步骤

### 1. 安装依赖

使用uv安装项目依赖：

```bash
cd backend
uv sync
```

### 2. 配置应用凭证

在飞书开放平台创建应用后，获取 `App ID` 和 `App Secret`。

设置环境变量：

```bash
export FEISHU_APP_ID='your_app_id'
export FEISHU_APP_SECRET='your_app_secret'
```

或者创建 `.env` 文件（需要安装 `python-dotenv`）：

```
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
```

### 3. 在飞书开放平台配置事件订阅

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 进入您的应用（App ID: `cli_a9da4baa1fa2dbc9`）
3. 进入「事件订阅」页面
4. 选择「使用长连接接收事件」
5. 订阅需要的事件类型，例如：
   - `im.message.receive_v1` - 接收消息事件
   - `application.bot.menu_v6` - 机器人菜单事件
   - `im.message.card.action` - 卡片交互事件

### 4. 运行机器人

```bash
uv run python main.py
```

或者直接运行：

```bash
uv run python feishu_bot.py
```

## 代码结构

- `feishu_bot.py` - 飞书机器人主程序，包含长连接客户端实现
- `main.py` - 程序入口
- `pyproject.toml` - 项目配置和依赖

## 功能说明

- 使用飞书官方SDK建立WebSocket长连接
- 自动接收和处理飞书事件
- 支持消息接收、菜单事件、卡片交互等事件类型
- 可扩展的消息处理和回复功能

## 开发说明

在 `feishu_bot.py` 中的 `_handle_message` 方法中添加您的消息处理逻辑。

如果需要回复消息，可以使用 `reply_message` 方法。

