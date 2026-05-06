# ===========================================
# API Views - 音效库相关
# ===========================================

"""
音效库 API 视图

提供音效库的完整 CRUD 操作：
- GET /api/sound-effects/ - 列出音效
- POST /api/sound-effects/ - 创建音效
- GET /api/sound-effects/{id}/ - 获取音效详情
- PUT /api/sound-effects/{id}/ - 更新音效
- DELETE /api/sound-effects/{id}/ - 删除音效
- POST /api/sound-effects/search/ - 搜索音效
- POST /api/sound-effects/recommend/ - 推荐音效
- GET /api/sound-effects/statistics/ - 统计信息
- POST /api/sound-effects/bbc-sync/ - BBC 同步
- POST /api/sound-effects/download/ - 下载 BBC 音效
"""

import logging
from typing import Any

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import (
    SoundEffect,
    SoundEffectUsage,
    SoundEffectCollection,
    SoundEffectType,
    SoundEffectStatus,
)
from core.database import get_db_context
from services.svc_sound_effect_library import get_sound_effect_library_service
from api.serializers.sound_effect import (
    SoundEffectSerializer,
    SoundEffectListSerializer,
    SoundEffectCreateSerializer,
    SoundEffectUpdateSerializer,
    SoundEffectSearchSerializer,
    SoundEffectMatchSerializer,
    SoundEffectRecommendSerializer,
    SoundEffectUsageSerializer,
    SoundEffectUsageCreateSerializer,
    SoundEffectCollectionSerializer,
    SoundEffectCollectionDetailSerializer,
    SoundEffectCollectionCreateSerializer,
    SoundEffectCollectionUpdateSerializer,
    SoundEffectStatisticsSerializer,
    BBSSyncSerializer,
    ChapterSoundDesignSerializer,
    SoundEffectImportExportSerializer,
)


logger = logging.getLogger("audiobook")


# ===========================================
# 音效管理
# ===========================================

