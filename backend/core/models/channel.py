"""
发布渠道数据模型
"""
from django.db import models
from django.utils import timezone


class PlatformType(models.TextChoices):
    """平台类型枚举"""
    SELF_HOSTED = "self_hosted", "自建平台"
    XIMALAYA = "ximalaya", "喜马拉雅"
    QINGTING = "qingting", "蜻蜓FM"
    LIZHI = "lizhi", "荔枝FM"
    CUSTOM = "custom", "自定义平台"


class PublishChannel(models.Model):
    """发布渠道数据模型"""

    name = models.CharField(max_length=100, verbose_name="渠道名称")
    description = models.TextField(blank=True, null=True, verbose_name="渠道描述")

    platform_type = models.CharField(
        max_length=20,
        choices=PlatformType.choices,
        default=PlatformType.SELF_HOSTED,
        verbose_name="平台类型"
    )

    api_config = models.JSONField(blank=True, null=True, verbose_name="API配置")

    oauth_client_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="OAuth客户端ID")
    oauth_access_token = models.CharField(max_length=1000, blank=True, null=True, verbose_name="OAuth访问令牌")
    oauth_refresh_token = models.CharField(max_length=1000, blank=True, null=True, verbose_name="OAuth刷新令牌")
    oauth_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="令牌过期时间")

    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    auto_publish = models.BooleanField(default=False, verbose_name="是否自动发布")
    priority = models.IntegerField(default=0, verbose_name="发布优先级")

    publish_as_draft = models.BooleanField(default=True, verbose_name="发布为草稿")
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name="分类")
    tags = models.JSONField(blank=True, null=True, verbose_name="标签列表")

    total_published = models.IntegerField(default=0, verbose_name="已发布书籍数")
    success_count = models.IntegerField(default=0, verbose_name="成功次数")
    failure_count = models.IntegerField(default=0, verbose_name="失败次数")
    last_published_at = models.DateTimeField(blank=True, null=True, verbose_name="最后发布时间")

    user_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="用户ID")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "publish_channels"
        ordering = ["-priority", "-created_at"]
        indexes = [
            models.Index(fields=["platform_type", "is_enabled"]),
            models.Index(fields=["user_id", "is_enabled"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_platform_type_display()})"

    @property
    def is_oauth_expired(self):
        """检查 OAuth 令牌是否过期"""
        if self.oauth_expires_at:
            return timezone.now() >= self.oauth_expires_at
        return False
