/**
 * 渲染組織選單[cite: 1]
 */
const liveFeedState = {
    allItems: [],
    visibleCount: 0,
    pageSize: 20,
    maxTotal: 50,
    fetchSourceLimit: 200,
    lookbackDays: 90,
    currentUserId: null,
    isLoading: false
};

function renderMenu() {
    const container = document.getElementById('menu-container');
    if (!container) return;

    const renderChannels = (channels = []) => channels.map(ch => `
        <div class="menu-channel-row" style="display: flex; align-items: center; justify-content: space-between;">
            <label class="menu-channel" style="flex: 1;">
                <input type="checkbox" value="${ch.value}" class="child-checkbox">
                <span>${ch.name}</span>
            </label>
            <button onclick="event.stopPropagation(); openPreviewModal('${ch.value}')" class="preview-btn" title="預覽此分類" style="padding: 0.25rem 0.5rem; background: none; border: none; color: #6B7280; cursor: pointer; font-size: 0.875rem;">
                <i class="fas fa-eye"></i>
            </button>
        </div>
    `).join('');

    const renderSubUnit = (sub) => `
        <div class="menu-subunit">
            <div onclick="toggleElement('${sub.id}')" class="menu-row menu-row-sub">
                <div class="menu-row-left">
                    <i id="icon-${sub.id}" class="fas fa-caret-right menu-icon menu-icon-sub"></i>
                    <span class="menu-label">${sub.name}</span>
                </div>
                <input type="checkbox" class="menu-checkbox menu-checkbox-sub parent-checkbox"
                       onclick="event.stopPropagation(); handleParentClick(this, '${sub.id}')">
            </div>
            <div id="${sub.id}" class="collapsible-content menu-children menu-children-channel">
                ${(Array.isArray(sub.subUnits) && sub.subUnits.length > 0)
                    ? sub.subUnits.map(renderSubUnit).join('')
                    : renderChannels(sub.channels || [])}
            </div>
        </div>
    `;

    const renderUnit = (unit) => `
        <div class="menu-unit">
            <div class="menu-row menu-row-unit" onclick="toggleElement('${unit.id}')">
                <div class="menu-row-left">
                    <i id="icon-${unit.id}" class="fas fa-caret-right menu-icon menu-icon-unit"></i>
                    <span class="menu-label">${unit.name}</span>
                </div>
                <input type="checkbox" class="menu-checkbox menu-checkbox-unit parent-checkbox"
                       onclick="event.stopPropagation(); handleParentClick(this, '${unit.id}')">
            </div>
            <div id="${unit.id}" class="collapsible-content menu-children menu-children-unit">
                ${(unit.channels || []).length > 0 ? renderChannels(unit.channels) : ''}
                ${(unit.subUnits || []).map(renderSubUnit).join('')}
            </div>
        </div>
    `;

    container.innerHTML = universitySchema.map(category => `
        <div class="menu-group border border-slate-200 rounded-2xl overflow-hidden mb-4 bg-white">
            <div class="menu-row menu-row-category" onclick="toggleElement('${category.id}')">
                <div class="menu-row-left">
                    <i id="icon-${category.id}" class="fas fa-chevron-right menu-icon menu-icon-category"></i>
                    <span class="menu-label menu-label-category">${category.name}</span>
                </div>
                <input type="checkbox" class="menu-checkbox menu-checkbox-category parent-checkbox" 
                       onclick="event.stopPropagation(); handleParentClick(this, '${category.id}')">
            </div>
            <div id="${category.id}" class="collapsible-content menu-children menu-children-category">
                ${(category.units || []).map(renderUnit).join('')}
            </div>
        </div>
    `).join('');
}

/**
 * 階層式連動勾選邏輯[cite: 1]
 */
