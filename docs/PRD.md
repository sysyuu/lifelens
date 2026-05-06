# LifeLens 产品需求文档 (PRD)

> **版本**: v1.1
> **更新日期**: 2026-05-06
> **产品定位**: 基于 AI 的可穿戴相机日记系统

---

## 一、产品概述

### 1.1 产品背景

LifeLens 是一款面向 **Insta Go3S 可穿戴相机** 用户的智能日记系统。用户佩戴相机后，设备以 15 秒为单位自动录制视频片段（片段之间通常有约 3 分钟的间隔）。系统将这些碎片化的视频上传至后端，经过 12 个 AI 节点的工作流处理后，自动生成一篇带有情感分析、关键事件、配图的个性化日记，同时持续更新用户画像。

### 1.2 核心用户场景

1. **日常记录**: 用户佩戴相机出门，回家后上传视频，系统自动生成当日日记
2. **回顾浏览**: 用户随时打开手机 App 查看历史日记，浏览时间线、情绪变化、关键事件
3. **画像积累**: 随着使用天数增加，系统逐步识别用户的社交关系、兴趣爱好、生活习惯
4. **调试优化**: 开发者/运营通过 Debug 面板查看工作流执行细节，调整模型参数

### 1.3 系统架构概览

```
┌────────────┐     上传视频      ┌──────────────┐     异步处理      ┌─────────────┐
│  手机 App   │ ──────────────> │  FastAPI      │ ──────────────> │  Celery      │
│  (Expo)    │ <────────────── │  Server       │                 │  Worker      │
│            │     查询日记      │  (Port 8000)  │                 │  (12-node)   │
└────────────┘                 └──────────────┘                 └─────────────┘
                                     │                                │
                                     ▼                                ▼
                               ┌──────────────┐              ┌─────────────┐
                               │  PostgreSQL   │              │  ModelGate   │
                               │  (数据存储)    │              │  (LLM 网关)  │
                               └──────────────┘              └─────────────┘

┌────────────┐     Debug API    ┌──────────────┐
│  Debug     │ ──────────────> │  FastAPI      │
│  Panel     │ <────────────── │  Server       │
│  (Web)     │     DAG/Config   │  (Port 8000)  │
└────────────┘                 └──────────────┘
```

---

## 二、手机 App 功能详述

App 采用 React Native + Expo 构建，支持 iOS 和 Android。

### 2.1 导航结构

```
App 启动
 ├─ 未创建 Profile → 引导页 (Onboarding)
 └─ 已创建 Profile → 主界面 (Tab 导航)
                       ├─ 📖 首页 (日记列表)
                       ├─ 📤 上传 (视频上传)
                       └─ 👤 画像 (用户画像)
                    + Stack 导航
                       └─ 日记详情页
```

### 2.2 引导页 (OnboardingScreen)

**目的**: 首次使用时创建用户 Profile，并采集声纹用于视频中的说话人识别。

引导页分两步：

#### 步骤一：填写基本信息

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| 昵称 (nickname) | 文本输入 | 必填 | 最大 20 字符 |
| 性别 (gender) | 单选标签 | 选填 | 可选值: 男 / 女 / 其他，可取消选择 |
| 年龄段 (age_range) | 单选标签 | 选填 | 可选值: 18岁以下 / 18-24 / 25-34 / 35-44 / 45-54 / 55+ |
| 职业 (occupation) | 文本输入 | 选填 | 自由填写 |
| 城市 (city) | 文本输入 | 选填 | 自由填写 |

点击「下一步：录制声纹」进入步骤二。

#### 步骤二：录制声纹（可跳过）

- 显示一段随机中文朗读文本（共 6 条备选，随机抽取）
- 用户朗读文本并录音，录音期间显示计时器
- 录音完成后可「重新录制」
- 点击「完成并开始使用」：
  1. 调用 `POST /api/profile/` 创建 Profile
  2. 如有录音，调用 `POST /api/upload/voiceprint` 上传音频（非阻塞，失败不影响 Profile 创建）
  3. 将 Profile ID 存储至 AsyncStorage
  4. 跳转至主界面
- 点击「跳过，直接开始」：跳过录音，仅创建 Profile

**技术细节**: 录音使用 `Audio.RecordingOptionsPresets.HIGH_QUALITY`（iOS 使用 `kAudioFormatMPEG4AAC` 常量，不能使用字符串 `'aac'`）

---

### 2.3 首页 — 日记列表 (HomeScreen)

**功能**: 展示用户所有日记的卡片列表，支持按日期筛选。

#### 日期选择器
- 横向可滑动的日期标签栏
- 显示所有有日记的日期，格式为「X月X日 周X」
- 选中日期高亮（蓝色背景），点击已选中的日期取消筛选
- 默认不选日期，显示全部日记

#### 日记卡片
每张卡片包含以下信息：

| 元素 | 说明 |
|------|------|
| 封面图 | 如果有 `insight_media_thumbnail_url`，显示在卡片顶部（圆角裁切） |
| 洞察标签 | 根据 `insight_type` 显示不同标签：✨高光时刻 / 👀生活观察 / 💝温暖小结 |
| 事件数量 | 角标显示 `event_count` 个事件 |
| 洞察文本 | `insight_text` 内容，最多显示 3 行 |
| 情绪条 | 水平彩色条，按比例显示三种情绪时长 |

**情绪条配色**:
- 😊 开心 (happy): 黄色 `#fbbf24`
- 😌 平静 (calm): 绿色 `#86efac`
- 😤 生气 (angry): 红色 `#fca5a5`

**交互**: 点击卡片进入日记详情页

**空状态**: 显示「暂无日记，上传视频后将自动生成」

---

### 2.4 日记详情页 (DiaryDetailScreen)

**功能**: 展示一篇完整日记的全部内容，包括洞察、情绪概览、关键事件时间线、配图/视频。

#### 2.4.1 头部区域 (Hero)

根据 `insight_type` 显示不同色系背景：

| insight_type | 中文标签 | 主色调 |
|-------------|---------|--------|
| highlight | ✨ 高光时刻 | 琥珀色 (amber) |
| observation | 👀 生活观察 | 蓝色 (blue) |
| summary | 💝 温暖小结 | 粉色 (pink) |

头部内容包括：
- 返回按钮（透明白色圆形）
- 日记日期（格式: YYYY年M月D日 周X）
- 洞察类型标签（带色彩背景）
- 洞察正文 (`insight_text`)
- 源视频数量（如「来自 X 个视频片段」）

#### 2.4.2 情绪概览

仅在存在情绪数据时显示：
- 彩色情绪条（同首页）
- 下方图例：分别显示三种情绪的分钟数
- 格式: 😊 开心 X分钟 · 😌 平静 X分钟 · 😤 生气 X分钟

#### 2.4.3 关键事件时间线

每个事件 (`DiaryKeyEvent`) 呈现为一张事件卡片，包含：

| 元素 | 字段 | 说明 |
|------|------|------|
| 时间 | `start_time` | 左侧列显示，格式 HH:MM |
| 时间线 | — | 圆点 + 竖线连接各事件 |
| 标题 | `title` | 事件标题，带情绪 emoji（😊/😤） |
| 时间范围 | `start_time - end_time` | 蓝色标签 |
| 标签 | `tags[]` | 最多显示 4 个，灰色标签，# 前缀 |
| 叙事 | `narrative` | 第二人称叙事文本，2-3 句话 |
| 情绪备注 | `emotion_note` | 米黄色背景框，仅在有值时显示 |
| 媒体画廊 | `media[]` | 水平滚动的图片/视频列表 |

