import sqlite3
import json
import os
from datetime import datetime, timezone

class HistoryManager:
    """Manages local SQLite storage for attention sessions and cycles."""
    
    def __init__(self, db_path="focuslens_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Table for cycles (raw data)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    attention_score INTEGER,
                    productivity_score INTEGER,
                    state TEXT,
                    context TEXT,
                    window_title TEXT,
                    process_name TEXT,
                    payload_json TEXT
                )
            """)
            # Index for faster retrieval
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cycles_timestamp ON cycles(timestamp)")

    def save_cycle(self, payload: dict):
        """Persists a single engine cycle to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                win_info = payload.get("window_info", {})
                conn.execute("""
                    INSERT INTO cycles (
                        timestamp, attention_score, productivity_score, state, context, 
                        window_title, process_name, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    payload.get("timestamp"),
                    payload.get("attention_score"),
                    payload.get("productivity_score"),
                    payload.get("attention_state"),
                    payload.get("context"),
                    win_info.get("title", "Unknown"),
                    win_info.get("process_name", "Unknown"),
                    json.dumps(payload)
                ))
        except Exception as e:
            print(f"[HistoryManager] Error saving cycle: {e}")

    def get_recent_history(self, limit=100):
        """Retrieves recent cycles."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT payload_json FROM cycles ORDER BY timestamp DESC LIMIT ?", 
                    (limit,)
                )
                return [json.loads(row["payload_json"]) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[HistoryManager] Error retrieving history: {e}")
            return []

    def get_task_history(self, limit=50):
        """Retrieves aggregated recent app usage history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT process_name, window_title,
                           COUNT(*) AS cycle_count,
                           AVG(attention_score) AS avg_score,
                           SUM(5) AS total_seconds,
                           MAX(timestamp) AS last_seen
                    FROM cycles
                    GROUP BY process_name, window_title
                    ORDER BY last_seen DESC
                    LIMIT ?
                """, (limit,))
                tasks = []
                for row in cursor.fetchall():
                    duration_min = round((row["cycle_count"] * 5) / 60, 1)
                    tasks.append({
                        "process_name": row['process_name'],
                        "window_title": row['window_title'],
                        "attention_score": round(row["avg_score"] or 0, 1),
                        "time": f"{duration_min} min",
                        "timestamp": row["last_seen"]
                    })
                return tasks
        except Exception as e:
            print(f"[HistoryManager] Error retrieving tasks: {e}")
            return []

    def get_daily_trend(self, days=7):
        """Aggregates scores by day."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT DATE(timestamp) as date, AVG(attention_score) as avg_score
                    FROM cycles
                    WHERE timestamp >= date('now', ?)
                    GROUP BY DATE(timestamp)
                    ORDER BY date ASC
                """, (f'-{days} days',))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[HistoryManager] Error retrieving trends: {e}")
            return []
