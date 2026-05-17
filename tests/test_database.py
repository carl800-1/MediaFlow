"""
数据库测试
"""

import pytest
import tempfile
import os
from pathlib import Path

from mediaflow.database.connection import Database, DatabaseConfig


class TestDatabase:
    """数据库测试"""

    def setup_method(self):
        """测试初始化"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.config = DatabaseConfig(path=self.temp_db.name)
        self.db = Database(self.config)

    def teardown_method(self):
        """测试清理"""
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_database_initialization(self):
        """测试数据库初始化"""
        assert self.db._connection is not None
        tables = self.db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [t["name"] for t in tables]
        assert "media" in table_names
        assert "torrents" in table_names
        assert "sites" in table_names
        assert "brush_tasks" in table_names
        assert "subscriptions" in table_names

    def test_execute_query(self):
        """测试执行SQL"""
        result = self.db.execute(
            "INSERT INTO sites (name, url) VALUES (?, ?)",
            ("Test Site", "https://test.com")
        )
        assert result.lastrowid > 0

    def test_fetch_one(self):
        """测试查询单条"""
        self.db.execute(
            "INSERT INTO sites (name, url) VALUES (?, ?)",
            ("Test Site", "https://test.com")
        )
        row = self.db.fetch_one(
            "SELECT * FROM sites WHERE name = ?",
            ("Test Site",)
        )
        assert row is not None
        assert row["name"] == "Test Site"

    def test_fetch_all(self):
        """测试查询所有"""
        self.db.execute(
            "INSERT INTO sites (name, url) VALUES (?, ?)",
            ("Site 1", "https://site1.com")
        )
        self.db.execute(
            "INSERT INTO sites (name, url) VALUES (?, ?)",
            ("Site 2", "https://site2.com")
        )
        rows = self.db.fetch_all("SELECT * FROM sites")
        assert len(rows) == 2

    def test_torrent_operations(self):
        """测试种子操作"""
        self.db.execute(
            """
            INSERT INTO torrents (hash, title, size, site_id)
            VALUES (?, ?, ?, ?)
            """,
            ("ABC123", "Test Torrent", 1024000, 1)
        )
        torrent = self.db.fetch_one(
            "SELECT * FROM torrents WHERE hash = ?",
            ("ABC123",)
        )
        assert torrent is not None
        assert torrent["title"] == "Test Torrent"

    def test_brushtask_operations(self):
        """测试刷流任务操作"""
        self.db.execute(
            """
            INSERT INTO brush_tasks (name, interval, state)
            VALUES (?, ?, ?)
            """,
            ("Test Task", "30", "S")
        )
        task = self.db.fetch_one(
            "SELECT * FROM brush_tasks WHERE name = ?",
            ("Test Task",)
        )
        assert task is not None
        assert task["state"] == "S"

    def test_index_creation(self):
        """测试索引创建"""
        indexes = self.db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        index_names = [i["name"] for i in indexes]
        assert "idx_torrents_hash" in index_names
        assert "idx_torrents_site" in index_names
