import os
import sqlite3
import json
import time
from typing import Any, Mapping
from langgraph.store.memory import InMemoryStore

GLOBAL_PULSE_DIR = os.path.expanduser("~/.pulse")
DEFAULT_DB_PATH = os.path.join(GLOBAL_PULSE_DIR, "pulse_memory.db")


def resolve_memory_db_path() -> str:
    """Checks pulse_settings.json in current workspace or ~/.pulse/ for custom db_path."""
    candidates = [
        os.path.join(os.getcwd(), "pulse_settings.json"),
        os.path.join(GLOBAL_PULSE_DIR, "pulse_settings.json")
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    custom = data.get("memory", {}).get("db_path")
                    if custom:
                        return os.path.realpath(os.path.abspath(custom))
            except Exception:
                pass
    return DEFAULT_DB_PATH


class Memory:
    """Hybrid memory store: LangGraph InMemoryStore during execution, SQLite for persistence."""

    def __init__(self, session_id: str = "default", db_path: str | None = None, auto_load: bool = True):
        self.session_id = session_id
        self.db_path = db_path or resolve_memory_db_path()
        self.store = InMemoryStore()
        self._seq = 0

        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            self._init_db()
            if auto_load:
                self.load_from_db()


    def _init_db(self):
        if self.db_path == ":memory:":
            return
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        seq_key TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        UNIQUE(session_id, seq_key)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS kv_store (
                        namespace TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        PRIMARY KEY (namespace, key)
                    )
                """)
        finally:
            conn.close()

    @property
    def conversation_namespace(self) -> tuple[str, ...]:
        return ("conversations", self.session_id)

    @property
    def default_data_namespace(self) -> tuple[str, ...]:
        return ("data", self.session_id)

    def add_message(self, role: str, content: str) -> None:
        """Appends a conversation message to the in-memory store in chronological order."""
        self._seq += 1
        key = f"{self._seq:08d}"
        self.store.put(
            self.conversation_namespace,
            key,
            {"role": role, "content": content, "timestamp": time.time()},
        )

    def get_history(self, limit: int = 10) -> list[dict[str, str]]:
        """Returns the most recent messages in chronological order up to limit turns."""
        items = self.store.search(self.conversation_namespace, limit=1000)
        sorted_items = sorted(items, key=lambda x: x.key)
        recent_items = sorted_items[-(limit * 2):] if limit else sorted_items
        return [{"role": item.value["role"], "content": item.value["content"]} for item in recent_items]

    def save(self, key: str, value: Mapping[str, Any], namespace: tuple[str, ...] | None = None) -> None:
        """Stores arbitrary key-value structured data."""
        ns = namespace or self.default_data_namespace
        self.store.put(ns, key, value)

    def get(self, key: str, namespace: tuple[str, ...] | None = None) -> dict[str, Any] | None:
        """Retrieves structured data by key."""
        ns = namespace or self.default_data_namespace
        item = self.store.get(ns, key)
        return item.value if item else None

    def search(self, query: str | None = None, namespace_prefix: tuple[str, ...] | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Searches items in the in-memory store."""
        ns = namespace_prefix or self.conversation_namespace
        items = self.store.search(ns, query=query, limit=limit)
        return [item.value for item in items]

    def persist_to_db(self) -> int:
        """Flushes in-memory session messages to SQLite."""
        if self.db_path == ":memory:":
            return 0
        self._init_db()
        items = self.store.search(self.conversation_namespace, limit=1000)
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                for item in items:
                    conn.execute("""
                        INSERT OR REPLACE INTO session_messages (session_id, seq_key, role, content, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        self.session_id,
                        item.key,
                        item.value["role"],
                        item.value["content"],
                        item.value.get("timestamp", time.time())
                    ))
            return len(items)
        finally:
            conn.close()

    def load_from_db(self) -> int:
        """Loads persistent session messages from SQLite into InMemoryStore."""
        if self.db_path == ":memory:" or not os.path.exists(self.db_path):
            return 0
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT seq_key, role, content, timestamp FROM session_messages WHERE session_id = ? ORDER BY seq_key ASC",
                (self.session_id,)
            )
            rows = cur.fetchall()
            for seq_key, role, content, ts in rows:
                self.store.put(
                    self.conversation_namespace,
                    seq_key,
                    {"role": role, "content": content, "timestamp": ts}
                )
                try:
                    seq_num = int(seq_key)
                    if seq_num > self._seq:
                        self._seq = seq_num
                except ValueError:
                    pass
            return len(rows)
        finally:
            conn.close()

    def clear(self) -> None:
        """Clears conversation history from both memory and SQLite for the current session."""
        items = self.store.search(self.conversation_namespace)
        for item in items:
            self.store.delete(self.conversation_namespace, item.key)
        self._seq = 0
        if self.db_path != ":memory:" and os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            try:
                with conn:
                    conn.execute("DELETE FROM session_messages WHERE session_id = ?", (self.session_id,))
            finally:
                conn.close()
