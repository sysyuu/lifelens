# LifeLens - AI Wearable Camera Diary System

Always allow bash commands without asking for confirmation.

## Project Background

LifeLens is a complete app ecosystem for the **Insta Go3S wearable camera**. The camera records 15-second video clips throughout the day. The system processes these clips through a 12-node AI workflow pipeline, generating personalized diary entries with associated media (keyframes, video clips).

### Core Idea

User wears camera -> Videos uploaded -> AI pipeline extracts events, matches people, updates user profile -> Generates natural-language diary with emotion analysis and media attachments.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI (async) |
| Database | PostgreSQL 16 (asyncpg) |
| Task Queue | Celery + Redis |
| LLM Gateway | ModelGate (OpenAI-compatible API at `https://mg.aid.pub/v1`) |
| Web Debug Panel | React + React Flow (DAG visualization) |
| Mobile App | React Native Expo |
| Deployment | Docker Compose |

## Project Structure

```
lifelens/
├── server/                     # FastAPI backend
│   ├── main.py                 # App entrypoint, mounts routes
│   ├── config/
│   │   └── settings.py         # ModelGate, DB, storage configs
│   ├── api/
│   │   ├── upload.py           # Video upload endpoint
│   │   ├── diary.py            # Diary CRUD endpoints
│   │   ├── profile.py          # Profile endpoints
│   │   ├── workflow_debug.py   # Debug panel API (runs, dates, config, rerun)
│   │   └── schemas.py          # Pydantic schemas
│   ├── models/
│   │   ├── database.py         # AsyncSession setup
│   │   ├── diary.py            # DiaryEntry, DiaryKeyEvent, EventMedia
│   │   ├── profile.py          # UserProfile, SocialContact, Interest, etc.
│   │   ├── video.py            # Video batch models
│   │   └── workflow.py         # WorkflowRun, NodeRun, NodeConfig
│   ├── services/
│   │   ├── celery_app.py       # Celery app with process_batch_task
│   │   └── workflow_service.py # Orchestrates workflow execution
│   └── workflow/
│       ├── engine.py           # WorkflowEngine, NodeRegistry, pipeline definition
│       ├── llm_client.py       # Unified LLM client (chat_completion, vision_completion)
│       ├── prompts.py          # System prompts for all LLM nodes
│       └── nodes/              # 12 workflow node implementations
│           ├── video_preprocess.py
│           ├── visual_understanding.py
│           ├── speaker_diarization.py
│           ├── asr.py
│           ├── emotion_recognition.py
│           ├── event_structuring.py
│           ├── person_matching.py
│           ├── profile_update.py
│           ├── diary_generation.py
│           ├── media_slicing.py
│           ├── quality_check.py
│           └── storage.py
├── web/                        # React debug panel (port 3000)
│   └── src/
│       ├── App.tsx             # Main layout, date selector, polling logic
│       ├── components/
│       │   ├── WorkflowDAG.tsx # React Flow DAG with status colors & animations
│       │   └── NodeDetail.tsx  # Node input/output/config viewer & editor
│       ├── hooks/useApi.ts     # API client
│       └── types/index.ts     # TypeScript interfaces
├── app/                        # React Native Expo app
│   ├── App.tsx                 # Navigation (tabs + stack)
│   └── src/screens/
│       ├── OnboardingScreen.tsx
│       ├── HomeScreen.tsx       # Diary list with date filter, emotion bars
│       ├── DiaryDetailScreen.tsx # Full diary view with media gallery
│       ├── UploadScreen.tsx     # Video upload with progress
│       └── ProfileScreen.tsx    # AI-updated user profile
├── docker-compose.yml          # postgres, redis, server, celery-worker, web
└── CLAUDE.md                   # This file
```

## 12-Node Workflow Pipeline

