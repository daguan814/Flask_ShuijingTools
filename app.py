from flask import Flask
import ssl
import os
import sys
from db.database import db_manager
from Controller.text_controller import text_bp

current_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.join(current_dir, 'Service')
if service_dir not in sys.path:
    sys.path.insert(0, service_dir)

app = Flask(__name__, static_url_path='/static')

upload_dir = os.path.join(current_dir, 'uploads')
os.makedirs(upload_dir, exist_ok=True)
app.config['UPLOAD_FOLDER'] = upload_dir
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

app.register_blueprint(text_bp, url_prefix='/')

if __name__ == '__main__':
    db_manager.init_db()

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        certfile=os.path.join(current_dir, 'SSL/shuijingnas.xin.crt'),
        keyfile=os.path.join(current_dir, 'SSL/shuijingnas.xin.key')
    )

    app.run(
        host='0.0.0.0',
        port=8080,
        ssl_context=ssl_context,
        debug=False,
        threaded=True
    )
