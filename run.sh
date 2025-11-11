#!/bin/bash
# =========================================
# Flask_ShuijingTools 自动部署启动脚本
# 作者：shuijing
# =========================================

# 1. 设置基础变量
PROJECT_DIR="/shuijing/Flask_ShuijingTools"
LOG_FILE="/shuijing/flask_app.log"
CONDA_ENV="flask_env"

# 2. 切换到项目目录
echo ">>> 切换到项目目录: $PROJECT_DIR"
cd $PROJECT_DIR || { echo "❌ 目录不存在"; exit 1; }

# 3. 激活 conda 环境
echo ">>> 激活 conda 环境: $CONDA_ENV"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate $CONDA_ENV

# 4. 拉取最新代码
echo ">>> 拉取最新 GitHub 代码..."
git fetch origin
git pull origin main || git pull origin master


# 6. 启动服务（后台运行并记录日志）
echo ">>> 启动 Flask 项目..."
python app.py

# 7. 显示运行状态
echo "✅ Flask 项目已启动！"

