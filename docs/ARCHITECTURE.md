# AI 有声书工坊 - 架构重构蓝图

> 文档版本: v2.0.0  
> 创建日期: 2026-05-04  
> 目标: 构建清晰、可维护、可扩展的微内核+插件化架构

---

## 目录

1. [架构概览](#架构概览)
2. [分层设计](#分层设计)
3. [核心领域模型](#核心领域模型)
4. [服务编排](#服务编排)
5. [任务系统](#任务系统)
6. [API 设计](#api-设计)
7. [数据模型](#数据模型)
8. [配置管理](#配置管理)
9. [目录结构](#目录结构)
10. [迁移策略](#迁移策略)

---

## 架构概览

### 设计原则

1. **清晰分层**: 严格的依赖方向，禁止跨层调用
2. **领域驱动**: 按业务域划分模块，而非按技术分层
3. **接口抽象**: 服务间通过抽象接口通信，便于测试和替换
4. **单一职责**: 每个模块专注于单一功能
5. **开闭原则**: 对扩展开放，对修改关闭

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| API 层 | Django + DRF | RESTful API |
| 业务层 | 纯 Python | 领域逻辑 |
| 任务层 | Celery + Redis | 异步任务队列 |
| 数据层 | Django ORM + PostgreSQL | ORM + 关系型数据库 |
| 存储层 | MinIO (S3 兼容) | 对象存储 |
| 缓存层 | Redis | 缓存 + 会话 |
| 前端 | Next.js | 服务端渲染 |

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│                   (Django REST Framework)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      API Layer                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │  Books API  │ │ Chapters API │ │  Audio API  │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │  Voice API  │ │ Publish API │ │  Watch API  │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    Domain Layer (Core)                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     Book Service                             ││
│  │  - create_book()    - get_book()      - list_books()      ││
│  │  - update_book()    - delete_book()    - get_progress()   ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Chapter Service                            ││
│  │  - get_chapter()    - list_chapters() - update_status()   ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Audio Service                             ││
│  │  - get_segments()    - update_segment()                    ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                  Infrastructure Layer                            │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│  │  EPUB Parser  │ │ DeepSeek AI   │ │  MiniMax TTS  │       │
│  └───────────────┘ └───────────────┘ └───────────────┘       │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│  │MinIO Storage  │ │Audio Processor│ │   Publisher   │       │
│  └───────────────┘ └───────────────┘ └───────────────┘       │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                     Task Layer (Celery)                         │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│  │Parse Pipeline │ │Analyze Pipeline│ │Synth Pipeline│       │
│  └───────────────┘ └───────────────┘ └───────────────┘       │
│  ┌───────────────┐ ┌───────────────┐                          │
│  │Publish Pipeline│ │ Watch Pipeline│                          │
│  └───────────────┘ └───────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 分层设计

### 1. API 层 (`api/`)

**职责**:
- HTTP 请求/响应处理
- 请求验证
- 权限控制
- 序列化/反序列化

**设计模式**: Resource-based ViewSets

```
api/
├── __init__.py
├── views/
│   ├── __init__.py
│   ├── books.py          # 书籍资源视图
│   ├── chapters.py       # 章节资源视图
│   ├── segments.py       # 片段资源视图
│   ├── upload.py         # 文件上传视图
│   ├── voices.py         # 音色管理视图
│   ├── publish.py        # 发布管理视图
│   ├── watch.py          # 监听管理视图
│   └── health.py         # 健康检查视图
├── serializers/
│   ├── __init__.py
│   ├── book.py
│   ├── chapter.py
│   ├── segment.py
│   └── common.py
├── schemas/               # OpenAPI schemas
│   ├── __init__.py
│   ├── book.py
│   └── chapter.py
├── permissions.py        # 自定义权限
├── pagination.py        # 分页器
├── filters.py            # 过滤器
├── middleware.py         # 中间件
└── urls.py
```

### 2. 领域层 (`core/services/`)

**职责**:
- 纯业务逻辑
- 领域模型
- 业务规则
- 无外部依赖

**设计模式**: Domain Service + Repository

```
services/
├── __init__.py
├── books/
│   ├── __init__.py
│   ├── models.py          # 领域模型（Pydantic）
│   ├── repository.py      # 数据访问接口
│   ├── service.py        # 业务服务
│   └── exceptions.py     # 领域异常
├── chapters/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   └── service.py
├── segments/
│   ├── __init__.py
│   ├── models.py
│   ├── repository.py
│   └── service.py
└── common/
    ├── __init__.py
    ├── repository.py      # 通用 Repository 基类
    └── service.py        # 通用 Service 基类
```

### 3. 基础设施层 (`infrastructure/`)

**职责**:
- 外部服务集成
- 数据持久化
- 缓存实现
- 消息队列

```
infrastructure/
├── __init__.py
├── storage/
│   ├── __init__.py
│   ├── base.py           # 存储接口
│   ├── minio.py          # MinIO 实现
│   └── cache.py          # Redis 缓存
├── ai/
│   ├── __init__.py
│   ├── base.py           # AI 客户端接口
│   ├── deepseek.py       # DeepSeek 实现
│   └── minimax.py        # MiniMax 实现
├── parser/
│   ├── __init__.py
│   ├── base.py
│   ├── epub.py           # EPUB 解析器
│   └── cleaner.py         # 文本清洗器
├── processor/
│   ├── __init__.py
│   ├── base.py
│   ├── audio.py          # 音频处理器
│   └── publisher.py      # 发布处理器
└── database/
    ├── __init__.py
    ├── unit_of_work.py   # 工作单元模式
    └── repositories/      # Django ORM 实现
        ├── __init__.py
        ├── book.py
        ├── chapter.py
        └── segment.py
```

### 4. 应用层 (`tasks/`)

**职责**:
- 任务编排
- 工作流协调
- 事务边界

```
tasks/
├── __init__.py
├── base.py               # 任务基类
├── pipeline/
│   ├── __init__.py
│   ├── parse.py          # 解析流水线
│   ├── analyze.py        # 分析流水线
│   ├── synthesize.py      # 合成流水线
│   ├── postprocess.py    # 后处理流水线
│   └── publish.py        # 发布流水线
├── watcher.py            # 文件监听任务
├── scheduler.py          # 定时任务
└── celery_app.py
```

---

## 核心领域模型

### Book (书籍)

```python
class Book:
    id: int
    title: str                    # 书名
    author: Optional[str]         # 作者
    description: Optional[str]     # 简介
    language: str                 # 语言
    cover_image_url: Optional[str] # 封面URL
    
    # 文件信息
    file_name: str               # 原始文件名
    file_size: int               # 文件大小
    file_hash: str               # 文件哈希
    file_path: str               # MinIO 存储路径
    
    # 处理状态
    status: BookStatus           # 状态枚举
    source_type: SourceType      # 来源类型
    generation_mode: GenerationMode  # 生成模式
    
    # 统计
    total_chapters: int          # 总章节数
    processed_chapters: int     # 已处理章节数
    total_duration: int          # 总音频时长
    
    # 完整音频
    full_audio_path: Optional[str]
    full_audio_duration: Optional[int]
    full_audio_size: Optional[int]
    full_audio_format: str
    
    # 发布
    auto_publish_enabled: bool
    publish_channels: List[PublishChannel]
    
    # 错误处理
    error_message: Optional[str]
    error_count: int
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
```

### Chapter (章节)

```python
class Chapter:
    id: int
    book_id: int
    
    chapter_index: int           # 章节序号
    title: str                   # 章节标题
    
    # 文本内容
    raw_text: Optional[str]       # 原始文本（预览）
    cleaned_text: Optional[str]   # 清洗后文本（MinIO路径）
    
    # 分析结果
    analysis_result: JSON        # DeepSeek 分析结果
    characters: JSON             # 角色列表
    
    status: ChapterStatus       # 处理状态
    
    # 下一章链接
    next_chapter_id: Optional[int]
    
    # 音频信息
    audio_file_path: Optional[str]
    audio_url: Optional[str]
    audio_duration: Optional[int]
    audio_file_size: Optional[int]
    audio_format: str
    
    # 片段统计
    total_segments: int
    completed_segments: int
    failed_segments: int
    
    # 成本统计
    deepseek_tokens: int
    minimax_characters: int
    estimated_cost: int
    
    # 错误
    error_message: Optional[str]
    
    created_at: datetime
    updated_at: datetime
```

### AudioSegment (音频片段)

```python
class AudioSegment:
    id: int
    chapter_id: int
    
    segment_index: int           # 片段序号
    
    # 文本内容
    text_content: str            # 文本内容
    raw_text: Optional[str]      # 原始文本
    
    # 语音参数
    role: Optional[str]          # 角色名
    emotion: Optional[str]       # 情感
    emotion_intensity: Optional[str]  # 情感强度
    
    speed: str                  # 语速
    pause_after: Optional[str]  # 段后停顿
    voice_id: Optional[str]     # 音色ID
    
    status: SegmentStatus       # 处理状态
    
    # API 调用
    minimax_request_id: Optional[str]
    minimax_cost: int          # MiniMax 消耗
    deepseek_cost: int         # DeepSeek 消耗
    
    # 音频文件
    audio_file_path: Optional[str]
    audio_url: Optional[str]
    audio_duration_ms: Optional[int]
    audio_file_size: Optional[int]
    
    # 重试
    retry_count: int
    error_message: Optional[str]
    
    # 扩展参数
    extra_params: JSON
    
    created_at: datetime
    updated_at: datetime
```

---

## 服务编排

### Pipeline Orchestrator

```python
class PipelineOrchestrator:
    """
    流水线编排器
    
    负责协调各个服务完成完整的有声书生成流程。
    """
    
    def __init__(
        self,
        parser_service: ParserService,
        analyzer_service: AnalyzerService,
        synthesizer_service: SynthesizerService,
        processor_service: ProcessorService,
        publisher_service: PublisherService,
    ):
        self.parser = parser_service
        self.analyzer = analyzer_service
        self.synthesizer = synthesizer_service
        self.processor = processor_service
        self.publisher = publisher_service
    
    async def generate_audiobook(
        self,
        book_id: int,
        options: GenerationOptions = None,
    ) -> GenerationResult:
        """
        生成有声书完整流程
        
        流程:
        1. 解析 EPUB → 提取章节
        2. 清洗文本 → 准备分析
        3. DeepSeek 分析 → 角色识别、情感标注
        4. 创建片段 → TTS 参数
        5. TTS 合成 → 音频片段
        6. 音频后处理 → 拼接、标准化
        7. 发布 → 上传平台
        """
        # 实现...
    
    async def process_chapter(
        self,
        chapter_id: int,
        options: ChapterProcessingOptions = None,
    ) -> ChapterProcessingResult:
        """
        处理单个章节
        
        事件驱动：章节处理完成后自动触发下一阶段。
        """
        # 实现...
```

### 服务依赖图

```
┌──────────────┐
│ParserService │
└──────┬───────┘
       │ parsed_chapters
       ▼
┌──────────────┐
│CleanerService│
└──────┬───────┘
       │ cleaned_texts
       ▼
┌──────────────┐
│AnalyzerService│◄───── DeepSeek API
└──────┬───────┘
       │ analysis_result
       ▼
┌──────────────┐
│SegmentService │
└──────┬───────┘
       │ segments
       ▼
┌──────────────┐
│Synthesizer   │◄───── MiniMax API
└──────┬───────┘
       │ audio_files
       ▼
┌──────────────┐
│ProcessorService│
└──────┬───────┘
       │ final_audio
       ▼
┌──────────────┐
│PublisherService│
└──────────────┘
```

---

## 任务系统

### Celery 架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Celery Workers                        │
├─────────────────────────────────────────────────────────────┤
│  Queue: celery      │  Queue: analyze  │  Queue: pipeline  │
│  - Health checks    │  - DeepSeek tasks│  - Chapter tasks │
│  - File watching    │  - AI analysis   │  - Audio tasks  │
├─────────────────────────────────────────────────────────────┤
│  Queue: publish     │  Queue: watch                        │
│  - Platform publish │  - File monitoring                   │
└─────────────────────────────────────────────────────────────┘
```

### 任务设计

```python
# 任务命名约定: {domain}.{action}
# 例: book.parse, chapter.analyze, segment.synthesize

@celery_app.task(
    bind=True,
    name="book.parse",
    queue="pipeline",
    max_retries=3,
    autoretry_for=(EPUBParseError,),
    retry_backoff=True,
    retry_backoff_max=120,
)
def parse_book(self, book_id: int) -> Dict[str, Any]:
    """解析 EPUB 文件"""
    orchestrator = get_orchestrator()
    return await orchestrator.parse_book(book_id)


@celery_app.task(
    bind=True,
    name="chapter.analyze",
    queue="analyze",
    max_retries=3,
    autoretry_for=(DeepSeekApiError,),
    rate_limit="10/m",  # 限制 API 调用频率
)
def analyze_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """分析章节"""
    orchestrator = get_orchestrator()
    return await orchestrator.analyze_chapter(chapter_id)


@celery_app.task(
    bind=True,
    name="segment.synthesize",
    queue="pipeline",
    max_retries=5,
    autoretry_for=(MiniMaxApiError,),
    rate_limit="60/m",  # TTS API 限制
)
def synthesize_segment(self, segment_id: int) -> Dict[str, Any]:
    """合成音频片段"""
    orchestrator = get_orchestrator()
    return await orchestrator.synthesize_segment(segment_id)


@celery_app.task(
    name="chapter.postprocess",
    queue="pipeline",
    max_retries=2,
)
def postprocess_chapter(self, chapter_id: int) -> Dict[str, Any]:
    """后处理章节音频"""
    orchestrator = get_orchestrator()
    return await orchestrator.postprocess_chapter(chapter_id)
```

### 工作流编排

```python
# 使用 Celery Canvas 进行复杂工作流编排

from celery import chain, group, chord

def generate_audiobook_workflow(book_id: int):
    """
    完整有声书生成工作流
    
    策略:
    - 使用 chord 编排章节级并行处理
    - 使用 chain 确保阶段顺序
    """
    
    # 阶段1: 解析书籍
    parse_job = parse_book.s(book_id)
    
    # 阶段2: 并行分析所有章节
    analyze_group = group(
        analyze_chapter.s(ch_id) for ch_id in get_chapter_ids(book_id)
    )
    
    # 阶段3: 汇总后处理
    postprocess_job = postprocess_book.s(book_id)
    
    # 完整工作流: 解析 → 并行分析 → 汇总后处理
    workflow = chain(parse_job, analyze_group, postprocess_job)
    
    return workflow.apply_async()


def chapter_workflow(chapter_id: int):
    """
    单章节处理工作流
    
    流程: 分析 → 创建片段 → 合成 → 后处理
    """
    
    analyze_job = analyze_chapter.s(chapter_id)
    create_job = create_segments.s(chapter_id)
    synthesize_job = synthesize_chapter.s(chapter_id)
    postprocess_job = postprocess_chapter.s(chapter_id)
    
    return chain(analyze_job, create_job, synthesize_job, postprocess_job)
```

---

## API 设计

### RESTful 约定

| 操作 | HTTP 方法 | URL | 说明 |
|------|----------|-----|------|
| 列表 | GET | /api/v1/books | 获取书籍列表 |
| 详情 | GET | /api/v1/books/{id} | 获取书籍详情 |
| 创建 | POST | /api/v1/books | 创建书籍 |
| 更新 | PATCH | /api/v1/books/{id} | 更新书籍 |
| 删除 | DELETE | /api/v1/books/{id} | 删除书籍 |
| 上传 | POST | /api/v1/upload | 上传 EPUB |
| 生成 | POST | /api/v1/books/{id}/generate | 触发生成 |
| 重试 | POST | /api/v1/books/{id}/retry | 重试失败章节 |

### 响应格式

```json
// 成功响应
{
    "success": true,
    "data": { ... },
    "meta": {
        "page": 1,
        "page_size": 20,
        "total": 100
    }
}

// 错误响应
{
    "success": false,
    "error": {
        "code": "BOOK_NOT_FOUND",
        "message": "书籍不存在",
        "details": { "book_id": 123 }
    }
}
```

### 状态码约定

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 状态冲突 |
| 422 | Unprocessable | 业务逻辑错误 |
| 429 | Too Many Requests | 请求过于频繁 |
| 500 | Internal Error | 服务器错误 |
| 503 | Service Unavailable | 服务不可用 |

---

## 数据模型

### 数据库 Schema

```sql
-- 书籍表
CREATE TABLE books (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    description TEXT,
    language VARCHAR(50) DEFAULT 'zh-CN',
    
    -- 封面
    cover_image_url VARCHAR(1000),
    cover_image_path VARCHAR(500),
    
    -- 文件信息
    file_name VARCHAR(500) NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64),
    file_path VARCHAR(1000),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'PENDING',
    source_type VARCHAR(20) DEFAULT 'MANUAL',
    generation_mode VARCHAR(20) DEFAULT 'AUTO',
    
    -- 统计
    total_chapters INT DEFAULT 0,
    processed_chapters INT DEFAULT 0,
    total_duration BIGINT DEFAULT 0,
    
    -- 完整音频
    full_audio_path VARCHAR(1000),
    full_audio_duration INT,
    full_audio_size BIGINT,
    full_audio_format VARCHAR(20) DEFAULT 'm4b',
    
    -- 发布
    auto_publish_enabled BOOLEAN DEFAULT FALSE,
    watch_path VARCHAR(500),
    
    -- 错误
    error_message TEXT,
    error_count INT DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- 索引
    CONSTRAINT books_status_created_idx UNIQUE (status, created_at)
);

-- 章节表
CREATE TABLE chapters (
    id BIGSERIAL PRIMARY KEY,
    book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_index INT NOT NULL,
    title VARCHAR(500),
    
    -- 文本
    raw_text TEXT,
    cleaned_text TEXT,
    
    -- 分析结果
    analysis_result JSONB,
    characters JSONB,
    
    status VARCHAR(20) DEFAULT 'PENDING',
    next_chapter_id BIGINT,
    
    -- 音频
    audio_file_path VARCHAR(1000),
    audio_url VARCHAR(1000),
    audio_duration INT,
    audio_file_size BIGINT,
    audio_format VARCHAR(20) DEFAULT 'mp3',
    
    -- 统计
    total_segments INT DEFAULT 0,
    completed_segments INT DEFAULT 0,
    failed_segments INT DEFAULT 0,
    
    -- 成本
    deepseek_tokens INT DEFAULT 0,
    minimax_characters INT DEFAULT 0,
    estimated_cost INT DEFAULT 0,
    
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 约束和索引
    CONSTRAINT chapters_book_chapter_idx UNIQUE (book_id, chapter_index),
    CONSTRAINT chapters_book_status_idx UNIQUE (book_id, status)
);

-- 音频片段表
CREATE TABLE audio_segments (
    id BIGSERIAL PRIMARY KEY,
    chapter_id BIGINT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    segment_index INT NOT NULL,
    
    text_content TEXT NOT NULL,
    raw_text TEXT,
    
    -- 语音参数
    role VARCHAR(100),
    emotion VARCHAR(50),
    emotion_intensity VARCHAR(20),
    speed VARCHAR(20) DEFAULT 'normal',
    pause_after VARCHAR(20),
    voice_id VARCHAR(100),
    
    status VARCHAR(20) DEFAULT 'PENDING',
    
    -- API
    minimax_request_id VARCHAR(255),
    minimax_cost INT DEFAULT 0,
    deepseek_cost INT DEFAULT 0,
    
    -- 音频
    audio_file_path VARCHAR(1000),
    audio_url VARCHAR(1000),
    audio_duration_ms INT,
    audio_file_size BIGINT,
    
    retry_count INT DEFAULT 0,
    error_message TEXT,
    
    extra_params JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 约束和索引
    CONSTRAINT segments_chapter_segment_idx UNIQUE (chapter_id, segment_index),
    CONSTRAINT segments_chapter_status_idx UNIQUE (chapter_id, status)
);

-- 发布渠道表
CREATE TABLE publish_channels (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    platform_type VARCHAR(20) NOT NULL,
    api_config JSONB,
    is_enabled BOOLEAN DEFAULT TRUE,
    auto_publish BOOLEAN DEFAULT FALSE,
    priority INT DEFAULT 0,
    
    -- 统计
    total_published INT DEFAULT 0,
    success_count INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    last_published_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 发布记录表
CREATE TABLE publish_records (
    id BIGSERIAL PRIMARY KEY,
    book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES publish_channels(id),
    
    status VARCHAR(20) DEFAULT 'PENDING',
    external_album_id VARCHAR(255),
    external_album_url VARCHAR(1000),
    
    total_chapters INT,
    published_chapters INT DEFAULT 0,
    failed_chapters INT DEFAULT 0,
    
    error_message TEXT,
    retry_count INT DEFAULT 0,
    result_details JSONB,
    published_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- TTS 任务表 (可选，用于详细追踪)
CREATE TABLE tts_tasks (
    id BIGSERIAL PRIMARY KEY,
    segment_id BIGINT REFERENCES audio_segments(id),
    request_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'PENDING',
    
    text_content TEXT,
    voice_id VARCHAR(100),
    audio_duration_ms INT,
    
    cost INT DEFAULT 0,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 任务历史表 (可选)
CREATE TABLE task_history (
    id BIGSERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    task_id VARCHAR(100),
    
    entity_type VARCHAR(50),
    entity_id BIGINT,
    
    status VARCHAR(20),
    result JSONB,
    error_message TEXT,
    
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INT,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 配置管理

### 配置分层

```
config/
├── __init__.py
├── settings/
│   ├── __init__.py
│   ├── base.py          # 基础配置
│   ├── development.py   # 开发环境
│   ├── production.py    # 生产环境
│   └── test.py         # 测试环境
├── django.py           # Django 专用配置
├── celery.py           # Celery 配置
├── database.py        # 数据库配置
├── storage.py        # 存储配置
├── ai.py             # AI 服务配置
└── logging.py       # 日志配置
```

### 环境变量

```bash
# .env.example

# 应用配置
APP_NAME="AI 有声书工坊"
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000

# 数据库
DB_ENGINE=django.db.backends.postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=audiobook_db
DB_USER=audiobook_user
DB_PASSWORD=your-db-password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET_EPUB=books-epub
MINIO_BUCKET_AUDIO=books-audio

# DeepSeek
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_TEMPERATURE=0.7

# MiniMax
MINIMAX_API_KEY=your-api-key
MINIMAX_API_HOST=https://api.minimax.chat
MINIMAX_GROUP_ID=your-group-id

# 文件监听
WATCH_DIR=/books/incoming
WATCH_DIRS=
WATCH_INTERVAL=60
WATCH_ENABLED=true
WATCH_CONCURRENT=3
WATCH_MAX_FILE_SIZE_MB=500

# 音频处理
AUDIO_SAMPLE_RATE=44100
AUDIO_BITRATE=192
AUDIO_CROSSFADE_MS=20

# 日志
LOG_LEVEL=INFO
```

---

## 目录结构

### 完整目录结构

```
backend/
├── apps/
│   ├── __init__.py
│   ├── books/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── filters.py
│   │   ├── permissions.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       ├── test_views.py
│   │       └── test_services.py
│   ├── chapters/
│   │   └── ...
│   ├── audio/
│   │   └── ...
│   └── monitor/
│       └── ...
├── core/
│   ├── __init__.py
│   ├── domain/               # 领域层
│   │   ├── __init__.py
│   │   ├── models.py         # Pydantic 领域模型
│   │   ├── services.py       # 领域服务
│   │   ├── repositories.py    # 仓储接口
│   │   ├── events.py         # 领域事件
│   │   └── exceptions.py     # 领域异常
│   ├── infrastructure/       # 基础设施层
│   │   ├── __init__.py
│   │   ├── storage/          # 存储实现
│   │   ├── ai/               # AI 服务实现
│   │   ├── parser/           # 解析器实现
│   │   ├── processor/        # 处理器实现
│   │   └── database/          # 数据库实现
│   ├── constants.py          # 常量定义
│   ├── exceptions.py         # 应用异常
│   ├── middleware.py         # 中间件
│   └── utils.py              # 工具函数
├── services/                 # 业务服务层 (Facade)
│   ├── __init__.py
│   ├── book_service.py
│   ├── chapter_service.py
│   ├── audio_service.py
│   ├── pipeline_service.py   # 流水线服务
│   └── publish_service.py
├── tasks/                    # Celery 任务
│   ├── __init__.py
│   ├── base.py
│   ├── celery_app.py
│   ├── pipeline/             # 流水线任务
│   │   ├── parse.py
│   │   ├── analyze.py
│   │   ├── synthesize.py
│   │   ├── postprocess.py
│   │   └── publish.py
│   ├── watcher.py
│   └── scheduler.py
├── api/                      # API 层
│   ├── __init__.py
│   ├── views/
│   │   ├── books.py
│   │   ├── chapters.py
│   │   ├── audio.py
│   │   ├── upload.py
│   │   ├── voices.py
│   │   ├── publish.py
│   │   ├── watch.py
│   │   └── health.py
│   ├── serializers/
│   │   ├── book.py
│   │   ├── chapter.py
│   │   ├── segment.py
│   │   └── common.py
│   ├── schemas/              # OpenAPI schemas
│   ├── urls.py
│   ├── middleware.py
│   └── permissions.py
├── config/                   # 配置
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── celery.py
│   ├── database.py
│   ├── storage.py
│   ├── ai.py
│   └── logging.py
├── migrations/              # 数据库迁移
├── scripts/                  # 运维脚本
│   ├── init_db.py
│   ├── seed_data.py
│   └── benchmark.py
├── tests/                   # 测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
└── manage.py
```

---

## 迁移策略

### Phase 1: 架构铺垫 (1-2周)
- [ ] 创建新目录结构
- [ ] 配置管理系统（多环境配置）
- [ ] 统一异常处理
- [ ] 中间件完善
- [ ] 日志系统标准化

### Phase 2: 模型重构 (1周)
- [ ] 重构 Django Models（添加索引、约束）
- [ ] 创建 Pydantic 领域模型
- [ ] 编写数据迁移脚本
- [ ] 更新 Serializers

### Phase 3: 服务拆分 (2-3周)
- [ ] 提取 Parser Service
- [ ] 提取 Analyzer Service
- [ ] 提取 TTS Service
- [ ] 提取 Audio Processor Service
- [ ] 提取 Publisher Service
- [ ] 服务接口统一

### Phase 4: API 重构 (1-2周)
- [ ] ViewSets 按资源分离
- [ ] Serializers 完善
- [ ] 权限系统重构
- [ ] 分页/过滤优化
- [ ] API 文档完善

### Phase 5: 任务系统重构 (1-2周)
- [ ] Celery 任务拆分
- [ ] 重试机制完善
- [ ] 限流机制
- [ ] 任务监控
- [ ] 错误处理

### Phase 6: 测试完善 (1-2周)
- [ ] 单元测试覆盖
- [ ] 集成测试
- [ ] E2E 测试
- [ ] 性能测试

### Phase 7: DevOps 优化 (1周)
- [ ] Dockerfile 优化
- [ ] docker-compose 完善
- [ ] CI/CD 流程
- [ ] 监控告警

---

## 附录

### A. 依赖关系图

```
api.views ──► services.* ──► core.domain ──► core.infrastructure.*
                │
                ▼
          infrastructure.*
                │
                ▼
          core.database
                │
                ▼
          Django ORM
```

### B. 错误码规范

```
{模块}_{编号}

例:
- BOOK_001: 书籍不存在
- BOOK_002: 书籍已存在
- BOOK_003: 文件格式错误
- CHAPTER_001: 章节不存在
- CHAPTER_002: 章节状态错误
- AUDIO_001: 音频生成失败
- AUDIO_002: 音频文件损坏
- AI_001: DeepSeek API 错误
- AI_002: MiniMax API 错误
- STORAGE_001: 存储服务错误
```

### C. 监控指标

| 指标 | 类型 | 说明 |
|------|------|------|
| book_generation_duration | Histogram | 书籍生成耗时 |
| chapter_processing_duration | Histogram | 章节处理耗时 |
| deepseek_api_calls_total | Counter | DeepSeek API 调用次数 |
| minimax_api_calls_total | Counter | MiniMax API 调用次数 |
| api_request_duration | Histogram | API 请求耗时 |
| celery_task_duration | Histogram | Celery 任务耗时 |
| celery_task_retries_total | Counter | 任务重试次数 |
| celery_task_failures_total | Counter | 任务失败次数 |
| storage_operations_total | Counter | 存储操作次数 |
| storage_operations_duration | Histogram | 存储操作耗时 |

---

*文档结束*
