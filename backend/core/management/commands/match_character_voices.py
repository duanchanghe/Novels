# ===========================================
# 管理命令 - 批量匹配角色音色
# ===========================================

"""
Django 管理命令：批量为书籍角色匹配音色

用法：
    python manage.py match_character_voices <book_id> [--preview] [--min-confidence=medium] [--apply]

示例：
    # 预览匹配结果
    python manage.py match_character_voices 1 --preview

    # 预览并应用（高置信度）
    python manage.py match_character_voices 1 --apply --min-confidence=high

    # 预览并应用（中及以上置信度）
    python manage.py match_character_voices 1 --apply --min-confidence=medium
"""

from django.core.management.base import BaseCommand, CommandError
from core.models import Book

from services.svc_character_voice_matcher import (
    CharacterVoiceMatcher,
    VoiceMatchConfidence,
)


class Command(BaseCommand):
    help = "为书籍的所有角色批量匹配最佳音色"

    def add_arguments(self, parser):
        parser.add_argument(
            "book_id",
            type=int,
            help="书籍ID",
        )
        parser.add_argument(
            "--preview",
            action="store_true",
            help="仅预览匹配结果，不实际应用",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="应用匹配结果到角色",
        )
        parser.add_argument(
            "--min-confidence",
            type=str,
            choices=["high", "medium", "low"],
            default="medium",
            help="最低置信度阈值（默认: medium）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="预览并显示将执行的更改，但不实际保存",
        )

    def handle(self, *args, **options):
        book_id = options["book_id"]
        is_preview = options["preview"]
        is_apply = options["apply"]
        min_confidence_str = options["min_confidence"]
        is_dry_run = options["dry_run"]

        # 验证书籍存在
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            raise CommandError(f"书籍ID {book_id} 不存在")

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"角色音色智能匹配")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"书籍: {book.title} (ID: {book_id})")

        # 创建匹配器
        matcher = CharacterVoiceMatcher()

        # 预览匹配结果
        self.stdout.write(f"\n正在分析角色...")
        preview = matcher.preview_matches(book_id)

        # 显示统计信息
        self.stdout.write(f"\n{'─'*40}")
        self.stdout.write(f"匹配统计:")
        self.stdout.write(f"  总角色数: {preview['total_characters']}")
        self.stdout.write(f"  按性别: {preview['by_gender']}")
        self.stdout.write(f"  按年龄: {preview['by_age_group']}")

        self.stdout.write(f"\n  按置信度:")
        for conf, count in preview['by_confidence'].items():
            self.stdout.write(f"    {conf}: {count}")

        self.stdout.write(f"\n  音色使用分布 (Top 10):")
        for voice in preview['voice_usage'][:10]:
            self.stdout.write(f"    {voice['voice_name']}: {voice['count']} 个角色")

        # 显示角色详情
        self.stdout.write(f"\n{'─'*40}")
        self.stdout.write(f"角色匹配详情:")
        self.stdout.write(f"")

        for char in preview['characters']:
            conf_color = {
                "high": self.style.SUCCESS("[高]"),
                "medium": self.style.WARNING("[中]"),
                "low": self.style.ERROR("[低]"),
            }.get(char['confidence'], char['confidence'])

            self.stdout.write(
                f"  {conf_color} {char['name']} | {char['gender']} | {char['age_group']} "
                f"→ {char['recommended_voice']}"
            )
            if char['reasons']:
                self.stdout.write(f"       原因: {'; '.join(char['reasons'])}")
            if char['speech_style']:
                self.stdout.write(f"       说话风格: {char['speech_style'][:40]}...")
            self.stdout.write("")

        # 根据选项执行
        if is_preview or (not is_apply and not is_dry_run):
            self.stdout.write(self.style.WARNING("\n使用 --apply 来应用这些匹配结果"))
            self.stdout.write(f"使用 --min-confidence=low 来包含所有匹配结果")

        if is_apply and not is_dry_run:
            confidence_map = {
                "high": VoiceMatchConfidence.HIGH,
                "medium": VoiceMatchConfidence.MEDIUM,
                "low": VoiceMatchConfidence.LOW,
            }
            min_confidence = confidence_map[min_confidence_str]

            self.stdout.write(f"\n正在应用匹配结果 (最低置信度: {min_confidence_str})...")

            # 构建结果对象
            from services.svc_character_voice_matcher import VoiceMatchResult
            conf_map = {"high": VoiceMatchConfidence.HIGH, "medium": VoiceMatchConfidence.MEDIUM, "low": VoiceMatchConfidence.LOW}
            results = []
            for char in preview['characters']:
                confidence = conf_map.get(char['confidence'], VoiceMatchConfidence.MEDIUM)
                if confidence.value >= min_confidence.value:
                    results.append(VoiceMatchResult(
                        character_id=char['id'],
                        character_name=char['name'],
                        recommended_voice_id=next(
                            (v['voice_id'] for v in preview['voice_usage']
                             if v['voice_name'] == char['recommended_voice']),
                            None
                        ),
                        recommended_voice_name=char['recommended_voice'],
                        confidence=confidence,
                        match_reasons=char['reasons'],
                        gender=char['gender'],
                        age_group=char['age_group'],
                        speech_style_preview=char['speech_style'],
                    ))

            updated, created = matcher.apply_matches(results, min_confidence)

            self.stdout.write(self.style.SUCCESS(f"\n✓ 完成!"))
            self.stdout.write(f"  更新了 {updated} 个角色的音色配置")
            self.stdout.write(f"  创建了 {created} 个音色配置记录")

        if is_dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] 未实际应用更改"))

        self.stdout.write("")
