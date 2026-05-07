# ===========================================
# 音频拼接脚本
# ===========================================

"""
使用 pydub 正确拼接第9章的音频片段
"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'audiobook.settings')
import django
django.setup()

from core.models import Chapter, AudioSegment
from core.models.segment import SegmentStatus
from pydub import AudioSegment as PydubAudioSegment
from datetime import datetime
import uuid
from io import BytesIO


def concat_audio(chapter_id: int):
    """拼接章节音频"""
    from services.svc_minio_storage import get_storage_service
    
    chapter = Chapter.objects.get(id=chapter_id)
    segments = chapter.segments.filter(status=SegmentStatus.SUCCESS).order_by('segment_index')
    
    print(f"=== 拼接章节 {chapter_id} ===")
    print(f"总片段数: {segments.count()}")
    
    storage = get_storage_service()
    
    # 收集并拼接音频
    combined = None
    total_duration = 0
    
    for seg in segments:
        print(f"处理片段 {seg.segment_index}...")
        if seg.audio_file_path:
            # 下载音频文件
            audio_data = storage.download_file("books-audio", seg.audio_file_path)
            
            # 使用 pydub 加载
            audio = PydubAudioSegment.from_mp3(BytesIO(audio_data))
            total_duration += len(audio)
            
            if combined is None:
                combined = audio
            else:
                combined = combined + audio
            
            print(f"  片段时长: {len(audio)/1000:.1f}s, 累计: {len(combined)/1000:.1f}s")
    
    if combined is None:
        print("没有找到音频片段")
        return None
    
    print(f"\n总时长: {len(combined)/1000:.1f} 秒")
    
    # 导出为 MP3
    print("导出 MP3...")
    output = BytesIO()
    combined.export(output, format="mp3", bitrate="192k")
    output_data = output.getvalue()
    
    # 保存到 MinIO
    object_name = f"chapters/{chapter_id}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.mp3"
    
    print(f"上传到: {object_name}")
    storage.upload_file(
        bucket="books-audio",
        object_name=object_name,
        data=output_data,
        content_type="audio/mpeg",
    )
    
    # 获取 URL
    url = storage.get_presigned_url("books-audio", object_name)
    
    # 更新章节
    chapter.audio_file_path = object_name
    chapter.audio_url = url
    chapter.audio_duration = len(combined)  # 毫秒
    chapter.audio_file_size = len(output_data)
    chapter.save(update_fields=['audio_file_path', 'audio_url', 'audio_duration', 'audio_file_size'])
    
    print(f"完成!")
    print(f"文件大小: {len(output_data) / 1024 / 1024:.2f} MB")
    print(f"时长: {len(combined) / 1000:.1f} 秒")
    print(f"URL: {url[:100]}...")
    
    return {
        "chapter_id": chapter_id,
        "audio_file_path": object_name,
        "audio_url": url,
        "file_size": len(output_data),
        "duration_ms": len(combined),
    }


if __name__ == "__main__":
    result = concat_audio(9)
    print(f"\n结果: {result}")
