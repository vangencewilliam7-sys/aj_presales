"""
Knowledge Repository — Middleware for knowledge_sources and knowledge_chunks tables.
This is the ONLY file that knows these table names exist.
"""
from typing import Dict, Any, Optional, List


class KnowledgeRepo:
    def __init__(self, supabase_client):
        self._db = supabase_client

    # =====================================================================
    # KNOWLEDGE SOURCES TABLE
    # =====================================================================
    def create_source(self, metadata: dict) -> dict:
        """Create a parent knowledge source record."""
        res = self._db.table("knowledge_sources").insert(metadata).execute()
        if not res.data:
            raise Exception("Failed to create knowledge source.")
        return res.data[0]

    # =====================================================================
    # KNOWLEDGE CHUNKS TABLE
    # =====================================================================
    def insert_chunks(self, chunks: list) -> None:
        """Batch insert knowledge chunks."""
        self._db.table("knowledge_chunks").insert(chunks).execute()

    # =====================================================================
    # RETRIEVAL (VECTOR SEARCH + KEYWORD FALLBACK)
    # =====================================================================
    def vector_search(self, embedding: list, threshold: float, limit: int) -> list:
        """
        Perform a vector similarity search using the match_knowledge_chunks RPC function.
        Returns a list of matching chunks with content, location_marker, source_name, similarity.
        """
        res = self._db.rpc("match_knowledge_chunks", {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": limit
        }).execute()
        return res.data if res.data else []

    def keyword_search(self, keyword: str, limit: int) -> list:
        """
        Fallback text search using ILIKE on the content column.
        Returns a list of matching chunks with flattened source_name.
        """
        res = self._db.table("knowledge_chunks")\
            .select("id, content, location_marker, knowledge_sources(title)")\
            .ilike("content", f"%{keyword}%")\
            .limit(limit)\
            .execute()

        results = []
        if res.data:
            for row in res.data:
                source_title = row.get("knowledge_sources", {}).get("title", "Unknown Document") if row.get("knowledge_sources") else "Unknown Document"
                row["source_name"] = source_title
                results.append(row)
        return results
