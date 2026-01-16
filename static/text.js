// text.js
const CORRECT_PASSWORD = '521';
let currentPassword = '';

window.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();

    document.addEventListener('keydown', function(event) {
        if (event.key >= '1' && event.key <= '9') {
            addNumber(parseInt(event.key));
        }
    });
});

function checkLoginStatus() {
    const loginCookie = getCookie('text_system_login');
    if (loginCookie === 'true') {
        showMainContent();
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function setCookie(name, value, days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = `expires=${date.toUTCString()}`;
    document.cookie = `${name}=${value}; ${expires}; path=/`;
}

function addNumber(number) {
    currentPassword += number;
    updatePasswordDisplay();

    if (currentPassword.length === 3) {
        checkPassword();
    }

    if (currentPassword.length === 6) {
        alert('密码错误');
        currentPassword = '';
        updatePasswordDisplay();
    }
}

function updatePasswordDisplay() {
    const display = document.getElementById('passwordDisplay');
    let dots = '';
    for (let i = 0; i < currentPassword.length; i++) {
        dots += '•';
    }
    display.textContent = dots || '••••';
    display.className = 'password-dots';
}

function checkPassword() {
    if (currentPassword === CORRECT_PASSWORD) {
        setCookie('text_system_login', 'true', 30);
        showMainContent();
    }
}

function showMainContent() {
    document.documentElement.classList.add('logged-in');
    document.getElementById('lockScreen').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';

    processTextContent();
    initModeSwitch();
    initUploadForm();
    initDeleteForms();
    initTrashTrigger();
}

function processTextContent() {
    function autoLink(text) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        return text.replace(urlRegex, function(url) {
            return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + url + '</a>';
        });
    }

    const textElements = document.querySelectorAll('.text-content');
    textElements.forEach(function(element) {
        const originalText = element.textContent || element.innerText;
        element.innerHTML = autoLink(originalText);
    });
}

function initModeSwitch() {
    const switchEl = document.getElementById('modeSwitch');
    if (!switchEl) return;

    const buttons = switchEl.querySelectorAll('.mode-btn');
    buttons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            setMode(btn.dataset.target);
        });
    });

    const saved = localStorage.getItem('shuijing_mode') || 'text-section';
    setMode(saved);
}

function setMode(targetId) {
    const textSection = document.getElementById('text-section');
    const fileSection = document.getElementById('file-section');
    if (!textSection || !fileSection) return;

    textSection.classList.toggle('section-hidden', targetId !== 'text-section');
    fileSection.classList.toggle('section-hidden', targetId !== 'file-section');

    const buttons = document.querySelectorAll('.mode-btn');
    buttons.forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.target === targetId);
    });

    localStorage.setItem('shuijing_mode', targetId);
}

function initUploadForm() {
    const form = document.getElementById('uploadForm');
    if (!form) return;

    const filesInput = document.getElementById('uploadFiles');
    const fileHint = document.getElementById('fileHint');
    const fileNames = document.getElementById('fileNames');

    function renderSelected() {
        const files = filesInput && filesInput.files ? filesInput.files : [];
        if (fileHint) {
            fileHint.textContent = '已选择 ' + files.length + ' 个文件';
        }
        if (fileNames) {
            const list = Array.from(files).map(function(file) {
                return '<div>' + escapeHtml(file.name) + '</div>';
            }).join('');
            fileNames.innerHTML = list;
        }
    }

    if (filesInput) {
        filesInput.addEventListener('change', renderSelected);
        renderSelected();
    }

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        if (!filesInput || !filesInput.files || filesInput.files.length === 0) {
            return;
        }

        const progressWrap = document.getElementById('uploadProgress');
        const progressBar = document.getElementById('uploadProgressBar');
        const progressText = document.getElementById('uploadProgressText');
        const submitBtn = form.querySelector('button[type=submit]');
        if (submitBtn) submitBtn.disabled = true;

        const data = new FormData(form);
        const xhr = new XMLHttpRequest();
        xhr.open('POST', form.action);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        if (progressWrap && progressBar && progressText) {
            progressWrap.style.display = 'block';
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
        }

        xhr.upload.onprogress = function(evt) {
            if (!evt.lengthComputable || !progressBar || !progressText) return;
            const percent = Math.round((evt.loaded / evt.total) * 100);
            progressBar.style.width = percent + '%';
            progressText.textContent = percent + '%';
        };

        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                filesInput.value = '';
                renderSelected();
                refreshFileList();
            } else {
                alert('上传失败，请重试');
            }
        };

        xhr.onerror = function() {
            alert('上传失败，请重试');
        };

        xhr.onloadend = function() {
            if (submitBtn) submitBtn.disabled = false;
            if (progressWrap) {
                setTimeout(function() {
                    progressWrap.style.display = 'none';
                }, 600);
            }
        };

        xhr.send(data);
    });
}

