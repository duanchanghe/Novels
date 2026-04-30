# ===========================================
# EPUB 解析服务测试
# ===========================================

"""
EPUB 解析服务单元测试

测试 EPUB 文件的解析、元数据提取、DRM检测等功能。
"""

import pytest
import os
import zipfile
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock

from services.svc_epub_parser import EPUBParserService
from core.exceptions import EPUBParseError


class TestEPUBParserService:
    """EPUB 解析服务测试类"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return EPUBParserService()

    @pytest.fixture
    def sample_epub_bytes(self):
        """创建示例 EPUB 字节数据"""
        # 创建一个最小的 EPUB 文件
        epub_content = self._create_minimal_epub()
        return epub_content

    def _create_minimal_epub(self) -> bytes:
        """创建最小化的 EPUB 文件用于测试"""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # mimetype 必须是非压缩的
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
            zf.writestr("META-INF/container.xml", container_xml.encode('utf-8'))

            # content.opf
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>测试书籍</dc:title>
    <dc:creator>测试作者</dc:creator>
    <dc:language>zh-CN</dc:language>
    <dc:publisher>测试出版社</dc:publisher>
    <dc:description>这是一本测试书籍</dc:description>
    <dc:identifier id="bookid">test-book-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>'''
            zf.writestr("OEBPS/content.opf", content_opf.encode('utf-8'))

            # chapter1.xhtml
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>第一章</title></head>
<body>
  <h1>第一章 测试标题</h1>
  <p>这是第一段的文本内容。</p>
  <p>这是第二段的文本内容，包含对话："你好啊！"他说。</p>
  <p>第三段的文本内容。</p>
</body>
</html>'''
            zf.writestr("OEBPS/chapter1.xhtml", chapter1.encode('utf-8'))

        return buffer.getvalue()

    def _create_epub_with_cover(self) -> bytes:
        """创建带封面的 EPUB 文件"""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
            zf.writestr("META-INF/container.xml", container_xml.encode('utf-8'))

            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>带封面的书籍</dc:title>
    <dc:creator>作者乙</dc:creator>
    <dc:language>zh-CN</dc:language>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
    <item id="cover-image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>'''
            zf.writestr("OEBPS/content.opf", content_opf.encode('utf-8'))

            # 1x1 像素的 JPEG 图片（最小的有效 JPEG）
            jpeg_data = bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
                0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
                0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
                0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
                0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
                0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
                0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
                0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
                0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
                0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
                0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
                0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
                0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
                0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
                0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
                0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
                0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
                0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
                0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
                0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
                0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
                0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
                0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
                0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
                0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
                0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD4, 0xFF, 0xD9
            ])
            zf.writestr("OEBPS/cover.jpg", jpeg_data)

            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>第一章</title></head>
<body>
  <h1>第一章 测试章节</h1>
  <p>带封面的书籍内容。</p>
</body>
</html>'''
            zf.writestr("OEBPS/chapter1.xhtml", chapter1.encode('utf-8'))

        return buffer.getvalue()

    # ===== 测试 parse_bytes 方法 =====

    def test_parse_bytes_basic(self, parser, sample_epub_bytes):
        """测试基本 EPUB 字节解析"""
        result = parser.parse_bytes(sample_epub_bytes)

        assert result is not None
        assert "title" in result
        assert "author" in result
        assert "chapters" in result
        assert "chapter_count" in result
        assert "total_characters" in result
        assert "total_words" in result
        assert result["chapter_count"] >= 1

    def test_parse_bytes_metadata_extraction(self, parser, sample_epub_bytes):
        """测试元数据提取"""
        result = parser.parse_bytes(sample_epub_bytes)

        assert result["title"] == "测试书籍"
        assert result["author"] == "测试作者"
        assert result["language"] == "zh-CN"
        assert result["publisher"] == "测试出版社"
        assert result["description"] == "这是一本测试书籍"

    def test_parse_bytes_chapter_extraction(self, parser, sample_epub_bytes):
        """测试章节内容提取"""
        result = parser.parse_bytes(sample_epub_bytes)

        assert len(result["chapters"]) > 0
        chapter = result["chapters"][0]
        assert "title" in chapter
        assert "content" in chapter
        assert "第一章" in chapter["content"] or "测试" in chapter["content"]

    def test_parse_bytes_with_cover(self, parser):
        """测试带封面的 EPUB 解析"""
        epub_bytes = self._create_epub_with_cover()
        result = parser.parse_bytes(epub_bytes)

        assert result["title"] == "带封面的书籍"
        assert result["author"] == "作者乙"
        # 封面可能提取不到，这是正常的
        assert "cover_image" in result
        assert "cover_image_type" in result

    def test_parse_bytes_invalid_data(self, parser):
        """测试无效数据解析"""
        with pytest.raises(EPUBParseError):
            parser.parse_bytes(b"invalid epub data")

    def test_parse_bytes_empty_data(self, parser):
        """测试空数据解析"""
        with pytest.raises(EPUBParseError):
            parser.parse_bytes(b"")

    # ===== 测试 clean_html 方法 =====

    def test_clean_html_basic(self, parser):
        """测试基本 HTML 清洗"""
        html = "<p>Hello, <b>World</b>!</p>"
        result = parser.clean_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

    def test_clean_html_with_scripts(self, parser):
        """测试移除脚本标签"""
        html = "<p>Content</p><script>alert('xss');</script>"
        result = parser.clean_html(html)
        assert "Content" in result
        assert "alert" not in result

    def test_clean_html_with_styles(self, parser):
        """测试移除样式标签"""
        html = "<style>.hidden { display: none; }</style><p>Visible</p>"
        result = parser.clean_html(html)
        assert "Visible" in result
        assert ".hidden" not in result

    def test_clean_html_chinese(self, parser):
        """测试中文 HTML 清洗"""
        html = "<p>你好，世界！</p><span>测试文本</span>"
        result = parser.clean_html(html)
        assert "你好" in result
        assert "世界" in result
        assert "测试文本" in result

    def test_clean_html_whitespace_normalization(self, parser):
        """测试空白字符规范化"""
        html = "<p>Line 1</p>\n\n\n<p>Line 2</p>\n\n\n\n<p>Line 3</p>"
        result = parser.clean_html(html)
        # 多个换行应该被合并
        assert "\n\n\n" not in result

    # ===== 测试格式校验 =====

    def test_validate_epub_format_valid(self, parser, sample_epub_bytes, tmp_path):
        """测试有效 EPUB 格式校验"""
        epub_path = tmp_path / "valid.epub"
        with open(epub_path, "wb") as f:
            f.write(sample_epub_bytes)

        assert parser._validate_epub_format(str(epub_path)) is True

    def test_validate_epub_format_invalid(self, parser, tmp_path):
        """测试无效 EPUB 格式校验"""
        invalid_path = tmp_path / "invalid.txt"
        with open(invalid_path, "w") as f:
            f.write("not an epub")

        assert parser._validate_epub_format(str(invalid_path)) is False

    def test_validate_epub_bytes_valid(self, parser, sample_epub_bytes):
        """测试有效 EPUB 字节校验"""
        assert parser._validate_epub_bytes(sample_epub_bytes) is True

    def test_validate_epub_bytes_invalid(self, parser):
        """测试无效 EPUB 字节校验"""
        assert parser._validate_epub_bytes(b"not an epub") is False

    # ===== 测试 DRM 检测 =====

    def test_drm_detection_none(self, parser, sample_epub_bytes, tmp_path):
        """测试无 DRM 的 EPUB"""
        epub_path = tmp_path / "test.epub"
        with open(epub_path, "wb") as f:
            f.write(sample_epub_bytes)

        assert parser._is_drm_protected(str(epub_path)) is False

    def test_drm_detection_bytes(self, parser, sample_epub_bytes):
        """测试无 DRM 的 EPUB 字节"""
        assert parser._is_drm_protected_bytes(sample_epub_bytes) is False

    def test_drm_detection_with_drm(self, parser, tmp_path):
        """测试带 DRM 的 EPUB"""
        # 创建包含 encryption.xml 的 EPUB
        import zipfile
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            zf.writestr("META-INF/encryption.xml", "<encryption/>")
            zf.writestr("META-INF/container.xml", '''<?xml version="1.0"?>
<container version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>''')
            zf.writestr("OEBPS/content.opf", '''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata><dc:title>DRM书</dc:title></metadata>
  <manifest><item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/></manifest>
  <spine><itemref idref="ch1"/></spine>
</package>''')
            zf.writestr("OEBPS/ch1.xhtml", "<html><body><p>内容</p></body></html>")

        epub_path = tmp_path / "drm.epub"
        with open(epub_path, "wb") as f:
            f.write(buffer.getvalue())

        assert parser._is_drm_protected(str(epub_path)) is True

    # ===== 测试边界情况 =====

    def test_parse_bytes_missing_metadata(self, parser):
        """测试缺少元数据的 EPUB"""
        import zipfile
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            zf.writestr("META-INF/container.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''.encode('utf-8'))
            zf.writestr("OEBPS/content.opf", '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title></dc:title>
  </metadata>
  <manifest>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="ch1"/></spine>
</package>'''.encode('utf-8'))
            zf.writestr("OEBPS/ch1.xhtml", '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><p>内容</p></body></html>'''.encode('utf-8'))

        result = parser.parse_bytes(buffer.getvalue())
        # 空标题应该被替换为"未命名"或None
        assert result["title"] in ["未命名", "", None]
        assert result["language"] in ["zh-CN", None]

    def test_parse_bytes_multiple_chapters(self, parser):
        """测试多章节 EPUB 解析"""
        import zipfile
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            zf.writestr("META-INF/container.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''.encode('utf-8'))
            zf.writestr("OEBPS/content.opf", '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>多章节书籍</dc:title>
  </metadata>
  <manifest>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>'''.encode('utf-8'))
            zf.writestr("OEBPS/ch1.xhtml", '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>第一章</h1><p>第一张内容</p></body></html>'''.encode('utf-8'))
            zf.writestr("OEBPS/ch2.xhtml", '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>第二章</h1><p>第二章内容</p></body></html>'''.encode('utf-8'))

        result = parser.parse_bytes(buffer.getvalue())
        assert result["chapter_count"] == 2
        assert len(result["chapters"]) == 2


class TestEPUBParserEdgeCases:
    """EPUB 解析边界情况测试"""

    @pytest.fixture
    def parser(self):
        return EPUBParserService()

    def test_parse_empty_chapters(self, parser):
        """测试空章节处理"""
        import zipfile
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            zf.writestr("META-INF/container.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''.encode('utf-8'))
            zf.writestr("OEBPS/content.opf", '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>测试</dc:title></metadata>
  <manifest>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="ch1"/></spine>
</package>'''.encode('utf-8'))
            # 空白内容
            zf.writestr("OEBPS/ch1.xhtml", '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body></body></html>'''.encode('utf-8'))

        result = parser.parse_bytes(buffer.getvalue())
        # 空章节不应被添加
        assert all(ch.get("content", "").strip() for ch in result["chapters"])

    def test_parse_special_characters(self, parser):
        """测试特殊字符处理"""
        import zipfile
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            zf.writestr("META-INF/container.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''.encode('utf-8'))
            zf.writestr("OEBPS/content.opf", '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>特殊字符测试</dc:title></metadata>
  <manifest>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="ch1"/></spine>
</package>'''.encode('utf-8'))
            zf.writestr("OEBPS/ch1.xhtml", '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<p>英文: Hello World</p>
<p>数字: 12345</p>
<p>符号: @#$%^&amp;*()</p>
<p>中文: 你好世界</p>
<p>混合: 测试abc123</p>
</body></html>'''.encode('utf-8'))

        result = parser.parse_bytes(buffer.getvalue())
        content = result["chapters"][0]["content"]
        assert "Hello" in content
        assert "12345" in content
        assert "你好" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
