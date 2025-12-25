#!/bin/bash
set -e

echo "========================================="
echo ">>> 启动 Flask_ShuijingTools"
echo ">>> 时间: $(date)"
echo "========================================="

# 1️⃣ 进入项目目录
cd /shuijing/Flask_ShuijingTools

# 2️⃣ 激活 conda
echo ">>> 激活 conda 环境"
source /opt/conda/etc/profile.d/conda.sh
conda activate flask_env

# 3️⃣ 当前 conda 环境
echo ">>> 当前 conda 环境: $CONDA_DEFAULT_ENV"

# 4️⃣ 安装 / 更新依赖（日志实时输出）
echo ">>> 安装 / 更新 Python 依赖（实时日志）"
pip install --no-cache-dir -r requirements.txt

# 5️⃣ 启动 Flask（日志直出，不缓冲）
echo ">>> 启动 Flask 服务（日志实时输出）"
export PYTHONUNBUFFERED=1
exec python app.py
