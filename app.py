from flask import Flask
import ssl
import os
import sys
from db.database import db_manager
from Controller.text_controller import text_bp

# 添加Service目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.join(current_dir, 'Service')
if service_dir not in sys.path:
    sys.path.insert(0, service_dir)

# 创建Flask应用，设置静态文件路径为 /text/static
app = Flask(__name__, static_url_path="/text/static")

# 注册蓝图，URL前缀设为 /text
app.register_blueprint(text_bp, url_prefix='/text')

if __name__ == '__main__':
    # 确保数据库已初始化
    db_manager.init_db()

    # SSL 部分保持不变
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        certfile=os.path.join(base_dir, 'SSL/shuijingnas.xin.crt'),
        keyfile=os.path.join(base_dir, 'SSL/shuijingnas.xin.key')
    )

    app.run(
        host='0.0.0.0',
        port=8080,
        ssl_context=ssl_context,
        debug=True
    )