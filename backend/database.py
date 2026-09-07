import sqlite3
from datetime import datetime
from pathlib import Path

import mysql.connector
from mysql.connector import pooling

from .config import (
    DB_DRIVER,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    DEFAULT_USERS,
    SQLITE_DB_PATH,
    DEFAULT_QUOTA_BYTES,
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

        self._migrate_accounts(cursor)

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
        cursor.execute(
            "UPDATE storage_users SET group_id = "
            "(SELECT id FROM user_groups WHERE name = " + self.placeholder() + " LIMIT 1) "
            "WHERE group_id IS NULL",
            ("默认组",),
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

    def _column_names(self, cursor, table):
        if self.is_sqlite:
            cursor.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cursor.fetchall()}
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        return {row[0] for row in cursor.fetchall()}

    def _migrate_accounts(self, cursor):
        if self.is_sqlite:
            cursor.execute("""CREATE TABLE IF NOT EXISTS user_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS registration_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
                username TEXT NOT NULL, password_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT NULL)""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS admin_sessions (
                token TEXT PRIMARY KEY, expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            definitions = {
                "group_id": "INTEGER NULL", "password_hash": "TEXT NULL",
                "status": "TEXT NOT NULL DEFAULT 'active'",
                "quota_bytes": f"INTEGER NOT NULL DEFAULT {DEFAULT_QUOTA_BYTES}",
                "deleted_at": "TEXT NULL",
            }
        else:
            cursor.execute("""CREATE TABLE IF NOT EXISTS user_groups (
                id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(64) NOT NULL UNIQUE,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS registration_requests (
                id BIGINT AUTO_INCREMENT PRIMARY KEY, group_id INT NOT NULL,
                username VARCHAR(64) NOT NULL, password_hash VARCHAR(255) NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'pending', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at DATETIME NULL, INDEX idx_registration_status(status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS admin_sessions (
                token VARCHAR(128) PRIMARY KEY, expires_at DATETIME NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            definitions = {
                "group_id": "INT NULL", "password_hash": "VARCHAR(255) NULL",
                "status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
                "quota_bytes": f"BIGINT NOT NULL DEFAULT {DEFAULT_QUOTA_BYTES}",
                "deleted_at": "DATETIME NULL",
            }
        columns = self._column_names(cursor, "storage_users")
        for name, definition in definitions.items():
            if name not in columns:
                cursor.execute(f"ALTER TABLE storage_users ADD COLUMN {name} {definition}")
        insert = "INSERT OR IGNORE INTO user_groups(name) VALUES (?)" if self.is_sqlite else "INSERT IGNORE INTO user_groups(name) VALUES (%s)"
        cursor.execute(insert, ("默认组",))
        cursor.execute("SELECT id FROM user_groups WHERE name = " + self.placeholder(), ("默认组",))
        group_id = cursor.fetchone()[0]
        cursor.execute(
            f"UPDATE storage_users SET group_id = {self.placeholder()} WHERE group_id IS NULL",
            (group_id,),
        )

    def find_user_by_username(self, username: str):
        if not username:
            return None
        ph = self.placeholder()
        conn = self.get_connection()
        cursor = self.cursor(conn, dictionary=True)
        cursor.execute(
            f"SELECT id, username, storage_key, group_id, password_hash, status, quota_bytes FROM storage_users "
            f"WHERE username = {ph} LIMIT 1",
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
            f"SELECT id, username, storage_key, group_id, password_hash, status, quota_bytes FROM storage_users "
            f"WHERE id = {ph} LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row


db_manager = DatabaseManager()
