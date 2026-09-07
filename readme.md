# 水镜云盘（ShuijingTools）

面向教学场景的轻量云盘，采用 Flask、MySQL 和原生 HTML/CSS/JavaScript 构建。系统按“管理员 → 班级 → 学生”组织：学生保存课堂文件，管理员管理班级、账号、文件、公告和学习汇报。



## 功能

- 学生注册时选择班级，填写姓名、密码和确认密码，审核通过后才能登录；
- 学生按班级和姓名隔离存储，目录结构为 `storage/<班级>/<学生姓名>/`；
- 管理员后台位于 `/admin/`，可以新增、改名和删除空班级；
- 管理员可以审核注册、修改学生姓名/班级/密码、禁用账号，并谨慎删除学生；
- 管理员改名或转班时，对应文件目录同步移动；
- 管理员可以进入任意学生目录，浏览、上传、新建、重命名、移动、删除和下载文件；
- 管理员可以按班级发布公告，学生可以向管理员提交学习汇报；
- 浏览目录、查看修改时间和普通文件大小；
- 文件夹显示直接下一层的文件夹数、文件数以及全部内容总大小；
- 上传单个文件、多个文件或完整文件夹；
- 支持拖放上传并保留目录结构；
- 新建文件夹、单项重命名、批量移动和批量删除；
- 文件列表较长时，路径、上传和批量操作工具栏会固定在页面顶部；
- 学生删除内容后进入 `storage/回收站/` 下的统一回收站，只有管理员可以恢复；
- 常见图片、文档、文本、音视频文件在线预览；
- 单个文件使用浏览器原生下载，支持条件请求和 Range；
- 多文件或文件夹在服务器临时生成 ZIP 后下载；
- 文件操作日志统一在管理后台查看，可按班级、学生、日期与操作类型组合筛选，并支持统计和分页；
- 班级与学生在同一页面按班级折叠展示，注册审核、学生汇报和公告发布集中在消息中心；
- 同一浏览器连续登录失败5次后锁定5小时；
- 显示用户已用空间和服务器磁盘容量。

现有账号升级时统一归入默认班级 `111`。由于旧账号没有密码，迁移后状态为“待设置密码”，管理员设置密码后即可启用。

## 目录结构

```text
.
├── backend/                       Flask API
│   ├── app.py                     应用、中间件、CORS 和预览入口
│   ├── config.py                  环境配置
│   ├── database.py                MySQL/SQLite 初始化和查询
│   ├── auth_service.py            登录会话
│   ├── file_service.py            文件隔离、路径校验和 ZIP 生成
│   ├── log_service.py             用户文件操作日志
│   ├── recycle_service.py         统一回收站移动与管理员恢复
│   ├── school_service.py          班级、注册、学生、公告和汇报
│   ├── routes/                    API 路由
│   └── storage/                   本地预览存储（生产环境不使用）
├── frontend/                      学生端和 `/admin/` 管理端
├── deploy/                        Nginx、systemd 和部署说明
├── tests/                         集成测试
├── .env.example                   环境变量示例
└── requirements.txt               固定版本的 Python 依赖
```

## 存储模型

生产文件保存在：

```text
/vol2/1000/backup/ShuijingTools/storage/<班级>/<学生姓名>/
```

例如：

```text
storage/
├── 111/
│   ├── shuijing/
│   └── stu_203/
└── 回收站/
    └── 111/
```

班级名和学生姓名最长64个字符，不允许斜杠、控制字符、`.` 或 `..`。学生姓名可使用中文、字母、数字、下划线和短横线。后端会校验所有相对路径，拒绝绝对路径、`..` 和逃逸学生目录的访问。

文件夹大小不在目录列表中实时计算，以免递归扫描大量文件导致页面卡顿；普通文件仍显示实际大小。

## 下载机制

下载分为两步：

1. 前端携带登录令牌调用 `/api/files/download/prepare`；
2. 后端返回5分钟有效的签名下载链接，浏览器使用原生下载访问该链接。

只选择一个普通文件时直接返回原文件。选择多个项目或文件夹时，后端在系统临时目录生成 ZIP，响应结束后自动删除临时文件。这避免了旧版本在服务器和浏览器中同时保存数百 MB Blob 的问题。

前端 JS/CSS 使用版本参数并由 Nginx 设置重新验证缓存，部署新版本后不会继续调用已删除的旧接口。

## 本地开发

### 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 使用 SQLite 启动后端

```bash
DB_DRIVER=sqlite \
SQLITE_DB_PATH=/tmp/shuijingtools_preview.db \
STORAGE_ROOT=/tmp/shuijingtools_preview_storage \
SECRET_KEY=local-development-secret \
FLASK_DEBUG=1 \
python3 -m backend.app
```

### 启动前端

```bash
python3 -m http.server 5173 -d frontend
```

浏览器打开 `http://127.0.0.1:5173`。前端会请求 `http://127.0.0.1:8080` 的本地 API。

## 环境变量

