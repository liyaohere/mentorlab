# MentorLab 开发交接文档

**日期**: 2026 年 5 月
**交接人**: Xilan Zhang（Stanford PhD, 项目负责人）
**接收人**: 李垚（RA, 清华 CS & Finance）

---

## 概述

MentorLab 是一个田野实验（field experiment）平台。实验对象是乌干达约 450 名创业者。App 会生成 AI 商业诊断，以 3 种不同的呈现方式展示给创业者，然后测量不同呈现方式如何影响创业者自己的 problem formulation 质量。

**你的任务**: 把这个产品做好。现有代码是 vibe coding 的产物——后端（FastAPI）基本能用，前端是一个 830 行的单文件 HTML，比较糙。技术栈、架构、前后端怎么组织，你自己决定。可以重写前端、可以前后端都重构、也可以在现有基础上迭代——只要满足下面的原则就行。

---

## 三条原则

### 原则 1: 在 WiFi 很差的地方也能用

目标用户在乌干达，网络条件很差（可能只有 3G 甚至更慢）。这意味着：
- 首屏加载要轻（小 bundle、少请求）
- 核心流程中断后能恢复（不能因为断网丢数据）
- 在低端 Android 手机上流畅（测试基准：375px 宽度，Chrome）

具体方案你选——PWA、轻量 SPA、甚至服务端渲染都行，只要在 3G 下实测过。

### 原则 2: 不需要复杂安装流程

用户打开浏览器、输入网址就能用。不要 app store、不要 APK 下载、不要任何安装步骤。Xilan 会提供域名。

### 原则 3: System prompt 和 agent workflow 要跟 Xilan 一起过

后端的 `backend/app/services/diagnosis_service.py` 是实验核心——里面的 multi-agent pipeline（orchestrator → 3 agents → divergence check → integrator/summarizer）直接决定实验结果。`backend/app/prompts/` 里的 system prompt 同理。

**这些内容在改之前必须跟 Xilan 讨论。** 但其他部分（前端架构、UI 设计、部署方案、甚至后端重构）可以先推进，不用等。建议的节奏：先搭好整体架构和前端壳子，prompt/agent 的部分留到后面一起 work through。

---

## 研究背景（必读）

这是一个 **3 组被试间实验（3-arm between-subjects experiment）**。每个创业者描述自己的商业挑战，然后收到 AI 生成的诊断——关键在于呈现方式不同：

| 条件 | 创业者看到什么 | 后端行为 |
|------|---------------|---------|
| **C1**（单一诊断） | 1 个 AI 诊断 | 调用 1 次 Claude → 生成 1 个诊断 |
| **C2**（整合诊断） | 1 个综合诊断 | 调用 3 次 Claude → integrator 合并为 1 个 |
| **C3**（分开展示） | 3 个独立诊断 | 调用 3 次 Claude → summarizer 保留 3 个 |

**核心 manipulation**: C2 和 C3 用的是同一套 AI 输出，唯一区别是创业者看到的是合并后的还是分开的。这是实验干净的关键。

看完诊断后，所有创业者回答同一个中性问题（neutral prompt）：*"Based on what you've read and your own experience, how do you now understand the core challenge your venture is facing?"* —— 这个回答是 **primary outcome variable**（主要因变量），会由专家编码评分。

**完整实验设计**: 见 [experiment-design-v2.md](experiment-design-v2.md)

---

## 实验流程（核心用户旅程）

这是产品的主流程。每一步对应一个现有的后端 endpoint（如果你重写后端，这些 step 的逻辑需要保留）：

```
1. 开始          POST /api/v1/interview/start
   → 返回第一个 intake 问题

2. 信息采集(×6)  POST /api/v1/interview/{id}/intake
   Q1-4: 商业基本信息（公司名、行业等）
   Q5-6: 基线诊断能力（前测）
   → 每次调用返回下一个问题或完成标志

3. 生成诊断      POST /api/v1/interview/{id}/generate-diagnosis
   → 根据条件返回诊断：
     C1: { type: "single", diagnoses: [1个] }
     C2: { type: "integrated", diagnoses: [1个] }
     C3: { type: "competing", diagnoses: [3个] }
   → 同时返回 response_prompt（中性提问）

4. 选择          POST /api/v1/interview/{id}/selection
   (仅 C3)      → 创业者选择最认同的诊断

5. 回答          POST /api/v1/interview/{id}/response
   (主要因变量)   → 创业者写出自己的 problem formulation
                 → 必须传 reading_time_seconds, writing_time_seconds

6. 问卷          POST /api/v1/interview/{id}/survey
   → 7 个 Likert 量表项：cognitive_load, confusion,
     trust, confidence, ownership,
     perceived_disagreement, perceived_breadth

7. 完成          GET /api/v1/interview/{id}/transcript
   → 导出完整 session 数据
```

