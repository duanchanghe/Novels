#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')
import asyncio
import re
import json
from services.svc_deepseek_analyzer import DeepSeekAnalyzerService
from sqlalchemy import text
from core.database import SessionLocal

async def test():
    a = DeepSeekAnalyzerService()
    db = SessionLocal()
    try:
        result = db.execute(text('SELECT raw_text FROM chapters WHERE book_id = 10 LIMIT 1'))
        row = result.fetchone()
        if row:
            chapter_text = row[0]
            short_text = chapter_text[:2000]
            print(f'Testing with {len(short_text)} chars')
            
            import httpx
            prompt = a.FULL_ANALYSIS_PROMPT.format(text=short_text, role_list='未知')
            
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{a.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {a.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": a.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": a.temperature,
                        "max_tokens": a.max_tokens,
                    },
                )
            
            print(f"Status: {response.status_code}")
            result_data = response.json()
            
            # 检查完整响应
            print(f"\nResult keys: {result_data.keys()}")
            print(f"Usage: {result_data.get('usage')}")
            
            content = result_data["choices"][0]["message"]["content"]
            
            # 检查结束的反引号
            print(f"\nContent ends with: {repr(content[-50:])}")
            
            # 检查是否有截断标记
            print(f"Ends with ```: {content.strip().endswith('```')}")
            print(f"Ends with newline: {content.endswith(chr(10))}")
    finally:
        db.close()

asyncio.run(test())
