-- ===========================================
-- 迁移脚本：添加音效库相关表
-- ===========================================
-- 执行: docker-compose exec db psql -U postgres -d novels
-- 或: 等待 Docker 启动后执行 python manage.py migrate

-- ===========================================
-- 1. 创建 sound_effects 表
-- ===========================================
CREATE TABLE IF NOT EXISTS sound_effects (
    id SERIAL PRIMARY KEY,
    -- 基本信息
    name VARCHAR(255) NOT NULL,
    description TEXT,
    chinese_description VARCHAR(500),

    -- 分类信息
    effect_type VARCHAR(20) DEFAULT 'environment',
    layer VARCHAR(20) DEFAULT 'foreground',

    -- 标签系统
    tags JSONB,
    chinese_tags JSONB,
    semantic_keywords JSONB,

    -- 语义匹配
    audio_embedding JSONB,

    -- 来源信息
    source VARCHAR(20) DEFAULT 'bbc',
    source_id VARCHAR(255),
    source_url VARCHAR(1000),
    license_type VARCHAR(100),

    -- 音频属性
    duration_ms INTEGER,
    file_format VARCHAR(20),
    file_size BIGINT,
    sample_rate INTEGER,

    -- 存储信息
    local_path VARCHAR(500),
    minio_path VARCHAR(500),
    minio_url VARCHAR(1000),

    -- 状态管理
    status VARCHAR(20) DEFAULT 'active',
    is_favorite BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,

    -- 推荐信息
    priority VARCHAR(20) DEFAULT 'medium',
    suitable_scenes JSONB,
    recommended_volume_min FLOAT,
    recommended_volume_max FLOAT,
    recommended_fade_in_ms INTEGER,
    recommended_fade_out_ms INTEGER,

    -- 审核信息
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_sound_effects_effect_type_status ON sound_effects(effect_type, status);
CREATE INDEX IF NOT EXISTS ix_sound_effects_source_status ON sound_effects(source, status);
CREATE INDEX IF NOT EXISTS ix_sound_effects_usage_count ON sound_effects(usage_count DESC);
CREATE INDEX IF NOT EXISTS ix_sound_effects_priority ON sound_effects(priority);
CREATE INDEX IF NOT EXISTS ix_sound_effects_verified_status ON sound_effects(is_verified, status);
CREATE INDEX IF NOT EXISTS ix_sound_effects_name ON sound_effects(name);

COMMENT ON TABLE sound_effects IS '音效库 - 存储所有可用的音效资源';
COMMENT ON COLUMN sound_effects.effect_type IS '音效类型: environment/action/transition/nature/ambient/weather/urban/fantasy/scifi';
COMMENT ON COLUMN sound_effects.source IS '音效来源: bbc/fsd50k/user_upload/generated';

-- ===========================================
-- 2. 创建 sound_effect_usages 表
-- ===========================================
CREATE TABLE IF NOT EXISTS sound_effect_usages (
    id SERIAL PRIMARY KEY,
    sound_effect_id INTEGER NOT NULL REFERENCES sound_effects(id) ON DELETE CASCADE,

    -- 使用场景
    book_id INTEGER,
    chapter_id INTEGER,

    -- 使用参数
    trigger_at_ms INTEGER,
    volume FLOAT,
    fade_in_ms INTEGER,
    fade_out_ms INTEGER,
    loop BOOLEAN DEFAULT FALSE,

    -- 来源信息
    matched_from_query VARCHAR(500),
    match_score FLOAT,

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_sound_effect_usages_sound_effect_created ON sound_effect_usages(sound_effect_id, created_at);
CREATE INDEX IF NOT EXISTS ix_sound_effect_usages_book_chapter ON sound_effect_usages(book_id, chapter_id);

COMMENT ON TABLE sound_effect_usages IS '音效使用记录 - 跟踪音效的使用情况';

-- ===========================================
-- 3. 创建 sound_effect_collections 表
-- ===========================================
CREATE TABLE IF NOT EXISTS sound_effect_collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- 适用场景
    scene_type VARCHAR(50),

    -- 统计
    sound_count INTEGER DEFAULT 0,

    -- 元信息
    is_public BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_sound_effect_collections_name ON sound_effect_collections(name);

COMMENT ON TABLE sound_effect_collections IS '音效收藏集 - 用户自定义的音效集合';

-- ===========================================
-- 4. 创建 sound_effect_collection_items 表
-- ===========================================
CREATE TABLE IF NOT EXISTS sound_effect_collection_items (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES sound_effect_collections(id) ON DELETE CASCADE,
    sound_effect_id INTEGER NOT NULL REFERENCES sound_effects(id) ON DELETE CASCADE,

    -- 自定义配置
    custom_volume FLOAT,
    custom_fade_in_ms INTEGER,
    custom_fade_out_ms INTEGER,

    -- 排序
    sort_order INTEGER DEFAULT 0,

    -- 时间戳
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(collection_id, sound_effect_id)
);

CREATE INDEX IF NOT EXISTS ix_sound_effect_collection_items_collection ON sound_effect_collection_items(collection_id);
CREATE INDEX IF NOT EXISTS ix_sound_effect_collection_items_sound_effect ON sound_effect_collection_items(sound_effect_id);

COMMENT ON TABLE sound_effect_collection_items IS '音效收藏集项目 - 连接收藏集和音效的多对多中间表';

-- ===========================================
-- 5. 为 chapters 表添加 sound_effects 字段（如果还没有）
-- ===========================================
-- 注意：这个在之前的迁移中可能已经添加
-- ALTER TABLE chapters ADD COLUMN IF NOT EXISTS sound_effects JSONB;
-- ALTER TABLE chapters ADD COLUMN IF NOT EXISTS background_music JSONB;
-- ALTER TABLE chapters ADD COLUMN IF NOT EXISTS audio_bridge JSONB;

-- ===========================================
-- 6. 插入默认音效收藏集
-- ===========================================
INSERT INTO sound_effect_collections (name, description, scene_type, is_default, sound_count)
VALUES
    ('常用音效', '最常用的音效集合', '通用', TRUE, 0),
    ('玄幻/仙侠', '适合玄幻、仙侠小说的音效', '仙侠', FALSE, 0),
    ('都市/现代', '适合都市、现代小说的音效', '都市', FALSE, 0),
    ('古风/历史', '适合古风、历史小说的音效', '古风', FALSE, 0)
ON CONFLICT DO NOTHING;

-- ===========================================
-- 7. 验证
-- ===========================================
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'sound_effect%';
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'sound_effects';
-- SELECT COUNT(*) FROM sound_effects;
-- SELECT * FROM sound_effect_collections;

-- ===========================================
-- 8. 清理函数
-- ===========================================
-- 删除 orphaned 使用记录（音效已删除）
-- DELETE FROM sound_effect_usages WHERE sound_effect_id NOT IN (SELECT id FROM sound_effects);

-- 更新收藏集音效数量
-- UPDATE sound_effect_collections sc SET sound_count = (
--     SELECT COUNT(*) FROM sound_effect_collection_items sci
--     WHERE sci.collection_id = sc.id
-- );
