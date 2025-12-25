#!/bin/bash
# Flask_ShuijingTools 启动脚本（容器可用简化版）

PROJECT_DIR="/shuijing/Flask_ShuijingTools"
CONDA_ENV="flask_env"

echo ">>> 切换到项目目录: $PROJECT_DIR"
cd "$PROJECT_DIR" || {
  echo "❌ 项目目录不存在"
  exit 1
}

echo ">>> 拉取最新 GitHub 代码..."
git pull origin main

echo ">>> 使用 conda 环境启动 Flask: $CONDA_ENV"
echo "------------------------------------------"

conda run -n "$CONDA_ENV" python app.py
