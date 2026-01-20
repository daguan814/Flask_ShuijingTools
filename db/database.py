import mysql.connector
from mysql.connector import pooling


class DatabaseManager:
    def __init__(self):
        self.host = "172.17.0.1"
        self.user = "root"
        self.password = "Lhf134652"
        self.database = "shuijingTools"
        self._pool = None

    def init_db(self):
        """Initialize database and schema."""
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                connection_timeout=5
            )
            c = conn.cursor()

            c.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            conn.commit()
            conn.close()

            conn = self.get_connection()
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS texts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at DATETIME,
                    is_active TINYINT(1) NOT NULL DEFAULT 1
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    action VARCHAR(32) NOT NULL,
                    text_id INT NULL,
                    content TEXT NULL,
                    client_ip VARCHAR(45) NULL,
                    created_at DATETIME
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS file_trash (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    original_path TEXT NOT NULL,
                    trash_path TEXT NOT NULL,
                    size BIGINT NOT NULL,
                    deleted_at DATETIME
                )
                """
            )
            conn.commit()
            c.execute(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'texts' AND COLUMN_NAME = 'is_active'
                """,
                (self.database,)
            )
            if c.fetchone()[0] == 0:
                c.execute("ALTER TABLE texts ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1")
                c.execute("UPDATE texts SET is_active = 1 WHERE is_active IS NULL")
            conn.close()
            print("MySQL database initialized")
        except Exception as e:
            print(f"Database init failed: {e}")

    def init_pool(self, pool_size=5):
        """Initialize a small connection pool for faster remote requests."""
        self._pool = pooling.MySQLConnectionPool(
            pool_name="shuijing_pool",
            pool_size=pool_size,
            pool_reset_session=True,
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            connection_timeout=5
        )

    def get_connection(self):
        """Get database connection."""
        if self._pool is None:
            self.init_pool()
        return self._pool.get_connection()


db_manager = DatabaseManager()
