const API_BASE = '/api';

const api = {
    async request(url, options = {}) {
        const token = localStorage.getItem('auth_token') || 'mediaflow-default-token';
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        };
        try {
            const response = await fetch(`${API_BASE}${url}`, { ...defaultOptions, ...options });
            const data = await response.json();
            if (data.code !== 0 && data.code !== 200) {
                throw new Error(data.message || '请求失败');
            }
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    get(url) {
        return this.request(url, { method: 'GET' });
    },

    post(url, body) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    },

    put(url, body) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
    },

    delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

const app = {
    currentPage: 'dashboard',

    init() {
        this.bindEvents();
        this.loadPage('dashboard');
        this.loadStats();
        setInterval(() => this.loadStats(), 30000);
    },

    bindEvents() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.dataset.page;
                this.navigateTo(page);
            });
        });

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                this.switchTab(tab);
            });
        });

        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });

        document.getElementById('addBrushtask')?.addEventListener('click', () => this.showAddBrushtaskModal());
        document.getElementById('addSubscription')?.addEventListener('click', () => this.showAddSubscriptionModal());
        document.getElementById('addSite')?.addEventListener('click', () => this.showAddSiteModal());
        document.getElementById('signinAll')?.addEventListener('click', () => this.signinAllSites());
        document.getElementById('searchBtn')?.addEventListener('click', () => this.performSearch());
        document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });

        document.querySelector('.modal')?.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) this.closeModal();
        });
    },

    navigateTo(page) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === page);
        });

        const pages = document.querySelectorAll('.page');
        pages.forEach(p => {
            const pageName = p.id.replace('page', '').toLowerCase();
            p.classList.toggle('hidden', pageName !== page);
        });

        const titles = {
            dashboard: '仪表盘',
            brushtask: '刷流任务',
            search: '媒体搜索',
            subscription: 'RSS订阅',
            downloader: '下载器',
            sites: '站点管理',
            sync: '文件同步',
            settings: '设置'
        };
        document.getElementById('pageTitle').textContent = titles[page] || page;
        this.currentPage = page;
        this.loadPageData(page);
    },

    switchTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `tab${tab.charAt(0).toUpperCase() + tab.slice(1)}`);
        });
    },

    loadPage(page) {
        this.navigateTo(page);
    },

    async loadPageData(page) {
        switch (page) {
            case 'dashboard':
                await this.loadDashboardData();
                break;
            case 'brushtask':
                await this.loadBrushtasks();
                break;
            case 'subscription':
                await this.loadSubscriptions();
                break;
            case 'downloader':
                await this.loadDownloaders();
                break;
            case 'sites':
                await this.loadSites();
                break;
        }
    },

    async loadStats() {
        try {
            const [tasks, downloaders, sites] = await Promise.all([
                api.get('/brushtask/').catch(() => ({ data: [] })),
                api.get('/downloader/').catch(() => ({ data: [] })),
                api.get('/site/statistics').catch(() => ({ data: {} }))
            ]);

            const runningTasks = tasks.data?.filter(t => t.state === 'Y').length || 0;
            let totalTorrents = 0;
            downloaders.data?.forEach(d => {
                totalTorrents += d.torrents_count || 0;
            });

            document.getElementById('statTasks').textContent = runningTasks;
            document.getElementById('statTorrents').textContent = totalTorrents;
            document.getElementById('statSites').textContent = sites.data?.total_sites || 0;
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    },

    async loadDashboardData() {
        await this.loadStats();
        await this.loadActivities();
    },

    async loadActivities() {
        const activities = [
            { icon: 'check-circle', type: 'success', text: '系统运行正常', time: '刚刚' },
            { icon: 'download', type: 'info', text: '下载任务进行中', time: '5分钟前' }
        ];

        const html = activities.map(a => `
            <div class="activity-item">
                <i class="fas fa-${a.icon} ${a.type}"></i>
                <span>${a.text}</span>
                <small>${a.time}</small>
            </div>
        `).join('');

        document.getElementById('activityList').innerHTML = html || '<div class="activity-item">暂无活动</div>';
    },

    async loadBrushtasks() {
        try {
            const result = await api.get('/brushtask/');
            const tasks = result.data || [];

            const html = tasks.map(task => `
                <tr>
                    <td>${task.name}</td>
                    <td>站点 #${task.site_id}</td>
                    <td>下载器 #${task.downloader_id}</td>
                    <td><span class="status-badge ${task.state === 'Y' ? 'running' : 'stopped'}">${task.state === 'Y' ? '运行中' : '已停止'}</span></td>
                    <td>0</td>
                    <td>0</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="app.toggleBrushtask(${task.id}, '${task.state}')">
                            <i class="fas fa-${task.state === 'Y' ? 'pause' : 'play'}"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="app.deleteBrushtask(${task.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

            document.getElementById('brushtaskTable').innerHTML = html || '<tr><td colspan="7" class="text-center">暂无数据</td></tr>';
        } catch (error) {
            console.error('Failed to load brushtasks:', error);
        }
    },

    async loadSubscriptions() {
        try {
            const result = await api.get('/subscription/');
            const subs = result.data || [];

            const html = subs.map(sub => `
                <tr>
                    <td>${sub.name}</td>
                    <td>${sub.rss_url || '-'}</td>
                    <td>下载器 #${sub.downloader_id || '-'}</td>
                    <td><span class="status-badge ${sub.state === 'Y' ? 'running' : 'stopped'}">${sub.state === 'Y' ? '启用' : '禁用'}</span></td>
                    <td>${sub.auto_download ? '是' : '否'}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="app.deleteSubscription(${sub.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

            document.getElementById('subscriptionTable').innerHTML = html || '<tr><td colspan="6" class="text-center">暂无数据</td></tr>';
        } catch (error) {
            console.error('Failed to load subscriptions:', error);
        }
    },

    async loadDownloaders() {
        try {
            const result = await api.get('/downloader/');
            const downloaders = result.data || [];

            const html = downloaders.map(dl => `
                <div class="downloader-card">
                    <div class="downloader-header">
                        <h3>${dl.name}</h3>
                        <div class="downloader-status">
                            <span class="status-dot online"></span>
                            ${dl.enabled ? '在线' : '离线'}
                        </div>
                    </div>
                    <div class="downloader-stats">
                        <div class="downloader-stat">
                            <div class="value">${dl.torrents_count}</div>
                            <div class="label">种子数</div>
                        </div>
                        <div class="downloader-stat">
                            <div class="value">${this.formatSpeed(dl.download_speed)}</div>
                            <div class="label">下载速度</div>
                        </div>
                        <div class="downloader-stat">
                            <div class="value">${this.formatSpeed(dl.upload_speed)}</div>
                            <div class="label">上传速度</div>
                        </div>
                        <div class="downloader-stat">
                            <div class="value">${dl.type}</div>
                            <div class="label">类型</div>
                        </div>
                    </div>
                    <div class="downloader-actions">
                        <button class="btn btn-sm btn-primary" onclick="app.viewDownloaderTorrents(${dl.id})">
                            <i class="fas fa-list"></i> 种子列表
                        </button>
                    </div>
                </div>
            `).join('');

            document.getElementById('downloaderGrid').innerHTML = html || '<div class="empty-state"><p>暂无下载器</p></div>';
        } catch (error) {
            console.error('Failed to load downloaders:', error);
        }
    },

    async loadSites() {
        try {
            const result = await api.get('/site/');
            const sites = result.data?.sites || [];

            const html = sites.map(site => `
                <tr>
                    <td>${site.name}</td>
                    <td><a href="${site.url}" target="_blank">${site.url}</a></td>
                    <td>${site.user_class || '-'}</td>
                    <td>${site.bonus || '-'}</td>
                    <td>${this.formatSize(site.upload)}</td>
                    <td>${this.formatSize(site.download)}</td>
                    <td>${site.ratio || '-'}</td>
                    <td>${site.seeding || 0}</td>
                    <td>
                        <button class="btn btn-sm btn-success" onclick="app.signinSite(${site.id})">
                            <i class="fas fa-sign-in-alt"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="app.deleteSite(${site.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

            document.getElementById('sitesTable').innerHTML = html || '<tr><td colspan="9" class="text-center">暂无数据</td></tr>';
        } catch (error) {
            console.error('Failed to load sites:', error);
        }
    },

    async performSearch() {
        const keyword = document.getElementById('searchInput').value.trim();
        const mediaType = document.getElementById('searchType').value;

        if (!keyword) {
            this.showToast('请输入搜索关键词', 'warning');
            return;
        }

        try {
            const result = await api.get(`/search/?keyword=${encodeURIComponent(keyword)}&media_type=${mediaType}`);
            const results = result.data?.results || [];

            if (results.length === 0) {
                document.getElementById('searchResults').innerHTML = '<div class="empty-state"><i class="fas fa-search"></i><p>未找到相关结果</p></div>';
                return;
            }

            const html = results.map(r => `
                <div class="search-result-item">
                    <div class="result-info">
                        <h3>${r.title} ${r.year ? `(${r.year})` : ''}</h3>
                        <p>${r.overview?.substring(0, 100)}...</p>
                        <div class="result-meta">
                            <span><i class="fas fa-film"></i> ${r.media_type}</span>
                            <span><i class="fas fa-star"></i> ${r.score?.toFixed(1) || 'N/A'}</span>
                        </div>
                    </div>
                    <div class="result-actions">
                        <button class="btn btn-sm btn-primary" onclick="app.downloadTorrent('${r.torrents?.[0]?.torrent_url}')">
                            <i class="fas fa-download"></i> 下载
                        </button>
                    </div>
                </div>
            `).join('');

            document.getElementById('searchResults').innerHTML = html;
        } catch (error) {
            console.error('Search failed:', error);
            this.showToast('搜索失败', 'error');
        }
    },

    showAddBrushtaskModal() {
        this.showModal('新建刷流任务', `
            <div class="form-group">
                <label>任务名称</label>
                <input type="text" id="taskName" placeholder="输入任务名称">
            </div>
            <div class="form-group">
                <label>站点</label>
                <select id="taskSite"></select>
            </div>
            <div class="form-group">
                <label>下载器</label>
                <select id="taskDownloader"></select>
            </div>
            <div class="form-group">
                <label>执行间隔（分钟）</label>
                <input type="number" id="taskInterval" value="30">
            </div>
            <div class="form-group">
                <label>过滤规则（JSON）</label>
                <textarea id="taskFilter" rows="3" placeholder='{"include_keywords": [], "exclude_keywords": [], "size_min": 0}'></textarea>
            </div>
        `, [
            { text: '取消', class: 'btn-secondary', action: 'close' },
            { text: '创建', class: 'btn-primary', action: 'createBrushtask' }
        ]);
    },

    showAddSubscriptionModal() {
        this.showModal('新建订阅', `
            <div class="form-group">
                <label>订阅名称</label>
                <input type="text" id="subName" placeholder="输入订阅名称">
            </div>
            <div class="form-group">
                <label>RSS地址</label>
                <input type="url" id="subRss" placeholder="https://example.com/rss">
            </div>
            <div class="form-group">
                <label>下载器</label>
                <select id="subDownloader"></select>
            </div>
            <div class="form-group">
                <label>关键词过滤</label>
                <input type="text" id="subKeywords" placeholder="关键词1,关键词2">
            </div>
        `, [
            { text: '取消', class: 'btn-secondary', action: 'close' },
            { text: '创建', class: 'btn-primary', action: 'createSubscription' }
        ]);
    },

    showAddSiteModal() {
        this.showModal('添加站点', `
            <div class="form-group">
                <label>站点名称</label>
                <input type="text" id="siteName" placeholder="输入站点名称">
            </div>
            <div class="form-group">
                <label>站点URL</label>
                <input type="url" id="siteUrl" placeholder="https://example.com">
            </div>
            <div class="form-group">
                <label>Cookie</label>
                <textarea id="siteCookie" rows="3" placeholder="粘贴站点Cookie"></textarea>
            </div>
            <div class="form-group">
                <label>签到URL</label>
                <input type="url" id="siteSignUrl" placeholder="https://example.com/sign">
            </div>
            <div class="form-group">
                <label>RSS地址</label>
                <input type="url" id="siteRssUrl" placeholder="https://example.com/rss">
            </div>
        `, [
            { text: '取消', class: 'btn-secondary', action: 'close' },
            { text: '添加', class: 'btn-primary', action: 'createSite' }
        ]);
    },

    showModal(title, content, buttons) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').innerHTML = content;

        const footer = document.getElementById('modalFooter');
        footer.innerHTML = buttons.map(btn => `
            <button class="btn ${btn.class}" data-action="${btn.action}">${btn.text}</button>
        `).join('');

        footer.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (action === 'close') {
                    this.closeModal();
                } else {
                    this.handleModalAction(action);
                }
            });
        });

        document.getElementById('modalContainer').classList.add('active');
    },

    closeModal() {
        document.getElementById('modalContainer').classList.remove('active');
    },

    async handleModalAction(action) {
        switch (action) {
            case 'createBrushtask':
                await this.createBrushtask();
                break;
            case 'createSubscription':
                await this.createSubscription();
                break;
            case 'createSite':
                await this.createSite();
                break;
        }
    },

    async createBrushtask() {
        const name = document.getElementById('taskName').value;
        const site_id = parseInt(document.getElementById('taskSite').value) || 0;
        const downloader_id = parseInt(document.getElementById('taskDownloader').value) || 0;
        const interval = document.getElementById('taskInterval').value;
        const filter_rule = document.getElementById('taskFilter').value;

        try {
            await api.post('/brushtask/', { name, site_id, downloader_id, interval, filter_rule, state: 'S' });
            this.showToast('创建成功', 'success');
            this.closeModal();
            await this.loadBrushtasks();
        } catch (error) {
            this.showToast('创建失败', 'error');
        }
    },

    async createSubscription() {
        const name = document.getElementById('subName').value;
        const rss_url = document.getElementById('subRss').value;
        const downloader_id = parseInt(document.getElementById('subDownloader').value) || 0;
        const keywords = document.getElementById('subKeywords').value;

        try {
            await api.post('/subscription/', { name, rss_url, downloader_id, keywords, state: 'Y' });
            this.showToast('创建成功', 'success');
            this.closeModal();
            await this.loadSubscriptions();
        } catch (error) {
            this.showToast('创建失败', 'error');
        }
    },

    async createSite() {
        const name = document.getElementById('siteName').value;
        const url = document.getElementById('siteUrl').value;
        const cookie = document.getElementById('siteCookie').value;
        const sign_url = document.getElementById('siteSignUrl').value;
        const rss_url = document.getElementById('siteRssUrl').value;

        try {
            await api.post('/site/', { name, url, cookie, sign_url, rss_url, enabled: true });
            this.showToast('添加成功', 'success');
            this.closeModal();
            await this.loadSites();
        } catch (error) {
            this.showToast('添加失败', 'error');
        }
    },

    async toggleBrushtask(id, currentState) {
        try {
            const action = currentState === 'Y' ? 'stop' : 'start';
            await api.post(`/brushtask/${id}/${action}`);
            this.showToast(`${action === 'start' ? '启动' : '停止'}成功`, 'success');
            await this.loadBrushtasks();
        } catch (error) {
            this.showToast('操作失败', 'error');
        }
    },

    async deleteBrushtask(id) {
        if (!confirm('确定要删除这个任务吗？')) return;
        try {
            await api.delete(`/brushtask/${id}`);
            this.showToast('删除成功', 'success');
            await this.loadBrushtasks();
        } catch (error) {
            this.showToast('删除失败', 'error');
        }
    },

    async deleteSubscription(id) {
        if (!confirm('确定要删除这个订阅吗？')) return;
        try {
            await api.delete(`/subscription/${id}`);
            this.showToast('删除成功', 'success');
            await this.loadSubscriptions();
        } catch (error) {
            this.showToast('删除失败', 'error');
        }
    },

    async signinSite(id) {
        try {
            const result = await api.post(`/site/${id}/signin`);
            const data = result.data;
            this.showToast(`${data.site_name}: ${data.message}`, data.success ? 'success' : 'error');
            await this.loadSites();
        } catch (error) {
            this.showToast('签到失败', 'error');
        }
    },

    async signinAllSites() {
        try {
            this.showToast('正在批量签到...', 'info');
            const result = await api.post('/site/signin/all');
            const data = result.data;
            const success = data.filter(r => r.success).length;
            this.showToast(`签到完成: ${success}/${data.length} 成功`, success > 0 ? 'success' : 'warning');
            await this.loadSites();
        } catch (error) {
            this.showToast('批量签到失败', 'error');
        }
    },

    async deleteSite(id) {
        if (!confirm('确定要删除这个站点吗？')) return;
        try {
            await api.delete(`/site/${id}`);
            this.showToast('删除成功', 'success');
            await this.loadSites();
        } catch (error) {
            this.showToast('删除失败', 'error');
        }
    },

    downloadTorrent(url) {
        if (!url) {
            this.showToast('无可用下载链接', 'warning');
            return;
        }
        this.showToast('已开始下载', 'success');
    },

    viewDownloaderTorrents(id) {
        this.showToast('功能开发中', 'info');
    },

    formatSize(bytes) {
        if (!bytes) return '-';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let i = 0;
        while (bytes >= 1024 && i < units.length - 1) {
            bytes /= 1024;
            i++;
        }
        return `${bytes.toFixed(2)} ${units[i]}`;
    },

    formatSpeed(bytes) {
        if (!bytes) return '0 B/s';
        const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
        let i = 0;
        while (bytes >= 1024 && i < units.length - 1) {
            bytes /= 1024;
            i++;
        }
        return `${bytes.toFixed(2)} ${units[i]}`;
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : type === 'warning' ? 'exclamation-circle' : 'info-circle'}"></i>${message}`;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
};

document.addEventListener('DOMContentLoaded', () => app.init());
