/**
 * CappyAutoPost - Frontend JavaScript Controller
 * Cozy Capybara Onsen Theme & Custom Dialog Window System
 */

let currentSelectedImages = [];
let isCampaignRunning = false;

// Custom Dialog Promise Resolvers
let alertResolve = null;
let confirmResolve = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initCustomDialogs();
    waitForPyWebView();
});

function initCustomDialogs() {
    const btnAlertOk = document.getElementById('btn-dialog-alert-ok');
    if (btnAlertOk) {
        btnAlertOk.addEventListener('click', () => {
            closeModal('modal-custom-alert');
            if (alertResolve) { alertResolve(); alertResolve = null; }
        });
    }

    const btnConfirmOk = document.getElementById('btn-dialog-confirm-ok');
    const btnConfirmCancel = document.getElementById('btn-dialog-confirm-cancel');

    if (btnConfirmOk) {
        btnConfirmOk.addEventListener('click', () => {
            closeModal('modal-custom-confirm');
            if (confirmResolve) { confirmResolve(true); confirmResolve = null; }
        });
    }

    if (btnConfirmCancel) {
        btnConfirmCancel.addEventListener('click', () => {
            closeModal('modal-custom-confirm');
            if (confirmResolve) { confirmResolve(false); confirmResolve = null; }
        });
    }
}

// ── CUSTOM BEAUTIFUL POPUP WINDOWS ──
function showCustomAlert(title, message, type = 'info') {
    return new Promise((resolve) => {
        alertResolve = resolve;
        const iconMap = {
            'info': 'ℹ️',
            'success': '✨',
            'warning': '⚠️',
            'error': '❌'
        };
        const iconEl = document.getElementById('dialog-alert-icon');
        iconEl.className = `dialog-icon-wrapper ${type}`;
        iconEl.innerHTML = `<span>${iconMap[type] || 'ℹ️'}</span>`;
        document.getElementById('dialog-alert-title').innerText = title || 'Thông báo';
        document.getElementById('dialog-alert-message').innerText = message || '';
        openModal('modal-custom-alert');
    });
}

function showCustomConfirm(title, message, confirmText = 'Xác nhận', cancelText = 'Hủy bỏ', type = 'warning') {
    return new Promise((resolve) => {
        confirmResolve = resolve;
        const iconMap = {
            'warning': '⚠️',
            'error': '🗑️',
            'info': '❓'
        };
        const iconEl = document.getElementById('dialog-confirm-icon');
        iconEl.className = `dialog-icon-wrapper ${type}`;
        iconEl.innerHTML = `<span>${iconMap[type] || '⚠️'}</span>`;
        document.getElementById('dialog-confirm-title').innerText = title || 'Xác nhận';
        document.getElementById('dialog-confirm-message').innerText = message || '';
        
        const btnOk = document.getElementById('btn-dialog-confirm-ok');
        const btnCancel = document.getElementById('btn-dialog-confirm-cancel');
        btnOk.innerText = confirmText;
        btnCancel.innerText = cancelText;

        openModal('modal-custom-confirm');
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const pill = document.createElement('div');
    pill.className = `toast-pill ${type}`;
    pill.innerHTML = `<span>${escapeHtml(message)}</span>`;
    container.appendChild(pill);
    
    setTimeout(() => pill.classList.add('show'), 10);
    setTimeout(() => {
        pill.classList.remove('show');
        setTimeout(() => pill.remove(), 250);
    }, 3200);
}

function waitForPyWebView() {
    if (window.pywebview && window.pywebview.api) {
        initApp();
    } else {
        window.addEventListener('pywebviewready', initApp);
        let attempts = 0;
        const interval = setInterval(() => {
            attempts++;
            if (window.pywebview && window.pywebview.api) {
                clearInterval(interval);
                initApp();
            } else if (attempts > 30) {
                clearInterval(interval);
            }
        }, 100);
    }
}

function initApp() {
    loadDashboard();
    loadAccounts();
    loadGroups();
    loadPosts();
    loadHistory();
}

// Navigation Tabs
function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));

    const navTarget = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
    if (navTarget) navTarget.classList.add('active');

    const paneTarget = document.getElementById(tabId);
    if (paneTarget) paneTarget.classList.add('active');

    if (tabId === 'tab-dashboard') loadDashboard();
    else if (tabId === 'tab-accounts') loadAccounts();
    else if (tabId === 'tab-groups') loadGroups();
    else if (tabId === 'tab-posts') loadPosts();
    else if (tabId === 'tab-campaign') setupCampaignView();
    else if (tabId === 'tab-history') loadHistory();
}

