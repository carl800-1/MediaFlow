"""
集成测试

测试各模块之间的集成功能
"""

import pytest
import tempfile
import os
from pathlib import Path

from mediaflow.database.connection import Database, DatabaseConfig
from mediaflow.utils.config import ConfigManager, AppConfig
from mediaflow.brushtask.task_manager import BrushTaskManager
from mediaflow.subscribe.subscription_manager import SubscriptionManager
from mediaflow.sites.site_manager import SiteManager


class TestDatabaseIntegration:
    """数据库集成测试"""

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

    def test_site_and_brushtask_relation(self):
        """测试站点与刷流任务关联"""
        site_id = self.db.execute(
            "INSERT INTO sites (name, url) VALUES (?, ?)",
            ("Test Site", "https://test.com")
        ).lastrowid

        task_id = self.db.execute(
            "INSERT INTO brush_tasks (name, site_id, downloader_id, interval) VALUES (?, ?, ?, ?)",
            ("Test Task", site_id, 1, "30")
        ).lastrowid

        task = self.db.fetch_one("SELECT * FROM brush_tasks WHERE id = ?", (task_id,))
        assert task is not None
        assert task["site_id"] == site_id

        site = self.db.fetch_one("SELECT * FROM sites WHERE id = ?", (site_id,))
        assert site is not None
        assert site["name"] == "Test Site"


class TestConfigAndDatabase:
    """配置与数据库集成测试"""

    def test_config_loading(self):
        """测试配置加载"""
        config = ConfigManager()
        assert config.app is not None
        assert config.database is not None

    def test_database_config(self):
        """测试数据库配置"""
        config = ConfigManager()
        db_config = config.database
        assert db_config.type in ["sqlite", "mysql", "postgresql"]


class TestAPIRoutes:
    """API路由测试"""

    def test_health_endpoint(self):
        """测试健康检查端点"""
        from mediaflow.web.app import create_app

        app = create_app()
        client = app.test_client()

        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "healthy"

    def test_system_info_endpoint(self):
        """测试系统信息端点"""
        from mediaflow.web.app import create_app

        app = create_app()
        client = app.test_client()

        response = client.get("/api/system/info")
        assert response.status_code == 200

        data = response.get_json()
        assert data["data"]["name"] == "MediaFlow"


class TestManagerIntegration:
    """管理器集成测试"""

    def test_sites_and_manager(self):
        """测试站点与管理器集成"""
        site_manager = SiteManager()

        sites_before = len(site_manager.get_all_sites())
        assert sites_before >= 0

    def test_subscription_manager_initialization(self):
        """测试订阅管理器初始化"""
        sub_manager = SubscriptionManager()
        assert sub_manager is not None


class TestEndToEnd:
    """端到端测试"""

    def test_create_site_flow(self):
        """测试创建站点的完整流程"""
        from mediaflow.sites import get_site_manager, SiteInfo

        manager = get_site_manager()

        site = SiteInfo(
            id=0,
            name="Test Site E2E",
            url="https://test-e2e.com",
            enabled=True
        )

        site_id = manager.add_site(site)
        assert site_id is not None

        saved_site = manager.get_site(site_id)
        assert saved_site is not None
        assert saved_site.name == "Test Site E2E"

        manager.delete_site(site_id)

    def test_create_brushtask_flow(self):
        """测试创建刷流任务的完整流程"""
        from mediaflow.brushtask import get_brush_task_manager, BrushTaskConfig
        from mediaflow.brushtask.task import BrushTaskState

        manager = get_brush_task_manager()

        task = BrushTaskConfig(
            name="Test Brush Task E2E",
            site_id=1,
            downloader_id=1,
            interval="30",
            state=BrushTaskState.STOPPED,
            enabled=True
        )

        task_id = manager.create_task(task)
        assert task_id is not None

        saved_task = manager.get_task(task_id)
        assert saved_task is not None
        assert saved_task.name == "Test Brush Task E2E"

        manager.start_task(task_id)
        saved_task = manager.get_task(task_id)
        assert saved_task.state == BrushTaskState.RUNNING

        manager.stop_task(task_id)
        manager.delete_task(task_id)


class TestPerformance:
    """性能测试"""

    def test_database_query_performance(self):
        """测试数据库查询性能"""
        import time

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()
        config = DatabaseConfig(path=temp_db.name)
        db = Database(config)

        for i in range(100):
            db.execute(
                "INSERT INTO sites (name, url) VALUES (?, ?)",
                (f"Site {i}", f"https://site{i}.com")
            )

        start_time = time.time()
        sites = db.fetch_all("SELECT * FROM sites")
        elapsed = time.time() - start_time

        assert len(sites) == 100
        assert elapsed < 1.0

        db.close()
        os.unlink(temp_db.name)
