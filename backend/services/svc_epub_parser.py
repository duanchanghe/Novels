# ===========================================
# EPUB 解析服务
# ===========================================

"""
EPUB 解析服务

解析 EPUB 文件，提取元数据和章节内容。
"""

import logging
import os
from typing import Dict, List, Any, Optional
from io import BytesIO

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from core.exceptions import EPUBParseError


logger = logging.getLogger("audiobook")


class EPUBParserService:
    """
    EPUB 解析服务

    提供 EPUB 文件的解析功能：
    - 元数据提取
    - 章节内容提取
    - 封面图片提取
    - DRM 检测
    """

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

            self.logger.info(
                f"EPUB 解析完成: {metadata.get('title')}, "
                f"章节数: {len(chapters)}"
            )

            return {
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "language": metadata.get("language"),
                "description": metadata.get("description"),
                "publisher": metadata.get("publisher"),
                "cover_image": metadata.get("cover_image"),
                "chapters": chapters,
                "chapter_count": len(chapters),
            }

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
            book = epub.read_epub(BytesIO(data))

            # 检测 DRM
            # 注意：ebooklib 可能无法检测所有 DRM

            # 提取元数据
            metadata = self._extract_metadata(book)

            # 提取章节
            chapters = self._extract_chapters(book)

            return {
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "language": metadata.get("language"),
                "description": metadata.get("description"),
                "publisher": metadata.get("publisher"),
                "cover_image": metadata.get("cover_image"),
                "chapters": chapters,
                "chapter_count": len(chapters),
            }

        except Exception as e:
            self.logger.error(f"EPUB 解析失败 - {e}")
            raise EPUBParseError(f"EPUB 解析失败: {e}")

    def _is_drm_protected(self, file_path: str) -> bool:
        """
        检测 EPUB 是否受 DRM 保护

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否受保护
        """
        # ebooklib 无法检测 DRM，这里作为预留接口
        # 实际项目中可以使用 adept 等工具检测
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

        # 提取封面
        metadata["cover_image"] = self._extract_cover(book)

        return metadata

    def _extract_cover(self, book: epub.EpubBook) -> Optional[bytes]:
        """
        提取封面图片

        Args:
            book: EpubBook 对象

        Returns:
            bytes: 封面图片数据
        """
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_TYPE_IMAGE:
                if "cover" in item.get_name().lower():
                    return item.get_content()

        return None

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
            if item.get_type() == ebooklib.ITEM_TYPE_DOCUMENT
        ]

        for index, doc in enumerate(docs):
            try:
                content = doc.get_content()
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
