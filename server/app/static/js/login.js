document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const errorMsg = document.getElementById('errorMsg');

    if (!username || !password) {
        errorMsg.textContent = '请输入用户名和密码';
        errorMsg.style.display = 'block';
        return;
    }

    try {
        const resp = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await resp.json();

        if (data.success) {
            window.location.href = data.redirect;
        } else {
            errorMsg.textContent = data.message || '登录失败';
            errorMsg.style.display = 'block';
        }
    } catch (err) {
        errorMsg.textContent = '网络错误，请检查连接';
        errorMsg.style.display = 'block';
    }
});
