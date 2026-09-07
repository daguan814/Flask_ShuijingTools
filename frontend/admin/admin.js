const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
let token = sessionStorage.getItem("school_admin") || "";
let state = {classes: [], students: [], requests: [], reports: []};
let path = "";
let logPage = 1;
let logTotalPages = 1;

async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    options.body = JSON.stringify(options.json);
  }
  const response = await fetch(`/api/admin${url}`, {...options, headers});
  if (response.status === 401 && url !== "/login") logout();
  return response;
}

async function detail(response) {
  try { return (await response.json()).detail || "操作失败"; } catch (_) { return "操作失败"; }
}

function note(text) {
  $("notice").textContent = text;
  setTimeout(() => { if ($("notice").textContent === text) $("notice").textContent = ""; }, 3000);
}

function logout() {
  token = "";
  sessionStorage.removeItem("school_admin");
  $("app").classList.add("hidden");
  $("login").classList.remove("hidden");
}

$("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await api("/login", {method: "POST", json: {username: $("adminName").value, password: $("adminPassword").value}});
  if (!response.ok) { $("loginError").textContent = await detail(response); return; }
  token = (await response.json()).token;
  sessionStorage.setItem("school_admin", token);
  $("login").classList.add("hidden");
  $("app").classList.remove("hidden");
  await loadOverview();
});

$("logoutBtn").addEventListener("click", logout);

document.querySelector("nav").addEventListener("click", (event) => {
  const button = event.target.closest("[data-view]");
  if (!button) return;
  document.querySelectorAll("nav button").forEach((item) => item.classList.toggle("active", item === button));
  document.querySelectorAll(".view").forEach((view) => view.classList.add("hidden"));
  $(button.dataset.view).classList.remove("hidden");
  if (button.dataset.view === "files") loadFiles("");
  if (button.dataset.view === "logs") loadLogs();
  if (button.dataset.view === "recycle") loadRecycle();
});

async function loadOverview() {
  const response = await api("/overview");
  if (!response.ok) return;
  state = await response.json();
  renderOverview();
}

function statusLabel(status) {
  return status === "active" ? "正常" : status === "disabled" ? "已禁用" : "待设置密码";
}

function renderOverview() {
  const classOptions = state.classes.map((item) => `<option value="${item.id}">${esc(item.name)}</option>`).join("");
  $("announcementClass").innerHTML = classOptions;
  $("logClass").innerHTML = `<option value="">全部班级</option>${classOptions}`;
  renderLogStudents();
  $("studentSelect").innerHTML = `<option value="">选择学生</option>` + state.students.map((item) => `<option value="${item.id}">${esc(item.class_name)} / ${esc(item.username)}</option>`).join("");
  $("messageBadge").textContent = state.requests.length ? state.requests.length : "";

  $("classStudentList").innerHTML = state.classes.map((classItem) => {
    const students = state.students.filter((student) => student.class_id === classItem.id);
    const rows = students.map((student) => `<tr><td>${esc(student.username)}</td><td>${statusLabel(student.status)}</td><td>${esc(student.used_display)}</td><td><div class="actions"><button data-student-edit="${student.id}">修改</button><button data-student-toggle="${student.id}" data-status="${student.status}">${student.status === "disabled" ? "启用" : "禁用"}</button><button class="danger" data-student-delete="${student.id}" data-name="${esc(student.username)}">删除</button></div></td></tr>`).join("") || `<tr><td colspan="4" class="muted">这个班级还没有学生</td></tr>`;
    return `<article class="class-card"><div class="class-head"><button class="class-toggle" data-class-toggle="${classItem.id}"><span>▾</span>${esc(classItem.name)} <span class="class-count">${students.length} 名学生</span></button><div class="actions"><button data-class-rename="${classItem.id}" data-name="${esc(classItem.name)}">班级改名</button><button class="danger" data-class-delete="${classItem.id}">删除空班级</button></div></div><div class="class-body" data-class-body="${classItem.id}"><div class="table"><table><thead><tr><th>学生姓名</th><th>状态</th><th>已用空间</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table></div></div></article>`;
  }).join("");

  $("requestRows").innerHTML = state.requests.map((item) => `<tr><td>${esc(item.class_name)}</td><td>${esc(item.username)}</td><td>${new Date(item.created_at).toLocaleString()}</td><td><button data-review="${item.id}" data-approve="1">通过</button> <button data-review="${item.id}" data-approve="0">拒绝</button></td></tr>`).join("") || `<tr><td colspan="4" class="muted">没有待审核申请</td></tr>`;
  $("reportList").innerHTML = state.reports.map((item) => `<article class="report"><strong>${esc(item.class_name)} / ${esc(item.username)}</strong><p>${esc(item.content)}</p><span class="muted">${new Date(item.created_at).toLocaleString()}</span></article>`).join("") || `<p class="muted">暂无学生汇报</p>`;
}