// ==================== DASHBOARD ====================
async function loadDashboard() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
        const stats = await window.pywebview.api.get_dashboard_stats();
        document.getElementById('stat-accounts').innerText = `${stats.live_accounts} / ${stats.total_accounts}`;
        document.getElementById('stat-groups').innerText = stats.total_groups;
        document.getElementById('stat-posts').innerText = stats.total_posts;
        document.getElementById('stat-success').innerText = stats.history_success;

        const history = await window.pywebview.api.get_history(5);
        const tbody = document.querySelector('#table-dashboard-history tbody');
        if (!history || history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">Chưa có lượt đăng bài nào</td></tr>';
            return;
        }

        tbody.innerHTML = history.map(item => `
            <tr>
                <td>${item.posted_at || 'Vừa xong'}</td>
                <td><strong style="color: var(--caramel);">${escapeHtml(item.account_name)}</strong></td>
                <td>${escapeHtml(item.group_name)}</td>
                <td>${escapeHtml(item.post_title)}</td>
                <td>${getStatusBadge(item.status)}</td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading dashboard:', err);
    }
}

// ==================== ACCOUNTS ====================
async function loadAccounts() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
        const accounts = await window.pywebview.api.get_accounts();
        const tbody = document.getElementById('tbody-accounts');
        if (!accounts || accounts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">Chưa có tài khoản nào. Hãy nhấn "Thêm Cookie / Proxy" để bắt đầu.</td></tr>';
            return;
        }

        tbody.innerHTML = accounts.map(acc => `
            <tr>
                <td>${acc.id}</td>
                <td>
                    <div style="font-weight: 700; color: var(--text-main);">${escapeHtml(acc.name || 'Facebook User')}</div>
                    <div style="font-size: 11.5px; color: var(--text-dim); font-family: var(--font-mono);">UID: ${acc.uid || 'N/A'}</div>
                </td>
                <td><code style="color: var(--caramel-light); font-family: var(--font-mono);">${escapeHtml(acc.proxy || 'Trực tiếp (No Proxy)')}</code></td>
                <td>${getStatusBadge(acc.status)}</td>
                <td><strong>${acc.posts_count_today}</strong> / ${acc.max_posts_per_day}</td>
                <td>${acc.last_checked || 'Chưa check'}</td>
                <td>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-secondary" style="padding: 5px 10px; font-size: 11.5px;" onclick="checkAccount(${acc.id})">Check Live</button>
                        <button class="btn btn-danger" style="padding: 5px 10px; font-size: 11.5px;" onclick="deleteAccount(${acc.id})">Xóa</button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading accounts:', err);
    }
}

async function checkAccount(id) {
    try {
        showToast('Đang kiểm tra tài khoản...', 'info');
        const res = await window.pywebview.api.check_account(id);
        const alertType = res.status === 'Live' ? 'success' : (res.status === 'Die' ? 'error' : 'warning');
        await showCustomAlert(`Kết quả kiểm tra #${id}`, `Trạng thái: ${res.status}\nThông báo: ${res.message}`, alertType);
        loadAccounts();
    } catch (err) {
        await showCustomAlert('Lỗi kiểm tra', String(err), 'error');
    }
}

