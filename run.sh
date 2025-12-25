#!/bin/bash
# =========================================
# Flask_ShuijingTools 自动部署启动脚本
# 作者：shuijing
# =========================================

set -e   # 任意一步失败，直接退出（非常重要）

# 1. 基础变量
PROJECT_DIR="/shuijing/Flask_ShuijingTools"
CONDA_ENV="flask_env"
LOG_FILE="/shuijing/flask_app.log"

echo "========================================="
echo ">>> 启动 Flask_ShuijingTools"
echo ">>> 时间: $(date)"
echo "========================================="

# 2. 进入项目目录
echo ">>> 切换到项目目录: $PROJECT_DIR"
cd "$PROJECT_DIR" || {
  echo "❌ 项目目录不存在，退出"
  exit 1
}

# 3. 拉取最新代码
echo ">>> 拉取最新 GitHub 代码..."
git fetch origin

# 自动识别 main / master
BRANCH=$(git symbolic-ref --short HEAD)
echo ">>> 当前分支: $BRANCH"

git pull origin "$BRANCH"

# 4. （可选）安装依赖 —— 建议只在首次或你明确需要时打开
# echo ">>> 安装 Python 依赖..."
# conda run -n "$CONDA_ENV" pip install -r requirements.txt

# 5. 启动 Flask 服务
echo ">>> 启动 Flask 服务..."
echo ">>> 使用 conda 环境: $CONDA_ENV"

exec conda run -n "$CONDA_ENV" python app.py >> "$LOG_FILE" 2>&1
