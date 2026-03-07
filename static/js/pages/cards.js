/**
 * cards.js — 卡片管理頁面：展示每張卡的回饋優惠
 */

const BANK_COLORS = {
  "國泰世華": "#1A6B4B", "中國信託": "#C8102E", "玉山銀行": "#006B3F",
  "台新銀行": "#E31937", "永豐銀行": "#003DA5", "富邦銀行": "#00205B",
  "聯邦銀行": "#1B3F8B", "滙豐銀行": "#DB0011", "遠東商銀": "#003A70",
  "第一銀行": "#008751", "美國運通": "#006FCF", "星展銀行": "#E31837",
  "凱基銀行": "#B8860B", "新光銀行": "#FF6600", "華南銀行": "#003399",
  "兆豐銀行": "#0066B3", "渣打銀行": "#0072AA", "合作金庫": "#00843D",
  "台灣企銀": "#004B87",
};

const REWARD_TYPE_LABEL = {
  cashback: "現金回饋",
  points: "點數",
  miles: "哩程",
};

let _allCards = null;

async function CardsPage() {
  const allCards = await (_allCards || API.getCards());
  _allCards = allCards;

  const myIds = Store.getMyCards();
  const myCards = allCards.filter((c) => myIds.includes(c.id));

  let cardsHtml = "";
  if (myCards.length) {
    myCards.forEach((c) => {
      const color = BANK_COLORS[c.bank_name] || "#555";
      const feeText = c.annual_fee ? `年費 $${c.annual_fee}` : "免年費";
      cardsHtml += `
        <div class="cd-card" data-card-id="${c.id}">
          <div class="cd-card-header" style="background:${color}">
            <div class="cd-card-info">
              <div class="cd-card-bank">${c.bank_name}</div>
              <div class="cd-card-name">${c.card_name}</div>
              <div class="cd-card-fee">${feeText}</div>
            </div>
            <div class="cd-card-actions">
              <span class="cd-card-expand">▼</span>
              <span class="cd-card-remove" data-remove="${c.id}">&times;</span>
            </div>
          </div>
          ${c.note ? `<div class="cd-card-note">${c.note}</div>` : ""}
          <div class="cd-card-rewards" id="rewards-${c.id}">
            <div class="cd-loading">載入優惠中...</div>
          </div>
        </div>`;
    });
  } else {
    cardsHtml = `<div class="cd-empty">
      <div class="cd-empty-icon">💳</div>
      <div class="cd-empty-text">還沒有卡片</div>
      <div class="cd-empty-hint">點擊下方按鈕新增你的信用卡，查看各分類的回饋優惠</div>
    </div>`;
  }

  return `
    <div class="cards-page">
      <div class="page-title">💳 我的卡片</div>
      <div class="cd-card-list">${cardsHtml}</div>
      <button class="cd-add-btn" id="btnAddCard">
        <span class="cd-add-icon">+</span> 新增卡片
      </button>
    </div>

    <!-- 新增卡片 Modal -->
    <div class="modal-overlay" id="addCardModal">
      <div class="modal-content">
        <div class="modal-header">
          <span class="modal-close" id="modalClose">&times;</span>
          <span class="modal-title">新增信用卡</span>
        </div>
        <div class="modal-search">
          <input class="modal-search-input" id="cardSearchInput"
            type="text" placeholder="搜尋銀行或卡片名稱" autocomplete="off">
          <span class="modal-search-icon">🔍</span>
        </div>
        <div class="modal-list" id="cardSearchList"></div>
      </div>
    </div>
  `;
}

