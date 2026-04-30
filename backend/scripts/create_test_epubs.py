#!/usr/bin/env python3
"""
创建测试用 EPUB 文件
用于本地测试 EPUB 解析功能
"""

import zipfile
import os
from io import BytesIO


def create_novel_epub(filename: str, title: str, author: str, chapters: list) -> bytes:
    """
    创建一本测试用 EPUB 文件

    Args:
        filename: 保存的文件名
        title: 书名
        author: 作者
        chapters: 章节列表，每个元素为 (标题, 内容) 元组
    """
    buffer = BytesIO()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. mimetype（必须是非压缩的）
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # 2. META-INF/container.xml
        container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
        zf.writestr("META-INF/container.xml", container_xml.encode('utf-8'))

        # 3. OEBPS/content.opf
        manifest_items = []
        spine_items = []
        chapter_files = []

        for i, (chapter_title, _) in enumerate(chapters):
            item_id = f"chapter{i+1}"
            href = f"chapter{i+1}.xhtml"
            manifest_items.append(f'    <item id="{item_id}" href="{href}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'    <itemref idref="{item_id}"/>')
            chapter_files.append((href, chapter_title))

        manifest_str = "\n".join(manifest_items)
        spine_str = "\n".join(spine_items)

        content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>zh-CN</dc:language>
    <dc:identifier id="bookid">urn:uuid:test-{filename}</dc:identifier>
    <dc:description>测试书籍 - {title}</dc:description>
  </metadata>
  <manifest>
{manifest_str}
  </manifest>
  <spine>
{spine_str}
  </spine>
</package>'''
        zf.writestr("OEBPS/content.opf", content_opf.encode('utf-8'))

        # 4. 章节内容
        for href, chapter_title in chapter_files:
            idx = chapters[chapter_files.index((href.split('.')[0].replace('chapter', ''), chapter_title))][1] if False else None
            chapter_idx = int(href.split('.')[0].replace('chapter', ''))
            _, content = chapters[chapter_idx - 1]

            # 构建段落
            paragraphs = content.split('\n\n')
            p_tags = '\n    '.join([f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()])

            chapter_xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{chapter_title}</title>
  <style>
    body {{ font-family: "Noto Serif SC", serif; margin: 1em; }}
    h1 {{ text-align: center; margin: 2em 0; }}
    p {{ text-indent: 2em; line-height: 1.8; }}
  </style>
</head>
<body>
  <h1>{chapter_title}</h1>
{p_tags}
</body>
</html>'''
            zf.writestr(f"OEBPS/{href}", chapter_xhtml.encode('utf-8'))

    return buffer.getvalue()


def create_chinese_novel() -> bytes:
    """创建中文小说测试 EPUB"""
    title = "测试小说：AI有声书工坊"
    author = "测试作者"

    chapters = [
        ("第一章 新的开始", """李明站在公司门口，深吸了一口气。

"终于到了。"他喃喃自语。

今天是他入职的第一天。作为一名 AI 工程师，他对这家专注于人工智能的公司充满期待。

走进大厅，一位年轻的女接待员微笑着迎了上来。

"您好，请问有什么可以帮助您的？"她问道。

"我是李明，今天来报到的新员工。"李明回答。

"请稍等，我帮您联系HR。"接待员拿起电话，轻轻按了几个号码。

李明环顾四周，发现大厅的装修非常现代。墙上挂着各种科技公司的logo，角落里摆放着几株绿植，给严肃的办公环境增添了一丝生机。"""),

        ("第二章 第一次会议", """九点整，李明准时来到了会议室。

推开门，他发现已经有几位同事在座了。一位中年男子坐在主位，看起来像是团队的负责人。

"请坐，你就是李明吧？"中年男子微笑着说，"我是张总，工号001，是这个团队的创始人。"

"张总好！"李明连忙打招呼。

"不用这么客气，"张总摆摆手，"在我们这里，大家都是平等的。我更喜欢大家叫我张哥或者老张。"

会议开始后，张总详细介绍了公司的愿景和目标。

"我们的目标是用 AI 技术改变人们的生活，"他说，"尤其是我们的'AI 有声书工坊'项目，希望能让每个人都能'听'到任何一本书。"

李明认真地听着，心中燃起了热情。"""),

        ("第三章 挑战与机遇", """项目启动后的第三周，李明遇到了第一个重大挑战。

"这个 EPUB 解析模块有问题，"项目经理王姐在会议上说，"它无法正确处理某些特殊格式的文件。"

李明主动请缨："让我来看看这个问题吧。"

接下来的几天里，他深入研究了 EPUB 的规范，阅读了大量的技术文档。

"我发现问题了，"他对团队说，"某些 EPUB 文件使用了非标准的命名约定，导致我们的解析器无法找到内容文件。"

"你能修复它吗？"张总问。

"给我三天时间，"李明自信地说。

三天后，修复版本成功上线，所有的测试用例都通过了。"""),

        ("第四章 团队合作", """一个月的相处，李明渐渐融入了这个团队。

每天中午，大家都会一起去楼下的餐厅吃饭。这天，团队又聚在了一起。

"李明，你之前在哪里工作？"测试工程师小陈好奇地问。

"在一家传统企业做后台开发，"李明回答，"但我一直在关注 AI 领域的发展。"

"那你来对地方了！"前端工程师小刘兴奋地说，"我们这里的 AI 项目可多了。"

"对了，听说你们正在做一个有声书项目？"新来的产品经理小林问道。

"是的，"张总点点头，"我们希望打造一个全自动化的有声书生成系统。用户只需要上传 EPUB，就能得到高质量的有声书。"

"听起来很酷！"小林说，"我也想试试。"

饭后，大家又投入到了紧张的工作中。"""),

        ("第五章 成果展示", """两个月后，"AI 有声书工坊"迎来了第一次内部演示。

"这个系统能够自动解析 EPUB 文件，提取章节结构，"李明介绍道，"然后通过 AI 进行角色识别和情感标注，最后生成自然流畅的有声书。"

演示过程中，一段经典小说被自动转换为语音播放出来。

"太神奇了！"小林惊叹道，"这声音听起来几乎和真人一模一样。"

"目前还在优化阶段，"张总谦虚地说，"但基础功能已经可以使用了。"

演示结束后，公司高层对这个项目给予了高度评价。

"这个项目有很大的市场潜力，"CEO 说，"我们要加快进度，争取早日上线。"

会后，李明和团队成员击掌庆祝。

"这只是开始，"他对自己说，"更大的挑战还在后面。" """),
    ]

    return create_novel_epub("chinese_novel", title, author, chapters)


def create_english_novel() -> bytes:
    """创建英文小说测试 EPUB"""
    title = "The Adventure of the AI Engineer"
    author = "Test Author"

    chapters = [
        ("Chapter 1: A New Beginning", """John stood at the entrance of the tech company, taking a deep breath.

"Here we go," he whispered to himself.

Today was his first day as an AI engineer at this innovative company. He had high hopes for the future.

As he walked into the lobby, a young receptionist greeted him with a smile.

"Good morning! How may I help you?" she asked.

"I'm John Smith, here for my first day," he replied.

"Please have a seat. I'll contact HR right away," she said, picking up the phone."""),

        ("Chapter 2: The First Challenge", """One week into his job, John encountered his first major challenge.

"This text preprocessing module has a bug," the project manager announced during the meeting. "It fails to handle special characters correctly."

John volunteered to investigate the issue.

Over the next few days, he delved deep into the documentation and studied various text processing techniques.

"I found the problem," he told the team. "The module doesn't handle unicode characters properly."

"Can you fix it?" the team lead asked.

"Give me two days," John said confidently.

Two days later, the fix was deployed successfully."""),

        ("Chapter 3: Success and Celebration", """After a month of hard work, John's team finally completed the first phase of the project.

"We did it!" the team celebrated.

The AI audiobook system could now:
- Parse EPUB files automatically
- Extract chapter structures
- Convert text to natural-sounding speech

"This is just the beginning," John thought. "There are many more features to implement and challenges to overcome."

But for now, they deserved to celebrate their success. The future looked bright."""),
    ]

    return create_novel_epub("english_novel", title, author, chapters)


def create_multi_language_epub() -> bytes:
    """创建多语言混合测试 EPUB"""
    title = "多语言混合测试 / Multi-Language Test"
    author = "测试团队"

    chapters = [
        ("测试章节 - Test Chapter", """这是一个多语言混合的测试章节。

This is a multi-language test chapter.

测试混合内容：Hello 你好 World 世界！

数字测试：12345、67.89、100%

英文段落：The quick brown fox jumps over the lazy dog.

中文段落：窗前明月光，疑是地上霜。举头望明月，低头思故乡。

混合对话："你好，" 他说，"How are you today?"

代码示例：print("Hello, World!")

测试完成。Test completed."""),
    ]

    return create_novel_epub("multi_language", title, author, chapters)


def create_empty_metadata_epub() -> bytes:
    """创建元数据缺失的测试 EPUB"""
    chapters = [
        ("第一章", """这是一个元数据不完整的 EPUB 文件。

主要用于测试解析器如何处理缺失的元数据。

测试标题为空的情况。

测试作者为空的情况。"""),
    ]

    # 不添加任何 DRM 标记
    return create_novel_epub("empty_metadata", "", "", chapters)


def create_drm_epub() -> bytes:
    """创建带 DRM 标记的 EPUB（实际无效DRM，用于测试检测）"""
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

        # 添加 DRM 相关文件（虽然是无效的，但用于测试检测功能）
        encryption_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <!-- This is a test DRM marker file -->
</encryption>'''
        zf.writestr("META-INF/encryption.xml", encryption_xml.encode('utf-8'))

        content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>DRM 测试书籍</dc:title>
    <dc:creator>测试作者</dc:creator>
    <dc:language>zh-CN</dc:language>
    <dc:identifier id="bookid">urn:uuid:drm-test</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>'''
        zf.writestr("OEBPS/content.opf", content_opf.encode('utf-8'))

        chapter = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <h1>DRM 测试章节</h1>
  <p>这本书带有 DRM 标记。</p>
</body>
</html>'''
        zf.writestr("OEBPS/chapter1.xhtml", chapter.encode('utf-8'))

    return buffer.getvalue()


def main():
    """生成所有测试 EPUB 文件"""
    output_dir = os.path.join(os.path.dirname(__file__), "..", "test_data", "epub")
    os.makedirs(output_dir, exist_ok=True)

    test_files = [
        ("chinese_novel.epub", create_chinese_novel, "中文小说测试（5章节）"),
        ("english_novel.epub", create_english_novel, "英文小说测试（3章节）"),
        ("multi_language.epub", create_multi_language_epub, "多语言混合测试"),
        ("empty_metadata.epub", create_empty_metadata_epub, "元数据缺失测试"),
        ("drm_marker.epub", create_drm_epub, "DRM标记检测测试"),
    ]

    print("=" * 60)
    print("Generating test EPUB files")
    print("=" * 60)
    print(f"Output directory: {output_dir}\n")

    for filename, creator_func, description in test_files:
        filepath = os.path.join(output_dir, filename)
        epub_data = creator_func()

        with open(filepath, 'wb') as f:
            f.write(epub_data)

        size = len(epub_data)
        print(f"  [OK] {filename}")
        print(f"      Description: {description}")
        print(f"      Size: {size:,} bytes\n")

    print("=" * 60)
    print(f"Generated {len(test_files)} test EPUB files")
    print("=" * 60)

    # 列出所有文件
    print("\nFiles in test_data/epub/:")
    for f in sorted(os.listdir(output_dir)):
        if f.endswith('.epub'):
            path = os.path.join(output_dir, f)
            size = os.path.getsize(path)
            print(f"  - {f} ({size:,} bytes)")


if __name__ == "__main__":
    main()
