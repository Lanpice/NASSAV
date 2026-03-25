# NASSAV HTTP API 服务器 Docker 部署指南

## 概述

本指南说明如何使用 Docker 构建和部署 NASSAV HTTP API 服务器版本。该部署方案包括：

- **后端 API 服务**：Go 编写的 HTTP 服务器，提供视频管理 API
- **前端 Web 界面**：Vue 构建的前端应用，通过 Nginx 提供
- **下载管理**：支持后台下载管理功能

## 系统要求

- Docker 23.x 或更高版本
- Docker Compose 2.x 或更高版本
- 至少 2GB RAM
- 足够的磁盘空间用于视频存储

## 快速开始

### 1. 前置准备

```bash
# 进入项目目录
cd /home/lanpice/NASSAV

# 复制配置文件（如果还未配置）
cp cfg/configs.json.example cfg/configs.json
```

### 2. 编辑配置文件

编辑 `cfg/configs.json`，配置关键参数：

```json
{
    "LogPath": "./logs",
    "SavePath": "/vol2/1000/MissAV",
    "DBPath": "./db/downloaded.db",
    "QueuePath": "./db/download_queue.txt",
    "Proxy": "http://127.0.0.1:7897",
    "IsNeedVideoProxy": false,
    "Downloader": [
        {"Name": "MissAV", "Priority": 1},
        {"Name": "Jable", "Priority": 2}
    ]
}
```

**重要说明**：
- `SavePath` 映射到容器内的 `/vol2/1000/MissAV`
- 通过 Docker volume 挂载到本地目录 `./storage`

### 3. 构建镜像

```bash
# 方式1：使用 docker-compose（推荐）
docker-compose build

# 方式2：直接使用 docker build
docker build -f Dockerfile.api -t nassav-api:latest .
```

### 4. 启动服务

```bash
# 启动所有服务（API + 前端）
docker-compose up -d

# 或仅启动 API 服务
docker-compose up -d nassav-api
```

### 5. 构建并启动前端（可选）

如果要使用前端 Web 界面：

```bash
# 构建前端静态文件
cd frontend
npm install
npm run build
cd ..

# 启动前端服务
docker-compose up -d nassav-frontend
```

## 访问服务

### API 服务
- **地址**：`http://localhost:31471`
- **API 文档**：
  - 获取视频列表：`GET /api/videos`
  - 获取视频详情：`GET /api/videos/{id}`
  - 添加下载任务：`POST /api/addvideo/{id}`

### 前端 Web 界面
- **地址**：`http://localhost:5177`
- **功能**：浏览视频列表、查看详情、管理下载

## 队列处理机制

Docker 版本的 NASSAV 包含自动队列处理功能：

### 自动处理
- **定时检查**：API 服务器每 30 秒自动检查并处理下载队列
- **并发控制**：确保同时只运行一个下载任务，避免冲突
- **失败重试**：下载失败的任务会重新加入队列等待下次处理

### 添加下载任务

通过 API 添加下载任务最直接的方式：

```bash
# 添加单个视频到队列
curl -X POST http://localhost:31471/api/addvideo/STCV-336
```

### 查看队列状态

```bash
# 查看队列内容
docker-compose exec nassav-api cat db/download_queue.txt

# 查看工作状态（0=空闲，2=队列处理中）
docker-compose exec nassav-api cat work
```

### 示例请求

```bash
# 获取视频列表
curl http://localhost:31471/api/videos

# 获取特定视频详情
curl http://localhost:31471/api/videos/FPRE-017

# 添加下载任务
curl -X POST http://localhost:31471/api/addvideo/SVGAL-009

# 访问视频文件
curl http://localhost:31471/file/SVGAL-009/SVGAL-009.mp4
```

## 目录结构说明

```
NASSAV/
├── Dockerfile.api          # API 服务 Docker 构建文件
├── docker-compose.yml      # Docker 编排配置
├── nginx.conf             # Nginx 反向代理配置
├── cfg/
│   ├── configs.json       # 主配置文件（需修改）
│   └── configs.json.example
├── storage/               # 本地视频存储目录（通过 volume 挂载）
├── db/
│   ├── downloaded.db      # SQLite 数据库
│   └── download_queue.txt # 下载队列
├── logs/                  # 日志目录
├── backend/               # Go API 服务源码
│   ├── main.go
│   └── go.mod
└── frontend/              # Vue 前端源码
    ├── src/
    ├── package.json
    └── vite.config.js
```

