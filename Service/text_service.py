import mysql.connector
import os
from datetime import datetime


class TextService:
    def __init__(self):
        self.host = "192.168.100.242"
        self.user = "root"
        self.password = "Lhf134652"
        self.database = "shuijingTools"

    def get_connection(self):
        """获取数据库连接"""
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def get_all_texts(self):
        """获取所有文本"""
        conn = self.get_connection()
        c = conn.cursor(dictionary=True)
        c.execute('SELECT * FROM texts ORDER BY created_at DESC')
        texts = c.fetchall()
        conn.close()
        
        # 转换结果为元组格式以保持兼容性
        result = []
        for text in texts:
            result.append((text['id'], text['content'], text['created_at']))
        
        return result

    def add_text(self, content):
        """添加文本"""
        conn = self.get_connection()
        c = conn.cursor()
        # 使用当前本地时间
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO texts (content, created_at) VALUES (%s, %s)', (content, local_time))
        conn.commit()
        text_id = c.lastrowid
        conn.close()
        return text_id

    def delete_text(self, text_id):
        """删除文本"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM texts WHERE id = %s', (text_id,))
        conn.commit()
        affected_rows = c.rowcount
        conn.close()
        return affected_rows > 0


# 创建全局文本服务实例
text_service = TextService()