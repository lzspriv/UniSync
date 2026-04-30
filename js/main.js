/**
 * 渲染組織選單[cite: 1]
 */
function renderMenu() {
    const container = document.getElementById('menu-container');
    if (!container) return;

    const renderChannels = (channels) => channels.map(ch => `
        <label class="menu-channel">
            <input type="checkbox" value="${ch.value}" class="child-checkbox">
            <span>${ch.name}</span>
        </label>
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
                ${renderChannels(sub.channels)}
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
                ${unit.subUnits.map(renderSubUnit).join('')}
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
                ${category.units.map(renderUnit).join('')}
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
    
    // 自動展開選單[cite: 1]
    if (isChecked && !container.classList.contains('expanded')) {
        container.classList.add('expanded');
        document.getElementById(`icon-${containerId}`)?.classList.add('rotate-icon');
    }
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

// 頁面初始化
document.addEventListener('DOMContentLoaded', async () => {
    if (window.universitySchemaPromise) {
        await window.universitySchemaPromise;
    }
    renderMenu();
    // 附加 checkbox 行為監聽，處理 child -> parent 的同步
    const menuContainer = document.getElementById('menu-container');
    if (menuContainer) {
        // 當 child-checkbox 或 parent-checkbox 改變時，同步上層狀態
        menuContainer.addEventListener('change', (e) => {
            const target = e.target;
            if (target.matches('.child-checkbox')) {
                updateParentStates(target);
            } else if (target.matches('.parent-checkbox')) {
                // parent checkbox 會由原本的 onclick 處理子項，但在此也更新上層父層的勾選狀態
                updateParentStates(target);
            }
        });
    }
});

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