"""
数据库连接管理模块
"""

import sqlite3
from pathlib import Path
from typing import Optional, Any, List, Dict
from contextlib import contextmanager
from threading import Lock
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"
    path: str = "data/mediaflow.db"
    echo: bool = False


class Database:
    """数据库连接管理器"""

    _instance: Optional["Database"] = None
    _lock = Lock()

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        self._config = config or DatabaseConfig()
        self._connection: Optional[sqlite3.Connection] = None
        self._init_database()

    @classmethod
    def get_instance(cls, config: Optional[DatabaseConfig] = None) -> "Database":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
        return cls._instance

    def _init_database(self) -> None:
        """初始化数据库"""
        db_path = Path(self._config.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(str(db_path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """创建数据表"""
        cursor = self._connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                year INTEGER,
                media_type TEXT NOT NULL,
                tmdb_id INTEGER,
                imdb_id TEXT,
                imdb_rating REAL,
                poster_path TEXT,
                overview TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS torrents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                size INTEGER,
                site_id INTEGER,
                seeders INTEGER,
                leechers INTEGER,
                download_speed REAL,
                upload_speed REAL,
                completed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                cookie TEXT,
                sign_url TEXT,
                rss_url TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS brush_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                site_id INTEGER,
                downloader_id INTEGER,
                interval TEXT,
                state TEXT DEFAULT 'S',
                filter_rule TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id),
                FOREIGN KEY (downloader_id) REFERENCES downloaders(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                media_id INTEGER,
                rss_url TEXT,
                keywords TEXT,
                state TEXT DEFAULT 'Y',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloaders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER,
                username TEXT,
                password TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_torrents_hash ON torrents(hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_torrents_site ON torrents(site_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_torrents_status ON torrents(status)
        """)

        self._connection.commit()

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        yield self._connection
        self._connection.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行SQL语句"""
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        self._connection.commit()
        return cursor

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """查询单条记录"""
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """查询所有记录"""
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None


_global_database: Optional[Database] = None


def get_database() -> Database:
    """获取全局数据库实例"""
    global _global_database
    if _global_database is None:
        _global_database = Database.get_instance()
    return _global_database
