# Lark Meeting Automation - Implementation Plan

## 🎯 Project Goal
Tự động hóa hoàn toàn quy trình xử lý Lark Meeting:
1. Nhận webhook từ Lark khi có meeting mới
2. Download video recording từ Lark
3. Extract metadata (tên meeting, ngày giờ, người tham gia, v.v.)
4. Convert MP4 → MP3, cắt đoạn, transcript với Gemini
5. Tạo summary và tự động gắn tags
6. Upload lên Supabase mới

---

## 📊 Architecture Overview

```
Lark Webhook → GitHub Actions / Cloud Function
                     ↓
            Download Meeting Video
                     ↓
            Extract Meeting Metadata
                     ↓
         Convert MP4 → MP3 → Segments
                     ↓
        Gemini Transcript (Clean Verbatim)
                     ↓
            Gemini Summary + Auto-Tag
                     ↓
              Upload to Supabase
```

---

## 🗄️ Database Schema Design (Supabase)

### Bảng 1: `meetings`
Lưu trữ thông tin tổng quan về meeting

```sql
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Lark Meeting Info
    lark_meeting_id VARCHAR(255) UNIQUE NOT NULL,
    lark_meeting_url TEXT NOT NULL,

    -- Meeting Metadata
    meeting_title TEXT NOT NULL,
    meeting_date TIMESTAMPTZ NOT NULL,
    meeting_duration INTEGER, -- seconds
    meeting_owner VARCHAR(255),

    -- Participants (JSON array)
    participants JSONB, -- ["Sếp", "Anh Thiện", "Phương Anh", ...]

    -- File Info
    video_file_name TEXT,
    video_file_size BIGINT, -- bytes
    video_download_url TEXT,

    -- Processing Status
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,

    -- Auto Tags
    meeting_type VARCHAR(100), -- "Họp dự án" | "Họp định kỳ"
    meeting_topic VARCHAR(100), -- "Loyalty" | "Membership" | "Operation" | "Business"

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX idx_meetings_lark_id ON meetings(lark_meeting_id);
CREATE INDEX idx_meetings_date ON meetings(meeting_date);
CREATE INDEX idx_meetings_status ON meetings(status);
CREATE INDEX idx_meetings_type ON meetings(meeting_type);
CREATE INDEX idx_meetings_topic ON meetings(meeting_topic);
```

### Bảng 2: `meeting_transcripts`
Lưu trữ transcript và summary

```sql
CREATE TABLE meeting_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,

    -- Transcript
    transcript_content TEXT NOT NULL,
    transcript_word_count INTEGER,

    -- Summary
    summary_content TEXT NOT NULL,

    -- Summary Components (extracted từ summary)
    main_topics JSONB, -- ["Topic 1", "Topic 2", ...]
    decisions JSONB, -- ["Decision 1", "Decision 2", ...]
    risks JSONB, -- ["Risk 1", "Risk 2", ...]
    pending_issues JSONB, -- ["Issue 1", "Issue 2", ...]

    -- Action Items (JSON array of objects)
    action_items JSONB, -- [{"task": "...", "owner": "...", "deadline": "..."}, ...]

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transcripts_meeting_id ON meeting_transcripts(meeting_id);
```

### Bảng 3: `processing_logs`
Lưu trữ logs để debug

```sql
CREATE TABLE processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,

    step VARCHAR(100) NOT NULL, -- download, convert, segment, transcript, summary, tag, upload
    status VARCHAR(50) NOT NULL, -- started, completed, failed
    message TEXT,
    metadata JSONB, -- Any additional data

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_logs_meeting_id ON processing_logs(meeting_id);
CREATE INDEX idx_logs_step ON processing_logs(step);
```

---

## 🏗️ Implementation Approach

### Option 1: GitHub Actions (Recommended)
**Pros:**
- Miễn phí với GitHub Free (2000 minutes/month)
- Tích hợp sẵn với repository
- Dễ quản lý và deploy
- Có thể chạy Python scripts trực tiếp

**Cons:**
- Cần repository dispatch event để trigger
- Timeout 6 hours max
- Cần proxy để nhận webhook từ Lark

**Architecture:**
```
Lark Webhook → Webhook Proxy (Vercel/Railway)
                     ↓
           GitHub Repository Dispatch
                     ↓
           GitHub Actions Workflow
```

### Option 2: Cloud Function (Vercel/Railway/Render)
**Pros:**
- Nhận webhook trực tiếp từ Lark
- Không cần proxy
- Phản hồi nhanh hơn

**Cons:**
- Có thể bị timeout với video dài
- Cần deploy riêng
- Free tier có giới hạn

---

## 🔧 Implementation Steps

