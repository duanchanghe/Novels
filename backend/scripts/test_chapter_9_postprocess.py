# ===========================================
# 测试脚本：后处理第9章音频
# ===========================================

"""
后处理第9章音频：拼接、混音、格式转换
"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'audiobook.settings')
import django
django.setup()

from tasks.task_postprocess import postprocess_chapter
from core.models import Chapter


def main():
    chapter_id = 9
    
    # 1. 检查章节状态
    chapter = Chapter.objects.get(id=chapter_id)
    print(f"=== 章节 {chapter_id} 信息 ===")
    print(f"标题: {chapter.title}")
    print(f"状态: {chapter.status}")
    
    # 2. 检查音频片段
    segments = chapter.segments.all()
    success_segments = segments.filter(status='SUCCESS').count()
    print(f"成功片段: {success_segments}")
    
    # 3. 执行后处理
    print(f"\n=== 开始后处理 ===")
    try:
        result = postprocess_chapter(chapter_id)
        print(f"后处理结果: {result}")
    except Exception as e:
        print(f"后处理失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
