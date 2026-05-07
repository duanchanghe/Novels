#!/usr/bin/env python3
"""
测试脚本：验证 DeepSeek 分析服务的句子级拆分和音色区分效果
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.database import get_db_context
from core.models import Chapter
from services.svc_deepseek_analyzer import DeepSeekAnalyzerService
from services.svc_voice_mapper import VoiceMapperService
from core.constants import VoiceID


def test_chapter_analysis(chapter_id: int):
    """测试章节分析"""
    print(f"\n{'='*60}")
    print(f"测试章节 ID={chapter_id} 的分析")
    print('='*60)

    with get_db_context() as db:
        chapter = db.query(Chapter).filter(id=chapter_id).first()
        if not chapter:
            print(f"❌ 章节 {chapter_id} 不存在")
            return

        # 获取文本
        text = chapter.cleaned_text or chapter.raw_text or ""
        if not text:
            print(f"❌ 章节 {chapter_id} 没有文本内容")
            return

        print(f"📖 文本长度: {len(text)} 字符")
        print(f"📖 文本预览 (前200字):\n{text[:200]}...")
        print()

    # 执行分析
    print("🔄 调用 DeepSeek 分析服务...")
    analyzer = DeepSeekAnalyzerService()
    voice_mapper = VoiceMapperService()

    try:
        result = analyzer.analyze_chapter(text)
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return

    # 分析结果统计
    sentences = result.get("sentences", [])
    characters = result.get("characters", [])

    items = sentences

    print(f"\n📊 分析结果统计:")
    print(f"   - 句子/段落数: {len(items)}")
    print(f"   - 角色数: {len(characters)}")

    # 统计对话和旁白
    dialogues = [item for item in items if item.get("type") == "dialogue"]
    narrations = [item for item in items if item.get("type") == "narration"]

    print(f"   - 对话数: {len(dialogues)}")
    print(f"   - 旁白数: {len(narrations)}")

    # 检查问题1：对话是否正确标注了说话人
    print(f"\n🔍 问题1检查：旁白与对话分离")
    narrator_dialogues = [d for d in dialogues if d.get("speaker") == "旁白"]
    if narrator_dialogues:
        print(f"   ❌ 发现 {len(narrator_dialogues)} 条对话的 speaker 是'旁白'（错误）")
        for d in narrator_dialogues[:3]:
            print(f"      - {d.get('text', '')[:50]}...")
    else:
        print(f"   ✅ 所有对话都有正确的说话人（非'旁白'）")

    # 旁白说话人检查
    narrator_speakers = set(item.get("speaker") for item in narrations)
    if "旁白" in narrator_speakers or len(narrator_speakers) <= 1:
        print(f"   ✅ 旁白句子的 speaker 正确（应为'旁白'）")
    else:
        print(f"   ⚠️ 旁白句子 speaker: {narrator_speakers}")

    # 问题2：音色区分度检查
    print(f"\n🔍 问题2检查：音色区分度")

    # 获取所有说话人及其音色
    speaker_voices = {}
    for item in items:
        speaker = item.get("speaker", "旁白")
        if speaker not in speaker_voices:
            char_info = next((c for c in characters if c.get("name") == speaker), None)
            voice = voice_mapper.get_voice_for_speaker(speaker, char_info)
            speaker_voices[speaker] = voice.get("voice_id", "unknown")

    # 统计音色使用情况
    voice_usage = {}
    for speaker, voice_id in speaker_voices.items():
        if voice_id not in voice_usage:
            voice_usage[voice_id] = []
        voice_usage[voice_id].append(speaker)

    print(f"   音色使用统计 (共 {len(voice_usage)} 种音色):")
    for voice_id, speakers in voice_usage.items():
        voice_name = {
            VoiceID.MALE_QN_QINGSE: "清澈青年",
            VoiceID.MALE_QN_JINGYING: "精英青年",
            VoiceID.MALE_QN_BADAO: "霸道青年",
            VoiceID.GENTLEMAN: "温润男声",
            VoiceID.MALE_ANCHOR: "播报男声",
            VoiceID.RELIABLE_EXECUTIVE: "沉稳高管",
            VoiceID.FEMALE_TIANMEI: "甜美女声",
            VoiceID.FEMALE_SHAON: "少女音色",
            VoiceID.FEMALE_YUJIE: "御姐音色",
            VoiceID.FEMALE_CHENGSHU: "成熟女性",
        }.get(voice_id, voice_id)
        print(f"   - {voice_name} ({voice_id}): {speakers}")

    # 详细展示角色和音色
    print(f"\n📋 角色音色映射详情:")
    for char in characters:
        name = char.get("name", "未知")
        gender = char.get("gender", "unknown")
        char_info = char
        voice = voice_mapper.get_voice_for_speaker(name, char_info)
        voice_id = voice.get("voice_id", "unknown")
        personality = char.get("personality", "")
        voice_desc = char.get("voice_description", "")

        print(f"   [{name}]")
        print(f"      - 性别: {gender}")
        print(f"      - 性格: {personality or '未标注'}")
        print(f"      - 声线描述: {voice_desc or '未标注'}")
        print(f"      - 音色: {voice_id}")

    # 展示前几条分析结果示例
    print(f"\n📝 分析结果示例（前5条）:")
    for i, item in enumerate(items[:5]):
        text = item.get("text", "")[:40]
        item_type = item.get("type", "unknown")
        speaker = item.get("speaker", "未知")
        emotion = item.get("emotion", "-")
        voice = speaker_voices.get(speaker, "unknown")

        type_icon = "💬" if item_type == "dialogue" else "📖"
        print(f"   {i+1}. {type_icon} [{item_type}] speaker={speaker} emotion={emotion}")
        print(f"      文本: {text}...")


if __name__ == "__main__":
    chapter_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    test_chapter_analysis(chapter_id)
