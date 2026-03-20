# MentorLab Web App — UI Specification & Iteration Guide

## 如何使用这个文档

把这个文档带到一个新的Claude对话中，说："帮我根据这个spec迭代MentorLab的web app UI"。这个文档包含了所有你需要的上下文。

---

## 1. 项目概述

MentorLab是一个AI导师聊天应用，用于乌干达难民企业家的田野实验。参与者通过邀请码注册，和AI导师聊天讨论他们的创业问题。

**目标用户**: 乌干达难民营的小企业主（低端Android手机，3G网络）
**主要交互方式**: 语音输入为主（很多用户不习惯打字），文字输入为辅
**设计参考**: Olo app (https://www.olo.app/) 的语音输入元素，Claude app的字体风格

## 2. 技术架构

### 2.1 当前实现

Web app是一个**单个HTML文件**，没有框架，纯HTML/CSS/JS：
- 文件位置: `backend/static/app/index.html`
- 通过FastAPI的StaticFiles中间件服务
- 线上URL: `https://mentorlab-api-production.up.railway.app/`
- 所有API调用发送到同一个域名（`window.location.origin`）

### 2.2 为什么是单文件

- 不需要build步骤
- 修改后直接部署即可
- 对于一个聊天界面，不需要React/Vue的复杂度

### 2.3 部署方式

```bash
# 修改 backend/static/app/index.html 后：

# 1. 复制到部署目录
cp -r backend/static /tmp/mentorlab-backend/static
cp -r backend/app /tmp/mentorlab-backend/app
cp -r backend/alembic /tmp/mentorlab-backend/alembic

# 2. 部署到Railway
cd /tmp/mentorlab-backend && railway up

# 约3分钟后生效
```

或者本地测试：
```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
# 打开 http://localhost:8000/
```

## 3. 后端API接口

Web app调用以下API（全部是REST JSON）：

### 3.1 认证
```
POST /api/v1/auth/register
Body: { invite_code, name, phone_number, venture_name, venture_description, industry_vertical }
Response: { access_token, participant: { id, name, arm, ... } }
```
所有后续请求需要 `Authorization: Bearer <token>` header.

### 3.2 知情同意
```
POST /api/v1/me/consent
Body: { study_consent: true, audio_consent: false }
Response: participant object (with consent_at filled)
```

### 3.3 对话列表
```
GET /api/v1/conversations
Response: { conversations: [{ id, title, week_number, initiated_by, created_at, last_message: {...} }] }
```

### 3.4 创建新对话
```
POST /api/v1/conversations
Response: { conversation: { id, title, week_number, ... }, messages: [{ role: "assistant", content: "greeting..." }] }
```

### 3.5 获取对话详情（含所有消息）
```
GET /api/v1/conversations/{id}
Response: { conversation: {...}, messages: [{ id, role, content, input_method, created_at, ... }] }
```

### 3.6 发送消息
```
POST /api/v1/conversations/{id}/messages
Body: { content: "message text", input_method: "text"|"voice", client_id: "uuid" }
Response: { user_message: {...}, assistant_message: { role: "assistant", content: "AI reply" } }
```
注意：`client_id` 必须是一个UUID，用于去重。用 `crypto.randomUUID()` 生成。

### 3.7 语音转写
```
POST /api/v1/voice/transcribe
Body: FormData with audio file + conversation_id
Response: { transcript: "transcribed text", audio_url: null }
```

## 4. 应用的三个页面

### 4.1 登录/注册页
- 第一步：输入邀请码（8位字母数字）
- 第二步：填写个人信息（名字、电话、企业名、企业描述、行业）
- 提交后自动同意知情同意书
- 成功后跳转到对话列表

### 4.2 对话列表页
- 显示所有对话，按时间倒序
- 每个对话显示：**标题**（AI自动生成）、Week标签（小tag）、最后消息预览、时间
- 右下角 "+" 按钮创建新对话
- 顶部有 "Log out" 按钮
- 如果没有对话，显示空状态提示

### 4.3 聊天页（核心页面）
- 顶部：返回按钮 + 对话标题 + Week标签
- 中间：消息列表（用户消息右对齐深色，AI消息左对齐浅色）
- 底部：输入区域

## 5. 输入区域设计（当前问题所在）

### 5.1 期望的行为

**默认是语音模式**：
- 显示一个大的圆形麦克风按钮（居中）
- 按钮下方文字 "Tap to speak"
- 再下方有 "or type instead" 切换链接

**点击麦克风 → 录音中**：
- 按钮变红，有脉冲动画
- 显示录音时长 "0:05"
- 再次点击停止录音

**录音结束 → 转写中**：
- 显示 spinner + "Transcribing your voice..."

**转写完成**：
- 切换到文字模式
- 转写文字出现在输入框中
- 上方显示 "🎤 Voice transcript — edit before sending" + "Clear" 按钮
- 用户可以编辑文字后点发送

**文字模式**：
- 文字输入框 + 发送按钮
- 下方有 "use voice" 切换链接

**发送后**：
- 用户消息立即显示
- 显示 "Thinking..." 等待AI回复
- AI回复出现后，输入区域切换回语音模式

### 5.2 语音录制的技术实现

使用浏览器原生API：
```javascript
// 请求麦克风权限
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

// 创建录音器
const mediaRec = new MediaRecorder(stream);
const chunks = [];
mediaRec.ondataavailable = e => chunks.push(e.data);

// 开始录音
mediaRec.start();

// 停止录音
mediaRec.stop();

// 停止后，发送到后端转写
mediaRec.onstop = () => {
  stream.getTracks().forEach(t => t.stop()); // 释放麦克风
  const blob = new Blob(chunks, { type: 'audio/webm' });

  // 上传转写
  const form = new FormData();
  form.append('audio', blob, 'recording.webm');
  form.append('conversation_id', convId);
  fetch('/api/v1/voice/transcribe', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: form,
  }).then(r => r.json()).then(d => {
    // d.transcript 就是转写结果
    // 放入输入框让用户编辑
  });
};
```

### 5.3 当前的问题

用户报告 "voice input似乎消失了"。可能的原因：
- 麦克风按钮在某些浏览器上不可见或不可点击
- CSS布局问题导致按钮被遮挡
- 状态切换逻辑有bug（录音后没有正确切回）
- 在iOS Safari上 `navigator.mediaDevices` 可能需要HTTPS（Railway已经是HTTPS）

### 5.4 已知的浏览器兼容问题

- iOS Safari: 需要用户交互才能调用 `getUserMedia`，需要HTTPS
- 某些Android浏览器: `MediaRecorder` 可能不支持 `audio/webm`，需要fallback到 `audio/mp4`
- 桌面Chrome: 工作正常

## 6. 设计指南

### 6.1 当前使用的字体

```css
/* UI文字 */
font-family: 'Inter', -apple-system, sans-serif;

/* AI回复和标题 */
font-family: 'Newsreader', serif;
```

通过Google Fonts加载：
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Newsreader:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
```

### 6.2 当前色彩系统

```css
--green: #1B5E20;         /* 主色调 - 深绿 */
--green-light: #4CAF50;   /* 浅绿 */
--green-glow: rgba(76, 175, 80, 0.15);
--green-subtle: #E8F5E9;  /* 绿色背景 */
--bg: #FAFAF8;            /* 页面背景 - 暖白 */
--surface: #FFFFFF;       /* 卡片背景 */
--text: #1a1a1a;          /* 主文字 */
--text-secondary: #6b6b6b;
--text-light: #9e9e9e;
--user-bubble: #1a1a1a;   /* 用户消息气泡 - 深色 */
--assistant-bg: #f5f4f0;  /* AI消息气泡 - 暖灰 */
```

### 6.3 期望的文字大小

- 消息正文: 17-18px
- 输入框: 17px
- 按钮: 16px
- 时间戳: 11px
- 标签/辅助文字: 13px

### 6.4 设计参考

- **Olo app** (https://www.olo.app/): 中心语音元素的设计感——一个显眼的、有呼吸感的圆形按钮，不一定是方框，可以是一个带颜色渐变或光晕的圆形元素
- **Claude app**: 字体选择和排版风格——Inter用于UI，衬线字体用于AI回复，整体干净温暖的感觉
- **WhatsApp**: 消息列表和气泡的基本布局参考

## 7. 状态管理

App使用 `sessionStorage` 保持登录状态：
```javascript
sessionStorage.getItem('t')  // JWT token
sessionStorage.getItem('p')  // participant JSON

// 登录后设置
sessionStorage.setItem('t', token);
sessionStorage.setItem('p', JSON.stringify(participant));
```

关闭浏览器标签后需要重新登录（这是预期行为，因为是demo/测试用）。

## 8. 当前完整代码

文件: `backend/static/app/index.html`

这是一个单文件应用（~350行），包含HTML + CSS + JavaScript。修改这个文件就能改变所有UI。

## 9. 迭代时的注意事项

1. **不要改动API接口** — 后端API是固定的，只改前端
2. **保持单文件** — 不要引入React/Vue，保持纯HTML/CSS/JS的简单
3. **测试语音功能** — 需要HTTPS环境（Railway已经是），本地localhost也可以
4. **手机优先** — 主要在手机上使用，用Chrome DevTools的手机模式测试
5. **部署** — 修改后按上面的部署方式推送到Railway

## 10. 测试信息

- 线上URL: https://mentorlab-api-production.up.railway.app/
- 可用的邀请码: `KNRW433P`（constructive arm）
- 如果需要新邀请码，用admin面板上传CSV: https://mentorlab-api-production.up.railway.app/admin （密码: mentorlab2026）
- GitHub仓库: github.com/xilan-zhang/mentorlab (private)
