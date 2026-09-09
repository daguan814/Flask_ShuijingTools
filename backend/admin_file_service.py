import os
import shutil
from pathlib import Path

from .config import STORAGE_ROOT
from .database import db_manager
from .file_service import file_service


class AdminFileService:
    """Dedicated private storage for administrators and controlled group sharing."""

    def root(self, admin_id):
        root = (STORAGE_ROOT / "管理员文件" / str(int(admin_id))).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _path(self, admin_id, raw_path=""):
        relative = file_service.normalize_relative_path(raw_path)
        root = self.root(admin_id)
        target = (root / relative).resolve() if relative else root
        if target != root and root not in target.parents:
            raise ValueError("路径超出管理员文件目录")
        return target, relative

    def _entry(self, absolute, relative):
        stat = absolute.stat()
        if absolute.is_dir():
            folders = files = 0
            try:
                for child in absolute.iterdir():
                    if child.name == ".DS_Store":
                        continue
                    if child.is_dir():
                        folders += 1
                    elif child.is_file():
                        files += 1
            except OSError:
                pass
            size = file_service._directory_size(absolute)
            content = f"{folders} 个文件夹 · {files} 个文件"
        else:
            size = stat.st_size
            content = "--"
        from datetime import datetime, timezone
        from .file_service import format_size
        return {"name": absolute.name, "path": relative, "type": "folder" if absolute.is_dir() else "file",
                "size": size, "size_display": format_size(size), "content_display": content,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()}

    def list_entries(self, admin_id, path=""):
        target, relative = self._path(admin_id, path)
        if not target.exists() or not target.is_dir():
            raise FileNotFoundError(relative)
        rows = [self._entry(child, f"{relative}/{child.name}".strip("/")) for child in target.iterdir() if child.name != ".DS_Store"]
        rows.sort(key=lambda item: (item["type"] != "folder", file_service._natural_sort_key(item["name"])))
        return {"path": relative, "entries": rows}

    def upload(self, admin_id, parent, uploaded_files, relatives):
        target, parent_rel = self._path(admin_id, parent)
        if not target.exists() or not target.is_dir():
            raise FileNotFoundError(parent_rel)
        results = []
        for storage, raw_name in zip(uploaded_files, relatives):
            name = file_service.normalize_relative_path(raw_name)
            if not name:
                raise ValueError("文件路径无效")
            destination = (target / name).resolve()
            root = self.root(admin_id)
            if root not in destination.parents:
                raise ValueError("路径超出管理员文件目录")
            destination.parent.mkdir(parents=True, exist_ok=True)
            storage.save(str(destination))
            results.append({"path": f"{parent_rel}/{name}".strip("/"), "name": destination.name})
        return results

    def mkdir(self, admin_id, parent, name):
        target, parent_rel = self._path(admin_id, parent)
        if not target.exists() or not target.is_dir():
            raise FileNotFoundError(parent_rel)
        child = (target / file_service.normalize_name(name)).resolve()
        if child.exists():
            raise FileExistsError(child.name)
        child.mkdir()
        return f"{parent_rel}/{child.name}".strip("/")

    def rename(self, admin_id, raw_path, name):
        source, relative = self._path(admin_id, raw_path)
        if not relative or not source.exists():
            raise ValueError("文件不存在或不能重命名根目录")
        target = (source.parent / file_service.normalize_name(name)).resolve()
        if target.exists() and target != source:
            raise FileExistsError(target.name)
        new_relative = str(target.relative_to(self.root(admin_id))).replace("\\", "/")
        source.rename(target)
        self.remove_shares(admin_id, relative, include_children=True)
        return new_relative

    def move(self, admin_id, paths, destination):
        dest, _ = self._path(admin_id, destination)
        if not dest.exists() or not dest.is_dir():
            raise FileNotFoundError(destination)
        moved = []
        for raw_path in paths:
            source, relative = self._path(admin_id, raw_path)
            if not relative or not source.exists():
                raise ValueError("文件不存在或不能移动根目录")
            target = (dest / source.name).resolve()
            if target.exists() and target != source:
                raise FileExistsError(target.name)
            source.rename(target)
            self.remove_shares(admin_id, relative, include_children=True)
            moved.append(str(target.relative_to(self.root(admin_id))).replace("\\", "/"))
        return moved

    def delete(self, admin_id, paths):
        for raw_path in paths:
            target, relative = self._path(admin_id, raw_path)
            if not relative or not target.exists():
                raise ValueError("文件不存在或不能删除根目录")
            self.remove_shares(admin_id, relative, include_children=True)
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

    def target(self, admin_id, raw_path):
        target, relative = self._path(admin_id, raw_path)
        if not relative or not target.exists():
            raise FileNotFoundError(relative)
        return target

    def set_shares(self, admin_id, paths, class_ids):
        if not paths:
            raise ValueError("请选择要共享的文件")
        ids = sorted({int(item) for item in class_ids if str(item).strip()})
        ph = db_manager.placeholder()
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn)
        try:
            for raw_path in paths:
                target, relative = self._path(admin_id, raw_path)
                if not relative or not target.exists():
                    raise FileNotFoundError(relative)
                cursor.execute(f"DELETE FROM admin_file_shares WHERE admin_id={ph} AND relative_path={ph}", (admin_id, relative))
                for class_id in ids:
                    cursor.execute(f"INSERT INTO admin_file_shares(admin_id,relative_path,class_id) VALUES({ph},{ph},{ph})", (admin_id, relative, class_id))
            conn.commit()
        finally:
            cursor.close(); conn.close()

    def remove_shares(self, admin_id, relative, include_children=False):
        ph = db_manager.placeholder(); conn = db_manager.get_connection(); cursor = db_manager.cursor(conn)
        try:
            if include_children:
                cursor.execute(f"DELETE FROM admin_file_shares WHERE admin_id={ph} AND (relative_path={ph} OR relative_path LIKE {ph})", (admin_id, relative, f"{relative}/%"))
            else:
                cursor.execute(f"DELETE FROM admin_file_shares WHERE admin_id={ph} AND relative_path={ph}", (admin_id, relative))
            conn.commit()
        finally:
            cursor.close(); conn.close()

    def shares_for_admin(self, admin_id):
        ph = db_manager.placeholder()
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn, dictionary=True)
        aggregate = "GROUP_CONCAT(c.name, '、')" if db_manager.is_sqlite else "GROUP_CONCAT(c.name ORDER BY c.name SEPARATOR '、')"
        cursor.execute(f"SELECT relative_path,{aggregate} AS group_names FROM admin_file_shares s JOIN school_classes c ON c.id=s.class_id WHERE admin_id={ph} GROUP BY relative_path", (admin_id,))
        rows = cursor.fetchall(); cursor.close(); conn.close()
        return {row["relative_path"]: row["group_names"] for row in rows}

    def share_ids_for_admin(self, admin_id):
        ph = db_manager.placeholder()
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn, dictionary=True)
        cursor.execute(f"SELECT relative_path,class_id FROM admin_file_shares WHERE admin_id={ph}", (admin_id,))
        rows = cursor.fetchall(); cursor.close(); conn.close()
        result = {}
        for row in rows:
            result.setdefault(row["relative_path"], []).append(row["class_id"])
        return result

    def shared_for_user(self, class_id):
        ph = db_manager.placeholder()
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn, dictionary=True)
        cursor.execute(f"SELECT s.id,s.admin_id,s.relative_path,s.created_at,a.username AS admin_name FROM admin_file_shares s JOIN admin_users a ON a.id=s.admin_id WHERE s.class_id={ph} AND a.status='active' ORDER BY s.id DESC", (class_id,))
        rows = cursor.fetchall(); cursor.close(); conn.close()
        items=[]
        for row in rows:
            try:
                target = self.target(row["admin_id"], row["relative_path"])
                item = self._entry(target, row["relative_path"])
                item.update({"share_id":row["id"], "admin_name":row["admin_name"]})
                items.append(item)
            except FileNotFoundError:
                self.remove_shares(row["admin_id"], row["relative_path"])
        return items

    def shared_target(self, share_id, class_id):
        ph = db_manager.placeholder()
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn, dictionary=True)
        cursor.execute(f"SELECT admin_id,relative_path FROM admin_file_shares WHERE id={ph} AND class_id={ph}", (share_id, class_id))
        row = cursor.fetchone(); cursor.close(); conn.close()
        if not row:
            raise FileNotFoundError("共享文件不存在")
        return self.target(row["admin_id"], row["relative_path"])


admin_file_service = AdminFileService()
