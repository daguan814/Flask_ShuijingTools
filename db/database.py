import sqlite3
import os


class DatabaseManager:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'texts.db')
        self.init_db()

    def init_db(self):
        """初始化数据库和表结构"""
        # 确保db目录存在
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
                  CREATE TABLE IF NOT EXISTS texts
                  (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      content TEXT NOT NULL,
                      created_at TEXT
                  )
                  ''')
        conn.commit()
        conn.close()

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)


# 创建全局数据库管理器实例
db_manager = DatabaseManager()