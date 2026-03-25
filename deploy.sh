#!/bin/bash

# NASSAV HTTP API Docker 部署脚本
# 用于快速构建和启动 NASSAV HTTP API 服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 本脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 函数定义
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 检查前置条件
check_prerequisites() {
    print_header "检查前置条件"

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    print_success "Docker 已安装"

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    print_success "Docker Compose 已安装"

    # 检查配置文件
    if [ ! -f "$SCRIPT_DIR/cfg/configs.json" ]; then
        if [ -f "$SCRIPT_DIR/cfg/configs.json.example" ]; then
            print_warning "configs.json 不存在，从示例文件复制"
            cp "$SCRIPT_DIR/cfg/configs.json.example" "$SCRIPT_DIR/cfg/configs.json"
            print_warning "请编辑 cfg/configs.json 并设置正确的参数"
            print_info "关键配置项：SavePath, Proxy, Downloader"
        fi
    fi
    print_success "配置检查完成"
}

# 创建必要的目录
create_directories() {
    print_header "创建必要的目录"

    mkdir -p "$SCRIPT_DIR/storage"
    mkdir -p "$SCRIPT_DIR/db"
    mkdir -p "$SCRIPT_DIR/logs"

    print_success "目录创建完成"
}

# 构建镜像
build_image() {
    print_header "构建 Docker 镜像"

    print_info "这可能需要几分钟..."
    cd "$SCRIPT_DIR"
    docker-compose build

    print_success "镜像构建完成"
}

# 启动服务
start_services() {
    print_header "启动服务"

    cd "$SCRIPT_DIR"
    docker-compose up -d

    print_success "服务已启动"

    # 等待服务就绪
    print_info "等待服务就绪..."
    sleep 3

    # 检查服务状态
    if docker-compose ps | grep -q "nassav-api.*Up"; then
        print_success "API 服务已就绪"
        print_info "API 地址: http://localhost:31471"
    else
        print_error "API 服务启动失败"
        docker-compose logs nassav-api
        exit 1
    fi
}

# 构建前端
build_frontend() {
    print_header "构建前端（可选）"

    read -p "是否构建前端 Web 界面？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "检查 Node.js..."
        if ! command -v npm &> /dev/null; then
            print_error "npm 未安装，无法构建前端"
            print_info "跳过前端构建"
            return
        fi

        print_info "构建前端..."
        cd "$SCRIPT_DIR/frontend"
        npm install
        npm run build
        cd "$SCRIPT_DIR"

        print_success "前端构建完成"

        # 启动前端服务
        read -p "是否启动前端服务？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "启动前端服务..."
            docker-compose up -d nassav-frontend
            print_success "前端服务已启动"
            print_info "Web 界面地址: http://localhost:5177"
        fi
    fi
}

# 显示服务状态
show_status() {
    print_header "服务状态"

    cd "$SCRIPT_DIR"
    docker-compose ps

    echo ""
    print_header "访问地址"
    print_info "API 服务: http://localhost:31471"
    print_info "API 文档:"
    print_info "  - 获取视频列表: curl http://localhost:31471/api/videos"
    print_info "  - 获取视频详情: curl http://localhost:31471/api/videos/{id}"
    print_info "  - 添加下载任务: curl -X POST http://localhost:31471/api/addvideo/{id}"
    echo ""

    if docker-compose ps | grep -q "nassav-frontend.*Up"; then
        print_info "Web 界面: http://localhost:5177"
    fi
}

# 显示帮助信息
show_help() {
    cat << EOF
使用方法: $0 [命令]

命令:
  setup       （默认）执行完整的初始化流程
  build       仅构建 Docker 镜像
  start       启动服务
  stop        停止服务
  restart     重启服务
  logs        查看服务日志
  status      查看服务状态
  down        停止并删除容器（保留数据）
  clean       完全清理（删除容器和卷）
  help        显示帮助信息

示例:
  $0              # 完整安装和启动
  $0 build        # 仅构建镜像
  $0 start        # 启动已存在的服务
  $0 logs         # 查看最新日志
  $0 restart      # 重启服务
EOF
}

# 主函数
main() {
    local command="${1:-setup}"

    case "$command" in
        setup)
            check_prerequisites
            create_directories
            build_image
            start_services
            build_frontend
            show_status
            ;;
        build)
            check_prerequisites
            build_image
            ;;
        start)
            cd "$SCRIPT_DIR"
            docker-compose up -d
            show_status
            ;;
        stop)
            cd "$SCRIPT_DIR"
            docker-compose stop
            print_success "服务已停止"
            ;;
        restart)
            cd "$SCRIPT_DIR"
            docker-compose restart
            print_success "服务已重启"
            show_status
            ;;
        logs)
            cd "$SCRIPT_DIR"
            docker-compose logs -f nassav-api
            ;;
        status)
            show_status
            ;;
        down)
            cd "$SCRIPT_DIR"
            docker-compose down
            print_success "容器已删除（数据已保留）"
            ;;
        clean)
            print_warning "这将删除所有容器和卷中的数据"
            read -p "确定要继续吗？(y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cd "$SCRIPT_DIR"
                docker-compose down -v
                print_success "清理完成"
            fi
            ;;
        help)
            show_help
            ;;
        *)
            print_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
