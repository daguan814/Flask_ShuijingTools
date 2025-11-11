"""
Created on 2025/11/11 11:54 
Author: Shuijing
Description: 文本管理功能控制器
"""
from flask import Blueprint, render_template, request, redirect, url_for
import requests
import json

# 创建蓝图
index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def share():
    try:
        # 获取文本数据 - 已修改为按id降序排序
        url = 'http://192.168.100.242:9090/api/v3/data/prcpwdqu102y74c/mwlfmq5vw4pauop/records?sort=%7B%22direction%22%3A%22desc%22%2C%20%22field%22%3A%22id%22%7D&where=%28delect_status%2Ceq%2C0%29'
        headers = {
            'accept': 'application/json',
            'xc-token': 'SpxCrO_w8MOUcNiTLj4x-ryXaps8ntMTznC3vxiH'
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        records = data.get('records', [])
        
        # 准备显示数据 - 移除了收藏状态相关字段
        texts = []
        for record in records:
            fields = record.get('fields', {})
            texts.append({
                'id': record.get('id'),
                'text': fields.get('text'),
                'created_at': fields.get('CreatedAt')
            })
        
        # 处理URL参数中的消息
        error_message = request.args.get('error')
        success_message = request.args.get('success')
        
        return render_template('share.html', texts=texts, error=error_message, success=success_message)
    except Exception as e:
        # 错误处理
        error_message = str(e)
        return render_template('share.html', error=error_message, texts=[])

@index_bp.route('/submit_text', methods=['POST'])
def submit_text():
    try:
        # 获取表单提交的文本
        text_content = request.form.get('text_content')
        
        if not text_content or text_content.strip() == '':
            return redirect(url_for('index.share', error='文本内容不能为空'))
        
        # 构建API请求 - 移除了collection_status字段
        url = 'http://192.168.100.242:9090/api/v3/data/prcpwdqu102y74c/mwlfmq5vw4pauop/records'
        headers = {
            'accept': 'application/json',
            'xc-token': 'SpxCrO_w8MOUcNiTLj4x-ryXaps8ntMTznC3vxiH',
            'Content-Type': 'application/json'
        }
        payload = {
            'fields': {
                'text': text_content,
                'delect_status': 0
            }
        }
        
        # 发送POST请求
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # 如果状态码不是200，抛出异常
        
        # 重定向回主页面，不显示成功消息
        return redirect(url_for('index.share'))
    except Exception as e:
        # 错误处理
        error_message = f'提交失败: {str(e)}'
        return redirect(url_for('index.share', error=error_message))

@index_bp.route('/delete_text/<int:text_id>', methods=['POST'])
def delete_text(text_id):
    try:
        # 构建删除API请求
        url = 'http://192.168.100.242:9090/api/v3/data/prcpwdqu102y74c/mwlfmq5vw4pauop/records'
        headers = {
            'accept': 'application/json',
            'xc-token': 'SpxCrO_w8MOUcNiTLj4x-ryXaps8ntMTznC3vxiH',
            'Content-Type': 'application/json'
        }
        payload = {
            'id': text_id,
            'fields': {
                'delect_status': 1
            }
        }
        
        # 发送PATCH请求
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()  # 如果状态码不是200，抛出异常
        
        # 重定向回主页面，不显示成功消息
        return redirect(url_for('index.share'))
    except Exception as e:
        # 错误处理
        error_message = f'删除失败: {str(e)}'
        return redirect(url_for('index.share', error=error_message))