function handleParentClick(parentCheckbox, containerId) {
    const container = document.getElementById(containerId);
    const isChecked = parentCheckbox.checked;
    
    // 勾選該容器下所有的 checkbox[cite: 1]
    const allCheckboxes = container.querySelectorAll('input[type="checkbox"]');
    allCheckboxes.forEach(cb => cb.checked = isChecked);
}

/**
 * 通用選單展開切換[cite: 1]
 */
function toggleElement(id) {
    const content = document.getElementById(id);
    const icon = document.getElementById(`icon-${id}`);
    content?.classList.toggle('expanded');
    icon?.classList.toggle('rotate-icon');
}

// 將某一節點（child 或 parent）狀態向上同步至祖先 parent-checkbox
function updateParentStates(startElem) {
    // 從 startElem 找到它所屬的容器（若為 child 則為最近的 .collapsible-content；若為 parent 則找到其對應的 container）
    let container = null;
    if (startElem.classList.contains('child-checkbox')) {
        container = startElem.closest('.collapsible-content');
    } else if (startElem.classList.contains('parent-checkbox')) {
        const row = startElem.closest('.menu-row');
        container = row ? row.nextElementSibling : null;
    }

    while (container) {
        const row = container.previousElementSibling; // menu-row
        const parentCheckbox = row ? row.querySelector('.parent-checkbox') : null;
        if (parentCheckbox) {
            const anyChildChecked = container.querySelectorAll('.child-checkbox:checked').length > 0;
            parentCheckbox.checked = anyChildChecked;
        }
        // 繼續往上尋找包含當前 row 的父層容器
        container = row ? row.closest('.collapsible-content') : null;
    }
}

