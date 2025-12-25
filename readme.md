# 水镜工具集 Flask 项目

## 项目简介
基于 Flask 框架构建的多功能工具平台，集成以下核心功能：
- 📚 单词释义查询系统（支持4万词库检索）
- 📁 文件分享管理系统
- 🔌 ESP设备管理接口
- 🔒 SSL安全通信支持

## 主要功能
### 单词查询
- 静态词库包含 40,000+ 单词条目
- 每个词条独立HTML页面展示
- 响应式布局适配移动端

### 文件分享
- 文件上传/下载管理
- 可视化分享界面
- 安全访问控制

### 设备管理
- ESP设备通信接口
- 设备状态监控
- 指令控制协议

## 技术栈
- **Web框架**: Flask
- **前端**: Bootstrap + 自定义样式
- **部署**: Conda环境管理 + 自动化启动脚本
- **安全**: 自签名SSL证书（位于SSL目录）

## 快速启动
```bash
# 安装依赖
conda create -n flask_env python=3.8
conda activate flask_env
pip install -r requirements.txt

# 启动服务（需先配置SSL证书）
bash run.sh
