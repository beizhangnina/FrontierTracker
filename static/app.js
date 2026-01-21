// Frontier Tracker - 前端逻辑 (密码登录)

const API_BASE = window.location.origin;

// DOM 元素
const loginSection = document.getElementById('login-section');
const dashboardSection = document.getElementById('dashboard-section');
const loginForm = document.getElementById('login-form');
const passwordInput = document.getElementById('password-input');
const emailInput = document.getElementById('email-input');
const queryForm = document.getElementById('query-form');
const messageDiv = document.getElementById('message');
const queryMessageDiv = document.getElementById('query-message');
const logoutBtn = document.getElementById('logout-btn');
const loadingDiv = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');

// 页面加载时检查登录状态
async function checkLoginStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/me`);
        const data = await response.json();

        if (data.logged_in) {
            showDashboard();
        } else {
            showLogin();
        }
    } catch (error) {
        console.error('检查登录状态失败:', error);
        showLogin();
    }
}

// 显示登录界面
function showLogin() {
    loginSection.style.display = 'block';
    dashboardSection.style.display = 'none';
}

// 显示仪表盘
function showDashboard() {
    loginSection.style.display = 'none';
    dashboardSection.style.display = 'block';
}

// 显示消息
function showMessage(element, text, type = 'info') {
    element.textContent = text;
    element.className = `message ${type}`;
    element.style.display = 'block';

    // 5秒后自动隐藏
    setTimeout(() => {
        if (element === messageDiv || type === 'success') {
            element.style.display = 'none';
        }
    }, 5000);
}

// 显示/隐藏加载
function setLoading(show, text = '加载中...') {
    loadingDiv.style.display = show ? 'block' : 'none';
    loadingText.textContent = text;
    loginSection.style.display = show ? 'none' : loginSection.style.display;
    dashboardSection.style.display = show ? 'none' : dashboardSection.style.display;
}

// 登录表单
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const password = passwordInput.value;

    try {
        const submitBtn = document.getElementById('login-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = '登录中...';

        const response = await fetch(`${API_BASE}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showMessage(messageDiv, '登录成功！', 'success');
            setTimeout(() => showDashboard(), 500);
        } else {
            showMessage(messageDiv, '密码错误', 'error');
        }
    } catch (error) {
        console.error('登录失败:', error);
        showMessage(messageDiv, '网络错误，请重试', 'error');
    } finally {
        const submitBtn = document.getElementById('login-btn');
        submitBtn.disabled = false;
        submitBtn.textContent = '登录';
    }
});

// 查询航班
queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = emailInput.value;

    try {
        setLoading(true, '正在查询航班价格，请稍候...');

        const response = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        setLoading(false);

        if (response.ok && data.success) {
            showMessage(queryMessageDiv, '✅ ' + data.message, 'success');
        } else {
            showMessage(queryMessageDiv, data.detail || data.message || '查询失败，请重试', 'error');
        }
    } catch (error) {
        console.error('查询失败:', error);
        setLoading(false);
        showMessage(queryMessageDiv, '网络错误，请重试', 'error');
    }
});

// 登出
logoutBtn.addEventListener('click', async () => {
    try {
        await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
        passwordInput.value = '';
        showMessage(messageDiv, '已登出', 'info');
        showLogin();
    } catch (error) {
        console.error('登出失败:', error);
    }
});

// 初始化
checkLoginStatus();
