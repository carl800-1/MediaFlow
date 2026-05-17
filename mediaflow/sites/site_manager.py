"""
站点管理器

管理站点信息和签到等操作
"""

import threading
from typing import Dict, Optional, List
from dataclasses import dataclass

from mediaflow.utils.cli import getLogger
from mediaflow.database import get_database
from mediaflow.sites.site import SiteInfo, SiteStatistics, SignInResult


logger = getLogger("sites")


class SiteManager:
    """站点管理器"""

    _instance: Optional["SiteManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._sites: Dict[int, SiteInfo] = {}
        self._site_by_name: Dict[str, SiteInfo] = {}
        self._db = get_database()
        self._load_sites()

    @classmethod
    def get_instance(cls) -> "SiteManager":
        """获取单例实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _load_sites(self) -> None:
        """从数据库加载站点"""
        try:
            rows = self._db.fetch_all("SELECT * FROM sites WHERE enabled = 1")
            for row in rows:
                site = SiteInfo(
                    id=row["id"],
                    name=row["name"],
                    url=row["url"],
                    cookie=row.get("cookie"),
                    sign_url=row.get("sign_url"),
                    rss_url=row.get("rss_url"),
                    enabled=bool(row["enabled"]),
                )
                self._sites[site.id] = site
                self._site_by_name[site.name.lower()] = site
            logger.info(f"已加载 {len(self._sites)} 个站点")
        except Exception as e:
            logger.error(f"加载站点失败: {e}")

    def get_site(self, site_id: int) -> Optional[SiteInfo]:
        """获取指定站点"""
        return self._sites.get(site_id)

    def get_site_by_name(self, name: str) -> Optional[SiteInfo]:
        """根据名称获取站点"""
        return self._site_by_name.get(name.lower())

    def get_all_sites(self) -> List[SiteInfo]:
        """获取所有站点"""
        return list(self._sites.values())

    def get_enabled_sites(self) -> List[SiteInfo]:
        """获取已启用的站点"""
        return [site for site in self._sites.values() if site.enabled]

    def get_statistics(self) -> SiteStatistics:
        """获取站点统计"""
        sites = self.get_all_sites()
        return SiteStatistics(
            total_sites=len(sites),
            enabled_sites=len(self.get_enabled_sites()),
            total_upload=sum(s.upload or 0 for s in sites),
            total_download=sum(s.download or 0 for s in sites),
            total_seeding=sum(s.seeding for s in sites),
        )

    def add_site(self, site: SiteInfo) -> Optional[int]:
        """添加站点"""
        try:
            cursor = self._db.execute(
                """
                INSERT INTO sites (name, url, cookie, sign_url, rss_url, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (site.name, site.url, site.cookie, site.sign_url, site.rss_url,
                 1 if site.enabled else 0)
            )
            site_id = cursor.lastrowid
            site.id = site_id
            self._sites[site_id] = site
            self._site_by_name[site.name.lower()] = site
            logger.info(f"添加站点成功: {site.name}")
            return site_id
        except Exception as e:
            logger.error(f"添加站点失败: {e}")
            return None

    def update_site(self, site_id: int, site: SiteInfo) -> bool:
        """更新站点"""
        try:
            self._db.execute(
                """
                UPDATE sites
                SET name = ?, url = ?, cookie = ?, sign_url = ?, rss_url = ?, enabled = ?
                WHERE id = ?
                """,
                (site.name, site.url, site.cookie, site.sign_url, site.rss_url,
                 1 if site.enabled else 0, site_id)
            )
            self._sites[site_id] = site
            self._site_by_name[site.name.lower()] = site
            logger.info(f"更新站点成功: {site.name}")
            return True
        except Exception as e:
            logger.error(f"更新站点失败: {e}")
            return False

    def delete_site(self, site_id: int) -> bool:
        """删除站点"""
        try:
            site = self._sites.get(site_id)
            if site:
                self._site_by_name.pop(site.name.lower(), None)
            self._sites.pop(site_id, None)
            self._db.execute("DELETE FROM sites WHERE id = ?", (site_id,))
            logger.info(f"删除站点: {site_id}")
            return True
        except Exception as e:
            logger.error(f"删除站点失败: {e}")
            return False

    def update_site_cookie(self, site_id: int, cookie: str) -> bool:
        """更新站点Cookie"""
        try:
            self._db.execute(
                "UPDATE sites SET cookie = ? WHERE id = ?",
                (cookie, site_id)
            )
            if site_id in self._sites:
                self._sites[site_id].cookie = cookie
            logger.info(f"更新站点Cookie: {site_id}")
            return True
        except Exception as e:
            logger.error(f"更新站点Cookie失败: {e}")
            return False

    def update_site_stats(self, site_id: int, stats: Dict) -> bool:
        """更新站点统计信息"""
        try:
            fields = []
            values = []
            for key, value in stats.items():
                fields.append(f"{key} = ?")
                values.append(value)

            if fields:
                values.append(site_id)
                self._db.execute(
                    f"UPDATE sites SET {', '.join(fields)} WHERE id = ?",
                    tuple(values)
                )

            if site_id in self._sites:
                site = self._sites[site_id]
                for key, value in stats.items():
                    if hasattr(site, key):
                        setattr(site, key, value)

            return True
        except Exception as e:
            logger.error(f"更新站点统计失败: {e}")
            return False

    def sign_in(self, site_id: int) -> SignInResult:
        """站点签到"""
        site = self.get_site(site_id)
        if not site:
            return SignInResult(
                site_name="Unknown",
                success=False,
                message="站点不存在"
            )

        if not site.sign_url:
            return SignInResult(
                site_name=site.name,
                success=False,
                message="未配置签到URL"
            )

        try:
            import requests
            response = requests.get(
                site.sign_url,
                cookies={"cookie": site.cookie} if site.cookie else {},
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"站点 {site.name} 签到成功")
                return SignInResult(
                    site_name=site.name,
                    success=True,
                    message="签到成功",
                    bonus=0
                )
            else:
                return SignInResult(
                    site_name=site.name,
                    success=False,
                    message=f"签到失败: {response.status_code}"
                )
        except Exception as e:
            logger.error(f"站点 {site.name} 签到失败: {e}")
            return SignInResult(
                site_name=site.name,
                success=False,
                message=f"签到异常: {str(e)}"
            )

    def sign_in_all(self) -> List[SignInResult]:
        """批量签到所有站点"""
        results = []
        for site in self.get_enabled_sites():
            if site.sign_url:
                result = self.sign_in(site.id)
                results.append(result)
        return results


_global_site_manager: Optional[SiteManager] = None


def get_site_manager() -> SiteManager:
    """获取全局站点管理器"""
    global _global_site_manager
    if _global_site_manager is None:
        _global_site_manager = SiteManager.get_instance()
    return _global_site_manager