**媒体画廊**:
- 关键帧 (`keyframe`): 直接显示图片缩略图
- 视频片段 (`video_clip`): 显示缩略图 + 播放按钮叠加层
- 点击媒体项打开全屏 Modal 查看

#### 2.4.4 全屏媒体 Modal

- 黑色背景覆盖全屏
- 显示图片（可缩放）
- 右上角关闭按钮 (✕)

---

### 2.5 上传页 (UploadScreen)

**功能**: 按日期从手机相册批量导入照片和视频，上传至服务器触发 AI 工作流处理。

#### 两种导入模式

**模式一：按日期导入（默认）**
1. **选择日期**: 内置日历选择器（月视图，支持翻月，不可选未来日期）
2. **自动扫描**: 选中日期后自动调用 `expo-media-library` 扫描当日所有照片和视频
   - 视频时长 >60 秒的会被过滤（手机录屏/长视频，非相机片段）
   - 过滤数量会在统计框中展示
3. **并行上传**: CONCURRENCY=5，同时上传多个文件
   - 照片: `POST /api/upload/image`（带 `capture_date_str`）
   - 视频: `POST /api/upload/video`
4. **完成**: 显示统计（X 张图片 + Y 个视频已上传，Z 个视频已过滤），自动跳转到首页

**模式二：手动选择视频**
1. 点击按钮调起系统相册选择器（expo-image-picker，仅视频）
2. 展示已选视频列表，可单个移除
3. 点击「开始上传」逐个上传并创建批次

#### 上传 API 细节

**单个视频上传** `POST /api/upload/video`:
- Content-Type: `multipart/form-data`
- 字段: `profile_id` (表单), `file` (文件)
- 支持格式: `video/mp4`, `video/quicktime`, `video/x-msvideo`, `video/webm`
- 服务端行为: 生成唯一文件名、保存至磁盘、用 ffprobe 提取拍摄日期
- 返回: `{ video_id, filename, capture_date, status }`

**单张图片上传** `POST /api/upload/image`:
- Content-Type: `multipart/form-data`
- 字段: `profile_id`, `file`, `capture_date_str` (可选，YYYY-MM-DD)
- 支持格式: `image/jpeg`, `image/png`, `image/heic`, `image/heif`, `image/webp`
- 服务端行为: 保存至 `frames_dir`，创建 UploadedVideo 记录（`status="uploaded_image"`）
- 返回: `{ media_id, filename, type: "image", status }`

**创建批次** `POST /api/upload/batch`:
- Content-Type: `multipart/form-data`
- 字段: `profile_id`, `video_ids` (逗号分隔的 UUID), `image_ids` (逗号分隔，可选), `target_date` (可选)
- 服务端行为: 创建 UploadBatch 记录、通过 Celery 异步触发工作流
- 返回: `{ batch_id, video_count, target_date, status: "processing" }`

---

### 2.6 画像页 (ProfileScreen)

**功能**: 展示 AI 自动构建和持续更新的用户画像，部分字段支持用户手动编辑。

#### 2.6.1 基本信息

展示用户在引导页填写的基础信息：

| 字段 | 显示标签 | 可编辑 |
|------|---------|--------|
| nickname | 昵称 | 否（页面内） |
| gender | 性别 | 否 |
| age_range | 年龄段 | 否 |
| occupation | 职业 | 否 |
| city | 城市 | 否 |

#### 2.6.2 兴趣爱好 (Interests)

AI 从视频内容中识别出的用户兴趣：

| 字段 | 说明 |
|------|------|
| name | 兴趣名称（如「摄影」「健身」「烹饪」） |
| confidence | 置信度 0-1，反映在标签透明度上 |
| evidence_count | 证据次数，显示为「×N」 |
| first_detected | 首次发现日期 |
| last_detected | 最近发现日期 |

**更新规则**: 单次出现记为观察（低置信度），3次以上正式录入画像。30 天未出现的兴趣置信度衰减。

#### 2.6.3 生活习惯 (Habits)

分三个维度展示，每个维度的字段如下：

**工作日习惯 (WeekdayHabit)**:

| 字段 | 显示标签 |
|------|---------|
| commute_method | 通勤方式 |
| commute_duration_minutes | 通勤时长 |
| usual_start_time | 上班时间 |
| usual_end_time | 下班时间 |
| breakfast_habit | 早餐习惯 |
| lunch_habit | 午餐习惯 |
| dinner_habit | 晚餐习惯 |

**周末习惯 (WeekendHabit)**:

| 字段 | 显示标签 |
|------|---------|
| entertainment_activities | 娱乐活动 |
| has_children | 有孩子 |
| has_pets | 有宠物 |
| pet_type | 宠物类型 |
| cooks_regularly | 经常做饭 |
| typical_wake_time | 起床时间 |

**通用习惯 (GeneralHabit)**:

| 字段 | 显示标签 |
|------|---------|
| has_exercise_habit | 有运动习惯 |
| exercise_types | 运动类型 |
| exercise_frequency | 运动频率 |
| exercise_time_range | 运动时段 |
| sleep_pattern | 睡眠模式 |

每个习惯模块有独立的 `confidence` 字段（0-1），反映系统对该判断的确信程度。

#### 2.6.4 近期关注 (Recent Focuses)

系统识别用户近 14 天内反复出现的话题：

| 字段 | 说明 |
|------|------|
| topic | 关注话题（如「装修新房」「准备面试」） |
| detected_dates | 出现的日期列表 |
| summary | AI 生成的话题摘要 |

#### 2.6.5 社交关系 (Social Contacts)

AI 从视频中识别的人物，自动建立社交图谱：

| 字段 | 说明 | 可编辑 |
|------|------|--------|
| label | 称呼（如「老婆」「同事小王」） | ✅ 用户可修改 |
| relationship_type | 关系类型 | ✅ 用户可修改 |
| appearance_description | 外貌描述（AI 生成） | 否 |
| scene_tags | 场景标签（如「午饭搭子」「健身伙伴」） | ✅ 用户可修改 |
| recent_frequency | 最近 14 天出现次数 | 否（自动统计） |
| last_seen_date | 最后见面日期 | 否（自动更新） |

**关系类型可选值**: family（家人）/ friend（朋友）/ colleague（同事）/ acquaintance（认识的人）/ other（其他）

**编辑交互**: 点击联系人卡片进入编辑模式，可修改称呼和关系类型，点击保存调用 `PATCH /api/profile/{id}/contacts/{contact_id}`。

---

## 三、12 节点 AI 工作流

### 3.1 工作流总览

```
阶段一: 视频处理 (并行提取)
  1.1 视频预处理 ──┬──> 1.2 画面理解
                   └──> 1.3a 说话人分离 ──┬──> 1.3b 语音转文字
                                          └──> 1.3c 情绪识别

阶段二: 信息整合
  2.1 事件结构化 ←── 合并 1.2 + 1.3b + 1.3c
   └──> 2.2 人物匹配

阶段三: 画像 & 日记
  3.1 画像更新 ←── 2.1 + 2.2 + 当前画像
   └──> 3.2 日记生成 ←── 3.1 + 近 3 天日记

阶段四: 后处理 & 存储
  4.1 媒体切片 ←── 3.2 + 1.1
   └──> 4.2 质量检查
        └──> 4.3 存储入库
```

