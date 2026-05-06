#!/bin/bash
# ===========================================
# Docker 构建优化脚本
# ===========================================

set -e

# 启用 BuildKit
export DOCKER_BUILDKIT=1

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 默认值
COMPOSE_FILE="docker-compose.yml"
SKIP_TESTS=false
NO_CACHE=false
PARALLEL=true

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --no-cache      不使用缓存，强制重新构建"
            echo "  --skip-tests    跳过测试"
            echo "  --file <file>   指定 docker-compose 文件"
            echo "  --help          显示帮助"
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            exit 1
            ;;
    esac
done

# 检查 Docker
if ! docker info > /dev/null 2>&1; then
    log_error "Docker 未运行"
    exit 1
fi

log_info "构建配置:"
log_info "  BuildKit: $DOCKER_BUILDKIT"
log_info "  Compose: $COMPOSE_FILE"
log_info "  Skip Tests: $SKIP_TESTS"
log_info "  No Cache: $NO_CACHE"

# 构建参数
BUILD_ARGS=""

if [ "$NO_CACHE" = true ]; then
    BUILD_ARGS="$BUILD_ARGS --no-cache"
    log_warn "不使用缓存，构建时间会比较长"
fi

# 构建 API 服务
log_info "开始构建 API 服务..."
time docker compose -f "$COMPOSE_FILE" build $BUILD_ARGS --parallel api

# 构建其他服务（并行）
log_info "开始构建其他服务..."
time docker compose -f "$COMPOSE_FILE" build $BUILD_ARGS --parallel celery-worker celery-beat

log_info "构建完成！"
log_info ""
log_info "启动服务: docker compose -f $COMPOSE_FILE up -d"
log_info "查看日志: docker compose -f $COMPOSE_FILE logs -f"
