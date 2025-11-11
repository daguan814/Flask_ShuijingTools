from flask import Blueprint, render_template

# 创建蓝图
words_bp = Blueprint('words', __name__)

@words_bp.route('/words')
def search_words():
    # 渲染单词搜索页面
    return render_template('search_words.html')