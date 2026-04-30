/**
 * 從單一 JSON 設定檔載入校園組織架構資料庫。
 * main.js 會等待這個 promise 完成後再渲染選單。
 */
window.universitySchemaPromise = fetch('config/university-config.json')
    .then(response => {
        if (!response.ok) {
            throw new Error(`無法載入設定檔：${response.status}`);
        }
        return response.json();
    })
    .then(config => {
        window.universitySchema = config.schema || [];
        window.categoryConfig = config.categories || {};
        return config;
    })
    .catch(error => {
        console.error('載入 university-config.json 失敗', error);
        window.universitySchema = [];
        window.categoryConfig = {};
        return { schema: [], categories: {} };
    });