async function checkAllAccounts() {
    try {
        const btn = event.currentTarget;
        const originalText = btn.innerHTML;
        btn.innerHTML = 'Đang kiểm tra...';
        btn.disabled = true;

        showToast('Đang kiểm tra toàn bộ danh sách tài khoản...', 'info');
        await window.pywebview.api.check_all_accounts();
        btn.innerHTML = originalText;
        btn.disabled = false;

        await showCustomAlert('Hoàn tất', 'Đã hoàn tất kiểm tra trạng thái toàn bộ danh sách tài khoản!', 'success');
        loadAccounts();
        loadDashboard();
    } catch (err) {
        await showCustomAlert('Lỗi kiểm tra', String(err), 'error');
    }
}

async function submitImportAccounts() {
    const raw = document.getElementById('input-account-cookies').value;
    const autoCheck = document.getElementById('check-account-auto').checked;
    if (!raw.trim()) {
        await showCustomAlert('Thiếu dữ liệu', 'Vui lòng nhập cookie tài khoản!', 'warning');
        return;
    }

    try {
        showToast('Đang nạp và phân tích cookie...', 'info');
        const res = await window.pywebview.api.import_accounts(raw, autoCheck);
        closeModal('modal-account');
        document.getElementById('input-account-cookies').value = '';
        await showCustomAlert('Thành công', res.message, 'success');
        loadAccounts();
        loadDashboard();
    } catch (err) {
        await showCustomAlert('Lỗi nhập tài khoản', String(err), 'error');
    }
}

async function deleteAccount(id) {
    const confirmed = await showCustomConfirm('Xác nhận xóa tài khoản', `Bạn có chắc chắn muốn xóa tài khoản #${id} khỏi hệ thống?`, 'Xóa ngay', 'Hủy bỏ', 'error');
    if (!confirmed) return;

    try {
        await window.pywebview.api.delete_account(id);
        showToast(`Đã xóa tài khoản #${id}`, 'success');
        loadAccounts();
        loadDashboard();
    } catch (err) {
        await showCustomAlert('Lỗi xóa tài khoản', String(err), 'error');
    }
}

// ==================== GROUPS (Tên / ID đứng trước URL) ====================
async function loadGroups() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
        const groups = await window.pywebview.api.get_groups();
        const tbody = document.getElementById('tbody-groups');
        if (!groups || groups.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">Chưa có nhóm nào. Nhấn "Nhập Nhóm Hàng Loạt" để thêm.</td></tr>';
            return;
        }

        tbody.innerHTML = groups.map(g => `
            <tr>
                <td>${g.id}</td>
                <td><strong style="color: var(--caramel);">${escapeHtml(g.name || 'Nhóm Facebook')}</strong></td>
                <td><a href="#" style="color: var(--caramel-light); text-decoration: none;" onclick="window.open('${g.url}', '_blank')">${escapeHtml(g.url)}</a></td>
                <td><span class="badge badge-unknown">${escapeHtml(g.category || 'Chung')}</span></td>
                <td>${g.requires_approval ? '<span class="badge badge-pending">Có duyệt</span>' : '<span class="badge badge-live">Đăng ngay</span>'}</td>
                <td>${g.allow_anonymous ? '<span class="badge badge-live">Hỗ trợ</span>' : '<span class="badge badge-unknown">Chưa rõ</span>'}</td>
                <td>
                    <button class="btn btn-danger" style="padding: 5px 10px; font-size: 11.5px;" onclick="deleteGroup(${g.id})">Xóa</button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading groups:', err);
    }
}

async function submitImportGroups() {
    const raw = document.getElementById('input-group-urls').value;
    const category = document.getElementById('input-group-category').value.trim() || 'Chung';
    const defaultName = document.getElementById('input-group-default-name').value.trim() || null;

    if (!raw.trim()) {
        await showCustomAlert('Thiếu dữ liệu', 'Vui lòng dán danh sách liên kết nhóm Facebook!', 'warning');
        return;
    }

    try {
        showToast('Đang nạp và phân loại danh sách nhóm...', 'info');
        const res = await window.pywebview.api.import_groups(raw, category, defaultName);
        closeModal('modal-group');
        document.getElementById('input-group-urls').value = '';
        document.getElementById('input-group-default-name').value = '';
        await showCustomAlert('Thành công', `Đã tìm thấy ${res.total_found} nhóm hợp lệ.\nĐã lưu thành công: ${res.added_count} nhóm vào danh mục "${category}".`, 'success');
        loadGroups();
        loadDashboard();
    } catch (err) {
        await showCustomAlert('Lỗi nhập nhóm', String(err), 'error');
    }
}

async function deleteGroup(id) {
    const confirmed = await showCustomConfirm('Xác nhận xóa nhóm', `Bạn có chắc chắn muốn xóa nhóm #${id} khỏi danh sách?`, 'Xóa ngay', 'Hủy bỏ', 'error');
    if (!confirmed) return;

    try {
        await window.pywebview.api.delete_group(id);
        showToast(`Đã xóa nhóm #${id}`, 'success');
        loadGroups();
        loadDashboard();
    } catch (err) {
        await showCustomAlert('Lỗi xóa nhóm', String(err), 'error');
    }
}