function renderLogStudents() {
  const classId = Number($("logClass").value || 0);
  const current = $("logStudent").value;
  const students = state.students.filter((item) => !classId || item.class_id === classId);
  $("logStudent").innerHTML = `<option value="">全部学生</option>` + students.map((item) => `<option value="${item.id}">${esc(item.username)}</option>`).join("");
  if (students.some((item) => String(item.id) === current)) $("logStudent").value = current;
}

$("classStudentList").addEventListener("click", async (event) => {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.dataset.classToggle) {
    const body = document.querySelector(`[data-class-body="${target.dataset.classToggle}"]`);
    body.classList.toggle("hidden");
    target.firstElementChild.textContent = body.classList.contains("hidden") ? "▸" : "▾";
  } else if (target.dataset.classRename) {
    const name = prompt("新班级名称", target.dataset.name);
    if (!name) return;
    const response = await api(`/classes/${target.dataset.classRename}`, {method: "PATCH", json: {name}});
    note(response.ok ? "班级及目录已改名" : await detail(response)); await loadOverview();
  } else if (target.dataset.classDelete) {
    if (!confirm("只能删除没有学生且目录为空的班级，确认删除？")) return;
    const response = await api(`/classes/${target.dataset.classDelete}`, {method: "DELETE"});
    note(response.ok ? "班级已删除" : await detail(response)); await loadOverview();
  } else if (target.dataset.studentEdit) {
    await editStudent(Number(target.dataset.studentEdit));
  } else if (target.dataset.studentToggle) {
    await toggleStudent(Number(target.dataset.studentToggle), target.dataset.status);
  } else if (target.dataset.studentDelete) {
    await removeStudent(Number(target.dataset.studentDelete), target.dataset.name);
  }
});

$("addClass").addEventListener("click", async () => {
  const name = prompt("新班级名称"); if (!name) return;
  const response = await api("/classes", {method: "POST", json: {name}});
  note(response.ok ? "班级已创建" : await detail(response)); await loadOverview();
});

async function editStudent(id) {
  const student = state.students.find((item) => item.id === id);
  const name = prompt("学生姓名", student.username); if (name === null) return;
  const classId = Number(prompt("班级ID\n" + state.classes.map((item) => `${item.id}: ${item.name}`).join("\n"), student.class_id));
  const password = prompt("新密码（不修改请留空）", ""); if (password === null) return;
  const response = await api(`/students/${id}`, {method: "PATCH", json: {username: name, class_id: classId, password}});
  note(response.ok ? "学生信息已更新" : await detail(response)); await loadOverview();
}

async function toggleStudent(id, status) {
  const next = status === "disabled" ? "active" : "disabled";
  if (!confirm(`确认${next === "disabled" ? "禁用" : "启用"}该学生？`)) return;
  const response = await api(`/students/${id}`, {method: "PATCH", json: {status: next}});
  note(response.ok ? "学生状态已更新" : await detail(response)); await loadOverview();
}

async function removeStudent(id, name) {
  alert("请不要随意删除学生！账号将停用，学生目录会移入统一回收站。");
  if (prompt(`请输入学生姓名 ${name} 确认`) !== name || !confirm("最后确认删除该学生？")) return;
  const response = await api(`/students/${id}`, {method: "DELETE", json: {username: name, acknowledge: "我确认删除学生并将文件移入回收站"}});
  note(response.ok ? "学生已删除，目录已移入回收站" : await detail(response)); await loadOverview();
}

$("requestRows").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-review]"); if (!button) return;
  const approve = button.dataset.approve === "1";
  if (!confirm(approve ? "通过申请并创建学生目录？" : "拒绝该申请？")) return;
  const response = await api(`/requests/${button.dataset.review}/review`, {method: "POST", json: {approve}});
  note(response.ok ? "申请已处理" : await detail(response)); await loadOverview();
});

$("announcementForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await api("/announcements", {method: "POST", json: {class_id: Number($("announcementClass").value), title: $("announcementTitle").value, content: $("announcementContent").value}});
  note(response.ok ? "公告已发布" : await detail(response)); if (response.ok) event.target.reset();
});

$("studentSelect").addEventListener("change", () => loadFiles(""));
$("upBtn").addEventListener("click", () => loadFiles(path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : ""));
$("mkdirBtn").addEventListener("click", async () => { const name = prompt("文件夹名称"); if (!name) return; await api(`/students/${$("studentSelect").value}/mkdir`, {method: "POST", json: {path, name}}); loadFiles(path); });
$("uploadBtn").addEventListener("click", () => $("uploadInput").click());
$("uploadInput").addEventListener("change", async (event) => { const form = new FormData(); form.append("path", path); [...event.target.files].forEach((file) => { form.append("files", file); form.append("relative_paths", file.name); }); await api(`/students/${$("studentSelect").value}/upload`, {method: "POST", body: form}); event.target.value = ""; loadFiles(path); });

