import sqlite3
from datetime import datetime
from pathlib import Path

import mysql.connector
from mysql.connector import pooling
from werkzeug.security import generate_password_hash

from .config import (
    DB_DRIVER,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    DEFAULT_USERS,
    SQLITE_DB_PATH,
)


class DatabaseManager:
    """Database manager supporting MySQL (default) and SQLite for local preview."""

    def __init__(self):
        self.driver = DB_DRIVER
        self.sqlite_path = Path(SQLITE_DB_PATH)
        self._pool = None

    @property
    def is_sqlite(self) -> bool:
        return self.driver == "sqlite"

    def placeholder(self) -> str:
        return "?" if self.is_sqlite else "%s"

    def now_expr(self) -> str:
        return "CURRENT_TIMESTAMP" if self.is_sqlite else "NOW()"

    def cursor(self, conn, dictionary=False):
        if self.is_sqlite:
            return conn.cursor()
        return conn.cursor(dictionary=dictionary)

    def init_pool(self, pool_size=5):
        if self.is_sqlite:
            return None
        if self._pool is not None:
            return self._pool
        self._pool = pooling.MySQLConnectionPool(
            pool_name="shuijing_storage_pool",
            pool_size=pool_size,
            pool_reset_session=True,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connection_timeout=5,
        )
        return self._pool

    def get_connection(self):
        if self.is_sqlite:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.sqlite_path), timeout=10)
            conn.row_factory = sqlite3.Row
            return conn
        return self.init_pool().get_connection()

    def _create_database(self):
        if self.is_sqlite:
            return
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            connection_timeout=5,
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cursor.close()
        conn.close()

    def init_db(self):
        """Create the database, users, and session tables."""
        self._create_database()
        conn = self.get_connection()
        cursor = conn.cursor()

        if self.is_sqlite:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS storage_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    storage_key TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT NOT NULL,
                    last_seen_at TEXT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id
                ON user_sessions (user_id)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_logs_user_id
                ON user_logs (user_id)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recycle_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    original_path TEXT NOT NULL,
                    stored_name TEXT NOT NULL UNIQUE,
                    item_name TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    deleted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_recycle_items_user_id
                ON recycle_items (user_id)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS login_attempts (
                    device_key TEXT PRIMARY KEY,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    blocked_until TEXT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS storage_users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(64) NOT NULL UNIQUE,
                    storage_key VARCHAR(64) NOT NULL UNIQUE,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    token VARCHAR(128) PRIMARY KEY,
                    user_id INT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    last_seen_at DATETIME NULL,
                    INDEX idx_user_sessions_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_logs_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recycle_items (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    original_path VARCHAR(2048) NOT NULL,
                    stored_name VARCHAR(128) NOT NULL UNIQUE,
                    item_name VARCHAR(512) NOT NULL,
                    item_type VARCHAR(16) NOT NULL,
                    deleted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_recycle_items_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS login_attempts (
                    device_key VARCHAR(64) PRIMARY KEY,
                    failed_count INT NOT NULL DEFAULT 0,
                    blocked_until DATETIME NULL,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )

        self._init_school_schema(cursor)
        self._init_admin_schema(cursor)
        self._init_admin_file_schema(cursor)

        # 从原来的环境变量管理员平滑迁移：仅在管理员不存在时创建，绝不覆盖
        # 已在数据库中修改过的管理员密码或状态。
        if ADMIN_USERNAME and ADMIN_PASSWORD:
            ph = self.placeholder()
            cursor.execute(f"SELECT id FROM admin_users WHERE username={ph}", (ADMIN_USERNAME,))
            if not cursor.fetchone():
                now_expr = self.now_expr()
                cursor.execute(
                    f"INSERT INTO admin_users(username,password_hash,status,created_at,updated_at) "
                    f"VALUES({ph},{ph},'active',{now_expr},{now_expr})",
                    (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD)),
                )

        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        insert_sql = (
            """
            INSERT OR IGNORE INTO storage_users
                (username, storage_key, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """
            if self.is_sqlite
            else """
            INSERT IGNORE INTO storage_users
                (username, storage_key, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            """
        )
        for username in DEFAULT_USERS:
            storage_key = username
            cursor.execute(insert_sql, (username, storage_key, now, now))

        ph = self.placeholder()
        cursor.execute(f"SELECT id FROM school_classes WHERE name={ph}", ("111",))
        legacy_group = cursor.fetchone()
        # 仅在历史默认组仍存在时迁移未归组的旧账号；不能再自动重建 111。
        if legacy_group:
            class_id = legacy_group[0]
            cursor.execute(
                f"UPDATE storage_users SET class_id={ph}, status='password_required' WHERE class_id IS NULL",
                (class_id,),
            )

        conn.commit()
        cursor.close()
        conn.close()

        # Ensure every configured user has a storage directory.
        from .file_service import file_service

        for username in DEFAULT_USERS:
            user = self.find_user_by_username(username)
            if user:
                file_service.ensure_user_root(user)

        # 管理员个人文件使用独立目录。启动时为既有管理员补齐目录，
        # 不依赖用户第一次打开页面或第一次上传时才创建。
        from .admin_file_service import admin_file_service
        conn = self.get_connection()
        cursor = self.cursor(conn, dictionary=True)
        cursor.execute("SELECT id FROM admin_users")
        admin_rows = cursor.fetchall()
        cursor.close()
        conn.close()
        for admin in admin_rows:
            admin_file_service.root(admin["id"])

    def _columns(self, cursor, table):
        if self.is_sqlite:
            cursor.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cursor.fetchall()}
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        return {row[0] for row in cursor.fetchall()}

    def _init_school_schema(self, cursor):
        if self.is_sqlite:
            cursor.execute("""CREATE TABLE IF NOT EXISTS school_classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
                storage_key TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS registration_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER NOT NULL,
                username TEXT NOT NULL, password_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT NULL)""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER NOT NULL,
                title TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS student_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'unread',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            definitions={"class_id":"INTEGER NULL","password_hash":"TEXT NULL","status":"TEXT NOT NULL DEFAULT 'active'","deleted_at":"TEXT NULL"}
            insert="INSERT OR IGNORE INTO school_classes(name,storage_key) VALUES (?,?)"
        else:
            cursor.execute("""CREATE TABLE IF NOT EXISTS school_classes (
                id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(64) NOT NULL UNIQUE,
                storage_key VARCHAR(64) NOT NULL UNIQUE, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS registration_requests (
                id BIGINT AUTO_INCREMENT PRIMARY KEY, class_id INT NOT NULL,
                username VARCHAR(64) NOT NULL, password_hash VARCHAR(255) NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'pending', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at DATETIME NULL, INDEX idx_registration_status(status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS announcements (
                id BIGINT AUTO_INCREMENT PRIMARY KEY, class_id INT NOT NULL,
                title VARCHAR(160) NOT NULL, content TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, INDEX idx_announcement_class(class_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS student_reports (
                id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
                content TEXT NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'unread',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, INDEX idx_report_user(user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            definitions={"class_id":"INT NULL","password_hash":"VARCHAR(255) NULL","status":"VARCHAR(24) NOT NULL DEFAULT 'active'","deleted_at":"DATETIME NULL"}
            insert="INSERT IGNORE INTO school_classes(name,storage_key) VALUES (%s,%s)"
        columns=self._columns(cursor,"storage_users")
        for name,definition in definitions.items():
            if name not in columns:
                cursor.execute(f"ALTER TABLE storage_users ADD COLUMN {name} {definition}")

    def _init_admin_schema(self, cursor):
        if self.is_sqlite:
            cursor.execute("""CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
        else:
            cursor.execute("""CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(64) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'active',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")

    def _init_admin_file_schema(self, cursor):
        """Share records for files owned by an administrator.

        Files themselves stay in the dedicated administrator storage directory; this
        table only controls which user groups can download each item.
        """
        if self.is_sqlite:
            cursor.execute("""CREATE TABLE IF NOT EXISTS admin_file_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                relative_path TEXT NOT NULL,
                class_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(admin_id, relative_path, class_id)
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_file_shares_class ON admin_file_shares(class_id)")
        else:
            cursor.execute("""CREATE TABLE IF NOT EXISTS admin_file_shares (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                admin_id INT NOT NULL,
                relative_path VARCHAR(512) NOT NULL,
                class_id INT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_admin_file_share (admin_id, relative_path, class_id),
                INDEX idx_admin_file_shares_class (class_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")

    def find_user_by_username(self, username: str):
        if not username:
            return None
        ph = self.placeholder()
        conn = self.get_connection()
        cursor = self.cursor(conn, dictionary=True)
        cursor.execute(
            f"SELECT u.id,u.username,u.storage_key,u.class_id,u.password_hash,u.status,c.name AS class_name,c.storage_key AS class_storage_key FROM storage_users u JOIN school_classes c ON c.id=u.class_id "
            f"WHERE u.username = {ph} LIMIT 1",
            (username,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    def find_user_by_id(self, user_id: int):
        ph = self.placeholder()
        conn = self.get_connection()
        cursor = self.cursor(conn, dictionary=True)
        cursor.execute(
            f"SELECT u.id,u.username,u.storage_key,u.class_id,u.password_hash,u.status,c.name AS class_name,c.storage_key AS class_storage_key FROM storage_users u JOIN school_classes c ON c.id=u.class_id "
            f"WHERE u.id = {ph} LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row


db_manager = DatabaseManager()
