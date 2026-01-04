// text.js
// 密码相关变量
const CORRECT_PASSWORD = '521';
let currentPassword = '';

// 页面加载时检查登录状态
document.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();
    
    // 添加键盘支持，只支持1-9
    document.addEventListener('keydown', function(event) {
        if (event.key >= '1' && event.key <= '9') {
            addNumber(parseInt(event.key));
        }
    });
});

// 检查是否已经登录
function checkLoginStatus() {
    const loginCookie = getCookie('text_system_login');
    if (loginCookie === 'true') {
        // 已登录，显示主内容
        showMainContent();
    }
}

// 获取Cookie
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// 设置Cookie
function setCookie(name, value, days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = `expires=${date.toUTCString()}`;
    document.cookie = `${name}=${value}; ${expires}; path=/`;
}

// 添加数字到密码
function addNumber(number) {
    currentPassword += number;
    updatePasswordDisplay();
    
    // 检查密码
    if (currentPassword.length === 3) {
        checkPassword();
    }
    
    // 错误输入达到6位，显示弹窗
    if (currentPassword.length === 6) {
        alert('密码错误');
        currentPassword = '';
        updatePasswordDisplay();
    }
}

// 更新密码显示（只显示圆点）
function updatePasswordDisplay() {
    const display = document.getElementById('passwordDisplay');
    let dots = '';
    for (let i = 0; i < currentPassword.length; i++) {
        dots += '•';
    }
    display.textContent = dots || '••••';
    display.className = 'password-dots';
}

// 检查密码
function checkPassword() {
    if (currentPassword === CORRECT_PASSWORD) {
        // 密码正确，保存30天登录状态
        setCookie('text_system_login', 'true', 30);
        // 显示主内容
        showMainContent();
    }
    // 密码错误不立即提示，继续输入直到6位
}

// 显示主内容
function showMainContent() {
    document.getElementById('lockScreen').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';
    
    // 处理文本内容中的链接
    processTextContent();
}

// 处理文本内容中的链接
function processTextContent() {
    // URL正则表达式
    function autoLink(text) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        // 将URL替换为链接
        return text.replace(urlRegex, function(url) {
            return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + url + '</a>';
        });
    }

    // 获取所有文本内容元素
    const textElements = document.querySelectorAll('.text-content');
    
    textElements.forEach(function(element) {
        // 获取原始文本内容
        const originalText = element.textContent || element.innerText;
        
        // 处理链接并更新HTML
        element.innerHTML = autoLink(originalText);
    });
}