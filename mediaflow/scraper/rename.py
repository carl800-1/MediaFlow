"""
媒体文件重命名器
"""

import os
import shutil
from typing import Optional, List, Dict
from pathlib import Path

from mediaflow.utils.cli import getLogger
from mediaflow.scraper.scraper import ScraperMediaInfo, MediaScraper


logger = getLogger("renamer")


class MediaRenamer:
    """媒体文件重命名器"""

    def __init__(self, naming_template: str = None) -> None:
        self._naming_template = naming_template or "{title}/{title} ({year})"
        self._scraper = MediaScraper()

    def rename(self, file_path: str, media_info: ScraperMediaInfo,
               target_dir: str, create_dir: bool = True) -> Optional[str]:
        """重命名并移动文件"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None

            new_name = self.generate_filename(media_info, file_path.suffix)
            target_path = Path(target_dir) / new_name

            if create_dir:
                target_path.parent.mkdir(parents=True, exist_ok=True)

            if target_path.exists():
                logger.warning(f"目标文件已存在: {target_path}")
                return None

            shutil.move(str(file_path), str(target_path))
            logger.info(f"文件已移动: {file_path} -> {target_path}")
            return str(target_path)

        except Exception as e:
            logger.error(f"重命名失败: {e}")
            return None

    def copy(self, file_path: str, media_info: ScraperMediaInfo,
             target_dir: str, create_dir: bool = True) -> Optional[str]:
        """复制并重命名文件"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None

            new_name = self.generate_filename(media_info, file_path.suffix)
            target_path = Path(target_dir) / new_name

            if create_dir:
                target_path.parent.mkdir(parents=True, exist_ok=True)

            if target_path.exists():
                logger.warning(f"目标文件已存在: {target_path}")
                return None

            shutil.copy2(str(file_path), str(target_path))
            logger.info(f"文件已复制: {file_path} -> {target_path}")
            return str(target_path)

        except Exception as e:
            logger.error(f"复制失败: {e}")
            return None

    def generate_filename(self, media_info: ScraperMediaInfo, extension: str = ".mkv") -> str:
        """生成文件名"""
        if media_info.media_type == "tv":
            filename = self._generate_tv_filename(media_info)
        else:
            filename = self._generate_movie_filename(media_info)

        if not filename.endswith(extension.lower()) and not filename.endswith(extension.upper()):
            filename += extension.lower()

        return filename

    def _generate_movie_filename(self, media_info: ScraperMediaInfo) -> str:
        """生成电影文件名"""
        parts = []

        title = media_info.title or "Unknown"
        title = self._clean_filename(title)
        parts.append(title)

        if media_info.year:
            parts.append(f"({media_info.year})")

        quality = []
        if media_info.resolution:
            quality.append(media_info.resolution)
        if media_info.video_codec:
            quality.append(media_info.video_codec)
        if media_info.audio_codec:
            quality.append(media_info.audio_codec)

        if quality:
            parts.append(f"[{'-'.join(quality)}]")

        if media_info.release_group:
            parts.append(f"[{media_info.release_group}]")

        return " ".join(parts)

    def _generate_tv_filename(self, media_info: ScraperMediaInfo) -> str:
        """生成剧集文件名"""
        parts = []

        title = media_info.title or "Unknown"
        title = self._clean_filename(title)
        parts.append(title)

        if media_info.season and media_info.episode:
            parts.append(f"S{media_info.season:02d}E{media_info.episode:02d}")

        if media_info.episode_title:
            episode_title = self._clean_filename(media_info.episode_title)
            parts.append(f"- {episode_title}")

        quality = []
        if media_info.resolution:
            quality.append(media_info.resolution)

        if quality:
            parts.append(f"[{'-'.join(quality)}]")

        return " ".join(parts)

    def _clean_filename(self, filename: str) -> str:
        """清理文件名"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        filename = filename.strip('. ')

        return filename or "Unknown"

    def batch_rename(self, files: List[str], target_dir: str,
                     dry_run: bool = False) -> List[Dict[str, str]]:
        """批量重命名"""
        results = []

        for file_path in files:
            try:
                media_info = self._scraper.scrape(file_path)
                if not media_info:
                    results.append({
                        "source": file_path,
                        "target": None,
                        "status": "failed",
                        "reason": "刮削失败"
                    })
                    continue

                if dry_run:
                    new_path = Path(target_dir) / self.generate_filename(media_info, Path(file_path).suffix)
                    results.append({
                        "source": file_path,
                        "target": str(new_path),
                        "status": "pending"
                    })
                else:
                    new_path = self.rename(file_path, media_info, target_dir)
                    if new_path:
                        results.append({
                            "source": file_path,
                            "target": new_path,
                            "status": "success"
                        })
                    else:
                        results.append({
                            "source": file_path,
                            "target": None,
                            "status": "failed"
                        })

            except Exception as e:
                logger.error(f"批量重命名失败: {file_path} - {e}")
                results.append({
                    "source": file_path,
                    "target": None,
                    "status": "failed",
                    "reason": str(e)
                })

        return results


class NamingService:
    """命名服务"""

    MOVIE_TEMPLATE = "{title} ({year})"

    TV_TEMPLATE = "{title}/Season {season}/{title} S{season:02d}E{episode:02d}"

    @staticmethod
    def get_movie_naming_pattern(title: str, year: int = None, quality: str = None,
                                 media_info: ScraperMediaInfo = None) -> str:
        """获取电影命名模式"""
        if media_info:
            title = media_info.title or title
            year = year or media_info.year
            quality = quality or media_info.resolution

        title = title or "Unknown"
        year = year or ""

        pattern = f"{title}"
        if year:
            pattern += f" ({year})"

        if quality:
            pattern += f" [{quality}]"

        return pattern

    @staticmethod
    def get_tv_naming_pattern(title: str, season: int, episode: int,
                              episode_title: str = None, media_info: ScraperMediaInfo = None) -> str:
        """获取剧集命名模式"""
        if media_info:
            title = media_info.title or title
            episode_title = episode_title or media_info.episode_title

        title = title or "Unknown"
        season = season or 1
        episode = episode or 1

        pattern = f"{title}/Season {season:02d}/{title} S{season:02d}E{episode:02d}"

        if episode_title:
            pattern += f" - {episode_title}"

        return pattern
