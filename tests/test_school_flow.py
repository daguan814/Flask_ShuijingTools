import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path


_TEMP_DIR = tempfile.TemporaryDirectory()
_ROOT = Path(_TEMP_DIR.name)
os.environ.update(
    {
        "DB_DRIVER": "sqlite",
        "SQLITE_DB_PATH": str(_ROOT / "test.db"),
        "STORAGE_ROOT": str(_ROOT / "storage"),
        "RECYCLE_ROOT": str(_ROOT / "storage" / "回收站"),
        "SECRET_KEY": "school-flow-test-secret",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "admin-test-password",
    }
)

from backend.app import create_app


class SchoolFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def admin_headers(self):
        response = self.client.post(
            "/api/admin/login",
            json={"username": "admin", "password": "admin-test-password"},
        )
        self.assertEqual(response.status_code, 200)

        return {"Authorization": f"Bearer {response.json['token']}"}

    def test_registration_files_messages_and_admin_restore(self):
        headers = self.admin_headers()
        response = self.client.post(
            "/api/admin/admins", headers=headers,
            json={"username": "second-admin", "password": "second-admin-password"},
        )
        self.assertEqual(response.status_code, 201)
        second_admin_id = response.json["id"]
        self.assertEqual(
            self.client.post(
                "/api/admin/login",
                json={"username": "second-admin", "password": "second-admin-password"},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/admin/admins/{second_admin_id}", headers=headers,
                json={"status": "disabled"},
            ).status_code,
            204,
        )
        response = self.client.post("/api/admin/classes", headers=headers, json={"name": "测试用户组"})
        self.assertEqual(response.status_code, 201)
        class_111 = {"id": response.json["id"], "name": "测试用户组"}

        response = self.client.post(
            "/api/auth/register",
            json={
                "class_id": class_111["id"],
                "username": "测试学生",
                "password": "student123",
                "confirm_password": "student123",
            },
        )
        self.assertEqual(response.status_code, 201)

        overview = self.client.get("/api/admin/overview", headers=headers).json
        request_id = next(
            item["id"] for item in overview["requests"] if item["username"] == "测试学生"
        )
        response = self.client.post(
            f"/api/admin/requests/{request_id}/review",
            headers=headers,
            json={"approve": True},
        )
        self.assertEqual(response.status_code, 204)

        response = self.client.post(
            "/api/auth/login",
            json={
                "class_id": class_111["id"],
                "username": "测试学生",
                "password": "student123",
            },
        )
        self.assertEqual(response.status_code, 200)
        student_headers = {"Authorization": f"Bearer {response.json['token']}"}
        self.assertTrue((_ROOT / "storage" / "测试用户组" / "测试学生").is_dir())

        response = self.client.post(
            "/api/files/upload",
            headers=student_headers,
            data={
                "path": "",
                "relative_paths": "作业.txt",
                "files": (BytesIO(b"homework"), "作业.txt"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)

        # 下载不能只验证“生成链接”接口：必须继续请求签名链接并拿到原文件。
        # 这样可拦住链接编码、缺失运行时导入等会让所有用户无法下载的回归。
        response = self.client.post(
            "/api/files/download/prepare",
            headers=student_headers,
            json={"paths": ["作业.txt"], "base": ""},
        )
        self.assertEqual(response.status_code, 200)
        ticket_url = response.json["url"]
        self.assertTrue(ticket_url.startswith("/api/files/download/ticket/"))
        response = self.client.get(ticket_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"homework")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        response.close()

        # 管理员个人文件、用户组共享下载和对应操作日志也走独立链路，统一覆盖。
        response = self.client.post(
            "/api/admin/personal-files/upload",
            headers=headers,
            data={
                "path": "",
                "relative_paths": "管理员资料.txt",
                "files": (BytesIO(b"admin-resource"), "管理员资料.txt"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            "/api/admin/personal-files/download?path=管理员资料.txt", headers=headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"admin-resource")
        response.close()
        self.assertEqual(
            self.client.post(
                "/api/admin/personal-files/share",
                headers=headers,
                json={"paths": ["管理员资料.txt"], "class_ids": [class_111["id"]]},
            ).status_code,
            204,
        )
        shared = self.client.get("/api/auth/shared-files", headers=student_headers).json["items"]
        share = next(item for item in shared if item["name"] == "管理员资料.txt")
        response = self.client.get(
            f"/api/auth/shared-files/{share['share_id']}/download", headers=student_headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"admin-resource")
        response.close()
        download_logs = self.client.get(
            "/api/admin/logs?action=download", headers=headers
        ).json["items"]
        self.assertTrue(
            any("下载管理员共享文件：管理员资料.txt" in item["content"] for item in download_logs)
        )
        self.assertEqual(
            self.client.post(
                "/api/admin/personal-files/delete",
                headers=headers,
                json={"paths": ["管理员资料.txt"]},
            ).status_code,
            200,
        )
        admin_recycle = self.client.get("/api/admin/recycle", headers=headers).json["items"]
        deleted_admin_file = next(
            item for item in admin_recycle
            if item["owner_type"] == "admin" and item["name"] == "管理员资料.txt"
        )
        self.assertEqual(
            self.client.post(
                f"/api/admin/recycle/{deleted_admin_file['id']}/restore",
                headers=headers,
                json={"owner_type": "admin"},
            ).status_code,
            200,
        )
        personal_names = [
            item["name"]
            for item in self.client.get("/api/admin/personal-files", headers=headers).json["entries"]
        ]
        self.assertIn("管理员资料.txt", personal_names)

        response = self.client.get(
            f"/api/admin/classes/{class_111['id']}/files", headers=headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("测试学生", [item["name"] for item in response.json["entries"]])
        response = self.client.get(
            f"/api/admin/classes/{class_111['id']}/files?path=测试学生",
            headers=headers,
        )
        self.assertIn("作业.txt", [item["name"] for item in response.json["entries"]])
        self.assertEqual(
            self.client.post(
                f"/api/admin/classes/{class_111['id']}/preview/start?path=测试学生/作业.txt",
                headers=headers,
            ).status_code,
            200,
        )
        response = self.client.get(
            f"/api/admin/classes/{class_111['id']}/download?path=测试学生",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        response.close()
        response = self.client.post(
            f"/api/admin/classes/{class_111['id']}/batch-download",
            headers=headers,
            json={"paths": ["测试学生/作业.txt"]},
        )
        self.assertEqual(response.status_code, 200)
        response.close()
        protected = self.client.post(
            f"/api/admin/classes/{class_111['id']}/batch-delete",
            headers=headers,
            json={"paths": ["测试学生"]},
        ).json["results"][0]
        self.assertFalse(protected["deleted"])

        self.assertEqual(
            self.client.post(
                "/api/admin/announcements",
                headers=headers,
                json={"class_id": class_111["id"], "title": "通知", "content": "明天上课"},
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/reports", headers=student_headers, json={"content": "作业已完成"}
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.post(
                "/api/files/delete", headers=student_headers, json={"path": "作业.txt"}
            ).status_code,
            204,
        )
        self.assertEqual(self.client.get("/api/logs", headers=student_headers).status_code, 404)

        overview = self.client.get("/api/admin/overview", headers=headers).json
        student = next(item for item in overview["students"] if item["username"] == "测试学生")
        self.assertEqual(overview["reports"][0]["content"], "作业已完成")
        admin_logs = self.client.get("/api/admin/logs", headers=headers).json
        self.assertGreaterEqual(admin_logs["total"], 2)
        self.assertEqual(admin_logs["items"][0]["class_name"], "测试用户组")
        self.assertEqual(admin_logs["items"][0]["username"], "测试学生")
        self.assertEqual(
            self.client.get("/api/auth/announcements", headers=student_headers).json["items"][0]["title"],
            "通知",
        )
        recycle = self.client.get("/api/admin/recycle", headers=headers).json["items"]
        item = next(item for item in recycle if item["username"] == "测试学生")
        response = self.client.post(
            f"/api/admin/recycle/{item['id']}/restore",
            headers=headers,
            json={"user_id": student["id"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue((_ROOT / "storage" / "测试用户组" / "测试学生" / "作业.txt").is_file())

        response = self.client.post(
            "/api/admin/classes", headers=headers, json={"name": "二班"}
        )
        self.assertEqual(response.status_code, 201)
        class_id = response.json["id"]
        response = self.client.patch(
            f"/api/admin/students/{student['id']}",
            headers=headers,
            json={"username": "新姓名", "class_id": class_id},
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse((_ROOT / "storage" / "测试用户组" / "测试学生").exists())
        self.assertTrue((_ROOT / "storage" / "二班" / "新姓名" / "作业.txt").is_file())
        self.assertEqual(self.client.get("/api/auth/me", headers=student_headers).status_code, 401)

        response = self.client.patch(
            f"/api/admin/classes/{class_id}", headers=headers, json={"name": "新二班"}
        )
        self.assertEqual(response.status_code, 204)
        self.assertTrue((_ROOT / "storage" / "新二班" / "新姓名" / "作业.txt").is_file())


if __name__ == "__main__":
    unittest.main()
