-- Supabase Database Schema for Lark Meeting Automation
-- Run this in Supabase SQL Editor

-- Table 1: meetings
-- Stores meeting metadata and processing status
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Lark Meeting Info
    lark_meeting_id VARCHAR(255) UNIQUE NOT NULL,
    lark_meeting_url TEXT NOT NULL,
    minute_token VARCHAR(50) NOT NULL,

    -- Meeting Metadata
    meeting_title TEXT NOT NULL,
    meeting_date TIMESTAMPTZ NOT NULL,
    meeting_duration INTEGER, -- seconds
    meeting_owner VARCHAR(255),
    participants JSONB, -- ["Sếp", "Anh Thiện", ...]

    -- File Info
    video_file_name TEXT,
    video_file_size BIGINT, -- bytes
    video_download_url TEXT,

    -- Processing Status
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,

    -- Auto Tags
    meeting_type VARCHAR(100), -- "Họp dự án" | "Họp định kỳ"
    meeting_topic VARCHAR(100), -- "Loyalty" | "Membership" | "Operation" | "Business" | "Data"

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Indexes for meetings table
CREATE INDEX IF NOT EXISTS idx_meetings_lark_id ON meetings(lark_meeting_id);
CREATE INDEX IF NOT EXISTS idx_meetings_minute_token ON meetings(minute_token);
CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(meeting_date DESC);
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);
CREATE INDEX IF NOT EXISTS idx_meetings_type ON meetings(meeting_type);
CREATE INDEX IF NOT EXISTS idx_meetings_topic ON meetings(meeting_topic);
CREATE INDEX IF NOT EXISTS idx_meetings_created ON meetings(created_at DESC);

-- Table 2: meeting_transcripts
-- Stores transcript and summary content
CREATE TABLE IF NOT EXISTS meeting_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,

    -- Transcript Content
    transcript_content TEXT NOT NULL,
    transcript_word_count INTEGER,

    -- Summary Content
    summary_content TEXT NOT NULL,

    -- Extracted Summary Components
    main_topics JSONB, -- ["Topic 1", "Topic 2", ...]
    decisions JSONB, -- ["Decision 1", "Decision 2", ...]
    risks JSONB, -- ["Risk 1", "Risk 2", ...]
    pending_issues JSONB, -- ["Issue 1", "Issue 2", ...]

    -- Action Items
    action_items JSONB, -- [{"task": "...", "owner": "...", "deadline": "..."}, ...]

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for meeting_transcripts table
CREATE INDEX IF NOT EXISTS idx_transcripts_meeting_id ON meeting_transcripts(meeting_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_created ON meeting_transcripts(created_at DESC);

-- Table 3: processing_logs
-- Stores processing logs for debugging
CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,

    -- Log Details
    step VARCHAR(100) NOT NULL, -- download, convert, segment, transcript, summary, tag, upload
    status VARCHAR(50) NOT NULL, -- started, completed, failed
    message TEXT,
    metadata JSONB, -- Any additional data like file sizes, durations, etc.

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for processing_logs table
CREATE INDEX IF NOT EXISTS idx_logs_meeting_id ON processing_logs(meeting_id);
CREATE INDEX IF NOT EXISTS idx_logs_step ON processing_logs(step);
CREATE INDEX IF NOT EXISTS idx_logs_status ON processing_logs(status);
CREATE INDEX IF NOT EXISTS idx_logs_created ON processing_logs(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE meeting_transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Allow all operations for service role (anon key will have full access)
CREATE POLICY "Allow all for service role - meetings" ON meetings
    FOR ALL USING (true);

CREATE POLICY "Allow all for service role - transcripts" ON meeting_transcripts
    FOR ALL USING (true);

CREATE POLICY "Allow all for service role - logs" ON processing_logs
    FOR ALL USING (true);

-- Comments for documentation
COMMENT ON TABLE meetings IS 'Stores Lark meeting metadata and processing status';
COMMENT ON TABLE meeting_transcripts IS 'Stores meeting transcripts and summaries';
COMMENT ON TABLE processing_logs IS 'Stores processing logs for debugging and monitoring';

COMMENT ON COLUMN meetings.status IS 'Processing status: pending, processing, completed, failed';
COMMENT ON COLUMN meetings.meeting_type IS 'Auto-tagged meeting type: Họp dự án, Họp định kỳ';
COMMENT ON COLUMN meetings.meeting_topic IS 'Auto-tagged topic: Loyalty, Membership, Operation, Business, Data';
COMMENT ON COLUMN processing_logs.step IS 'Processing step: download, convert, segment, transcript, summary, tag, upload';
COMMENT ON COLUMN processing_logs.status IS 'Step status: started, completed, failed';
