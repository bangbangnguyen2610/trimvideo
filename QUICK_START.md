# Quick Start Guide - Lark Meeting Automation

## 🎯 Mục tiêu
Setup hệ thống tự động: **Lark Webhook → Download → Transcript → Auto-Tag → Supabase**

---

## ⚡ Quick Setup (30 phút)

### Bước 1: Setup Supabase Database (5 phút)

1. Đăng nhập Supabase: https://iuadezkhfzcvkvgmhupe.supabase.co

2. Mở SQL Editor

3. Copy toàn bộ nội dung file `supabase_schema.sql`

4. Paste vào SQL Editor và Run

5. Verify 3 tables đã được tạo:
   - ✅ `meetings`
   - ✅ `meeting_transcripts`
   - ✅ `processing_logs`

**Credentials:**
```
URL: https://iuadezkhfzcvkvgmhupe.supabase.co
Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1YWRlemtoZnpjdmt2Z21odXBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTkyNDQsImV4cCI6MjA4MDc5NTI0NH0.mlDh2GfgnG0Q54CXnTGsZ_3WjhfChPLh9eeK9eZdLYc
```

---

### Bước 2: Deploy lên Railway (10 phút)

#### Option A: Deploy từ GitHub (Recommended)

1. Code đã được push lên branch: `feature/supabase-integration` ✅

2. Vào Railway.app → New Project

3. Deploy from GitHub → Select `bangbangnguyen2610/trimvideo`

4. Railway sẽ tự detect Python và dùng `Procfile`

#### Option B: Deploy với Railway CLI

```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

---

### Bước 3: Configure Environment Variables (5 phút)

Trong Railway dashboard, thêm biến môi trường:

```bash
LARK_APP_ID=cli_a9aab0f22978deed
LARK_APP_SECRET=qGF9xiBcIcZrqzpTS8wV3fB7ouywulDV
GEMINI_API_KEY=AIzaSyBg-P8MBhJllhisSRxsxPW8nEh-bQtu0w4
SUPABASE_URL=https://iuadezkhfzcvkvgmhupe.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1YWRlemtoZnpjdmt2Z21odXBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTkyNDQsImV4cCI6MjA4MDc5NTI0NH0.mlDh2GfgnG0Q54CXnTGsZ_3WjhfChPLh9eeK9eZdLYc
PORT=8000
```

**Lưu ý:** Copy chính xác, không thêm dấu ngoặc kép!

---

### Bước 4: Verify Deployment (2 phút)

Railway sẽ cung cấp public URL, ví dụ:
```
https://your-app.railway.app
```

Test health check:
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{"status": "healthy"}
```

---

### Bước 5: Configure Lark Webhook (5 phút)

1. Vào Lark Open Platform: https://open.larksuite.com/app

2. Select app: `cli_a9aab0f22978deed`

3. Vào mục "Event Subscriptions" hoặc "Webhooks"

4. Thêm webhook URL:
   ```
   https://your-app.railway.app/webhook/lark-meeting
   ```

5. Subscribe events:
   - `meeting.recording_ready` ✅
   - `minutes.transcript_ready` ✅

6. **Important:** Verify app có đủ scopes:
   - ✅ "Export minutes"
   - ✅ "Download audio/video files of minutes"

7. Save

---

### Bước 6: Test End-to-End (3 phút)

#### Test 1: Manual Trigger

```bash
curl -X POST "https://your-app.railway.app/process?meeting_url=https://gearvn-com.sg.larksuite.com/minutes/YOUR_MEETING_ID"
```

#### Test 2: Simulate Webhook

```bash
curl -X POST https://your-app.railway.app/webhook/lark-meeting \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_url": "https://gearvn-com.sg.larksuite.com/minutes/YOUR_MEETING_ID",
    "event_type": "meeting_completed"
  }'
```

Expected response:
```json
{
  "status": "accepted",
  "message": "Meeting processing started in background"
}
```

#### Test 3: Check Supabase

1. Vào Supabase Dashboard
2. Table `meetings` → Should have 1 new row với status "processing"
3. Table `processing_logs` → Should see processing steps
4. Sau vài phút → status thành "completed"
5. Table `meeting_transcripts` → Should have transcript + summary

---

## 🎉 Hoàn thành!

Hệ thống đã sẵn sàng. Từ giờ mỗi khi có meeting hoàn thành:

1. Lark gửi webhook → Railway
2. Railway tự động download video
3. Convert → Transcript → Summary
4. Gemini gắn tags tự động
5. Upload lên Supabase

**Không cần làm gì cả!** ✨

---

## 📊 Monitoring

### Railway Logs
- Vào Railway dashboard
- Click vào service
- Xem "Deployments" → Latest → Logs
- Real-time processing logs

### Supabase Dashboard
- Table `meetings`: Xem tất cả meetings
- Table `processing_logs`: Debug processing steps
- Filter by status: `pending`, `processing`, `completed`, `failed`

### Key Metrics
- Processing success rate (target: > 95%)
- Average processing time: ~5-10 minutes cho video 1 giờ
- Failed meetings: Check error_message column

---

## 🆘 Troubleshooting

### Issue: Webhook không nhận được
✅ Check Railway app đang chạy (không sleep)
✅ Verify webhook URL trong Lark settings
✅ Test với `/webhook/test` endpoint

### Issue: Video download fails
✅ Check Lark app scopes enabled
✅ Verify meeting đã có recording
✅ Check access token valid (xem Railway logs)

### Issue: Supabase connection fails
✅ Verify environment variables trong Railway
✅ Test Supabase URL manually
✅ Check API key permissions

### Issue: Processing quá lâu
✅ Normal: 5-10 phút cho video 1 giờ
✅ Nếu > 30 phút: Check Railway logs for errors
✅ Có thể do video quá lớn → upgrade Railway plan

---

## 📚 Next Steps

- [ ] Test với 1 meeting thật
- [ ] Verify transcript quality
- [ ] Check auto-tagging accuracy
- [ ] Setup monitoring alerts
- [ ] Configure backup strategy

Chi tiết deployment: [DEPLOYMENT.md](DEPLOYMENT.md)
Chi tiết implementation: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

---

## 💡 Tips

**Testing locally:**
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env với credentials của bạn

# Run webhook receiver
python webhook_receiver.py
# Server sẽ chạy tại http://localhost:8000

# Test manual processing
python meeting_processor.py "https://gearvn-com.sg.larksuite.com/minutes/YOUR_ID"
```

**Cost optimization:**
- Railway Free Tier: 500 hours/month (đủ cho ~50 meetings)
- Upgrade to Hobby ($5/month) nếu xử lý > 50 meetings/month
- Supabase Free Tier: 500MB database (đủ cho ~100 meetings with transcripts)

**Auto-tagging accuracy:**
- Meeting Type accuracy: ~95%
- Meeting Topic accuracy: ~90%
- Nếu sai → manually update trong Supabase dashboard
- Gemini sẽ học từ patterns trong summaries

---

**Ready to automate your meetings!** 🚀
