/* --- 🌐 Global Radar Keywords Management (Optimized Scheme A) --- */

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
    isSyncing: false,
    pendingKeyword: ''
};

/**
 * 從 Supabase 載入當前使用者的關鍵字
 */
async function loadKeywordsFromSupabase(userId) {
    if (!userId || !_supabase) return [];
    
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
            console.error('Supabase 拒絕更新關鍵字，詳細錯誤原因:', error.message, '代碼:', error.code);
            window.globalRadarKeywords.isSyncing = false;
            return false;
        }
        
        console.log('關鍵字已同步至 Supabase:', keywords);
        window.dispatchEvent(new CustomEvent('keywords:updated', {
            detail: {
                userId: window.globalRadarKeywords.currentUserId,
                keywords: [...keywords]
            }
        }));
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
 * 🛰️ 從 Supabase 撈取匹配關鍵字的最新 10 筆公告 (方案 A 專用)
 */
async function fetchPreviewMatches(keyword) {
    if (!keyword || typeof keyword !== 'string' || !_supabase) return [];
    
    keyword = keyword.trim();
    if (keyword.length === 0) return [];
    
    try {
        const { data: matches, error } = await _supabase
            .from('announcements')
            .select('id, title, url, source, published_at')
            .or(`title.ilike.%${keyword}%,source.ilike.%${keyword}%`) 
            .order('published_at', { ascending: false }) 
            .limit(50);

        if (error) {
            console.error('預覽關鍵字查詢失敗:', error);
            return [];
        }
        return matches;
    } catch (err) {
        console.error('執行預覽時發生非預期錯誤:', err);
        return [];
    }
}

function aggregatePreviewMatches(matches) {
    if (!Array.isArray(matches) || matches.length === 0) return [];

    const grouped = new Map();

    matches.forEach((item) => {
        const key = item.url || item.id || `${item.title || ''}::${item.published_at || ''}`;
        const sourceLabel = item.source || '未分類';

        if (!grouped.has(key)) {
            grouped.set(key, {
                ...item,
                sources: [sourceLabel]
            });
            return;
        }

        const current = grouped.get(key);
        if (sourceLabel && !current.sources.includes(sourceLabel)) {
            current.sources.push(sourceLabel);
        }
    });

    return Array.from(grouped.values()).map((item) => ({
        ...item,
        sources: Array.isArray(item.sources) ? item.sources : []
    }));
}

/**
 * 🎨 將撈出的公告陣列渲染到前端預覽貨架上
 */
function renderPreviewList(keyword, matches) {
    const list = document.getElementById('modal-preview-list');
    const footer = document.getElementById('modal-action-footer');
    
    if (!list) return;

    if (!keyword || keyword.trim().length === 0) {
        list.innerHTML = '';
        if (footer) footer.classList.add('hidden');
        return;
    }

    window.globalRadarKeywords.pendingKeyword = keyword.trim();
    list.innerHTML = '';

    const mergedMatches = aggregatePreviewMatches(matches).slice(0, 10);

    if (mergedMatches.length === 0) {
        list.innerHTML = `
            <li class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-800">
                ⚠️ 目前資料庫中無相符公告。新增此關鍵字後，未來有新公告上架時仍會觸發雷達。
            </li>`;
        if (footer) footer.classList.add('hidden');
        return;
    }

    mergedMatches.forEach((item, index) => {
        const dateDisplay = item.published_at ? item.published_at.split('T')[0] : '未知日期';
        const sources = Array.isArray(item.sources) ? item.sources : [];
        
        const li = document.createElement('li');
        li.className = 'preview-card group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg';
        li.style.animationDelay = `${Math.min(index * 40, 240)}ms`;
        li.innerHTML = `
            <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" class="block text-base font-bold leading-8 text-slate-800 transition-colors group-hover:text-blue-600" title="${escapeHtml(item.title)}">
                <span class="mr-2 inline-flex rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-black uppercase tracking-[0.2em] text-blue-600">${escapeHtml(item.source || '未分類')}</span>
                <span class="whitespace-normal break-words">${escapeHtml(item.title)}</span>
            </a>
            ${sources.length > 1 ? `
                <div class="mt-3 flex flex-wrap gap-2">
                    ${sources.map((source) => `<span class="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-bold text-slate-500">${escapeHtml(source)}</span>`).join('')}
                </div>
            ` : ''}
            <div class="mt-3 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
                <span class="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">${sources.length > 1 ? `已合併 ${sources.length} 個標籤` : '點擊可開啟原文'}</span>
                <span class="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 font-mono text-xs font-bold text-slate-500">${dateDisplay}</span>
            </div>
        `;
        list.appendChild(li);
    });

    if (footer) footer.classList.remove('hidden');
}

function clearKeywordModalState() {
    const input = document.getElementById('modal-radar-input');
    const list = document.getElementById('modal-preview-list');
    const footer = document.getElementById('modal-action-footer');

    if (input) input.value = '';
    if (list) list.innerHTML = '';
    if (footer) footer.classList.add('hidden');
    window.globalRadarKeywords.pendingKeyword = '';
}

