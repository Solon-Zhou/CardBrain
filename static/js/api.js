/**
 * escapeHtml — 全域 HTML 轉義，防止 XSS
 */
function escapeHtml(text) {
  if (text == null) return "";
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

/**
 * api.js — API 呼叫封裝
 */
const API = (() => {
  async function fetchJSON(url) {
    const res = await fetch(Config.API_BASE + url);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  function getCards() {
    return fetchJSON("/api/cards");
  }

  function getCategories() {
    return fetchJSON("/api/categories");
  }

  function recommendByMerchant(q, cardIds) {
    const params = new URLSearchParams({ q });
    if (cardIds.length) params.set("card_ids", cardIds.join(","));
    return fetchJSON(`/api/recommend/merchant?${params}`);
  }

  function recommendByCategory(categoryId, cardIds) {
    const params = new URLSearchParams({ category_id: categoryId });
    if (cardIds.length) params.set("card_ids", cardIds.join(","));
    return fetchJSON(`/api/recommend/category?${params}`);
  }

  function searchMerchants(q) {
    return fetchJSON(`/api/merchants/search?q=${encodeURIComponent(q)}`);
  }

  async function brain(payload) {
    // 自動帶入使用者卡片
    if (!payload.card_ids) {
      payload.card_ids = Store.getMyCards();
    }
    const res = await fetch(Config.API_BASE + "/api/brain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  async function agent(message, history) {
    const payload = {
      message,
      history: history || [],
      card_ids: Store.getMyCards(),
    };
    const res = await fetch(Config.API_BASE + "/api/agent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  function getCardRewards(cardId) {
    return fetchJSON(`/api/cards/${cardId}/rewards`);
  }

  return { getCards, getCategories, recommendByMerchant, recommendByCategory, searchMerchants, brain, agent, getCardRewards };
})();