function escapeHtml(value) {
    if (typeof value !== 'string') return '';
    return value
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function formatFeedDate(timeValue) {
    if (!timeValue) return '--';
    const dt = new Date(timeValue);
    if (Number.isNaN(dt.getTime())) return '--';
    const mm = String(dt.getMonth() + 1).padStart(2, '0');
    const dd = String(dt.getDate()).padStart(2, '0');
    return `${mm}-${dd}`;
}

function normalizeGismeePathForKey(pathname) {
    const path = pathname.replace(/\/+$/, '') || '/';
    const segments = path.split('/').filter(Boolean);

    if (segments.length === 3 && segments[0] === 'zh_tw' && ['news', 'menu2_1'].includes(segments[1])) {
        return `/zh_tw/news/${segments[2]}`;
    }

    if (
        segments.length === 4 &&
        segments[0] === 'zh_tw' &&
        segments[1] === 'news' &&
        segments[2] === 'menu2_2'
    ) {
        return `/zh_tw/news/${segments[3]}`;
    }

    return path;
}

function normalizeAnnouncementUrlForKey(rawUrl) {
    if (!rawUrl) return '';

    try {
        const parsed = new URL(rawUrl, window.location.origin);
        const hostname = parsed.hostname.toLowerCase();
        const normalizedHost = ['www.gismee.ntnu.edu.tw', 'gismee.ntnu.edu.tw'].includes(hostname)
            ? 'www.gismee.ntnu.edu.tw'
            : hostname;
        const normalizedPath = normalizedHost === 'www.gismee.ntnu.edu.tw'
            ? normalizeGismeePathForKey(parsed.pathname)
            : (parsed.pathname.replace(/\/+$/, '') || '/');

        return `${parsed.protocol.toLowerCase()}//${normalizedHost}${normalizedPath}${parsed.search}`;
    } catch (err) {
        return String(rawUrl).trim().replace(/\/+$/, '');
    }
}

function getAnnouncementUrlCandidates(rawUrl) {
    const normalizedUrl = normalizeAnnouncementUrlForKey(rawUrl);
    if (!normalizedUrl) return [];

    const candidates = [];
    const append = value => {
        if (value && !candidates.includes(value)) candidates.push(value);
    };

    append(rawUrl);
    append(normalizedUrl);

    try {
        const parsed = new URL(normalizedUrl);
        if (parsed.hostname.toLowerCase() === 'www.gismee.ntnu.edu.tw') {
            const segments = parsed.pathname.replace(/\/+$/, '').split('/').filter(Boolean);
            if (segments.length === 3 && segments[0] === 'zh_tw' && segments[1] === 'news') {
                const slug = segments[2];
                [
                    `/zh_tw/news/${slug}`,
                    `/zh_tw/menu2_1/${slug}`,
                    `/zh_tw/news/menu2_2/${slug}`
                ].forEach(path => append(`${parsed.protocol}//${parsed.hostname}${path}${parsed.search}`));
            }
        }
    } catch (err) {
        // Keep the original normalized candidate only.
    }

    return candidates;
}

function getAnnouncementKey(item) {
    return normalizeAnnouncementUrlForKey(item?.url) || item?.id || `${item?.title || ''}::${item?.published_at || item?.created_at || ''}`;
}

function inferTriggerType(item) {
    const value = (item.trigger_type || '').toLowerCase();
    if (value.includes('global')) {
        return {
            label: '全域關鍵字',
            wrapperClass: 'bg-rose-100 text-rose-600 border-rose-200',
            icon: 'fa-crosshairs',
            rowClass: 'bg-rose-50/5 hover:bg-rose-50/30'
        };
    }
    return {
        label: '選單訂閱',
        wrapperClass: 'bg-blue-100 text-blue-600 border-blue-200',
        icon: 'fa-check-double',
        rowClass: 'hover:bg-blue-50/30'
    };
}

function normalizeFeedTriggers(item) {
    const triggers = Array.isArray(item.triggers)
        ? item.triggers
        : [item.trigger_type || '選單訂閱'];
    const dedupedTriggers = [];
    const seenTypes = new Set();

    triggers.filter(Boolean).forEach(trigger => {
        const triggerText = String(trigger);
        const typeKey = triggerText.toLowerCase().includes('global')
            ? 'global'
            : 'menu';

        if (seenTypes.has(typeKey)) return;

        seenTypes.add(typeKey);
        dedupedTriggers.push(trigger);
    });

    return dedupedTriggers;
}

function renderTriggerBadges(triggers) {
    const visibleTriggers = triggers.slice(0, 2);
    const badgesHtml = visibleTriggers.map(trigger => {
        const triggerType = inferTriggerType({ trigger_type: trigger });
        return `
            <span class="inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-black leading-none ${triggerType.wrapperClass}">
                <i class="fas ${triggerType.icon} text-[8px]"></i>
                <span>${escapeHtml(triggerType.label)}</span>
            </span>
        `;
    }).join('');

    const extraHtml = triggers.length > 2
        ? `<span class="inline-flex shrink-0 items-center rounded-full border bg-slate-100 px-2 py-1 text-[10px] font-black leading-none text-slate-600">+${triggers.length - 2}</span>`
        : '';

    return `<div class="flex flex-wrap items-center gap-1.5">${badgesHtml}${extraHtml}</div>`;
}

function normalizeFeedSources(item) {
    if (Array.isArray(item.sources) && item.sources.length > 0) {
        return item.sources.filter(Boolean);
    }
    return [item.source || item.category_id || '未分類'];
}

function renderSourceLabels(sources, compact = false) {
    const labels = Array.from(new Set((sources || []).filter(Boolean)));
    const textClass = compact ? 'text-sm' : 'text-sm';
    const containerClass = compact
        ? 'flex min-w-0 max-w-full flex-col gap-1 leading-relaxed'
        : 'flex min-w-[14rem] max-w-[22rem] flex-col gap-1 leading-relaxed';

    return `
        <div class="${containerClass}">
            ${labels.map(source => `
                <span class="${textClass} font-bold text-slate-600 break-words whitespace-normal">
                    ${escapeHtml(source)}
                </span>
            `).join('')}
        </div>
    `;
}

function setLiveFeedStatus(message, tone = 'default') {
    const statusEl = document.getElementById('live-feed-status');
    if (!statusEl) return;
    const classMap = {
        default: 'text-slate-500',
        loading: 'text-blue-600',
        error: 'text-rose-600',
        muted: 'text-slate-400'
    };
    statusEl.className = `px-4 sm:px-6 py-3 text-sm border-b border-slate-100 ${classMap[tone] || classMap.default}`;
    statusEl.textContent = message;
}

function toggleLoadMoreButton() {
    const btn = document.getElementById('live-feed-load-more');
    if (!btn) return;
    const hasMore = liveFeedState.visibleCount < liveFeedState.allItems.length;
    btn.classList.toggle('hidden', !hasMore);
}

function renderFeedItems(reset = false) {
    const tableBody = document.getElementById('live-feed-table-body');
    const mobileContainer = document.getElementById('live-feed-mobile');
    if (!tableBody || !mobileContainer) return;

    if (reset) {
        tableBody.innerHTML = '';
        mobileContainer.innerHTML = '';
    }

    const nextCount = Math.min(liveFeedState.visibleCount + liveFeedState.pageSize, liveFeedState.allItems.length);
    const chunk = liveFeedState.allItems.slice(liveFeedState.visibleCount, nextCount);
    liveFeedState.visibleCount = nextCount;

    const desktopRows = chunk.map((item) => {
        const timeValue = item.published_at || item.created_at;
        const timeText = formatFeedDate(timeValue);
        const sourceHtml = renderSourceLabels(normalizeFeedSources(item));
        const titleText = escapeHtml(item.title || '無標題');
        const safeUrl = item.url || '#';

        const triggers = normalizeFeedTriggers(item);
        const badgesHtml = renderTriggerBadges(triggers);

        // rowClass - prefer first trigger's rowClass
        const primaryRowClass = inferTriggerType({ trigger_type: triggers[0] }).rowClass;

        return `
            <tr class="transition-colors group ${primaryRowClass}">
                <td class="px-6 py-4 text-xs font-bold text-slate-500 whitespace-nowrap">${timeText}</td>
                <td class="px-6 py-4 w-44">${badgesHtml}</td>
                <td class="px-6 py-4 min-w-[15rem] align-top">${sourceHtml}</td>
                <td class="px-6 py-4"><p class="text-sm font-bold text-slate-800">${titleText}</p></td>
                <td class="px-6 py-4 text-right"><a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="text-slate-300 hover:text-blue-600"><i class="fas fa-external-link-alt"></i></a></td>
            </tr>
        `;
    }).join('');

    const mobileRows = chunk.map((item) => {
        const timeValue = item.published_at || item.created_at;
        const timeText = formatFeedDate(timeValue);
        const sourceHtml = renderSourceLabels(normalizeFeedSources(item), true);
        const titleText = escapeHtml(item.title || '無標題');
        const safeUrl = item.url || '#';
        const triggers = normalizeFeedTriggers(item);
        const badgesHtml = renderTriggerBadges(triggers);
        const wrapperClass = (triggers[0] && inferTriggerType({ trigger_type: triggers[0] }).rowClass.includes('rose')) ? 'p-4 bg-rose-50/5' : 'p-4';
        return `
            <div class="${wrapperClass}">
                <div class="flex justify-between items-start mb-2 gap-2">
                    ${badgesHtml}
                    <span class="text-xs font-bold text-slate-500 whitespace-nowrap">${timeText}</span>
                </div>
                <p class="text-base font-bold text-slate-800 mb-1">${titleText}</p>
                <div class="flex justify-between items-center gap-3">
                    <div class="min-w-0 flex-1">${sourceHtml}</div>
                    <a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="text-slate-400 hover:text-blue-600"><i class="fas fa-external-link-alt"></i></a>
                </div>
            </div>
        `;
    }).join('');

    tableBody.insertAdjacentHTML('beforeend', desktopRows);
    mobileContainer.insertAdjacentHTML('beforeend', mobileRows);
    toggleLoadMoreButton();
}

function resetLiveFeedWithStatus(message, tone = 'default') {
    liveFeedState.allItems = [];
    liveFeedState.visibleCount = 0;
    const tableBody = document.getElementById('live-feed-table-body');
    const mobileContainer = document.getElementById('live-feed-mobile');
    if (tableBody) tableBody.innerHTML = '';
    if (mobileContainer) mobileContainer.innerHTML = '';
    toggleLoadMoreButton();
    setLiveFeedStatus(message, tone);
}

function setGlobalKeywordMatchCount(count) {
    const countEl = document.getElementById('global-keyword-matches-count');
    if (!countEl) return;
    countEl.textContent = Number.isFinite(count) ? count : '--';
}

function countGlobalKeywordMatches(items) {
    if (!Array.isArray(items)) return 0;
    return items.filter(item => {
        const triggers = Array.isArray(item.triggers)
            ? item.triggers
            : [item.trigger_type || ''];
        return triggers.some(trigger => String(trigger).toLowerCase().includes('global'));
    }).length;
}

const FEED_SELECT_WITH_PUBLISHED_AT = 'id,title,url,source,category_id,trigger_type,published_at,created_at';
const FEED_SELECT_WITHOUT_PUBLISHED_AT = 'id,title,url,source,category_id,trigger_type,created_at';

function getLiveFeedCutoffIso() {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - liveFeedState.lookbackDays);
    return cutoff.toISOString();
}

