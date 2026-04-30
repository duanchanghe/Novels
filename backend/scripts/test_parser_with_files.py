#!/usr/bin/env python3
"""
使用测试 EPUB 文件验证解析器功能
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, '/app')

from services.svc_epub_parser import EPUBParserService
from core.exceptions import EPUBParseError


def test_epub_file(filepath: str) -> dict:
    """测试单个 EPUB 文件"""
    parser = EPUBParserService()
    result = {
        "success": False,
        "file": os.path.basename(filepath),
        "title": None,
        "author": None,
        "chapter_count": 0,
        "total_chars": 0,
        "error": None,
        "warnings": [],
    }

    try:
        result.update(parser.parse_file(filepath))
        result["success"] = True

        # 检查 DRM
        if parser._is_drm_protected(filepath):
            result["warnings"].append("DRM protected (detected)")

    except EPUBParseError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"

    return result


def main():
    test_dir = "/app/test_data/epub"

    print("=" * 70)
    print("EPUB Parser Test Suite - Using Real Test Files")
    print("=" * 70)
    print(f"Test directory: {test_dir}\n")

    # 获取所有 EPUB 文件
    epub_files = sorted([f for f in os.listdir(test_dir) if f.endswith('.epub')])

    if not epub_files:
        print("[ERROR] No EPUB files found in test directory!")
        return

    results = []
    drm_detected_files = []

    for filename in epub_files:
        filepath = os.path.join(test_dir, filename)
        print(f"Testing: {filename}")

        # 特殊处理 DRM 测试文件
        if "drm" in filename.lower():
            from services.svc_epub_parser import EPUBParserService
            parser = EPUBParserService()
            is_drm = parser._is_drm_protected(filepath)
            if is_drm:
                print(f"  ✓ DRM detected correctly")
                drm_detected_files.append(filename)
            else:
                print(f"  ✗ DRM NOT detected")
                results.append({"file": filename, "success": False, "error": "DRM not detected"})
            print()
            continue

        result = test_epub_file(filepath)
        results.append(result)

        if result["success"]:
            print(f"  ✓ Title: {result.get('title', 'N/A')}")
            print(f"  ✓ Author: {result.get('author', 'N/A')}")
            print(f"  ✓ Chapters: {result.get('chapter_count', 0)}")
            print(f"  ✓ Total chars: {result.get('total_characters', 0):,}")
            if result["warnings"]:
                print(f"  ⚠ Warnings: {', '.join(result['warnings'])}")
        else:
            print(f"  ✗ Error: {result['error']}")
        print()

    # 汇总
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    print(f"\nParsing tests: {success_count}/{total_count} passed")

    if drm_detected_files:
        print(f"DRM detection: {len(drm_detected_files)}/{len(drm_detected_files)} files detected")

    overall_success = success_count == total_count

    if overall_success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")
        print("\nFailed files:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['file']}: {r['error']}")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
