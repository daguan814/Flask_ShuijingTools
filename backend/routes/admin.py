from functools import wraps
from flask import Blueprint, current_app, jsonify, request, send_file
from itsdangerous import BadSignature, SignatureExpired

from ..config import ADMIN_PASSWORD, ADMIN_USERNAME
from ..database import db_manager
from ..file_service import file_service
from ..log_service import log_service
from ..recycle_service import recycle_service
from ..school_service import school_service

admin_bp=Blueprint("admin",__name__,url_prefix="/api/admin")

def admin_required(view):
    @wraps(view)
    def wrapped(*args,**kwargs):
        token=request.headers.get("Authorization","").removeprefix("Bearer ").strip()
        try: payload=current_app.admin_serializer.loads(token,max_age=12*3600)
        except (BadSignature,SignatureExpired): return jsonify({"detail":"管理员登录已失效"}),401
        if payload.get("role")!="admin": return jsonify({"detail":"无权限"}),403
        return view(*args,**kwargs)
    return wrapped

@admin_bp.post("/login")
def login():
    payload=request.get_json(silent=True) or {}
    if not ADMIN_PASSWORD or payload.get("username")!=ADMIN_USERNAME or payload.get("password")!=ADMIN_PASSWORD:
        return jsonify({"detail":"管理员账号或密码错误"}),401
    return jsonify({"token":current_app.admin_serializer.dumps({"role":"admin"})})

@admin_bp.get("/overview")
@admin_required
def overview():
    return jsonify({"classes":school_service.classes(),"students":school_service.students(),"requests":school_service.requests(),"reports":school_service.reports()})

@admin_bp.get("/logs")
@admin_required
def logs():
    action=request.args.get("action","all"); day=request.args.get("date","").strip()
    if action not in {"all",*log_service.ACTION_PREFIXES.keys()}:return jsonify({"detail":"日志类型无效"}),400
    try:
        page=max(1,int(request.args.get("page","1")))
        page_size=min(100,max(10,int(request.args.get("page_size","20"))))
        class_id=int(request.args.get("class_id","0") or 0)
        user_id=int(request.args.get("user_id","0") or 0)
        if day:
            from datetime import datetime
            datetime.strptime(day,"%Y-%m-%d")
    except ValueError:return jsonify({"detail":"日志筛选参数无效"}),400
    return jsonify(log_service.list_all_logs(None if action=="all" else action,day or None,class_id or None,user_id or None,page,page_size))

@admin_bp.post("/classes")
@admin_required
def create_class():
    try: class_id=school_service.create_class((request.get_json(silent=True) or {}).get("name"))
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return jsonify({"id":class_id}),201

@admin_bp.patch("/classes/<int:class_id>")
@admin_required
def rename_class(class_id):
    try: school_service.rename_class(class_id,(request.get_json(silent=True) or {}).get("name"))
    except FileExistsError as exc:return jsonify({"detail":str(exc)}),409
    except ValueError as exc:return jsonify({"detail":str(exc)}),400
    return "",204

@admin_bp.delete("/classes/<int:class_id>")
@admin_required
def delete_class(class_id):
    try:school_service.delete_class(class_id)
    except ValueError as exc:return jsonify({"detail":str(exc)}),409
    return "",204

@admin_bp.post("/requests/<int:request_id>/review")
@admin_required
def review(request_id):
    try:school_service.review(request_id,bool((request.get_json(silent=True) or {}).get("approve")))
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return "",204

@admin_bp.patch("/students/<int:user_id>")
@admin_required
def update_student(user_id):
    payload=request.get_json(silent=True) or {}
    try:school_service.update_student(user_id,payload.get("username"),payload.get("class_id"),payload.get("password"),payload.get("status"))
    except FileExistsError as exc:return jsonify({"detail":str(exc)}),409
    except ValueError as exc:return jsonify({"detail":str(exc)}),400
    return "",204

