#!/bin/bash
set -e

echo "========================================="
echo ">>> 启动 Flask_ShuijingTools（容器内）"
echo ">>> 时间: $(date)"
echo "========================================="

# 1️⃣ 进入项目目录
cd /shuijing/Flask_ShuijingTools

# 2️⃣ 拉取 GitHub 最新代码
echo ">>> 拉取 GitHub 最新代码..."
git fetch origin

BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo ">>> 当前分支: $BRANCH"

git pull origin "$BRANCH"

# 3️⃣ 激活 conda
echo ">>> 激活 conda 环境"
source /opt/miniconda/etc/profile.d/conda.sh
conda activate flask_env

# 4️⃣ 明确当前 conda 环境
echo ">>> 当前 conda 环境: $CONDA_DEFAULT_ENV"

# 5️⃣ 安装 / 更新依赖（实时日志）
echo ">>> 安装 / 更新 Python 依赖（实时日志）"
pip install --no-cache-dir -r requirements.txt

# 6️⃣ 启动 Flask（前台 + 日志直出）
echo ">>> 启动 Flask 服务（日志实时输出）"
export PYTHONUNBUFFERED=1
exec python app.py
