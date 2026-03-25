# NASSAV HTTP API Docker 部署快速指南

## 🚀 一键启动

```bash
# 进入项目目录
cd /home/lanpice/NASSAV

# 执行部署脚本（完整初始化）
./deploy.sh

# 或直接使用 docker-compose
docker-compose up -d
```

## 📋 部署步骤

### 第1步：配置
```bash
# 复制配置文件（如果还没有）
cp cfg/configs.json.example cfg/configs.json

# 编辑配置文件
# 重点：修改 SavePath 为你的视频目录位置
nano cfg/configs.json
```

**关键配置项**：
```json
{
    "SavePath": "/vol2/1000/MissAV",    // 视频保存目录
    "Proxy": "http://127.0.0.1:7897",   // 代理地址
    "IsNeedVideoProxy": false             // 是否对视频使用代理
}
```

### 第2步：构建并启动
```bash
# 使用部署脚本（推荐）
./deploy.sh setup

# 或使用 docker-compose
docker-compose build
docker-compose up -d
```

### 第3步：验证服务
```bash
# 查看服务状态
docker-compose ps

# 测试 API
curl http://localhost:31471/api/videos
```

## 🌐 访问方式

| 服务 | 地址 | 说明 |
|-----|------|------|
| **API 服务** | `http://localhost:31471` | HTTP API server |
| **Web 界面** | `http://localhost:5177` | 前端应用（需先构建） |

## 📡 API 调用示例

### 获取视频列表
```bash
curl http://localhost:31471/api/videos
```

### 获取视频详情
```bash
curl http://localhost:31471/api/videos/FPRE-017
```

### 添加下载任务
```bash
curl -X POST http://localhost:31471/api/addvideo/SVGAL-009
```

### 获取视频文件
```bash
curl http://localhost:31471/file/SVGAL-009/SVGAL-009.mp4
```

## � 队列处理机制

Docker 版本包含**自动队列处理**：

- ✅ **每 2 分钟自动检查**下载队列
- ✅ **并发控制**：同时只运行一个下载任务
- ✅ **失败自动重试**：失败任务重新加入队列

**无需手动设置定时任务！**

### 查看队列状态

```bash
# 查看队列内容
docker-compose exec nassav-api cat db/download_queue.txt

# 查看工作状态（0=空闲，1=忙碌）
docker-compose exec nassav-api cat work
```

## �🛠 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 查看日志
docker-compose logs -f nassav-api

# 重启服务
docker-compose restart

# 删除容器（保留数据）
docker-compose down

# 完全清理（删除容器和卷）
docker-compose down -v

# 使用部署脚本
./deploy.sh start      # 启动
./deploy.sh stop       # 停止
./deploy.sh logs       # 查看日志
./deploy.sh status     # 查看状态
./deploy.sh restart    # 重启
./deploy.sh help       # 查看帮助
```

## 🐳 Docker 镜像说明

### Dockerfile.api 包含：
- **Go 运行环境**：用于编译和运行 HTTP API 服务器
- **Python 环境**：用于运行下载管理任务
- **FFmpeg**：视频处理依赖
- **系统工具**：CA 证书等

### 镜像大小
- 基础镜像：Alpine Linux（极小）
- 最终镜像：~500-600 MB

## 📁 数据持久化

所有重要数据都通过 volume 挂载到本地：

```
本地路径          容器路径
./storage      ←→  /vol2/1000/MissAV    (视频)
./db           ←→  /app/db               (数据库)
./logs         ←→  /app/logs             (日志)
./cfg          ←→  /app/cfg              (配置)
```

即使容器删除，数据也会保留在本地。

## 🌟 前端部署（可选）

如果需要 Web 界面：

```bash
# 方式1：使用部署脚本（会自动询问）
./deploy.sh setup

# 方式2：手动构建
cd frontend
npm install
npm run build
cd ..
docker-compose up -d nassav-frontend
```

前端将运行在 `http://localhost:5177`

## 🔧 配置代理

如果需要通过代理下载：

编辑 `docker-compose.yml`：
```yaml
environment:
  HTTP_PROXY: "http://proxy.example.com:7897"
  HTTPS_PROXY: "http://proxy.example.com:7897"
```

## ❌ 故障排除

### 问题：容器立即退出
```bash
# 查看错误日志
docker-compose logs nassav-api
```

### 问题：无法连接 API
```bash
# 检查容器状态
docker-compose ps

# 检查端口占用
netstat -tulpn | grep 31471
```

### 问题：重新构建镜像
```bash
# 清除旧镜像
docker-compose down
docker image prune -a

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

## 📚 更多信息

- 详细部署指南：查看 [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)
- 项目信息：查看 [README.md](README.md)
- 源代码：[GitHub](https://github.com/Satoing/NASSAV)

## 💡 Tips

1. **首次构建较慢**：第一次构建可能需要5-10分钟，后续会使用缓存
2. **磁盘空间**：确保有足够的磁盘空间用于视频存储
3. **代理配置**：如无法访问资源，建议配置代理以提高下载速度
4. **定时更新**：可配置 cron 任务定时添加下载队列和触发下载

---

**快速开始**：
```bash
cd /home/lanpice/NASSAV
cp cfg/configs.json.example cfg/configs.json
./deploy.sh setup
```

然后访问 `http://localhost:31471/api/videos` 验证服务是否正常运行！
