/**
 * cards.js — 卡片管理頁面
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

let _allCards = null;

function _buildThumbs(allCards) {
  const myIds = Store.getMyCards();
  const myCards = allCards.filter((c) => myIds.includes(c.id));
  return myCards
    .map((c) => {
      const color = BANK_COLORS[c.bank_name] || "#555";
      return `<div class="card-thumb" data-id="${c.id}" style="background:${color}">
        <span class="card-thumb-x" data-remove="${c.id}">&times;</span>
        <span class="card-thumb-bank">${c.bank_name}</span>
        <span class="card-thumb-name">${c.card_name}</span>
      </div>`;
    })
    .join("");
}

async function CardsPage() {
  const allCards = await (_allCards || API.getCards());
  _allCards = allCards;

  const thumbsHtml = _buildThumbs(allCards);
  const myCount = Store.getMyCards().length;

  return `
    <div class="cards-page">
      <div class="page-title">💳 我的卡片</div>
      <div class="mycard-desc">管理你的信用卡組合，點擊 + 新增，點擊 × 移除</div>

      <div class="mycard-thumbs" id="cardThumbs">
        ${thumbsHtml}
        <div class="card-thumb-add" id="btnAddCard"><span>+</span></div>
      </div>

      ${myCount === 0 ? '<div class="cards-empty-hint">還沒有卡片，點擊 + 開始新增吧！</div>' : ''}
    </div>

    <!-- 新增卡片 Modal -->
    <div class="modal-overlay" id="addCardModal">
      <div class="modal-content">
        <div class="modal-header">
          <span class="modal-close" id="modalClose">&times;</span>
          <span class="modal-title">請輸入信用卡資訊</span>
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
  const thumbsEl = document.getElementById("cardThumbs");

  function refreshThumbs() {
    const html = _buildThumbs(_allCards);
    thumbsEl.innerHTML =
      html + `<div class="card-thumb-add" id="btnAddCard"><span>+</span></div>`;
    document.getElementById("btnAddCard").addEventListener("click", openModal);
    bindRemoveButtons();
  }

  function bindRemoveButtons() {
    thumbsEl.querySelectorAll("[data-remove]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        Store.toggleCard(parseInt(btn.dataset.remove, 10));
        refreshThumbs();
      });
    });
  }

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
    const myIds = Store.getMyCards();
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
        const isAdded = myIds.includes(c.id);
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
    refreshThumbs();
  });
  bindRemoveButtons();
};