function normalizeLiveFeedKeywords(keywords) {
    if (!Array.isArray(keywords)) return [];

    const seen = new Set();
    return keywords
        .map(keyword => (typeof keyword === 'string' ? keyword.trim() : ''))
        .filter(Boolean)
        .filter(keyword => {
            const key = keyword.toLocaleLowerCase();
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
}

async function fetchKeywordsForLiveFeed(userId) {
    const keywordState = window.globalRadarKeywords;
    if (
        keywordState?.currentUserId === userId &&
        Array.isArray(keywordState.keywords)
    ) {
        return normalizeLiveFeedKeywords(keywordState.keywords);
    }

    const { data: profile, error } = await _supabase
        .from('profiles')
        .select('keywords')
        .eq('id', userId)
        .single();

    if (error) {
        console.warn('Unable to load Global Radar keywords for Live Feed.', error);
        return [];
    }

    return normalizeLiveFeedKeywords(profile?.keywords);
}

async function fetchSubscribedFeedWithFallback(userId) {
    const cutoffIso = getLiveFeedCutoffIso();

    // 優先使用 RPC（DB 端聚合較省讀取），若未建立則 fallback 直接查詢
    const { data: rpcData, error: rpcError } = await _supabase.rpc('get_user_feed', {
        p_user_id: userId,
        p_per_cat_limit: 50,
        p_overall_limit: liveFeedState.fetchSourceLimit,
        p_days: liveFeedState.lookbackDays
    });

    if (!rpcError && Array.isArray(rpcData)) {
        return rpcData;
    }

    const { data: subs, error: subsError } = await _supabase
        .from('user_subscriptions')
        .select('category_id')
        .eq('user_id', userId);

    if (subsError) throw subsError;

    const subIds = (subs || []).map(s => s.category_id);
    if (subIds.length === 0) return [];

    let query = _supabase
        .from('announcements')
        .select(FEED_SELECT_WITH_PUBLISHED_AT)
        .in('category_id', subIds)
        .gte('published_at', cutoffIso)
        .order('published_at', { ascending: false, nullsFirst: false })
        .order('created_at', { ascending: false })
        .limit(liveFeedState.fetchSourceLimit);

    let { data, error } = await query;

    if (error) {
        const retry = await _supabase
            .from('announcements')
            .select(FEED_SELECT_WITHOUT_PUBLISHED_AT)
            .in('category_id', subIds)
            .gte('created_at', cutoffIso)
            .order('created_at', { ascending: false })
            .limit(liveFeedState.fetchSourceLimit);
        data = retry.data;
        error = retry.error;
    }

    if (error) throw error;
    return data || [];
}

async function fetchKeywordMatchesByField(keyword, fieldName) {
    const pattern = `%${keyword}%`;
    const cutoffIso = getLiveFeedCutoffIso();

    let { data, error } = await _supabase
        .from('announcements')
        .select(FEED_SELECT_WITH_PUBLISHED_AT)
        .ilike(fieldName, pattern)
        .gte('published_at', cutoffIso)
        .order('published_at', { ascending: false, nullsFirst: false })
        .order('created_at', { ascending: false })
        .limit(liveFeedState.fetchSourceLimit);

    if (error) {
        const retry = await _supabase
            .from('announcements')
            .select(FEED_SELECT_WITHOUT_PUBLISHED_AT)
            .ilike(fieldName, pattern)
            .gte('created_at', cutoffIso)
            .order('created_at', { ascending: false })
            .limit(liveFeedState.fetchSourceLimit);
        data = retry.data;
        error = retry.error;
    }

    if (error) {
        console.warn(`Unable to load Global Radar matches from ${fieldName}.`, error);
        return [];
    }

    return data || [];
}

async function fetchAnnouncementRowsForUrls(urls) {
    const uniqueUrls = Array.from(new Set((urls || []).flatMap(getAnnouncementUrlCandidates).filter(Boolean)));
    if (uniqueUrls.length === 0) return [];

    const rows = [];
    const chunkSize = 50;

    for (let i = 0; i < uniqueUrls.length; i += chunkSize) {
        const chunk = uniqueUrls.slice(i, i + chunkSize);
        let { data, error } = await _supabase
            .from('announcements')
            .select(FEED_SELECT_WITH_PUBLISHED_AT)
            .in('url', chunk)
            .order('published_at', { ascending: false, nullsFirst: false })
            .order('created_at', { ascending: false });

        if (error) {
            const retry = await _supabase
                .from('announcements')
                .select(FEED_SELECT_WITHOUT_PUBLISHED_AT)
                .in('url', chunk)
                .order('created_at', { ascending: false });
            data = retry.data;
            error = retry.error;
        }

        if (error) {
            console.warn('Unable to load full tag set for Global Radar matches.', error);
            continue;
        }

        rows.push(...(data || []));
    }

    return rows;
}

function appendUnique(target, value) {
    if (value && !target.includes(value)) {
        target.push(value);
    }
}

async function fetchGlobalKeywordFeed(userId) {
    const keywords = await fetchKeywordsForLiveFeed(userId);
    if (keywords.length === 0) return [];

    const matchedByKey = new Map();

    for (const keyword of keywords) {
        const [titleMatches, sourceMatches] = await Promise.all([
            fetchKeywordMatchesByField(keyword, 'title'),
            fetchKeywordMatchesByField(keyword, 'source')
        ]);

        [...titleMatches, ...sourceMatches].forEach(item => {
            const key = getAnnouncementKey(item);
            const triggerLabel = `global_keyword:${keyword}`;
            const existing = matchedByKey.get(key);

            if (!existing) {
                matchedByKey.set(key, {
                    ...item,
                    trigger_type: triggerLabel,
                    triggers: [triggerLabel],
                    matched_keywords: [keyword],
                    sources: [item.source || item.category_id || '未分類']
                });
                return;
            }

            appendUnique(existing.triggers, triggerLabel);
            appendUnique(existing.matched_keywords, keyword);
            appendUnique(existing.sources, item.source || item.category_id || '未分類');
        });
    }

    const matchedUrls = Array.from(matchedByKey.values()).map(item => item.url).filter(Boolean);
    const fullTagRows = await fetchAnnouncementRowsForUrls(matchedUrls);

    fullTagRows.forEach(item => {
        const key = getAnnouncementKey(item);
        const existing = matchedByKey.get(key);
        if (!existing) return;

        appendUnique(existing.sources, item.source || item.category_id || '未分類');
    });

    return Array.from(matchedByKey.values());
}

async function fetchFeedWithFallback(userId) {
    const [subscribedItems, keywordItems] = await Promise.all([
        fetchSubscribedFeedWithFallback(userId),
        fetchGlobalKeywordFeed(userId)
    ]);

    return [...subscribedItems, ...keywordItems];
}

async function reloadLiveFeedForUser(userId) {
    if (!userId || liveFeedState.isLoading) return;
    liveFeedState.isLoading = true;
    liveFeedState.currentUserId = userId;
    setLiveFeedStatus('Live Feed 載入中...', 'loading');

    try {
        const fetchedItems = await fetchFeedWithFallback(userId);
        // aggregate same announcement (by canonical URL) to combine multiple triggers/tags
        const aggregatedItems = aggregateFeedItems(fetchedItems);
        setGlobalKeywordMatchCount(countGlobalKeywordMatches(aggregatedItems));

        const items = aggregatedItems.slice(0, liveFeedState.maxTotal);
        liveFeedState.allItems = items;
        liveFeedState.visibleCount = 0;

        if (items.length === 0) {
            resetLiveFeedWithStatus('你目前的訂閱尚未有可顯示的公告。', 'muted');
            return;
        }

        renderFeedItems(true);
        setLiveFeedStatus(`已載入 ${Math.min(liveFeedState.visibleCount, items.length)} / ${items.length} 筆。`);
    } catch (err) {
        console.error('載入 Live Feed 失敗', err);
        resetLiveFeedWithStatus('載入 Live Feed 失敗，請稍後再試。', 'error');
    } finally {
        liveFeedState.isLoading = false;
    }
}

async function initializeLiveFeed() {
    const loadMoreBtn = document.getElementById('live-feed-load-more');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => {
            renderFeedItems(false);
            setLiveFeedStatus(`已載入 ${liveFeedState.visibleCount} / ${liveFeedState.allItems.length} 筆。`);
        });
    }

    if (!_supabase || !_supabase.auth) {
        resetLiveFeedWithStatus('尚未初始化 Supabase，無法載入 Live Feed。', 'error');
        return;
    }

    _supabase.auth.onAuthStateChange((_event, session) => {
        if (session?.user?.id) {
            reloadLiveFeedForUser(session.user.id);
        } else {
            resetLiveFeedWithStatus('請先登入以載入 Live Feed。');
        }
    });

    window.addEventListener('subscriptions:updated', async (e) => {
        const nextUserId = e?.detail?.userId || liveFeedState.currentUserId;
        if (nextUserId) {
            await reloadLiveFeedForUser(nextUserId);
        }
    });

    window.addEventListener('keywords:updated', async (e) => {
        const nextUserId = e?.detail?.userId || liveFeedState.currentUserId;
        if (nextUserId) {
            await reloadLiveFeedForUser(nextUserId);
        }
    });

    const { data: { session } } = await _supabase.auth.getSession();
    if (session?.user?.id) {
        await reloadLiveFeedForUser(session.user.id);
    } else {
        resetLiveFeedWithStatus('請先登入以載入 Live Feed。');
    }
}

