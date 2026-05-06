# 有声书制作系统 - DeepSeek 提示词

## 工作流

```
epub导入 → MinIO存储 → 自动分割 → MinIO读取 → DeepSeek一次调用
                                                          ↓
                                               提取完整剧本信息
                                               ├─ 有声小说剧本
                                               ├─ 角色信息
                                               ├─ 音效设计（含时间点）
                                               └─ 背景音乐规划
                                                          ↓
                                                  自动匹配音色
                                                          ↓
                                                  人工审阅
                                                          ↓
                                              手动触发生成多角色音频
```

## DeepSeek 提示词 (一次性调用)

```python
FULL_ANALYSIS_PROMPT = """你是一位专业的有声书制作人兼音频导演。请对以下小说文本进行全面分析，一次性输出完整剧本信息。

【已知角色】（如已知）
{role_list}

【分析任务】（一次性完成所有分析）
1. 段落拆分与说话人识别
2. 情感标注（细分强度）
3. 多音字消歧
4. 音效设计与时间点标注（核心新增）
5. 背景音乐建议与时间轴规划（核心新增）

【中文网络小说特色】
- 网络小说特有称呼：道兄、前辈、宗主、仙尊、魔帝、陛下、父皇等
- 特殊格式：[系统提示]、（心想）、*注释*、（暗道）
- 玄幻元素：灵根、筑基、金丹、元婴等修炼术语保持原样
- 识别场景关键词：打斗、法宝、阵法、渡劫等用于音效设计

【音效类型定义】
- environment: 环境音（雨声、风声、城市喧嚣、雷声、虫鸣）
- action: 动作音（脚步声、剑鸣、关门声、翻书声、马蹄声）
- transition: 转场音（章节过渡、时间跳转提示音）
- nature: 自然音（鸟鸣、水流、瀑布、风声）
- ambient: 氛围音（远处人声、心跳、时钟滴答、呼吸声）

【音效设计原则】
- 时间点格式：使用 "00:01:30" 格式（时:分:秒）
- 基于文本推断关键音效触发点
- 标注淡入淡出时间（fade_in_ms, fade_out_ms）
- 音量层级建议：人声100% > 前景音效80% > 背景音效50% > 背景音乐30%

【背景音乐设计原则】
- 类型：theme/epic/romantic/mysterious/tension/calm/adventure/sad/heroic
- 标注强度(1-5)，1最弱，5最强
- 考虑情绪起伏和场景变化
- 标注交叉淡入淡出点

【输出格式】（严格 JSON，不要有任何额外文字）
{
  "meta": {
    "title": "自动识别或'章节X'",
    "estimated_duration_minutes": 预估分钟数,
    "language": "zh-CN"
  },
  "paragraphs": [...],
  "characters": [...],
  "sound_effects": [
    {
      "index": 1,
      "type": "environment|action|transition|nature|ambient",
      "description": "具体音效描述",
      "trigger_at": "00:01:30",
      "duration_ms": 3000,
      "volume": 0.5,
      "fade_in_ms": 500,
      "fade_out_ms": 500,
      "loop": false,
      "priority": "high|medium|low",
      "layer": "foreground|background",
      "text_anchor": "关联的原文片段"
    }
  ],
  "background_music": [
    {
      "index": 1,
      "type": "theme|epic|romantic|mysterious|tension|calm|adventure|sad|heroic",
      "mood": "情绪氛围描述",
      "trigger_at": "00:00:00",
      "end_at": "00:05:30",
      "volume": 0.3,
      "fade_in_ms": 2000,
      "fade_out_ms": 3000,
      "crossfade_with_next": true,
      "intensity": 3,
      "scene_context": "适用场景描述"
    }
  ],
  "audio_bridge": {
    "opening": "开场音效描述",
    "chapter_transitions": ["章节过渡音效建议"],
    "ending": "结尾音效描述",
    "silence_markers": ["需要留白的时刻"]
  },
  "statistics": {...},
  "technical_notes": {...}
}

待分析文本：
{text}"""
```

## 数据库字段

| 字段 | 类型 | 说明 |
|------|------|------|
| sound_effects | JSONB | 音效设计列表 |
| background_music | JSONB | 背景音乐列表 |
| audio_bridge | JSONB | 音频桥接设计 |