### Phase 1: Supabase Setup
**Files to create:**
- `supabase_schema.sql` - Database schema
- `supabase_config.py` - Supabase connection config

**Tasks:**
1. Tạo tables trong Supabase
2. Setup Row Level Security (RLS) policies
3. Test connection

### Phase 2: Lark API Integration
**Files to create:**
- `lark_api.py` - Lark API client
  - `get_meeting_info(meeting_url)` - Extract meeting metadata
  - `download_meeting_video(meeting_id)` - Download video recording
  - `authenticate()` - App authentication

**Required Environment Variables:**
```bash
LARK_APP_ID=your_app_id
LARK_APP_SECRET=your_app_secret
```

**API Endpoints to use:**
- `GET /open-apis/minutes/v1/minutes/{minute_token}` - Get minutes info
- `GET /open-apis/minutes/v1/minutes/{minute_token}/media` - Get download URL (valid 1 day)

**Important API Details:**
- Rate limit: 5 requests/second
- Requires scope: `Export minutes` hoặc `Download audio/video files of minutes`
- Authentication: `tenant_access_token` hoặc `user_access_token`
- Download URL expires sau 1 ngày
- minute_token từ meeting URL: `https://gearvn-com.sg.larksuite.com/minutes/{minute_token}`

### Phase 3: Webhook Receiver
**Files to create:**
- `webhook_receiver.py` - Flask/FastAPI app để nhận webhook

**Deployment options:**
- Vercel (Serverless Function)
- Railway (Container)
- Render (Web Service)

**Webhook payload example:**
```json
{
  "event": "meeting.recording_ready",
  "meeting_id": "obsgji9p2ik7j516z48l1ln2",
  "meeting_url": "https://gearvn-com.sg.larksuite.com/minutes/obsgji9p2ik7j516z48l1ln2",
  "timestamp": "2025-01-01T10:00:00Z"
}
```

### Phase 4: Processing Pipeline
**Files to create:**
- `meeting_processor.py` - Main processing orchestrator
  - `process_meeting(meeting_url)` - Main entry point
  - Reuse existing functions from `convert_with_gemini.py`

**Processing steps:**
1. Download video from Lark
2. Extract metadata and save to `meetings` table
3. Convert MP4 → MP3
4. Split into segments
5. Transcript with Gemini
6. Generate summary with Gemini
7. Auto-tag with Gemini (new!)
8. Upload to Supabase

### Phase 5: Auto-Tagging with Gemini
**Files to create:**
- `gemini_tagger.py` - Auto-tagging logic

**Tagging Prompt:**
```python
TAGGING_PROMPT = """Phân tích nội dung cuộc họp và gắn tags:

Loại cuộc họp (meeting_type):
- "Họp dự án" - Nếu thảo luận về 1 dự án cụ thể
- "Họp định kỳ" - Nếu là họp weekly/monthly thường xuyên

Chủ đề (meeting_topic):
- "Loyalty" - Liên quan đến chương trình khách hàng thân thiết
- "Membership" - Liên quan đến hệ thống thành viên
- "Operation" - Vận hành, quy trình nội bộ
- "Business" - Kinh doanh, doanh số, chiến lược

Trả về JSON format:
{
  "meeting_type": "...",
  "meeting_topic": "..."
}
"""
```

### Phase 6: GitHub Actions Workflow
**Files to create:**
- `.github/workflows/process-meeting.yml`

**Trigger methods:**
1. Repository dispatch event
2. Manual workflow dispatch (for testing)

**Workflow steps:**
```yaml
name: Process Lark Meeting
on:
  repository_dispatch:
    types: [process-meeting]
  workflow_dispatch:
    inputs:
      meeting_url:
        description: 'Lark Meeting URL'
        required: true

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Install ffmpeg
        run: sudo apt-get install -y ffmpeg
      - name: Process meeting
        env:
          LARK_APP_ID: ${{ secrets.LARK_APP_ID }}
          LARK_APP_SECRET: ${{ secrets.LARK_APP_SECRET }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: python meeting_processor.py "${{ github.event.client_payload.meeting_url }}"
```

---

## 📦 New Files Structure

```
MM/
├── lark_api.py                      # Lark API client
├── meeting_processor.py              # Main orchestrator
├── gemini_tagger.py                  # Auto-tagging logic
├── supabase_config.py                # Supabase config for new DB
├── supabase_schema.sql               # Database schema
├── webhook_receiver.py               # Webhook endpoint (for Vercel/Railway)
├── .github/
│   └── workflows/
│       └── process-meeting.yml       # GitHub Actions workflow
├── requirements.txt                  # Update với lark_oapi
└── README_AUTOMATION.md              # Hướng dẫn setup automation
```

