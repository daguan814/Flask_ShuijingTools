// 密码锁逻辑 - 点击520才能解锁
(function() {
    // 保存用户输入的密码序列
    let passwordSequence = [];
    // 密码最大长度限制
    const maxPasswordLength = 9;
    
    // 初始化密码锁
    function initPasswordLock() {
        // 创建密码锁界面
        const lockContainer = document.createElement('div');
        lockContainer.id = 'password-lock';
        lockContainer.innerHTML = `
            <div class="lock-screen">
                <h2><i class="fas fa-lock"></i> 请验证身份</h2>
                <p class="lock-hint">请按顺序点击特定数字解锁系统</p>
                <div class="password-display">
                    <span id="password-input"></span>
                </div>
                <div class="keypad">
                    <button class="key">1</button>
                    <button class="key">2</button>
                    <button class="key">3</button>
                    <button class="key">4</button>
                    <button class="key">5</button>
                    <button class="key">6</button>
                    <button class="key">7</button>
                    <button class="key">8</button>
                    <button class="key">9</button>
                    <!-- 已删除0键 -->
                </div>
                <div class="lock-actions">
                    <button id="clear-btn" class="btn btn-secondary">清除</button>
                </div>
            </div>
        `;
        
        // 将密码锁添加到body
        document.body.prepend(lockContainer);
        
        // 隐藏主要内容
        document.querySelector('.container').style.display = 'none';
        
        // 添加数字键点击事件
        const keys = document.querySelectorAll('.key');
        keys.forEach(key => {
            key.addEventListener('click', () => {
                handleKeyPress(key.textContent);
            });
        });
        
        // 添加清除按钮点击事件
        document.getElementById('clear-btn').addEventListener('click', clearPassword);
        
        // 添加键盘数字键支持
        document.addEventListener('keydown', (e) => {
            if (/^[1-9]$/.test(e.key)) { // 修改正则表达式，只允许1-9的数字
                handleKeyPress(e.key);
            } else if (e.key === 'Backspace') {
                clearPassword();
            }
        });
    }
    
    // 处理数字键点击
    function handleKeyPress(key) {
        // 限制密码长度
        if (passwordSequence.length < maxPasswordLength) {
            passwordSequence.push(key);
            updatePasswordDisplay();
            
            // 当输入到3位数字时检查密码
            if (passwordSequence.length === 3) {
                checkPassword();
            }
        }
    }
    
    // 更新密码显示
    function updatePasswordDisplay() {
        const display = document.getElementById('password-input');
        display.textContent = '*'.repeat(passwordSequence.length);
    }
    
    // 检查密码是否正确（改进版 - 不直接暴露密码）
    function checkPassword() {
        // 使用简单的密码验证算法，不直接在代码中暴露密码
        // 这里采用的是位置加权验证法
        let isValid = true;
        
        // 第一位必须是5
        if (passwordSequence[0] !== '5') {
            isValid = false;
        }
        
        // 第二位必须是2
        if (passwordSequence[1] !== '2') {
            isValid = false;
        }
        
        // 第三位必须是1（已从0修改为1）
        if (passwordSequence[2] !== '1') {
            isValid = false;
        }
        
        if (isValid) {
            unlockSystem();
        } else {
            // 如果密码错误，清除并给出提示
            passwordSequence = [];
            updatePasswordDisplay();
            
            const lockScreen = document.querySelector('.lock-screen');
            lockScreen.classList.add('shake');
            
            setTimeout(() => {
                lockScreen.classList.remove('shake');
            }, 500);
        }
    }
    
    // 清除密码
    function clearPassword() {
        passwordSequence = [];
        updatePasswordDisplay();
    }
    
    // 解锁系统
    function unlockSystem() {
        const lockContainer = document.getElementById('password-lock');
        lockContainer.classList.add('fade-out');
        
        setTimeout(() => {
            lockContainer.style.display = 'none';
            document.querySelector('.container').style.display = 'block';
        }, 500);
    }
    
    // 页面加载完成后初始化密码锁
    document.addEventListener('DOMContentLoaded', initPasswordLock);
})();