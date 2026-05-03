# ===========================================
# 章节正文清洗器
# ===========================================

"""
章节正文清洗器

从 EPUB 提取的章节原始 HTML/文本中，只保留有声小说需要的有声内容（正文），
丢弃不需要的非正文内容。

清理规则：
1. 移除 HTML 标签（保留换行结构）
2. 移除卷/章/节的标题前缀（如"第X章"已在数据库存储，不重复朗读）
3. 移除脚注、尾注
4. 移除页眉页脚（如页码、网站URL、广告）
5. 移除作者废话、前言后记中的非叙事内容
6. 移除版权声明、ISBN、出版信息等
7. 标准化空白字符
8. 移除连续空行（最多保留1个空行）
9. 检测并移除乱码段落
10. 保留对话、描写、叙述等正文内容

输出：纯文本正文，可直接送入 DeepSeek 分析或 TTS 合成。
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field


logger = logging.getLogger("audiobook.cleaner")


@dataclass
class CleanResult:
    """清洗结果"""
    original_length: int = 0
    cleaned_length: int = 0
    removed_chars: int = 0
    removed_lines: List[str] = field(default_factory=list)
    warning_count: int = 0
    quality_score: float = 1.0   # 0.0~1.0，1.0 表示完美


class ChapterTextCleaner:
    """
    章节正文清洗器

    从章节原始内容中提取正文，丢弃非有声内容。
    """

    # ── 需要移除的行模式 ──
    REMOVE_LINE_PATTERNS = [
        # 页码
        r'^\s*\d{1,4}\s*$',
        # 纯数字行（可能是页码/行号）
        r'^\s*\d+\s*$',
        # 版权声明
        r'版权所有|版权归|Copyright|©|All Rights Reserved',
        # ISBN
        r'ISBN[:\s]*[\d\-Xx]+',
        # 网站地址
        r'https?://\S+|www\.\S+|更多好书|请访问|欢迎访问|扫一扫|二维码',
        # 出版信息
        r'出版[社号]|印刷[厂次]|版[本次]|印[张次]|开本|字数|定价',
        # 图书在版编目（CIP）
        r'图书在版编目.*数据|CIP.*核字.*号',
        # 中国版本图书馆
        r'中国版本图书馆.*数据',
        # 广告/推广
        r'关注.*公众号|加.*微信|QQ群|读者群|书友群|求.*收藏|求.*推荐|求.*月票',
        # 作者备注（非叙事）
        r'^[\(（【\[]?作者[话按注说].*[\)）】\]]?$',
        r'^[\(（【\[]?[Pp][Ss][：:].*',  # PS: ... 作者附言
        r'^题外话[：:]',
        # 纯符号行
        r'^[=＝\-－—\-_\*#~～\.。…·]{3,}$',
        # "未完待续"类
        r'未完待续|待续|本章完|本章结束',
        # 阅读提示/网站提示
        r'请记住.*域名|手机.*阅读|电脑.*阅读|推荐阅读|热门.*推荐',
        r'如果喜欢|喜欢.*请|觉得.*不错',
        # ── 以下为 EPUB 解析残留物 ──
        # HTML 标签残留（文件位置锚点等）
        r'^\s*id\s*=\s*["\']?(?:filepos|p\d|anchor)[\w]+["\']?\s*/?\s*>\s*$',
        r'^\s*id\s*=\s*["\']?[\w]+["\']?\s*/?\s*>\s*$',
        # 编目/出版信息行
        r'Ⅰ．|Ⅱ．|Ⅲ．|Ⅳ．|Ⅴ．',  # 罗马数字编号（常出现在 CIP 数据中）
        r'[（(]套装全\d册[)）]',   # 套装全X册
        r'^\s*◆.*◆\s*$',         # ◆ 装饰符号
        # 空白/空标签行
        r'^\s*<[^>]+>\s*$',
        # 返回目录/返回总目录
        r'返回.*目录',
        # 定价行
        r'定\s*价[：:]\s*[¥￥]?\d+\.?\d*元?',
    ]

    # ── 需要移除的 HTML 标签（内容也移除） ──
    REMOVE_TAGS = [
        'script', 'style', 'meta', 'link', 'noscript',
        'iframe', 'object', 'embed', 'applet',
    ]

    # ── 脚注/尾注标记 ──
    FOOTNOTE_PATTERNS = [
        r'\[\d+\]',           # [1] 脚注引用
        r'〔\d+〕',            # 〔1〕
        r'注\d+[：:]',         # 注1：
        r'①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩',  # 圈号脚注
    ]

    # ── 乱码检测模式 ──
    GARBLED_PATTERNS = [
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]',  # 控制字符
        r'�+',                               # Unicode 替换字符
        r'[\uFFFD]+',                        # 同上
        r'(?:[ΐΰ]|[\u0370-\u03FF]{10,})',    # 连续希腊字母（可能是乱码）
    ]

    # ── 章节标题模式（需要移除，因为标题已在数据库） ──
    CHAPTER_TITLE_PATTERNS = [
        r'^第[零一二三四五六七八九十百千万\d]+[章节卷部集篇回]',
        r'^[Cc]hapter\s+\d+',
        r'^[Vv]ol(?:ume)?\.?\s*\d+',
        r'^[Pp]art\s+\d+',
        r'^[Ss]ection\s+\d+',
    ]

    def __init__(self):
        self.remove_patterns = [re.compile(p, re.IGNORECASE) for p in self.REMOVE_LINE_PATTERNS]
        self.footnote_patterns = [re.compile(p) for p in self.FOOTNOTE_PATTERNS]
        self.garbled_patterns = [re.compile(p) for p in self.GARBLED_PATTERNS]

    def clean(self, text: str, title: str = None) -> str:
        """
        清洗章节文本，只保留正文

        Args:
            text: 原始章节文本（可能含 HTML）
            title: 章节标题（用于标题行匹配）

        Returns:
            str: 清洗后的纯正文
        """
        if not text:
            return ""

        # 1. 移除 HTML 标签，保留文本
        text = self._strip_html(text)

        # 2. 移除脚注/尾注
        text = self._remove_footnotes(text)

        # 3. 逐行过滤
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append('')
                continue

            # 检查是否需要移除
            if self._should_remove_line(stripped, title):
                continue

            # 检查乱码
            if self._is_garbled(stripped):
                logger.debug(f"乱码行已跳过: {stripped[:50]}...")
                continue

            cleaned_lines.append(stripped)

        # 4. 合并连续空行（最多保留1个空行作为段落分隔）
        result = self._normalize_blank_lines(cleaned_lines)

        return result

    def clean_with_report(self, text: str, title: str = None) -> tuple:
        """
        清洗文本并返回报告

        Args:
            text: 原始文本
            title: 章节标题

        Returns:
            tuple: (清洗后文本, CleanResult)
        """
        report = CleanResult()
        report.original_length = len(text) if text else 0

        cleaned = self.clean(text, title)

        report.cleaned_length = len(cleaned)
        report.removed_chars = report.original_length - report.cleaned_length

        # 计算质量分数
        if report.original_length > 0:
            retention = report.cleaned_length / report.original_length
            # 保留率在 30%-98% 之间认为是正常的
            if retention < 0.1:
                report.quality_score = 0.1
                report.warning_count += 1
                logger.warning(f"文本保留率过低: {retention:.1%}")
            elif retention > 0.99:
                report.quality_score = 0.95
            else:
                report.quality_score = min(1.0, retention * 1.1)

        return cleaned, report

    def _strip_html(self, text: str) -> str:
        """移除 HTML 标签，保留文本内容和换行结构"""
        # 移除不需要的标签（含内容）
        for tag in self.REMOVE_TAGS:
            text = re.sub(
                rf'<{tag}[^>]*>.*?</{tag}>',
                '',
                text,
                flags=re.DOTALL | re.IGNORECASE,
            )

        # 将块级标签替换为换行
        block_tags = ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr']
        for tag in block_tags:
            text = re.sub(rf'</?{tag}[^>]*>', '\n', text, flags=re.IGNORECASE)

        # 移除单个自闭合标签及属性锚点（如 id="filepos0000031476"/>）
        # 这是 EPUB 锚点拆分的常见残留
        text = re.sub(
            r'\s*id\s*=\s*["\']?(?:filepos|p\d+|anchor)[^"\'>\s]*["\']?\s*/?\s*>\s*',
            '',
            text,
        )
        # 移除遗漏的残留自闭合标签
        text = re.sub(r'\s*/?\s*>\s*$', '', text, flags=re.MULTILINE)

        # 移除残留的 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)

        # 解码 HTML 实体
        import html
        text = html.unescape(text)

        return text

    def _remove_footnotes(self, text: str) -> str:
        """移除脚注/尾注标记"""
        for pattern in self.footnote_patterns:
            text = pattern.sub('', text)
        return text

    def _should_remove_line(self, line: str, title: str = None) -> bool:
        """
        判断该行是否应该被移除

        Args:
            line: 单行文本
            title: 章节标题

        Returns:
            bool: True 表示应移除
        """
        # 检查章节标题模式
        if self._is_chapter_title_line(line, title):
            return True

        # 检查移除模式
        for pattern in self.remove_patterns:
            if pattern.search(line):
                return True

        # 内容过短且无意义（但保留对话短句如"嗯""好"）
        if len(line) <= 1 and not line in {'嗯', '啊', '哦', '好', '行', '对', '不', '是', '我', '你', '他', '她', '它'}:
            return True

        return False

    def _is_chapter_title_line(self, line: str, title: str = None) -> bool:
        """判断是否是章节标题行"""
        # 精确匹配已知标题
        if title and line.strip() == title.strip():
            return True

        # 模式匹配
        for pattern in self.CHAPTER_TITLE_PATTERNS:
            if re.match(pattern, line.strip()):
                return True

        return False

    def _is_garbled(self, text: str) -> bool:
        """检测乱码"""
        # 如果乱码字符超过 30% 则认为是乱码
        garbled_count = 0
        for pattern in self.garbled_patterns:
            garbled_count += len(pattern.findall(text))

        if len(text) > 0 and garbled_count / len(text) > 0.3:
            return True

        # 检查是否包含过多非中文字符（可能是编码错误）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if len(text) > 50 and chinese_chars / len(text) < 0.1:
            return True

        return False

    def _normalize_blank_lines(self, lines: List[str]) -> str:
        """规范化空行（连续空行合并为一个）"""
        result = []
        prev_blank = False

        for line in lines:
            is_blank = len(line.strip()) == 0
            if is_blank:
                if not prev_blank:
                    result.append('')
                prev_blank = True
            else:
                result.append(line)
                prev_blank = False

        # 去掉首尾空行
        while result and not result[0].strip():
            result.pop(0)
        while result and not result[-1].strip():
            result.pop()

        return '\n'.join(result)


# 全局实例
_chapter_cleaner = ChapterTextCleaner()


def clean_chapter_text(text: str, title: str = None) -> str:
    """
    便捷函数：清洗章节文本

    Args:
        text: 原始文本
        title: 章节标题

    Returns:
        str: 清洗后的纯正文
    """
    return _chapter_cleaner.clean(text, title)


def clean_chapter_with_report(text: str, title: str = None) -> tuple:
    """
    便捷函数：清洗章节文本并返回报告

    Args:
        text: 原始文本
        title: 章节标题

    Returns:
        tuple: (清洗后文本, CleanResult)
    """
    return _chapter_cleaner.clean_with_report(text, title)