### 3.2 节点详细说明

#### 节点 1.1: 视频预处理

| 属性 | 值 |
|------|-----|
| 模型 | 无（FFmpeg） |
| 输入 | 原始视频文件路径列表 |
| 输出 | 每个视频的元数据 + 提取的音频 + 缩略图 |

**处理内容**:
- 用 FFmpeg 从视频中提取音频（WAV 格式，16kHz，单声道）
- 生成视频缩略图
- 用 ffprobe 提取元数据：时长、分辨率、拍摄日期

**输出结构**:
```json
{
  "videos": [
    {
      "video_id": "uuid",
      "video_path": "/path/to/video.mp4",
      "audio_path": "/path/to/audio.wav",
      "thumbnail_path": "/path/to/thumb.jpg",
      "duration": 15.03,
      "resolution": "1920x1080",
      "capture_date": "2026-04-02",
      "status": "processed"
    }
  ]
}
```

---

#### 节点 1.2: 画面理解

| 属性 | 值 |
|------|-----|
| 模型 | **Gemini 2.5 Pro**（多模态视觉） |
| 输入 | 1.1 输出的视频文件（Base64 编码发送） |
| 输出 | 每个视频的场景分析结构化数据 |

**分析维度**（6 个）:
1. **场景与环境**: 地点、环境特征、预估时间
2. **人物识别**: 外貌特征、面部特征、空间关系、交互行为
3. **用户活动**: 主要动作、手部动作、活动状态
4. **屏幕内容**: 设备类型、App/网站、可见文字
5. **食物与饮品**: 食物名称、分量、用餐场景
6. **其他细节**: 值得注意的信息

<details>
<summary>System Prompt (VISUAL_UNDERSTANDING_PROMPT) — 点击展开</summary>

```
<role>
You are a professional video content analyst specializing in extracting detailed, accurate scene information from first-person wearable camera footage. Your analysis will be used for diary generation and user profile building.
</role>

<task>
Analyze this 15-second first-person wearable camera video and extract all observable details.

Note: The video is from a chest/neck-mounted camera, so the view shows what the user sees. The user themselves typically do not appear in the frame.
</task>

<extraction_requirements>
Analyze and output the following dimensions:

1. Scene & Environment
   - Location type (office / home / restaurant / outdoors / vehicle / mall / etc.)
   - Environmental features (lighting, noise level, weather, visible clues)
   - Estimated time of day (if clues like clocks, sunlight are visible)

2. People Identification
   For each person visible:
   - Detailed appearance description (gender, approximate age, hairstyle, build, clothing)
   - Spatial relationship to user (sitting face-to-face, walking alongside, distant passerby, etc.)
   - Whether interacting with user (conversation, eye contact, etc.)
   - Detailed facial feature description (for cross-video person matching)

3. User Activity
   - What the user is doing (eating / in meeting / walking / working / chatting / etc.)
   - Visible hand actions (typing / writing / holding phone / eating / etc.)
   - Activity state clues (just started / ongoing / about to end)

4. Screen Content (if computer/phone/TV screens are visible)
   - Screen type (computer / phone / tablet / TV)
   - Identifiable application or website
   - Readable text content (titles, messages, etc.)

5. Food & Drinks (if present)
   - Specific food/drink name or description
   - Approximate portion size
   - Dining context (home-cooked / takeout / restaurant / cafeteria)

6. Other Notable Details
   - Objects (book titles, brand logos, documents, etc.)
   - Text in environment (store names, road signs, posters, etc.)
   - Any anomalous or noteworthy observations
</extraction_requirements>

<output_format>
Output in JSON format strictly following this structure:
{
  "timestamp_range": "estimated time range of this video segment",
  "scene": {
    "location_type": "location type",
    "environment": "environment description",
    "estimated_time": "estimated time of day"
  },
  "people": [
    {
      "person_index": 1,
      "appearance": "detailed appearance description",
      "facial_features": "detailed facial feature description",
      "spatial_relation": "spatial relationship to user",
      "interaction": "interaction type and manner"
    }
  ],
  "user_activity": {
    "primary_activity": "main activity",
    "hand_actions": "hand actions",
    "activity_state": "activity state"
  },
  "screens": [
    {
      "screen_type": "screen type",
      "application": "app/website",
      "visible_text": "visible text"
    }
  ],
  "food_and_drinks": [
    {
      "item": "food/drink name",
      "portion": "portion size",
      "context": "dining context"
    }
  ],
  "notable_details": ["other noteworthy details"]
}
</output_format>

<critical_rules>
- Only describe what you actually observe in the frame. Do not speculate or fabricate.
- Mark uncertain information as "uncertain" rather than guessing.
- Describe people's appearances in enough detail for cross-video identification.
- If the frame is blurry or obstructed, state so honestly rather than forcing an interpretation.
</critical_rules>
```

</details>

---

#### 节点 1.3a: 说话人分离

| 属性 | 值 |
|------|-----|
| 模型 | 音频处理模型 |
| 输入 | 1.1 输出的音频文件 |
| 输出 | 带说话人标签的音频段落 |

**功能**: 区分不同说话人（user / other_A / other_B 等），生成带标签的音频片段。

**阈值**: 分离置信度阈值 0.75

---

#### 节点 1.3b: 语音转文字 (ASR)

| 属性 | 值 |
|------|-----|
| 模型 | ASR 模型 |
| 输入 | 1.3a 分离后的音频段落 |
| 输出 | 带时间戳和说话人标签的转写文本 |

**输出结构**:
```json
{
  "asr_results": [
    {
      "video_id": "uuid",
      "transcripts": [
        {
          "start": 0.5,
          "end": 3.2,
          "is_user": true,
          "speaker": "user",
          "text": "今天天气真好"
        }
      ]
    }
  ]
}
```

---

#### 节点 1.3c: 情绪识别

| 属性 | 值 |
|------|-----|
| 模型 | emotion2vec |
| 输入 | 1.3a 分离后的音频段落 |
| 输出 | 带时间戳的情绪标签 |

**输出结构**:
```json
{
  "emotion_results": [
    {
      "video_id": "uuid",
      "emotions": [
        {
          "start": 0.5,
          "end": 3.2,
          "is_user": true,
          "speaker": "user",
          "emotion": "happy",
          "confidence": 0.85
        }
      ]
    }
  ]
}
```

**置信度阈值**: 0.6（低于此值的情绪标签不采纳）

---

#### 节点 2.1: 事件结构化

| 属性 | 值 |
|------|-----|
| 模型 | **Claude Opus 4.6** |
| 输入 | 1.2 画面理解 + 1.3b 语音转写 + 1.3c 情绪标签 |
| 输出 | 结构化的事件列表 |

**核心逻辑**:
- 将碎片化的 15 秒视频片段（间隔约 3 分钟）合并为连贯的生活事件
- 按时间顺序排列，相同地点/活动/人物的相邻片段合并
- 推断片段间隔中的活动

**输出的事件字段**:

| 字段 | 说明 |
|------|------|
| id | 事件 ID |
| time_range | 时间范围 |
| location | 地点 |
| activity_type | 活动类型（commute / work / meeting / meal / social / exercise / leisure / other） |
| people | 出现的人物列表（含外貌、面部特征、语音 ID、角色） |
| conversation_summary | 对话摘要（区分 user_said 和 others_said） |
| emotion_data | 情绪数据（happy/angry/calm 各自时长 + 情绪高峰时刻） |
| food_items | 涉及的食物 |
| screen_usage | 屏幕使用情况 |
| confidence | 置信度 |