复制 `.env.example` 并填写生产值。真实 `.env` 已被 Git 忽略，权限应设置为 `600`。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DB_HOST` | `127.0.0.1` | 数据库地址 |
| `DB_PORT` | `3306` | 数据库端口 |
| `DB_USER` | `root` | 数据库用户，生产环境应使用专用账户 |
| `DB_PASSWORD` | 空 | 数据库密码 |
| `DB_NAME` | `shuijingTools` | 数据库名称 |
| `DB_DRIVER` | `mysql` | `mysql` 或 `sqlite` |
| `SQLITE_DB_PATH` | `backend/shuijingtools.db` | SQLite 文件位置 |
| `APP_HOST` | `0.0.0.0` | 开发服务器监听地址 |
| `APP_PORT` | `8080` | 开发服务器端口 |
| `STORAGE_ROOT` | `backend/storage` | 用户文件根目录 |
| `RECYCLE_ROOT` | `STORAGE_ROOT/回收站` | 统一回收站文件根目录 |
| `ADMIN_USERNAME` | `shuijing` | 管理员账号 |
| `ADMIN_PASSWORD` | 空 | 管理员密码，生产环境必须配置 |
| `MAX_CONTENT_LENGTH` | `10737418240` | 单次请求最大10GB |
| `SECRET_KEY` | 无安全默认值 | 生产签名密钥，必须配置 |
| `ALLOWED_ORIGINS` | `http://127.0.0.1:5173` | 逗号分隔的 CORS 来源 |

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/auth/classes` | 注册和登录可选择的班级 |
| `POST` | `/api/auth/register` | 提交学生注册申请 |
| `POST` | `/api/auth/login` | 使用班级、姓名和密码登录 |
| `GET` | `/api/auth/me` | 当前用户和容量信息 |
| `POST` | `/api/auth/logout` | 注销当前会话 |
| `GET` | `/api/files?path=` | 列出目录 |
| `POST` | `/api/files/upload` | 上传文件或文件夹 |
| `POST` | `/api/files/mkdir` | 新建文件夹 |
| `POST` | `/api/files/move` | 批量移动 |
| `POST` | `/api/files/rename` | 重命名单个文件或文件夹 |
| `POST` | `/api/files/delete` | 删除单个路径 |
| `POST` | `/api/files/batch-delete` | 批量删除 |
| `POST` | `/api/files/download/prepare` | 生成短期下载链接 |
| `GET` | `/api/files/download/ticket/<ticket>` | 下载原文件或 ZIP |
| `GET` | `/api/files/download?path=` | 直接下载接口 |
| `GET` | `/api/files/preview?path=` | API 内联预览 |
| `POST` | `/api/files/preview/start` | 创建预览会话 |
| `GET` | `/preview/<path>` | 使用预览会话打开文件 |
| `GET` | `/api/auth/announcements` | 当前班级公告 |
| `POST` | `/api/auth/reports` | 向管理员提交汇报 |
| `POST` | `/api/admin/login` | 管理员登录 |
| `GET` | `/api/admin/overview` | 班级、学生、申请和汇报总览 |
| `GET` | `/api/admin/logs` | 管理员统一查询全部学生操作日志 |
| `POST/PATCH/DELETE` | `/api/admin/classes...` | 管理班级及联动目录 |
| `POST` | `/api/admin/requests/<id>/review` | 审核注册申请 |
| `PATCH/DELETE` | `/api/admin/students/<id>` | 管理学生及联动目录 |
| `GET/POST` | `/api/admin/students/<id>/...` | 管理学生文件 |
| `GET` | `/api/admin/recycle` | 查看统一回收站 |
| `POST` | `/api/admin/recycle/<id>/restore` | 管理员恢复文件 |

除健康检查、登录和签名下载链接外，API 需要：

```http
Authorization: Bearer <token>
```

## 测试

```bash
SECRET_KEY=test-secret \
DB_DRIVER=sqlite \
SQLITE_DB_PATH=/tmp/shuijingtools_test.db \
STORAGE_ROOT=/tmp/shuijingtools_test_storage \
python -m unittest discover -s tests -v
```

测试覆盖注册审核、密码登录、班级/学生目录、文件上传、公告、汇报、统一回收站恢复，以及学生改名和转班的目录联动。

## 生产部署

生产环境由以下组件组成：

- Nginx 容器 `shuijing-nginx`：TLS、静态前端和反向代理；
- systemd 服务 `shuijing-tools.service`：运行两个 Gunicorn worker；
- MySQL 容器：保存用户、会话和文件操作日志；
- `storage/`：保存按班级和学生划分的真实文件，以及其中的统一回收站。
- 旧的 `recycle_bin/` 仅用于迁移前历史数据，迁移后不再写入。

后端与 Nginx 的长请求超时均为600秒。完整更新命令和回滚说明见 `deploy/README.md`。

## 数据安全

以下生产目录是持久化数据，部署或清理代码时绝对不能删除：

```text
/vol2/1000/backup/ShuijingTools/storage
/vol2/1000/backup/ShuijingTools/recycle_bin
/vol2/1000/backup/docker/mysql
```

同时谨慎处理：

```text
/vol2/1000/backup/ShuijingTools/deploy/nginx/certs
/vol2/1000/backup/ShuijingTools/logs
```

不要在生产项目根目录运行 `git clean -fdx`，也不要对整个项目根目录使用 `rsync --delete`。数据库结构变更前应先导出数据库或创建数据快照。
