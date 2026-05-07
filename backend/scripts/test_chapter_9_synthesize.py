# ===========================================
# 测试脚本：合成第9章音频
# ===========================================

"""
直接调用任务流水线合成第9章音频
"""

import os
import sys

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'audiobook.settings')
import django
django.setup()

from tasks.task_pipeline import create_segments
from tasks.task_synthesize import synthesize_chapter
from core.models import Chapter


def main():
    chapter_id = 9
    
    # 1. 检查章节状态
    chapter = Chapter.objects.get(id=chapter_id)
    print(f"=== 章节 {chapter_id} 信息 ===")
    print(f"标题: {chapter.title}")
    print(f"状态: {chapter.status}")
    print(f"总段落: {chapter.total_segments}")
    
    # 2. 创建音频片段
    print(f"\n=== 步骤1: 创建音频片段 ===")
    try:
        result = create_segments(chapter_id)
        print(f"创建结果: {result}")
    except Exception as e:
        print(f"创建片段失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 合成音频
    print(f"\n=== 步骤2: 合成音频 ===")
    try:
        result = synthesize_chapter(chapter_id)
        print(f"合成结果: {result}")
    except Exception as e:
        print(f"合成失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