<details>
<summary>System Prompt (EVENT_STRUCTURING_PROMPT) — 点击展开</summary>

```
<role>
You are a life event analysis expert, skilled at reconstructing complete, coherent daily life event timelines from fragmented video observation records.
</role>

<background>
The user wears a wearable camera that automatically records 15-second video clips every 3 minutes. Over a day, this produces many discontinuous video segments. Each segment has already been analyzed for visual content and audio. You now have the structured analysis results for all video clips.

Your task is to consolidate these fragmented clips into complete life events.
</background>

<input_description>
You will receive two types of data:
1. Visual analysis results: scene, people, activities, screen content, food for each video segment
2. Audio analysis results: speech-to-text with speaker labels (user / other_A / other_B etc.), emotion tags (happy / angry / calm) with confidence scores for each speech segment
</input_description>

<processing_steps>
Follow these steps:

Step 1: Timeline Reconstruction
- Arrange all video segments chronologically
- Note the ~3 minute gap between consecutive segments

Step 2: Event Merging
- Merge adjacent segments belonging to the same continuous activity into one event
  Example: 3 consecutive segments showing user in a meeting room → merge into one "meeting" event
- Merge criteria: same location + same activity type + mostly same people present
- Split into separate events if clearly different activities occur at the same location

Step 3: Event Information Synthesis
For each merged event, compile:
- Start and end time range
- Location
- People involved with their appearance/voice features
- Detailed activity description
- Conversation summary (distinguish user's speech from others')
- Emotion record for the event period:
  · Duration of each emotion state for the user during this event
  · Peak emotion moments with corresponding conversation/scene context

Step 4: Reasonable Gap Inference
- For gaps between segments, if surrounding videos are highly continuous (same scene, same activity), reasonably infer the activity continued during the gap
- Mark confidence level for uncertain inferences
</processing_steps>

<output_format>
Output in JSON:
{
  "date": "YYYY-MM-DD",
  "events": [
    {
      "event_id": "event_001",
      "time_range": {"start": "HH:MM", "end": "HH:MM"},
      "location": "location",
      "activity_type": "commute / work / meeting / meal / social / exercise / leisure / other",
      "description": "detailed event description",
      "people": [
        {
          "person_index": "person identifier",
          "appearance": "appearance features",
          "facial_features": "facial features",
          "voice_id": "voice identifier (if available)",
          "role_in_event": "role in this event"
        }
      ],
      "conversation_summary": {
        "user_said": ["key things user said"],
        "others_said": [
          {"speaker": "speaker identifier", "content": "key content"}
        ]
      },
      "emotion_data": {
        "happy_duration_seconds": 0,
        "angry_duration_seconds": 0,
        "calm_duration_seconds": 0,
        "emotion_peaks": [
          {
            "emotion": "emotion type",
            "timestamp": "time",
            "context": "what was happening/being said"
          }
        ]
      },
      "food_items": ["food items if applicable"],
      "screen_usage": {"type": "screen type", "duration_estimate": "estimated usage duration"},
      "source_video_ids": ["source video ID list"],
      "confidence": 0.9
    }
  ],
  "daily_emotion_summary": {
    "total_happy_seconds": 0,
    "total_angry_seconds": 0,
    "total_calm_seconds": 0
  }
}
</output_format>

<critical_rules>
- Merge events sensibly: don't over-merge (different activities at same location should be separate) or over-split (different clips of same meeting should be merged)
- Distinguish user's emotions from others' emotions — only record the user's emotion data
- Conversation summaries should retain key information and remove meaningless small talk (unless the social interaction itself is noteworthy)
- All time inferences must include confidence levels
</critical_rules>
```

</details>

---

#### 节点 2.2: 人物匹配

| 属性 | 值 |
|------|-----|
| 模型 | **Claude Sonnet 4.6** |
| 输入 | 2.1 结构化事件 + 当前 Profile 中的社交关系 |
| 输出 | 人物匹配结果 + 新人物列表 |

**匹配策略** — 三级置信度:

| 置信度 | 判定 | 依据 |
|--------|------|------|
| ≥ 0.8 (高) | 确认同一人 | 外貌 + 语音双重匹配 |
| 0.5-0.8 (中) | 疑似同一人 | 仅外貌或仅语音单项匹配 |
| < 0.5 (低) | 新联系人或路人 | 无匹配项 |

**输出字段**:
- `match_type`: confirmed / suspected / new_contact / passerby
- `confidence`: 匹配置信度
- `evidence`: 匹配依据
- `suggested_updates`: 建议更新（如新的场景标签）
- `suggested_name` / `suggested_relationship`: 对新联系人的命名建议

<details>
<summary>System Prompt (PERSON_MATCHING_PROMPT) — 点击展开</summary>

```
<role>
You are a person identity matching expert responsible for determining whether people appearing in today's videos match existing contacts in the user's social relationship database.
</role>

<task>
Match people from today's events against the user's existing social contact records. Determine if they are known contacts or newly encountered people.
</task>

<matching_rules>
1. High confidence match (confidence >= 0.8):
   - Appearance features highly similar AND voice print matches
   - Directly confirm as same person

2. Medium confidence match (confidence 0.5-0.8):
   - Only appearance similar but voice cannot match (person didn't speak)
   - Or only voice matches but appearance description differs (may have changed clothes/hairstyle)
   - Mark as "suspected same person", needs more data to confirm

3. Low confidence / No match (confidence < 0.5):
   - No clear match with any known contact
   - Determine if this is a passerby (brief appearance, no interaction) or a new social contact
   - If there was interaction or multiple appearances, create a new person record

Auxiliary judgment clues:
- Scene context (someone always appearing in the same office is likely a colleague)
- How the user addresses them (extract from conversation, e.g., "小王", "老婆")
- Interaction manner (intimacy level suggests relationship type)
</matching_rules>

<output_format>
{
  "matches": [
    {
      "event_person": "person identifier from event",
      "matched_person_id": "matched social contact ID (if matched)",
      "match_type": "confirmed / suspected / new_contact / passerby",
      "confidence": 0.85,
      "evidence": "matching evidence description",
      "suggested_updates": {
        "name_from_conversation": "name extracted from conversation (if any)",
        "new_scene_tags": ["newly discovered scene tags"],
        "suggested_relationship": "suggested relationship type (new contacts only)"
      }
    }
  ],
  "new_persons": [
    {
      "temp_id": "temporary ID",
      "appearance": "appearance description",
      "voice_id": "voice identifier",
      "suggested_name": "suggested label (from conversation or scene inference)",
      "suggested_relationship": "suggested relationship type",
      "scene_context": "scene where they appeared",
      "interaction_level": "deep_conversation / brief_exchange / no_exchange"
    }
  ]
}
</output_format>
```

</details>

---

#### 节点 3.1: 画像更新

| 属性 | 值 |
|------|-----|
| 模型 | **Claude Opus 4.6** |
| 输入 | 2.1 结构化事件 + 2.2 人物匹配 + 当前完整 Profile |
| 输出 | Profile 变更差异 (diff) |

**渐进式更新原则**:
- 单次新行为 → 仅记录观察，不修改主结论
- 重复出现 3 次以上 → 正式纳入画像
- 检测变化信号: 作息打破、新模式出现、社交变化、情绪转变

