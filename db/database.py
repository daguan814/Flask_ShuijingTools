import mysql.connector
import os


class DatabaseManager:
    def __init__(self):
        self.host = "192.168.100.242"
        self.user = "root"
        self.password = "Lhf134652"
        self.database = "shuijingTools"
        self.init_db()

    def init_db(self):
        """初始化数据库和表结构"""
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            c = conn.cursor()
            
            # 创建数据库（如果不存在）
            c.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            conn.commit()
            conn.close()
            
            # 连接到具体数据库并创建表
            conn = self.get_connection()
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS texts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at DATETIME
                )
            ''')
            conn.commit()
            conn.close()
            print("MySQL数据库初始化成功")
        except Exception as e:
            print(f"数据库初始化失败: {e}")

    def get_connection(self):
        """获取数据库连接"""
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )


# 创建全局数据库管理器实例
db_manager = DatabaseManager()