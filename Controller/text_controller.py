from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    current_app,
    abort,
    send_file,
)
from werkzeug.utils import safe_join
import os
import re
from Service.text_service import text_service

text_bp = Blueprint('text', __name__)


def get_client_ip():
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr


def normalize_upload_path(filename):
    if not filename:
        return None
    return filename


def format_size(num_bytes):
    size = float(num_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            if unit == 'B':
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def list_uploads():
    base_dir = current_app.config['UPLOAD_FOLDER']
    uploads = []
    for root, _, filenames in os.walk(base_dir):
        for name in filenames:
            full_path = os.path.join(root, name)
            rel_path = os.path.relpath(full_path, base_dir).replace(os.sep, '/')
            if '/' in rel_path:
                continue
            mtime = os.path.getmtime(full_path)
            uploads.append({
                'path': rel_path,
                'size': format_size(os.path.getsize(full_path)),
                'mtime': mtime
            })
    uploads.sort(key=lambda item: item['mtime'], reverse=True)
    for item in uploads:
        item.pop('mtime', None)
    return uploads


@text_bp.route('/')
def index():
    texts = text_service.get_all_texts()
    uploads = list_uploads()
    return render_template('index.html', texts=texts, uploads=uploads)


@text_bp.route('/add', methods=['POST'])
def add_text():
    content = request.form.get('content')
    if content:
        text_id = text_service.add_text(content)
    return redirect(url_for('text.index'))


@text_bp.route('/delete/<int:text_id>')
def delete_text(text_id):
    deleted = text_service.delete_text(text_id)
    return redirect(url_for('text.index'))


@text_bp.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('files')
    if not files:
        return redirect(url_for('text.index'))

    base_dir = current_app.config['UPLOAD_FOLDER']
    for f in files:
        if not f or not f.filename:
            continue
        rel_path = normalize_upload_path(f.filename)
        if not rel_path:
            continue
        safe_path = safe_join(base_dir, rel_path)
        if safe_path is None:
            continue
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        f.save(safe_path)
        text_service.add_log('file_upload', content=rel_path.replace(os.sep, '/'), client_ip=get_client_ip())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return ('', 204)
    return redirect(url_for('text.index', _anchor='file-section'))


@text_bp.route('/files/download/<path:filepath>')
def download_file(filepath):
    base_dir = current_app.config['UPLOAD_FOLDER']
    safe_path = safe_join(base_dir, filepath)
    if safe_path is None or not os.path.isfile(safe_path):
        abort(404)
    return send_file(safe_path, as_attachment=True)


@text_bp.route('/files/delete', methods=['POST'])
def delete_file():
    rel_path = request.form.get('path')
    if not rel_path:
        return redirect(url_for('text.index', _anchor='file-section'))

    base_dir = current_app.config['UPLOAD_FOLDER']
    safe_path = safe_join(base_dir, rel_path)
    if safe_path and os.path.isfile(safe_path):
        os.remove(safe_path)
        text_service.add_log('file_delete', content=rel_path, client_ip=get_client_ip())

        parent = os.path.dirname(safe_path)
        base_abs = os.path.abspath(base_dir)
        while os.path.abspath(parent).startswith(base_abs) and parent != base_abs:
            if os.listdir(parent):
                break
            os.rmdir(parent)
            parent = os.path.dirname(parent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return ('', 204)
    return redirect(url_for('text.index', _anchor='file-section'))


@text_bp.route('/api/files')
def get_files():
    uploads = list_uploads()
    return jsonify(uploads)


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
