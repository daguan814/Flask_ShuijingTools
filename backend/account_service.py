import uuid
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from .config import ADMIN_PASSWORD, ADMIN_USERNAME, DEFAULT_QUOTA_BYTES
from .database import db_manager
from .file_service import file_service


class AccountService:
    def _rows(self, sql, params=()):
        conn = db_manager.get_connection()
        cursor = db_manager.cursor(conn, dictionary=True)
        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        cursor.close(); conn.close()
        return rows

    def groups(self):
        return self._rows("SELECT id, name, created_at FROM user_groups ORDER BY name")

    def create_group(self, name):
        name = str(name or "").strip()
        if not name or len(name) > 64:
            raise ValueError("用户组名称不能为空且不能超过64个字符")
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn)
        ph = db_manager.placeholder()
        cursor.execute(f"INSERT INTO user_groups(name) VALUES ({ph})", (name,))
        conn.commit(); group_id = cursor.lastrowid; cursor.close(); conn.close()
        return group_id

    def delete_group(self, group_id):
        ph = db_manager.placeholder(); conn = db_manager.get_connection(); cursor = db_manager.cursor(conn)
        cursor.execute(f"SELECT COUNT(*) FROM storage_users WHERE group_id={ph} AND status!='deleted'", (group_id,))
        if cursor.fetchone()[0]:
            cursor.close(); conn.close(); raise ValueError("该用户组仍有用户，不能删除")
        cursor.execute(f"SELECT COUNT(*) FROM registration_requests WHERE group_id={ph} AND status='pending'", (group_id,))
        if cursor.fetchone()[0]:
            cursor.close(); conn.close(); raise ValueError("该用户组仍有待审核申请，不能删除")
        cursor.execute(f"DELETE FROM user_groups WHERE id={ph}", (group_id,))
        conn.commit(); deleted = cursor.rowcount; cursor.close(); conn.close()
        return bool(deleted)

    def register(self, group_id, username, password):
        username = file_service.normalize_username(username)
        if len(password or "") < 6:
            raise ValueError("密码至少需要6个字符")
        ph = db_manager.placeholder(); conn = db_manager.get_connection(); cursor = db_manager.cursor(conn)
        cursor.execute(f"SELECT id FROM user_groups WHERE id={ph}", (group_id,))
        if not cursor.fetchone():
            cursor.close(); conn.close(); raise ValueError("用户组不存在")
        cursor.execute(f"SELECT id FROM storage_users WHERE username={ph} LIMIT 1", (username,))
        if cursor.fetchone():
            cursor.close(); conn.close(); raise FileExistsError("用户名已存在")
        cursor.execute(f"SELECT id FROM registration_requests WHERE username={ph} AND status='pending' LIMIT 1", (username,))
        if cursor.fetchone():
            cursor.close(); conn.close(); raise FileExistsError("该用户名已有待审核申请")
        now = db_manager.now_expr()
        cursor.execute(
            f"INSERT INTO registration_requests(group_id,username,password_hash,status,created_at) VALUES({ph},{ph},{ph},'pending',{now})",
            (group_id, username, generate_password_hash(password)),
        )
        conn.commit(); request_id = cursor.lastrowid; cursor.close(); conn.close()
        return request_id

    def admin_login(self, username, password):
        if not ADMIN_PASSWORD or username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            return None
        token = uuid.uuid4().hex + uuid.uuid4().hex
        expires = datetime.now() + timedelta(hours=12)
        ph = db_manager.placeholder(); now = db_manager.now_expr()
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn)
        cursor.execute(f"INSERT INTO admin_sessions(token,expires_at,created_at) VALUES({ph},{ph},{now})", (token, expires))
        conn.commit(); cursor.close(); conn.close(); return token

    def is_admin(self, token):
        if not token: return False
        ph = db_manager.placeholder(); now = db_manager.now_expr()
        rows = self._rows(f"SELECT token FROM admin_sessions WHERE token={ph} AND expires_at>{now}", (token,))
        return bool(rows)

    def admin_logout(self, token):
        ph = db_manager.placeholder(); conn = db_manager.get_connection(); cursor = db_manager.cursor(conn)
        cursor.execute(f"DELETE FROM admin_sessions WHERE token={ph}", (token,)); conn.commit(); cursor.close(); conn.close()

    def users(self):
        ph = db_manager.placeholder()
        rows = self._rows("""SELECT u.id,u.username,u.storage_key,u.status,u.quota_bytes,u.created_at,g.name AS group_name,g.id AS group_id
            FROM storage_users u LEFT JOIN user_groups g ON g.id=u.group_id WHERE u.status!='deleted' ORDER BY g.name,u.username""")
        for row in rows:
            usage = file_service.storage_usage(row)
            row.update(used_bytes=usage["used"], used_display=usage["used_display"])
        return rows

    def requests(self):
        return self._rows("""SELECT r.id,r.username,r.group_id,r.status,r.created_at,g.name AS group_name
            FROM registration_requests r JOIN user_groups g ON g.id=r.group_id WHERE r.status='pending' ORDER BY r.id""")

    def create_user(self, group_id, username, password, quota_bytes=DEFAULT_QUOTA_BYTES):
        username = file_service.normalize_username(username)
        if len(password or "") < 6: raise ValueError("密码至少需要6个字符")
        ph = db_manager.placeholder(); now = db_manager.now_expr(); conn=db_manager.get_connection(); cursor=db_manager.cursor(conn)
        cursor.execute(f"SELECT id FROM user_groups WHERE id={ph}", (group_id,))
        if not cursor.fetchone(): cursor.close(); conn.close(); raise ValueError("用户组不存在")
        if int(quota_bytes) < 0: cursor.close(); conn.close(); raise ValueError("额度不能小于0")
        cursor.execute(f"INSERT INTO storage_users(username,storage_key,group_id,password_hash,status,quota_bytes,created_at,updated_at) VALUES({ph},{ph},{ph},{ph},'active',{ph},{now},{now})",
                       (username, username, group_id, generate_password_hash(password), int(quota_bytes)))
        conn.commit(); user_id=cursor.lastrowid; cursor.close(); conn.close()
        user=db_manager.find_user_by_id(user_id); file_service.ensure_user_root(user); return user_id

    def review(self, request_id, approve):
        ph=db_manager.placeholder(); conn=db_manager.get_connection(); cursor=db_manager.cursor(conn, dictionary=True)
        cursor.execute(f"SELECT * FROM registration_requests WHERE id={ph} AND status='pending'", (request_id,)); row=cursor.fetchone()
        if not row: cursor.close(); conn.close(); raise ValueError("申请不存在或已处理")
        if approve:
            now=db_manager.now_expr()
            cursor.execute(f"INSERT INTO storage_users(username,storage_key,group_id,password_hash,status,quota_bytes,created_at,updated_at) VALUES({ph},{ph},{ph},{ph},'active',{ph},{now},{now})",
                           (row["username"],row["username"],row["group_id"],row["password_hash"],DEFAULT_QUOTA_BYTES))
            user_id=cursor.lastrowid; status='approved'
        else: user_id=None; status='rejected'
        cursor.execute(f"UPDATE registration_requests SET status={ph},reviewed_at={db_manager.now_expr()} WHERE id={ph}", (status,request_id))
        conn.commit(); cursor.close(); conn.close()
        if user_id: file_service.ensure_user_root(db_manager.find_user_by_id(user_id))

    def update_user(self, user_id, status=None, quota_bytes=None, password=None, group_id=None):
        ph=db_manager.placeholder(); fields=[]; params=[]
        if status is not None and status not in {"active", "disabled"}: raise ValueError("用户状态无效")
        if quota_bytes is not None and int(quota_bytes) < 0: raise ValueError("额度不能小于0")
        if group_id is not None:
            rows=self._rows(f"SELECT id FROM user_groups WHERE id={ph}", (group_id,))
            if not rows: raise ValueError("用户组不存在")
        for field,value in (("status",status),("quota_bytes",quota_bytes),("group_id",group_id)):
            if value is not None: fields.append(f"{field}={ph}"); params.append(value)
        if password:
            if len(password)<6: raise ValueError("密码至少需要6个字符")
            fields.append(f"password_hash={ph}"); params.append(generate_password_hash(password))
        if not fields: return
        params.append(user_id); conn=db_manager.get_connection(); cursor=db_manager.cursor(conn)
        cursor.execute(f"UPDATE storage_users SET {','.join(fields)} WHERE id={ph} AND status!='deleted'", tuple(params))
        if status == 'disabled': cursor.execute(f"DELETE FROM user_sessions WHERE user_id={ph}", (user_id,))
        conn.commit(); cursor.close(); conn.close()

    def delete_user(self, user_id, confirm_username):
        user=db_manager.find_user_by_id(user_id)
        if not user or user["username"] != confirm_username: raise ValueError("确认用户名不匹配")
        ph=db_manager.placeholder(); conn=db_manager.get_connection(); cursor=db_manager.cursor(conn)
        cursor.execute(f"UPDATE storage_users SET status='deleted',deleted_at={db_manager.now_expr()} WHERE id={ph}", (user_id,))
        cursor.execute(f"DELETE FROM user_sessions WHERE user_id={ph}", (user_id,))
        conn.commit(); cursor.close(); conn.close()


account_service = AccountService()
