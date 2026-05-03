# ===========================================
# MinIO 存储服务
# ===========================================

"""
MinIO 存储服务模块

提供对象存储功能，用于存储 EPUB 文件和生成的音频文件。
支持文件上传、下载、预签名 URL 生成等功能。
"""

import io
import logging
from datetime import timedelta
from typing import Optional, List, Tuple

from minio import Minio
from minio.error import S3Error

from core.config import settings
from core.exceptions import StorageError


logger = logging.getLogger("audiobook")


class MinioStorageService:
    """
    MinIO 存储服务

    提供统一的文件存储接口，支持：
    - 存储桶管理
    - 文件上传/下载
    - 预签名 URL 生成
    - 大文件分片上传
    - 章节文本存取（供 DeepSeek 分析使用）
    """

    # 章节文本存储路径前缀
    CHAPTER_TEXT_PREFIX = "chapters"

    def __init__(self):
        """
        初始化 MinIO 客户端

        从配置中读取 MinIO 连接信息。
        """
        self._client: Optional[Minio] = None
        self._initialized = False

    @property
    def client(self) -> Minio:
        """
        获取 MinIO 客户端（懒加载）

        Returns:
            Minio: MinIO 客户端实例
        """
        if self._client is None:
            self._client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        return self._client

    def initialize(self) -> None:
        """
        初始化存储服务

        创建必要的存储桶，设置生命周期策略。
        """
        if self._initialized:
            return

        try:
            # 创建 EPUB 存储桶
            if not self.client.bucket_exists(settings.MINIO_BUCKET_EPUB):
                self.client.make_bucket(settings.MINIO_BUCKET_EPUB)
                logger.info(f"创建存储桶: {settings.MINIO_BUCKET_EPUB}")

            # 创建音频存储桶
            if not self.client.bucket_exists(settings.MINIO_BUCKET_AUDIO):
                self.client.make_bucket(settings.MINIO_BUCKET_AUDIO)
                logger.info(f"创建存储桶: {settings.MINIO_BUCKET_AUDIO}")

            self._initialized = True
            logger.info("MinIO 存储服务初始化完成")

        except S3Error as e:
            logger.error(f"MinIO 初始化失败: {e}")
            raise StorageError(f"MinIO 初始化失败: {e}")

    def upload_file(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict = None,
    ) -> str:
        """
        上传文件到 MinIO

        Args:
            bucket: 存储桶名称
            object_name: 对象名称（路径）
            data: 文件数据
            content_type: 内容类型
            metadata: 元数据

        Returns:
            str: 对象存储路径

        Raises:
            StorageError: 上传失败时抛出
        """
        try:
            data_stream = io.BytesIO(data)
            data_stream_len = len(data)

            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=data_stream,
                length=data_stream_len,
                content_type=content_type,
                metadata=metadata or {},
            )

            logger.info(f"文件上传成功: {bucket}/{object_name} ({data_stream_len} bytes)")
            return object_name

        except S3Error as e:
            logger.error(f"文件上传失败: {bucket}/{object_name} - {e}")
            raise StorageError(f"文件上传失败: {e}")

    def upload_file_from_path(
        self,
        bucket: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        从本地路径上传文件

        Args:
            bucket: 存储桶名称
            object_name: 对象名称
            file_path: 本地文件路径
            content_type: 内容类型

        Returns:
            str: 对象存储路径
        """
        try:
            self.client.fput_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
            )

            logger.info(f"文件上传成功: {bucket}/{object_name} <- {file_path}")
            return object_name

        except S3Error as e:
            logger.error(f"文件上传失败: {bucket}/{object_name} - {e}")
            raise StorageError(f"文件上传失败: {e}")

    def download_file(self, bucket: str, object_name: str) -> bytes:
        """
        下载文件

        Args:
            bucket: 存储桶名称
            object_name: 对象名称

        Returns:
            bytes: 文件数据

        Raises:
            StorageError: 下载失败时抛出
        """
        try:
            response = self.client.get_object(bucket_name=bucket, object_name=object_name)
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(f"文件下载成功: {bucket}/{object_name} ({len(data)} bytes)")
            return data

        except S3Error as e:
            logger.error(f"文件下载失败: {bucket}/{object_name} - {e}")
            raise StorageError(f"文件下载失败: {e}")

    def get_presigned_url(
        self,
        bucket: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """
        生成预签名 URL

        用于临时授权访问私有文件。

        Args:
            bucket: 存储桶名称
            object_name: 对象名称
            expires: 过期时间

        Returns:
            str: 预签名 URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=expires,
            )

            logger.info(f"生成预签名 URL: {bucket}/{object_name}, 过期: {expires}")
            return url

        except S3Error as e:
            logger.error(f"生成预签名 URL 失败: {bucket}/{object_name} - {e}")
            raise StorageError(f"生成预签名 URL 失败: {e}")

    def delete_file(self, bucket: str, object_name: str) -> bool:
        """
        删除文件

        Args:
            bucket: 存储桶名称
            object_name: 对象名称

        Returns:
            bool: 是否删除成功
        """
        try:
            self.client.remove_object(bucket_name=bucket, object_name=object_name)
            logger.info(f"文件删除成功: {bucket}/{object_name}")
            return True

        except S3Error as e:
            logger.error(f"文件删除失败: {bucket}/{object_name} - {e}")
            return False

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        recursive: bool = True,
    ) -> List[dict]:
        """
        列出对象

        Args:
            bucket: 存储桶名称
            prefix: 对象名称前缀
            recursive: 是否递归列出

        Returns:
            List[dict]: 对象列表
        """
        try:
            objects = self.client.list_objects(
                bucket_name=bucket,
                prefix=prefix,
                recursive=recursive,
            )

            result = []
            for obj in objects:
                result.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })

            return result

        except S3Error as e:
            logger.error(f"列出对象失败: {bucket}/{prefix} - {e}")
            raise StorageError(f"列出对象失败: {e}")

    def get_object_stat(self, bucket: str, object_name: str) -> dict:
        """
        获取对象元信息

        Args:
            bucket: 存储桶名称
            object_name: 对象名称

        Returns:
            dict: 对象元信息
        """
        try:
            stat = self.client.stat_object(bucket_name=bucket, object_name=object_name)

            return {
                "name": stat.object_name,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
            }

        except S3Error as e:
            logger.error(f"获取对象元信息失败: {bucket}/{object_name} - {e}")
            raise StorageError(f"获取对象元信息失败: {e}")

    def copy_object(
        self,
        bucket: str,
        source_name: str,
        dest_name: str,
    ) -> bool:
        """
        复制对象

        Args:
            bucket: 存储桶名称
            source_name: 源对象名称
            dest_name: 目标对象名称

        Returns:
            bool: 是否复制成功
        """
        try:
            self.client.copy_object(
                bucket_name=bucket,
                object_name=dest_name,
                source=self.client.fake_object(source_name),
            )

            logger.info(f"对象复制成功: {bucket}/{source_name} -> {dest_name}")
            return True

        except S3Error as e:
            logger.error(f"对象复制失败: {bucket}/{source_name} -> {dest_name} - {e}")
            return False


    # ── 章节文本存取（供 DeepSeek 分析从 MinIO 读取） ──

    def upload_chapter_text(
        self,
        book_id: int,
        chapter_index: int,
        text: str,
        encoding: str = "utf-8",
    ) -> str:
        """
        上传清洗后的章节文本到 MinIO

        路径格式: chapters/{book_id}/{chapter_index:03d}_cleaned.txt

        Args:
            book_id: 书籍 ID
            chapter_index: 章节序号
            text: 清洗后的纯正文
            encoding: 文本编码

        Returns:
            str: MinIO 对象路径
        """
        object_name = f"{self.CHAPTER_TEXT_PREFIX}/{book_id}/{chapter_index:03d}_cleaned.txt"
        data = text.encode(encoding)

        self.upload_file(
            bucket=settings.MINIO_BUCKET_EPUB,
            object_name=object_name,
            data=data,
            content_type="text/plain; charset=utf-8",
        )

        logger.debug(f"章节文本已上传: {object_name} ({len(data)} bytes)")
        return object_name

    def download_chapter_text(
        self,
        book_id: int,
        chapter_index: int,
    ) -> str:
        """
        从 MinIO 下载清洗后的章节文本

        Args:
            book_id: 书籍 ID
            chapter_index: 章节序号

        Returns:
            str: 章节纯正文（UTF-8 解码）

        Raises:
            StorageError: 文件不存在或下载失败
        """
        object_name = f"{self.CHAPTER_TEXT_PREFIX}/{book_id}/{chapter_index:03d}_cleaned.txt"

        try:
            data = self.download_file(
                bucket=settings.MINIO_BUCKET_EPUB,
                object_name=object_name,
            )
            return data.decode("utf-8")
        except StorageError:
            # 尝试兼容旧路径（无 _cleaned 后缀）
            alt_name = f"{self.CHAPTER_TEXT_PREFIX}/{book_id}/{chapter_index:03d}.txt"
            try:
                data = self.download_file(
                    bucket=settings.MINIO_BUCKET_EPUB,
                    object_name=alt_name,
                )
                return data.decode("utf-8")
            except StorageError:
                raise StorageError(f"章节文本不存在: book={book_id}, chapter={chapter_index}")

    def get_chapter_text_path(self, book_id: int, chapter_index: int) -> str:
        """获取章节文本在 MinIO 中的标准路径"""
        return f"{self.CHAPTER_TEXT_PREFIX}/{book_id}/{chapter_index:03d}_cleaned.txt"

    def delete_chapter_texts(self, book_id: int) -> int:
        """
        删除某本书的所有章节文本

        Args:
            book_id: 书籍 ID

        Returns:
            int: 删除的文件数
        """
        prefix = f"{self.CHAPTER_TEXT_PREFIX}/{book_id}/"
        try:
            objects = self.list_objects(
                bucket=settings.MINIO_BUCKET_EPUB,
                prefix=prefix,
            )
            count = 0
            for obj in objects:
                self.delete_file(settings.MINIO_BUCKET_EPUB, obj["name"])
                count += 1
            logger.info(f"已删除 {count} 个章节文本: book={book_id}")
            return count
        except Exception as e:
            logger.warning(f"删除章节文本失败: book={book_id} - {e}")
            return 0


# 全局单例
storage_service = MinioStorageService()


def get_storage_service() -> MinioStorageService:
    """
    获取存储服务实例

    Returns:
        MinioStorageService: 存储服务实例
    """
    if not storage_service._initialized:
        storage_service.initialize()
    return storage_service
