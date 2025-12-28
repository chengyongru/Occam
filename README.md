# Feishu Bot Backend

飞书机器人后端服务，使用官方SDK实现长连接客户端。

## 配置步骤

### 1. 安装依赖

使用uv安装项目依赖：

```bash
cd backend
uv sync
```

### 2. 安装 Playwright 浏览器驱动和系统依赖

首次使用需要安装 Playwright 浏览器驱动和系统依赖：

```bash
# 安装浏览器驱动
uv run playwright install

# 安装系统依赖（需要 sudo 权限）
# Ubuntu/Debian 系统：
uv run playwright install-deps

```

### 3. 配置环境变量

创建 `.env` 文件（在 `backend` 目录下），配置以下环境变量：

#### 飞书配置（必需）
```
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_ENCRYPT_KEY=your_encrypt_key (可选)
FEISHU_VERIFICATION_TOKEN=your_verification_token (可选)
```

#### LLM 配置（必需）
```
BASE_URL=https://api.openai-proxy.org/v1
API_KEY=your_api_key
LLM_MODEL=deepseek-chat (可选，默认为 deepseek-chat)
LLM_TIMEOUT=120.0 (可选，超时时间，默认 120 秒)
LLM_TEMPERATURE=0.7 (可选，温度参数，默认 0.7，DeepSeek 不支持但不会报错)
LLM_MAX_RETRIES=2 (可选，最大重试次数，默认 2)
```

**重要提示：** 
- **BASE_URL 必须包含 `/v1` 后缀**，例如：`https://api.openai-proxy.org/v1`
- OpenAI 客户端会自动在 BASE_URL 后添加 `/chat/completions`
- 完整调用路径为：`{BASE_URL}/chat/completions`

