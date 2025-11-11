// 全局变量
let wordList = []; // 存储单词列表
let fuse; // Fuse.js 搜索实例
let isLoading = true; // 加载状态

// 创建弹出窗口和背景
function createPopup() {
    const backdrop = document.createElement('div');
    backdrop.className = 'popup-backdrop';
    document.body.appendChild(backdrop);
    
    const popup = document.createElement('div');
    popup.className = 'popup-window';
    
    const popupHeader = document.createElement('div');
    popupHeader.className = 'popup-header';
    
    const popupTitle = document.createElement('h3');
    popupTitle.className = 'popup-title';
    popupTitle.textContent = '单词详情';
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'close-btn';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', closePopup);
    
    const popupContent = document.createElement('div');
    popupContent.className = 'popup-content';
    popupContent.id = 'popupContent';
    
    popupHeader.appendChild(popupTitle);
    popupHeader.appendChild(closeBtn);
    popup.appendChild(popupHeader);
    popup.appendChild(popupContent);
    document.body.appendChild(popup);
    
    // 点击背景关闭弹出窗口
    backdrop.addEventListener('click', closePopup);
    
    // 阻止冒泡，避免点击弹出窗口内容也关闭窗口
    popup.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    
    // 添加ESC键退出功能
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePopup();
        }
    });
}

// 打开弹出窗口
function openPopup(fileUrl, title) {
    const popup = document.querySelector('.popup-window');
    const backdrop = document.querySelector('.popup-backdrop');
    const popupTitle = document.querySelector('.popup-title');
    const popupContent = document.getElementById('popupContent');
    
    // 设置标题
    popupTitle.textContent = title || fileUrl;
    
    // 显示加载状态
    popupContent.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="sr-only">加载中...</span>
            </div>
            <p class="mt-2 text-muted">正在加载内容...</p>
        </div>
    `;
    
    // 显示弹出窗口
    popup.style.display = 'flex';
    backdrop.style.display = 'block';
    
    // 修改：使用绝对路径加载HTML文件
    // 去掉前面的./，并添加绝对路径前缀
    const absoluteUrl = '/static/search_words/' + fileUrl.replace('./', '');
    
    // 加载HTML内容
    fetch(absoluteUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常');
            }
            return response.text();
        })
        .then(html => {
            // 在弹出窗口中显示HTML内容
            popupContent.innerHTML = html;
        })
        .catch(error => {
            console.error('加载内容失败:', error);
            popupContent.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-exclamation-circle text-danger" style="font-size: 3rem;"></i>
                    <p class="mt-2 text-danger">加载失败，请稍后重试</p>
                </div>
            `;
        });
}

// 关闭弹出窗口
function closePopup() {
    const popup = document.querySelector('.popup-window');
    const backdrop = document.querySelector('.popup-backdrop');
    
    popup.style.display = 'none';
    backdrop.style.display = 'none';
}

// 初始化 Fuse.js 搜索
function initFuseSearch(data) {
    // 配置 Fuse.js 选项
    const options = {
        includeScore: true,
        keys: [
            { name: 'title', weight: 1 },
            // 可以添加更多字段进行搜索
        ],
        threshold: 0.3, // 搜索灵敏度，值越小越精确
        ignoreLocation: true, // 忽略单词位置
        findAllMatches: true, // 找到所有匹配项
        minMatchCharLength: 1 // 最小匹配字符长度
    };
    
    // 创建 Fuse.js 实例
    fuse = new Fuse(data, options);
}

// 搜索功能
function search(query) {
    if (!query || query.trim() === '' || !fuse) {
        return [];
    }
    
    // 使用 Fuse.js 进行模糊搜索
    const results = fuse.search(query);
    
    // 提取匹配的项目
    return results.map(result => result.item);
}

// 显示搜索结果
function displayResults(results) {
    const resultsList = document.getElementById('resultsList');
    const emptyState = document.getElementById('emptyState');
    const resultsCount = document.getElementById('resultsCount');
    
    // 清空结果列表
    resultsList.innerHTML = '';
    
    // 更新结果数量
    resultsCount.textContent = `找到 ${results.length} 个结果`;
    
    // 显示或隐藏空状态
    if (results.length === 0) {
        emptyState.style.display = 'block';
        resultsList.style.display = 'none';
        
        // 如果是在加载完成后搜索无结果，显示不同的提示
        if (!isLoading) {
            emptyState.innerHTML = `
                <i class="fas fa-book-open text-muted" style="font-size: 3rem;"></i>
                <p class="mt-3 text-muted">没有找到相关结果</p>
            `;
        }
    } else {
        emptyState.style.display = 'none';
        resultsList.style.display = 'block';
        
        // 添加搜索结果
        results.forEach(item => {
            // 从标题中提取关键词（去掉编号部分）
            const pattern = /「([^」]+)」/;
            const match = item.title.match(pattern);
            const keyword = match ? match[1] : item.title;
            
            const listItem = document.createElement('li');
            listItem.className = 'list-group-item';
            listItem.innerHTML = `
                <div class="result-title">${keyword}</div>
                <div class="result-filename">${item.title}</div>
                <span class="badge badge-primary">查看</span>
            `;
            
            // 添加点击事件
            listItem.addEventListener('click', function() {
                openPopup(item.url, keyword);
            });
            
            resultsList.appendChild(listItem);
        });
    }
}

// 加载单词列表
function loadWordList() {
    const searchInfo = document.getElementById('searchInfo');
    
    // 显示加载状态
    searchInfo.textContent = '正在加载单词库，请稍候...';
    
    // 加载 words.json 文件
    fetch('/static/search_words/words.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('加载单词库失败');
            }
            return response.json();
        })
        .then(data => {
            wordList = data;
            
            // 初始化 Fuse.js 搜索
            initFuseSearch(wordList);
            
            // 更新加载状态
            isLoading = false;
            searchInfo.textContent = '输入关键词后按回车或点击搜索按钮开始搜索';
            
            // 显示所有单词（这是新增的代码）
            displayResults(wordList);
            
            console.log(`成功加载 ${wordList.length} 个单词文件`);
        })
        .catch(error => {
            console.error('加载单词库时出错:', error);
            searchInfo.textContent = '加载单词库失败，请刷新页面重试';
            
            const emptyState = document.getElementById('emptyState');
            emptyState.innerHTML = `
                <i class="fas fa-exclamation-circle text-danger" style="font-size: 3rem;"></i>
                <p class="mt-3 text-danger">加载单词库失败</p>
                <p class="text-muted">请刷新页面重试</p>
            `;
        });
}

// 初始化搜索功能
function initSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const searchInfo = document.getElementById('searchInfo');
    
    // 创建弹出窗口
    createPopup();
    
    // 加载单词列表
    loadWordList();
    
    // 搜索按钮点击事件
    searchBtn.addEventListener('click', function() {
        const query = searchInput.value.trim();
        if (query) {
            searchInfo.textContent = `正在搜索: "${query}"`;
            const results = search(query);
            displayResults(results);
        } else {
            // 修改：当输入为空时显示所有单词，而不是空结果
            searchInfo.textContent = '显示所有单词';
            displayResults(wordList);
        }
    });
    
    // 回车键搜索
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchBtn.click();
        }
    });
    
    // 输入时更新提示信息
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        if (query) {
            searchInfo.textContent = `按回车或点击搜索按钮查找包含 "${query}" 的内容`;
        } else if (!isLoading) {
            searchInfo.textContent = '输入关键词后按回车或点击搜索按钮开始搜索';
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initSearch);