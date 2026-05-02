# ===========================================
# EPUB 解析服务
# ===========================================

"""
EPUB 解析服务

解析 EPUB 文件，提取元数据和章节内容。
支持：
- 元数据提取（书名、作者、封面、出版信息等）
- 章节结构提取
- DRM 检测
- 文本清洗
"""

import logging
import os
import zipfile
from typing import Dict, List, Any, Optional
from io import BytesIO
from datetime import datetime

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# ebooklib 类型常量（兼容新旧版本）
ITEM_IMAGE = 1  # EpubImage type
ITEM_DOCUMENT = 9  # EpubHtml type

from core.exceptions import EPUBParseError


logger = logging.getLogger("audiobook")


class EPUBParserService:
    """
    EPUB 解析服务

    提供 EPUB 文件的解析功能：
    - 元数据提取（书名、作者、封面、出版信息、ISBN等）
    - 章节内容提取
    - 封面图片提取
    - DRM 检测
    - 文件格式校验
    """

    # DRM 相关文件名检测
    DRM_PATTERNS = [
        "encryption.xml",
        "license.xml",
        ".adept",
        ".enc",
        "drm",
    ]

    def __init__(self):
        self.logger = logging.getLogger("audiobook.epub_parser")

    def parse_file(self, file_path: str, book_id: int = None) -> Dict[str, Any]:
        """
        解析 EPUB 文件

        Args:
            file_path: 文件路径
            book_id: 关联的书籍 ID

        Returns:
            dict: 解析结果

        Raises:
            EPUBParseError: 解析失败时抛出
        """
        if not os.path.exists(file_path):
            raise EPUBParseError(f"文件不存在: {file_path}")

        # 校验文件格式
        if not self._validate_epub_format(file_path):
            raise EPUBParseError("无效的 EPUB 文件格式")

        try:
            # 检测 DRM
            if self._is_drm_protected(file_path):
                raise EPUBParseError("EPUB 文件受 DRM 保护，无法解析")

            # 解析 EPUB
            book = epub.read_epub(file_path)

            # 提取元数据
            metadata = self._extract_metadata(book)

            # 提取章节
            chapters = self._extract_chapters(book)

            # 计算基本信息
            total_chars = sum(len(ch.get("content", "")) for ch in chapters)
            total_words = sum(len(ch.get("content", "").replace("\n", "")) for ch in chapters)

            self.logger.info(
                f"EPUB 解析完成: {metadata.get('title')}, "
                f"章节数: {len(chapters)}, "
                f"总字符: {total_chars}"
            )

            return {
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "language": metadata.get("language"),
                "description": metadata.get("description"),
                "publisher": metadata.get("publisher"),
                "isbn": metadata.get("isbn"),
                "publish_date": metadata.get("publish_date"),
                "cover_image": metadata.get("cover_image"),
                "cover_image_type": metadata.get("cover_image_type"),
                "chapters": chapters,
                "chapter_count": len(chapters),
                "total_characters": total_chars,
                "total_words": total_words,
                "file_path": file_path,
            }

        except EPUBParseError:
            raise
        except Exception as e:
            self.logger.error(f"EPUB 解析失败: {file_path} - {e}")
            raise EPUBParseError(f"EPUB 解析失败: {e}")

    def parse_bytes(self, data: bytes, book_id: int = None) -> Dict[str, Any]:
        """
        从字节数据解析 EPUB

        Args:
            data: EPUB 文件字节数据
            book_id: 关联的书籍 ID

        Returns:
            dict: 解析结果
        """
        try:
            # 校验格式
            if not self._validate_epub_bytes(data):
                raise EPUBParseError("无效的 EPUB 文件格式")

            # 检测 DRM
            if self._is_drm_protected_bytes(data):
                raise EPUBParseError("EPUB 文件受 DRM 保护，无法解析")

            book = epub.read_epub(BytesIO(data))

            # 提取元数据
            metadata = self._extract_metadata(book)

            # 提取章节
            chapters = self._extract_chapters(book)

            # 计算基本信息
            total_chars = sum(len(ch.get("content", "")) for ch in chapters)
            total_words = sum(len(ch.get("content", "").replace("\n", "")) for ch in chapters)

            return {
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "language": metadata.get("language"),
                "description": metadata.get("description"),
                "publisher": metadata.get("publisher"),
                "isbn": metadata.get("isbn"),
                "publish_date": metadata.get("publish_date"),
                "cover_image": metadata.get("cover_image"),
                "cover_image_type": metadata.get("cover_image_type"),
                "chapters": chapters,
                "chapter_count": len(chapters),
                "total_characters": total_chars,
                "total_words": total_words,
            }

        except EPUBParseError:
            raise
        except Exception as e:
            self.logger.error(f"EPUB 解析失败 - {e}")
            raise EPUBParseError(f"EPUB 解析失败: {e}")

    def _validate_epub_format(self, file_path: str) -> bool:
        """
        验证 EPUB 文件格式

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否是有效的 EPUB 文件
        """
        try:
            # 必须是 zip 文件
            if not zipfile.is_zipfile(file_path):
                return False

            # 必须包含 mimetype 文件
            with zipfile.ZipFile(file_path, 'r') as zf:
                if "mimetype" not in zf.namelist():
                    return False

                # mimetype 内容必须是 application/epub+zip
                mimetype = zf.read("mimetype").decode("utf-8").strip()
                if mimetype != "application/epub+zip":
                    return False

            return True

        except Exception as e:
            self.logger.warning(f"EPUB 格式校验失败: {e}")
            return False

    def _validate_epub_bytes(self, data: bytes) -> bool:
        """
        验证 EPUB 字节数据格式

        Args:
            data: EPUB 文件字节数据

        Returns:
            bool: 是否是有效的 EPUB 文件
        """
        try:
            if not zipfile.is_zipfile(BytesIO(data)):
                return False

            with zipfile.ZipFile(BytesIO(data), 'r') as zf:
                if "mimetype" not in zf.namelist():
                    return False

                mimetype = zf.read("mimetype").decode("utf-8").strip()
                if mimetype != "application/epub+zip":
                    return False

            return True

        except Exception as e:
            self.logger.warning(f"EPUB 格式校验失败: {e}")
            return False

    def _is_drm_protected(self, file_path: str) -> bool:
        """
        检测 EPUB 是否受 DRM 保护

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否受保护
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                filenames = zf.namelist()

                # 检查是否包含 DRM 相关文件
                for filename in filenames:
                    filename_lower = filename.lower()
                    for pattern in self.DRM_PATTERNS:
                        if pattern in filename_lower:
                            self.logger.warning(f"检测到 DRM 相关文件: {filename}")
                            return True

            return False

        except Exception as e:
            self.logger.warning(f"DRM 检测失败: {e}")
            return False

    def _is_drm_protected_bytes(self, data: bytes) -> bool:
        """
        检测 EPUB 字节数据是否受 DRM 保护

        Args:
            data: EPUB 文件字节数据

        Returns:
            bool: 是否受保护
        """
        try:
            with zipfile.ZipFile(BytesIO(data), 'r') as zf:
                filenames = zf.namelist()

                for filename in filenames:
                    filename_lower = filename.lower()
                    for pattern in self.DRM_PATTERNS:
                        if pattern in filename_lower:
                            self.logger.warning(f"检测到 DRM 相关文件: {filename}")
                            return True

            return False

        except Exception as e:
            self.logger.warning(f"DRM 检测失败: {e}")
            return False

    def _extract_metadata(self, book: epub.EpubBook) -> Dict[str, Any]:
        """
        提取元数据

        Args:
            book: EpubBook 对象

        Returns:
            dict: 元数据字典
        """
        metadata = {}

        # 提取标题
        titles = book.get_metadata("DC", "title")
        if titles:
            metadata["title"] = titles[0][0] if titles[0] else "未命名"

        # 提取作者
        creators = book.get_metadata("DC", "creator")
        if creators:
            metadata["author"] = creators[0][0] if creators[0] else None

        # 提取语言
        languages = book.get_metadata("DC", "language")
        if languages:
            metadata["language"] = languages[0][0] if languages[0] else "zh-CN"

        # 提取出版社
        publishers = book.get_metadata("DC", "publisher")
        if publishers:
            metadata["publisher"] = publishers[0][0] if publishers[0] else None

        # 提取描述
        descriptions = book.get_metadata("DC", "description")
        if descriptions:
            metadata["description"] = descriptions[0][0] if descriptions[0] else None

        # 提取 ISBN
        identifiers = book.get_metadata("DC", "identifier")
        for identifier in identifiers:
            if identifier[0]:
                id_value = identifier[0]
                id_attrs = identifier[1] if len(identifier) > 1 else {}
                # 检查是否包含 ISBN
                if "isbn" in id_value.lower():
                    metadata["isbn"] = id_value
                    break
                # 检查 opf:scheme
                if isinstance(id_attrs, dict) and id_attrs.get("opf:scheme", "").upper() == "ISBN":
                    metadata["isbn"] = id_value
                    break
        metadata.setdefault("isbn", None)

        # 提取发布日期
        dates = book.get_metadata("DC", "date")
        if dates:
            metadata["publish_date"] = dates[0][0] if dates[0] else None
        else:
            metadata["publish_date"] = None

        # 提取封面
        cover_result = self._extract_cover(book)
        metadata["cover_image"] = cover_result.get("image_data")
        metadata["cover_image_type"] = cover_result.get("image_type")

        return metadata

    def _extract_cover(self, book: epub.EpubBook) -> Dict[str, Any]:
        """
        提取封面图片

        Args:
            book: EpubBook 对象

        Returns:
            dict: 包含 image_data 和 image_type 的字典
        """
        result = {"image_data": None, "image_type": None}

        # 方法1：通过 manifest 中的 properties="cover-image" 查找
        for item in book.get_items():
            if item.get_type() == ITEM_IMAGE:
                item_props = item.properties if hasattr(item, 'properties') else []
                if 'cover-image' in item_props:
                    content = item.get_content()
                    result["image_data"] = content
                    result["image_type"] = self._get_image_type(content, item.get_name())
                    return result

        # 方法2：通过文件名包含 cover 查找
        for item in book.get_items():
            if item.get_type() == ITEM_IMAGE:
                name = item.get_name().lower()
                if "cover" in name:
                    content = item.get_content()
                    result["image_data"] = content
                    result["image_type"] = self._get_image_type(content, item.get_name())
                    return result

        # 方法3：查找 metadata 中的 cover 定义
        try:
            cover_meta = book.get_metadata("meta", "cover")
            if cover_meta:
                cover_id = cover_meta[0][0] if cover_meta and cover_meta[0] else None
                if cover_id:
                    cover_item = book.get_item_with_id(cover_id)
                    if cover_item:
                        content = cover_item.get_content()
                        result["image_data"] = content
                        result["image_type"] = self._get_image_type(content, cover_item.get_name())
                        return result
        except (KeyError, Exception):
            pass

        # 方法4：查找第一个图片（通常是封面）
        for item in book.get_items():
            if item.get_type() == ITEM_IMAGE:
                content = item.get_content()
                result["image_data"] = content
                result["image_type"] = self._get_image_type(content, item.get_name())
                return result

        return result

    def _get_image_type(self, data: bytes, filename: str) -> Optional[str]:
        """
        根据文件内容或文件名判断图片类型

        Args:
            data: 图片数据
            filename: 文件名

        Returns:
            str: 图片类型 (image/jpeg, image/png, image/webp)
        """
        # 从文件名判断
        if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
            return "image/jpeg"
        elif filename.lower().endswith(".png"):
            return "image/png"
        elif filename.lower().endswith(".webp"):
            return "image/webp"
        elif filename.lower().endswith(".gif"):
            return "image/gif"

        # 从文件头判断
        if data[:2] == b'\xff\xd8':
            return "image/jpeg"
        elif data[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return "image/webp"

        return "image/jpeg"  # 默认假设为 JPEG

    def _extract_chapters(self, book: epub.EpubBook) -> List[Dict[str, Any]]:
        """
        提取章节内容

        Args:
            book: EpubBook 对象

        Returns:
            list: 章节列表
        """
        chapters = []

        # 获取所有文档项
        docs = [
            item for item in book.get_items()
            if item.get_type() == ITEM_DOCUMENT
        ]

        for index, doc in enumerate(docs):
            try:
                content = doc.get_content()
                # 优先使用 xml 解析器（适合 XHTML），如果失败则使用 lxml
                try:
                    soup = BeautifulSoup(content, "xml")
                    # 检查是否解析成功
                    if soup.find() is None:
                        raise ValueError("XML parser returned empty result")
                except Exception:
                    soup = BeautifulSoup(content, "lxml")

                # 提取文本
                text = soup.get_text(separator="\n", strip=True)

                # 提取标题
                title = self._extract_chapter_title(soup, index)

                if text.strip():
                    chapters.append({
                        "index": index,
                        "title": title,
                        "content": text,
                        "html": content,
                    })

            except Exception as e:
                self.logger.warning(f"解析章节失败: index={index} - {e}")
                continue

        return chapters

    def _extract_chapter_title(self, soup: BeautifulSoup, index: int) -> str:
        """
        提取章节标题

        Args:
            soup: BeautifulSoup 对象
            index: 章节索引

        Returns:
            str: 章节标题
        """
        # 尝试从 h1-h6 标签提取
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            title_tag = soup.find(tag)
            if title_tag and title_tag.get_text(strip=True):
                return title_tag.get_text(strip=True)

        # 默认标题
        return f"第 {index + 1} 章"

    def clean_html(self, html_content: str) -> str:
        """
        清洗 HTML 内容，提取纯文本

        Args:
            html_content: HTML 内容

        Returns:
            str: 纯文本
        """
        soup = BeautifulSoup(html_content, "lxml")

        # 移除脚本和样式
        for tag in soup(["script", "style"]):
            tag.decompose()

        # 获取文本
        text = soup.get_text(separator="\n", strip=True)

        # 规范化空白字符
        import re
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text