## 数据持久化

Docker Compose 配置已设置以下 volume 挂载：

| 容器路径 | 本地路径 | 说明 |
|---------|---------|------|
| `/vol2/1000/MissAV` | `./storage` | 视频存储 |
| `/app/db` | `./db` | 数据库文件 |
| `/app/logs` | `./logs` | 日志文件 |
| `/app/cfg` | `./cfg` | 配置文件 |

所有数据都会持久化到本地磁盘。

## 管理命令

```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f nassav-api

# 重启服务
docker-compose restart

# 停止服务
docker-compose stop

# 启动已停止的服务
docker-compose start

# 完全删除容器和卷
docker-compose down -v
```

## API 详细说明

### 1. 获取视频列表
```
GET /api/videos
```

**响应示例**：
```json
[
  {
    "id": "ACHJ-057",
    "title": "ACHJ-057 時には勝手に痴女りたい…",
    "poster": "/file/ACHJ-057/ACHJ-057-poster.jpg"
  }
]
```

### 2. 获取视频详情
```
GET /api/videos/{id}
```

**例子**：`GET /api/videos/FPRE-017`

**响应示例**：
```json
{
  "id": "FPRE-017",
  "title": "FPRE-017 爆乳セレブ痴女に見つめられて犯●れたい",
  "releaseDate": "2024-02-02",
  "fanarts": [
    "/file/FPRE-017/FPRE-017-fanart-1.jpg",
    "/file/FPRE-017/FPRE-017-fanart-2.jpg"
  ],
  "videoFile": "/file/FPRE-017/FPRE-017.mp4"
}
```

### 3. 添加下载任务
```
POST /api/addvideo/{id}
```

**例子**：`POST /api/addvideo/SVGAL-009`

## 环境变量配置

在 `docker-compose.yml` 中可配置：

```yaml
environment:
  # 代理配置
  HTTP_PROXY: "http://proxy.example.com:7897"
  HTTPS_PROXY: "http://proxy.example.com:7897"
  # 时区
  TZ: Asia/Shanghai
```

## 故障排除

### 1. 容器无法启动
```bash
# 查看详细错误
docker-compose logs nassav-api
```

### 2. 连接被拒绝
- 检查防火墙是否开放了 31471 和 5177 端口
- 检查容器是否正常运行：`docker-compose ps`

### 3. 无法访问视频文件
- 检查 volume 挂载是否正确：`docker inspect nassav-api`
- 确认本地存储目录 `./storage` 中有视频文件

### 4. 重新构建镜像
```bash
# 清除旧镜像并重新构建
docker-compose down
docker image prune -a
docker-compose build --no-cache
docker-compose up -d
```

## 性能优化建议

### 1. 增加系统资源

在 `docker-compose.yml` 中配置资源限制：

```yaml
services:
  nassav-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 2. 启用缓存

Go 服务器每 30 分钟自动更新视频列表缓存。可根据需要在 `backend/main.go` 中修改：

```go
go startCacheUpdater(30 * time.Minute)  // 修改时间间隔
```

### 3. 网络优化

确保 Docker 网络性能良好：
```bash
# 检查网络配置
docker network ls
docker network inspect nassav-network
```

## 安全建议

### 1. 修改 API Key

编辑 `backend/main.go` 中的 apiKey：
```go
const (
    apiKey = "IBHUSDBWQHJEJOBDSW"  // 修改为强密钥
)
```

### 2. 启用反向代理认证

在 `nginx.conf` 中添加认证：
```nginx
location /api {
    auth_basic "NASSAV API";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://nassav-api:31471;
}
```

### 3. 生成 Nginx 密码文件
```bash
docker run --rm httpd:2.4-alpine htpasswd -c .htpasswd username
```

## 更新和维护

### 更新镜像
```bash
# 拉取最新源代码
git pull

# 重新构建镜像
docker-compose build --no-cache

# 重启服务
docker-compose down
docker-compose up -d
```

### 清理磁盘
```bash
# 删除未使用的镜像和卷
docker system prune -a --volumes

# 查看磁盘使用情况
docker system df
```

## 支持和问题反馈

- GitHub Issues：https://github.com/Satoing/NASSAV/issues
- 项目主页：https://github.com/Satoing/NASSAV

## 相关链接

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [Nginx 官方文档](https://nginx.org/en/docs/)
