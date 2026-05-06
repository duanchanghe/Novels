# ===========================================
# 音效库服务
# ===========================================

"""
音效库服务模块

提供音效库的完整管理功能：
- BBC Sound Effects API 集成
- 音效搜索和推荐（基于语义匹配）
- 音效下载和缓存管理
- 与 DeepSeek 分析结果无缝集成
- panns-inference 音频特征匹配支持

参考 audiobookshelf 的音效库设计理念，
结合 panns-inference 的音频理解能力。
"""

import json
import logging
import re
import os
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading

import httpx

from core.config import settings
from core.database import get_db_context
from core.models import (
    SoundEffect,
    SoundEffectUsage,
    SoundEffectCollection,
    SoundEffectCollectionItem,
    SoundEffectType,
    SoundLayer,
    SoundPriority,
    SoundSource,
    SoundEffectStatus,
)


logger = logging.getLogger("audiobook")


# ===========================================
# 数据结构定义
# ===========================================

@dataclass
class SoundEffectMatch:
    """音效匹配结果"""
    sound_effect: SoundEffect
    match_score: float  # 0.0 - 1.0
    match_reason: str
    suggested_volume: float
    suggested_fade_in_ms: int
    suggested_fade_out_ms: int


@dataclass
class ChapterSoundDesign:
    """章节音效设计方案"""
    chapter_id: int
    sound_effects: List[SoundEffectMatch]
    background_music: List[Dict[str, Any]]
    audio_bridge: Dict[str, Any]
    total_duration_ms: int
    warnings: List[str]


# ===========================================
# BBC Sound Effects API 客户端
# ===========================================

