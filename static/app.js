// Frontier Tracker - 前端逻辑

const API_BASE = window.location.origin;
let codeSent = false;
let timerInterval = null;

// DOM 元素
const loginSection = document.getElementById('login-section');
const dashboardSection = document.getElementById('dashboard-section');
const loginForm = document.getElementById('login-form');
const emailInput = document.getElementById('email-input');
const codeInput = document.getElementById('code-input');
const codeSection = document.getElementById('code-section');
const submitBtn = document.getElementById('submit-btn');
const messageDiv = document.getElementById('message');
const queryMessageDiv = document.getElementById('query-message');
const queryBtn = document.getElementById('query-btn');
const logoutBtn = document.getElementById('logout-btn');
const loadingDiv = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');
const timerDiv = document.getElementById('timer');
const timerCount = document.getElementById('timer-count');
const userEmailSpan = document.getElementById('user-email');

// 页面加载时检查登录状态
async function checkLoginStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/me`);
        const data = await response.json();

        if (data.logged_in) {
            showDashboard(data.email);
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
function showDashboard(email) {
    loginSection.style.display = 'none';
    dashboardSection.style.display = 'block';
    userEmailSpan.textContent = email;
}

// 显示消息
function showMessage(element, text, type = 'info') {
    element.textContent = text;
    element.className = `message ${type}`;
    element.style.display = 'block';

    // 5秒后自动隐藏
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

// 显示/隐藏加载
function setLoading(show, text = '加载中...') {
    loadingDiv.style.display = show ? 'block' : 'none';
    loadingText.textContent = text;
    loginSection.style.display = show ? 'none' : loginSection.style.display;
    dashboardSection.style.display = show ? 'none' : dashboardSection.style.display;
}

// 倒计时
function startTimer() {
    let seconds = 600; // 10分钟
    timerDiv.style.display = 'block';

    timerInterval = setInterval(() => {
        seconds--;
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        timerCount.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;

        if (seconds <= 0) {
            clearInterval(timerInterval);
            timerCount.textContent = '已过期';
        }
    }, 1000);
}

// 表单提交
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = emailInput.value;

    if (!codeSent) {
        // 发送验证码
        await sendCode(email);
    } else {
        // 验证登录
        await verifyLogin(email, codeInput.value);
    }
});

// 发送验证码
async function sendCode(email) {
    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '发送中...';

        const response = await fetch(`${API_BASE}/api/send-code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (response.ok) {
            codeSent = true;
            codeSection.style.display = 'block';
            submitBtn.textContent = '验证登录';
            emailInput.disabled = true;
            codeInput.focus();
            showMessage(messageDiv, '验证码已发送，请查收邮件', 'success');
            startTimer();
        } else {
            showMessage(messageDiv, data.detail || '发送失败，请重试', 'error');
        }
    } catch (error) {
        console.error('发送验证码失败:', error);
        showMessage(messageDiv, '网络错误，请重试', 'error');
    } finally {
        submitBtn.disabled = false;
    }
}

// 验证登录
async function verifyLogin(email, code) {
    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '验证中...';

        const response = await fetch(`${API_BASE}/api/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, code })
        });

        const data = await response.json();

        if (response.ok) {
            clearInterval(timerInterval);
            showMessage(messageDiv, '登录成功！', 'success');
            setTimeout(() => showDashboard(email), 500);
        } else {
            showMessage(messageDiv, data.detail || '验证码错误或已过期', 'error');
        }
    } catch (error) {
        console.error('验证失败:', error);
        showMessage(messageDiv, '网络错误，请重试', 'error');
    } finally {
        submitBtn.disabled = false;
    }
}

// 查询航班
queryBtn.addEventListener('click', async () => {
    try {
        queryBtn.disabled = true;
        queryBtn.textContent = '查询中...';
        setLoading(true, '正在查询航班价格，请稍候...');

        const response = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: userEmailSpan.textContent })
        });

        const data = await response.json();

        setLoading(false);

        if (response.ok) {
            showMessage(queryMessageDiv, '✅ 报告已发送到您的邮箱！', 'success');
        } else {
            showMessage(queryMessageDiv, data.detail || '查询失败，请重试', 'error');
        }
    } catch (error) {
        console.error('查询失败:', error);
        setLoading(false);
        showMessage(queryMessageDiv, '网络错误，请重试', 'error');
    } finally {
        queryBtn.disabled = false;
        queryBtn.textContent = '🚀 查询航班';
    }
});

// 登出
logoutBtn.addEventListener('click', async () => {
    try {
        await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
        codeSent = false;
        emailInput.value = '';
        emailInput.disabled = false;
        codeInput.value = '';
        codeSection.style.display = 'none';
        submitBtn.textContent = '发送验证码';
        showMessage(messageDiv, '已登出', 'info');
        showLogin();
    } catch (error) {
        console.error('登出失败:', error);
    }
});

// 初始化
checkLoginStatus();