## MinIO 存储路径

| 用途 | 路径格式 |
|------|----------|
| 章节文本 | `chapters/{book_id}/{index:03d}_cleaned.txt` |
| 完整剧本 | `scripts/{book_id}/{index:03d}_script.json` |
| 角色音色映射 | `books/{book_id}/voice_mapping.json` |

## 数据库迁移

```bash
# 方式1: Docker 环境
docker-compose exec backend python manage.py makemigrations core --name add_sound_effects_and_music
docker-compose exec backend python manage.py migrate

# 方式2: 直接执行 SQL
docker-compose exec db psql -U postgres -d novels -f /migrations/add_sound_effects_and_music.sql
```

## 音效库推荐

| 来源 | 特点 | 协议 | 预估大小 |
|------|------|------|----------|
| fsd50k-cc0-Qwen3-Omni | AI生成场景描述 | CC0 | 40GB |
| BBC Sound Effects | 广播级环境音 | BBC License | 按需下载 |
| AudioCaps | 句子级语义描述 | Creative Common | - |

## 音效库实现 (新增)

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    音效库系统架构                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐  │
│  │ DeepSeek    │──▶│ SoundEffect │──▶│ SoundEffectMixer │  │
│  │ Analyzer    │   │ Library     │   │ Service         │  │
│  └─────────────┘   └─────────────┘   └─────────────────┘  │
│        │                  │                    │            │
│        ▼                  ▼                    ▼            │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐  │
│  │ sound_effects│   │ BBC Sound   │   │ Audio Post-    │  │
│  │ JSON Field  │   │ Effects API │   │ Processor      │  │
│  └─────────────┘   └─────────────┘   └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 数据模型

#### SoundEffect (音效表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| name | VARCHAR(255) | 音效名称 |
| chinese_description | VARCHAR(500) | 中文描述 |
| effect_type | VARCHAR(20) | 音效类型 |
| layer | VARCHAR(20) | 音效层级 |
| tags | JSONB | 英文标签 |
| chinese_tags | JSONB | 中文标签 |
| source | VARCHAR(20) | 音效来源 |
| source_id | VARCHAR(255) | 来源ID |
| duration_ms | INTEGER | 时长(毫秒) |
| usage_count | INTEGER | 使用次数 |
| priority | VARCHAR(20) | 推荐优先级 |

#### SoundEffectUsage (使用记录表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| sound_effect_id | INTEGER | 音效ID |
| book_id | INTEGER | 书籍ID |
| chapter_id | INTEGER | 章节ID |
| trigger_at_ms | INTEGER | 触发时间 |
| volume | FLOAT | 音量 |
| match_score | FLOAT | 匹配分数 |

### API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/sound-effects/ | 列出所有音效 |
| POST | /api/sound-effects/ | 创建音效 |
| POST | /api/sound-effects/search/ | 搜索音效 |
| POST | /api/sound-effects/recommend/ | 推荐音效 |
| POST | /api/sound-effects/bbc-sync/ | 同步BBC音效 |
| GET | /api/sound-effects/collections/ | 列出收藏集 |
| GET | /api/books/{id}/sound-effects/export/ | 导出配置 |
| POST | /api/books/{id}/sound-effects/import/ | 导入配置 |

### 音效类型枚举

```python
class SoundEffectType(models.TextChoices):
    ENVIRONMENT = "environment", "环境音"
    ACTION = "action", "动作音"
    TRANSITION = "transition", "转场音"
    NATURE = "nature", "自然音"
    AMBIENT = "ambient", "氛围音"
    WEATHER = "weather", "天气音"
    URBAN = "urban", "城市音"
    FANTASY = "fantasy", "玄幻/奇幻音"
    SCIFI = "scifi", "科幻音"
```

### 数据库迁移

```bash
# Docker 环境
docker-compose exec db psql -U postgres -d novels -f /migrations/add_sound_effect_library.sql
```

### 音量层级配置

```
人声对话: 100%
前景音效: 80%
背景音效: 50%
环境音:   30%
背景音乐: 30%
```
