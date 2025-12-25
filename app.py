from flask import Flask
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

# 创建Flask应用，使用默认的静态文件URL前缀'/static'
app = Flask(__name__)

# 添加before_request中间件，处理Nginx代理的路径
@app.before_request
def before_request():
    from flask import request
    # 检查是否通过Nginx代理访问
    if request.headers.get('X-Forwarded-For'):
        # 如果请求路径不是以/text开头，添加/text前缀
        if not request.path.startswith('/text'):
            # 重定向到带/text前缀的路径
            from flask import redirect, url_for
            return redirect(url_for('text.index'))

# 注册蓝图，使用根路径作为前缀
app.register_blueprint(text_bp, url_prefix='/')

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