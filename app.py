from flask import Flask, request
import ssl
import os
import sys
# 导入数据库管理器并初始化数据库
from db.database import db_manager
# 导入蓝图
from Controller.text_controller import text_bp

# 添加Service目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.join(current_dir, 'Service')
if service_dir not in sys.path:
    sys.path.insert(0, service_dir)

# 创建Flask应用，设置静态文件路径
app = Flask(__name__, static_url_path="/text/static")

# 设置应用根路径
app.config['APPLICATION_ROOT'] = '/text'

# 注册蓝图，URL前缀设为根路径
app.register_blueprint(text_bp, url_prefix='/')

# 添加反向代理支持中间件
@app.before_request
def before_request():
    """处理反向代理环境下的URL生成"""
    # 如果请求头中包含X-Forwarded-Prefix，使用它作为URL前缀
    if 'X-Forwarded-Prefix' in request.headers:
        app.config['APPLICATION_ROOT'] = request.headers['X-Forwarded-Prefix']
        # 动态更新静态文件路径
        app.static_url_path = request.headers['X-Forwarded-Prefix'] + '/static'

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