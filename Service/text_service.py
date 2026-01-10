from datetime import datetime
from db.database import db_manager


class TextService:
    def __init__(self):
        pass

    def get_connection(self):
        """Get database connection from db_manager."""
        return db_manager.get_connection()

    def get_all_texts(self):
        """Get all saved texts."""
        conn = self.get_connection()
        c = conn.cursor(dictionary=True)
        c.execute('SELECT * FROM texts ORDER BY created_at DESC')
        texts = c.fetchall()
        conn.close()

        result = []
        for text in texts:
            result.append((text['id'], text['content'], text['created_at']))

        return result

    def add_text(self, content):
        """Add new text."""
        conn = self.get_connection()
        c = conn.cursor()
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO texts (content, created_at) VALUES (%s, %s)', (content, local_time))
        conn.commit()
        text_id = c.lastrowid
        conn.close()
        return text_id

    def delete_text(self, text_id):
        """Delete a text."""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM texts WHERE id = %s', (text_id,))
        conn.commit()
        affected_rows = c.rowcount
        conn.close()
        return affected_rows > 0

    def add_log(self, action, text_id=None, content=None, client_ip=None):
        """Add an operation log entry."""
        conn = self.get_connection()
        c = conn.cursor()
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            'INSERT INTO operation_logs (action, text_id, content, client_ip, created_at) '
            'VALUES (%s, %s, %s, %s, %s)',
            (action, text_id, content, client_ip, local_time)
        )
        conn.commit()
        conn.close()


text_service = TextService()
