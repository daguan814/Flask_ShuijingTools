# 部署说明

> 重要：更新代码时绝对不要删除以下目录：
>
> ```text
> /vol2/1000/backup/ShuijingTools/storage
> /vol2/1000/backup/docker/mysql
> ```
>
> 这两个目录分别保存用户文件和 MySQL 数据。

当前部署目标：

- 服务器：`shuijing.site`
- SSH 端口：`12222`
- 部署目录：`/vol2/1000/backup/ShuijingTools`
- 后端：`systemd` 服务 `shuijing-tools.service`，监听 `127.0.0.1:18080`
- 前端：由 `shuijing-nginx` 容器提供，挂载目录 `frontend`
- 对外入口：`https://shuijing.site:8080`
- 敏感配置：项目根目录 `.env`，权限必须为 `600`，禁止提交 Git

## 更新后端

只同步代码，不使用 `--delete`：

```bash
rsync -az --exclude='__pycache__' --exclude='*.pyc' \
  backend requirements.txt readme.md \
  shuijing@shuijing.site:/vol2/1000/backup/ShuijingTools/

ssh -p 12222 shuijing@shuijing.site \
  'sudo systemctl restart shuijing-tools.service'
```

## 更新前端

只同步 `frontend` 目录，不要动 `storage` 和 `docker/mysql`：

```bash
rsync -az --exclude='.DS_Store' frontend \
  shuijing@shuijing.site:/vol2/1000/backup/ShuijingTools/
```

## Nginx

配置文件位于：

```text
deploy/nginx/conf.d/shuijing.site.conf
```

前端挂载到容器内的 `/srv/frontend`，`/api/` 反向代理到 `127.0.0.1:18080`。

如果修改了 Nginx 配置，需要让容器重新加载：

```bash
ssh -p 12222 shuijing@shuijing.site \
  'docker exec shuijing-nginx nginx -s reload'
```

## kkFileView 文件预览

管理员端的“用户组文件”和“个人文件”使用 kkFileView 预览；普通用户端不提供预览。

- 容器名称：`shuijing-kkfileview`
- 镜像：`keking/kkfileview:latest`
- 仅监听服务器本机：`127.0.0.1:8012`
- 公网入口：Nginx 的 `/kk/` 反向代理；不要直接暴露 `8012` 端口。
- 后端通过 10 分钟有效的单文件预览票据向 kkFileView 提供文件；不要改成公开存储路径或长期链接。

容器回源时必须把 `shuijing.site` 映射到 Docker 宿主机网关，否则服务器外网回环可能出现 `Connection reset`。创建或重建容器时保留以下关键参数：

```bash
docker run -d --name shuijing-kkfileview --restart unless-stopped \
  --add-host shuijing.site:host-gateway \
  -p 127.0.0.1:8012:8012 \
  -e KK_BASE_URL=https://shuijing.site:8080/kk \
  -e KK_TRUST_HOST=shuijing.site \
  -e KK_NOT_TRUST_HOST=localhost,127.0.0.1,10.*,172.16.*,169.254.* \
  -e KK_FILE_UPLOAD_DISABLE=true -e KK_ADD_TASK=false \
  keking/kkfileview:latest
```

修改 `/kk/` 的 Nginx 配置后需要热加载 Nginx；修改 `backend/preview_service.py`、`backend/app.py` 或预览路由后需要重启 `shuijing-tools.service`。

## 回滚

部署前备份位于服务器：

```text
/vol2/1000/backup/ShuijingTools_backup_*
```

包含旧 `app/`、`vue/`、`deploy/`、`readme.md`、`requirements.txt` 和旧的
`shuijing-tools.service`。
