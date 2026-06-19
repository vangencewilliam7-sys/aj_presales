-- ============================================================
-- AJ PRESALES — MASTER DATABASE SCHEMA
-- ============================================================
-- Run this in: Supabase Dashboard > SQL Editor > New Query
-- 
-- This script sets up the brand new database for the Presales app,
-- and includes the new `running_summary` column for infinite memory!
-- ============================================================



-- 1. EXPERTS
CREATE TABLE IF NOT EXISTS experts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT,
    stream_type TEXT,
    expertise_streams TEXT,
    years_of_experience INTEGER,
    short_bio TEXT,
    linkedin_url TEXT,
    archetype TEXT DEFAULT 'balanced',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. EXPERT PROFILE (Tacit Knowledge Storage)
CREATE TABLE IF NOT EXISTS expert_profile (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    expert_id UUID REFERENCES experts(id) ON DELETE CASCADE,
    persona_traits JSONB DEFAULT '[]'::jsonb,
    war_stories JSONB DEFAULT '[]'::jsonb,
    mental_models JSONB DEFAULT '[]'::jsonb,
    edge_cases JSONB DEFAULT '[]'::jsonb,
    pattern_breaks JSONB DEFAULT '[]'::jsonb,
    tacit_insights JSONB DEFAULT '[]'::jsonb,
    linguistic_fingerprint JSONB DEFAULT '{}'::jsonb,
    system_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. INTERVIEW SESSIONS (With the new Context Memory!)
CREATE TABLE IF NOT EXISTS interview_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expert_id UUID REFERENCES experts(id) ON DELETE CASCADE,
    iteration_number INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    script JSONB DEFAULT '{}'::jsonb,
    raw_transcript TEXT DEFAULT '',
    running_summary TEXT DEFAULT '',  -- NEW: Infinite Memory Ledger
    current_block_index INTEGER DEFAULT 0,  -- NEW: Tracks which block you are on
    current_question_index INTEGER DEFAULT 0, -- NEW: Tracks which question you are on
    session_synthesis JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMP WITH TIME ZONE
);

-- 4. HOMEWORK LEDGER
CREATE TABLE IF NOT EXISTS homework_ledger (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    expert_id UUID REFERENCES experts(id) ON DELETE CASCADE,
    session_id UUID REFERENCES interview_sessions(id) ON DELETE CASCADE,
    iteration_number INTEGER DEFAULT 1,
    ai_open_loops JSONB DEFAULT '[]'::jsonb,
    human_manual_notes TEXT DEFAULT '',
    is_validated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 5. RAG KNOWLEDGE SYSTEM (For Uploaded Documents)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL,
    title TEXT,
    author_or_channel TEXT,
    url_or_identifier TEXT,
    global_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    chunk_index INT,
    content TEXT NOT NULL,
    location_marker TEXT,
    embedding vector(1536)
);

-- Vector Search RPC Function
CREATE OR REPLACE FUNCTION match_knowledge_chunks(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  content text,
  location_marker text,
  source_name text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    kc.id,
    kc.content,
    kc.location_marker,
    ks.title as source_name,
    1 - (kc.embedding <=> query_embedding) AS similarity
  FROM knowledge_chunks kc
  JOIN knowledge_sources ks ON kc.source_id = ks.id
  WHERE 1 - (kc.embedding <=> query_embedding) > match_threshold
  ORDER BY kc.embedding <=> query_embedding
  LIMIT match_count;
$$;