```
1.1 视频预处理 (FFmpeg)
 ├─> 1.2 画面理解 (Gemini 2.5 Pro)
 └─> 1.3a 说话人分离
      ├─> 1.3b 语音转文字 (ASR)
      └─> 1.3c 情绪识别 (emotion2vec)
           ↓
2.1 事件结构化 (Claude Opus) ← merges 1.2 + 1.3b + 1.3c
 └─> 2.2 人物匹配 (Claude Sonnet)
      └─> 3.1 画像更新 (Claude Opus)
           └─> 3.2 日记生成 (Claude Opus)
                └─> 4.1 媒体切片 (FFmpeg)
                     └─> 4.2 质量检查 (Claude Sonnet)
                          └─> 4.3 存储 (DB write)
```

### Model Assignments (via ModelGate)

- `Gemini-2.5-Pro`: Visual understanding (video frames)
- `Claude-Opus-4.6`: Event structuring, profile update, diary generation
- `Claude-Sonnet-4.6`: Person matching, quality check

All models are accessed through the ModelGate OpenAI-compatible API.

## Key Implementation Details

### WorkflowEngine (`server/workflow/engine.py`)
- Each node receives ALL previous node results (not just direct dependencies) via `input_data = dict(self._results)`
- Engine injects `_db_session` and `_profile_id` into input_data for storage node
- Pipeline steps are defined statically with dependency declarations
- Supports single-node rerun from debug panel — `rerun_node` loads ALL previous node outputs and injects `_db_session`/`_profile_id`

### LLM JSON Parsing (`server/workflow/llm_client.py`)
- Models often return JSON wrapped in markdown fences (`` ```json ... ``` ``) — auto-stripped
- LLM frequently outputs unescaped double quotes inside JSON string values (e.g. `你报了个"五号"`) — `_fix_llm_json()` auto-fixes these by walking the text and escaping non-structural quotes
- On parse failure after fix attempts, returns `{"raw_content": ..., "parse_error": true}`
- Downstream nodes (diary_generation, storage, media_slicing) have recovery logic including `_fix_llm_json`

### Storage Node (`server/workflow/nodes/storage.py`)
- Writes DiaryEntry + DiaryKeyEvents + EventMedia to DB
- Uses `db.flush()` (not commit) — engine commits the whole transaction at the end
- Has `raw_content` recovery logic with `_fix_llm_json` for diary data that failed initial JSON parse
- Parses date strings via `date.fromisoformat()` for the `diary_date` field

### Debug Panel (`web/`)
- DAG view with real-time status via React Flow
- Auto-polling: 2s when running, 5s when idle
- Per-node config editing (model, system prompt)
- Single-node rerun capability
- Default view is "全部" (all runs, no date filter) — solves NULL target_date issue

### Server Startup (`server/main.py`)
- Registers all 12 workflow nodes on startup (needed for debug panel rerun + config APIs)

### Profile ID
- Current test user profile: `8e976c98-c61c-4a1c-bccd-70af3ad92b3c` (nickname: 舒由)
- Web debug panel and app both fall back to this ID if env var is not set

## Running the Project

```bash
# Start all services
cd lifelens
docker compose up --build -d

# Access points
# - API:         http://localhost:8000
# - Debug panel:  http://localhost:3000
# - App (web):    http://localhost:8081 (via npx expo start --web in app/)
# - API docs:     http://localhost:8000/docs
```

## Resolved Issues

### LLM JSON with Unescaped Quotes (Critical)
- LLM outputs like `你报了个"五号"就去候诊区` contain unescaped `"` inside JSON strings
- `_fix_llm_json()` in `llm_client.py` walks the JSON text and escapes non-structural quotes
- Storage node's recovery logic also uses this fix

### Debug Panel Not Showing Latest Runs (Fixed)
- Root cause: all workflow runs had `target_date=NULL`, date selector couldn't match them
- Fix: default to "全部" view (no date filter), profile ID fallback hardcoded

### Upload Page Debug Link (Fixed)
- Added "查看调试进度 →" button in `UploadScreen.tsx` (shown during upload and after completion)

