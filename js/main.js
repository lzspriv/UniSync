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

    const renderChannels = (channels = [], parentPath = []) => channels.map(ch => {
        const displayLabel = [...parentPath, ch.name].filter(Boolean).join('-');
        return `
        <div class="menu-channel-row" data-menu-leaf data-menu-text="${escapeAttribute(displayLabel || ch.name)}">
            <label class="menu-channel">
                <input type="checkbox" value="${ch.value}" class="child-checkbox">
                <span>${ch.name}</span>
            </label>
            <button type="button" class="preview-btn" data-preview-category="${escapeAttribute(ch.value)}" data-preview-label="${escapeAttribute(displayLabel)}" title="預覽此分類">
                <i class="fas fa-eye"></i>
            </button>
        </div>
    `;
    }).join('');

    const renderMenuToolbar = () => `
        <div class="menu-toolbar">
            <div class="menu-toolbar-summary">
                <span class="menu-toolbar-title">訂閱來源</span>
                <span id="menu-selected-count" class="menu-selected-count">已選 0</span>
            </div>
            <div class="menu-search-wrap">
                <i class="fas fa-search menu-search-icon"></i>
                <input id="menu-search-input" type="search" class="menu-search-input" placeholder="搜尋單位或公告類型">
            </div>
            <div class="menu-toolbar-actions">
                <label class="menu-filter-toggle">
                    <input id="menu-selected-only" type="checkbox">
                    <span>只看已選</span>
                </label>
                <button type="button" id="menu-expand-all" class="menu-tool-btn" title="展開全部"><i class="fas fa-angles-down"></i></button>
                <button type="button" id="menu-collapse-all" class="menu-tool-btn" title="收合全部"><i class="fas fa-angles-up"></i></button>
            </div>
        </div>
    `;

    const hasMenuChildren = (node) =>
        (node.channels || []).length > 0 || (node.subUnits || []).length > 0;

    const countSubscribableChannels = (node) =>
        (node.channels || []).length +
        (node.units || []).reduce((sum, child) => sum + countSubscribableChannels(child), 0) +
        (node.subUnits || []).reduce((sum, child) => sum + countSubscribableChannels(child), 0);

    const renderSubUnit = (sub, parentPath = []) => {
        const hasChildren = hasMenuChildren(sub);
        const subscribableCount = countSubscribableChannels(sub);
        const hasSubscribable = subscribableCount > 0;
        const currentPath = [...parentPath, sub.name].filter(Boolean);
        return `
            <div class="menu-subunit menu-node ${hasChildren ? '' : 'menu-node-empty'}" data-menu-node data-menu-text="${escapeHtml(sub.name)}" data-subscribable="${hasSubscribable ? 'true' : 'false'}">
                <div class="menu-row menu-row-sub ${hasChildren ? '' : 'menu-row-empty'}" ${hasChildren ? 'aria-expanded="false"' : ''}>
                    <div class="menu-row-left" ${hasChildren ? `data-menu-toggle="${escapeAttribute(sub.id)}" role="button" tabindex="0"` : ''}>
                        ${hasChildren
                            ? `<i id="icon-${sub.id}" class="fas fa-caret-right menu-icon menu-icon-sub"></i>`
                            : '<span class="menu-icon menu-icon-sub"></span>'}
                        <span class="menu-label">${sub.name}</span>
                        ${hasSubscribable ? `<span class="menu-count">${subscribableCount}</span>` : ''}
                    </div>
                    ${hasSubscribable ? `
                        <input type="checkbox" class="menu-checkbox menu-checkbox-sub parent-checkbox"
                               onclick="event.stopPropagation(); handleParentClick(this, '${sub.id}')">
                    ` : '<span class="menu-pending-badge">待接公告</span>'}
                </div>
                ${hasChildren ? `
                    <div id="${sub.id}" class="collapsible-content menu-children menu-children-channel">
                        ${(sub.channels || []).length > 0 ? renderChannels(sub.channels, currentPath) : ''}
                        ${(sub.subUnits || []).map(child => renderSubUnit(child, currentPath)).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    };

    const renderUnit = (unit, parentPath = []) => {
        const hasChildren = hasMenuChildren(unit);
        const subscribableCount = countSubscribableChannels(unit);
        const hasSubscribable = subscribableCount > 0;
        const currentPath = [...parentPath, unit.name].filter(Boolean);
        return `
            <div class="menu-unit menu-node ${hasChildren ? '' : 'menu-node-empty'}" data-menu-node data-menu-text="${escapeHtml(unit.name)}" data-subscribable="${hasSubscribable ? 'true' : 'false'}">
                <div class="menu-row menu-row-unit ${hasChildren ? '' : 'menu-row-empty'}" ${hasChildren ? 'aria-expanded="false"' : ''}>
                    <div class="menu-row-left" ${hasChildren ? `data-menu-toggle="${escapeAttribute(unit.id)}" role="button" tabindex="0"` : ''}>
                        ${hasChildren
                            ? `<i id="icon-${unit.id}" class="fas fa-caret-right menu-icon menu-icon-unit"></i>`
                            : '<span class="menu-icon menu-icon-unit"></span>'}
                        <span class="menu-label">${unit.name}</span>
                        ${hasSubscribable ? `<span class="menu-count">${subscribableCount}</span>` : ''}
                    </div>
                    ${hasSubscribable ? `
                        <input type="checkbox" class="menu-checkbox menu-checkbox-unit parent-checkbox"
                               onclick="event.stopPropagation(); handleParentClick(this, '${unit.id}')">
                    ` : '<span class="menu-pending-badge">待接公告</span>'}
                </div>
                ${hasChildren ? `
                    <div id="${unit.id}" class="collapsible-content menu-children menu-children-unit">
                        ${(unit.channels || []).length > 0 ? renderChannels(unit.channels, currentPath) : ''}
                        ${(unit.subUnits || []).map(sub => renderSubUnit(sub, [])).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    };

    container.innerHTML = `
        ${renderMenuToolbar()}
        <div id="menu-empty-state" class="menu-empty-state hidden">找不到符合條件的單位或公告類型</div>
        ${universitySchema.map(category => {
        const subscribableCount = countSubscribableChannels(category);
        return `
        <div class="menu-group border border-slate-200 rounded-2xl overflow-hidden mb-4 bg-white" data-menu-group>
            <div class="menu-row menu-row-category" aria-expanded="false">
                <div class="menu-row-left" data-menu-toggle="${escapeAttribute(category.id)}" role="button" tabindex="0">
                    <i id="icon-${category.id}" class="fas fa-chevron-right menu-icon menu-icon-category"></i>
                    <span class="menu-label menu-label-category">${category.name}</span>
                    ${subscribableCount > 0 ? `<span class="menu-count">${subscribableCount}</span>` : '<span class="menu-pending-badge">待接公告</span>'}
                </div>
                ${subscribableCount > 0 ? `<input type="checkbox" class="menu-checkbox menu-checkbox-category parent-checkbox"
                       onclick="event.stopPropagation(); handleParentClick(this, '${category.id}')">
                ` : ''}
            </div>
            <div id="${category.id}" class="collapsible-content menu-children menu-children-category">
                ${(category.units || []).map(unit => renderUnit(unit, [])).join('')}
            </div>
        </div>
    `;
    }).join('')}
    `;

    bindMenuToolbar();
    bindMenuInteractions();
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

function syncAncestorHeights(content) {
    let parent = content.parentElement?.closest('.collapsible-content.expanded');
    while (parent) {
        parent.style.height = parent.dataset.animating === 'true' ? `${parent.scrollHeight}px` : 'auto';
        parent = parent.parentElement?.closest('.collapsible-content.expanded');
    }
}

function syncExpandedMenuHeights(root = document) {
    if (!root) return;

    Array.from(root.querySelectorAll('.collapsible-content.expanded'))
        .reverse()
        .forEach(content => {
            content.style.height = content.dataset.animating === 'true' ? `${content.scrollHeight}px` : 'auto';
        });
}

function setCollapsibleExpanded(content, expanded) {
    const animationToken = `${Date.now()}-${Math.random()}`;
    content.dataset.animationToken = animationToken;

    const finishAnimation = () => {
        if (content.dataset.animationToken !== animationToken) return;

        content.dataset.animating = 'false';
        if (content.classList.contains('expanded')) {
            content.style.height = 'auto';
        }
        syncAncestorHeights(content);
    };

    content.addEventListener('transitionend', (event) => {
        if (event.target === content && event.propertyName === 'height') {
            finishAnimation();
        }
    }, { once: true });
    window.setTimeout(finishAnimation, 320);

    if (expanded) {
        content.dataset.animating = 'true';
        content.classList.add('expanded');
        content.style.height = '0px';
        content.offsetHeight;
        content.style.height = `${content.scrollHeight}px`;
        syncAncestorHeights(content);
        return;
    }

    content.dataset.animating = 'true';
    content.style.height = `${content.scrollHeight}px`;
    content.offsetHeight;
    content.classList.remove('expanded');
    content.style.height = '0px';
    syncAncestorHeights(content);
}

function toggleElement(id) {
    const content = document.getElementById(id);
    if (!content) return;

    setMenuNodeExpanded(id, !content.classList.contains('expanded'));
}

function bindMenuInteractions() {
    const container = document.getElementById('menu-container');
    if (!container) return;
    if (container.dataset.menuInteractionsBound === 'true') return;
    container.dataset.menuInteractionsBound = 'true';

    container.addEventListener('click', (event) => {
        const previewButton = event.target.closest('[data-preview-category]');
        if (previewButton && container.contains(previewButton)) {
            event.preventDefault();
            event.stopPropagation();
            openPreviewModal(previewButton.dataset.previewCategory, previewButton.dataset.previewLabel);
            return;
        }

        const toggleTarget = event.target.closest('[data-menu-toggle]');
        if (!toggleTarget || !container.contains(toggleTarget)) return;

        event.preventDefault();
        event.stopPropagation();
        toggleElement(toggleTarget.dataset.menuToggle);
    });

    container.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;

        const toggleTarget = event.target.closest('[data-menu-toggle]');
        if (!toggleTarget || !container.contains(toggleTarget)) return;

        event.preventDefault();
        toggleElement(toggleTarget.dataset.menuToggle);
    });
}

