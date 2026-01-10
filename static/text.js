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
    document.getElementById('lockScreen').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';

    processTextContent();
    initModeSwitch();
    initUploadForm();
    initDeleteForms();
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

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
