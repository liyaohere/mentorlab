# MentorLab Architecture & Testing Guide

## 目录

1. [系统总览](#1-系统总览)
2. [后端架构详解](#2-后端架构详解)
3. [移动端架构详解](#3-移动端架构详解)
4. [管理面板架构](#4-管理面板架构)
5. [三臂实验设计如何实现](#5-三臂实验设计如何实现)
6. [数据流详解](#6-数据流详解)
7. [本地开发测试指南](#7-本地开发测试指南)
8. [部署与生产测试](#8-部署与生产测试)

---

## 1. 系统总览

MentorLab 是一个完整的全栈研究平台，由三个独立的代码库组成：

```
mentorlab/
├── backend/     ← FastAPI (Python) — API服务器、AI集成、数据库
├── app/         ← React Native (Expo) — 参与者使用的手机App
├── admin/       ← Vite + React — 研究者使用的管理面板
├── scripts/     ← 工具脚本（种子数据、数据库备份）
├── docs/        ← 文档（你正在读的这个）
└── docker-compose.yml  ← 一键部署配置
```

**架构示意图：**

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Mobile App     │     │  Admin Panel     │     │  Scheduler      │
│  (React Native) │     │  (Vite+React)    │     │  (APScheduler)  │
│  参与者手机端    │     │  研究者浏览器端   │     │  定时任务        │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │ HTTP/JSON             │ HTTP/JSON              │ 内部调用
         ▼                       ▼                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                       │
│                                                                  │
│  /api/v1/auth/*        ← 注册、JWT认证                           │
│  /api/v1/conversations/* ← 对话CRUD                              │
│  /api/v1/conversations/*/messages ← 发消息、获取AI回复            │
│  /api/v1/sync/*        ← 离线消息批量同步                        │
│  /api/v1/voice/*       ← 语音上传+Whisper转写                    │
│  /api/v1/surveys/*     ← 问卷配置、提交、查询                    │
│  /api/v1/notifications/* ← 推送通知追踪                          │
│  /api/v1/admin/*       ← 管理接口（CSV上传、数据导出、仪表盘）    │
└──────┬──────────┬────────────┬──────────────┬────────────────────┘
       │          │            │              │
       ▼          ▼            ▼              ▼
┌──────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐
│PostgreSQL│ │Claude/   │ │Whisper   │ │Firebase   │
│ 数据库   │ │OpenAI API│ │语音转写  │ │推送通知   │
└──────────┘ └─────────┘ └──────────┘ └───────────┘
```

**为什么选择这个架构？**

- **FastAPI (Python)**：你已经熟悉Python；FastAPI自动生成API文档（`/docs`页面）；async原生支持，适合I/O密集的AI调用
- **React Native (Expo)**：一套代码→Android APK；Expo Go方便开发调试；不需要Android Studio
- **PostgreSQL**：关系型数据，适合参与者-对话-消息的层级结构；JSON列支持灵活字段
- **Zustand (状态管理)**：比Redux简单10倍，没有action/reducer/dispatch的样板代码

---

## 2. 后端架构详解

### 2.1 目录结构与职责

```
backend/
├── app/
│   ├── main.py              ← FastAPI入口：注册路由、CORS、启动scheduler
│   ├── config.py            ← 环境变量配置（从.env加载）
│   ├── database.py          ← SQLAlchemy异步引擎和会话工厂
│   │
│   ├── models/              ← 数据库表定义（SQLAlchemy ORM）
│   │   ├── participant.py   ← participants表 + invite_codes表
│   │   ├── conversation.py  ← conversations表
│   │   ├── message.py       ← messages表（核心数据表）
│   │   ├── survey.py        ← surveys表
│   │   ├── notification.py  ← notifications表（推送追踪）
│   │   └── admin.py         ← admin_users + admin_events表
│   │
│   ├── schemas/             ← Pydantic模型（请求/响应的数据验证）
│   │   ├── auth.py          ← RegisterRequest, AuthResponse等
│   │   ├── conversation.py  ← ConversationResponse, MessageResponse等
│   │   ├── message.py       ← SendMessageRequest, SyncMessagesRequest等
│   │   └── survey.py        ← SurveyConfig, SurveyQuestion等
│   │
│   ├── routers/             ← API路由处理器（每个文件=一组endpoints）
│   │   ├── auth.py          ← POST /register, POST /refresh, GET/PATCH /me
│   │   ├── conversations.py ← GET/POST /conversations, GET /conversations/{id}
│   │   ├── messages.py      ← POST /conversations/{id}/messages, POST /sync/messages
│   │   ├── voice.py         ← POST /voice/transcribe
│   │   ├── surveys.py       ← GET /surveys/pending, POST /surveys, GET /surveys/config/{type}
│   │   ├── notifications.py ← POST /notifications/{id}/delivered, POST /notifications/{id}/opened
│   │   └── admin.py         ← 管理接口（CSV上传、导出、仪表盘、prompt编辑）
│   │
│   ├── services/            ← 业务逻辑层（与外部API交互）
│   │   ├── claude_service.py      ← ⭐ 核心：prompt组装 + AI调用（支持Anthropic和OpenAI）
│   │   ├── whisper_service.py     ← 语音转文字（OpenAI Whisper API）
│   │   ├── notification_service.py ← Firebase推送通知
│   │   ├── storage_service.py     ← S3/R2音频文件存储
│   │   └── scheduler_service.py   ← APScheduler定时任务（每周AI主动发起对话）
│   │
│   ├── prompts/             ← ⭐ 实验操纵的核心 — 系统提示词模板
│   │   ├── arm1_control.md        ← 控制组：结构化日记，不给建议
│   │   ├── arm2_analytic.md       ← 分析组：给具体建议，不挑战假设
│   │   ├── arm3_constructive.md   ← 建构组：用知识挑战思维框架
│   │   └── shared/
│   │       ├── conversation_rules.md  ← 所有组共享的对话规则
│   │       └── knowledge/             ← 行业知识库（农业、零售、服务、食品饮料）
│   │
│   ├── middleware/
│   │   └── auth.py          ← JWT验证中间件
│   │
│   └── utils/
│       └── invite_codes.py  ← 邀请码生成器（8位，排除易混淆字符）
│
├── tests/                   ← 20个自动化测试
├── alembic/                 ← 数据库迁移文件
├── .env                     ← 环境变量（API密钥等，不提交到git）
├── .env.example             ← 环境变量模板（提交到git）
├── pyproject.toml           ← Python依赖声明
└── Dockerfile               ← 生产部署用
```

### 2.2 数据库设计逻辑

**核心原则：** 每条消息都必须持久化到服务器端。不允许有"丢失"的消息。

```
invite_codes (预生成)          participants (注册时创建)
┌──────────┐                   ┌──────────────────┐
│ code     │──注册时消费──→    │ id (UUID)        │
│ arm      │   (绑定arm)       │ invite_code      │
│ cohort_id│                   │ arm (控制/分析/建构)│
│ used     │                   │ name, phone      │
└──────────┘                   │ venture_name     │
                               │ venture_desc     │
                               │ industry_vertical│
                               │ status (active)  │
                               │ consent_at       │
                               └────────┬─────────┘
                                        │ 1:N
                               ┌────────▼─────────┐
                               │ conversations    │
                               │ id, week_number  │
                               │ initiated_by     │
                               │ (system/participant)│
                               └────────┬─────────┘
                                        │ 1:N
                               ┌────────▼─────────┐
                               │ messages         │
                               │ id, client_id ⭐ │  ← client_id是离线同步的关键
                               │ role (user/asst) │
                               │ content          │
                               │ input_method     │
                               │ token_usage      │  ← AI成本追踪
                               │ sync_status      │
                               └──────────────────┘
```

**关键设计决策：**

1. **`client_id` (UUID, UNIQUE约束)**：手机端为每条消息生成一个UUID。如果网络断了消息发送失败，重试时服务器用client_id去重——同一条消息不会被处理两次，也不会产生重复的AI回复。这是离线队列正确性的基础。

2. **`invite_codes` 表与 `participants` 表分离**：邀请码在管理员上传CSV时生成，每个码绑定一个arm。参与者注册时"消费"这个码，继承其arm分配。这意味着随机化在码生成时就完成了，不是在注册时。

3. **`arm` 存在participant表而非conversation表**：一个参与者永远属于同一个arm。所有对话都使用该arm的prompt。

### 2.3 AI服务的Prompt组装逻辑（最核心的文件）

`backend/app/services/claude_service.py` 是整个实验的心脏。

**组装过程：**

```python
system_prompt = join([
    ARM_INSTRUCTIONS,        # ← arm1_control.md / arm2_analytic.md / arm3_constructive.md
    PARTICIPANT_CONTEXT,     # ← 动态生成：名字、企业、行业、第几周
    KNOWLEDGE_CONTEXT,       # ← 行业知识文件（仅arm 2和3使用）
    CONVERSATION_RULES,      # ← 共享规则：语言匹配、安全守则、回复长度
], separator="\n\n---\n\n")
```

**关键点：**
- 控制组（arm1）**不会收到**行业知识文件 → AI无法提供领域建议
- 分析组（arm2）和建构组（arm3）收到**完全相同的**行业知识 → 区别仅在于ARM_INSTRUCTIONS告诉AI如何使用这些知识
- prompt模板存储为markdown文件，可以通过admin面板实时编辑
- 修改prompt后自动清除缓存（`_prompt_cache.clear()`），下次请求生效

**双AI提供者支持：**

```
.env中设置 AI_PROVIDER=openai  →  使用OpenAI的gpt-4o-mini
.env中设置 AI_PROVIDER=anthropic → 使用Anthropic的Claude Sonnet

如果没设ANTHROPIC_API_KEY但设了OPENAI_API_KEY → 自动用OpenAI
```

这样你可以用OpenAI开发和测试（已有key），生产环境切换到Claude Sonnet。

### 2.4 离线消息同步流程

这是技术上最复杂的部分。为什么需要离线支持？因为乌干达Palabek/Adjumani的3G网络不稳定。

```
参与者发送消息:

1. 手机端生成 client_id = UUID
2. 消息写入本地SQLite, sync_status='pending'
3. UI立即显示这条消息（乐观更新），带时钟图标⏳

如果有网:
4a. POST /conversations/{id}/messages → 服务器保存 → 调用AI → 返回AI回复
5a. 本地标记 sync_status='synced' ✓ → UI显示勾号
6a. AI回复也缓存到本地SQLite

如果没网:
4b. HTTP请求失败 → 消息留在pending状态
5b. NetInfo监听器检测到网络恢复 → 自动触发同步
6b. POST /sync/messages (批量同步) → 服务器按顺序处理每条消息
7b. 每条消息用client_id去重 → 不会重复

如果同步失败3次:
8. sync_status='failed' ❌ → UI显示红色感叹号 + "点击重试"
```

### 2.5 定时任务（Scheduler）

每周一上午9:00 EAT（=UTC 06:00），scheduler自动：

1. 查询所有 `status='active'` 的参与者
2. 为每人创建一个新的 `conversation`（`initiated_by='system'`）
3. 调用AI生成开场白（基于该参与者的arm和历史）
4. 保存AI消息到数据库
5. 通过Firebase发送推送通知："Your mentor has a new message for you"

时间表可以通过admin面板按cohort自定义。也可以手动触发（用于测试）。

---

## 3. 移动端架构详解

### 3.1 目录结构

```
app/src/
├── App.tsx                 ← 根组件：加载token、注册推送、版本检查
├── navigation/
│   └── AppNavigator.tsx    ← 导航逻辑：未登录→AuthStack，已登录→MainStack
├── screens/
│   ├── WelcomeScreen.tsx   ← 输入邀请码
│   ├── RegisterScreen.tsx  ← 填写个人信息
│   ├── ConsentScreen.tsx   ← 知情同意
│   ├── ConversationListScreen.tsx ← 对话列表（主页）
│   ├── ChatScreen.tsx      ← ⭐ 聊天界面（核心屏幕）
│   ├── SurveyScreen.tsx    ← 动态问卷渲染
│   └── SettingsScreen.tsx  ← 设置（退出研究）
├── components/
│   ├── VoiceRecorder.tsx   ← 长按录音组件
│   └── UpdateBanner.tsx    ← 版本更新提示横幅
├── services/
│   ├── api.ts              ← HTTP客户端（所有API调用）
│   ├── offlineQueue.ts     ← SQLite离线队列（核心）
│   ├── syncService.ts      ← 网络监听+自动同步+指数退避重试
│   └── notificationService.ts ← 推送通知注册+处理
├── stores/
│   ├── authStore.ts        ← Zustand: JWT、参与者信息
│   └── conversationStore.ts ← Zustand: 对话列表、消息、发送逻辑
├── types/
│   └── index.ts            ← TypeScript类型定义
└── utils/
    └── constants.ts        ← API URL、颜色、行业列表
```

### 3.2 导航流程

```
App启动
  │
  ├── SecureStore中没有token → AuthStack
  │     WelcomeScreen (邀请码)
  │         → RegisterScreen (个人信息)
  │             → ConsentScreen (知情同意)
  │                 → MainStack
  │
  └── SecureStore中有token → MainStack
        ConversationListScreen (对话列表)
            │
            ├── 点击对话 → ChatScreen (聊天)
            ├── 点击"+" → 创建新对话 → ChatScreen
            ├── 点击问卷横幅 → SurveyScreen
            └── 点击⚙ → SettingsScreen
```

### 3.3 ChatScreen 语音输入流程

```
普通文字输入:
  [文字输入框] [发送按钮↑]

文字框为空时:
  [文字输入框] [🎤麦克风按钮]

点击麦克风 → 录音中:
  [取消]  [🔴 0:05 录音中...]  [发送↑]

录音完成 → 转写中:
  [🔄 Transcribing voice...]

转写完成 → 文字出现在输入框:
  [🎤 Voice transcript — edit before sending] [Clear]
  [转写的文字...]  [发送↑]

参与者可以编辑文字后再发送。发送时标记 input_method='voice'。
```

---

## 4. 管理面板架构

```
admin/src/
├── App.tsx          ← 路由配置 + 顶部导航栏
├── api.ts           ← 所有API调用的封装
├── App.css          ← 全局样式
└── pages/
    ├── DashboardPage.tsx     ← 统计仪表盘：参与者数量、消息数、成本估算
    ├── ParticipantsPage.tsx  ← 参与者表格 + CSV批量上传
    ├── PromptsPage.tsx       ← 三臂system prompt在线编辑器
    ├── SchedulePage.tsx      ← 定时任务配置 + 手动触发按钮
    └── ExportPage.tsx        ← CSV下载（聊天记录、问卷数据）
```

**管理面板功能一览：**

| 页面 | 功能 | 对应API |
|------|------|---------|
| Dashboard | 按arm统计参与者/消息数，AI成本 | `GET /admin/dashboard` |
| Participants | 查看所有参与者 + CSV上传生成邀请码 | `GET /admin/participants`, `POST /admin/participants/upload` |
| Prompts | 编辑三臂的system prompt，保存/回滚 | `GET/PUT /admin/prompts/{arm}` |
| Schedule | 配置每周发送时间 + 手动触发 | `GET/PUT /admin/schedule`, `POST /admin/trigger/{cohort}` |
| Export | 下载聊天记录CSV + 问卷CSV | `GET /admin/export/transcripts`, `GET /admin/export/surveys` |

---

## 5. 三臂实验设计如何实现

### 5.1 盲法保证

参与者**看到完全相同的UI**。没有任何视觉差异暴露arm分配。具体措施：

- App名称、颜色、图标三个arm完全一致
- 推送通知文字固定："Your mentor has a new message for you"（不含AI内容）
- admin面板使用arm名称（control/analytic/constructive），可以映射为A/B/C
- JWT中包含arm信息，但只在服务器端用于选择prompt，客户端不使用
- 系统prompt永远不会暴露给客户端

### 5.2 操纵的唯一差异

```python
# claude_service.py 中的关键代码
arm_file = {
    "control": "arm1_control.md",         # ← 结构化日记，不给建议
    "analytic": "arm2_analytic.md",       # ← 给建议但不挑战假设
    "constructive": "arm3_constructive.md", # ← 用知识挑战思维框架
}[participant.arm.value]
```

**这是整个实验操纵的全部实现。** 除了这三个.md文件的内容不同之外，三个arm的一切都完全相同。

### 5.3 操纵检查

你可以通过admin面板的Export功能导出所有聊天记录，然后检查：
- 控制组AI是否只在问三个固定问题+给通用鼓励
- 分析组AI是否在给具体建议但没有挑战假设
- 建构组AI是否在用思想实验/重构/类比等技术挑战思维

---

## 6. 数据流详解

### 6.1 参与者注册流程

```
管理员上传CSV                研究助理分发邀请码              参与者安装App
┌─────────────┐            ┌─────────────┐               ┌─────────────┐
│ CSV文件:     │   POST     │ 生成结果:    │   WhatsApp    │ 输入邀请码:  │
│ name, arm,  │──upload──→ │ XKLM49RP    │──分享链接──→  │ XKLM49RP   │
│ cohort      │            │ (control)   │               │            │
└─────────────┘            └─────────────┘               └──────┬──────┘
                                                                │
                                                          POST /register
                                                                │
                                                         ┌──────▼──────┐
                                                         │ 服务器:      │
                                                         │ 1. 查找码    │
                                                         │ 2. 码→arm   │
                                                         │ 3. 创建参与者│
                                                         │ 4. 返回JWT  │
                                                         └─────────────┘
```

### 6.2 一次完整的聊天数据流

```
参与者输入: "My tomato prices have dropped"
        │
        ▼
[ChatScreen] → conversationStore.sendMessage()
        │
        ├── 1. offlineQueue.enqueueMessage() → SQLite写入 (sync_status=pending)
        ├── 2. Zustand state更新 → UI立即显示消息
        ├── 3. POST /conversations/{id}/messages
        │       │
        │       ▼ (服务器端)
        │   ┌─────────────────────────────────────────┐
        │   │ messages.py._process_message():          │
        │   │                                          │
        │   │ 1. 检查client_id去重                     │
        │   │ 2. 保存user message到PostgreSQL          │
        │   │ 3. 加载对话历史（最多20条）               │
        │   │ 4. claude_service.get_response():        │
        │   │    a. 加载arm模板 (arm2_analytic.md)      │
        │   │    b. 生成参与者上下文                     │
        │   │    c. 加载行业知识 (agriculture.md)       │
        │   │    d. 加载对话规则                        │
        │   │    e. 组装system prompt                   │
        │   │    f. 调用OpenAI/Claude API               │
        │   │ 5. 保存assistant message + token_usage   │
        │   │ 6. 返回两条消息                          │
        │   └─────────────────────────────────────────┘
        │       │
        │       ▼
        ├── 4. markSynced() → SQLite更新 (sync_status=synced)
        ├── 5. cacheMessage(AI回复) → SQLite缓存
        └── 6. Zustand state更新 → UI显示AI回复 + ✓勾号
```

---

## 7. 本地开发测试指南

### 7.1 前提条件

你的机器上已经有了（之前安装好的）：
- PostgreSQL 16（Homebrew安装，`brew services start postgresql@16`）
- Python 3.11 + venv（`backend/.venv/`）
- Node.js 18+（Expo和admin用）
- `.env` 文件配好了OpenAI API key

### 7.2 启动后端

```bash
# 终端1: 后端
cd AppDev/mentorlab/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 输出应该是:
# INFO: Uvicorn running on http://127.0.0.1:8000
# INFO: Started reloader process
```

**验证后端是否正常：**
- 打开浏览器访问 http://localhost:8000/docs → 应该看到Swagger API文档页面
- 打开 http://localhost:8000/health → 应该看到 `{"status":"ok","version":"0.1.0"}`

### 7.3 运行自动化测试（后端）

```bash
cd AppDev/mentorlab/backend
source .venv/bin/activate
pytest tests/ -v
```

**预期输出：20 passed**

每个测试文件测试什么：

| 文件 | 测试内容 | 数量 |
|------|----------|------|
| `test_auth.py` | 注册（有效码、无效码、重复码）、个人资料、知情同意、未认证访问 | 6 |
| `test_conversations.py` | 创建对话、列表、获取详情、跨参与者访问控制 | 4 |
| `test_messages.py` | 发消息、幂等性（同一client_id）、批量同步、同步幂等性 | 4 |
| `test_voice.py` | 语音转写、无效文件类型拒绝、未认证拒绝 | 3 |
| `test_scheduler.py` | 手动触发创建对话、定时配置CRUD、通知追踪 | 3 |

**测试使用SQLite内存数据库**（不依赖PostgreSQL），Claude API被mock了（不消耗API额度）。

### 7.4 用curl手动测试API

```bash
# === 1. 注册 ===
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "invite_code": "TEST001A",
    "name": "Test User",
    "venture_name": "My Farm",
    "venture_description": "Growing vegetables",
    "industry_vertical": "Agriculture"
  }' | python3 -m json.tool

# 记下返回的 access_token

# === 2. 知情同意 ===
TOKEN="<paste-token-here>"
curl -s -X POST http://localhost:8000/api/v1/me/consent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"study_consent": true, "audio_consent": true}' | python3 -m json.tool

# === 3. 创建对话（AI生成开场白）===
curl -s -X POST http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 记下返回的 conversation.id

# === 4. 发送消息 ===
CONV_ID="<paste-conversation-id>"
curl -s -X POST "http://localhost:8000/api/v1/conversations/${CONV_ID}/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": \"I am struggling with getting customers for my vegetables.\",
    \"input_method\": \"text\",
    \"client_id\": \"$(python3 -c 'import uuid; print(uuid.uuid4())')\"
  }" | python3 -m json.tool

# === 5. 检查三个arm的AI行为差异 ===
# TEST001A = control → AI只会问模板问题+给鼓励
# TEST002B = analytic → AI给具体市场建议
# TEST003C = constructive → AI挑战你的假设
```

### 7.5 测试三臂差异

这是实验最关键的测试。用三个不同的邀请码注册三个参与者，问同一个问题：

```bash
# 对三个参与者说同样的话:
# "I sell chapati at the market. Business is slow this month."

# 控制组(TEST001A)应该回复类似:
# "Thank you for sharing that. What progress did you make this week?"
# (模板问题，没有任何建议)

# 分析组(TEST002B)应该回复类似:
# "Chapati businesses typically have 40-60% margins. To increase sales,
#  you could try positioning near schools or offices during lunch hour."
# (具体建议，在现有框架内优化)

# 建构组(TEST003C)应该回复类似:
# "You describe this as a slow month, but what if the issue isn't demand
#  but timing? What would change if you shifted to a catering model?"
# (挑战假设，提供替代视角)
```

### 7.6 启动移动端App

```bash
# 终端2: 移动App
cd AppDev/mentorlab/app
npx expo start
```

**测试方式（三选一）：**

1. **手机上安装Expo Go** → 扫描终端中显示的QR码 → App加载
2. **按 `w` 打开Web版** → 在浏览器中测试（功能有限）
3. **按 `a` 打开Android模拟器**（需要安装Android Studio）

**重要：** 如果用真机测试，需要把 `app/src/utils/constants.ts` 中的 `API_URL` 改成你电脑的局域网IP：
```typescript
export const API_URL = __DEV__
  ? 'http://192.168.1.XXX:8000'  // ← 改成你的IP (ifconfig | grep "inet ")
  : 'https://api.mentorlab.app';
```

### 7.7 启动管理面板

```bash
# 终端3: 管理面板
cd AppDev/mentorlab/admin
npm run dev
```

打开 http://localhost:5173 → 你应该看到管理面板。

**测试流程：**

1. **Dashboard页** → 查看参与者统计（如果之前通过curl注册了参与者，应该能看到数据）
2. **Participants页** → 上传CSV测试：

创建一个 `test.csv` 文件：
```csv
name,phone,arm,cohort,industry_vertical
Alice Amara,+256700111111,control,pilot_test,Agriculture
Bob Kato,+256700222222,analytic,pilot_test,Retail
Carol Nakato,+256700333333,constructive,pilot_test,Services
```

上传后应该看到3个新邀请码生成。

3. **Prompts页** → 选择arm → 查看/编辑system prompt → 点Save → 新对话会使用更新后的prompt
4. **Schedule页** → 设置定时 → 点"Trigger Conversations Now"（如果有active参与者，会立即生成AI主动发起的对话）
5. **Export页** → 下载Transcripts CSV和Surveys CSV

### 7.8 测试离线功能

1. 在手机上打开App → 进入一个对话
2. **打开飞行模式**
3. 发送3条消息 → 应该看到每条消息旁边有⏳时钟图标
4. **关闭飞行模式**
5. 等几秒 → 时钟图标变成✓勾号 → AI回复出现

### 7.9 测试语音输入

1. 进入一个对话
2. 文字输入框为空时，右侧显示🎤按钮
3. 点击麦克风 → 开始录音（需要麦克风权限）
4. 说一段话 → 点发送
5. 等待"Transcribing voice..."完成
6. 转写文字出现在输入框 → 可以编辑 → 点发送
7. 消息旁边显示"🎤 Voice"标记

---

## 8. 部署与生产测试

### 8.1 部署到Railway（推荐）

最简单的部署方式：

1. 把代码推到GitHub
2. 在 [railway.app](https://railway.app) 创建项目
3. 添加PostgreSQL数据库
4. 添加后端服务（指向 `backend/` 目录）
5. 设置环境变量（从 `.env` 复制）
6. Railway自动部署

### 8.2 生产环境Pilot前检查清单

```
环境配置:
□ AI_PROVIDER 设置正确（anthropic或openai）
□ API key有效且有足够余额
□ JWT_SECRET_KEY 已换成随机生成的密钥
□ DATABASE_URL 指向生产数据库
□ CORS_ORIGINS 包含生产域名

功能测试:
□ 注册 → 知情同意 → 创建对话 → AI回复正常
□ 三个arm的AI行为各不相同且符合协议
□ 语音输入能正常转写
□ 推送通知能正常到达（需配置Firebase）
□ 离线发送 → 上线后同步成功
□ App重启后历史消息仍在
□ admin面板能看到数据 → CSV导出正常

APK分发:
□ eas build --platform android --profile preview
□ APK能安装到Tecno Spark等低端Android手机
□ 在3G网络下能正常使用
□ 下载页面 (download.html) 能正常访问

数据安全:
□ .env 不在git中（.gitignore已配置）
□ JWT token有90天过期
□ 数据库有备份脚本在运行
□ 参与者只能看到自己的对话（跨参与者访问返回403）
```

### 8.3 成本预估

| 项目 | 单价 | 预估用量 | 总计 |
|------|------|----------|------|
| AI (OpenAI gpt-4o-mini) | ~$0.003/消息 | 450人 × 7周 × 6条 = 18,900条 | ~$57 |
| AI (Claude Sonnet) | ~$0.01/消息 | 同上 | ~$190 |
| Whisper 语音转写 | $0.006/分钟 | ~30%参与者用语音, 5min/条 | ~$280 |
| 服务器 (Railway) | $5-20/月 | 6个月 | ~$60-120 |
| **总计 (OpenAI)** | | | **~$400-460** |
| **总计 (Claude)** | | | **~$530-590** |

---

## 附录：关键文件速查表

| 你想做什么 | 看哪个文件 |
|------------|-----------|
| 修改AI的行为/prompt | `backend/app/prompts/arm{1,2,3}_*.md` |
| 修改问卷问题 | `backend/app/schemas/survey.py` 中的 `SURVEY_CONFIGS` |
| 修改App的颜色/UI | `app/src/utils/constants.ts` 中的 `COLORS` |
| 修改API URL | `app/src/utils/constants.ts` 中的 `API_URL` |
| 修改AI模型 | `backend/.env` 中的 `AI_PROVIDER` 和 `OPENAI_CHAT_MODEL` |
| 添加新的行业知识 | 在 `backend/app/prompts/shared/knowledge/` 下添加.md文件 |
| 修改邀请码格式 | `backend/app/utils/invite_codes.py` |
| 修改定时发送时间 | admin面板 Schedule页，或 `backend/app/services/scheduler_service.py` |
| 查看所有API端点 | 启动后端后访问 http://localhost:8000/docs |
| 导出聊天数据 | admin面板 Export页，或 `GET /api/v1/admin/export/transcripts` |