class SoundEffectListView(APIView):
    """
    音效列表视图

    GET: 列出所有音效
    POST: 创建新音效
    """

    def get(self, request) -> Response:
        """列出所有音效"""
        with get_db_context() as db:
            # 构建查询
            query = db.query(SoundEffect)

            # 过滤条件
            effect_type = request.query_params.get("effect_type")
            source = request.query_params.get("source")
            status_filter = request.query_params.get("status")
            is_favorite = request.query_params.get("is_favorite")
            is_verified = request.query_params.get("is_verified")

            if effect_type:
                query = query.filter(SoundEffect.effect_type == effect_type)
            if source:
                query = query.filter(SoundEffect.source == source)
            if status_filter:
                query = query.filter(SoundEffect.status == status_filter)
            if is_favorite and is_favorite.lower() == "true":
                query = query.filter(SoundEffect.is_favorite == True)
            if is_verified and is_verified.lower() == "true":
                query = query.filter(SoundEffect.is_verified == True)

            # 排序
            ordering = request.query_params.get("ordering", "-usage_count")
            if ordering.startswith("-"):
                field_name = ordering[1:]
                query = query.order_by(getattr(SoundEffect, field_name).desc())
            else:
                query = query.order_by(getattr(SoundEffect, ordering))

            # 分页
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            offset = (page - 1) * page_size

            total = query.count()
            effects = query.offset(offset).limit(page_size).all()

            serializer = SoundEffectListSerializer(effects, many=True)

            return Response({
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            })

    def post(self, request) -> Response:
        """创建新音效"""
        serializer = SoundEffectCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with get_db_context() as db:
            effect = SoundEffect(
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description", ""),
                chinese_description=serializer.validated_data.get("chinese_description", ""),
                effect_type=serializer.validated_data.get("effect_type", SoundEffectType.ENVIRONMENT),
                layer=serializer.validated_data.get("layer"),
                tags=serializer.validated_data.get("tags", []),
                chinese_tags=serializer.validated_data.get("chinese_tags", []),
                semantic_keywords=serializer.validated_data.get("semantic_keywords", []),
                source=serializer.validated_data.get("source"),
                source_id=serializer.validated_data.get("source_id"),
                source_url=serializer.validated_data.get("source_url"),
                duration_ms=serializer.validated_data.get("duration_ms"),
                file_format=serializer.validated_data.get("file_format"),
                local_path=serializer.validated_data.get("local_path"),
                minio_path=serializer.validated_data.get("minio_path"),
                suitable_scenes=serializer.validated_data.get("suitable_scenes", []),
                recommended_volume_min=serializer.validated_data.get("recommended_volume_min"),
                recommended_volume_max=serializer.validated_data.get("recommended_volume_max"),
                recommended_fade_in_ms=serializer.validated_data.get("recommended_fade_in_ms"),
                recommended_fade_out_ms=serializer.validated_data.get("recommended_fade_out_ms"),
            )

            db.add(effect)
            db.commit()
            db.refresh(effect)

            result_serializer = SoundEffectSerializer(effect)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class SoundEffectDetailView(APIView):
    """
    音效详情视图

    GET: 获取音效详情
    PUT: 更新音效
    DELETE: 删除音效
    """

    def get(self, request, effect_id: int) -> Response:
        """获取音效详情"""
        with get_db_context() as db:
            effect = db.query(SoundEffect).filter(id=effect_id).first()

            if not effect:
                return Response(
                    {"error": "音效不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = SoundEffectSerializer(effect)
            return Response(serializer.data)

    def put(self, request, effect_id: int) -> Response:
        """更新音效"""
        serializer = SoundEffectUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with get_db_context() as db:
            effect = db.query(SoundEffect).filter(id=effect_id).first()

            if not effect:
                return Response(
                    {"error": "音效不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            data = serializer.validated_data

            # 更新字段
            for field in [
                "name", "description", "chinese_description", "effect_type",
                "layer", "tags", "chinese_tags", "semantic_keywords",
                "priority", "suitable_scenes", "recommended_volume_min",
                "recommended_volume_max", "recommended_fade_in_ms",
                "recommended_fade_out_ms", "status"
            ]:
                if field in data:
                    setattr(effect, field, data[field])

            # 处理布尔字段
            if "is_favorite" in data:
                effect.is_favorite = data["is_favorite"]
            if "is_verified" in data:
                effect.is_verified = data["is_verified"]
                if data["is_verified"]:
                    from django.utils import timezone
                    effect.verified_at = timezone.now()

            db.commit()
            db.refresh(effect)

            result_serializer = SoundEffectSerializer(effect)
            return Response(result_serializer.data)

    def delete(self, request, effect_id: int) -> Response:
        """删除音效"""
        with get_db_context() as db:
            effect = db.query(SoundEffect).filter(id=effect_id).first()

            if not effect:
                return Response(
                    {"error": "音效不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 软删除：标记为归档状态
            effect.status = SoundEffectStatus.ARCHIVED
            db.commit()

            return Response(status=status.HTTP_204_NO_CONTENT)


class SoundEffectSearchView(APIView):
    """音效搜索视图"""

    def post(self, request) -> Response:
        """搜索音效"""
        serializer = SoundEffectSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_sound_effect_library_service()

        results = service.search_sound_effects(
            query=serializer.validated_data["query"],
            effect_type=serializer.validated_data.get("effect_type"),
            layer=serializer.validated_data.get("layer"),
            tags=serializer.validated_data.get("tags"),
            limit=serializer.validated_data["limit"],
            include_bbc=serializer.validated_data.get("include_bbc", True),
        )

        match_serializer = SoundEffectMatchSerializer(
            [r.__dict__ for r in results],
            many=True
        )

        return Response({
            "query": serializer.validated_data["query"],
            "total": len(results),
            "results": match_serializer.data,
        })


class SoundEffectRecommendView(APIView):
    """章节音效推荐视图"""

    def post(self, request) -> Response:
        """推荐音效"""
        serializer = SoundEffectRecommendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_sound_effect_library_service()

        # 获取章节分析数据
        book_id = serializer.validated_data.get("book_id")
        chapter_id = request.data.get("chapter_id")

        if chapter_id:
            # 从数据库获取章节分析结果
            with get_db_context() as db:
                from core.models import Chapter
                chapter = db.query(Chapter).filter(id=chapter_id).first()
                if not chapter:
                    return Response(
                        {"error": "章节不存在"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                chapter_analysis = {
                    "sound_effects": chapter.sound_effects or [],
                    "background_music": chapter.background_music or [],
                    "audio_bridge": chapter.audio_bridge or {},
                }
        else:
            # 直接使用请求中的分析数据
            chapter_analysis = {
                "sound_effects": request.data.get("sound_effects", []),
                "background_music": request.data.get("background_music", []),
                "audio_bridge": request.data.get("audio_bridge", {}),
            }

        results = service.recommend_for_chapter(
            chapter_analysis=chapter_analysis,
            book_id=book_id,
            limit=serializer.validated_data["limit"],
        )

        # 序列化结果
        serialized_results = []
        for match in results:
            serialized_results.append({
                "sound_effect": match.sound_effect.to_dict() if match.sound_effect.id else {
                    "id": 0,
                    "name": match.sound_effect.name,
                    "description": match.sound_effect.description,
                    "source": match.sound_effect.source,
                    "source_id": match.sound_effect.source_id,
                    "duration_ms": match.sound_effect.duration_ms,
                },
                "match_score": match.match_score,
                "match_reason": match.match_reason,
                "suggested_volume": match.suggested_volume,
                "suggested_fade_in_ms": match.suggested_fade_in_ms,
                "suggested_fade_out_ms": match.suggested_fade_out_ms,
            })

        return Response({
            "chapter_id": chapter_id,
            "book_id": book_id,
            "total": len(results),
            "recommendations": serialized_results,
        })


class SoundEffectStatisticsView(APIView):
    """音效库统计视图"""

    def get(self, request) -> Response:
        """获取统计信息"""
        service = get_sound_effect_library_service()
        stats = service.get_statistics()

        return Response(stats)


class BBSSyncView(APIView):
    """BBC Sound Effects 同步视图"""

    def post(self, request) -> Response:
        """从 BBC 同步音效"""
        serializer = BBSSyncSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = get_sound_effect_library_service()

        stats = service.sync_from_bbc(
            keywords=serializer.validated_data.get("keywords"),
            effect_type=serializer.validated_data.get("effect_type"),
            limit=serializer.validated_data["limit"],
        )

        return Response({
            "message": "同步完成",
            "statistics": stats,
        })


class BBCEffectDownloadView(APIView):
    """BBC 音效下载视图"""

    def post(self, request) -> Response:
        """下载 BBC 音效"""
        bbc_id = request.data.get("bbc_id")
        book_id = request.data.get("book_id")

        if not bbc_id:
            return Response(
                {"error": "bbc_id 是必填参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = get_sound_effect_library_service()
        effect, message = service.download_and_save_bbc_effect(bbc_id, book_id)

        if effect:
            return Response({
                "success": True,
                "message": message,
                "sound_effect": SoundEffectSerializer(effect).data,
            })
        else:
            return Response(
                {"success": False, "error": message},
                status=status.HTTP_400_BAD_REQUEST
            )


class SoundEffectUsageView(APIView):
    """音效使用记录视图"""

    def get(self, request, effect_id: int) -> Response:
        """获取音效的使用记录"""
        with get_db_context() as db:
            usages = db.query(SoundEffectUsage).filter(
                SoundEffectUsage.sound_effect_id == effect_id
            ).order_by(SoundEffectUsage.created_at.desc()).limit(100).all()

            serializer = SoundEffectUsageSerializer(usages, many=True)
            return Response({
                "effect_id": effect_id,
                "total": len(usages),
                "usages": serializer.data,
            })

    def post(self, request, effect_id: int) -> Response:
        """记录音效使用"""
        serializer = SoundEffectUsageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with get_db_context() as db:
            # 检查音效是否存在
            effect = db.query(SoundEffect).filter(id=effect_id).first()
            if not effect:
                return Response(
                    {"error": "音效不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            usage = SoundEffectUsage(
                sound_effect_id=effect_id,
                book_id=serializer.validated_data.get("book_id"),
                chapter_id=serializer.validated_data.get("chapter_id"),
                trigger_at_ms=serializer.validated_data.get("trigger_at_ms"),
                volume=serializer.validated_data.get("volume"),
                fade_in_ms=serializer.validated_data.get("fade_in_ms"),
                fade_out_ms=serializer.validated_data.get("fade_out_ms"),
                loop=serializer.validated_data.get("loop", False),
                matched_from_query=serializer.validated_data.get("matched_from_query"),
                match_score=serializer.validated_data.get("match_score"),
            )

            # 更新使用次数
            effect.increment_usage()

            db.add(usage)
            db.commit()
            db.refresh(usage)

            result_serializer = SoundEffectUsageSerializer(usage)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class SoundEffectFavoriteView(APIView):
    """音效收藏视图"""

    def post(self, request, effect_id: int) -> Response:
        """切换收藏状态"""
        with get_db_context() as db:
            effect = db.query(SoundEffect).filter(id=effect_id).first()

            if not effect:
                return Response(
                    {"error": "音效不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            effect.toggle_favorite()

            return Response({
                "effect_id": effect_id,
                "is_favorite": effect.is_favorite,
            })


class SoundEffectVerifyView(APIView):
    """音效审核视图"""

    def post(self, request, effect_id: int) -> Response:
        """审核音效"""
        with get_db_context() as db:
            effect = db.query(SoundEffect).filter(id=effect_id).first()

            if not effect:
                return Response(
                    {"error": "音效不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            effect.verify()

            return Response({
                "effect_id": effect_id,
                "is_verified": effect.is_verified,
                "verified_at": effect.verified_at.isoformat() if effect.verified_at else None,
            })


# ===========================================
# 音效收藏集管理
# ===========================================

class SoundEffectCollectionListView(APIView):
    """音效收藏集列表视图"""

    def get(self, request) -> Response:
        """列出所有收藏集"""
        with get_db_context() as db:
            collections = db.query(SoundEffectCollection).order_by(
                SoundEffectCollection.is_default.desc(),
                SoundEffectCollection.name,
            ).all()

            serializer = SoundEffectCollectionSerializer(collections, many=True)
            return Response({
                "total": len(collections),
                "collections": serializer.data,
            })

    def post(self, request) -> Response:
        """创建收藏集"""
        serializer = SoundEffectCollectionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with get_db_context() as db:
            collection = SoundEffectCollection(
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description", ""),
                scene_type=serializer.validated_data.get("scene_type"),
                is_public=serializer.validated_data.get("is_public", False),
            )

            db.add(collection)
            db.flush()  # 获取 ID

            # 添加音效到收藏集
            sound_effect_ids = serializer.validated_data.get("sound_effect_ids", [])
            for idx, effect_id in enumerate(sound_effect_ids):
                effect = db.query(SoundEffect).filter(id=effect_id).first()
                if effect:
                    item = SoundEffectCollectionItem(
                        collection_id=collection.id,
                        sound_effect_id=effect_id,
                        sort_order=idx,
                    )
                    db.add(item)

            # 更新音效数量
            collection.sound_count = len(sound_effect_ids)

            db.commit()
            db.refresh(collection)

            result_serializer = SoundEffectCollectionSerializer(collection)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class SoundEffectCollectionDetailView(APIView):
    """音效收藏集详情视图"""

    def get(self, request, collection_id: int) -> Response:
        """获取收藏集详情"""
        with get_db_context() as db:
            collection = db.query(SoundEffectCollection).filter(id=collection_id).first()

            if not collection:
                return Response(
                    {"error": "收藏集不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = SoundEffectCollectionDetailSerializer(collection)
            return Response(serializer.data)

    def put(self, request, collection_id: int) -> Response:
        """更新收藏集"""
        serializer = SoundEffectCollectionUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with get_db_context() as db:
            collection = db.query(SoundEffectCollection).filter(id=collection_id).first()

            if not collection:
                return Response(
                    {"error": "收藏集不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            data = serializer.validated_data
            for field in ["name", "description", "scene_type"]:
                if field in data:
                    setattr(collection, field, data[field])

            if "is_public" in data:
                collection.is_public = data["is_public"]
            if "is_default" in data:
                collection.is_default = data["is_default"]

            db.commit()
            db.refresh(collection)

            result_serializer = SoundEffectCollectionSerializer(collection)
            return Response(result_serializer.data)

    def delete(self, request, collection_id: int) -> Response:
        """删除收藏集"""
        with get_db_context() as db:
            collection = db.query(SoundEffectCollection).filter(id=collection_id).first()

            if not collection:
                return Response(
                    {"error": "收藏集不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            db.delete(collection)
            db.commit()

            return Response(status=status.HTTP_204_NO_CONTENT)


class SoundEffectCollectionItemView(APIView):
    """音效收藏集项目视图"""

    def post(self, request, collection_id: int) -> Response:
        """添加音效到收藏集"""
        effect_id = request.data.get("effect_id")
        if not effect_id:
            return Response(
                {"error": "effect_id 是必填参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with get_db_context() as db:
            collection = db.query(SoundEffectCollection).filter(id=collection_id).first()
            if not collection:
                return Response(
                    {"error": "收藏集不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            effect = db.query(SoundEffect).filter(id=effect_id).first()
            if not effect:
                return Response(
                    {"error": "音效不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 检查是否已存在
            existing = db.query(SoundEffectCollectionItem).filter(
                SoundEffectCollectionItem.collection_id == collection_id,
                SoundEffectCollectionItem.sound_effect_id == effect_id,
            ).first()

            if existing:
                return Response(
                    {"error": "音效已在收藏集中"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 添加到收藏集
            max_order = db.query(SoundEffectCollectionItem).filter(
                SoundEffectCollectionItem.collection_id == collection_id
            ).count()

            item = SoundEffectCollectionItem(
                collection_id=collection_id,
                sound_effect_id=effect_id,
                sort_order=max_order,
            )
            db.add(item)

            # 更新收藏集音效数量
            collection.sound_count = db.query(SoundEffectCollectionItem).filter(
                SoundEffectCollectionItem.collection_id == collection_id
            ).count() + 1

            db.commit()

            return Response({
                "success": True,
                "collection_id": collection_id,
                "effect_id": effect_id,
            })

    def delete(self, request, collection_id: int) -> Response:
        """从收藏集移除音效"""
        effect_id = request.data.get("effect_id")
        if not effect_id:
            return Response(
                {"error": "effect_id 是必填参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with get_db_context() as db:
            item = db.query(SoundEffectCollectionItem).filter(
                SoundEffectCollectionItem.collection_id == collection_id,
                SoundEffectCollectionItem.sound_effect_id == effect_id,
            ).first()

            if not item:
                return Response(
                    {"error": "收藏集中没有此音效"},
                    status=status.HTTP_404_NOT_FOUND
                )

            db.delete(item)

            # 更新收藏集音效数量
            collection = db.query(SoundEffectCollection).filter(id=collection_id).first()
            if collection:
                collection.sound_count = db.query(SoundEffectCollectionItem).filter(
                    SoundEffectCollectionItem.collection_id == collection_id
                ).count()

            db.commit()

            return Response(status=status.HTTP_204_NO_CONTENT)


# ===========================================
# 导入导出
# ===========================================

class SoundEffectExportView(APIView):
    """音效配置导出视图"""

    def get(self, request, book_id: int) -> Response:
        """导出书籍的音效配置"""
        service = get_sound_effect_library_service()
        json_data = service.export_to_json(book_id)

        return Response({
            "book_id": book_id,
            "data": json_data,
        })


class SoundEffectImportView(APIView):
    """音效配置导入视图"""

    def post(self, request, book_id: int) -> Response:
        """导入音效配置"""
        serializer = SoundEffectImportExportSerializer(data={
            "book_id": book_id,
            **request.data
        })
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        json_data = request.data.get("json_data")
        if not json_data:
            return Response(
                {"error": "json_data 是必填参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = get_sound_effect_library_service()
        result = service.import_from_json(
            book_id=book_id,
            json_data=json_data,
            overwrite=serializer.validated_data.get("overwrite", False),
        )

        return Response({
            "book_id": book_id,
            "result": result,
        })


# ===========================================
# 音效类型和来源
# ===========================================

class SoundEffectTypeListView(APIView):
    """音效类型列表视图"""

    def get(self, request) -> Response:
        """获取所有音效类型"""
        types_data = [
            {"value": choice[0], "label": choice[1]}
            for choice in SoundEffectType.choices
        ]
        return Response({"types": types_data})


class SoundEffectSourceListView(APIView):
    """音效来源列表视图"""

    def get(self, request) -> Response:
        """获取所有音效来源"""
        sources_data = [
            {"value": choice[0], "label": choice[1]}
            for choice in [
                ("bbc", "BBC Sound Effects"),
                ("fsd50k", "FSD50K"),
                ("user_upload", "用户上传"),
                ("generated", "AI生成"),
            ]
        ]
        return Response({"sources": sources_data})
