"""
媒体元信息解析测试
"""

import pytest
from mediaflow.media.meta import MetaParser, MetaInfo


class TestMetaParser:
    """元信息解析器测试"""

    def setup_method(self):
        """测试初始化"""
        self.parser = MetaParser()

    def test_parse_movie_title(self):
        """测试电影标题解析"""
        meta = self.parser.parse("The Shawshank Redemption 1994 1080p BluRay")
        assert meta.title
        assert meta.year == 1994
        assert meta.media_type == "movie"

    def test_parse_tv_title(self):
        """测试剧集标题解析"""
        meta = self.parser.parse("Breaking Bad S05E01 1080p WEB-DL")
        assert meta.season == 5
        assert meta.episode == 1
        assert meta.media_type == "tv"

    def test_parse_season_episode_patterns(self):
        """测试各种季集格式"""
        patterns = [
            ("S01E23", 1, 23),
            ("S2 E10", 2, 10),
            ("Season 1 Episode 5", 1, 5),
            ("S03E01-E03", 3, 1),
        ]
        for title, expected_season, expected_episode in patterns:
            meta = self.parser.parse(title)
            assert meta.season == expected_season, f"Failed for {title}"
            assert meta.episode == expected_episode, f"Failed for {title}"

    def test_parse_resolution(self):
        """测试分辨率解析"""
        resolutions = [
            ("1080p", "1080p"),
            ("720P", "720P"),
            ("4K", "4K"),
            ("2160p", "2160p"),
            ("x265", None),
        ]
        for title, expected in resolutions:
            meta = self.parser.parse(title)
            assert meta.resolution == expected, f"Failed for {title}"

    def test_parse_codec(self):
        """测试编码解析"""
        meta = self.parser.parse("Movie x265 HEVC AAC")
        assert meta.video_codec in ["x265", "HEVC"]
        assert meta.audio_codec == "AAC"

    def test_clean_title(self):
        """测试标题清理"""
        meta = self.parser.parse("Movie.Title.2023.1080p.BluRay.x264")
        assert "1080p" not in meta.title
        assert "x264" not in meta.title

    def test_normalize_title(self):
        """测试标题标准化"""
        title1 = "Movie Title (2023)"
        title2 = "movie title 2023"
        norm1 = self.parser.normalize_title(title1)
        norm2 = self.parser.normalize_title(title2)
        assert norm1 == norm2

    def test_batch_parse(self):
        """测试批量解析"""
        titles = [
            "Movie 2023 1080p",
            "TV Show S01E01",
            "Anime 720p",
        ]
        results = self.parser.parse_batch(titles)
        assert len(results) == 3
        assert all(isinstance(r, MetaInfo) for r in results)
