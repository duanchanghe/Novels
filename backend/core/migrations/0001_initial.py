# Generated migration for merging initial migrations
# This migration combines the initial setup into one consistent migration

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ("core", "0001_add_paragraph_model"),
        ("core", "0001_add_appears_to_character"),
        ("core", "0001_add_age_group_to_character"),
    ]

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SoundEffectCollection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="收藏集名称")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="收藏集描述"),
                ),
                (
                    "scene_type",
                    models.CharField(
                        blank=True,
                        help_text="如：武侠、仙侠、玄幻、都市",
                        max_length=50,
                        null=True,
                        verbose_name="场景类型",
                    ),
                ),
                (
                    "sound_count",
                    models.IntegerField(default=0, verbose_name="音效数量"),
                ),
                (
                    "is_public",
                    models.BooleanField(default=False, verbose_name="公开收藏集"),
                ),
                (
                    "is_default",
                    models.BooleanField(default=False, verbose_name="默认收藏集"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
            ],
            options={
                "verbose_name": "音效收藏集",
                "verbose_name_plural": "音效收藏集",
                "db_table": "sound_effect_collections",
                "ordering": ["-is_default", "-sound_count", "name"],
            },
        ),
        migrations.CreateModel(
            name="Book",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=500, verbose_name="书名")),
                (
                    "author",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="作者"
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="书籍简介"),
                ),
                (
                    "language",
                    models.CharField(
                        default="zh-CN", max_length=50, verbose_name="语言"
                    ),
                ),
                (
                    "cover_image_url",
                    models.URLField(
                        blank=True, max_length=1000, null=True, verbose_name="封面图URL"
                    ),
                ),
                (
                    "cover_image_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="封面图路径"
                    ),
                ),
                (
                    "file_name",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="原始文件名"
                    ),
                ),
                (
                    "file_size",
                    models.BigIntegerField(blank=True, null=True, verbose_name="文件大小"),
                ),
                (
                    "file_hash",
                    models.CharField(
                        blank=True, max_length=64, null=True, verbose_name="文件哈希"
                    ),
                ),
                (
                    "file_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="文件存储路径"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "待处理"),
                            ("ANALYZING", "正在分析"),
                            ("SYNTHESIZING", "正在合成"),
                            ("POST_PROCESSING", "正在后处理"),
                            ("PUBLISHING", "正在发布"),
                            ("DONE", "已完成"),
                            ("FAILED", "失败"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                        verbose_name="处理状态",
                    ),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[("MANUAL", "手动上传"), ("WATCH", "文件夹监听")],
                        default="MANUAL",
                        max_length=10,
                        verbose_name="来源类型",
                    ),
                ),
                (
                    "generation_mode",
                    models.CharField(
                        choices=[
                            ("AUTO", "自动"),
                            ("MANUAL", "手动"),
                        ],
                        default="AUTO",
                        max_length=10,
                        verbose_name="生成模式",
                    ),
                ),
                (
                    "auto_publish_enabled",
                    models.BooleanField(default=False, verbose_name="自动发布"),
                ),
                (
                    "total_chapters",
                    models.IntegerField(default=0, verbose_name="总章节数"),
                ),
                (
                    "processed_chapters",
                    models.IntegerField(default=0, verbose_name="已处理章节数"),
                ),
                (
                    "total_duration",
                    models.FloatField(
                        blank=True, null=True, verbose_name="总音频时长(秒)"
                    ),
                ),
                (
                    "full_audio_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="完整音频路径"
                    ),
                ),
                (
                    "full_audio_duration",
                    models.FloatField(
                        blank=True, null=True, verbose_name="完整音频时长"
                    ),
                ),
                (
                    "full_audio_size",
                    models.BigIntegerField(
                        blank=True, null=True, verbose_name="完整音频大小"
                    ),
                ),
                (
                    "full_audio_format",
                    models.CharField(
                        blank=True,
                        default="mp3",
                        max_length=10,
                        null=True,
                        verbose_name="音频格式",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, null=True, verbose_name="错误信息"),
                ),
                (
                    "error_count",
                    models.IntegerField(default=0, verbose_name="错误次数"),
                ),
                (
                    "watch_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="监听目录"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="删除时间"),
                ),
            ],
            options={
                "verbose_name": "书籍",
                "verbose_name_plural": "书籍列表",
                "db_table": "books",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Chapter",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "chapter_index",
                    models.IntegerField(db_index=True, verbose_name="章节序号"),
                ),
                ("title", models.CharField(blank=True, max_length=500, verbose_name="章节标题")),
                (
                    "raw_text",
                    models.TextField(blank=True, null=True, verbose_name="原始文本"),
                ),
                (
                    "cleaned_text",
                    models.TextField(blank=True, null=True, verbose_name="清洗后文本"),
                ),
                (
                    "analysis_result",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="分析结果"
                    ),
                ),
                (
                    "audio_file_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="音频文件路径"
                    ),
                ),
                (
                    "audio_url",
                    models.URLField(
                        blank=True, max_length=1000, null=True, verbose_name="音频URL"
                    ),
                ),
                (
                    "audio_duration",
                    models.FloatField(
                        blank=True, null=True, verbose_name="音频时长(秒)"
                    ),
                ),
                (
                    "audio_file_size",
                    models.BigIntegerField(
                        blank=True, null=True, verbose_name="音频文件大小"
                    ),
                ),
                (
                    "audio_format",
                    models.CharField(
                        blank=True,
                        default="mp3",
                        max_length=10,
                        null=True,
                        verbose_name="音频格式",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "待处理"),
                            ("ANALYZING", "正在分析"),
                            ("ANALYZED", "已分析"),
                            ("SYNTHESIZING", "正在合成"),
                            ("AWAITING_CONFIRM", "等待确认"),
                            ("DONE", "已完成"),
                            ("FAILED", "失败"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                        verbose_name="处理状态",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, null=True, verbose_name="错误信息"),
                ),
                (
                    "deepseek_tokens",
                    models.IntegerField(default=0, verbose_name="DeepSeek消耗Token"),
                ),
                (
                    "minimax_characters",
                    models.IntegerField(default=0, verbose_name="MiniMax消耗字符"),
                ),
                (
                    "completed_segments",
                    models.IntegerField(default=0, verbose_name="已完成片段"),
                ),
                (
                    "total_segments",
                    models.IntegerField(default=0, verbose_name="总片段数"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "next_chapter_id",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="下一章节ID"
                    ),
                ),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chapters",
                        to="core.book",
                        verbose_name="所属书籍",
                    ),
                ),
            ],
            options={
                "verbose_name": "章节",
                "verbose_name_plural": "章节列表",
                "db_table": "chapters",
                "ordering": ["book", "chapter_index"],
                "indexes": [
                    models.Index(
                        fields=["book", "chapter_index"],
                        name="chapters_book_chap_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["book", "chapter_index"],
                        name="uq_book_chapter",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="VoiceProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="音色名称")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="音色描述"),
                ),
                (
                    "role_type",
                    models.CharField(
                        choices=[
                            ("narrator", "旁白"),
                            ("male_protagonist", "男主角"),
                            ("female_protagonist", "女主角"),
                            ("male_supporting", "男性配角"),
                            ("female_supporting", "女性配角"),
                            ("elderly_male", "老年男性"),
                            ("elderly_female", "老年女性"),
                            ("child", "儿童"),
                            ("villain", "反派"),
                            ("other", "其他"),
                        ],
                        max_length=20,
                        verbose_name="角色类型",
                    ),
                ),
                (
                    "minimax_voice_id",
                    models.CharField(max_length=100, verbose_name="MiniMax音色ID"),
                ),
                (
                    "minimax_model",
                    models.CharField(
                        default="speech-02-hd", max_length=50, verbose_name="MiniMax模型"
                    ),
                ),
                (
                    "speed",
                    models.FloatField(
                        default=1.0,
                        help_text="语速倍率，1.0为正常速度",
                        verbose_name="语速",
                    ),
                ),
                (
                    "pitch",
                    models.FloatField(
                        default=0.0,
                        help_text="音调调整，范围-10到10",
                        verbose_name="音调",
                    ),
                ),
                (
                    "volume",
                    models.FloatField(
                        default=1.0,
                        help_text="音量调整，范围0到2",
                        verbose_name="音量",
                    ),
                ),
                (
                    "emotion_params",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="情感参数配置",
                        verbose_name="情感参数",
                    ),
                ),
                (
                    "character_names",
                    models.JSONField(
                        blank=True, default=list, verbose_name="关联角色名列表"
                    ),
                ),
                (
                    "is_system_preset",
                    models.BooleanField(default=False, verbose_name="系统预设"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="是否启用"),
                ),
                (
                    "sort_order",
                    models.IntegerField(
                        default=0,
                        help_text="用于排序，数字越小越靠前",
                        verbose_name="排序顺序",
                    ),
                ),
                (
                    "usage_count",
                    models.IntegerField(default=0, verbose_name="使用次数"),
                ),
                (
                    "created_by",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="创建者"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "book",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="voice_profiles",
                        to="core.book",
                        verbose_name="所属书籍",
                    ),
                ),
            ],
            options={
                "verbose_name": "音色配置",
                "verbose_name_plural": "音色配置列表",
                "db_table": "voice_profiles",
                "ordering": ["-is_system_preset", "sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="Character",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=100, verbose_name="角色名")),
                (
                    "aliases",
                    models.JSONField(
                        blank=True, default=list, verbose_name="角色别名列表"
                    ),
                ),
                (
                    "gender",
                    models.CharField(
                        choices=[
                            ("male", "男性"),
                            ("female", "女性"),
                            ("unknown", "未知"),
                        ],
                        default="unknown",
                        max_length=10,
                        verbose_name="性别",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="角色描述"),
                ),
                (
                    "voice_description",
                    models.TextField(
                        blank=True, null=True, verbose_name="声音特征描述"
                    ),
                ),
                (
                    "role_type",
                    models.CharField(
                        choices=[
                            ("protagonist", "主角"),
                            ("supporting", "配角"),
                            ("antagonist", "反派"),
                            ("minor", "次要角色"),
                            ("narrator", "旁白"),
                            ("other", "其他"),
                        ],
                        default="supporting",
                        max_length=20,
                        verbose_name="角色类型",
                    ),
                ),
                (
                    "emotions",
                    models.JSONField(
                        blank=True, default=list, verbose_name="角色常见情感"
                    ),
                ),
                (
                    "dialogue_count",
                    models.IntegerField(default=0, verbose_name="对话数量"),
                ),
                (
                    "usage_count",
                    models.IntegerField(default=0, verbose_name="使用次数"),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("deepseek", "DeepSeek分析"),
                            ("manual", "手动添加"),
                        ],
                        default="deepseek",
                        max_length=20,
                        verbose_name="来源",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "待审核"),
                            ("approved", "已审核"),
                            ("rejected", "已拒绝"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                        verbose_name="审核状态",
                    ),
                ),
                (
                    "sort_order",
                    models.IntegerField(
                        default=0,
                        help_text="用于排序，数字越小越靠前",
                        verbose_name="排序顺序",
                    ),
                ),
                (
                    "appears_in_chapters",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="角色出现的章节ID列表",
                        verbose_name="出现章节",
                    ),
                ),
                (
                    "age_group",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("child", "儿童"),
                            ("teenager", "青少年"),
                            ("young_adult", "青年"),
                            ("middle_aged", "中年"),
                            ("elderly", "老年"),
                        ],
                        max_length=20,
                        null=True,
                        verbose_name="年龄段",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "voice_profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="characters",
                        to="core.voiceprofile",
                        verbose_name="音色配置",
                    ),
                ),
                (
                    "custom_voice_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="自定义音色ID",
                    ),
                ),
                (
                    "custom_speed",
                    models.FloatField(
                        blank=True,
                        default=1.0,
                        null=True,
                        verbose_name="自定义语速",
                    ),
                ),
                (
                    "custom_pitch",
                    models.FloatField(
                        blank=True,
                        default=0.0,
                        null=True,
                        verbose_name="自定义音调",
                    ),
                ),
                (
                    "custom_volume",
                    models.FloatField(
                        blank=True,
                        default=1.0,
                        null=True,
                        verbose_name="自定义音量",
                    ),
                ),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="characters",
                        to="core.book",
                        verbose_name="所属书籍",
                    ),
                ),
            ],
            options={
                "verbose_name": "角色",
                "verbose_name_plural": "角色列表",
                "db_table": "characters",
                "ordering": ["book", "sort_order", "name"],
                "indexes": [
                    models.Index(
                        fields=["book", "name"], name="characters_book_name_idx"
                    ),
                    models.Index(
                        fields=["book", "status"],
                        name="characters_book_status_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["book", "name"], name="uq_book_character"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="AudioSegment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "segment_index",
                    models.IntegerField(db_index=True, verbose_name="片段序号"),
                ),
                (
                    "text_content",
                    models.TextField(verbose_name="文本内容"),
                ),
                (
                    "role",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="说话角色"
                    ),
                ),
                (
                    "emotion",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("calm", "平静"),
                            ("happy", "高兴"),
                            ("sad", "悲伤"),
                            ("angry", "愤怒"),
                            ("nervous", "紧张"),
                            ("surprised", "惊讶"),
                            ("gentle", "温柔"),
                            ("serious", "严肃"),
                            ("cold", "冷漠"),
                            ("sarcastic", "嘲讽"),
                        ],
                        max_length=20,
                        null=True,
                        verbose_name="情感",
                    ),
                ),
                (
                    "emotion_intensity",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("weak", "弱"),
                            ("medium", "中"),
                            ("strong", "强"),
                        ],
                        max_length=20,
                        null=True,
                        verbose_name="情感强度",
                    ),
                ),
                (
                    "voice_id",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="音色ID"
                    ),
                ),
                (
                    "speed",
                    models.CharField(
                        choices=[
                            ("slow", "慢速"),
                            ("normal", "正常"),
                            ("fast", "快速"),
                        ],
                        default="normal",
                        max_length=10,
                        verbose_name="语速",
                    ),
                ),
                (
                    "pause_after",
                    models.FloatField(
                        default=0.3,
                        help_text="片段后的停顿时长(秒)",
                        verbose_name="停顿时长",
                    ),
                ),
                (
                    "audio_file_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="音频文件路径"
                    ),
                ),
                (
                    "audio_url",
                    models.URLField(
                        blank=True, max_length=1000, null=True, verbose_name="音频URL"
                    ),
                ),
                (
                    "audio_duration_ms",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="音频时长(毫秒)"
                    ),
                ),
                (
                    "audio_file_size",
                    models.BigIntegerField(
                        blank=True, null=True, verbose_name="音频文件大小"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "待处理"),
                            ("SYNTHESIZING", "正在合成"),
                            ("SUCCESS", "成功"),
                            ("FAILED", "失败"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, null=True, verbose_name="错误信息"),
                ),
                (
                    "retry_count",
                    models.IntegerField(default=0, verbose_name="重试次数"),
                ),
                (
                    "minimax_cost",
                    models.IntegerField(default=0, verbose_name="MiniMax消耗字符"),
                ),
                (
                    "deepseek_cost",
                    models.IntegerField(default=0, verbose_name="DeepSeek消耗Token"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "chapter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="segments",
                        to="core.chapter",
                        verbose_name="所属章节",
                    ),
                ),
            ],
            options={
                "verbose_name": "音频片段",
                "verbose_name_plural": "音频片段列表",
                "db_table": "audio_segments",
                "ordering": ["chapter", "segment_index"],
                "indexes": [
                    models.Index(
                        fields=["chapter", "segment_index"],
                        name="segments_chapter_idx",
                    ),
                    models.Index(
                        fields=["status"], name="segments_status_idx"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="TTSTask",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "task_type",
                    models.CharField(
                        choices=[
                            ("full", "完整生成"),
                            ("incremental", "增量生成"),
                            ("regenerate", "重新生成"),
                        ],
                        default="full",
                        max_length=20,
                        verbose_name="任务类型",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "待处理"),
                            ("STARTED", "已开始"),
                            ("ANALYZING", "正在分析"),
                            ("SYNTHESIZING", "正在合成"),
                            ("POST_PROCESSING", "正在后处理"),
                            ("PUBLISHING", "正在发布"),
                            ("DONE", "已完成"),
                            ("FAILED", "失败"),
                            ("CANCELLED", "已取消"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                (
                    "celery_task_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Celery任务ID",
                    ),
                ),
                (
                    "parent_task_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="父任务ID",
                    ),
                ),
                (
                    "total_segments",
                    models.IntegerField(default=0, verbose_name="总片段数"),
                ),
                (
                    "completed_segments",
                    models.IntegerField(default=0, verbose_name="已完成片段数"),
                ),
                (
                    "failed_segments",
                    models.IntegerField(default=0, verbose_name="失败片段数"),
                ),
                (
                    "deepseek_total_tokens",
                    models.IntegerField(default=0, verbose_name="DeepSeek总Token"),
                ),
                (
                    "minimax_total_characters",
                    models.IntegerField(default=0, verbose_name="MiniMax总字符"),
                ),
                (
                    "total_cost_estimate",
                    models.FloatField(
                        blank=True, null=True, verbose_name="总预估成本"
                    ),
                ),
                (
                    "deepseek_calls",
                    models.IntegerField(default=0, verbose_name="DeepSeek调用次数"),
                ),
                (
                    "minimax_calls",
                    models.IntegerField(default=0, verbose_name="MiniMax调用次数"),
                ),
                (
                    "deepseek_avg_latency_ms",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="DeepSeek平均延迟(ms)"
                    ),
                ),
                (
                    "minimax_avg_latency_ms",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="MiniMax平均延迟(ms)"
                    ),
                ),
                (
                    "total_audio_duration_ms",
                    models.BigIntegerField(
                        blank=True, null=True, verbose_name="总音频时长(ms)"
                    ),
                ),
                (
                    "output_format",
                    models.CharField(
                        choices=[("mp3", "MP3"), ("wav", "WAV"), ("ogg", "OGG")],
                        default="mp3",
                        max_length=10,
                        verbose_name="输出格式",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, null=True, verbose_name="错误信息"),
                ),
                (
                    "error_traceback",
                    models.TextField(blank=True, null=True, verbose_name="错误堆栈"),
                ),
                (
                    "worker_name",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="Worker名称"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="开始时间"
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="完成时间"
                    ),
                ),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tts_tasks",
                        to="core.book",
                        verbose_name="关联书籍",
                    ),
                ),
            ],
            options={
                "verbose_name": "TTS任务",
                "verbose_name_plural": "TTS任务列表",
                "db_table": "tts_tasks",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PublishChannel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="渠道名称")),
                (
                    "platform_type",
                    models.CharField(
                        choices=[
                            ("ximalaya", "喜马拉雅"),
                            ("qingting", "蜻蜓FM"),
                            ("podcast", "播客"),
                            ("custom", "自定义"),
                        ],
                        max_length=20,
                        verbose_name="平台类型",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="渠道描述"),
                ),
                (
                    "is_enabled",
                    models.BooleanField(default=True, verbose_name="是否启用"),
                ),
                (
                    "auto_publish",
                    models.BooleanField(default=False, verbose_name="自动发布"),
                ),
                (
                    "priority",
                    models.IntegerField(
                        default=0, help_text="数字越大优先级越高", verbose_name="优先级"
                    ),
                ),
                (
                    "api_config",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="API配置"
                    ),
                ),
                (
                    "oauth_client_id",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="OAuth客户端ID"
                    ),
                ),
                (
                    "oauth_access_token",
                    models.TextField(
                        blank=True, null=True, verbose_name="OAuth访问令牌"
                    ),
                ),
                (
                    "oauth_refresh_token",
                    models.TextField(
                        blank=True, null=True, verbose_name="OAuth刷新令牌"
                    ),
                ),
                (
                    "oauth_expires_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="OAuth过期时间"
                    ),
                ),
                (
                    "publish_as_draft",
                    models.BooleanField(default=True, verbose_name="发布为草稿"),
                ),
                (
                    "category",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="默认分类"
                    ),
                ),
                (
                    "tags",
                    models.JSONField(blank=True, default=list, verbose_name="默认标签"),
                ),
                (
                    "total_published",
                    models.IntegerField(default=0, verbose_name="已发布书籍数"),
                ),
                (
                    "success_count",
                    models.IntegerField(default=0, verbose_name="成功次数"),
                ),
                (
                    "failure_count",
                    models.IntegerField(default=0, verbose_name="失败次数"),
                ),
                (
                    "last_published_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="最后发布时间"
                    ),
                ),
                (
                    "user_id",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="关联用户ID"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
            ],
            options={
                "verbose_name": "发布渠道",
                "verbose_name_plural": "发布渠道列表",
                "db_table": "publish_channels",
                "ordering": ["-priority", "-total_published"],
            },
        ),
        migrations.CreateModel(
            name="PublishRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "待发布"),
                            ("PREPARING", "准备中"),
                            ("UPLOADING", "上传中"),
                            ("DONE", "已完成"),
                            ("PARTIALLY_DONE", "部分完成"),
                            ("FAILED", "失败"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                (
                    "external_album_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="外部专辑ID",
                    ),
                ),
                (
                    "external_album_url",
                    models.URLField(
                        blank=True, max_length=1000, null=True, verbose_name="外部专辑URL"
                    ),
                ),
                (
                    "external_category_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="外部分类ID",
                    ),
                ),
                (
                    "chapters_published",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="章节发布映射"
                    ),
                ),
                (
                    "total_chapters",
                    models.IntegerField(default=0, verbose_name="总章节数"),
                ),
                (
                    "published_chapters",
                    models.IntegerField(default=0, verbose_name="已发布章节数"),
                ),
                (
                    "failed_chapters",
                    models.IntegerField(default=0, verbose_name="失败章节数"),
                ),
                (
                    "api_calls",
                    models.IntegerField(default=0, verbose_name="API调用次数"),
                ),
                (
                    "estimated_cost",
                    models.FloatField(
                        blank=True, null=True, verbose_name="预估成本"
                    ),
                ),
                (
                    "result_details",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="结果详情"
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, null=True, verbose_name="错误信息"),
                ),
                (
                    "error_code",
                    models.CharField(
                        blank=True, max_length=50, null=True, verbose_name="错误代码"
                    ),
                ),
                (
                    "retry_count",
                    models.IntegerField(default=0, verbose_name="重试次数"),
                ),
                (
                    "celery_task_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Celery任务ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "published_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="发布时间"
                    ),
                ),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="publish_records",
                        to="core.book",
                        verbose_name="关联书籍",
                    ),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="publish_records",
                        to="core.publishchannel",
                        verbose_name="发布渠道",
                    ),
                ),
            ],
            options={
                "verbose_name": "发布记录",
                "verbose_name_plural": "发布记录列表",
                "db_table": "publish_records",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Sentence",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sentence_index",
                    models.IntegerField(verbose_name="句子序号"),
                ),
                (
                    "text",
                    models.TextField(verbose_name="句子文本"),
                ),
                (
                    "sentence_type",
                    models.CharField(
                        choices=[("narration", "旁白"), ("dialogue", "对话")],
                        default="narration",
                        max_length=20,
                        verbose_name="句子类型",
                    ),
                ),
                (
                    "speaker",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="说话人"
                    ),
                ),
                (
                    "is_narrator",
                    models.BooleanField(default=True, verbose_name="是否旁白"),
                ),
                (
                    "emotion",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("calm", "平静"),
                            ("happy", "高兴"),
                            ("sad", "悲伤"),
                            ("angry", "愤怒"),
                            ("nervous", "紧张"),
                            ("surprised", "惊讶"),
                            ("gentle", "温柔"),
                            ("serious", "严肃"),
                            ("cold", "冷漠"),
                            ("sarcastic", "嘲讽"),
                        ],
                        max_length=20,
                        null=True,
                        verbose_name="情感",
                    ),
                ),
                (
                    "emotion_intensity",
                    models.CharField(
                        blank=True,
                        choices=[("weak", "弱"), ("medium", "中"), ("strong", "强")],
                        max_length=20,
                        null=True,
                        verbose_name="情感强度",
                    ),
                ),
                (
                    "polyphone_fixes",
                    models.JSONField(
                        blank=True, default=list, verbose_name="多音字修正"
                    ),
                ),
                (
                    "voice_context",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="语音特征"
                    ),
                ),
                (
                    "special_markers",
                    models.JSONField(
                        blank=True, default=list, verbose_name="特殊标记"
                    ),
                ),
                (
                    "is_ancient_text",
                    models.BooleanField(default=False, verbose_name="古文"),
                ),
                (
                    "is_poetry",
                    models.BooleanField(default=False, verbose_name="诗词"),
                ),
                (
                    "is_inner_thought",
                    models.BooleanField(default=False, verbose_name="内心独白"),
                ),
                (
                    "is_system_prompt",
                    models.BooleanField(default=False, verbose_name="系统提示"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "chapter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sentences",
                        to="core.chapter",
                        verbose_name="所属章节",
                    ),
                ),
            ],
            options={
                "verbose_name": "句子",
                "verbose_name_plural": "句子列表",
                "db_table": "sentences",
                "ordering": ["chapter", "sentence_index"],
            },
        ),
        migrations.AddIndex(
            model_name="sentence",
            index=models.Index(
                fields=["chapter", "sentence_index"],
                name="sentences_chapter_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="sentence",
            index=models.Index(
                fields=["sentence_type"], name="sentences_type_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="sentence",
            index=models.Index(
                fields=["emotion"], name="sentences_emotion_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="sentence",
            index=models.Index(
                fields=["speaker"], name="sentences_speaker_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="sentence",
            constraint=models.UniqueConstraint(
                fields=["chapter", "sentence_index"],
                name="uq_chapter_sentence",
            ),
        ),
        migrations.CreateModel(
            name="SoundEffect",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=200, verbose_name="音效名称")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="音效描述"),
                ),
                (
                    "chinese_description",
                    models.TextField(
                        blank=True, null=True, verbose_name="中文描述"
                    ),
                ),
                (
                    "effect_type",
                    models.CharField(
                        choices=[
                            ("environment", "环境音"),
                            ("action", "动作音"),
                            ("transition", "转场音"),
                            ("nature", "自然音"),
                            ("ambient", "氛围音"),
                            ("weather", "天气音"),
                            ("urban", "城市音"),
                            ("fantasy", "奇幻音"),
                            ("scifi", "科幻音"),
                            ("other", "其他"),
                        ],
                        db_index=True,
                        default="other",
                        max_length=20,
                        verbose_name="音效类型",
                    ),
                ),
                (
                    "layer",
                    models.CharField(
                        choices=[
                            ("background", "背景层"),
                            ("foreground", "前景层"),
                            ("transition", "转场层"),
                        ],
                        default="background",
                        max_length=20,
                        verbose_name="声音层次",
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        default=5,
                        help_text="优先级，数字越大优先级越高",
                        verbose_name="优先级",
                    ),
                ),
                (
                    "tags",
                    models.JSONField(
                        blank=True, default=list, verbose_name="标签列表"
                    ),
                ),
                (
                    "chinese_tags",
                    models.JSONField(
                        blank=True, default=list, verbose_name="中文标签"
                    ),
                ),
                (
                    "semantic_keywords",
                    models.JSONField(
                        blank=True,
                        default=list,
                        verbose_name="语义关键词",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("freesound", "Freesound"),
                            ("uploaded", "用户上传"),
                            ("generated", "AI生成"),
                            ("builtin", "内置"),
                        ],
                        default="uploaded",
                        max_length=20,
                        verbose_name="来源",
                    ),
                ),
                (
                    "source_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="来源ID",
                    ),
                ),
                (
                    "source_url",
                    models.URLField(
                        blank=True, max_length=500, null=True, verbose_name="来源URL"
                    ),
                ),
                (
                    "license_type",
                    models.CharField(
                        choices=[
                            ("cc0", "CC0"),
                            ("cc_by", "CC BY"),
                            ("cc_sa", "CC BY-SA"),
                            ("proprietary", "专有"),
                        ],
                        default="cc0",
                        max_length=20,
                        verbose_name="许可类型",
                    ),
                ),
                (
                    "duration_ms",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="时长(毫秒)"
                    ),
                ),
                (
                    "file_format",
                    models.CharField(
                        choices=[
                            ("mp3", "MP3"),
                            ("wav", "WAV"),
                            ("ogg", "OGG"),
                            ("flac", "FLAC"),
                        ],
                        default="mp3",
                        max_length=10,
                        verbose_name="文件格式",
                    ),
                ),
                (
                    "file_size",
                    models.BigIntegerField(
                        blank=True, null=True, verbose_name="文件大小"
                    ),
                ),
                (
                    "sample_rate",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="采样率"
                    ),
                ),
                (
                    "local_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="本地路径"
                    ),
                ),
                (
                    "minio_path",
                    models.CharField(
                        blank=True, max_length=500, null=True, verbose_name="MinIO路径"
                    ),
                ),
                (
                    "minio_url",
                    models.URLField(
                        blank=True, max_length=500, null=True, verbose_name="MinIO URL"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "启用"),
                            ("inactive", "停用"),
                            ("processing", "处理中"),
                            ("error", "错误"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                (
                    "is_favorite",
                    models.BooleanField(default=False, verbose_name="收藏"),
                ),
                (
                    "is_verified",
                    models.BooleanField(default=False, verbose_name="已审核"),
                ),
                (
                    "verified_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="审核时间"
                    ),
                ),
                (
                    "suitable_scenes",
                    models.JSONField(
                        blank=True,
                        default=list,
                        verbose_name="适用场景",
                    ),
                ),
                (
                    "recommended_volume_min",
                    models.FloatField(
                        blank=True,
                        default=0.3,
                        null=True,
                        verbose_name="推荐音量最小值",
                    ),
                ),
                (
                    "recommended_volume_max",
                    models.FloatField(
                        blank=True,
                        default=0.7,
                        null=True,
                        verbose_name="推荐音量最大值",
                    ),
                ),
                (
                    "recommended_fade_in_ms",
                    models.IntegerField(
                        blank=True,
                        default=100,
                        null=True,
                        verbose_name="推荐淡入时长(ms)",
                    ),
                ),
                (
                    "recommended_fade_out_ms",
                    models.IntegerField(
                        blank=True,
                        default=100,
                        null=True,
                        verbose_name="推荐淡出时长(ms)",
                    ),
                ),
                (
                    "usage_count",
                    models.IntegerField(default=0, verbose_name="使用次数"),
                ),
                (
                    "last_used_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="最后使用时间"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
            ],
            options={
                "verbose_name": "音效",
                "verbose_name_plural": "音效列表",
                "db_table": "sound_effects",
                "ordering": ["-usage_count", "-priority", "name"],
                "indexes": [
                    models.Index(
                        fields=["effect_type", "layer"],
                        name="sfx_type_layer_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SoundEffectUsage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "trigger_at_ms",
                    models.IntegerField(verbose_name="触发时间(毫秒)"),
                ),
                (
                    "volume",
                    models.FloatField(
                        blank=True, default=0.5, verbose_name="音量"
                    ),
                ),
                (
                    "fade_in_ms",
                    models.IntegerField(
                        blank=True, default=100, verbose_name="淡入时长"
                    ),
                ),
                (
                    "fade_out_ms",
                    models.IntegerField(
                        blank=True, default=100, verbose_name="淡出时长"
                    ),
                ),
                (
                    "match_score",
                    models.FloatField(
                        blank=True, default=0.0, verbose_name="匹配分数"
                    ),
                ),
                (
                    "matched_from_query",
                    models.CharField(
                        blank=True,
                        max_length=500,
                        null=True,
                        verbose_name="匹配的查询词",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="创建时间"
                    ),
                ),
                (
                    "chapter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sound_effect_usages",
                        to="core.chapter",
                        verbose_name="所属章节",
                    ),
                ),
                (
                    "sound_effect",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usages",
                        to="core.soundeffect",
                        verbose_name="音效",
                    ),
                ),
                (
                    "book_id",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="书籍ID"
                    ),
                ),
            ],
            options={
                "verbose_name": "音效使用记录",
                "verbose_name_plural": "音效使用记录",
                "db_table": "sound_effect_usages",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="soundeffectcollection",
            name="sound_effects",
            field=models.ManyToManyField(
                blank=True,
                related_name="collections",
                through="core.SoundEffectCollectionItem",
                to="core.soundeffect",
                verbose_name="音效列表",
            ),
        ),
        migrations.CreateModel(
            name="SoundEffectCollectionItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "custom_volume",
                    models.FloatField(
                        blank=True,
                        default=0.5,
                        null=True,
                        verbose_name="自定义音量",
                    ),
                ),
                (
                    "sort_order",
                    models.IntegerField(
                        default=0, verbose_name="排序顺序"
                    ),
                ),
                (
                    "added_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="添加时间"
                    ),
                ),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="core.soundeffectcollection",
                        verbose_name="收藏集",
                    ),
                ),
                (
                    "sound_effect",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collection_items",
                        to="core.soundeffect",
                        verbose_name="音效",
                    ),
                ),
            ],
            options={
                "verbose_name": "收藏集项目",
                "verbose_name_plural": "收藏集项目",
                "db_table": "sound_effect_collection_items",
                "ordering": ["collection", "sort_order"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["collection", "sound_effect"],
                        name="uq_collection_soundeffect",
                    ),
                ],
            },
        ),
    ]