// ==================== POSTS & SPINTAX ====================
async function loadPosts() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
        const posts = await window.pywebview.api.get_posts();
        const tbody = document.getElementById('tbody-posts');
        if (!posts || posts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-dim);">Chưa có bài viết nào. Hãy tạo bài viết mới.</td></tr>';
            return;
        }

        tbody.innerHTML = posts.map(p => `
            <tr>
                <td>${p.id}</td>
                <td><strong style="color: var(--caramel);">${escapeHtml(p.title)}</strong></td>
                <td><div style="max-width: 280px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-sub);">${escapeHtml(p.content_spintax)}</div></td>
                <td>${(p.image_paths || []).length} hình ảnh</td>
                <td>${p.use_anonymous ? '<span class="badge badge-live">Bật</span>' : '<span class="badge badge-unknown">Tắt</span>'}</td>
                <td>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-secondary" style="padding: 5px 10px; font-size: 11.5px;" onclick="editPost(${p.id})">Sửa</button>
                        <button class="btn btn-danger" style="padding: 5px 10px; font-size: 11.5px;" onclick="deletePost(${p.id})">Xóa</button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading posts:', err);
    }
}

async function testSpintaxPreview() {
    const content = document.getElementById('input-post-content').value;
    if (!content.trim()) {
        await showCustomAlert('Thiếu nội dung', 'Vui lòng nhập nội dung bài viết trước khi xem thử Spintax!', 'warning');
        return;
    }
    try {
        const result = await window.pywebview.api.preview_spintax(content);
        const box = document.getElementById('spintax-preview-box');
        const text = document.getElementById('spintax-preview-text');
        text.innerText = result;
        box.style.display = 'block';
    } catch (err) {
        await showCustomAlert('Lỗi Spintax', String(err), 'error');
    }
}

async function pickImages() {
    try {
        const paths = await window.pywebview.api.select_images();
        if (paths && paths.length > 0) {
            currentSelectedImages = paths;
            document.getElementById('selected-images-count').innerText = `Đã chọn ${paths.length} tệp ảnh`;
            document.getElementById('image-paths-list').innerHTML = paths.map(p => `<div>📁 ${p}</div>`).join('');
            showToast(`Đã chọn ${paths.length} hình ảnh`, 'info');
        }
    } catch (err) {
        await showCustomAlert('Lỗi chọn ảnh', String(err), 'error');
    }
}

async function editPost(id) {
    try {
        const post = await window.pywebview.api.get_post(id);
        if (!post) return;
        document.getElementById('modal-post-title').innerText = 'Chỉnh Sửa Bài Viết #' + id;
        document.getElementById('input-post-id').value = post.id;
        document.getElementById('input-post-title').value = post.title;
        document.getElementById('input-post-content').value = post.content_spintax;
        document.getElementById('input-post-anon').checked = !!post.use_anonymous;
        currentSelectedImages = post.image_paths || [];
        document.getElementById('selected-images-count').innerText = currentSelectedImages.length > 0 ? `Đã chọn ${currentSelectedImages.length} tệp ảnh` : 'Chưa chọn ảnh nào';
        document.getElementById('image-paths-list').innerHTML = currentSelectedImages.map(p => `<div>📁 ${p}</div>`).join('');
        document.getElementById('spintax-preview-box').style.display = 'none';
        openModal('modal-post');
    } catch (err) {
        await showCustomAlert('Lỗi nạp bài viết', String(err), 'error');
    }
}

async function submitSavePost() {
    const id = document.getElementById('input-post-id').value;
    const title = document.getElementById('input-post-title').value.trim();
    const content = document.getElementById('input-post-content').value.trim();
    const anon = document.getElementById('input-post-anon').checked;

    if (!title) {
        await showCustomAlert('Thiếu tiêu đề', 'Vui lòng nhập tiêu đề gợi nhớ cho bài viết!', 'warning');
        return;
    }
    if (!content) {
        await showCustomAlert('Thiếu nội dung', 'Vui lòng nhập nội dung bài viết!', 'warning');
        return;
    }

    try {
        await window.pywebview.api.save_post({
            id: id ? parseInt(id) : null,
            title: title,
            content_spintax: content,
            image_paths: currentSelectedImages,
            use_anonymous: anon
        });
        closeModal('modal-post');
        resetPostForm();
        showToast('Đã lưu bài viết thành công!', 'success');
        loadPosts();
        loadDashboard();
    } catch (err) {
        await showCustomAlert('Lỗi lưu bài viết', String(err), 'error');
    }
}

function resetPostForm() {
    document.getElementById('modal-post-title').innerText = 'Soạn Bài Viết Mới';
    document.getElementById('input-post-id').value = '';
    document.getElementById('input-post-title').value = '';
    document.getElementById('input-post-content').value = '';
    document.getElementById('input-post-anon').checked = false;
    currentSelectedImages = [];
    document.getElementById('selected-images-count').innerText = 'Chưa chọn ảnh nào';
    document.getElementById('image-paths-list').innerHTML = '';
    document.getElementById('spintax-preview-box').style.display = 'none';
}

async function deletePost(id) {
    const confirmed = await showCustomConfirm('Xác nhận xóa bài viết', `Bạn có chắc muốn xóa bài viết #${id} khỏi kho?`, 'Xóa ngay', 'Hủy bỏ', 'error');
    if (!confirmed) return;

    try {
        await window.pywebview.api.delete_post(id);
        showToast(`Đã xóa bài viết #${id}`, 'success');
        loadPosts();
        loadDashboard();
    } catch (err) {
        await showCustomAlert('Lỗi xóa bài viết', String(err), 'error');
    }
}

