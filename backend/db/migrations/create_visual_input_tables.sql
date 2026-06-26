-- ==============================================================================
-- Visual Input Parser Tables
-- ==============================================================================
-- RUN THIS IN YOUR SUPABASE SQL EDITOR

-- 1. Create the Storage Bucket (if not done via UI)
-- NOTE: In some Supabase setups, you must create buckets via the Dashboard UI 
-- (Storage -> Create Bucket -> Name: 'journalist-visual-inputs' -> Public: OFF)
-- Alternatively, if your SQL role has permissions, this will work:
INSERT INTO storage.buckets (id, name, public) 
VALUES ('journalist-visual-inputs', 'journalist-visual-inputs', false)
ON CONFLICT (id) DO NOTHING;

-- 1.5 Allow inserts into the bucket (Fixes the 403 RLS Error)
CREATE POLICY "Allow public uploads to visual inputs bucket"
ON storage.objects FOR INSERT
TO public
WITH CHECK (bucket_id = 'journalist-visual-inputs');

-- Optional: Allow reading if the backend needs to fetch the file later
CREATE POLICY "Allow public reads from visual inputs bucket"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'journalist-visual-inputs');

-- 2. journalist_visual_inputs
CREATE TABLE IF NOT EXISTS journalist_visual_inputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    user_id UUID,
    input_type TEXT NOT NULL,
    file_name TEXT,
    file_type TEXT,
    file_size BIGINT,
    storage_path TEXT,
    context_text TEXT,
    gemini_file_id TEXT,
    status TEXT DEFAULT 'uploaded',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. journalist_visual_analysis
CREATE TABLE IF NOT EXISTS journalist_visual_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    visual_input_id UUID REFERENCES journalist_visual_inputs(id) ON DELETE CASCADE,
    input_type TEXT,
    visual_summary TEXT,
    spoken_or_text_summary TEXT,
    timeline_json JSONB,
    visible_elements_json JSONB,
    key_observations_json JSONB,
    missing_context_json JSONB,
    raw_gemini_response_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