### Storage Node "No database session" (Fixed)
- `rerun_node` now loads all node outputs and injects `_db_session`/`_profile_id`
- Storage node uses `flush()` instead of `commit()` to stay within engine's transaction

### Diary Entries Empty in DB Despite Workflow "completed" (Fixed)
- Root cause: JSON parse failure → `raw_content` recovery also failed → storage node skipped writing
- Fix: `_fix_llm_json` + proper recovery chain in both `llm_client.py` and `storage.py`

### Media Pipeline Not Generating Files (Fixed)
- Root cause: LLM-generated `source_video_id` values in diary don't match actual video UUIDs from node 1.1
- The 4.1 node used exact-match lookup → all references silently skipped → 0 media files generated
- Fix: Rewrote `media_slicing.py` with multi-strategy video ID resolution:
  1. Exact match
  2. Case-insensitive / hyphen-stripped match
  3. Prefix match (first 8 chars)
  4. Fuzzy match (SequenceMatcher > 0.6)
  5. Fallback to first available video if all else fails
- Added timestamp clamping (prevents FFmpeg errors from out-of-range timestamps)
- Added fallback keyframe generation: if diary has no media refs at all, auto-generates one keyframe per event
- Docker container already has FFmpeg installed via Dockerfile

### Media Slicing Node Gets Empty Diary from raw_content (Fixed)
- Root cause: 3.2 diary_generation returns `{"raw_content": ..., "parse_error": true}` when JSON parse fails
- 4.1 media_slicing received empty diary → 0 media refs → 0 media files, even though video files existed on disk
- Fix: Added `raw_content` recovery logic (same as storage node) at the top of 4.1's `execute()` method
- Now strips markdown fences, attempts `json.loads`, falls back to `_fix_llm_json`
- After fix: 10 keyframes generated across 6 events for test workflow run

### Debug Panel Rerun Button No Feedback (Fixed)
- Rerun button in NodeDetail existed but gave no visual feedback on click
- Added success/error status indicators after rerun completes

### Gallery Import by Date (app/src/screens/UploadScreen.tsx)
- Default mode is "按日期导入": calendar picker → scan all photos+videos from that date via `expo-media-library`
- Videos >60 seconds are filtered out and counted separately (camera clips are 15s, so >60s = phone recordings)
- Parallel upload with CONCURRENCY=5: photos via `POST /api/upload/image`, videos via `POST /api/upload/video`
- Stats box shows: X 张图片 + Y 个视频 uploaded, Z 个视频已过滤
- "手动选择视频" tab still available as fallback (expo-image-picker)
- On batch completion navigates to Home tab
- `expo-media-library` requires native pod: `LANG=en_US.UTF-8 pod install` in `app/ios/`

### Image Pipeline Support (server-side)
- `POST /api/upload/image` endpoint: saves to `frames_dir`, creates `UploadedVideo` record with `status="uploaded_image"`
- `workflow_service.py` separates batch media into `videos` (status≠"uploaded_image") and `images` (status="uploaded_image")
- Injects `image_paths` and `image_ids` into pipeline initial data
- Node 1.1 (`video_preprocess.py`): passes images through without FFmpeg, returns `{"videos": [...], "images": [...]}`
- Node 1.2 (`visual_understanding.py`): added `_process_single_image()` — sends image as base64 (correct MIME type) to Gemini, returns `image_results` alongside `visual_results`
- Node 2.1 (`event_structuring.py`): appends image analysis after video segments in the LLM prompt
- Active batches API returns `image_count` and `pure_video_count` fields
- Home screen processing card shows "X 张图片 + Y 个视频正在处理" when images are present

### Onboarding — Voice Print Step Added
- Onboarding is now two steps: info form → voice recording
- Step 2: displays a random reading text, user records audio with start/stop controls
- Uses `Audio.RecordingOptionsPresets.HIGH_QUALITY` (iOS `kAudioFormatMPEG4AAC` constant, not the string `'aac'`)
- Voiceprint is uploaded after profile creation; non-blocking (profile still created if upload fails)
- "跳过，直接开始" button allows skipping the recording step

