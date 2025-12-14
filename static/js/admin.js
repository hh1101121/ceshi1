class AdminApp {
    constructor() {
        this.isLoggedIn = false;
        this.adminPassword = '';

        this.initElements();
        this.bindEvents();
        this.checkLoginStatus();
    }

    initElements() {
        this.loginContainer = document.getElementById('loginContainer');
        this.profileContainer = document.getElementById('profileContainer');
        this.adminPasswordInput = document.getElementById('adminPassword');
        this.loginBtn = document.getElementById('loginBtn');
        this.baiduCookie = document.getElementById('baiduCookie');
        this.quarkCookie = document.getElementById('quarkCookie');
        this.updateBaiduBtn = document.getElementById('updateBaiduBtn');
        this.updateQuarkBtn = document.getElementById('updateQuarkBtn');
        this.logoutBtn = document.getElementById('logoutBtn');
    }

    bindEvents() {
        this.loginBtn.addEventListener('click', () => this.login());
        this.adminPasswordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.login();
            }
        });
        this.updateBaiduBtn.addEventListener('click', () => this.updateBaiduCookie());
        this.updateQuarkBtn.addEventListener('click', () => this.updateQuarkCookie());
        this.logoutBtn.addEventListener('click', () => this.logout());
    }

    checkLoginStatus() {
        // 检查本地存储的登录状态
        const token = localStorage.getItem('admin_token');
        if (token) {
            this.isLoggedIn = true;
            this.showProfile();
            // 可以在这里加载现有的cookie配置
            this.loadCookies();
        }
    }

    async login() {
        this.adminPassword = this.adminPasswordInput.value;
        if (!this.adminPassword) {
            alert('请输入管理员密码');
            return;
        }

        // 简单的密码验证（实际应使用更安全的方式）
        // 这里假设后端有一个验证接口
        try {
            // 模拟登录验证
            if (this.adminPassword === 'admin123') { // 实际应该调用后端API验证
                this.isLoggedIn = true;
                localStorage.setItem('admin_token', 'logged_in');
                this.showProfile();
                this.loadCookies();
            } else {
                alert('密码错误');
            }
        } catch (error) {
            console.error('登录出错:', error);
            alert('登录失败，请稍后重试');
        }
    }

    showProfile() {
        this.loginContainer.classList.add('hidden');
        this.profileContainer.classList.remove('hidden');
    }

    hideProfile() {
        this.loginContainer.classList.remove('hidden');
        this.profileContainer.classList.add('hidden');
        this.adminPasswordInput.value = '';
    }

    async loadCookies() {
        // 这里可以调用后端接口加载现有的cookie配置
        // 暂时使用模拟数据
        console.log('加载cookie配置...');
        // 实际实现应该调用后端API获取当前配置
    }

    async updateBaiduCookie() {
        const cookieValue = this.baiduCookie.value.trim();
        if (!cookieValue) {
            alert('请输入百度网盘Cookie');
            return;
        }

        try {
            // 调用后端更新配置接口
            const response = await fetch('/update_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    config_type: 'baidu_cookie',
                    cookie_value: cookieValue
                })
            });

            if (response.ok) {
                alert('百度Cookie更新成功');
            } else {
                alert('百度Cookie更新失败');
            }
        } catch (error) {
            console.error('更新百度Cookie出错:', error);
            alert('更新失败，请稍后重试');
        }
    }

    async updateQuarkCookie() {
        const cookieValue = this.quarkCookie.value.trim();
        if (!cookieValue) {
            alert('请输入夸克网盘Cookie');
            return;
        }

        try {
            // 调用后端更新配置接口
            const response = await fetch('/update_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    config_type: 'cookie',
                    cookie_value: cookieValue
                })
            });

            if (response.ok) {
                alert('夸克Cookie更新成功');
            } else {
                alert('夸克Cookie更新失败');
            }
        } catch (error) {
            console.error('更新夸克Cookie出错:', error);
            alert('更新失败，请稍后重试');
        }
    }

    logout() {
        this.isLoggedIn = false;
        localStorage.removeItem('admin_token');
        this.hideProfile();
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new AdminApp();
});
