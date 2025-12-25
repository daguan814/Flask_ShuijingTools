// 链接自动识别函数
function autoLink(text) {
    // URL正则表达式
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    
    // 将URL替换为链接
    return text.replace(urlRegex, function(url) {
        return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + url + '</a>';
    });
}

// 页面加载完成后处理所有文本内容
document.addEventListener('DOMContentLoaded', function() {
    // 获取所有文本内容元素
    const textElements = document.querySelectorAll('.text-content');
    
    textElements.forEach(function(element) {
        // 获取原始文本内容
        const originalText = element.textContent || element.innerText;
        
        // 处理链接并更新HTML
        element.innerHTML = autoLink(originalText);
    });
});