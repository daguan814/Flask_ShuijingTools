import hashlib
import re
import uuid

from flask import Blueprint, g, jsonify, make_response, request

from ..config import SECRET_KEY

from ..auth_service import auth_service
from ..file_service import file_service
from ..account_service import account_service

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _login_device():
    device_id = request.cookies.get("login_device", "")
    if not re.fullmatch(r"[0-9a-f]{64}", device_id):
        device_id = uuid.uuid4().hex + uuid.uuid4().hex
    device_key = hashlib.sha256(f"{SECRET_KEY}:{device_id}".encode()).hexdigest()
    return device_id, device_key


def _login_response(payload, status, device_id):
    response = make_response(jsonify(payload), status)
    response.set_cookie(
        "login_device",
        device_id,
        max_age=365 * 24 * 60 * 60,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure,
    )
    return response


@auth_bp.route("/login", methods=["POST"])
def login():
    device_id, device_key = _login_device()
    attempt = auth_service.login_attempt_status(device_key)
    if attempt["blocked"]:
        blocked_until = attempt["blocked_until"]
        return _login_response(
            {
                "detail": "登录尝试次数过多，请在5小时后重试。",
                "blocked_until": blocked_until.isoformat(timespec="seconds"),
            },
            429,
            device_id,
        )

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _login_response({"detail": "invalid json"}, 400, device_id)

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    group_id = payload.get("group_id")
    if not username or not password or not group_id:
        return _login_response({"detail": "用户组、用户名和密码均为必填项"}, 400, device_id)

    user = auth_service.login(group_id, username, password)
    if not user:
        attempt = auth_service.record_login_failure(device_key)
        if attempt["blocked"]:
            return _login_response(
                {
                    "detail": "已连续失败5次，当前浏览器已锁定5小时。",
                    "blocked_until": attempt["blocked_until"].isoformat(timespec="seconds"),
                },
                429,
                device_id,
            )
        remaining = auth_service.MAX_LOGIN_FAILURES - attempt["failed_count"]
        return _login_response(
            {"detail": f"用户组、用户名或密码错误，还可尝试 {remaining} 次。"},
            404,
            device_id,
        )

    auth_service.clear_login_failures(device_key)
    token = auth_service.create_session(user["id"])
    return _login_response(
        {"token": token, "user": auth_service.public_user(user)},
        200,
        device_id,
    )


@auth_bp.route("/me", methods=["GET"])
def me():
    user = auth_service.public_user(g.current_user)
    user["storage"] = file_service.storage_usage(g.current_user)
    return jsonify({"user": user})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        auth_service.revoke_session(authorization[7:].strip())
    return "", 204


@auth_bp.route("/groups", methods=["GET"])
def groups():
    return jsonify({"groups": account_service.groups()})


@auth_bp.route("/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", ""))
    if password != str(payload.get("confirm_password", "")):
        return jsonify({"detail": "两次输入的密码不一致"}), 400
    try:
        request_id = account_service.register(
            payload.get("group_id"), payload.get("username"), password
        )
    except FileExistsError as exc:
        return jsonify({"detail": str(exc)}), 409
    except (ValueError, TypeError) as exc:
        return jsonify({"detail": str(exc)}), 400
    return jsonify({"id": request_id, "detail": "注册申请已提交，请等待管理员审核"}), 201
