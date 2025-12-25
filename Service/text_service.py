import sqlite3
import os
from datetime import datetime


class TextService:
    def __init__(self):
        # 数据库文件路径
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'texts.db')

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def get_all_texts(self):
        """获取所有文本"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM texts ORDER BY created_at DESC')
        texts = c.fetchall()
        conn.close()
        
        # 如果时间已经是本地时间，直接返回
        # 如果是UTC时间，转换为本地时间
        local_texts = []
        for text in texts:
            try:
                # 尝试解析时间
                text_time = text[2]
                # 如果是UTC时间格式，转换为本地时间
                if 'UTC' in text_time or text_time.endswith('Z'):
                    # 处理UTC时间
                    utc_time = datetime.strptime(text_time.replace('Z', ''), '%Y-%m-%d %H:%M:%S')
                    local_time = utc_time.replace(hour=(utc_time.hour + 8) % 24)
                    local_text = (text[0], text[1], local_time.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    # 已经是本地时间，直接使用
                    local_text = text
                local_texts.append(local_text)
            except:
                # 如果时间解析失败，使用原始时间
                local_texts.append(text)
        
        return local_texts

    def add_text(self, content):
        """添加文本"""
        conn = self.get_connection()
        c = conn.cursor()
        # 使用当前本地时间
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO texts (content, created_at) VALUES (?, ?)', (content, local_time))
        conn.commit()
        conn.close()
        return c.lastrowid

    def delete_text(self, text_id):
        """删除文本"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM texts WHERE id = ?', (text_id,))
        conn.commit()
        conn.close()
        return c.rowcount > 0


# 创建全局文本服务实例
text_service = TextService()