function openKeywordActionModal() {
    const modal = document.getElementById('keyword-action-modal');
    if (!modal) return;

    clearKeywordModalState();
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    const input = document.getElementById('modal-radar-input');
    if (input) {
        window.setTimeout(() => input.focus(), 0);
    }
}

function closeKeywordActionModal() {
    const modal = document.getElementById('keyword-action-modal');
    if (!modal) return;

    modal.classList.add('hidden');
    modal.classList.remove('flex');
    clearKeywordModalState();
}

/**
 * 新增關鍵字
 */
async function addKeyword(keyword) {
    if (!keyword || typeof keyword !== 'string') return false;
    
    keyword = keyword.trim();
    
    if (keyword.length === 0) {
        alert('請輸入有效的關鍵字');
        return false;
    }
    
    if (window.globalRadarKeywords.keywords.includes(keyword)) {
        alert('此關鍵字已存在，請勿重複新增');
        return false;
    }
    
    window.globalRadarKeywords.keywords.push(keyword);
    const success = await updateKeywordsInSupabase(window.globalRadarKeywords.keywords);
    
    if (success) {
        renderKeywordTags(window.globalRadarKeywords.keywords);
        return true;
    } else {
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
    
    const keyword = window.globalRadarKeywords.keywords[index];
    window.globalRadarKeywords.keywords.splice(index, 1);
    const success = await updateKeywordsInSupabase(window.globalRadarKeywords.keywords);
    
    if (success) {
        renderKeywordTags(window.globalRadarKeywords.keywords);
        return true;
    } else {
        window.globalRadarKeywords.keywords.splice(index, 0, keyword);
        alert('刪除關鍵字失敗，請稍後再試');
        return false;
    }
}

/**
 * 初始化關鍵字管理系統 (方案 A 完全體)
 */
function initializeKeywordManagement() {
    if (window.__keywordManagementInitialized) return;
    window.__keywordManagementInitialized = true;

    const container = document.getElementById('global-radar-tags');
    const openModalBtn = document.getElementById('open-radar-modal-btn');
    const modal = document.getElementById('keyword-action-modal');
    const modalInput = document.getElementById('modal-radar-input');
    const modalPreviewBtn = document.getElementById('modal-preview-btn');
    const modalCloseBtn = document.getElementById('close-keyword-modal-btn');
    const modalConfirmBtn = document.getElementById('confirm-modal-add-keyword-btn');
    
    if (!container) {
        console.warn('找不到關鍵字標籤容器');
        return;
    }

    if (openModalBtn) {
        openModalBtn.addEventListener('click', openKeywordActionModal);
    }

    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', closeKeywordActionModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeKeywordActionModal();
            }
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modalEl = document.getElementById('keyword-action-modal');
            if (modalEl && !modalEl.classList.contains('hidden')) {
                closeKeywordActionModal();
            }
        }
    });

    if (modalInput) {
        modalInput.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (modalPreviewBtn) {
                    modalPreviewBtn.click();
                }
            }
        });
    }
    
    // 監聽刪除按報按鈕（事件委派）
    container.addEventListener('click', async (e) => {
        if (e.target.classList.contains('keyword-delete-btn')) {
            const index = parseInt(e.target.dataset.index, 10);
            if (!isNaN(index)) {
                await removeKeyword(index);
            }
        }
    });
    
    if (modalPreviewBtn && modalInput) {
        modalPreviewBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const keyword = modalInput.value.trim();
            
            if (!keyword) {
                alert('請先輸入關鍵字再進行預覽');
                return;
            }

            const originalBtnText = modalPreviewBtn.innerHTML;
            modalPreviewBtn.innerHTML = '<span class="inline-flex items-center gap-2"><i class="fas fa-spinner fa-spin"></i>搜尋中...</span>';
            modalPreviewBtn.disabled = true;

            const matches = await fetchPreviewMatches(keyword);
            renderPreviewList(keyword, matches);

            modalPreviewBtn.innerHTML = originalBtnText;
            modalPreviewBtn.disabled = false;
        });
    }

    if (modalConfirmBtn) {
        modalConfirmBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const keyword = window.globalRadarKeywords.pendingKeyword || (modalInput ? modalInput.value.trim() : '');

            if (!keyword) {
                alert('請先輸入關鍵字再進行新增');
                return;
            }

            const success = await addKeyword(keyword);
            if (success) {
                closeKeywordActionModal();
            }
        });
    }
    
    // 初始化渲染
    renderKeywordTags(window.globalRadarKeywords.keywords);
}

// 監聽認證狀態改變並載入關鍵字
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

// 初始化關鍵字管理系統（等 Modal HTML 一起載入完成）
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeKeywordManagement, { once: true });
} else {
    initializeKeywordManagement();
}

// 頁面初始化時檢查 session
document.addEventListener('DOMContentLoaded', async () => {
    const { data: { session } } = await _supabase.auth.getSession();
    if (session?.user?.id) {
        const keywords = await loadKeywordsFromSupabase(session.user.id);
        renderKeywordTags(keywords);
    }
});