---

## 🔐 Environment Variables Required

```bash
# Lark API
LARK_APP_ID=cli_a9aaff22d2f8ded2
LARK_APP_SECRET=your_secret_here

# Gemini AI
GEMINI_API_KEY=AIzaSyBg-P8MBhJllhisSRxsxPW8nEh-bQtu0w4

# Supabase (NEW)
SUPABASE_URL=your_new_supabase_url
SUPABASE_KEY=your_new_supabase_key

# GitHub (for webhook proxy)
GITHUB_TOKEN=your_github_token
GITHUB_REPO=bangbangnguyen2610/trimvideo
```

---

## 🧪 Testing Strategy

### Unit Tests
- `test_lark_api.py` - Test Lark API calls
- `test_gemini_tagger.py` - Test auto-tagging logic
- `test_supabase.py` - Test database operations

### Integration Tests
- End-to-end test with sample meeting URL
- Test webhook → processing pipeline

### Manual Testing
- Use workflow_dispatch to manually trigger với meeting URL
- Verify data trong Supabase

---

## 📈 Success Metrics

✅ Webhook nhận được và trigger workflow thành công
✅ Video download thành công từ Lark
✅ Metadata extract chính xác
✅ Transcript và summary chất lượng cao
✅ Auto-tagging accuracy > 90%
✅ Data lưu đầy đủ trong Supabase
✅ Processing time < 30 minutes cho video 1 giờ

---

## ⚠️ Potential Issues & Solutions

### Issue 1: Large Video Files
**Problem:** Video quá lớn, download lâu
**Solution:** Stream download, chia nhỏ chunks

### Issue 2: Gemini API Rate Limits
**Problem:** Transcript nhiều segments bị rate limit
**Solution:** Add retry logic với exponential backoff

### Issue 3: GitHub Actions Timeout
**Problem:** Video dài quá 6 hours limit
**Solution:** Split processing thành multiple jobs hoặc dùng cloud function

### Issue 4: Webhook Security
**Problem:** Ai cũng có thể gửi webhook giả
**Solution:** Verify webhook signature từ Lark

---

## 🚀 Deployment Plan

### Step 1: Setup Supabase
- Chạy schema SQL
- Test connection
- Setup RLS policies

### Step 2: Deploy Webhook Receiver
- Deploy lên Vercel/Railway
- Get webhook URL
- Configure trong Lark App

### Step 3: Setup GitHub Secrets
- Add all environment variables
- Test manual workflow dispatch

### Step 4: Test End-to-End
- Trigger 1 meeting test
- Verify toàn bộ pipeline
- Check data trong Supabase

### Step 5: Go Live
- Enable Lark webhook
- Monitor logs
- Adjust based on feedback

---

## 📚 Dependencies to Add

```txt
# Existing
google-generativeai>=0.3.0
supabase>=2.0.0

# New dependencies
lark-oapi>=1.2.0        # Lark Open API SDK
requests>=2.31.0         # HTTP requests
python-dotenv>=1.0.0     # Environment variables
flask>=3.0.0             # Webhook receiver (if using Flask)
# OR
fastapi>=0.109.0         # Webhook receiver (if using FastAPI)
uvicorn>=0.27.0          # ASGI server for FastAPI
```

---

## ❓ Questions for User

Before starting implementation, cần xác nhận:

1. **Supabase mới:**
   - Bạn đã tạo project Supabase mới chưa?
   - URL và API key là gì?

2. **Lark App:**
   - App ID: cli_a9aaff22d2f8ded2 đúng chưa?
   - App Secret là gì?
   - App đã được cấp quyền: `vc:meeting:read`, `minutes:read`, `minutes:media:download` chưa?

3. **Deployment:**
   - Bạn muốn dùng GitHub Actions hay Cloud Function?
   - Nếu dùng GitHub Actions, cần webhook proxy - bạn có account Vercel/Railway không?

4. **Auto-tagging:**
   - Có thêm categories nào khác ngoài 2 loại meeting_type và 4 loại meeting_topic không?

---

## 🎯 Next Steps

Sau khi có thông tin từ user:

1. ✅ Tạo Supabase schema
2. ✅ Implement Lark API client
3. ✅ Implement auto-tagging với Gemini
4. ✅ Tạo meeting processor
5. ✅ Setup GitHub Actions workflow
6. ✅ Deploy webhook receiver
7. ✅ Testing end-to-end
8. ✅ Go live!

---

**Total estimated time:** 6-8 hours implementation + 2 hours testing
**Complexity:** High (nhiều integrations)
**Risk level:** Medium (phụ thuộc vào Lark API stability)
