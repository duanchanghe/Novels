#!/usr/bin/env python3
"""
从 Project Gutenberg 下载公版书 EPUB 进行测试
"""

import urllib.request
import urllib.error
import ssl
import os
import time

# 禁用 SSL 验证（某些环境下需要）
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 测试书籍列表（Project Gutenberg 公版书）
BOOKS = [
    {
        "id": "1342",
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "filename": "pride_and_prejudice.epub"
    },
    {
        "id": "11",
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "filename": "alice_in_wonderland.epub"
    },
    {
        "id": "345",
        "title": "Dracula",
        "author": "Bram Stoker",
        "filename": "dracula.epub"
    },
    {
        "id": "84",
        "title": "Frankenstein",
        "author": "Mary Shelley",
        "filename": "frankenstein.epub"
    },
    {
        "id": "64317",
        "title": "The Art of War (Chinese)",
        "author": "Sun Tzu",
        "filename": "art_of_war.epub"
    },
]


def download_book(book: dict, output_dir: str, max_retries: int = 3) -> bool:
    """下载单个书籍"""
    url = f"https://www.gutenberg.org/ebooks/{book['id']}.epub.noimages"
    output_path = os.path.join(output_dir, book["filename"])

    # 如果已存在，跳过
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"  [SKIP] {book['title']} - already exists")
        return True

    print(f"  [DOWNLOAD] {book['title']} by {book['author']}...")

    for attempt in range(max_retries):
        try:
            # 使用流式下载
            request = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Test Downloader/1.0)'
            })

            with urllib.request.urlopen(request, timeout=120, context=ctx) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192

                with open(output_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = (downloaded / total_size) * 100
                            print(f"\r    Progress: {pct:.1f}%", end='', flush=True)

                print()  # 换行
                print(f"  [OK] {book['title']} - {downloaded:,} bytes")

            return True

        except Exception as e:
            print(f"\n  [ERROR] Attempt {attempt + 1}/{max_retries}: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            time.sleep(2)  # 等待后重试

    print(f"  [FAILED] {book['title']}")
    return False


def main():
    # 获取输出目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "..", "..", "backend", "test_data", "epub")

    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Downloading test EPUB books from Project Gutenberg")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print()

    success_count = 0
    for i, book in enumerate(BOOKS, 1):
        print(f"[{i}/{len(BOOKS)}] {book['title']}")
        if download_book(book, output_dir):
            success_count += 1

    print()
    print("=" * 60)
    print(f"Download complete: {success_count}/{len(BOOKS)} books")
    print("=" * 60)

    # 列出下载的文件
    print("\nDownloaded files:")
    for f in sorted(os.listdir(output_dir)):
        if f.endswith('.epub'):
            path = os.path.join(output_dir, f)
            size = os.path.getsize(path)
            print(f"  - {f} ({size:,} bytes)")


if __name__ == "__main__":
    main()
