/* --- ⚙️ Supabase 初始化 --- */
const SUPABASE_URL = "https://enodcxbwqqigqfwnjlwc.supabase.co";
const SUPABASE_KEY = "sb_publishable_4oUBmjde-G-YsVS9bTo0bA_iA8kvSEv";
const _supabase = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

/* --- 🖥️ UI 元件選取 --- */
const authElements = {
    loginBtn: document.getElementById('login-btn'),
    logoutBtn: document.getElementById('logout-btn'),
    userInfo: document.getElementById('user-info'),
    userName: document.getElementById('user-name'),
    userAvatar: document.getElementById('user-avatar'),
    discordInput: document.getElementById('discord-input'),
    saveProfileBtn: document.getElementById('save-profile-btn'),
    updateSubBtn: document.getElementById('update-sub-btn'),
    monitoringStatus: document.getElementById('monitoring-status')
};

function setDashboardMetric(elementId, value) {
    const el = document.getElementById(elementId);
    if (el) el.textContent = value;
}

/* --- 🔑 認證邏輯 --- */

// Google 登入
async function loginWithGoogle() {
    const redirectTo = window.location.origin + window.location.pathname;
    await _supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo }
    });
}

// 登出
async function logout() {
    await _supabase.auth.signOut();
    // 重置訂閱計數
    setDashboardMetric('active-subscriptions-count', '--');
    setDashboardMetric('global-keyword-matches-count', '--');
    setDashboardMetric('global-keywords-count', '--');
    window.location.reload();
}

// 更新監控武是連線狀態
function updateMonitoringStatus(isConnected) {
    if (!authElements.monitoringStatus) return;
    if (isConnected) {
        authElements.monitoringStatus.className = 'flex items-center gap-1.5 text-sm font-bold text-green-600 bg-green-50 px-2 py-1 rounded-md';
        authElements.monitoringStatus.innerHTML = '<span class="w-2 h-2 bg-green-500 rounded-full status-pulse"></span> 全校網頁監控中';
    } else {
        authElements.monitoringStatus.className = 'flex items-center gap-1.5 text-sm font-bold text-slate-400 bg-slate-100 px-2 py-1 rounded-md';
        authElements.monitoringStatus.innerHTML = '<span class="w-2 h-2 bg-slate-400 rounded-full"></span> 未連線';
    }
}

// 更新登入狀態 UI
function updateAuthUI(user) {
    if (user) {
        authElements.loginBtn.classList.add('hidden');
        authElements.userInfo.classList.remove('hidden');
        authElements.userName.innerText = user.user_metadata.full_name || user.email;
        authElements.userAvatar.src = user.user_metadata.avatar_url || "";
        updateMonitoringStatus(true);
    } else {
        authElements.loginBtn.classList.remove('hidden');
        authElements.userInfo.classList.add('hidden');
        authElements.discordInput.value = "";
        updateMonitoringStatus(false);
        setDashboardMetric('active-subscriptions-count', '--');
        setDashboardMetric('global-keyword-matches-count', '--');
        setDashboardMetric('global-keywords-count', '--');
        // 清空所有勾勾
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    }
}

/* --- 🛰️ 資料同步邏輯 --- */

// 更新訂閱計數
async function updateSubscriptionCount(userId) {
    const countEl = document.getElementById('active-subscriptions-count');
    if (!countEl) return;
    
    try {
        const { count, error } = await _supabase
            .from('user_subscriptions')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', userId);
        
        if (error) throw error;
        countEl.textContent = count || 0;
    } catch (err) {
        console.error('獲取訂閱數量失敗', err);
        countEl.textContent = '--';
    }
}

// 從雲端載入使用者資料與訂閱
async function syncUserData(userId) {
    console.log("正在同步使用者資料...");

    // 1. 載入 Webhook 設定
    const { data: profile, error: profileError } = await _supabase
        .from('profiles')
        .select('discord_webhook')
        .eq('id', userId)
        .single();

    if (profileError) console.error('載入 profile 時發生錯誤', profileError);
    if (profile) authElements.discordInput.value = profile.discord_webhook || "";

    // 2. 載入訂閱偏好
    const { data: subs, error: subsError } = await _supabase
        .from('user_subscriptions')
        .select('category_id')
        .eq('user_id', userId);

    if (subsError) {
        console.error('載入 subscriptions 時發生錯誤', subsError);
        return; // 沒辦法同步訂閱就跳出
    }

    const subIds = (subs || []).map(s => s.category_id);

    // 抓取所有的子項目勾勾並自動點亮
    document.querySelectorAll('.child-checkbox').forEach(cb => {
        cb.checked = subIds.includes(cb.value);
    });

    // 同步父層 checkbox 的勾選狀態，但不自動展開選單
    document.querySelectorAll('.parent-checkbox').forEach(parentCb => {
        // 嘗試取得該 parent 對應的容器（通常為 menu-row 的下一個 sibling）
        const row = parentCb.closest('.menu-row');
        if (!row) return;
        const container = row.nextElementSibling; // 應該是 .collapsible-content
        if (!container) return;

        // 當前容器下是否有任何被勾選的 child-checkbox
        const anyChildChecked = container.querySelectorAll('.child-checkbox:checked').length > 0;
        parentCb.checked = anyChildChecked;
    });

    // 更新訂閱計數
    await updateSubscriptionCount(userId);
    window.updateMenuSelectedSummary?.();
    window.applyMenuFilter?.();
}