@admin_bp.delete("/students/<int:user_id>")
@admin_required
def delete_student(user_id):
    payload=request.get_json(silent=True) or {}
    if payload.get("acknowledge")!="我确认删除学生并将文件移入回收站":return jsonify({"detail":"请确认删除警告"}),400
    try:school_service.delete_student(user_id,str(payload.get("username","")))
    except ValueError as exc:return jsonify({"detail":str(exc)}),400
    return "",204

def _student(user_id):
    user=db_manager.find_user_by_id(user_id)
    if not user or user["status"]=="deleted":raise ValueError("学生不存在")
    return user

@admin_bp.get("/students/<int:user_id>/files")
@admin_required
def files(user_id):
    try:
        user=_student(user_id); path=request.args.get("path",""); entries=file_service.list_entries(user,path)
    except (ValueError,FileNotFoundError) as exc:return jsonify({"detail":str(exc)}),400
    return jsonify({"path":file_service.normalize_relative_path(path),"entries":entries})

@admin_bp.post("/students/<int:user_id>/mkdir")
@admin_required
def mkdir(user_id):
    payload=request.get_json(silent=True) or {}
    try:path=file_service.create_folder(_student(user_id),payload.get("path",""),payload.get("name"))
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return jsonify({"path":path}),201

@admin_bp.post("/students/<int:user_id>/rename")
@admin_required
def rename(user_id):
    payload=request.get_json(silent=True) or {}
    try:item=file_service.rename_path(_student(user_id),payload.get("path",""),payload.get("name",""))
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return jsonify(item)

@admin_bp.post("/students/<int:user_id>/delete")
@admin_required
def delete_file(user_id):
    try:item=recycle_service.move_to_recycle(_student(user_id),(request.get_json(silent=True) or {}).get("path",""))
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return jsonify(item)

@admin_bp.get("/students/<int:user_id>/download")
@admin_required
def download(user_id):
    try:target=file_service.download_target(_student(user_id),request.args.get("path",""))
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return send_file(target,as_attachment=True,download_name=target.name)

@admin_bp.post("/students/<int:user_id>/batch-download")
@admin_required
def batch_download(user_id):
    payload=request.get_json(silent=True) or {}
    try:
        archive=file_service.build_download_archive(_student(user_id),payload.get("paths",[]),payload.get("base_path",""))
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    response=send_file(archive,as_attachment=True,download_name="云盘文件.zip")
    response.call_on_close(lambda: archive.unlink(missing_ok=True))
    return response

@admin_bp.post("/students/<int:user_id>/upload")
@admin_required
def upload(user_id):
    user=_student(user_id); parent=request.form.get("path",""); files=request.files.getlist("files"); relatives=request.form.getlist("relative_paths")
    if not files or len(files)!=len(relatives):return jsonify({"detail":"上传参数无效"}),400
    try:uploaded=[file_service.upload_file(user,parent,rel,file) for file,rel in zip(files,relatives)]
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return jsonify({"uploaded":uploaded})

@admin_bp.post("/students/<int:user_id>/move")
@admin_required
def move(user_id):
    payload=request.get_json(silent=True) or {}
    try:moved=file_service.move_paths(_student(user_id),payload.get("paths",[]),payload.get("destination",""))
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return jsonify({"moved":moved})

@admin_bp.post("/announcements")
@admin_required
def announcement():
    payload=request.get_json(silent=True) or {}
    try:school_service.create_announcement(payload.get("class_id"),payload.get("title"),payload.get("content"))
    except ValueError as exc:return jsonify({"detail":str(exc)}),400
    return "",204

@admin_bp.get("/recycle")
@admin_required
def recycle():
    items=[]
    for user in school_service.students():
        for item in recycle_service.list_items(user):item.update(user_id=user["id"],username=user["username"],class_name=user["class_name"]);items.append(item)
    items.sort(key=lambda x:x["id"],reverse=True);return jsonify({"items":items})

@admin_bp.post("/recycle/<int:item_id>/restore")
@admin_required
def restore(item_id):
    payload=request.get_json(silent=True) or {}
    try:path=recycle_service.restore(_student(int(payload.get("user_id"))),item_id,require_password=False)
    except Exception as exc:return jsonify({"detail":str(exc)}),400
    return jsonify({"path":path})
