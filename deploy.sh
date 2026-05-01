#!/bin/bash
# ===========================================
# AI 有声书工坊 - 部署脚本
# ===========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 显示横幅
show_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║          AI 有声书工坊 - 部署脚本 v1.0                     ║"
    echo "║          AI Audiobook Workshop - Deployment Script         ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

# 显示使用说明
show_usage() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动所有服务"
    echo "  stop        停止所有服务"
    echo "  restart     重启所有服务"
    echo "  status      查看服务状态"
    echo "  logs        查看日志"
    echo "  build       构建镜像"
    echo "  clean       清理资源"
    echo "  test        运行测试"
    echo "  deploy      完整部署流程"
    echo "  health      健康检查"
    echo ""
    echo "示例:"
    echo "  $0 start          # 启动服务"
    echo "  $0 deploy         # 完整部署"
    echo "  $0 health         # 健康检查"
    echo ""
}

# 检查前置条件
check_prerequisites() {
    log_info "检查前置条件..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    # 检查 .env 文件
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            log_warn ".env 文件不存在，正在从 .env.example 创建..."
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            log_warn "请编辑 .env 文件配置必要的环境变量"
        else
            log_error ".env 文件不存在"
            exit 1
        fi
    fi

    log_success "前置条件检查通过"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."

    dirs=(
        "$PROJECT_ROOT/data/postgres"
        "$PROJECT_ROOT/data/minio"
        "$PROJECT_ROOT/data/incoming"
        "$PROJECT_ROOT/books/incoming"
        "$PROJECT_ROOT/books/dead-letter"
        "$PROJECT_ROOT/books/output"
    )

    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
        fi
    done

    # 设置权限
    chmod -R 755 "$PROJECT_ROOT/data" 2>/dev/null || true
    chmod -R 755 "$PROJECT_ROOT/books" 2>/dev/null || true

    log_success "目录创建完成"
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."

    cd "$PROJECT_ROOT"

    # 构建后端镜像
    log_info "构建后端镜像..."
    docker build -t audiobook-backend:latest -f backend/Dockerfile .

    # 构建前端镜像（如果存在）
    if [ -f "frontend/Dockerfile" ]; then
        log_info "构建前端镜像..."
        docker build -t audiobook-frontend:latest -f frontend/Dockerfile .
    fi

    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    cd "$PROJECT_ROOT"

    # 启动所有服务
    docker-compose up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10

    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        log_success "服务启动成功"
    else
        log_error "部分服务启动失败，请检查日志"
        docker-compose logs
        exit 1
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."

    cd "$PROJECT_ROOT"
    docker-compose down

    log_success "服务已停止"
}

# 查看状态
show_status() {
    log_info "服务状态:"
    echo ""
    docker-compose ps
    echo ""

    # 显示资源使用
    log_info "资源使用情况:"
    echo ""
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.Status}}"
}

# 查看日志
show_logs() {
    service=${1:-}

    if [ -n "$service" ]; then
        log_info "查看 $service 日志 (按 Ctrl+C 退出)..."
        docker-compose logs -f "$service"
    else
        log_info "查看所有日志 (按 Ctrl+C 退出)..."
        docker-compose logs -f
    fi
}

# 运行测试
run_tests() {
    log_info "运行测试..."

    cd "$PROJECT_ROOT"

    # 运行集成测试
    docker-compose exec -T backend python scripts/test_full_pipeline.py

    log_success "测试完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    cd "$PROJECT_ROOT"

    services=(
        "audiobook-backend:8000"
        "audiobook-postgres:5432"
        "audiobook-redis:6379"
        "audiobook-minio:9000"
    )

    all_healthy=true

    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"

        if docker-compose exec -T "$name" sh -c "nc -z localhost $port" &>/dev/null; then
            log_success "$name:$port ✓"
        else
            log_error "$name:$port ✗"
            all_healthy=false
        fi
    done

    # 检查 API
    log_info "检查 API 可用性..."
    backend_port=$(grep "APP_PORT" "$PROJECT_ROOT/.env" | cut -d'=' -f2 || echo "8000")
    if curl -sf "http://localhost:$backend_port/api/health" > /dev/null; then
        log_success "API 可用 ✓"
    else
        log_warn "API 暂不可用 (可能还在启动中)"
    fi

    if [ "$all_healthy" = true ]; then
        log_success "所有服务健康检查通过"
    else
        log_error "部分服务健康检查失败"
    fi
}

# 完整部署流程
deploy() {
    show_banner

    log_info "开始完整部署流程..."
    echo ""

    # 1. 检查前置条件
    check_prerequisites

    # 2. 创建目录
    create_directories

    # 3. 清理旧资源
    log_info "清理旧资源..."
    docker-compose down --remove-orphans 2>/dev/null || true
    docker system prune -f 2>/dev/null || true

    # 4. 构建镜像
    build_images

    # 5. 启动服务
    start_services

    # 6. 等待服务就绪
    log_info "等待服务就绪..."
    sleep 15

    # 7. 健康检查
    health_check

    echo ""
    log_success "═══════════════════════════════════════════════════"
    log_success "部署完成!"
    log_success "═══════════════════════════════════════════════════"
    echo ""
    log_info "访问地址:"
    log_info "  - API 文档: http://localhost:8000/api/docs"
    log_info "  - MinIO Console: http://localhost:9001"
    log_info "  - Flower (任务监控): http://localhost:5555"
    echo ""
    log_info "管理命令:"
    log_info "  - 查看日志: $0 logs"
    log_info "  - 查看状态: $0 status"
    log_info "  - 停止服务: $0 stop"
    echo ""
}

# 清理资源
clean_resources() {
    log_warn "即将清理所有资源，包括:"
    log_warn "  - 所有容器"
    log_warn "  - 所有镜像"
    log_warn "  - 所有数据卷"
    log_warn "  - 所有测试文件"
    echo ""

    read -p "确认清理? (yes/no): " confirm

    if [ "$confirm" = "yes" ]; then
        log_info "清理中..."

        cd "$PROJECT_ROOT"

        # 停止并删除容器
        docker-compose down -v --remove-orphans

        # 删除镜像
        docker rmi audiobook-backend:latest 2>/dev/null || true
        docker rmi audiobook-frontend:latest 2>/dev/null || true

        # 删除数据
        rm -rf "$PROJECT_ROOT/data/postgres"/*
        rm -rf "$PROJECT_ROOT/data/minio"/*
        rm -rf "$PROJECT_ROOT/books/output"/*

        # 清理未使用的 Docker 资源
        docker system prune -f

        log_success "清理完成"
    else
        log_info "取消清理"
    fi
}

# 重启服务
restart_services() {
    log_info "重启服务..."

    cd "$PROJECT_ROOT"

    docker-compose restart

    log_info "等待服务启动..."
    sleep 10

    health_check
}

# 主函数
main() {
    show_banner

    command=${1:-}

    case "$command" in
        start)
            check_prerequisites
            create_directories
            start_services
            health_check
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        build)
            check_prerequisites
            build_images
            ;;
        clean)
            clean_resources
            ;;
        test)
            run_tests
            ;;
        health|check)
            health_check
            ;;
        deploy)
            deploy
            ;;
        *)
            show_usage
            ;;
    esac
}

# 执行主函数
main "$@"