/* --- 💾 儲存操作 --- */

// 儲存 Webhook 設定[cite: 1]
authElements.saveProfileBtn.addEventListener('click', async () => {
    const { data: { session } } = await _supabase.auth.getSession();
    if (!session) return alert("請先登入！");
    authElements.saveProfileBtn.disabled = true;
    const { data, error } = await _supabase.from('profiles').upsert({
        id: session.user.id,
        discord_webhook: authElements.discordInput.value,
        updated_at: new Date().toISOString()
    });
    authElements.saveProfileBtn.disabled = false;

    if (error) {
        console.error('儲存 profile 失敗', error);
        return alert("儲存失敗: " + error.message);
    }

    alert("Webhook 設定已儲存 🚀");
});

// 儲存訂閱偏好[cite: 1]
authElements.updateSubBtn.addEventListener('click', async () => {
    const { data: { session } } = await _supabase.auth.getSession();
    if (!session) return alert("請先登入！");
    authElements.updateSubBtn.disabled = true;
    const prevText = authElements.updateSubBtn.innerText;
    authElements.updateSubBtn.innerText = "同步中...";

    // 取得所有被勾選的子項目 value
    const selected = Array.from(document.querySelectorAll('.child-checkbox:checked'))
        .map(cb => cb.value);

    // 先讀出舊的訂閱（以便於在必要時回滾）
    const { data: existingSubs, error: existingError } = await _supabase
        .from('user_subscriptions')
        .select('category_id')
        .eq('user_id', session.user.id);

    if (existingError) {
        console.error('讀取現有訂閱失敗', existingError);
        authElements.updateSubBtn.disabled = false;
        authElements.updateSubBtn.innerText = prevText;
        return alert('讀取現有訂閱失敗，請稍後重試');
    }

    const prevData = (existingSubs || []).map(s => ({ user_id: session.user.id, category_id: s.category_id }));

    // 刪除舊的
    const { error: delError } = await _supabase.from('user_subscriptions').delete().eq('user_id', session.user.id);
    if (delError) {
        console.error('刪除舊訂閱失敗', delError);
        authElements.updateSubBtn.disabled = false;
        authElements.updateSubBtn.innerText = prevText;
        return alert('更新失敗：無法刪除舊訂閱，請稍後再試');
    }

    // 若有新的要插入
    if (selected.length > 0) {
        const insertData = selected.map(val => ({
            user_id: session.user.id,
            category_id: val
        }));

        const { data: inserted, error: insertError } = await _supabase.from('user_subscriptions').insert(insertData);
        if (insertError) {
            console.error('插入新訂閱失敗，嘗試回滾', insertError);
            // 嘗試回滾至先前資料
            if (prevData.length > 0) {
                const { error: rollbackError } = await _supabase.from('user_subscriptions').insert(prevData);
                if (rollbackError) {
                    console.error('回滾失敗', rollbackError);
                    authElements.updateSubBtn.disabled = false;
                    authElements.updateSubBtn.innerText = prevText;
                    return alert('更新訂閱失敗且回滾失敗，請聯絡管理員');
                }
            }
            authElements.updateSubBtn.disabled = false;
            authElements.updateSubBtn.innerText = prevText;
            return alert('更新訂閱失敗，已回滾先前設定');
        }
    }

    authElements.updateSubBtn.disabled = false;
    authElements.updateSubBtn.innerText = prevText;
    
    // 更新訂閱計數
    await updateSubscriptionCount(session.user.id);
    
    window.dispatchEvent(new CustomEvent('subscriptions:updated', {
        detail: {
            userId: session.user.id,
            categoryIds: selected
        }
    }));
    alert("訂閱偏好已更新 🔔");
});

/* --- 🚀 初始化與事件綁定 --- */
authElements.loginBtn.addEventListener('click', loginWithGoogle);
authElements.logoutBtn.addEventListener('click', logout);

// 監聽認證狀態改變[cite: 1]
_supabase.auth.onAuthStateChange((event, session) => {
    if (session) {
        updateAuthUI(session.user);
        syncUserData(session.user.id);
    } else {
        updateAuthUI(null);
    }
});

// 初次載入頁面檢查 session[cite: 1]
document.addEventListener('DOMContentLoaded', async () => {
    const { data: { session } } = await _supabase.auth.getSession();
    if (session) {
        updateAuthUI(session.user);
        syncUserData(session.user.id);
    }
});