---

## 实验完整性约束（不管怎么改架构，这些必须保证）

1. **`input_method` tracking** —— 每条消息必须记录是语音输入还是文字输入（`voice` / `text`）。这是研究数据。

2. **计时数据** —— `reading_time_seconds`（阅读诊断的时间）和 `writing_time_seconds`（写回答的时间）是预注册的协变量。前端必须准确计时并传给后端。

3. **中性回答提示** —— 诊断展示后的提问在所有 3 个条件下必须完全一样。这个 prompt 从后端返回（`response_prompt` 字段）。前端不要在提问周围加任何条件特定的 UI 引导或额外文字。

4. **Invite code → 分组** —— 分组（arm assignment）在管理员上传邀请码时就确定了，不是在注册时。前端绝对不能让用户自己选条件。

5. **C2 vs C3 的展示差异** —— 这是整个实验的核心。C2 展示 1 个整合后的诊断，C3 展示 3 个独立诊断。前端的展示方式直接影响实验效度。在设计 C3 的卡片布局、交互方式之前，跟 Xilan 过一下。

---

## 语音输入

语音是主要输入方式——很多乌干达创业者更习惯说而不是打字。

**现有实现思路**（参考，不一定要沿用）：
1. `navigator.mediaDevices.getUserMedia({audio: true})` → MediaRecorder
2. 自动检测浏览器支持的音频格式: webm/opus > webm > mp4 > ogg > wav
3. 录音结束后 POST 音频到 `/api/v1/voice/transcribe`（后端调 OpenAI Whisper）
4. 展示转录文字供用户确认/编辑后再发送

**踩坑记录**:
- iOS Safari 需要 HTTPS 才能获取麦克风权限
- 部分 Android 浏览器只支持 `audio/mp4` 不支持 `audio/webm`
- 后端会自动去掉 content-type 里的 codec 参数（如 `audio/webm;codecs=opus` → `audio/webm`）

---

## 现有后端 API 参考

如果你决定保留现有后端，下面是完整的 endpoint 列表。如果你重写后端，这些可以作为功能规格参考。

### 认证 & 个人信息
| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/v1/auth/register` | 用 invite code 注册 |
| POST | `/api/v1/auth/login` | 手机号 + 密码登录 |
| POST | `/api/v1/auth/request-code` | 请求 OTP 验证码 |
| POST | `/api/v1/auth/verify-code` | 验证 OTP + 登录 |
| POST | `/api/v1/auth/refresh` | 刷新 JWT |
| GET | `/api/v1/me` | 获取个人信息 |
| PATCH | `/api/v1/me` | 更新个人信息 |
| POST | `/api/v1/me/consent` | 记录知情同意 |

### V2 实验流程（核心）
| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/v1/interview/start` | 开始 session |
| POST | `/api/v1/interview/{id}/intake` | 回答 intake 问题 |
| POST | `/api/v1/interview/{id}/generate-diagnosis` | 生成 AI 诊断 |
| POST | `/api/v1/interview/{id}/selection` | 记录选择（仅 C3） |
| POST | `/api/v1/interview/{id}/response` | 提交 problem formulation |
| POST | `/api/v1/interview/{id}/survey` | 提交过程性问卷 |
| GET | `/api/v1/interview/{id}/transcript` | 获取完整 transcript |

### V1 Chat（AI 导师对话 —— 次要功能）
| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | `/api/v1/conversations` | 列出所有对话 |
| POST | `/api/v1/conversations` | 创建新对话 |
| GET | `/api/v1/conversations/{id}` | 获取对话 + 消息 |
| POST | `/api/v1/conversations/{id}/messages/stream` | 发送消息（SSE 流式） |
| POST | `/api/v1/sync/messages` | 批量同步（离线支持） |

### 语音
| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/v1/voice/transcribe` | 音频 → 文字（Whisper） |
| POST | `/api/v1/interview/tts` | 文字 → 语音（OpenAI TTS） |

### 管理后台（需要 `X-Admin-Key` header）
| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/v1/admin/login` | 获取 admin API key |
| GET | `/api/v1/admin/dashboard` | 数据概览 |
| GET | `/api/v1/admin/participants` | 参与者列表 |
| POST | `/api/v1/admin/participants/upload` | CSV 批量导入 |
| GET | `/api/v1/admin/export/transcripts` | 导出对话记录 CSV |
| GET | `/api/v1/admin/export/surveys` | 导出问卷数据 CSV |
| GET/PUT | `/api/v1/admin/prompts/{arm}` | 查看/编辑 prompt |
| GET | `/api/v1/interview/admin/sessions` | 列出 V2 session |
| GET | `/api/v1/interview/admin/session/{id}` | V2 session 详情 |

**认证方式**: 参与者端 `Authorization: Bearer <jwt>`，管理端 `X-Admin-Key: <key>`。

