from functools import wraps

from flask import Blueprint, jsonify, request

from ..account_service import account_service
from ..database import db_manager
from ..file_service import file_service

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not account_service.is_admin(token):
            return jsonify({"detail": "管理员登录已失效"}), 401
        return view(*args, **kwargs)
    return wrapped


@admin_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    token = account_service.admin_login(str(payload.get("username", "")), str(payload.get("password", "")))
    if not token: return jsonify({"detail": "管理员账号或密码错误"}), 401
    return jsonify({"token": token})


@admin_bp.post("/logout")
@admin_required
def logout():
    account_service.admin_logout(request.headers.get("Authorization", "").removeprefix("Bearer ").strip())
    return "", 204


@admin_bp.get("/overview")
@admin_required
def overview():
    return jsonify({"groups": account_service.groups(), "users": account_service.users(), "requests": account_service.requests()})


@admin_bp.post("/groups")
@admin_required
def create_group():
    try: group_id = account_service.create_group((request.get_json(silent=True) or {}).get("name"))
    except Exception as exc: return jsonify({"detail": str(exc)}), 400
    return jsonify({"id": group_id}), 201


@admin_bp.delete("/groups/<int:group_id>")
@admin_required
def delete_group(group_id):
    try: deleted = account_service.delete_group(group_id)
    except ValueError as exc: return jsonify({"detail": str(exc)}), 409
    return ("", 204) if deleted else (jsonify({"detail": "用户组不存在"}), 404)


@admin_bp.post("/users")
@admin_required
def create_user():
    payload=request.get_json(silent=True) or {}
    try: user_id=account_service.create_user(payload.get("group_id"),payload.get("username"),str(payload.get("password","")),payload.get("quota_bytes") or 5*1024**3)
    except Exception as exc: return jsonify({"detail": str(exc)}), 400
    return jsonify({"id":user_id}),201


@admin_bp.patch("/users/<int:user_id>")
@admin_required
def update_user(user_id):
    payload=request.get_json(silent=True) or {}
    try: account_service.update_user(user_id,payload.get("status"),payload.get("quota_bytes"),payload.get("password"),payload.get("group_id"))
    except ValueError as exc: return jsonify({"detail":str(exc)}),400
    return "",204


@admin_bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    payload=request.get_json(silent=True) or {}
    if payload.get("acknowledge") != "我确认保留文件并删除账号":
        return jsonify({"detail":"请确认删除警告"}),400
    try: account_service.delete_user(user_id,str(payload.get("username","")))
    except ValueError as exc: return jsonify({"detail":str(exc)}),400
    return "",204


@admin_bp.post("/requests/<int:request_id>/review")
@admin_required
def review(request_id):
    try: account_service.review(request_id,bool((request.get_json(silent=True) or {}).get("approve")))
    except Exception as exc: return jsonify({"detail":str(exc)}),400
    return "",204


@admin_bp.get("/users/<int:user_id>/files")
@admin_required
def user_files(user_id):
    user=db_manager.find_user_by_id(user_id)
    if not user: return jsonify({"detail":"用户不存在"}),404
    path=request.args.get("path","")
    try: entries=file_service.list_entries(user,path)
    except (ValueError,FileNotFoundError) as exc: return jsonify({"detail":str(exc)}),400
    return jsonify({"path":file_service.normalize_relative_path(path),"entries":entries})