// ==================== CAMPAIGN ====================
async function setupCampaignView() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
        const select = document.getElementById('campaign-post-select');
        const prevSelected = select.value;
        const posts = await window.pywebview.api.get_posts();
        select.innerHTML = '<option value="">-- Chọn bài viết --</option>' +
            posts.map(p => `<option value="${p.id}">${escapeHtml(p.title)}</option>`).join('');
        if (prevSelected) select.value = prevSelected;

        // Restore saved delay & duplicate-check config
        const cfg = await window.pywebview.api.get_campaign_config();
        if (cfg) {
            document.getElementById('campaign-max-per-acc').value = cfg.max_posts_per_account ?? 3;
            document.getElementById('campaign-min-delay').value = cfg.min_delay ?? 120;
            document.getElementById('campaign-max-delay').value = cfg.max_delay ?? 240;
            document.getElementById('campaign-safe-wait').value = cfg.safe_wait_seconds ?? 0;
            document.getElementById('campaign-skip-posted').checked = cfg.skip_already_posted !== false;
            document.getElementById('campaign-cooldown-hours').value = cfg.cooldown_hours ?? 24;
            document.getElementById('campaign-check-fb-live').checked = cfg.check_fb_live !== false;
            toggleDuplicateScanOptions();
        }
    } catch (err) {
        console.error('Error setup campaign:', err);
    }
}

function toggleDuplicateScanOptions() {
    const skipEl = document.getElementById('campaign-skip-posted');
    const subBox = document.getElementById('duplicate-scan-suboptions');
    const cooldownEl = document.getElementById('campaign-cooldown-hours');
    const liveEl = document.getElementById('campaign-check-fb-live');
    if (!skipEl || !subBox) return;

    const enabled = skipEl.checked;
    subBox.style.opacity = enabled ? '1' : '0.45';
    if (cooldownEl) cooldownEl.disabled = !enabled;
    if (liveEl) liveEl.disabled = !enabled;
}

