// Frontier Tracker - 前端逻辑 (密码登录)

const API_BASE = window.location.origin;

// DOM 元素
const loginSection = document.getElementById('login-section');
const dashboardSection = document.getElementById('dashboard-section');
const loginForm = document.getElementById('login-form');
const passwordInput = document.getElementById('password-input');
const queryForm = document.getElementById('query-form');
const messageDiv = document.getElementById('message');
const queryMessageDiv = document.getElementById('query-message');
const logoutBtn = document.getElementById('logout-btn');
const resultsDiv = document.getElementById('results');

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

// HTML 转义，防止注入
function esc(value) {
    return String(value).replace(/[&<>"']/g, (c) => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
}

// 渲染一个价格单元格（带颜色分级）
function priceCell(value, low, mid) {
    if (value === 'N/A' || value === null || value === undefined) {
        return '<td class="price">N/A</td>';
    }
    const cls = value <= low ? 'price-low' : (value <= mid ? 'price-mid' : 'price-high');
    return `<td class="price ${cls}">$${esc(value)}</td>`;
}

// 渲染查询结果
function renderResults(data) {
    const routes = data.routes || [];
    if (routes.length === 0) {
        resultsDiv.innerHTML = '<div class="card"><p class="info-text">没有找到航班</p></div>';
        return;
    }

    let html = '';
    for (const route of routes) {
        let rows = '';
        for (const f of route.flights) {
            const best = f.is_best_price ? ' class="best-price"' : '';
            const nonstop = f.is_nonstop
                ? '<span class="nonstop-badge">Yes</span>'
                : '<span class="stop-badge">No</span>';
            rows += `<tr${best}>
                <td>${esc(f.date_display)}</td>
                <td class="route-${esc((f.origin || '').toLowerCase())}">${esc(f.flight_number)}</td>
                <td>${esc(f.departure_time)}</td>
                <td>${esc(f.arrival_time)}</td>
                <td>${esc(f.duration)}</td>
                <td>${nonstop}</td>
                ${priceCell(f.basic_fare, 50, 100)}
                ${priceCell(f.economy_bundle, 70, 120)}
                ${priceCell(f.premium_bundle, 120, 180)}
                ${priceCell(f.business_bundle, 200, 300)}
            </tr>`;
        }

        html += `<div class="card result-card">
            <h2 class="route-title">${esc(route.route)}</h2>
            <div class="table-wrap">
                <table class="result-table">
                    <thead>
                        <tr>
                            <th>Date</th><th>Flight</th><th>Depart</th><th>Arrive</th>
                            <th>Duration</th><th>Nonstop</th>
                            <th>Basic</th><th>Economy</th><th>Premium</th><th>Business</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
    }

    if (data.timestamp) {
        html += `<p class="results-timestamp">查询时间: ${esc(data.timestamp)}</p>`;
    }

    resultsDiv.innerHTML = html;
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

    const queryBtn = document.getElementById('query-btn');

    try {
        queryBtn.disabled = true;
        queryBtn.textContent = '⏳ 查询中…';
        queryMessageDiv.style.display = 'none';
        resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>正在查询航班价格，请稍候…</p></div>';

        const response = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok && data.success) {
            renderResults(data);
        } else {
            resultsDiv.innerHTML = '';
            showMessage(queryMessageDiv, data.detail || data.message || '查询失败，请重试', 'error');
        }
    } catch (error) {
        console.error('查询失败:', error);
        resultsDiv.innerHTML = '';
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
        passwordInput.value = '';
        resultsDiv.innerHTML = '';
        showMessage(messageDiv, '已登出', 'info');
        showLogin();
    } catch (error) {
        console.error('登出失败:', error);
    }
});

// 初始化
checkLoginStatus();