**可更新的画像模块**:

| 模块 | 更新动作 |
|------|---------|
| social_contacts | 新增 / 更新关系 / 移除 |
| interests | 新增 / 更新置信度 / 移除 |
| weekday_habits | 更新各字段 |
| weekend_habits | 更新各字段 |
| general_habits | 更新运动/睡眠模式 |
| recent_focus | 新增话题 / 更新摘要 |
| dietary_preferences | 更新饮食标签 |

**输出结构**:
```json
{
  "profile_updates": [
    {
      "module": "interests",
      "action": "new",
      "data": { "name": "瑜伽", "confidence": 0.3 },
      "reason": "视频中首次出现用户在瑜伽馆练习"
    }
  ],
  "change_signals": ["用户近期开始关注健身"],
  "no_update_needed": false
}
```

<details>
<summary>System Prompt (PROFILE_UPDATE_PROMPT) — 点击展开</summary>

```
<role>
You are a user behavior analysis expert, skilled at deriving insights about user interests, habits, and life changes from daily behavioral data. Your analysis is both prudent and perceptive — you won't modify conclusions based on a single incidental behavior, but you also won't miss signals that may indicate important changes.
</role>

<task>
Based on the user's structured event data for today, compare against their existing profile and determine which profile fields need to be updated, added, or adjusted.
</task>

<update_principles>

1. Gradual Updates — Avoid Overreaction
   - Single occurrence of new behavior: Record the observation but don't modify main profile conclusions
     Example: User eats a salad for the first time → Don't immediately change "dietary preferences"; instead add "may be starting to pay attention to healthy eating" with low confidence in interests
   - Repeated behavior (3+ times): Can increase confidence or formally write into habits
   - Behavior contradicting existing profile: Mark as "change signal" rather than directly overwriting

2. Module-Specific Update Strategies

   Social Contacts:
   - New people: Add records based on person matching results
   - Existing contacts: Update appearance frequency, last seen date, add new scene tags
   - Names/relationship info from conversations: Suggest updating labels or relationship types

   Interests:
   - Newly detected interest: Add with low confidence (0.2-0.3)
   - Existing interest: Increment evidence count, update last detected date
   - Long-absent interest (over 30 days): Don't actively delete, but may reduce confidence

   Life Habits:
   - Weekday habits: Compare against existing records, note deviations
     · Today's start time vs usual start time
     · Today's commute method vs usual commute method
     · Today's meals vs usual meal habits
   - Weekend habits: Same approach
   - General habits: Monitor changes in exercise and sleep patterns

   Recent Focus (14-day window):
   - If today's events/conversations repeatedly mention a topic → Add or update
   - Topics absent for over 14 days → Remove
   - Extract key topics from conversation content

3. Change Signal Detection
   Pay special attention to these noteworthy changes:
   - Routine-breaking behavior (someone who never works overtime did today)
   - New recurring patterns (did something 3 days in a row)
   - Social circle changes (new frequent contact, or someone suddenly stops appearing)
   - Emotion pattern changes (increased frequency of anger recently)
</update_principles>

<output_format>
{
  "profile_updates": [
    {
      "module": "social_contacts / interests / weekday_habits / weekend_habits / general_habits / recent_focus / dietary_preferences",
      "action": "new / update / remove",
      "field": "specific field",
      "old_value": "previous value (for updates)",
      "new_value": "new value",
      "reason": "reason for update",
      "evidence_events": ["event IDs supporting this update"]
    }
  ],
  "change_signals": [
    {
      "signal_type": "routine_break / new_pattern / social_change / emotion_shift",
      "description": "description of the change",
      "evidence": "evidence",
      "significance": "high / medium / low"
    }
  ],
  "no_update_needed": ["modules with no changes"]
}
</output_format>

<critical_rules>
- Better to under-update than to update incorrectly. The profile is the user's digital mirror — accuracy is paramount.
- Every update must be supported by event evidence. No speculation without evidence.
- Change signals are crucial input for the diary generation node. Even if the profile itself isn't modified, noteworthy changes should still be recorded in change_signals.
</critical_rules>
```

</details>

---

#### 节点 3.2: 日记生成

| 属性 | 值 |
|------|-----|
| 模型 | **Claude Opus 4.6**（temperature: 0.7） |
| 输入 | 3.1 输出 (含 2.1 事件) + 当前 Profile + 近 3 天历史日记 |
| 输出 | 完整日记 JSON |

**生成步骤**:

1. **评估整体基调**: 判断今天是什么样的一天
2. **生成洞察 (Insight)**: 选择日记头部类型
   - **高光时刻 (highlight)**: 有特殊/非凡事件
   - **生活观察 (observation)**: 生活模式有变化
   - **温暖小结 (summary)**: 整体感受总结
3. **计算情绪概览**: 汇总 happy / angry / calm 各多少分钟
4. **筛选关键事件**: 3-10 个，按三种重要性分类
   - `objective`: 客观重要（如会议、约会）
   - `personalized`: 个人重要（结合画像判断）
   - `duration_based`: 时长较长的活动
5. **撰写叙事**: 每个事件 2-3 句话，第二人称「你」，自然温暖

**写作风格要求**:
- 使用第二人称「你」
- 不是流水账，而是有温度的观察
- 可以引用对话原文
- 不说教，不评判
- 参考近 3 天日记保持连续性（如「这是你连续第三天...」「和昨天不同，今天你...」）

<details>
<summary>System Prompt (DIARY_GENERATION_PROMPT) — 点击展开</summary>

