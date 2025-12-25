#!/bin/bash
# Flask_ShuijingTools 启动脚本（容器简化实用版）

PROJECT_DIR="/shuijing/Flask_ShuijingTools"
CONDA_ENV="flask_env"

echo ">>> 切换到项目目录: $PROJECT_DIR"
cd "$PROJECT_DIR" || {
  echo "❌ 项目目录不存在"
  exit 1
}

echo ">>> 拉取最新 GitHub 代码..."
git pull origin main

echo ">>> 安装/更新 Python 依赖..."
conda run -n "$CONDA_ENV" pip install -r requirements.txt

echo ">>> 启动 Flask 服务..."
conda run -n "$CONDA_ENV" python app.py