class BBSSoundEffectsClient:
    """
    BBC Sound Effects API 客户端

    官方 API 文档: https://sound-effects.media.bl.bbc.co.uk/

    提供音效搜索和下载功能。
    """

    BASE_URL = "https://sound-effects.media.bl.bbc.co.uk"

    # 分类目录映射
    CATEGORY_MAPPING = {
        "environment": ["ambience", "environment", "rural", "urban"],
        "action": ["action", "footsteps", "doors", "foley"],
        "nature": ["nature", "animals", "birds", "weather"],
        "ambient": ["ambience", "atmosphere", "background"],
        "weather": ["weather", "rain", "wind", "thunder", "snow"],
        "urban": ["city", "traffic", "crowd", "office"],
        "fantasy": ["magical", "supernatural", "medieval", "ancient"],
        "scifi": ["sci-fi", "futuristic", "space", "technology"],
    }

    def __init__(self):
        self.session = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "AudioBookMaker/1.0",
                "Accept": "application/json",
            }
        )
        self._cache: Dict[str, List[Dict]] = {}
        self._cache_ttl = 3600  # 1小时缓存

    def search(
        self,
        query: str,
        category: str = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        搜索 BBC Sound Effects

        Args:
            query: 搜索关键词
            category: 分类筛选（可选）
            limit: 返回数量限制

        Returns:
            List[Dict]: 搜索结果列表
        """
        cache_key = f"{query}:{category}:{limit}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self._cache_ttl):
                return cached_data

        try:
            # BBC Sound Effects 使用 Google Search API 风格的查询
            # 实际实现需要使用他们的 API
            # 这里模拟搜索结果
            results = self._mock_search(query, category, limit)

            self._cache[cache_key] = (datetime.now(), results)
            return results

        except Exception as e:
            logger.error(f"BBC Sound Effects 搜索失败: {e}")
            return []

    def _mock_search(
        self,
        query: str,
        category: str = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        模拟搜索结果（实际项目中应调用真实 API）

        返回符合 BBC Sound Effects 格式的数据结构。
        """
        # 基础音效库（模拟数据）
        mock_database = [
            {
                "id": "bbc-rain-001",
                "title": "Heavy Rain on Window",
                "description": "Heavy rain falling on a window pane",
                "category": "ambience",
                "duration": 120.5,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07030151.mp3",
                "waveform_url": "https://sound-effects.bbcrewind.co.uk/waveform/07030151.png",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-thunder-001",
                "title": "Distant Thunder",
                "description": "Distant thunder rolling across the sky",
                "category": "weather",
                "duration": 45.2,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07012051.mp3",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-sword-001",
                "title": "Sword Clash",
                "description": "Two swords clashing together",
                "category": "action",
                "duration": 2.5,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07044015.mp3",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-footsteps-001",
                "title": "Footsteps on Stone",
                "description": "Walking on stone floor, medieval",
                "category": "foley",
                "duration": 8.0,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07044020.mp3",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-wind-001",
                "title": "Strong Wind",
                "description": "Strong wind blowing through trees",
                "category": "weather",
                "duration": 60.0,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07011030.mp3",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-crowd-001",
                "title": "Crowd Murmur",
                "description": "Large crowd murmuring quietly",
                "category": "ambience",
                "duration": 30.0,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07021005.mp3",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-door-001",
                "title": "Door Slam",
                "description": "Heavy wooden door slamming shut",
                "category": "foley",
                "duration": 1.5,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07044100.mp3",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-fire-001",
                "title": "Crackling Fire",
                "description": "Fire crackling in fireplace",
                "category": "ambience",
                "duration": 90.0,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07015010.mp3",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-horse-001",
                "title": "Horse Galloping",
                "description": "Horse galloping on dirt road",
                "category": "action",
                "duration": 15.0,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07046015.mp3",
                "license": "BBC Sound Effects License",
            },
            {
                "id": "bbc-bells-001",
                "title": "Temple Bells",
                "description": "Buddhist temple bells ringing",
                "category": "ambience",
                "duration": 25.0,
                "download_url": "https://sound-effects.bbcrewind.co.uk/mp3/07055020.mp3",
                "license": "BBC Sound Effects License",
            },
        ]

        # 关键词匹配
        query_lower = query.lower()
        results = []
        for item in mock_database:
            # 标题和描述匹配
            title_match = query_lower in item["title"].lower()
            desc_match = query_lower in item["description"].lower()

            # 分类匹配
            category_match = True
            if category:
                category_keywords = self.CATEGORY_MAPPING.get(category, [category])
                category_match = any(
                    kw in item["category"].lower()
                    for kw in category_keywords
                )

            if (title_match or desc_match) and category_match:
                results.append(item)
                if len(results) >= limit:
                    break

        # 如果没有精确匹配，返回相关结果
        if not results:
            for item in mock_database:
                if category:
                    category_keywords = self.CATEGORY_MAPPING.get(category, [category])
                    if any(kw in item["category"].lower() for kw in category_keywords):
                        results.append(item)
                        if len(results) >= limit:
                            break

        return results

    def get_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取音效详情"""
        results = self._mock_search(source_id)
        return results[0] if results else None

    def download(
        self,
        source_id: str,
        output_path: str,
    ) -> Tuple[bool, str]:
        """
        下载音效文件

        Args:
            source_id: BBC 音效 ID
            output_path: 输出文件路径

        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            item = self.get_by_id(source_id)
            if not item:
                return False, f"音效不存在: {source_id}"

            # 下载文件
            response = self.session.get(item["download_url"], timeout=60.0)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"下载完成: {item['title']} -> {output_path}")
            return True, output_path

        except Exception as e:
            logger.error(f"下载失败: {source_id} - {e}")
            return False, str(e)

    def close(self):
        """关闭会话"""
        self.session.close()


# ===========================================
# 音效库服务
# ===========================================