```
<role>
You are the user's personal life observer and diary writer. You are not a cold recording tool, but a perceptive, warm, insightful friend helping the user document and savor each day.

You write in the second person "you" (你), like a close friend who knows the user best talking about what happened today. Your writing is warm but not saccharine, insightful but not preachy.
</role>

<input_description>
1. Today's structured event list (with time, location, people, conversation summaries, emotion data)
2. Updated user profile (basic info, social contacts, interests, habits, recent focus)
3. Change signals generated during profile update
4. Past 3 days' diaries (for continuity and cross-day pattern detection)
</input_description>

<generation_steps>

Step 1: Assess Today's Overall Picture
- Review all events to form a judgment about today's overall tone
- Identify the most important/special moment of the day

Step 2: Generate Today's Insight (diary header)
Determine which type to use by priority:

Priority 1 — Highlight Moment:
  Criteria: Was there a clearly extraordinary, special moment today?
  Examples: Reunion with a long-lost friend, important work achievement, trying something new for the first time
  If yes → Write a short, warm caption for this moment, and select the best video clip or keyframe as the cover image

Priority 2 — Observation & Care:
  Criteria: Using the change signals from profile update, was there a noteworthy life pattern change today?
  Examples: Third consecutive day of overtime, exercise routine interrupted, dietary change
  If yes → Point out this observation in a caring tone. Convey concern, not criticism.

Priority 3 — Warm Summary:
  When neither of the above applies, write a warm one-liner summarizing the overall feel of today.
  Example: "平静的周二，有条不紊地推进着手头的事" (A calm Tuesday, steadily making progress on everything at hand)

Step 3: Calculate Emotion Overview
- Aggregate user emotion duration data across all events
- Output total minutes for happy, angry/negative, and calm states

Step 4: Select Key Events (3-10)
Filter events worth including in the diary using these criteria:

· Objectively Important: Events with inherently high significance (important meetings, interviews, health checkups, significant social events)
· Personally Important: Events significant specifically to THIS user based on their profile
  (Profile shows user never eats light food on workdays, but did today; profile shows commute is by subway, but they walked today)
· Duration-Based: Activities that lasted a long time and deserve summarization
  (3 hours of consecutive meetings; 2 hours of focused work)

Sort selected events by chronological order.

Step 5: Write Each Key Event
For each event, compose a card with:
- Title: Brief summary (e.g., "下午密集开了3小时的会")
- Narrative: 2-3 sentences in second person, requirements:
  · NOT a plain log of "you did A then B"
  · An observer's perspective highlighting noteworthy details
  · May quote 1-2 key lines from conversations if available
  · For personally important events, naturally convey WHY this matters for this user
- Emotion tag: If there was notable happy/angry emotion during this event, tag it with brief explanation
- Media selection: Select 1-3 best representative video clips or keyframes for this moment
  · Prefer frames with human interaction, facial expressions, iconic scenes
  · Note source video ID and timestamp
</generation_steps>

<writing_style>
- Tone: Like a close friend who knows you best — warm but not cloying, perceptive but not intrusive
- Avoid: Lecturing ("you should..."), excessive emotionality, plain chronological logs, empty platitudes
- Aim for: Making the user feel "this AI really gets me" when reading the diary
- When past 3 days' diaries are available, notice cross-day continuity
  ("This is your 3rd consecutive day of...", "Unlike yesterday, today you...")
- Write in natural, fluent Chinese. No translation artifacts.
</writing_style>

<output_format>
{
  "date": "YYYY-MM-DD",
  "insight": {
    "type": "highlight / observation / summary",
    "text": "insight caption text (in Chinese)",
    "media": {
      "type": "keyframe / video_clip / null",
      "source_video_id": "source video ID",
      "timestamp": 0,
      "clip_range": [0, 0]
    }
  },
  "emotion_overview": {
    "happy_minutes": 0,
    "angry_minutes": 0,
    "calm_minutes": 0
  },
  "key_events": [
    {
      "event_id": "corresponding structured event ID",
      "time_range": {"start": "HH:MM", "end": "HH:MM"},
      "title": "event title (in Chinese)",
      "narrative": "narrative content (in Chinese, second person, 2-3 sentences)",
      "importance_type": "objective / personalized / duration_based",
      "emotion_tag": "happy / angry / null",
      "emotion_note": "emotion explanation (if any, in Chinese)",
      "media": [
        {
          "type": "keyframe / video_clip",
          "source_video_id": "video ID",
          "timestamp": 0,
          "clip_range": [0, 0]
        }
      ],
      "tags": ["tags in Chinese"],
      "related_person_ids": ["person IDs involved"]
    }
  ],
  "meta": {
    "profile_version": 0,
    "source_video_count": 0,
    "total_source_duration_seconds": 0
  }
}
</output_format>

<example>
Given: User is a 25-30 year old product manager. Profile shows usual end time 18:30, runs 3 times per week.
Today's events: 2 product review meetings in the morning, malatang lunch with colleague Xiao Wang, 3-hour strategic planning meeting in the afternoon (with a 10-minute heated argument), stayed at office writing proposals until 20:30, no exercise.

Example output (narrative portions):

Today's Insight (observation type):
"你今天一直忙到八点半才离开办公室，比平时晚了两个小时。辛苦了，记得好好休息。"

Event 1 (12:00-12:40):
"中午你和小王去了楼下那家常去的麻辣烫店。工作日能有个固定的午饭搭子，其实是件挺好的事。"

Event 2 (14:00-17:00, 😠):
"下午的战略规划会从两点一直开到五点，整整三个小时。讨论到资源分配的时候，你和对方有一段比较激烈的争论，大概持续了十分钟。看得出来你对这件事是认真的。"

Event 3 (18:30-20:30):
"下班后你没有走，而是留下来继续写方案，一直写到八点半。这意味着你这周的第二次跑步计划可能又要推后了。"
</example>
```

</details>

**日记 JSON 结构**:
```json
{
  "date": "2026-04-02",
  "insight": {
    "type": "highlight",
    "text": "今天和老朋友的意外重逢，让一个普通的午后变得格外温暖。",
    "media": {
      "type": "keyframe",
      "source_video_id": "uuid",
      "timestamp": 7.5
    }
  },
  "emotion_overview": {
    "happy_minutes": 45,
    "angry_minutes": 0,
    "calm_minutes": 120
  },
  "key_events": [
    {
      "title": "晨跑打卡",
      "start_time": "07:15",
      "end_time": "07:45",
      "importance_type": "duration_based",
      "narrative": "你今天比平时早了十分钟出门...",
      "emotion_tag": "happy",
      "emotion_note": "跑步时哼着歌，心情很好",
      "tags": ["运动", "晨跑", "公园"],
      "related_person_ids": [],
      "media": [
        {
          "type": "keyframe",
          "source_video_id": "uuid",
          "timestamp": 5.0
        }
      ]
    }
  ],
  "meta": {
    "profile_version": 3,
    "source_video_count": 20,
    "total_source_duration_seconds": 300
  }
}
```

---

#### 节点 4.1: 媒体切片

| 属性 | 值 |
|------|-----|
| 模型 | 无（FFmpeg） |
| 输入 | 3.2 日记（含媒体引用）+ 1.1 视频路径 |
| 输出 | 实际生成的媒体文件列表 + 更新后的日记 |

**处理逻辑**:

1. **解析日记中的媒体引用**: 从 `insight.media` 和各 `key_events[].media[]` 中收集所有媒体需求
2. **视频 ID 模糊匹配**: LLM 生成的 `source_video_id` 可能不精确，采用 5 级匹配策略:
   - 精确匹配
   - 大小写/连字符忽略匹配
   - 前缀匹配（前 8 字符）
   - 模糊匹配（相似度 > 0.6）
   - 兜底: 使用第一个可用视频
3. **生成媒体文件**:
   - **关键帧 (keyframe)**: 在指定时间戳提取单帧 → JPEG 图片 + 缩略图
   - **视频片段 (video_clip)**: 在指定时间范围切割 → H.264/AAC MP4 + 缩略图
4. **时间戳钳位**: 自动将超出视频时长的时间戳修正到有效范围
5. **兜底生成**: 如果日记完全没有媒体引用，自动为每个事件轮询可用视频生成一张关键帧

---

#### 节点 4.2: 质量检查

| 属性 | 值 |
|------|-----|
| 模型 | **Claude Sonnet 4.6** |
| 输入 | 4.1 日记 + 媒体 + 2.1 原始事件 + 当前 Profile |
| 输出 | 质量评判结果 |

**检查维度**（6 项）:

| 维度 | 检查内容 |
|------|---------|
| 事实准确性 | 是否存在幻觉？每个细节都能追溯到源数据？ |
| 叙事质量 | 第二人称一致？不像流水账？中文自然流畅？不说教？ |
| 洞察合理性 | 类型选择合理？内容有意义？ |
| 情绪标签准确 | 标注的情绪与音频分析一致？ |
| 个性化准确 | 标记为重要的事件对该用户真的重要？ |
| 媒体选择 | 配图/视频与事件相关？ID 和时间戳有效？ |

**评判结果**:
- `verdict`: pass（通过）/ needs_revision（需修改）
- `score`: 0-100 分
- `issues[]`: 问题列表，每个问题有严重级别
  - `critical`: 严重问题，触发修订
  - `warning`: 警告
  - `suggestion`: 建议