---

## 数据库 Schema（关键表）

**Participant**（参与者）: id, invite_code, arm (c1/c2/c3), condition (single/integrated/competing), name, phone_number, venture_name, venture_description, industry_vertical, memory_notes, language_preference, status, password_hash, fcm_token, cohort_id

**Conversation**（对话/session）: id, participant_id, title, week_number, initiated_by, status (intake→baseline→analyzing→diagnosis→response→survey→complete), intake_responses (JSON), baseline_responses (JSON), diagnosis_raw (JSON array), diagnosis_integrated (text), diagnosis_shown (text), selection_choice (int), response_text (text), reading_time_seconds, writing_time_seconds, cognitive_load_score...perceived_breadth_score (7 个 Likert 分数)

**Message**（消息）: id, client_id (UUID, 用于幂等性去重), conversation_id, role, content, input_method (text/voice), audio_file_url, token_usage (JSON)

**InviteCode**（邀请码）: id, code, arm, cohort_id, used, used_by

完整 schema 在 `backend/app/models/` 目录。

---

## 优先级

### 必须做（Summer 2026 田野试验前）
1. **V2 实验流程**（intake → 诊断 → 回答 → 问卷）—— 这就是实验本身
2. **语音输入** + 文字备选
3. **计时功能**（阅读时间 + 写作时间）
4. **C3 诊断展示**（3 个独立诊断，清晰区分）
5. **移动端体验好**，3G 下可用
6. **Android Chrome 兼容**

### 有时间再做
7. 管理后台优化（现有 React admin 基本够用）
8. V1 Chat 界面（AI 导师对话 —— 次要功能）
9. Push notifications
10. 离线支持

### 暂不考虑
- iOS app / APK
- 多语言支持
- 支付功能

---

## 现有文件结构

```
mentorlab/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # .env 配置
│   │   ├── routers/            # API 端点
│   │   ├── services/
│   │   │   ├── claude_service.py      # AI 响应 + 流式
│   │   │   ├── diagnosis_service.py   # V2 多 agent pipeline ⚠️
│   │   │   ├── whisper_service.py     # 语音转文字
│   │   │   ├── tts_service.py         # 文字转语音
│   │   │   ├── scheduler_service.py   # 每周定时 AI 对话
│   │   │   ├── storage_service.py     # S3/R2 音频存储
│   │   │   └── notification_service.py
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── schemas/            # Pydantic 定义
│   │   └── prompts/            # 各条件的 system prompt ⚠️
│   ├── static/
│   │   ├── app/index.html      # 现有前端（830 行单文件）
│   │   └── admin/              # 管理后台 build 产物
│   ├── tests/                  # pytest (20 tests)
│   ├── .env                    # 密钥（找 Xilan 要）
│   └── pyproject.toml
├── admin/                      # 管理后台源码（React + Vite）
├── app/                        # Expo/React Native（已弃用）
├── docs/
│   ├── experiment-design-v2.md # ← 必读
│   ├── architecture.md         # 系统架构（中英双语）
│   ├── app-ui-spec.md          # UI 规范 + 语音设计
│   ├── setup.md                # 本地开发设置
│   ├── deployment.md           # Railway 部署
│   └── design-decisions/       # 设计决策记录
├── scripts/                    # 开发工具 + 冒烟测试
└── docker-compose.yml
```

---

## 本地开发

### 跑现有后端
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env    # API keys 找 Xilan 要
docker compose up -d db
alembic upgrade head
python scripts/seed_test_data.py
uvicorn app.main:app --reload --port 8000
```

### 测试用邀请码（seed 之后可用）
- `TEST001A` → C1（单一诊断）
- `TEST002B` → C2（整合诊断）
- `TEST003C` → C3（3 个独立诊断）

### 跑测试
```bash
pytest tests/ -v   # 20 个测试，SQLite 内存数据库
```

### 线上环境
- API: https://mentorlab-api-production.up.railway.app/api/v1/
- 管理后台: https://mentorlab-api-production.up.railway.app/admin（密码: `mentorlab2026`）

---

## 环境变量

找 Xilan 要具体的值。本地开发必需：

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mentorlab
JWT_SECRET_KEY=<本地随便写一个随机字符串>
ANTHROPIC_API_KEY=sk-ant-...        # Claude API（生成诊断）
OPENAI_API_KEY=sk-...               # Whisper + TTS
ADMIN_API_KEY=<管理后台密码>
```

可选（缺失不影响核心功能）：
```bash
S3_ENDPOINT_URL=...                 # Cloudflare R2（音频存储）
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
FCM_CREDENTIALS_PATH=...            # Firebase 推送通知
```

---

## 有问题？

微信找 Xilan。实验设计相关的问题先读 [experiment-design-v2.md](experiment-design-v2.md)。
