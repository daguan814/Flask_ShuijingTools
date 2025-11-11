from flask import Flask
import ssl
import os
# 导入蓝图
from Controller.ShareController import index_bp
from Controller.WordsController import words_bp

app = Flask(__name__)

# 注册words蓝图
app.register_blueprint(words_bp)
app.register_blueprint(index_bp)

if __name__ == '__main__':
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # SSL证书配置
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        certfile=os.path.join(base_dir, 'SSL/shuijingnas.xin.crt'),
        keyfile=os.path.join(base_dir, 'SSL/shuijingnas.xin.key')
    )

    # 使用SSL证书运行应用
    app.run(
        host='0.0.0.0',
        port=18080,
        ssl_context=ssl_context
    )