function initDeleteForms() {
    const container = document.getElementById('fileList');
    if (!container) return;

    container.addEventListener('submit', function(event) {
        const form = event.target.closest('form.file-delete-form');
        if (!form) return;
        event.preventDefault();

        const data = new FormData(form);
        fetch(form.action, {
            method: 'POST',
            body: data,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).then(function() {
            refreshFileList();
        }).catch(function() {
            alert('删除失败，请重试');
        });
    });
}

function refreshFileList() {
    fetch('/api/files')
        .then(function(res) { return res.json(); })
        .then(function(files) { renderFileList(files); })
        .catch(function() {});
}

function refreshTextList() {
    fetch('/api/texts')
        .then(function(res) { return res.json(); })
        .then(function(texts) { renderTextList(texts); })
        .catch(function() {});
}

function renderFileList(files) {
    const container = document.getElementById('fileList');
    if (!container) return;

    if (!files || files.length === 0) {
        container.innerHTML = [
            '<div class="empty-state">',
            '<i class="bi bi-cloud-upload"></i>',
            '<h4>还没有上传任何文件</h4>',
            '<p>你可以在上方选择文件进行上传</p>',
            '</div>'
        ].join('');
        return;
    }

    const html = files.map(function(f) {
        return [
            '<div class="card text-card mb-3">',
            '<div class="card-body">',
            '<div class="d-flex justify-content-between align-items-start">',
            '<div class="flex-grow-1 me-3">',
            '<div class="text-content mb-2">' + escapeHtml(f.path) + '</div>',
            '<small class="text-muted"><i class="bi bi-hdd"></i> ' + escapeHtml(f.size) + '</small>',
            '</div>',
            '<div class="flex-shrink-0">',
            '<div class="file-actions">',
            '<a href="' + encodeURI('/files/download/' + f.path) + '" class="btn btn-outline-primary btn-sm">',
            '<i class="bi bi-download"></i> 下载</a>',
            '<form class="file-delete-form" action="/files/delete" method="POST">',
            '<input type="hidden" name="path" value="' + escapeHtml(f.path) + '">',
            '<button type="submit" class="btn btn-outline-danger btn-sm">',
            '<i class="bi bi-trash"></i> 删除</button>',
            '</form>',
            '</div>',
            '</div>',
            '</div>',
            '</div>',
            '</div>'
        ].join('');
    }).join('');

    container.innerHTML = html;
}

function renderTextList(texts) {
    const container = document.getElementById('textList');
    if (!container) return;

    if (!texts || texts.length === 0) {
        container.innerHTML = [
            '<div class="empty-state">',
            '<i class="bi bi-journal-text"></i>',
            '<h4>还没有保存任何文本</h4>',
            '<p>在上方输入框中添加您的第一条文本吧</p>',
            '</div>'
        ].join('');
        return;
    }

    const html = texts.map(function(text) {
        return [
            '<div class="card text-card mb-3">',
            '<div class="card-body">',
            '<div class="d-flex justify-content-between align-items-start">',
            '<div class="flex-grow-1 me-3">',
            '<div class="text-content mb-2" id="text-content-' + text.id + '">',
            escapeHtml(text.content || ''),
            '</div>',
            '<small class="text-muted"><i class="bi bi-clock"></i> ' + escapeHtml(text.created_at || '') + '</small>',
            '</div>',
            '<div class="flex-shrink-0">',
            '<a href="/delete/' + text.id + '" class="btn btn-danger btn-sm">',
            '<i class="bi bi-trash"></i> 删除</a>',
            '</div>',
            '</div>',
            '</div>',
            '</div>'
        ].join('');
    }).join('');

    container.innerHTML = html;
    processTextContent();
}

function initTrashTrigger() {
    const title = document.getElementById('mainTitle');
    const closeBtn = document.getElementById('trashCloseBtn');
    const trashSection = document.getElementById('trash-section');
    if (!title || !trashSection) return;

    let clickCount = 0;
    let clickTimer = null;

    title.addEventListener('click', function() {
        clickCount += 1;
        if (clickCount === 1) {
            clickTimer = setTimeout(function() {
                clickCount = 0;
            }, 700);
        }
        if (clickCount === 3) {
            if (clickTimer) clearTimeout(clickTimer);
            clickCount = 0;
            openTrashSection();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            closeTrashSection();
        });
    }

    trashSection.addEventListener('click', function(event) {
        const btn = event.target.closest('button[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        if (!id) return;

        if (action === 'restore-text') {
            fetch('/trash/restore/text/' + id, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            }).then(function() {
                refreshTrash();
                refreshTextList();
            }).catch(function() {
                alert('还原失败，请重试');
            });
        }

        if (action === 'restore-file') {
            const data = new FormData();
            data.append('id', id);
            fetch('/trash/restore/file', {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: data
            }).then(function() {
                refreshTrash();
                refreshFileList();
            }).catch(function() {
                alert('还原失败，请重试');
            });
        }
    });
}

function openTrashSection() {
    const trashSection = document.getElementById('trash-section');
    const modeSwitch = document.getElementById('modeSwitch');
    if (!trashSection || !modeSwitch) return;

    const saved = localStorage.getItem('shuijing_mode') || 'text-section';
    localStorage.setItem('shuijing_last_mode', saved);
    modeSwitch.style.display = 'none';
    document.getElementById('text-section').classList.add('section-hidden');
    document.getElementById('file-section').classList.add('section-hidden');
    trashSection.classList.remove('section-hidden');
    refreshTrash();
}

function closeTrashSection() {
    const trashSection = document.getElementById('trash-section');
    const modeSwitch = document.getElementById('modeSwitch');
    if (!trashSection || !modeSwitch) return;

    trashSection.classList.add('section-hidden');
    modeSwitch.style.display = '';
    const lastMode = localStorage.getItem('shuijing_last_mode') || 'text-section';
    setMode(lastMode);
}

function refreshTrash() {
    fetch('/api/trash')
        .then(function(res) { return res.json(); })
        .then(function(data) { renderTrash(data); })
        .catch(function() {});
}

function renderTrash(data) {
    renderTrashTexts(data && data.texts ? data.texts : []);
    renderTrashFiles(data && data.files ? data.files : []);
}

function renderTrashTexts(texts) {
    const container = document.getElementById('trashTextList');
    if (!container) return;

    if (!texts || texts.length === 0) {
        container.innerHTML = [
            '<div class="empty-state">',
            '<i class="bi bi-journal-x"></i>',
            '<h4>没有已删除文本</h4>',
            '<p>删除的文本会出现在这里</p>',
            '</div>'
        ].join('');
        return;
    }

    const html = texts.map(function(text) {
        return [
            '<div class="card text-card mb-3">',
            '<div class="card-body">',
            '<div class="d-flex justify-content-between align-items-start">',
            '<div class="flex-grow-1 me-3">',
            '<div class="text-content mb-2">',
            escapeHtml(text.content || ''),
            '</div>',
            '<small class="text-muted"><i class="bi bi-clock"></i> ' + escapeHtml(text.created_at || '') + '</small>',
            '</div>',
            '<div class="flex-shrink-0">',
            '<button type="button" class="btn btn-outline-success btn-sm" data-action="restore-text" data-id="' + text.id + '">',
            '<i class="bi bi-arrow-counterclockwise"></i> 还原</button>',
            '</div>',
            '</div>',
            '</div>',
            '</div>'
        ].join('');
    }).join('');

    container.innerHTML = html;
    processTextContent();
}

function renderTrashFiles(files) {
    const container = document.getElementById('trashFileList');
    if (!container) return;

    if (!files || files.length === 0) {
        container.innerHTML = [
            '<div class="empty-state">',
            '<i class="bi bi-trash"></i>',
            '<h4>没有已删除文件</h4>',
            '<p>删除的文件会出现在这里</p>',
            '</div>'
        ].join('');
        return;
    }

    const html = files.map(function(file) {
        return [
            '<div class="card text-card mb-3">',
            '<div class="card-body">',
            '<div class="d-flex justify-content-between align-items-start">',
            '<div class="flex-grow-1 me-3">',
            '<div class="text-content mb-2">' + escapeHtml(file.original_path || '') + '</div>',
            '<small class="text-muted"><i class="bi bi-hdd"></i> ' + escapeHtml(file.size || '') + '</small>',
            '<div class="text-muted small mt-1"><i class="bi bi-clock"></i> ' + escapeHtml(file.deleted_at || '') + '</div>',
            '</div>',
            '<div class="flex-shrink-0">',
            '<button type="button" class="btn btn-outline-success btn-sm" data-action="restore-file" data-id="' + file.id + '">',
            '<i class="bi bi-arrow-counterclockwise"></i> 还原</button>',
            '</div>',
            '</div>',
            '</div>',
            '</div>'
        ].join('');
    }).join('');

    container.innerHTML = html;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