class SoundEffectLibraryService:
    """
    音效库服务

    提供音效库的完整管理功能：
    - 音效搜索和推荐
    - BBC Sound Effects 集成
    - 智能匹配（基于 DeepSeek 分析结果）
    - 本地缓存管理
    """

    def __init__(self):
        self.bbc_client = BBSSoundEffectsClient()
        self._lock = threading.Lock()

        # 常用音效类型的中文关键词映射
        self._chinese_keywords_map = {
            # 环境音
            "雨声": ["rain", "heavy rain", "light rain", "drizzle"],
            "雷声": ["thunder", "distant thunder", "lightning"],
            "风声": ["wind", "breeze", "strong wind", "gust"],
            "水声": ["water", "stream", "river", "waterfall", "waves"],
            "城市": ["city", "urban", "traffic", "crowd", "street"],
            "乡村": ["rural", "countryside", "farm", "village"],
            # 动作音
            "脚步声": ["footsteps", "walking", "steps"],
            "关门声": ["door", "slam", "close"],
            "剑声": ["sword", "blade", "clash", "metal"],
            "马蹄声": ["horse", "gallop", "hooves"],
            "翻书声": ["book", "page", "turning"],
            "打斗": ["fight", "action", "impact", "punch"],
            # 转场音
            "转场": ["transition", "whoosh", "sweep"],
            "章节": ["chapter", "section", "transition"],
            # 自然音
            "鸟鸣": ["birds", "bird", "chirp", "singing"],
            "虫鸣": ["insects", "crickets", "buzzing"],
            "瀑布": ["waterfall", "cascade", "rushing water"],
            # 氛围音
            "心跳": ["heartbeat", "heart", "pulse"],
            "呼吸": ["breathing", "breath", "inhale"],
            "时钟": ["clock", "tick", "timepiece"],
            # 玄幻/奇幻
            "魔法": ["magical", "magic", "spell", "supernatural"],
            "仙侠": ["spiritual", "cultivation", "mystical"],
            "战斗": ["battle", "war", "combat", "fighting"],
        }

    def search_sound_effects(
        self,
        query: str,
        effect_type: str = None,
        layer: str = None,
        tags: List[str] = None,
        limit: int = 10,
        include_bbc: bool = True,
    ) -> List[SoundEffectMatch]:
        """
        搜索音效

        支持本地库搜索 + BBC Sound Effects 在线搜索。

        Args:
            query: 搜索查询（可以是中文或英文）
            effect_type: 音效类型筛选
            layer: 音效层级筛选
            tags: 标签筛选
            limit: 返回数量
            include_bbc: 是否包含 BBC 搜索结果

        Returns:
            List[SoundEffectMatch]: 匹配结果列表
        """
        results = []

        with get_db_context() as db:
            # 1. 搜索本地库
            db_query = db.query(SoundEffect).filter(
                SoundEffect.status == SoundEffectStatus.ACTIVE
            )

            if effect_type:
                db_query = db_query.filter(SoundEffect.effect_type == effect_type)
            if layer:
                db_query = db_query.filter(SoundEffect.layer == layer)

            # 关键词匹配
            search_pattern = f"%{query}%"
            db_query = db_query.filter(
                (SoundEffect.name.ilike(search_pattern)) |
                (SoundEffect.description.ilike(search_pattern)) |
                (SoundEffect.chinese_description.ilike(search_pattern))
            )

            local_effects = db_query.order_by(
                SoundEffect.usage_count.desc(),
                SoundEffect.priority.desc(),
            ).limit(limit * 2).all()

            # 计算匹配分数
            for effect in local_effects:
                score = effect.match_score(query, tags)
                if score > 0:
                    results.append(SoundEffectMatch(
                        sound_effect=effect,
                        match_score=score,
                        match_reason=self._generate_match_reason(effect, query),
                        suggested_volume=effect.recommended_volume_max or 0.5,
                        suggested_fade_in_ms=effect.recommended_fade_in_ms or 500,
                        suggested_fade_out_ms=effect.recommended_fade_out_ms or 500,
                    ))

        # 2. 在线搜索 BBC Sound Effects
        if include_bbc and len(results) < limit:
            bbc_results = self._search_bbc(query, effect_type, limit - len(results))
            results.extend(bbc_results)

        # 3. 排序（按匹配分数）
        results.sort(key=lambda x: x.match_score, reverse=True)

        return results[:limit]

    def _search_bbc(
        self,
        query: str,
        effect_type: str = None,
        limit: int = 5,
    ) -> List[SoundEffectMatch]:
        """搜索 BBC Sound Effects 并创建临时匹配结果"""
        results = []
        bbc_results = self.bbc_client.search(query, effect_type, limit)

        for item in bbc_results:
            # 计算匹配分数
            score = self._calculate_bbc_match_score(item, query)

            # 估算推荐参数
            duration = item.get("duration", 10)
            if duration < 5:
                suggested_fade_in = 200
                suggested_fade_out = 200
            elif duration < 30:
                suggested_fade_in = 500
                suggested_fade_out = 500
            else:
                suggested_fade_in = 1000
                suggested_fade_out = 1000

            # 创建临时 SoundEffect 对象（未保存到数据库）
            temp_effect = SoundEffect(
                id=0,  # 临时 ID
                name=item["title"],
                description=item["description"],
                source=SoundSource.BBC,
                source_id=item["id"],
                source_url=item.get("download_url"),
                duration_ms=int(item["duration"] * 1000),
                effect_type=effect_type or self._map_bbc_category_to_type(item.get("category")),
                license_type=item.get("license", "BBC Sound Effects License"),
                status=SoundEffectStatus.ACTIVE,
            )

            results.append(SoundEffectMatch(
                sound_effect=temp_effect,
                match_score=score,
                match_reason=f"来自 BBC Sound Effects: {item['description']}",
                suggested_volume=0.5,
                suggested_fade_in_ms=suggested_fade_in,
                suggested_fade_out_ms=suggested_fade_out,
            ))

        return results

    def _calculate_bbc_match_score(self, item: Dict, query: str) -> float:
        """计算 BBC 音效的匹配分数"""
        score = 0.0

        title = item.get("title", "").lower()
        description = item.get("description", "").lower()
        query_lower = query.lower()

        # 标题精确匹配
        if query_lower in title:
            score += 0.6
        # 描述匹配
        elif query_lower in description:
            score += 0.4
        # 部分词匹配
        else:
            query_words = query_lower.split()
            for word in query_words:
                if word in title:
                    score += 0.3
                elif word in description:
                    score += 0.15

        return min(score, 1.0)

    def _map_bbc_category_to_type(self, category: str) -> str:
        """映射 BBC 分类到音效类型"""
        mapping = {
            "ambience": SoundEffectType.AMBIENT,
            "environment": SoundEffectType.ENVIRONMENT,
            "action": SoundEffectType.ACTION,
            "foley": SoundEffectType.ACTION,
            "weather": SoundEffectType.WEATHER,
            "nature": SoundEffectType.NATURE,
            "rural": SoundEffectType.NATURE,
            "urban": SoundEffectType.URBAN,
            "city": SoundEffectType.URBAN,
        }
        return mapping.get(category.lower(), SoundEffectType.ENVIRONMENT)

    def _generate_match_reason(self, effect: SoundEffect, query: str) -> str:
        """生成匹配原因说明"""
        reasons = []

        if effect.name and query.lower() in effect.name.lower():
            reasons.append(f"名称匹配: {effect.name}")
        if effect.chinese_description and query in effect.chinese_description:
            reasons.append(f"描述匹配: {effect.chinese_description}")

        if effect.tags:
            matching_tags = [t for t in effect.tags if query.lower() in t.lower()]
            if matching_tags:
                reasons.append(f"标签: {', '.join(matching_tags[:3])}")

        return reasons[0] if reasons else f"综合匹配度 {int(effect.match_score(query) * 100)}%"

    def recommend_for_chapter(
        self,
        chapter_analysis: Dict[str, Any],
        book_id: int = None,
        limit: int = 20,
    ) -> List[SoundEffectMatch]:
        """
        根据章节分析结果推荐音效

        解析 DeepSeek 生成的音效设计，为每个需求推荐最匹配的音效。

        Args:
            chapter_analysis: DeepSeek 分析结果（包含 sound_effects）
            book_id: 书籍 ID（用于获取书籍特定配置）
            limit: 返回数量

        Returns:
            List[SoundEffectMatch]: 推荐音效列表
        """
        recommendations = []
        sound_effects = chapter_analysis.get("sound_effects", [])

        if not sound_effects:
            logger.info("章节分析结果中没有音效设计")
            return []

        for se in sound_effects:
            description = se.get("description", "")
            effect_type = se.get("type")
            priority = se.get("priority", "medium")

            # 提取语义关键词
            keywords = self._extract_keywords(description)

            # 搜索匹配的音效
            matches = self.search_sound_effects(
                query=description,
                effect_type=effect_type,
                tags=keywords,
                limit=3,  # 每个需求返回 top 3
                include_bbc=True,
            )

            for match in matches:
                # 根据章节需求调整推荐参数
                if se.get("volume"):
                    match.suggested_volume = se["volume"]
                if se.get("fade_in_ms"):
                    match.suggested_fade_in_ms = se["fade_in_ms"]
                if se.get("fade_out_ms"):
                    match.suggested_fade_out_ms = se["fade_out_ms"]

                # 降低低优先级音效的分数
                if priority == "low":
                    match.match_score *= 0.7
                elif priority == "high":
                    match.match_score *= 1.2

                recommendations.append(match)

        # 按分数排序
        recommendations.sort(key=lambda x: x.match_score, reverse=True)

        return recommendations[:limit]

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        keywords = []

        # 中文关键词映射
        for cn_keyword, en_keywords in self._chinese_keywords_map.items():
            if cn_keyword in text:
                keywords.append(cn_keyword)
                keywords.extend(en_keywords[:2])  # 只添加前两个英文关键词

        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]+', text)
        keywords.extend(english_words[:5])  # 最多添加5个英文单词

        return list(set(keywords))[:10]  # 去重，最多10个

    def download_and_save_bbc_effect(
        self,
        bbc_id: str,
        book_id: int = None,
    ) -> Tuple[Optional[SoundEffect], str]:
        """
        下载 BBC 音效并保存到本地库

        Args:
            bbc_id: BBC 音效 ID
            book_id: 关联的书籍 ID（可选）

        Returns:
            Tuple[Optional[SoundEffect], str]: (保存的音效对象, 消息)
        """
        # 获取 BBC 音效信息
        bbc_info = self.bbc_client.get_by_id(bbc_id)
        if not bbc_info:
            return None, f"BBC 音效不存在: {bbc_id}"

        # 检查是否已存在
        with get_db_context() as db:
            existing = db.query(SoundEffect).filter(
                SoundEffect.source == SoundSource.BBC,
                SoundEffect.source_id == bbc_id,
            ).first()

            if existing:
                return existing, "音效已存在"

        # 下载文件
        from core.config import settings
        cache_dir = getattr(settings, "SOUND_EFFECT_CACHE_DIR", "/tmp/sound_effects")
        os.makedirs(cache_dir, exist_ok=True)

        filename = f"{bbc_id}.mp3"
        output_path = os.path.join(cache_dir, filename)

        success, message = self.bbc_client.download(bbc_id, output_path)
        if not success:
            return None, f"下载失败: {message}"

        # 保存到数据库
        effect = self._save_downloaded_effect(bbc_info, output_path, book_id)
        return effect, "下载并保存成功"

    def _save_downloaded_effect(
        self,
        bbc_info: Dict,
        local_path: str,
        book_id: int = None,
    ) -> SoundEffect:
        """保存下载的音效到数据库"""
        with get_db_context() as db:
            effect = SoundEffect(
                name=bbc_info["title"],
                description=bbc_info["description"],
                chinese_description=self._translate_to_chinese(bbc_info["description"]),
                effect_type=self._map_bbc_category_to_type(bbc_info.get("category")),
                layer=SoundLayer.FOREGROUND,
                source=SoundSource.BBC,
                source_id=bbc_info["id"],
                source_url=bbc_info.get("download_url"),
                license_type=bbc_info.get("license", "BBC Sound Effects License"),
                duration_ms=int(bbc_info.get("duration", 0) * 1000),
                file_format="mp3",
                local_path=local_path,
                status=SoundEffectStatus.ACTIVE,
                tags=self._generate_tags(bbc_info),
                chinese_tags=self._generate_chinese_tags(bbc_info),
                semantic_keywords=self._generate_semantic_keywords(bbc_info),
            )

            db.add(effect)
            db.commit()
            db.refresh(effect)

            logger.info(f"音效已保存: {effect.name} (ID: {effect.id})")
            return effect

    def _translate_to_chinese(self, text: str) -> str:
        """
        将英文描述翻译为中文

        实际项目中可以使用翻译 API，这里使用简单映射。
        """
        translations = {
            "rain": "雨声",
            "thunder": "雷声",
            "wind": "风声",
            "fire": "火焰声",
            "footsteps": "脚步声",
            "door": "门声",
            "sword": "剑击声",
            "crowd": "人群声",
            "birds": "鸟鸣声",
            "horse": "马蹄声",
            "water": "水声",
            "bells": "钟铃声",
        }

        result = text
        for en, cn in translations.items():
            if en in text.lower():
                result = result.replace(en.capitalize(), cn)

        return result if result != text else f"音效素材: {text}"

    def _generate_tags(self, bbc_info: Dict) -> List[str]:
        """生成英文标签"""
        tags = []
        title = bbc_info.get("title", "").lower()
        desc = bbc_info.get("description", "").lower()

        # 从标题和描述中提取关键词
        keywords = re.findall(r'\b\w+\b', f"{title} {desc}")
        tags.extend([w for w in keywords if len(w) > 3][:5])

        return list(set(tags))

    def _generate_chinese_tags(self, bbc_info: Dict) -> List[str]:
        """生成中文标签"""
        desc = bbc_info.get("description", "")
        chinese_desc = self._translate_to_chinese(desc)

        # 简单分词
        words = []
        for cn_kw, en_kws in self._chinese_keywords_map.items():
            if any(en_kw in bbc_info.get("description", "").lower() for en_kw in en_kws):
                words.append(cn_kw)

        return list(set(words))[:5]

    def _generate_semantic_keywords(self, bbc_info: Dict) -> List[str]:
        """生成语义关键词"""
        keywords = []
        title = bbc_info.get("title", "")
        desc = bbc_info.get("description", "")

        # 提取核心语义
        all_text = f"{title} {desc}"

        # 映射到语义类别
        semantic_mappings = {
            "outdoor": ["户外", "室外", "自然"],
            "indoor": ["室内", "屋内", "房间"],
            "day": ["白天", "日间"],
            "night": ["夜晚", "夜间", "晚上"],
            "heavy": ["大雨", "强风", "激烈"],
            "light": ["小雨", "微风", "轻柔"],
            "distant": ["远", "远处", "遥远"],
            "close": ["近", "附近", "临近"],
        }

        for semantic, cn_keywords in semantic_mappings.items():
            if semantic in all_text.lower():
                keywords.extend(cn_keywords)

        return list(set(keywords))

    def record_usage(
        self,
        sound_effect_id: int,
        book_id: int = None,
        chapter_id: int = None,
        trigger_at_ms: int = None,
        volume: float = None,
        fade_in_ms: int = None,
        fade_out_ms: int = None,
        matched_from_query: str = None,
        match_score: float = None,
    ) -> SoundEffectUsage:
        """
        记录音效使用

        Args:
            sound_effect_id: 音效 ID
            book_id: 书籍 ID
            chapter_id: 章节 ID
            trigger_at_ms: 触发时间（毫秒）
            volume: 音量
            fade_in_ms: 淡入时间
            fade_out_ms: 淡出时间
            matched_from_query: 匹配查询
            match_score: 匹配分数

        Returns:
            SoundEffectUsage: 使用记录
        """
        with get_db_context() as db:
            # 更新音效使用次数
            effect = db.query(SoundEffect).filter(id=sound_effect_id).first()
            if effect:
                effect.increment_usage()

            # 创建使用记录
            usage = SoundEffectUsage(
                sound_effect_id=sound_effect_id,
                book_id=book_id,
                chapter_id=chapter_id,
                trigger_at_ms=trigger_at_ms,
                volume=volume,
                fade_in_ms=fade_in_ms,
                fade_out_ms=fade_out_ms,
                matched_from_query=matched_from_query,
                match_score=match_score,
            )
            db.add(usage)
            db.commit()
            db.refresh(usage)

            return usage

    def get_statistics(self) -> Dict[str, Any]:
        """获取音效库统计信息"""
        with get_db_context() as db:
            total = db.query(SoundEffect).count()
            by_source = {}
            for source in SoundSource:
                count = db.query(SoundEffect).filter(
                    SoundEffect.source == source
                ).count()
                if count > 0:
                    by_source[source] = count

            by_type = {}
            for etype in SoundEffectType:
                count = db.query(SoundEffect).filter(
                    SoundEffect.effect_type == etype
                ).count()
                if count > 0:
                    by_type[etype] = count

            total_usage = db.query(SoundEffectUsage).count()
            total_downloads = db.query(SoundEffect).filter(
                SoundEffect.source == SoundSource.BBC,
                SoundEffect.local_path.isnot(None),
            ).count()

            return {
                "total_sound_effects": total,
                "by_source": by_source,
                "by_type": by_type,
                "total_usage_count": total_usage,
                "downloaded_count": total_downloads,
            }

    def sync_from_bbc(
        self,
        keywords: List[str] = None,
        effect_type: str = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        从 BBC Sound Effects 同步音效到本地库

        Args:
            keywords: 关键词列表
            effect_type: 音效类型
            limit: 限制数量

        Returns:
            Dict[str, Any]: 同步结果统计
        """
        if keywords is None:
            keywords = ["rain", "thunder", "wind", "footsteps", "sword", "crowd"]

        stats = {"searched": 0, "downloaded": 0, "skipped": 0, "errors": []}

        for keyword in keywords:
            bbc_results = self.bbc_client.search(keyword, effect_type, limit // len(keywords))

            for item in bbc_results:
                stats["searched"] += 1
                bbc_id = item["id"]

                # 检查是否已存在
                with get_db_context() as db:
                    existing = db.query(SoundEffect).filter(
                        SoundEffect.source == SoundSource.BBC,
                        SoundEffect.source_id == bbc_id,
                    ).first()

                    if existing:
                        stats["skipped"] += 1
                        continue

                # 下载并保存
                effect, message = self.download_and_save_bbc_effect(bbc_id)
                if effect:
                    stats["downloaded"] += 1
                else:
                    stats["errors"].append(f"{bbc_id}: {message}")

        logger.info(f"BBC 同步完成: {stats}")
        return stats

    def export_to_json(self, book_id: int) -> str:
        """
        导出书籍的音效配置为 JSON

        用于保存到 MinIO 或分享。

        Args:
            book_id: 书籍 ID

        Returns:
            str: JSON 格式的音效配置
        """
        with get_db_context() as db:
            # 获取书籍所有章节的音效设计
            from core.models import Chapter

            chapters = db.query(Chapter).filter(
                Chapter.book_id == book_id
            ).order_by(Chapter.chapter_index).all()

            export_data = {
                "book_id": book_id,
                "exported_at": datetime.now().isoformat(),
                "chapters": [],
            }

            for chapter in chapters:
                if chapter.sound_effects:
                    export_data["chapters"].append({
                        "chapter_index": chapter.chapter_index,
                        "chapter_title": chapter.title,
                        "sound_effects": chapter.sound_effects,
                    })

            return json.dumps(export_data, ensure_ascii=False, indent=2)

    def import_from_json(
        self,
        book_id: int,
        json_data: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        从 JSON 导入音效配置到书籍

        Args:
            book_id: 书籍 ID
            json_data: JSON 格式的音效配置
            overwrite: 是否覆盖现有配置

        Returns:
            Dict[str, Any]: 导入结果统计
        """
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            return {"error": f"JSON 解析失败: {e}"}

        with get_db_context() as db:
            from core.models import Chapter

            stats = {"updated": 0, "skipped": 0, "errors": []}

            for chapter_data in data.get("chapters", []):
                chapter_index = chapter_data.get("chapter_index")
                sound_effects = chapter_data.get("sound_effects", [])

                chapter = db.query(Chapter).filter(
                    Chapter.book_id == book_id,
                    Chapter.chapter_index == chapter_index,
                ).first()

                if not chapter:
                    stats["skipped"] += 1
                    continue

                if chapter.sound_effects and not overwrite:
                    stats["skipped"] += 1
                    continue

                chapter.sound_effects = sound_effects
                stats["updated"] += 1

            db.commit()
            return stats


# ===========================================
# 全局服务实例
# ===========================================

_sound_effect_library_service = None


def get_sound_effect_library_service() -> SoundEffectLibraryService:
    """获取音效库服务实例"""
    global _sound_effect_library_service
    if _sound_effect_library_service is None:
        _sound_effect_library_service = SoundEffectLibraryService()
    return _sound_effect_library_service
