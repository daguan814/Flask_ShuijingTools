#!/bin/bash

PROJECT_DIR="/shuijing/Flask_ShuijingTools"
CONDA_ENV="flask_env"

cd "$PROJECT_DIR" || exit 1

echo ">>> 拉取最新 GitHub 代码..."
git pull origin main

# 确保环境存在
if ! conda env list | grep -q "^$CONDA_ENV"; then
  echo ">>> 创建 conda 环境: $CONDA_ENV"
  conda create -n "$CONDA_ENV" python=3.10 -y
fi

echo ">>> 使用的 Python:"
conda run -n "$CONDA_ENV" python -V

echo ">>> 安装/更新 Python 依赖（verbose）..."
conda run -n "$CONDA_ENV" pip install -r requirements.txt -v

echo ">>> 启动 Flask 服务..."
conda run -n "$CONDA_ENV" python app.py