// 頁面初始化
document.addEventListener('DOMContentLoaded', async () => {
    if (window.universitySchemaPromise) {
        await window.universitySchemaPromise;
    }
    loadPreviewData();
    renderMenu();

    const menuContainer = document.getElementById('menu-container');
    if (menuContainer) {
        menuContainer.addEventListener('change', (e) => {
            const target = e.target;
            if (target.matches('.child-checkbox')) {
                updateParentStates(target);
            } else if (target.matches('.parent-checkbox')) {
                updateParentStates(target);
            }
        });
    }

    await initializeLiveFeed();
});

// 預覽模態邏輯
window.categoryPreviewData = null;

async function loadPreviewData() {
    if (window.categoryPreviewData) {
        return; // 已載入則直接返回
    }
    try {
        const response = await fetch('category-previews.json');
        if (response.ok) {
            window.categoryPreviewData = await response.json();
        } else {
            console.warn('無法載入預覽資料');
            window.categoryPreviewData = {};
        }
    } catch (error) {
        console.error('載入預覽資料失敗', error);
        window.categoryPreviewData = {};
    }
}

function openPreviewModal(categoryId) {
    if (!window.categoryPreviewData) {
        alert('預覽資料尚未載入，請稍候');
        return;
    }

    const data = window.categoryPreviewData[categoryId];
    if (!data) {
        alert('此分類暫無預覽資料');
        return;
    }

    const modal = document.getElementById('preview-modal');
    const title = document.getElementById('preview-title');
    const content = document.getElementById('preview-content');

    title.textContent = `${data.label} - 預覽`;

    if (data.announcements.length === 0) {
        content.innerHTML = '<p class="text-sm text-slate-500 text-center py-8">暫無公告</p>';
    } else {
        content.innerHTML = data.announcements.map((anno, idx) => `
            <div class="mb-4 pb-4 ${idx < data.announcements.length - 1 ? 'border-b border-slate-200' : ''}">
                <h4 class="text-sm font-bold text-slate-800 mb-1">
                    <a href="${anno.url}" target="_blank" class="text-blue-600 hover:underline">
                        ${anno.title}
                    </a>
                </h4>
                <p class="text-xs text-slate-500">📅 ${anno.date}</p>
            </div>
        `).join('');
    }

    modal.classList.remove('hidden');
}