**DeepSeek 模型配置：**
- 默认使用 `deepseek-chat` 模型
- 支持 OpenAI 兼容格式，可直接使用
- 注意：DeepSeek 不支持 `temperature`、`top_p`、`presence_penalty`、`frequency_penalty` 等参数，设置这些参数不会报错，但也不会生效
- 参考文档：[DeepSeek API 文档](https://doc.closeai-asia.com/tutorial/api/deepseek.html)

**常见配置示例：**
- CloseAI 代理（DeepSeek）：`BASE_URL=https://api.openai-proxy.org/v1` → 实际调用 `https://api.openai-proxy.org/v1/chat/completions`
- 标准 OpenAI API：`BASE_URL=https://api.openai.com/v1` → 实际调用 `https://api.openai.com/v1/chat/completions`

#### Notion 配置（必需）
```
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

**获取 Notion Token：**
1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 创建新的 Integration
3. 复制 "Internal Integration Token"
   - **新格式（2024年9月25日后）**：以 `ntn_` 开头
   - **旧格式（仍有效）**：以 `secret_` 开头
   - 两种格式都可以使用，新创建的 Integration 会使用 `ntn_` 格式
4. **重要**：确保 Integration 有 "Read content" 和 "Update content" 权限

> **注意**：Notion 在 2024 年 9 月 25 日更新了 token 格式。新生成的 token 使用 `ntn_` 前缀，旧的 `secret_` 前缀 token 仍然有效。建议将 token 视为不透明字符串，不要做格式验证。

**连接 Integration 到数据库（必需步骤）：**
1. 在 Notion 中打开您的目标数据库
2. 点击右上角的 **"..."** (三个点菜单)
3. 选择 **"Connections"** 或 **"连接"**
4. 在连接列表中找到并选择您创建的 Integration
5. 确认连接成功（数据库页面右上角会显示 Integration 图标）

**⚠️ 如果遇到 "Database has no properties" 错误：**
这通常意味着 Integration 没有正确连接到数据库。请按照上述步骤重新连接。

**获取 Notion Database ID：**
1. 在 Notion 中打开目标 Database
2. 从 URL 中提取 Database ID（32位字符，用连字符分隔）
3. 例如：`https://www.notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...` 中的 `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Notion 数据库属性配置：**
系统会自动获取数据库的 schema 并验证属性名称。如果您的数据库属性名称与默认值不同，可以通过环境变量自定义：

```
NOTION_PROPERTY_TITLE=Name              # 标题属性名称（默认: Title）
NOTION_PROPERTY_AI_SUMMARY=摘要          # AI摘要属性名称（默认: AI Summary）
NOTION_PROPERTY_CRITICAL_THINKING=思考点  # 批判性思考属性名称（默认: Critical Thinking）
NOTION_PROPERTY_TAGS=标签                # 标签属性名称（默认: Tags）
NOTION_PROPERTY_SCORE=评分               # 评分属性名称（默认: Score）
NOTION_PROPERTY_URL=链接                 # URL属性名称（默认: URL）
```

**数据库属性要求：**
- 必须有一个 **Title** 类型的属性（可以是任何名称，通过 `NOTION_PROPERTY_TITLE` 配置）
- 其他属性类型：
  - AI Summary: **Rich Text** 类型
  - Critical Thinking: **Rich Text** 类型
  - Tags: **Multi-select** 类型
  - Score: **Number** 类型
  - URL: **URL** 类型

**如果遇到属性不存在的错误：**

运行检查工具查看数据库属性：
```bash
uv run python check_notion_schema.py
```

这个工具会显示：
- 数据库中所有可用的属性及其类型
- 推荐的配置值
- 如何配置属性名称映射

然后根据输出结果，在 `.env` 文件中配置正确的属性名称。

**快速诊断步骤：**
1. 运行 `uv run python check_notion_schema.py` 查看数据库属性
2. 检查日志中输出的 "Available Notion database properties" 列表
3. 根据实际属性名称配置对应的环境变量
4. 确保属性类型正确（见上方要求）
5. 重新运行程序，查看详细的验证日志

**完整的 .env 文件示例：**
```
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxx
BASE_URL=https://api.openai-proxy.org/v1
API_KEY=sk-xxxxxxxxxxxxx
LLM_MODEL=deepseek-chat
NOTION_TOKEN=ntn_xxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. 在飞书开放平台配置事件订阅

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 进入您的应用（App ID: `cli_a9da4baa1fa2dbc9`）
3. 进入「事件订阅」页面
4. 选择「使用长连接接收事件」
5. 订阅需要的事件类型，例如：
   - `im.message.receive_v1` - 接收消息事件
   - `application.bot.menu_v6` - 机器人菜单事件
   - `im.message.card.action` - 卡片交互事件

### 5. 运行机器人

```bash
uv run python main.py
```

或者直接运行：

```bash
uv run python feishu_bot.py
```

## 代码结构

- `feishu_bot.py` - 飞书机器人主程序，包含长连接客户端实现和核心处理流程
- `main.py` - 程序入口
- `models.py` - 数据模型定义（Pydantic + Instructor）
- `scraper.py` - 网页抓取模块（使用 Playwright）
- `ai_processor.py` - AI 处理模块（使用自定义 LLM + Instructor）
- `notion_storage.py` - Notion API 客户端（存储模块）
- `pyproject.toml` - 项目配置和依赖

## 功能说明

### 核心工作流

1. **接收消息** - 通过 WebSocket 长连接接收飞书消息
2. **解析内容** - 从消息中提取 URL 和用户随笔
3. **抓取网页** - 使用 Playwright 抓取网页内容并转换为 Markdown
4. **AI 处理** - 使用自定义 LLM 提取结构化知识（标题、摘要、批判性思考点、标签、评分）
5. **存储到 Notion** - 将结构化数据写入 Notion Database
6. **发送通知** - 向飞书发送处理结果和 Notion 页面链接

### 技术特性

- 使用飞书官方SDK建立WebSocket长连接
- 异步任务处理，避免阻塞主线程
- 支持自定义 LLM 接口（兼容 OpenAI API 格式）
- 自动提取网页主要内容，去除导航、广告等噪音
- 结构化知识提取，使用 Instructor 确保输出格式稳定

## 使用方法

向飞书机器人发送包含 URL 的消息，格式如下：

```
https://example.com/article 这是我的随笔内容
```

机器人会自动：
1. 抓取网页内容
2. 使用 AI 提取结构化信息
3. 保存到 Notion
4. 发送处理结果通知

## 开发说明

核心处理逻辑在 `feishu_bot.py` 的 `process_and_save` 方法中。

如果需要修改 AI 提示词，请编辑 `ai_processor.py` 中的 `process_with_ai` 方法。

如果需要调整 Notion 字段映射，请编辑 `notion_storage.py` 中的 `create_page` 方法。