async function startCampaign() {
    const postId = document.getElementById('campaign-post-select').value;
    if (!postId) {
        await showCustomAlert('Chưa chọn bài', 'Vui lòng chọn bài viết cần đăng!', 'warning');
        return;
    }

    const rawMaxPerAcc = parseInt(document.getElementById('campaign-max-per-acc').value, 10);
    const rawMinDelay = parseInt(document.getElementById('campaign-min-delay').value, 10);
    const rawMaxDelay = parseInt(document.getElementById('campaign-max-delay').value, 10);
    const rawSafeWait = parseInt(document.getElementById('campaign-safe-wait').value, 10);
    const rawCooldownHours = parseInt(document.getElementById('campaign-cooldown-hours').value, 10);

    const maxPerAcc = Number.isNaN(rawMaxPerAcc) ? 3 : Math.max(1, rawMaxPerAcc);
    const minDelay = Number.isNaN(rawMinDelay) ? 120 : Math.max(0, rawMinDelay);
    const maxDelay = Number.isNaN(rawMaxDelay) ? 240 : Math.max(minDelay, rawMaxDelay);
    const safeWaitSeconds = Number.isNaN(rawSafeWait) ? 0 : Math.max(0, rawSafeWait);
    const skipAlreadyPosted = document.getElementById('campaign-skip-posted').checked;
    const cooldownHours = Number.isNaN(rawCooldownHours) ? 24 : Math.max(1, rawCooldownHours);
    const checkFbLive = document.getElementById('campaign-check-fb-live').checked;
    const headless = true; // Luôn luôn chạy ẩn ngầm mặc định (không tạo cửa sổ, không chiếm chuột)

    try {
        const accounts = await window.pywebview.api.get_accounts();
        const liveAccounts = accounts.filter(a => a.status !== 'Die').map(a => a.id);
        if (liveAccounts.length === 0) {
            await showCustomAlert('Không có nick Live', 'Không có tài khoản Live nào khả dụng! Vui lòng kiểm tra lại tài khoản.', 'warning');
            return;
        }

        const groups = await window.pywebview.api.get_groups();
        const groupIds = groups.map(g => g.id);
        if (groupIds.length === 0) {
            await showCustomAlert('Danh sách nhóm trống', 'Danh sách nhóm đang trống! Vui lòng nhập nhóm trước khi chạy.', 'warning');
            return;
        }

        const res = await window.pywebview.api.start_campaign({
            account_ids: liveAccounts,
            group_ids: groupIds,
            post_id: parseInt(postId),
            min_delay: minDelay,
            max_delay: maxDelay,
            safe_wait_seconds: safeWaitSeconds,
            max_posts_per_account: maxPerAcc,
            skip_already_posted: skipAlreadyPosted,
            cooldown_hours: cooldownHours,
            check_fb_live: checkFbLive,
            headless: headless
        });

        if (res.success) {
            isCampaignRunning = true;
            document.getElementById('campaign-status-badge').className = 'badge badge-live';
            document.getElementById('campaign-status-badge').innerText = 'Trạng thái: Đang chạy';
            document.getElementById('btn-start-campaign').disabled = true;
            showToast('Chiến dịch đã bắt đầu chạy ngầm!', 'success');
        } else {
            await showCustomAlert('Không thể bắt đầu', res.message, 'error');
        }
    } catch (err) {
        await showCustomAlert('Lỗi chiến dịch', String(err), 'error');
    }
}

async function pauseCampaign() {
    const res = await window.pywebview.api.pause_campaign();
    if (res.success) {
        document.getElementById('campaign-status-badge').className = 'badge badge-checkpoint';
        document.getElementById('campaign-status-badge').innerText = 'Trạng thái: Tạm dừng';
        showToast('Đã tạm dừng chiến dịch', 'warning');
    }
}

