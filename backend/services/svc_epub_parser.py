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
        按照 EPUB 目录（TOC）提取章节内容

        优先使用 EPUB 的 NCX/NAV 目录结构分割章节，
        而非简单按 HTML 文件拆分。
        一个 HTML 文件可能包含多个章节，目录中的每一项
        都对应一个独立的章节。

        Args:
            book: EpubBook 对象

        Returns:
            list: 按目录排序的章节列表
        """
        # ── 第一步：读取目录结构 ──
        toc_items = self._flatten_toc(book.toc)

        if toc_items:
            # 有目录：按目录拆分
            self.logger.info(f"使用 EPUB 目录拆分章节，共 {len(toc_items)} 项")
            return self._extract_by_toc(book, toc_items)
        else:
            # 无目录：回退到按 HTML 文件拆分
            self.logger.warning("EPUB 没有目录，回退到按文件拆分")
            return self._extract_by_documents(book)

    def _flatten_toc(self, toc: list, depth: int = 0) -> List[Dict[str, Any]]:
        """
        递归展开 EPUB 目录（TOC）为扁平列表

        支持两种 TOC 格式：
        1. 嵌套 (Link, [children]) 元组
        2. 直接 Link 对象

        Args:
            toc: ebooklib 的 TOC 列表
            depth: 当前深度

        Returns:
            list: 扁平化的目录项
        """
        items = []
        order = 0

        for entry in toc:
            order += 1

            # 格式1: (Link, [children]) 元组
            if isinstance(entry, tuple) and len(entry) >= 2:
                link = entry[0]
                children = entry[1]

                if hasattr(link, 'title') and hasattr(link, 'href'):
                    items.append({
                        "title": link.title or f"第{order}章",
                        "href": link.href or "",
                        "depth": depth,
                        "play_order": order,
                    })

                if children:
                    items.extend(self._flatten_toc(children, depth + 1))

            # 格式2: 直接 Link 对象
            elif hasattr(entry, 'title') and hasattr(entry, 'href'):
                items.append({
                    "title": entry.title or f"第{order}章",
                    "href": entry.href or "",
                    "depth": depth,
                    "play_order": order,
                })

        return items

    def _extract_by_toc(
        self, book: epub.EpubBook, toc_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        按照目录结构提取章节

        使用 BeautifulSoup 元素定位按锚点提取内容，
        避免 HTML 残留（如 id="filepos..."）。

        Args:
            book: EpubBook 对象
            toc_items: 扁平化的目录项

        Returns:
            list: 章节列表
        """
        from urllib.parse import unquote, urlparse

        # ── 构建文档索引：文件名 → BeautifulSoup ──
        doc_index = {}
        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                file_name = item.get_name()
                try:
                    content = item.get_content()
                    try:
                        soup = BeautifulSoup(content, "xml")
                        if soup.find() is None:
                            soup = BeautifulSoup(content, "lxml")
                    except Exception:
                        soup = BeautifulSoup(content, "lxml")
                    doc_index[file_name] = soup
                except Exception as e:
                    self.logger.warning(f"解析文档失败: {file_name} - {e}")

        # ── 分组：按文件名将 TOC 项分组 ──
        file_groups = {}  # {file_base: [(index, toc_entry), ...]}
        for i, entry in enumerate(toc_items):
            parsed = urlparse(entry["href"])
            file_part = unquote(parsed.path)
            file_base = file_part.split("/")[-1] if "/" in file_part else file_part

            matched = file_base
            if matched not in doc_index:
                for key in doc_index:
                    if key.endswith(matched) or matched in key:
                        matched = key
                        break

            if matched not in file_groups:
                file_groups[matched] = []
            file_groups[matched].append((i, entry, parsed.fragment))

        # ── 提取章节内容（BeautifulSoup 元素定位，拒绝 HTML 字符串操作） ──
        chapters = []
        seen_titles = set()

        for file_name, entries in file_groups.items():
            soup = doc_index.get(file_name)
            if not soup:
                continue

            # 按原始顺序排序
            entries.sort(key=lambda x: x[0])

            for idx_in_group, (orig_idx, entry, fragment) in enumerate(entries):
                title = entry["title"]
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                if fragment:
                    # 用 BeautifulSoup 定位锚点元素
                    anchor_el = soup.find(id=fragment)
                    if anchor_el is None:
                        # 有些 EPUB 用 name 属性代替 id
                        anchor_el = soup.find(attrs={"name": fragment})

                    if anchor_el:
                        text_parts = []

                        # 收集当前锚点之后、下一个锚点之前的所有兄弟元素
                        # 处理 next_siblings 时跳过空白/空节点
                        for sibling in anchor_el.next_siblings:
                            # 检查是否到达下一个锚点
                            if hasattr(sibling, 'attrs'):
                                skip = False
                                for next_entry in entries[idx_in_group + 1:]:
                                    next_frag = next_entry[2]
                                    if next_frag:
                                        sid = sibling.attrs.get("id", "")
                                        sname = sibling.attrs.get("name", "") if hasattr(sibling, 'attrs') else ""
                                        if sid == next_frag or sname == next_frag:
                                            skip = True
                                            break
                                if skip:
                                    break

                            # 提取文本
                            if hasattr(sibling, 'get_text'):
                                t = sibling.get_text(strip=True)
                                if t:
                                    text_parts.append(t)
                            elif isinstance(sibling, str):
                                t = sibling.strip()
                                if t:
                                    text_parts.append(t)

                        text = "\n".join(text_parts)

                        # 如果锚点本身有文本（如 <a>文本</a>），也提取
                        anchor_text = anchor_el.get_text(strip=True)
                        if anchor_text:
                            text_parts.insert(0, anchor_text)
                            text = "\n".join(text_parts)
                    else:
                        # 找不到锚点元素，降级：提取整个文档文本
                        text = soup.get_text(separator="\n", strip=True)
                        self.logger.warning(
                            f"找不到锚点元素: id={fragment}，使用全文"
                        )
                else:
                    # 无 fragment：整个文档
                    text = soup.get_text(separator="\n", strip=True)

                # 跳过非正文条目
                if self._is_non_body_entry(title):
                    self.logger.debug(f"跳过非正文条目: {title}")
                    continue

                if text.strip():
                    chapters.append({
                        "index": len(chapters),
                        "title": title,
                        "content": text,
                    })

        # 回退检查
        if len(chapters) < 2 and len(doc_index) >= 2:
            self.logger.warning(
                f"目录拆分仅得到 {len(chapters)} 章，回退到按文件拆分"
            )
            return self._extract_by_documents(book)

        return chapters

    def _is_non_body_entry(self, title: str) -> bool:
        """
        判断目录项是否为非正文（目录页、前言说明等）

        Args:
            title: 目录项标题

        Returns:
            bool: True 表示应跳过
        """
        skip_patterns = ["目录", "版权", "出版信息"]
        for p in skip_patterns:
            if p in (title or ""):
                return True
        return False

    def _extract_content_by_href(
        self, doc_index: Dict[str, BeautifulSoup], href: str
    ) -> str:
        """
        根据 href 从文档索引中提取内容

        兼容 fragment (#) 定位，支持以下格式：
        - "chapter1.xhtml"           → 整个文件
        - "chapter1.xhtml#section1"  → 文件中的某个元素
        - "../Text/chapter1.xhtml"   → 带相对路径

        Args:
            doc_index: 文件名 → BeautifulSoup 的映射
            href: 目标链接

        Returns:
            str: 提取的文本内容
        """
        # 去除 URL 编码和 fragment
        from urllib.parse import unquote, urlparse

        parsed = urlparse(href)
        file_part = unquote(parsed.path)
        fragment = parsed.fragment

        # 提取文件名（去掉路径前缀）
        file_name = file_part.split("/")[-1] if "/" in file_part else file_part

        # 查找匹配的文档
        soup = None
        if file_name in doc_index:
            soup = doc_index[file_name]
        else:
            # 模糊匹配（部分文件名匹配）
            for key in doc_index:
                if key.endswith(file_name) or file_name in key:
                    soup = doc_index[key]
                    break

        if soup is None:
            self.logger.warning(f"找不到文档: {file_name}")
            return ""

        # 如果有 fragment，定位到具体元素
        if fragment:
            element = soup.find(id=fragment) or soup.find(attrs={"name": fragment})
            if element:
                return element.get_text(separator="\n", strip=True)

        # 返回整个文档内容
        return soup.get_text(separator="\n", strip=True)

    def _extract_by_documents(self, book: epub.EpubBook) -> List[Dict[str, Any]]:
        """
        回退方案：按 HTML 文件逐一拆分章节

        Args:
            book: EpubBook 对象

        Returns:
            list: 章节列表
        """
        chapters = []
        docs = [
            item for item in book.get_items()
            if item.get_type() == ITEM_DOCUMENT
        ]

        for index, doc in enumerate(docs):
            try:
                content = doc.get_content()
                try:
                    soup = BeautifulSoup(content, "xml")
                    if soup.find() is None:
                        raise ValueError("XML parser returned empty result")
                except Exception:
                    soup = BeautifulSoup(content, "lxml")

                text = soup.get_text(separator="\n", strip=True)
                title = self._extract_chapter_title(soup, index)

                if text.strip():
                    chapters.append({
                        "index": index,
                        "title": title,
                        "content": text,
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