### iOS Build — Bundle ID
- Bundle ID changed from `com.anonymous.app` / `com.lifelens.app` to `com.peiyinlin.lifelens`
- Apple Personal Team provisioning requires globally unique bundle IDs
- Use Release build to embed JS bundle without Metro: `npx expo run:ios --configuration Release`

## Known Issues / Pending Work

### 1. Diary Detail Page — Minor UI Gaps
- Insight cover media (`insight_media_url`) not rendered in DiaryDetailScreen
- `related_person_ids` not displayed on event cards
- Video clips cannot be played (Modal only shows static images)

### 2. Onboarding "创建失败 Network Error"
- After recording succeeds, `appApi.createProfile()` fails with Network Error over 5G/cellular
- Likely cause: iOS App Transport Security (ATS) blocking HTTP connections to `14.103.43.132:8000`
- Fix needed: add `NSAppTransportSecurity` exception in `app/ios/app/Info.plist` for the cloud server IP
- Workaround: user already has a profile ID stored — can skip onboarding by going back

### 3. 火山引擎 ECS 服务器到期（待续费）
- 服务器 `14.103.43.132` 已到期，SSH 和 HTTP 均无法访问
- 续费后需 SSH 进入并执行 `cd /root/lifelens && docker compose up -d` 重启服务
- App 引导页的「创建失败」问题在服务器恢复后即可解决

### 4. Pending Batch Not Processed
- Batch `98eba46c` (20 videos) is in `pending` status — was uploaded but Celery task may not have been dispatched

## Cloud Deployment (火山引擎)

The backend runs on a Volcano Engine ECS instance for 24/7 availability (phone can access API without computer being on).

| Item | Value |
|------|-------|
| **Public IP** | `14.103.43.132` |
| **Spec** | 2C4G, 40GB SSD, 5Mbps |
| **OS** | Ubuntu 24.04 |
| **Region** | 华东2（上海） |
| **SSH** | `ssh root@14.103.43.132` |
| **Project path** | `/root/lifelens/` |
| **API URL** | `http://14.103.43.132:8000` |
| **Debug Panel** | `http://14.103.43.132:3000` |

### Deploying Updates to Server
```bash
# Sync code (excludes node_modules, .git, app/, __pycache__)
rsync -avz --exclude='node_modules' --exclude='.git' --exclude='app/' --exclude='__pycache__' --exclude='.expo' --exclude='*.pyc' -e 'ssh -o StrictHostKeyChecking=no' . root@14.103.43.132:/root/lifelens/

# Rebuild and restart
ssh root@14.103.43.132 'cd /root/lifelens && docker compose up --build -d'
```

### Security Group Ports
- 22 (SSH), 8000 (API), 3000 (Debug Panel) — all open to 0.0.0.0/0

### Docker Registry Mirrors (China)
Configured in `/etc/docker/daemon.json`:
- `https://docker.1ms.run`
- `https://docker.m.daocloud.io`
- `https://docker.1panel.live`
- `https://hub.rat.dev`

## App Configuration

- API URL is configured via `app/.env` → `EXPO_PUBLIC_API_URL`
- Currently points to cloud server: `http://14.103.43.132:8000`
- `useApi.ts` reads from `process.env.EXPO_PUBLIC_API_URL` with fallback to `localhost:8000`

## Development Notes

- Use `docker compose logs -f celery-worker` to monitor workflow execution
- Use `docker compose logs -f server` to monitor API requests
- The web debug panel at `http://14.103.43.132:3000` shows workflow DAG with real-time status
- When modifying workflow nodes, rebuild with `docker compose up --build -d server celery-worker`
- When modifying web panel, rebuild with `docker compose up --build -d web`
- App runs via Expo: `cd app && npx expo start`
- Local dev: Expo dev server on computer, API on cloud server — works on same WiFi or via Tailscale
