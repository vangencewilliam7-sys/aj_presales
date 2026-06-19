"""
Session Repository — Middleware for interview_sessions and homework_ledger tables.
This is the ONLY file that knows these table names exist.
"""
from typing import Dict, Any, Optional, List


class SessionRepo:
    def __init__(self, supabase_client):
        self._db = supabase_client

    # =====================================================================
    # INTERVIEW SESSIONS TABLE
    # =====================================================================
    def create_session(self, expert_id: str, iteration: int) -> dict:
        """Create a new interview session."""
        res = self._db.table("interview_sessions").insert({
            "expert_id": expert_id,
            "iteration_number": iteration,
            "status": "active"
        }).execute()
        if not res.data:
            raise Exception("Failed to create interview session.")
        return res.data[0]

    def get_by_id(self, session_id: str) -> dict:
        """Fetch a single session by ID."""
        res = self._db.table("interview_sessions").select("*").eq("id", session_id).execute()
        if not res.data:
            raise Exception(f"Session {session_id} not found.")
        return res.data[0]

    def get_active_session(self, expert_id: str) -> Optional[dict]:
        """Get the currently active session for an expert."""
        res = self._db.table("interview_sessions").select("id").eq("expert_id", expert_id).eq("status", "active").execute()
        return res.data[0] if res.data else None

    def get_latest_iteration(self, expert_id: str) -> int:
        """Get the highest iteration number for an expert's sessions."""
        res = self._db.table("interview_sessions").select("iteration_number").eq("expert_id", expert_id).order("iteration_number", desc=True).limit(1).execute()
        if res.data:
            return res.data[0]["iteration_number"]
        return 1

    def update_session(self, session_id: str, data: dict) -> None:
        """Update fields on an interview session (script, running_summary, transcript, status, etc.)."""
        self._db.table("interview_sessions").update(data).eq("id", session_id).execute()

    # =====================================================================
    # HOMEWORK LEDGER TABLE
    # =====================================================================
    def get_homework(self, expert_id: str) -> Optional[dict]:
        """Fetch the latest homework entry for an expert."""
        res = self._db.table("homework_ledger").select("*").eq("expert_id", expert_id).order("created_at", desc=True).limit(1).execute()
        return res.data[0] if res.data else None

    def update_homework(self, homework_id: str, data: dict) -> None:
        """Update fields on a homework ledger entry."""
        self._db.table("homework_ledger").update(data).eq("id", homework_id).execute()

    def create_homework(self, data: dict) -> dict:
        """Create a new homework ledger entry."""
        res = self._db.table("homework_ledger").insert(data).execute()
        if not res.data:
            raise Exception("Failed to create homework entry.")
        return res.data[0]