function updateMenuExpandedState(content, expanded) {
    const icon = document.getElementById(`icon-${content.id}`);
    icon?.classList.toggle('rotate-icon', expanded);

    const row = content.previousElementSibling;
    if (row) {
        row.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    }
}

function setMenuNodeExpanded(id, expanded) {
    const content = document.getElementById(id);
    if (!content) return;

    setCollapsibleExpanded(content, expanded);
    updateMenuExpandedState(content, expanded);
}

function updateMenuSelectedSummary() {
    const selectedCount = document.querySelectorAll('#menu-container .child-checkbox:checked').length;
    const selectedCountEl = document.getElementById('menu-selected-count');
    if (selectedCountEl) {
        selectedCountEl.textContent = `已選 ${selectedCount}`;
    }
}
window.updateMenuSelectedSummary = updateMenuSelectedSummary;

function bindMenuToolbar() {
    const searchInput = document.getElementById('menu-search-input');
    const selectedOnly = document.getElementById('menu-selected-only');
    const expandAllBtn = document.getElementById('menu-expand-all');
    const collapseAllBtn = document.getElementById('menu-collapse-all');

    const applyFilter = () => {
        const query = (searchInput?.value || '').trim().toLowerCase();
        const onlySelected = Boolean(selectedOnly?.checked);
        const groups = Array.from(document.querySelectorAll('[data-menu-group]'));
        let visibleGroups = 0;

        groups.forEach(group => {
            const nodes = Array.from(group.querySelectorAll('[data-menu-node]'));
            const leaves = Array.from(group.querySelectorAll('[data-menu-leaf]'));

            leaves.forEach(item => {
                const text = (item.dataset.menuText || item.textContent || '').toLowerCase();
                const isSelected = Boolean(item.querySelector('.child-checkbox:checked'));
                const matchesQuery = !query || text.includes(query);
                const matchesSubscriptionFilter = !onlySelected || isSelected;
                const visible = matchesQuery && matchesSubscriptionFilter;
                item.classList.toggle('hidden', !visible);
            });

            [...nodes].reverse().forEach(item => {
                const text = (item.dataset.menuText || item.textContent || '').toLowerCase();
                const hasSelectedDescendant = Boolean(item.querySelector('.child-checkbox:checked'));
                const matchesQuery = !query || text.includes(query);
                const matchesSubscriptionFilter = !onlySelected || hasSelectedDescendant;
                const selfMatches = matchesQuery && matchesSubscriptionFilter;
                const hasVisibleDescendant = Boolean(item.querySelector('[data-menu-node]:not(.hidden), [data-menu-leaf]:not(.hidden)'));
                item.classList.toggle('hidden', !(selfMatches || hasVisibleDescendant));
            });

            const groupHasMatch = Boolean(group.querySelector('[data-menu-node]:not(.hidden), [data-menu-leaf]:not(.hidden)'));
            group.classList.toggle('hidden', !groupHasMatch);
            if (groupHasMatch) visibleGroups += 1;

            if (query || onlySelected) {
                group.querySelectorAll('.collapsible-content').forEach(content => {
                    const hasVisibleChild = Boolean(content.querySelector('[data-menu-node]:not(.hidden), [data-menu-leaf]:not(.hidden)'));
                    if (hasVisibleChild) {
                        setMenuNodeExpanded(content.id, true);
                    }
                });
            }
        });

        document.getElementById('menu-empty-state')?.classList.toggle('hidden', visibleGroups > 0);
        syncExpandedMenuHeights(document.getElementById('menu-container'));
    };

    searchInput?.addEventListener('input', applyFilter);
    selectedOnly?.addEventListener('change', applyFilter);
    window.applyMenuFilter = applyFilter;
    updateMenuSelectedSummary();

    expandAllBtn?.addEventListener('click', () => {
        document.querySelectorAll('#menu-container .collapsible-content').forEach(content => setMenuNodeExpanded(content.id, true));
        syncExpandedMenuHeights(document.getElementById('menu-container'));
    });

    collapseAllBtn?.addEventListener('click', () => {
        document.querySelectorAll('#menu-container .collapsible-content').forEach(content => setMenuNodeExpanded(content.id, false));
    });
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

function escapeAttribute(value) {
    return escapeHtml(value);
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

function parseSourceLabel(source) {
    const text = String(source || '').trim();
    const separatorIndex = text.indexOf('-');

    if (separatorIndex <= 0) {
        return {
            unit: text,
            category: ''
        };
    }

    return {
        unit: text.slice(0, separatorIndex).trim(),
        category: text.slice(separatorIndex + 1).trim()
    };
}

function groupSourceLabels(sources) {
    const groups = [];
    const groupMap = new Map();

    Array.from(new Set((sources || []).filter(Boolean))).forEach(source => {
        const parsed = parseSourceLabel(source);
        if (!parsed.unit) return;

        if (!groupMap.has(parsed.unit)) {
            const group = {
                unit: parsed.unit,
                categories: []
            };
            groupMap.set(parsed.unit, group);
            groups.push(group);
        }

        if (parsed.category) {
            const group = groupMap.get(parsed.unit);
            if (!group.categories.includes(parsed.category)) {
                group.categories.push(parsed.category);
            }
        }
    });

    return groups;
}

function renderSourceLabels(sources, compact = false) {
    const groups = groupSourceLabels(sources);
    const visibleChipCount = compact ? 4 : 3;
    const containerClass = compact
        ? 'flex min-w-0 max-w-full flex-col gap-2 leading-relaxed'
        : 'flex min-w-[15rem] max-w-[22rem] flex-col gap-2 leading-relaxed';

    if (groups.length === 0) {
        return `
            <div class="${containerClass}">
                <span class="text-sm font-bold text-slate-500">未分類</span>
            </div>
        `;
    }

    return `
        <div class="${containerClass}">
            ${groups.map(group => {
                const visibleCategories = group.categories.slice(0, visibleChipCount);
                const hiddenCategories = group.categories.slice(visibleChipCount);
                const hiddenCount = Math.max(group.categories.length - visibleCategories.length, 0);
                const fullLabel = group.categories.length > 0
                    ? `${group.unit}-${group.categories.join('、')}`
                    : group.unit;

                return `
                    <div class="min-w-0" title="${escapeHtml(fullLabel)}">
                        <div class="truncate text-sm font-black text-slate-700">${escapeHtml(group.unit)}</div>
                        ${group.categories.length > 0 ? `
                            <div class="mt-1 flex flex-wrap gap-1.5">
                                ${visibleCategories.map(category => `
                                    <span class="inline-flex max-w-full items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-bold leading-5 text-slate-600">
                                        <span class="truncate">${escapeHtml(category)}</span>
                                    </span>
                                `).join('')}
                                ${hiddenCategories.map(category => `
                                    <span class="hidden max-w-full items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-bold leading-5 text-slate-600" data-source-extra>
                                        <span class="truncate">${escapeHtml(category)}</span>
                                    </span>
                                `).join('')}
                                ${hiddenCount > 0 ? `
                                    <button type="button" class="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-black leading-5 text-blue-600 hover:bg-blue-100" data-source-toggle data-expanded="false" data-more-label="+${hiddenCount}" data-less-label="收合">+${hiddenCount}</button>
                                ` : ''}
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function toggleSourceGroup(button) {
    const wrapper = button.closest('[title]');
    if (!wrapper) return;

    const expanded = button.dataset.expanded === 'true';
    wrapper.querySelectorAll('[data-source-extra]').forEach(chip => {
        chip.classList.toggle('hidden', expanded);
        chip.classList.toggle('inline-flex', !expanded);
    });

    button.dataset.expanded = expanded ? 'false' : 'true';
    button.textContent = expanded ? button.dataset.moreLabel : button.dataset.lessLabel;
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
    setLiveFeedStatus('最近命中載入中...', 'loading');

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
        resetLiveFeedWithStatus('載入最近命中失敗，請稍後再試。', 'error');
    } finally {
        liveFeedState.isLoading = false;
    }
}

async function initializeLiveFeed() {
    const tableBody = document.getElementById('live-feed-table-body');
    const mobileContainer = document.getElementById('live-feed-mobile');
    const loadMoreBtn = document.getElementById('live-feed-load-more');

    [tableBody, mobileContainer].filter(Boolean).forEach(container => {
        container.addEventListener('click', (event) => {
            const toggleButton = event.target.closest('[data-source-toggle]');
            if (!toggleButton || !container.contains(toggleButton)) return;
            event.preventDefault();
            event.stopPropagation();
            toggleSourceGroup(toggleButton);
        });
    });

    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => {
            renderFeedItems(false);
            setLiveFeedStatus(`已載入 ${liveFeedState.visibleCount} / ${liveFeedState.allItems.length} 筆。`);
        });
    }

    if (!_supabase || !_supabase.auth) {
        resetLiveFeedWithStatus('尚未初始化 Supabase，無法載入最近命中。', 'error');
        return;
    }

    _supabase.auth.onAuthStateChange((_event, session) => {
        if (session?.user?.id) {
            reloadLiveFeedForUser(session.user.id);
        } else {
            resetLiveFeedWithStatus('請先登入以載入最近命中。');
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
        resetLiveFeedWithStatus('請先登入以載入最近命中。');
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
            updateMenuSelectedSummary();
            window.applyMenuFilter?.();
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

function openPreviewModal(categoryId, displayLabel = '') {
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

    const previewLabel = displayLabel || data.full_label || data.label;
    title.textContent = `${previewLabel} - 預覽`;

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
                <p class="text-xs text-slate-500">📅 ${anno.date_label || '發布日期'}：${anno.date}</p>
                ${anno.show_summary && anno.summary ? `<p class="mt-1 text-xs leading-relaxed text-slate-600">${anno.summary}</p>` : ''}
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
