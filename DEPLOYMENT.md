# Deployment Guide - Lark Meeting Automation

## 🎯 Overview
Hướng dẫn deploy webhook receiver lên Railway để nhận Lark webhooks và xử lý meetings tự động.

---

## 📋 Prerequisites

1. ✅ Railway account (sign up at https://railway.app)
2. ✅ Supabase database đã setup (run `supabase_schema.sql`)
3. ✅ Lark App credentials:
   - App ID: `cli_a9aab0f22978deed`
   - App Secret: `qGF9xiBcIcZrqzpTS8wV3fB7ouywulDV`
   - Scopes enabled: "Export minutes", "Download audio/video files"

---

## 🚀 Deployment Steps

### Step 1: Setup Supabase Database

1. Login to Supabase: https://iuadezkhfzcvkvgmhupe.supabase.co
2. Go to SQL Editor
3. Copy and paste content from `supabase_schema.sql`
4. Run the SQL script
5. Verify tables created: `meetings`, `meeting_transcripts`, `processing_logs`

### Step 2: Deploy to Railway

#### Option A: Deploy from GitHub (Recommended)

1. Push code to GitHub repository
   ```bash
   git add .
   git commit -m "Add Lark meeting automation"
   git push origin feature/supabase-integration
   ```

2. Go to Railway.app and create new project
3. Click "Deploy from GitHub repo"
4. Select your repository: `bangbangnguyen2610/trimvideo`
5. Railway will auto-detect Python and use `Procfile`

#### Option B: Deploy with Railway CLI

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login:
   ```bash
   railway login
   ```

3. Initialize project:
   ```bash
   railway init
   ```

4. Deploy:
   ```bash
   railway up
   ```

### Step 3: Configure Environment Variables

In Railway dashboard, add these environment variables:

```
LARK_APP_ID=cli_a9aab0f22978deed
LARK_APP_SECRET=qGF9xiBcIcZrqzpTS8wV3fB7ouywulDV
GEMINI_API_KEY=AIzaSyBg-P8MBhJllhisSRxsxPW8nEh-bQtu0w4
SUPABASE_URL=https://iuadezkhfzcvkvgmhupe.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1YWRlemtoZnpjdmt2Z21odXBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTkyNDQsImV4cCI6MjA4MDc5NTI0NH0.mlDh2GfgnG0Q54CXnTGsZ_3WjhfChPLh9eeK9eZdLYc
PORT=8000
```

### Step 4: Install ffmpeg Buildpack

Railway auto-installs ffmpeg via `railway.json` config. Verify in deployment logs:
```
Installing ffmpeg...
ffmpeg version 4.x.x
```

### Step 5: Get Webhook URL

After deployment, Railway will provide a public URL like:
```
https://your-app.railway.app
```

Your webhook endpoint will be:
```
https://your-app.railway.app/webhook/lark-meeting
```

### Step 6: Configure Lark Webhook

1. Go to Lark Open Platform: https://open.larksuite.com/app
2. Select your app: `cli_a9aab0f22978deed`
3. Go to "Event Subscriptions" or "Webhooks"
4. Add webhook URL: `https://your-app.railway.app/webhook/lark-meeting`
5. Subscribe to events:
   - `meeting.recording_ready`
   - `minutes.transcript_ready`
6. Save and verify webhook

---

## 🧪 Testing

### Test 1: Health Check
```bash
curl https://your-app.railway.app/health
# Should return: {"status": "healthy"}
```

### Test 2: Manual Processing
```bash
curl -X POST "https://your-app.railway.app/process?meeting_url=https://gearvn-com.sg.larksuite.com/minutes/YOUR_MEETING_ID"
```

### Test 3: Webhook Simulation
```bash
curl -X POST https://your-app.railway.app/webhook/lark-meeting \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_url": "https://gearvn-com.sg.larksuite.com/minutes/YOUR_MEETING_ID",
    "event_type": "meeting_completed",
    "timestamp": "2025-12-09T10:00:00Z"
  }'
```

### Test 4: Check Supabase
1. Go to Supabase Dashboard
2. Check `meetings` table for new records
3. Check `processing_logs` table for processing steps
4. Check `meeting_transcripts` table for transcripts and summaries

---

## 📊 Monitoring

### Railway Logs
View real-time logs in Railway dashboard:
- Deployment logs
- Application logs
- Error logs

### Supabase Logs
Check `processing_logs` table for:
- Processing steps
- Success/failure status
- Error messages

### Key Metrics to Monitor
- Webhook response time (should be < 1 second)
- Processing success rate (target: > 95%)
- Average processing time per meeting
- Failed meetings count

---

## 🐛 Troubleshooting

### Issue 1: Webhook not receiving requests
**Solution:**
- Verify webhook URL in Lark App settings
- Check Railway app is running (not sleeping)
- Test with `/webhook/test` endpoint

### Issue 2: ffmpeg not found
**Solution:**
- Verify `railway.json` buildCommand includes ffmpeg install
- Check deployment logs for ffmpeg installation
- May need to add Nixpacks config

### Issue 3: Video download fails
**Solution:**
- Check Lark App scopes: "Export minutes" enabled?
- Verify access token is valid
- Check rate limits (5 req/sec)

### Issue 4: Supabase connection fails
**Solution:**
- Verify SUPABASE_URL and SUPABASE_KEY in Railway env vars
- Check Supabase project is active
- Test connection with simple query

### Issue 5: Processing timeout
**Solution:**
- Check Railway plan limits (free tier: 500 hours/month)
- For large videos, may need to upgrade Railway plan
- Consider splitting long meetings

---

## 💰 Cost Estimation

### Railway
- **Starter Plan (Free)**: $0/month
  - 500 execution hours
  - 512MB RAM
  - Shared CPU
  - **Suitable for:** Testing, low-volume (< 50 meetings/month)

- **Hobby Plan**: $5/month
  - Unlimited hours
  - 1GB RAM
  - Shared CPU
  - **Suitable for:** Production, medium-volume (< 200 meetings/month)

### Supabase
- **Free Tier**: $0/month
  - 500MB database
  - 1GB file storage
  - 2GB bandwidth
  - **Suitable for:** < 100 meetings/month

- **Pro Plan**: $25/month
  - 8GB database
  - 100GB file storage
  - 50GB bandwidth
  - **Suitable for:** > 100 meetings/month

### Total Estimated Cost
- **Development/Testing**: $0/month (free tiers)
- **Production (low-volume)**: $5-30/month
- **Production (high-volume)**: $30-100/month

---

## 🔒 Security Best Practices

1. ✅ Use environment variables for all secrets (never commit to git)
2. ✅ Enable Lark webhook signature verification (add in future)
3. ✅ Use Supabase Row Level Security (RLS) policies
4. ✅ Keep dependencies updated (run `pip list --outdated`)
5. ✅ Monitor logs for suspicious activity
6. ✅ Set up error notifications (Sentry, email alerts)

---

## 📈 Scaling Considerations

When processing volume increases:

1. **Database**: Upgrade Supabase plan or add indexes
2. **Compute**: Upgrade Railway plan for more RAM/CPU
3. **Queue System**: Add Redis queue for better job management
4. **Multiple Workers**: Deploy multiple Railway instances
5. **Caching**: Cache Lark API responses to reduce API calls

---

## 📝 Maintenance Checklist

### Weekly
- [ ] Check Railway app health
- [ ] Review error logs
- [ ] Monitor processing success rate

### Monthly
- [ ] Update Python dependencies
- [ ] Review Supabase storage usage
- [ ] Check Railway execution hours
- [ ] Backup Supabase database

### Quarterly
- [ ] Review and optimize database queries
- [ ] Clean up old meeting data (if needed)
- [ ] Update documentation
- [ ] Performance audit

---

## 📚 Additional Resources

- Railway Docs: https://docs.railway.app/
- Supabase Docs: https://supabase.com/docs
- Lark Open Platform: https://open.larksuite.com/document
- FastAPI Docs: https://fastapi.tiangolo.com/
- Gemini API Docs: https://ai.google.dev/docs

---

## 🆘 Support

For issues or questions:
1. Check deployment logs in Railway
2. Check processing logs in Supabase
3. Review this documentation
4. Contact repository maintainer

---

**Deployment Status Checklist:**
- [ ] Supabase database setup complete
- [ ] Railway app deployed
- [ ] Environment variables configured
- [ ] ffmpeg installed
- [ ] Lark webhook configured
- [ ] Health check passing
- [ ] Test meeting processed successfully
- [ ] Monitoring setup complete

**Ready to go live!** 🚀