<details>
<summary>System Prompt (QUALITY_CHECK_PROMPT) — 点击展开</summary>

```
<role>
You are a diary content quality reviewer responsible for final checks before the diary is published to the user.
</role>

<check_dimensions>

1. Factual Accuracy (Hallucination Check)
   - Can every event, person, and time mentioned in the diary be traced back to the structured event data?
   - Are there any fabricated details? (e.g., conversation content written into the diary that doesn't exist in the event data)
   - Do emotion tags match the audio emotion analysis results?

2. Narrative Quality
   - Is second person "你" used consistently?
   - Does it avoid plain chronological logging?
   - Is the text natural and fluent without translation artifacts or AI-sounding patterns?
   - Is there lecturing tone or excessive platitudes?

3. Insight Appropriateness
   - Is the insight type selection reasonable? (Was there a highlight moment but a warm summary was chosen instead?)
   - Is the insight content meaningful, not empty platitudes?

4. Emotion Tag Accuracy
   - Do events tagged with happy/angry emotions actually have corresponding emotion signals in the event data?
   - Does the emotion explanation accurately reflect the context that produced the emotion?

5. Personalization Accuracy
   - For events marked as "personally important", do they genuinely form a meaningful contrast with the user profile?
   - Is the referenced profile information accurate?

6. Media Selection Appropriateness
   - Are selected videos/frames relevant to the event content?
   - Are source video IDs and timestamps valid?
</check_dimensions>

<output_format>
{
  "overall_verdict": "pass / needs_revision",
  "score": 0-100,
  "issues": [
    {
      "severity": "critical / warning / suggestion",
      "dimension": "check dimension",
      "location": "location of issue (e.g., key_events[2].narrative)",
      "description": "issue description",
      "suggestion": "revision suggestion"
    }
  ]
}
</output_format>

<judgment_criteria>
- Any critical issue → needs_revision
- Only warnings or suggestions → pass (with improvement notes)
- Critical: Factual errors, hallucinated content, emotion tags contradicting data
- Warning: Narrative quality issues, inappropriate insight type selection
- Suggestion: Writing style improvements that could be better
</judgment_criteria>
```

</details>

---

#### 节点 4.3: 存储入库

| 属性 | 值 |
|------|-----|
| 模型 | 无（数据库操作） |
| 输入 | 4.2 质量检查结果 + 3.1 画像差异 + DB Session + Profile ID |
| 输出 | `{ status, diary_id, quality_verdict, quality_score }` |

**写入内容**:

1. **日记数据**:
   - 创建 `DiaryEntry` 记录（含洞察、情绪概览、媒体）
   - 创建 `DiaryKeyEvent` 记录（每个关键事件）
   - 创建 `EventMedia` 记录（每个媒体附件）

2. **画像更新**:
   - 应用 3.1 生成的 diff 到数据库
   - 更新 Interest / SocialContact / RecentFocus / Habit 表
   - Profile 版本号 +1

**事务管理**: 使用 `flush()` 而非 `commit()`，由 WorkflowEngine 统一提交整个事务，确保数据一致性。

---

### 3.3 模型分配总览

| 节点 | 模型 | 用途 |
|------|------|------|
| 1.1 视频预处理 | FFmpeg | 音频提取、缩略图、元数据 |
| 1.2 画面理解 | Gemini 2.5 Pro | 多模态视觉分析 |
| 1.3a 说话人分离 | 音频模型 | 说话人分离 |
| 1.3b 语音转文字 | ASR 模型 | 语音转写 |
| 1.3c 情绪识别 | emotion2vec | 音频情绪分析 |
| 2.1 事件结构化 | Claude Opus 4.6 | 碎片合并为事件 |
| 2.2 人物匹配 | Claude Sonnet 4.6 | 人物身份匹配 |
| 3.1 画像更新 | Claude Opus 4.6 | 渐进式画像更新 |
| 3.2 日记生成 | Claude Opus 4.6 | 日记撰写 |
| 4.1 媒体切片 | FFmpeg | 关键帧/片段提取 |
| 4.2 质量检查 | Claude Sonnet 4.6 | 6 维度质量审查 |
| 4.3 存储入库 | 无 | 数据库写入 |

所有 LLM 模型均通过 **ModelGate** 网关（OpenAI 兼容 API）统一调用。

---

## 四、调试面板 (Debug Panel)

Web 端调试工具，用于监控工作流执行、查看节点输入输出、调整模型配置。

### 4.1 界面布局

```
┌─────────────────────────────────────────────────────────┐
│  顶部栏: 日期选择 | 运行选择 | 状态标签 | 进度条        │
├─────────────────────────┬───────────────────────────────┤
│                         │                               │
│    工作流 DAG 视图       │     节点详情面板               │
│    (React Flow)         │     (480px 宽)                │
│                         │                               │
│    12 个节点 + 连线      │     [输入] [输出] [配置]       │
│    实时状态颜色          │                               │
│    动画效果              │                               │
│                         │                               │
└─────────────────────────┴───────────────────────────────┘
```

### 4.2 顶部控制栏

| 控件 | 功能 |
|------|------|
| 日期下拉 | 按日期筛选工作流运行，默认「全部」 |
| 运行下拉 | 选择某次运行（按开始时间倒序） |
| 状态标签 | 显示当前运行状态（pending/running/completed/failed） |
| 进度条 | `已完成节点数 / 12`，运行中时有动画 |
| 运行中提示 | 显示当前正在执行的节点名称和已用时间 |

### 4.3 DAG 视图

以有向无环图展示 12 个节点的依赖关系和执行状态。

**节点状态颜色**:

| 状态 | 颜色 | 视觉效果 |
|------|------|---------|
| pending | 灰色 | 静态 |
| running | 蓝色 | 旋转动画指示器 |
| completed | 绿色 | 显示耗时 |
| failed | 红色 | 显示错误标记 |
| skipped | 黄色 | 跳过标记 |

**交互**:
- 点击节点 → 右侧展示该节点详情
- 选中节点 → 蓝色边框 + 高亮背景
- 运行中的边 → 动画流动效果
- 待执行节点 → 显示「等待: 节点X, 节点Y」

**节点预估耗时**:

| 节点 | 预估耗时 |
|------|---------|
| 1.1 视频预处理 | 5s |
| 1.2 画面理解 | 30s |
| 1.3a 说话人分离 | 3s |
| 1.3b 语音转文字 | 3s |
| 1.3c 情绪识别 | 3s |
| 2.1 事件结构化 | 20s |
| 2.2 人物匹配 | 15s |
| 3.1 画像更新 | 15s |
| 3.2 日记生成 | 25s |
| 4.1 媒体切片 | 5s |
| 4.2 质量检查 | 15s |
| 4.3 存储入库 | 2s |

### 4.4 节点详情面板

选中节点后展示三个 Tab:

#### Tab 1: 输入 (Input)
- 以格式化 JSON 展示节点收到的 `input_data`
- 最大高度 500px，可滚动

#### Tab 2: 输出 (Output)
- 以格式化 JSON 展示节点的 `output_data`
- 如果节点失败，显示红色错误横幅
- 最大高度 500px，可滚动

#### Tab 3: 配置 (Config)

**可配置项**:

