"""
memory.py: Persistent Session State Database (SQLite/JSON), Context Caching &
History Compaction for long-context screenplays, and Non-Blocking Asynchronous
Evaluation execution queues.
"""

import asyncio
import json
import os
import sqlite3
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 1. PERSISTENT SESSION STATE DATABASE (SQLITE / JSON SESSION RECALL)
# ---------------------------------------------------------------------------
class PersistentSessionStateStore:
    """Persistent session database storing evaluation state across serverless restarts."""

    def __init__(self, db_path: str = "/tmp/compliance_session_store.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        asset_reference TEXT,
                        modality TEXT,
                        overall_status TEXT,
                        context_history TEXT,
                        last_updated REAL
                    )
                """)
                conn.commit()
        except Exception:
            pass

    def save_session(
        self,
        session_id: str,
        asset_ref: str,
        modality: str,
        status: str,
        history: List[Dict[str, Any]],
    ):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sessions (session_id, asset_reference, modality, overall_status, context_history, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        asset_ref,
                        modality,
                        status,
                        json.dumps(history),
                        time.time(),
                    ),
                )
                conn.commit()
        except Exception:
            pass

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT asset_reference, modality, overall_status, context_history, last_updated
                    FROM sessions WHERE session_id = ?
                """,
                    (session_id,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "session_id": session_id,
                        "asset_reference": row[0],
                        "modality": row[1],
                        "overall_status": row[2],
                        "context_history": json.loads(row[3]),
                        "last_updated": row[4],
                    }
        except Exception:
            pass
        return None


# Global singleton persistent store
session_store = PersistentSessionStateStore()


# ---------------------------------------------------------------------------
# 2. CONTEXT CACHING & SLIDING-WINDOW HISTORY COMPACTION
# ---------------------------------------------------------------------------
def compact_screenplay_history(
    text_or_history: str, max_chars: int = 45000
) -> str:
    """Compacts and caches multi-turn dialogue/screenplay context to prevent redundant context overflow."""
    if not text_or_history or len(text_or_history) <= max_chars:
        return text_or_history

    # Retain opening Title Page & Dramatis Personae (first 15%) and recent climax/ending scenes (last 65%)
    prefix_len = int(max_chars * 0.20)
    suffix_len = int(max_chars * 0.75)
    header = text_or_history[:prefix_len]
    footer = text_or_history[-suffix_len:]
    omitted = len(text_or_history) - (prefix_len + suffix_len)

    compaction_notice = (
        f"\n... [HISTORY COMPACTION & CONTEXT CACHE: {omitted:,} intermediate"
        " characters compacted to preserve full Title Page constraints and act"
        " climax continuity] ...\n"
    )
    return f"{header}{compaction_notice}{footer}"


# ---------------------------------------------------------------------------
# 3. NON-BLOCKING ASYNCHRONOUS EVALUATION EXECUTION WRAPPER
# ---------------------------------------------------------------------------
_async_executor = ThreadPoolExecutor(max_workers=4)


async def run_compliance_evaluation_async(
    asset_path: str,
    asset_type: str,
    constraints: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Asynchronously runs compliance evaluation on a background thread pool without blocking the UI."""
    loop = asyncio.get_event_loop()
    s_id = session_id or str(uuid.uuid4())

    def _sync_task():
        from src.agent import run_compliance_evaluation

        report = run_compliance_evaluation(
            asset_path, asset_type, constraints
        )
        session_store.save_session(
            session_id=s_id,
            asset_ref=asset_path,
            modality=asset_type,
            status=report.overall_status,
            history=[report.model_dump()],
        )
        return report

    result = await loop.run_in_executor(_async_executor, _sync_task)
    return result