async function loadFiles(next) {
  const id = $("studentSelect").value; if (!id) { $("fileRows").innerHTML = ""; return; }
  const response = await api(`/students/${id}/files?path=${encodeURIComponent(next)}`); if (!response.ok) return;
  const data = await response.json(); path = data.path; $("pathLabel").textContent = "/" + path;
  $("fileRows").innerHTML = data.entries.map((item) => `<tr><td>${item.type === "folder" ? `<button class="folder" data-open="${esc(item.path)}">📁 ${esc(item.name)}</button>` : esc(item.name)}</td><td>${item.type === "folder" ? "文件夹" : "文件"}</td><td>${esc(item.content_display)}</td><td>${esc(item.size_display)}</td><td>${item.type === "file" ? `<button data-download="${esc(item.path)}">下载</button> ` : ""}<button data-rename="${esc(item.path)}" data-name="${esc(item.name)}">改名</button> <button class="danger" data-delete="${esc(item.path)}">删除</button></td></tr>`).join("");
}

$("fileRows").addEventListener("click", async (event) => {
  const id = $("studentSelect").value; const button = event.target.closest("button"); if (!button) return;
  if (button.dataset.open) return loadFiles(button.dataset.open);
  if (button.dataset.rename) { const name = prompt("新名称", button.dataset.name); if (name) { await api(`/students/${id}/rename`, {method: "POST", json: {path: button.dataset.rename, name}}); loadFiles(path); } }
  if (button.dataset.delete && confirm("删除后将进入统一回收站，确认？")) { await api(`/students/${id}/delete`, {method: "POST", json: {path: button.dataset.delete}}); loadFiles(path); }
  if (button.dataset.download) { const response = await api(`/students/${id}/download?path=${encodeURIComponent(button.dataset.download)}`); const blob = await response.blob(); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = button.dataset.download.split("/").pop(); link.click(); URL.revokeObjectURL(link.href); }
});

function logType(content) {
  const action = String(content).split("：", 1)[0];
  for (const [prefix, label] of [["上传","上传"],["新建","新建"],["下载","下载"],["批量下载","下载"],["移动","移动"],["重命名","重命名"],["删除","删除"],["恢复","恢复"]]) if (action.startsWith(prefix)) return label;
  return "其他";
}

async function loadLogs() {
  const params = new URLSearchParams({action: $("logAction").value, page: String(logPage), page_size: $("logPageSize").value});
  if ($("logClass").value) params.set("class_id", $("logClass").value);
  if ($("logStudent").value) params.set("user_id", $("logStudent").value);
  if ($("logDate").value) params.set("date", $("logDate").value);
  const response = await api(`/logs?${params}`); if (!response.ok) return;
  const data = await response.json(); logPage = data.page; logTotalPages = data.total_pages;
  $("logTotal").textContent = `共 ${data.total} 条`;
  $("logPage").textContent = `第 ${data.page} / ${data.total_pages} 页`;
  $("logPrev").disabled = data.page <= 1; $("logNext").disabled = data.page >= data.total_pages;
  $("logRows").innerHTML = data.items.map((item) => `<tr><td>${new Date(item.created_at).toLocaleString()}</td><td>${esc(item.class_name)}</td><td>${esc(item.username)}</td><td>${logType(item.content)}</td><td>${esc(item.content)}</td></tr>`).join("") || `<tr><td colspan="5" class="muted">没有符合条件的日志</td></tr>`;
}

$("logClass").addEventListener("change", () => { renderLogStudents(); logPage = 1; loadLogs(); });
for (const id of ["logStudent", "logAction", "logDate", "logPageSize"]) $(id).addEventListener("change", () => { logPage = 1; loadLogs(); });
$("clearLogDate").addEventListener("click", () => { $("logDate").value = ""; logPage = 1; loadLogs(); });
$("refreshLogs").addEventListener("click", loadLogs);
$("logPrev").addEventListener("click", () => { if (logPage > 1) { logPage--; loadLogs(); } });
$("logNext").addEventListener("click", () => { if (logPage < logTotalPages) { logPage++; loadLogs(); } });

async function loadRecycle() {
  const response = await api("/recycle"); if (!response.ok) return;
  const data = await response.json();
  $("recycleRows").innerHTML = data.items.map((item) => `<tr><td>${esc(item.class_name)}</td><td>${esc(item.username)}</td><td>${esc(item.original_path)}</td><td>${new Date(item.deleted_at).toLocaleString()}</td><td><button data-restore="${item.id}" data-user="${item.user_id}">恢复</button></td></tr>`).join("") || `<tr><td colspan="5">回收站为空</td></tr>`;
}

$("recycleRows").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-restore]"); if (!button) return;
  const response = await api(`/recycle/${button.dataset.restore}/restore`, {method: "POST", json: {user_id: Number(button.dataset.user)}});
  note(response.ok ? "已恢复到学生原目录" : await detail(response)); loadRecycle();
});

if (token) {
  $("login").classList.add("hidden"); $("app").classList.remove("hidden"); loadOverview();
}
