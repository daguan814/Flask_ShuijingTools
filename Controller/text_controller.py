from flask import Blueprint, render_template, request, redirect, url_for, jsonify
import os
import sys
# 导入文本服务
from Service.text_service import text_service

# 添加Service目录到Python路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
service_dir = os.path.join(current_dir, 'Service')
if service_dir not in sys.path:
    sys.path.insert(0, service_dir)

# 创建蓝图
text_bp = Blueprint('text', __name__)


# 首页 - 显示所有文本
@text_bp.route('/')
def index():
    texts = text_service.get_all_texts()
    return render_template('index.html', texts=texts)


# 添加文本
@text_bp.route('/add', methods=['POST'])
def add_text():
    content = request.form.get('content')
    if content:
        text_service.add_text(content)
    return redirect(url_for('text.index'))


# 删除文本
@text_bp.route('/delete/<int:text_id>')
def delete_text(text_id):
    text_service.delete_text(text_id)
    return redirect(url_for('text.index'))


# API: 获取所有文本
@text_bp.route('/api/texts')
def get_texts():
    texts = text_service.get_all_texts()

    texts_list = []
    for text in texts:
        texts_list.append({
            'id': text[0],
            'content': text[1],
            'created_at': text[2]
        })

    return jsonify(texts_list)