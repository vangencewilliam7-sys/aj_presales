"""
RAG Engine — Unified Data Ingestion & Retrieval Service
Merged from: rag.py (PDF chunking + hybrid retrieval) + ingest_data.py (video transcript chunking)

Handles:
- PDF document ingestion (page-by-page extraction, recursive chunking)
- Video transcript ingestion (timestamped + non-timestamped chunking)
- DOCX/TXT file parsing
- Embedding generation (text-embedding-3-small)
- Hybrid RAG retrieval (Semantic-First, Lexical-Fallback)
"""

import os
import re
import time
import logging
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


# ============================================================
# STANDALONE UTILITY FUNCTIONS (imported by app.py)
# ============================================================

def read_txt_file(filepath: str) -> str:
    """Read a plain text file and return its content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def read_docx_file(filepath: str) -> str:
    """Read a DOCX file and return combined paragraph text."""
    import docx
    doc = docx.Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_transcript_text(raw_text: str, has_timestamps: bool) -> str:
    """
    Extract just the transcript portion from the raw file text.
    Strips header lines (Video Name, Link, TITLE, VIDEO URL, separator lines).
    """
    lines = raw_text.split('\n')
    transcript_lines = []
    header_done = False

    for line in lines:
        stripped = line.strip()
        if not header_done:
            if (stripped.lower().startswith('video name:') or
                stripped.lower().startswith('title:') or
                stripped.lower().startswith('video url:') or
                stripped.lower().startswith('link:') or
                stripped.lower().startswith('transcript:') or
                stripped.startswith('====') or
                stripped == ''):
                continue
            else:
                header_done = True

        if header_done and stripped:
            transcript_lines.append(stripped)

    return "\n".join(transcript_lines)


def chunk_timestamped(transcript_text: str, chunk_size: int = 800) -> list:
    """
    Track A: For timestamped docs.
    Split by [HH:MM:SS] markers, then group segments into ~chunk_size char chunks.
    Returns list of dicts: {"content": str, "location_marker": str}
    """
    ts_pattern = re.compile(r'\[(\d{2}:\d{2}:\d{2})\]\s*')
    parts = ts_pattern.split(transcript_text)

    segments = []
    i = 0
    if parts and not re.match(r'\d{2}:\d{2}:\d{2}', parts[0]):
        i = 1

    while i < len(parts) - 1:
        timestamp = parts[i]
        text = parts[i + 1].strip()
        if text:
            segments.append({"timestamp": timestamp, "text": text})
        i += 2

    if not segments:
        return [{"content": transcript_text.strip(), "location_marker": "00:00:00"}]

    chunks = []
    current_text = ""
    current_ts = segments[0]["timestamp"]

    for seg in segments:
        if len(current_text) + len(seg["text"]) > chunk_size and current_text:
            chunks.append({
                "content": current_text.strip(),
                "location_marker": current_ts
            })
            current_text = seg["text"]
            current_ts = seg["timestamp"]
        else:
            current_text += " " + seg["text"] if current_text else seg["text"]

    if current_text.strip():
        chunks.append({
            "content": current_text.strip(),
            "location_marker": current_ts
        })

    return chunks


def chunk_by_characters(transcript_text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    """
    Track B: For non-timestamped docs (speech-to-text with no punctuation).
    Character-based chunking that splits at word boundaries with overlap.
    Returns list of dicts: {"content": str, "location_marker": str}
    """
    text = transcript_text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    segment_num = 1

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunk_text = text[start:].strip()
            if chunk_text and len(chunk_text) >= 30:
                chunks.append({
                    "content": chunk_text,
                    "location_marker": f"Segment {segment_num}"
                })
            break

        break_point = text.rfind(' ', start + chunk_size // 2, end)
        if break_point > start:
            end = break_point

        chunk_text = text[start:end].strip()
        if chunk_text and len(chunk_text) >= 30:
            chunks.append({
                "content": chunk_text,
                "location_marker": f"Segment {segment_num}"
            })
            segment_num += 1

        start = end - overlap

    return chunks


# ============================================================
# RAG ENGINE CLASS
# ============================================================

class RagEngine:
    def __init__(self, db_client=None, knowledge_repo=None):
        """
        Initializes the RAG Engine.
        :param db_client: Supabase client (legacy, used if knowledge_repo not provided).
        :param knowledge_repo: KnowledgeRepo middleware instance (preferred).
        """
        self.embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
        self.db_client = db_client
        self.knowledge_repo = knowledge_repo

    # =====================================================================
    # 1. PDF INGESTION & CHUNKING
    # =====================================================================
    def ingest_pdf(self, pdf_path: str, chunk_size: int = 800, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Extracts text from a PDF, applies recursive chunking, and generates embeddings.
        Returns a list of batched chunk dictionaries ready for DB insertion.
        """
        doc = fitz.open(pdf_path)
        pages_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                pages_text.append({"page": page_num + 1, "text": text})
        doc.close()

        chunk_data = []
        chunk_idx = 0

        for page_info in pages_text:
            page_text = page_info["text"]
            page_num = page_info["page"]

            if len(page_text) <= chunk_size:
                chunks = [page_text]
            else:
                chunks = []
                start = 0
                while start < len(page_text):
                    end = start + chunk_size

                    if end < len(page_text):
                        last_break = page_text.rfind('\n', start, end)
                        if last_break > start + chunk_size // 2:
                            end = last_break + 1
                        else:
                            last_space = page_text.rfind(' ', start, end)
                            if last_space > start + chunk_size // 2:
                                end = last_space + 1

                    chunk_text = page_text[start:end].strip()
                    if chunk_text:
                        chunks.append(chunk_text)

                    start = end - chunk_overlap if end < len(page_text) else end

            for chunk_text in chunks:
                if len(chunk_text.strip()) < 30:
                    continue

                vector = self.embeddings_model.embed_query(chunk_text)

                chunk_data.append({
                    "chunk_index": chunk_idx,
                    "content": chunk_text,
                    "location_marker": f"Page {page_num}",
                    "embedding": vector
                })
                chunk_idx += 1

                if chunk_idx % 20 == 0:
                    time.sleep(1)

        return chunk_data

    # =====================================================================
    # 2. SUPABASE INGESTION (PDF)
    # =====================================================================
    def ingest_to_supabase(self, file_path: str, source_metadata: Dict[str, str], batch_size: int = 50) -> Dict[str, Any]:
        """
        End-to-end ingestion pipeline: Parses the PDF, generates embeddings,
        and actually INSERTS the data into the Supabase database.
        """
        source = self.knowledge_repo.create_source({
            "source_type": source_metadata.get("source_type", "pdf_document"),
            "title": source_metadata.get("title", os.path.basename(file_path)),
            "author_or_channel": source_metadata.get("author_or_channel", "Unknown"),
            "url_or_identifier": source_metadata.get("url_or_identifier", file_path),
            "global_summary": source_metadata.get("global_summary", "")
        })

        source_id = source['id']

        logger.info(f"Processing PDF and generating embeddings for: {file_path}...")
        chunk_data = self.ingest_pdf(file_path)

        for chunk in chunk_data:
            chunk["source_id"] = source_id

        logger.info(f"Pushing {len(chunk_data)} chunks to Supabase...")
        for i in range(0, len(chunk_data), batch_size):
            batch = chunk_data[i:i + batch_size]
            self.knowledge_repo.insert_chunks(batch)
            logger.info(f"Inserted batch {i // batch_size + 1}")

        return {"source_id": source_id, "total_chunks_inserted": len(chunk_data)}

    # =====================================================================
    # 3. VIDEO TRANSCRIPT INGESTION
    # =====================================================================
    def ingest_video_transcript(self, video_meta: dict, docs_dir: str) -> Dict[str, Any]:
        """
        Ingests a single video transcript into Supabase.
        1. Read file (TXT or DOCX)
        2. Extract transcript text
        3. Chunk using appropriate strategy
        4. Create parent source in knowledge_sources
        5. Generate embeddings and insert chunks into knowledge_chunks
        """
        filepath = os.path.join(docs_dir, video_meta["filename"])
        logger.info(f"Ingesting: {video_meta['title']}")

        if video_meta["filetype"] == "txt":
            raw_text = read_txt_file(filepath)
        else:
            raw_text = read_docx_file(filepath)

        transcript = extract_transcript_text(raw_text, video_meta["has_timestamps"])
        logger.info(f"  Transcript length: {len(transcript)} chars")

        if video_meta["has_timestamps"]:
            chunks = chunk_timestamped(transcript)
            logger.info(f"  Chunking: TIMESTAMP-BASED -> {len(chunks)} chunks")
        else:
            chunks = chunk_by_characters(transcript)
            logger.info(f"  Chunking: CHARACTER-BASED -> {len(chunks)} chunks")

        source = self.knowledge_repo.create_source({
            "source_type": video_meta["source_type"],
            "title": video_meta["title"],
            "author_or_channel": video_meta["author_or_channel"],
            "url_or_identifier": video_meta["url_or_identifier"],
            "global_summary": video_meta["global_summary"],
        })

        source_id = source['id']
        logger.info(f"  Parent source created: {source_id}")

        chunk_data = []
        for idx, chunk in enumerate(chunks):
            content = chunk["content"]
            if len(content.strip()) < 30:
                continue

            logger.info(f"  Embedding chunk {idx + 1}/{len(chunks)} ({len(content)} chars)...")
            vector = self.embeddings_model.embed_query(content)

            chunk_data.append({
                "source_id": source_id,
                "chunk_index": idx,
                "content": content,
                "location_marker": chunk["location_marker"],
                "embedding": vector,
            })

            if (idx + 1) % 10 == 0:
                time.sleep(0.5)

        batch_size = 20
        for i in range(0, len(chunk_data), batch_size):
            batch = chunk_data[i:i + batch_size]
            self.knowledge_repo.insert_chunks(batch)
            logger.info(f"  Batch {i // batch_size + 1}: Inserted {len(batch)} chunks")

        logger.info(f"  DONE: {len(chunk_data)} chunks inserted for: {video_meta['title']}")
        return {"source_id": source_id, "chunks_inserted": len(chunk_data)}

    # =====================================================================
    # 4. HYBRID RAG RETRIEVAL
    # =====================================================================
    def hybrid_rag_fetch(self, query: str, top_k: int = 4) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Strict Semantic-First, Lexical-Fallback retrieval strategy.
        Returns the concatenated context text and a list of metadata dictionaries.
        """
        query_embedding = self.embeddings_model.embed_query(query)
        match_threshold = 0.3

        # Step 1: Semantic Vector Search (Primary)
        results = self.knowledge_repo.vector_search(
            embedding=query_embedding,
            threshold=match_threshold,
            limit=top_k
        )

        # Step 2: Lexical Keyword Search (Fallback)
        if not results:
            fallback_query = query[:15]
            results = self.knowledge_repo.keyword_search(
                keyword=fallback_query,
                limit=top_k
            )

        # Step 3: Context Assembly
        context_chunks = []
        metadata = []

        for res in results:
            content = res.get("content", "")
            context_chunks.append(content)

            metadata.append({
                "source_name": res.get("source_name", "Unknown Document"),
                "location_marker": res.get("location_marker", "Unknown Location"),
                "snippet": content[:100] + "..." if len(content) > 100 else content
            })

        context_text = "\n\n".join(context_chunks)

        return context_text, metadata
