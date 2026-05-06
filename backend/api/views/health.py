# ===========================================
# API Views - 健康检查视图
# ===========================================

"""
健康检查视图
"""

import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response

logger = logging.getLogger("audiobook")


class HealthCheckView(APIView):
    """健康检查视图"""

    def get(self, request):
        """
        健康检查

        返回服务健康状态和各组件连接状态。
        """
        health = {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": "1.0.0",
        }

        # 检查数据库
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health["database"] = "connected"
        except Exception as e:
            health["database"] = f"error: {str(e)}"
            health["status"] = "unhealthy"

        # 检查 Redis
        try:
            import redis
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
            )
            r.ping()
            health["redis"] = "connected"
        except Exception as e:
            health["redis"] = f"error: {str(e)}"

        # 检查 MinIO
        try:
            from minio import Minio
            client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            client.list_buckets()
            health["minio"] = "connected"
        except Exception as e:
            health["minio"] = f"error: {str(e)}"

        return Response(health)