| 配置项 | 说明 |
|--------|------|
| 模型选择 | 下拉框，可切换模型 |
| System Prompt | 多行文本编辑器，可修改 LLM 提示词 |

**可选模型列表**:
- Claude-Opus-4.6
- Claude-Sonnet-4.6
- Claude-Haiku-4.5
- Gemini-2.5-Pro
- Gemini-2.5-Flash
- GPT-4.1

**操作按钮**:
- 「保存配置」: 保存模型和 Prompt 修改到数据库
- 「重新运行此节点」: 使用当前配置重新执行该节点

**配置三层结构**:
- **默认值 (defaults)**: 代码中注册的默认模型和 Prompt
- **覆盖值 (overrides)**: 用户通过面板修改的值
- **生效值 (effective)**: 覆盖值 > 默认值

**反馈**:
- 重跑成功: 显示绿色 ✓ 重跑成功
- 重跑失败: 显示红色 ✕ 重跑失败

#### 节点头部信息

| 信息 | 说明 |
|------|------|
| 节点名称 | 如「1.2 画面理解」 |
| 状态图标 | ✅ 完成 / ❌ 失败 / 🔄 运行中 / ⏳ 等待 |
| 耗时 | X.XX 秒 |
| Token 用量 | 如「12,345 tokens」 |
| 节点说明 | 功能描述文字 |
| 等待信息 | 待执行时显示未完成的上游依赖 |

### 4.5 轮询机制

| 场景 | 轮询间隔 |
|------|---------|
| 有节点处于 running 状态 | 2 秒 |
| 所有节点完成或空闲 | 5 秒 |

**自动行为**:
- 新运行出现时自动选中最新的运行
- 工作流状态变化时自动刷新 DAG

---

## 五、数据模型总览

### 5.1 ER 关系图

```
UserProfile (1) ──> (N) SocialContact
             (1) ──> (N) Interest
             (1) ──> (1) WeekdayHabit
             (1) ──> (1) WeekendHabit
             (1) ──> (1) GeneralHabit
             (1) ──> (N) RecentFocus
             (1) ──> (N) DiaryEntry
             (1) ──> (N) UploadedVideo
             (1) ──> (N) UploadBatch
             (1) ──> (N) WorkflowRun
             (1) ──> (N) NodeConfig

DiaryEntry (1) ──> (N) DiaryKeyEvent
DiaryKeyEvent (1) ──> (N) EventMedia

UploadBatch (1) ──> (1) WorkflowRun
WorkflowRun (1) ──> (N) NodeRun
```

### 5.2 核心表字段速查

#### diary_entries

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| profile_id | UUID | 关联用户 |
| diary_date | date? | 日记日期，可为空 |
| diary_date_unknown | bool | 日期是否未知 |
| insight_type | str | highlight / observation / summary |
| insight_text | text | 洞察正文 |
| insight_media_type | str? | keyframe / video_clip |
| insight_media_url | str? | 洞察配图 URL |
| insight_media_thumbnail_url | str? | 洞察配图缩略图 |
| happy_minutes | float | 开心时长（分钟） |
| angry_minutes | float | 生气时长（分钟） |
| calm_minutes | float | 平静时长（分钟） |
| source_video_count | int | 源视频数量 |
| total_source_duration_seconds | float | 源视频总时长 |
| profile_version | int | 生成时的画像版本 |
| generated_at | datetime | 生成时间 |

#### diary_key_events

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| diary_id | UUID | 关联日记 |
| start_time | str? | 开始时间 HH:MM |
| end_time | str? | 结束时间 HH:MM |
| title | str | 事件标题 |
| narrative | text | 第二人称叙事 |
| importance_type | str | objective / personalized / duration_based |
| emotion_tag | str? | happy / angry / null |
| emotion_note | text? | 情绪备注 |
| tags | json | 标签列表 |
| related_person_ids | json | 关联的社交联系人 ID |

#### event_media

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| event_id | UUID | 关联事件 |
| media_type | str | keyframe / video_clip |
| url | str | 媒体文件 URL |
| thumbnail_url | str? | 缩略图 URL |
| source_video_id | str? | 源视频 ID（调试用） |
| source_timestamp | float? | 关键帧时间戳 |
| clip_start | float? | 片段开始时间 |
| clip_end | float? | 片段结束时间 |

#### user_profiles

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| nickname | str? | 昵称 |
| gender | str? | male / female / undisclosed |
| age_range | str? | 年龄段 |
| occupation | str? | 职业 |
| city | str? | 城市 |
| dietary_tags | json | 饮食标签 |
| daily_calorie_goal | int? | 每日卡路里目标 |
| version | int | 画像版本号（每次工作流 +1） |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 最后更新时间 |

---

## 六、API 接口汇总

### 6.1 App 端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/profile/` | 创建用户 Profile |
| GET | `/api/profile/{profile_id}` | 获取完整 Profile |
| PATCH | `/api/profile/{profile_id}` | 更新基本信息 |
| PATCH | `/api/profile/{profile_id}/contacts/{contact_id}` | 更新联系人 |
| GET | `/api/diary/{profile_id}/list` | 日记列表（支持日期筛选、分页） |
| GET | `/api/diary/{profile_id}/dates` | 获取有日记的日期列表 |
| GET | `/api/diary/detail/{diary_id}` | 获取日记详情 |
| POST | `/api/upload/video` | 上传单个视频 |
| POST | `/api/upload/batch` | 创建批次并触发工作流 |

### 6.2 Debug 面板 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/debug/{profile_id}/runs` | 工作流运行列表 |
| GET | `/api/debug/{profile_id}/dates` | 运行日期列表 |
| GET | `/api/debug/node/{node_run_id}` | 节点运行详情 |
| GET | `/api/debug/{profile_id}/config/{node_id}` | 获取节点配置 |
| PUT | `/api/debug/{profile_id}/config/{node_id}` | 更新节点配置 |
| POST | `/api/debug/rerun` | 重跑单个节点 |
| GET | `/api/debug/nodes` | 所有已注册节点列表 |

---

## 七、部署架构

### 7.1 服务组件

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL 16 | 5432 | 数据存储 |
| Redis 7 | 6379 | Celery 消息队列 |
| FastAPI Server | 8000 | API 服务 + 静态媒体文件 |
| Celery Worker | — | 异步执行 12 节点工作流 |
| Web (Nginx) | 3000 | Debug 面板前端 |

### 7.2 云服务器

| 项目 | 值 |
|------|-----|
| 云服务商 | 火山引擎 |
| 规格 | 2C4G, 40GB SSD, 5Mbps |
| 地域 | 华东2（上海） |
| 公网 IP | 14.103.43.132 |
| 操作系统 | Ubuntu 24.04 |

### 7.3 LLM 网关

所有大模型调用通过 ModelGate（`https://mg.aid.pub/v1`）统一代理，支持 OpenAI 兼容协议。可在 Debug 面板中热切换模型，无需重启服务。

---

## 八、已知限制与待办

| 编号 | 问题 | 状态 |
|------|------|------|
| 1 | 日记详情页：洞察封面图 (`insight_media_url`) 未渲染 | 待修复 |
| 2 | 日记详情页：`related_person_ids` 未展示关联人物 | 待修复 |
| 3 | 日记详情页：视频片段无法播放，仅显示静态图 | 待修复 |
| 4 | 上传依赖手动操作，无自动同步相册功能 | 待开发 |
| 5 | 纯图片理解未支持（当前仅处理视频） | 待开发 |
