/* --- 🌐 Global Radar Keywords Management --- */

// Utility function to escape HTML
function escapeHtml(value) {
    if (typeof value !== 'string') return '';
    return value
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

// Global state for keywords
window.globalRadarKeywords = {
    keywords: [],
    currentUserId: null,
    isLoading: false,
    isSyncing: false
};

/**
 * 從 Supabase 載入當前使用者的關鍵字
 */
async function loadKeywordsFromSupabase(userId) {
    if (!userId || !_supabase) return;
    
    try {
        const { data: profile, error } = await _supabase
            .from('profiles')
            .select('keywords')
            .eq('id', userId)
            .single();
        
        if (error) {
            console.error('載入關鍵字失敗', error);
            return [];
        }
        
        const keywords = Array.isArray(profile?.keywords) ? profile.keywords : [];
        window.globalRadarKeywords.keywords = keywords;
        window.globalRadarKeywords.currentUserId = userId;
        
        console.log('已載入關鍵字:', keywords);
        return keywords;
    } catch (err) {
        console.error('載入關鍵字時發生錯誤', err);
        return [];
    }
}

/**
 * 將關鍵字陣列同步回 Supabase
 */
async function updateKeywordsInSupabase(keywords) {
    if (!window.globalRadarKeywords.currentUserId || !_supabase) return false;
    
    window.globalRadarKeywords.isSyncing = true;
    
    try {
        const { error } = await _supabase
            .from('profiles')
            .upsert({
                id: window.globalRadarKeywords.currentUserId,
                keywords: keywords,
                updated_at: new Date().toISOString()
            });
        
        if (error) {
            console.error('同步關鍵字失敗', error);
            window.globalRadarKeywords.isSyncing = false;
            return false;
        }
        
        console.log('關鍵字已同步至 Supabase:', keywords);
        window.globalRadarKeywords.isSyncing = false;
        return true;
    } catch (err) {
        console.error('同步關鍵字時發生錯誤', err);
        window.globalRadarKeywords.isSyncing = false;
        return false;
    }
}

/**
 * 動態渲染關鍵字標籤
 */
function renderKeywordTags(keywords) {
    const container = document.getElementById('global-radar-tags');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!Array.isArray(keywords) || keywords.length === 0) {
        container.innerHTML = '<p class="text-xs text-slate-400 italic py-2">尚無監控關鍵字</p>';
        return;
    }
    
    keywords.forEach((keyword, index) => {
        const tagHtml = document.createElement('span');
        tagHtml.className = 'px-2.5 py-1 bg-blue-600 text-white text-xs font-black rounded-lg flex items-center gap-2 group';
        tagHtml.dataset.index = index;
        tagHtml.innerHTML = `
            ${escapeHtml(keyword)}
            <i class="fas fa-times cursor-pointer opacity-50 group-hover:opacity-100 transition-opacity keyword-delete-btn" data-index="${index}"></i>
        `;
        container.appendChild(tagHtml);
    });
}

/**
 * 新增關鍵字
 */
async function addKeyword(keyword) {
    if (!keyword || typeof keyword !== 'string') return false;
    
    keyword = keyword.trim();
    
    // 驗證：空值檢查
    if (keyword.length === 0) {
        alert('請輸入有效的關鍵字');
        return false;
    }
    
    // 驗證：重複檢查
    if (window.globalRadarKeywords.keywords.includes(keyword)) {
        alert('此關鍵字已存在，請勿重複新增');
        return false;
    }
    
    // 新增至本地陣列
    window.globalRadarKeywords.keywords.push(keyword);
    
    // 同步至 Supabase
    const success = await updateKeywordsInSupabase(window.globalRadarKeywords.keywords);
    
    if (success) {
        // 重新渲染 UI
        renderKeywordTags(window.globalRadarKeywords.keywords);
        return true;
    } else {
        // 同步失敗，回滾本地陣列
        window.globalRadarKeywords.keywords.pop();
        alert('新增關鍵字失敗，請稍後再試');
        return false;
    }
}

/**
 * 刪除關鍵字
 */
async function removeKeyword(index) {
    if (typeof index !== 'number' || index < 0 || index >= window.globalRadarKeywords.keywords.length) {
        return false;
    }
    
    // 移除陣列中的關鍵字
    const keyword = window.globalRadarKeywords.keywords[index];
    window.globalRadarKeywords.keywords.splice(index, 1);
    
    // 同步至 Supabase
    const success = await updateKeywordsInSupabase(window.globalRadarKeywords.keywords);
    
    if (success) {
        // 重新渲染 UI
        renderKeywordTags(window.globalRadarKeywords.keywords);
        return true;
    } else {
        // 同步失敗，回滾本地陣列
        window.globalRadarKeywords.keywords.splice(index, 0, keyword);
        alert('刪除關鍵字失敗，請稍後再試');
        return false;
    }
}

/**
 * 初始化關鍵字管理系統
 */
function initializeKeywordManagement() {
    const input = document.getElementById('global-radar-input');
    const container = document.getElementById('global-radar-tags');
    
    if (!input || !container) {
        console.warn('找不到關鍵字輸入框或容器');
        return;
    }
    
    // 監聽 Enter 鍵事件
    input.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const keyword = input.value;
            
            // 新增關鍵字
            const success = await addKeyword(keyword);
            
            if (success) {
                input.value = ''; // 清空輸入框
            }
        }
    });
    
    // 監聽刪除按鈕事件（使用事件委派）
    container.addEventListener('click', async (e) => {
        if (e.target.classList.contains('keyword-delete-btn')) {
            const index = parseInt(e.target.dataset.index, 10);
            if (!isNaN(index)) {
                await removeKeyword(index);
            }
        }
    });
    
    // 初始化渲染
    renderKeywordTags(window.globalRadarKeywords.keywords);
}

/**
 * 監聽認證狀態改變並載入關鍵字
 */
_supabase.auth.onAuthStateChange(async (event, session) => {
    if (session?.user?.id) {
        const keywords = await loadKeywordsFromSupabase(session.user.id);
        renderKeywordTags(keywords);
    } else {
        window.globalRadarKeywords.keywords = [];
        window.globalRadarKeywords.currentUserId = null;
        renderKeywordTags([]);
    }
});

// 初始化關鍵字管理系統（立即執行，不等待 DOMContentLoaded）
initializeKeywordManagement();

// 頁面初始化時檢查 session
document.addEventListener('DOMContentLoaded', async () => {
    const { data: { session } } = await _supabase.auth.getSession();
    if (session?.user?.id) {
        const keywords = await loadKeywordsFromSupabase(session.user.id);
        renderKeywordTags(keywords);
    }
});