CardsPage.init = () => {
  const modal = document.getElementById("addCardModal");
  const cardSearchInput = document.getElementById("cardSearchInput");
  const listEl = document.getElementById("cardSearchList");
  const cardListEl = document.querySelector(".cd-card-list");

  // ── 載入每張卡的回饋明細 ──
  const myIds = Store.getMyCards();
  const _rewardsCache = {};

  async function loadCardRewards(cardId) {
    if (_rewardsCache[cardId]) return _rewardsCache[cardId];
    const rewards = await API.getCardRewards(cardId);
    _rewardsCache[cardId] = rewards;
    return rewards;
  }

  function renderRewards(cardId, rewards) {
    const container = document.getElementById(`rewards-${cardId}`);
    if (!container) return;

    if (!rewards.length) {
      container.innerHTML = '<div class="cd-no-rewards">暫無回饋資料</div>';
      return;
    }

    // 按父分類分組
    const groups = {};
    rewards.forEach((r) => {
      const groupName = r.parent_name || r.category_name;
      if (!groups[groupName]) groups[groupName] = [];
      groups[groupName].push(r);
    });

    let html = "";
    Object.entries(groups).forEach(([groupName, items]) => {
      html += `<div class="cd-reward-group">`;
      html += `<div class="cd-reward-group-name">${groupName}</div>`;
      items.forEach((r) => {
        const typeLabel = REWARD_TYPE_LABEL[r.reward_type] || r.reward_type;
        const capHtml = r.reward_cap
          ? `<span class="cd-reward-cap">上限 $${r.reward_cap}/月</span>`
          : "";
        const condHtml = r.conditions
          ? `<span class="cd-reward-cond">${r.conditions}</span>`
          : "";
        const rateClass = r.reward_rate >= 3 ? "high" : r.reward_rate >= 1.5 ? "mid" : "";

        html += `
          <div class="cd-reward-row">
            <div class="cd-reward-cat">${r.category_name !== groupName ? r.category_name : ""}</div>
            <div class="cd-reward-detail">
              <span class="cd-reward-rate ${rateClass}">${r.reward_rate}%</span>
              <span class="cd-reward-type">${typeLabel}</span>
              ${capHtml}${condHtml}
            </div>
          </div>`;
      });
      html += `</div>`;
    });

    container.innerHTML = html;
  }

  // 預先載入所有卡的回饋
  myIds.forEach(async (id) => {
    try {
      const rewards = await loadCardRewards(id);
      renderRewards(id, rewards);
    } catch (e) {
      const c = document.getElementById(`rewards-${id}`);
      if (c) c.innerHTML = '<div class="cd-no-rewards">載入失敗</div>';
    }
  });

  // ── 展開/收合 ──
  cardListEl.addEventListener("click", (e) => {
    const header = e.target.closest(".cd-card-header");
    if (!header) return;
    // 不要在點擊刪除按鈕時觸發展開
    if (e.target.closest(".cd-card-remove")) return;
    const card = header.closest(".cd-card");
    card.classList.toggle("expanded");
  });

  // ── 移除卡片 ──
  cardListEl.addEventListener("click", (e) => {
    const removeBtn = e.target.closest(".cd-card-remove");
    if (!removeBtn) return;
    e.stopPropagation();
    const cardId = parseInt(removeBtn.dataset.remove, 10);
    Store.toggleCard(cardId);
    // 重新渲染整頁
    location.hash = "#/cards";
  });

  // ── Modal 邏輯 ──
  function openModal() {
    modal.classList.add("show");
    cardSearchInput.value = "";
    cardSearchInput.focus();
    renderCardList("");
  }

  function closeModal() {
    modal.classList.remove("show");
  }

  function renderCardList(query) {
    const currentIds = Store.getMyCards();
    const q = query.toLowerCase();
    const filtered = _allCards.filter(
      (c) =>
        !q ||
        c.bank_name.toLowerCase().includes(q) ||
        c.card_name.toLowerCase().includes(q)
    );
    const groups = {};
    filtered.forEach((c) => {
      if (!groups[c.bank_name]) groups[c.bank_name] = [];
      groups[c.bank_name].push(c);
    });

    let html = "";
    Object.entries(groups).forEach(([bank, bankCards]) => {
      bankCards.forEach((c) => {
        const isAdded = currentIds.includes(c.id);
        const color = BANK_COLORS[bank] || "#555";
        html += `
          <div class="modal-card-item">
            <div class="modal-card-icon" style="background:${color}">
              <span>${bank.substring(0, 1)}</span>
            </div>
            <div class="modal-card-info">
              <div class="modal-card-name">${c.card_name}</div>
              <div class="modal-card-bank">${bank}</div>
            </div>
            <button class="modal-card-btn ${isAdded ? "added" : ""}"
              data-card-id="${c.id}">${isAdded ? "已新增" : "新增"}</button>
          </div>`;
      });
    });
    if (!filtered.length) {
      html = '<div class="modal-empty">找不到符合的卡片</div>';
    }
    listEl.innerHTML = html;
  }

  document.getElementById("btnAddCard").addEventListener("click", openModal);
  document.getElementById("modalClose").addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  cardSearchInput.addEventListener("input", () => {
    renderCardList(cardSearchInput.value.trim());
  });
  listEl.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-card-id]");
    if (!btn) return;
    Store.toggleCard(parseInt(btn.dataset.cardId, 10));
    renderCardList(cardSearchInput.value.trim());
  });
};
