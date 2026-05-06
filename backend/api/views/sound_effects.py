"""
Sound Effect 音效库视图
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import (
    SoundEffect, SoundEffectUsage, SoundEffectCollection, SoundEffectCollectionItem,
    SoundEffectType, SoundLayer, SoundPriority, SoundSource, SoundEffectStatus,
    Book, Chapter
)

logger = logging.getLogger("audiobook")


class SoundEffectListView(APIView):
    """音效列表视图"""

    def get(self, request):
        """获取音效列表"""
        effect_type = request.GET.get("effect_type")
        layer = request.GET.get("layer")
        source = request.GET.get("source")
        status_filter = request.GET.get("status", "active")

        qs = SoundEffect.objects.all()
        if effect_type:
            qs = qs.filter(effect_type=effect_type)
        if layer:
            qs = qs.filter(layer=layer)
        if source:
            qs = qs.filter(source=source)
        if status_filter:
            qs = qs.filter(status=status_filter)

        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))
        total = qs.count()
        items = qs[page_size*(page-1):page_size*page]

        data = [{
            "id": s.id,
            "name": s.name,
            "chinese_description": s.chinese_description,
            "effect_type": s.effect_type,
            "layer": s.layer,
            "source": s.source,
            "duration_ms": s.duration_ms,
            "minio_url": s.minio_url,
            "status": s.status,
            "is_favorite": s.is_favorite,
            "usage_count": s.usage_count,
        } for s in items]

        return Response({"total": total, "items": data})


class SoundEffectDetailView(APIView):
    """音效详情视图"""

    def get(self, request, effect_id):
        """获取音效详情"""
        try:
            se = SoundEffect.objects.get(id=effect_id)
        except SoundEffect.DoesNotExist:
            return Response({"detail": "音效不存在"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": se.id,
            "name": se.name,
            "description": se.description,
            "chinese_description": se.chinese_description,
            "effect_type": se.effect_type,
            "layer": se.layer,
            "tags": se.tags,
            "chinese_tags": se.chinese_tags,
            "source": se.source,
            "source_id": se.source_id,
            "duration_ms": se.duration_ms,
            "minio_path": se.minio_path,
            "minio_url": se.minio_url,
            "status": se.status,
            "is_favorite": se.is_favorite,
            "usage_count": se.usage_count,
            "priority": se.priority,
        })


class SoundEffectSearchView(APIView):
    """音效搜索视图"""

    def post(self, request):
        """搜索音效"""
        query = request.data.get("query", "")
        effect_type = request.data.get("effect_type")
        limit = int(request.data.get("limit", 10))

        qs = SoundEffect.objects.filter(status=SoundEffectStatus.ACTIVE)
        
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(chinese_description__icontains=query)
        if effect_type:
            qs = qs.filter(effect_type=effect_type)

        items = qs[:limit]
        data = [{
            "id": s.id,
            "name": s.name,
            "chinese_description": s.chinese_description,
            "effect_type": s.effect_type,
            "duration_ms": s.duration_ms,
            "match_score": 0.8,
        } for s in items]

        return Response({"items": data})


class SoundEffectRecommendView(APIView):
    """音效推荐视图"""

    def post(self, request):
        """根据场景推荐音效"""
        book_id = request.data.get("book_id")
        limit = int(request.data.get("limit", 20))

        qs = SoundEffect.objects.filter(status=SoundEffectStatus.ACTIVE, is_verified=True)

        if book_id:
            # 根据书籍类型推荐
            qs = qs.order_by("-usage_count")

        items = qs[:limit]
        data = [{
            "id": s.id,
            "name": s.name,
            "chinese_description": s.chinese_description,
            "effect_type": s.effect_type,
            "usage_count": s.usage_count,
        } for s in items]

        return Response({"items": data})


class SoundEffectStatisticsView(APIView):
    """音效统计视图"""

    def get(self, request):
        """获取音效库统计"""
        total = SoundEffect.objects.count()
        by_type = {}
        by_source = {}
        total_usage = 0

        for t in SoundEffectType.values:
            by_type[t] = SoundEffect.objects.filter(effect_type=t).count()
        for s in SoundSource.values:
            by_source[s] = SoundEffect.objects.filter(source=s).count()

        total_usage = SoundEffect.objects.aggregate(total=models.Sum("usage_count"))["total"] or 0

        return Response({
            "total_sound_effects": total,
            "by_type": by_type,
            "by_source": by_source,
            "total_usage_count": total_usage,
        })


class BBBSyncView(APIView):
    """BBC 音效同步视图"""

    def post(self, request):
        """同步 BBC 音效"""
        return Response({"message": "BBC 同步功能待实现"})


class BBCEffectDownloadView(APIView):
    """BBC 音效下载视图"""

    def post(self, request):
        """下载 BBC 音效"""
        effect_id = request.data.get("effect_id")
        return Response({"message": f"下载音效 {effect_id}"})


class SoundEffectUsageView(APIView):
    """音效使用记录视图"""

    def get(self, request, effect_id):
        """获取音效使用记录"""
        try:
            se = SoundEffect.objects.get(id=effect_id)
        except SoundEffect.DoesNotExist:
            return Response({"detail": "音效不存在"}, status=status.HTTP_404_NOT_FOUND)

        records = SoundEffectUsage.objects.filter(sound_effect=se).order_by("-created_at")[:50]
        data = [{
            "id": r.id,
            "book_id": r.book_id,
            "chapter_id": r.chapter_id,
            "trigger_at_ms": r.trigger_at_ms,
            "created_at": r.created_at,
        } for r in records]

        return Response({"items": data})


class SoundEffectFavoriteView(APIView):
    """音效收藏视图"""

    def post(self, request, effect_id):
        """切换收藏状态"""
        try:
            se = SoundEffect.objects.get(id=effect_id)
        except SoundEffect.DoesNotExist:
            return Response({"detail": "音效不存在"}, status=status.HTTP_404_NOT_FOUND)

        se.is_favorite = not se.is_favorite
        se.save()
        return Response({"is_favorite": se.is_favorite})


class SoundEffectVerifyView(APIView):
    """音效审核视图"""

    def post(self, request, effect_id):
        """审核通过音效"""
        try:
            se = SoundEffect.objects.get(id=effect_id)
        except SoundEffect.DoesNotExist:
            return Response({"detail": "音效不存在"}, status=status.HTTP_404_NOT_FOUND)

        se.is_verified = True
        se.save()
        return Response({"message": "审核通过"})


class SoundEffectCollectionListView(APIView):
    """音效收藏集列表"""

    def get(self, request):
        """获取收藏集列表"""
        collections = SoundEffectCollection.objects.all()
        data = [{
            "id": c.id,
            "name": c.name,
            "scene_type": c.scene_type,
            "sound_count": c.sound_count,
            "is_public": c.is_public,
        } for c in collections]
        return Response({"items": data})


class SoundEffectCollectionDetailView(APIView):
    """音效收藏集详情"""

    def get(self, request, collection_id):
        """获取收藏集详情"""
        try:
            collection = SoundEffectCollection.objects.get(id=collection_id)
        except SoundEffectCollection.DoesNotExist:
            return Response({"detail": "收藏集不存在"}, status=status.HTTP_404_NOT_FOUND)

        items = SoundEffectCollectionItem.objects.filter(collection=collection)
        effects = [{
            "id": i.sound_effect.id,
            "name": i.sound_effect.name,
            "effect_type": i.sound_effect.effect_type,
        } for i in items]

        return Response({
            "id": collection.id,
            "name": collection.name,
            "scene_type": collection.scene_type,
            "items": effects,
        })


class SoundEffectCollectionItemView(APIView):
    """音效收藏集项目"""

    def get(self, request, collection_id):
        """获取收藏集项目"""
        items = SoundEffectCollectionItem.objects.filter(collection_id=collection_id)
        data = [{
            "id": i.id,
            "sound_effect_id": i.sound_effect_id,
            "custom_volume": i.custom_volume,
            "sort_order": i.sort_order,
        } for i in items]
        return Response({"items": data})

    def post(self, request, collection_id):
        """添加音效到收藏集"""
        try:
            collection = SoundEffectCollection.objects.get(id=collection_id)
        except SoundEffectCollection.DoesNotExist:
            return Response({"detail": "收藏集不存在"}, status=status.HTTP_404_NOT_FOUND)

        effect_id = request.data.get("sound_effect_id")
        try:
            effect = SoundEffect.objects.get(id=effect_id)
        except SoundEffect.DoesNotExist:
            return Response({"detail": "音效不存在"}, status=status.HTTP_404_NOT_FOUND)

        item = SoundEffectCollectionItem.objects.create(
            collection=collection,
            sound_effect=effect,
        )
        return Response({"id": item.id}, status=status.HTTP_201_CREATED)


class SoundEffectExportView(APIView):
    """音效配置导出"""

    def get(self, request, book_id):
        """导出书籍的音效配置"""
        try:
            Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        chapters = Chapter.objects.filter(book_id=book_id)
        effects = []
        for ch in chapters:
            if ch.sound_effects:
                effects.append({
                    "chapter_id": ch.id,
                    "chapter_index": ch.chapter_index,
                    "sound_effects": ch.sound_effects,
                })

        return Response({"items": effects})


class SoundEffectImportView(APIView):
    """音效配置导入"""

    def post(self, request, book_id):
        """导入音效配置"""
        try:
            Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"detail": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "导入功能待实现"})


class SoundEffectTypeListView(APIView):
    """音效类型列表"""

    def get(self, request):
        """获取所有音效类型"""
        data = [{"value": t[0], "label": t[1]} for t in SoundEffectType.choices]
        return Response({"items": data})


class SoundEffectSourceListView(APIView):
    """音效来源列表"""

    def get(self, request):
        """获取所有音效来源"""
        data = [{"value": s[0], "label": s[1]} for s in SoundSource.choices]
        return Response({"items": data})