function closePreviewModal() {
    const modal = document.getElementById('preview-modal');
    modal.classList.add('hidden');
}

function aggregateFeedItems(items) {
    if (!Array.isArray(items)) return [];
    const map = new Map();
    const normalizeList = (value, fallback) => {
        if (Array.isArray(value)) {
            return value.filter(Boolean);
        }
        if (value) {
            return [value];
        }
        return fallback ? [fallback] : [];
    };

    items.forEach(item => {
        const key = getAnnouncementKey(item);
        const triggerLabels = normalizeList(item.triggers, item.trigger_type || '選單訂閱');
        const sourceLabels = normalizeList(item.sources, item.source || item.category_id || '未分類');

        if (!map.has(key)) {
            map.set(key, Object.assign({}, item, {
                triggers: Array.from(new Set(triggerLabels)),
                sources: Array.from(new Set(sourceLabels))
            }));
        } else {
            const cur = map.get(key);
            triggerLabels.forEach(label => {
                if (label && !cur.triggers.includes(label)) cur.triggers.push(label);
            });
            sourceLabels.forEach(label => {
                if (label && !cur.sources.includes(label)) cur.sources.push(label);
            });
            // prefer the newest published_at if available
            if (item.published_at && (!cur.published_at || new Date(item.published_at) > new Date(cur.published_at))) {
                cur.published_at = item.published_at;
            }
            if (item.created_at && (!cur.created_at || new Date(item.created_at) > new Date(cur.created_at))) {
                cur.created_at = item.created_at;
            }
            if (!cur.title && item.title) cur.title = item.title;
        }
    });
    // Normalize sources into single string
    return Array.from(map.values())
        .map(it => ({
            ...it,
            source: (it.sources || []).join(', '),
            triggers: it.triggers || []
        }))
        .sort((a, b) => {
            const aTime = new Date(a.published_at || a.created_at || 0).getTime();
            const bTime = new Date(b.published_at || b.created_at || 0).getTime();
            return bTime - aTime;
        });
}