async function resumeCampaign() {
    const res = await window.pywebview.api.resume_campaign();
    if (res.success) {
        document.getElementById('campaign-status-badge').className = 'badge badge-live';
        document.getElementById('campaign-status-badge').innerText = 'Trạng thái: Đang chạy';
        showToast('Tiếp tục chiến dịch', 'info');
    }
}

async function stopCampaign() {
    const res = await window.pywebview.api.stop_campaign();
    if (res.success) {
        document.getElementById('campaign-status-badge').className = 'badge badge-unknown';
        document.getElementById('campaign-status-badge').innerText = 'Trạng thái: Đã dừng';
        document.getElementById('btn-start-campaign').disabled = false;
        isCampaignRunning = false;
        showToast('Đã gửi lệnh dừng chiến dịch', 'info');
    }
}

function clearConsole() {
    document.getElementById('terminal-console').innerHTML = '';
}

// Event receiver from Python
window.onBackendEvent = function(eventName, data) {
    if (eventName === 'log') {
        const consoleEl = document.getElementById('terminal-console');
        const line = document.createElement('div');
        line.className = 'log-line';
        
        let levelClass = 'log-info';
        if (data.level === 'success') levelClass = 'log-success';
        else if (data.level === 'warning') levelClass = 'log-warning';
        else if (data.level === 'error') levelClass = 'log-error';

        line.innerHTML = `<span class="log-time">[${data.timestamp}]</span><span class="${levelClass}">${escapeHtml(data.message)}</span>`;
        consoleEl.appendChild(line);
        consoleEl.scrollTop = consoleEl.scrollHeight;
    } else if (eventName === 'progress') {
        const current = data.current || 0;
        const total = data.total || 1;
        const pct = Math.round((current / total) * 100);
        document.getElementById('campaign-progress-bar').style.width = `${pct}%`;
        document.getElementById('progress-text').innerText = `${current} / ${total} nhóm (${pct}%)`;
    } else if (eventName === 'finished') {
        isCampaignRunning = false;
        document.getElementById('campaign-status-badge').className = 'badge badge-unknown';
        document.getElementById('campaign-status-badge').innerText = 'Trạng thái: Hoàn tất';
        document.getElementById('btn-start-campaign').disabled = false;
        showToast('Chiến dịch đã hoàn tất!', 'success');
        loadDashboard();
        loadHistory();
    }
};

// ==================== HISTORY ====================
async function loadHistory() {
    if (!window.pywebview || !window.pywebview.api) return;
    try {
        const history = await window.pywebview.api.get_history(100);
        const tbody = document.getElementById('tbody-history');
        if (!history || history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">Chưa có lịch sử đăng bài nào.</td></tr>';
            return;
        }

        tbody.innerHTML = history.map(item => `
            <tr>
                <td>#${item.id}</td>
                <td>${item.posted_at || 'Vừa xong'}</td>
                <td><strong style="color: var(--caramel);">${escapeHtml(item.account_name)}</strong></td>
                <td>${escapeHtml(item.group_name)}</td>
                <td>${escapeHtml(item.post_title)}</td>
                <td>${getStatusBadge(item.status)}</td>
                <td><small style="color: var(--text-dim);">${escapeHtml(item.error_message || 'Thành công')}</small></td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Error loading history:', err);
    }
}

// ==================== HELPERS ====================
function openModal(id) {
    if (id === 'modal-post' && !document.getElementById('input-post-id').value) {
        resetPostForm();
    }
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('active');
}

function getStatusBadge(status) {
    const s = (status || '').toLowerCase();
    if (s === 'live' || s === 'success') {
        return `<span class="badge badge-live">Live / Thành công</span>`;
    } else if (s === 'die' || s === 'failed') {
        return `<span class="badge badge-die">Die / Thất bại</span>`;
    } else if (s === 'checkpoint' || s === 'pending_approval' || s === 'pending') {
        return `<span class="badge badge-checkpoint">Chờ duyệt / CP</span>`;
    }
    return `<span class="badge badge-unknown">${escapeHtml(status || 'Chưa rõ')}</span>`;
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
