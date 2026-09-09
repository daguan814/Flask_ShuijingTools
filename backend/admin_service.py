import re

from werkzeug.security import check_password_hash, generate_password_hash

from .database import db_manager


class AdminService:
    def _name(self, value):
        name = str(value or "").strip()
        if not re.fullmatch(r"[\w-]{2,64}", name):
            raise ValueError("管理员用户名需为2至64位字母、数字、下划线或短横线")
        return name

    def _password(self, value):
        password = str(value or "")
        if len(password) < 6:
            raise ValueError("密码至少需要6位")
        return password

    def list(self):
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn, dictionary=True)
        cursor.execute("SELECT id,username,status,created_at,updated_at FROM admin_users ORDER BY id")
        rows = [dict(row) for row in cursor.fetchall()]
        cursor.close(); conn.close(); return rows

    def find_by_id(self, admin_id):
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn, dictionary=True); ph = db_manager.placeholder()
        cursor.execute(f"SELECT * FROM admin_users WHERE id={ph}", (admin_id,))
        row = cursor.fetchone(); cursor.close(); conn.close(); return row

    def login(self, username, password):
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn, dictionary=True); ph = db_manager.placeholder()
        cursor.execute(f"SELECT * FROM admin_users WHERE username={ph} AND status='active'", (str(username or "").strip(),))
        row = cursor.fetchone(); cursor.close(); conn.close()
        return row if row and check_password_hash(row["password_hash"], str(password or "")) else None

    def create(self, username, password):
        username, password = self._name(username), self._password(password)
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn); ph = db_manager.placeholder(); now = db_manager.now_expr()
        try:
            cursor.execute(f"INSERT INTO admin_users(username,password_hash,status,created_at,updated_at) VALUES({ph},{ph},'active',{now},{now})", (username, generate_password_hash(password)))
            admin_id = cursor.lastrowid; conn.commit(); return admin_id
        except Exception as exc:
            conn.rollback()
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise ValueError("管理员用户名已存在")
            raise
        finally:
            cursor.close(); conn.close()

    def update(self, admin_id, username=None, password=None, status=None):
        current = self.find_by_id(admin_id)
        if not current: raise ValueError("管理员不存在")
        if status not in {None, "active", "disabled"}: raise ValueError("管理员状态无效")
        if status == "disabled" and current["status"] == "active":
            active = sum(item["status"] == "active" for item in self.list())
            if active <= 1: raise ValueError("不能禁用最后一名正常管理员")
        fields, params = [], []; ph = db_manager.placeholder()
        if username is not None:
            fields.append(f"username={ph}"); params.append(self._name(username))
        if password:
            fields.append(f"password_hash={ph}"); params.append(generate_password_hash(self._password(password)))
        if status is not None:
            fields.append(f"status={ph}"); params.append(status)
        if not fields: return
        conn = db_manager.get_connection(); cursor = db_manager.cursor(conn)
        try:
            params.append(admin_id)
            cursor.execute(f"UPDATE admin_users SET {','.join(fields)},updated_at={db_manager.now_expr()} WHERE id={ph}", tuple(params))
            conn.commit()
        except Exception as exc:
            conn.rollback()
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower(): raise ValueError("管理员用户名已存在")
            raise
        finally:
            cursor.close(); conn.close()


admin_service = AdminService()
