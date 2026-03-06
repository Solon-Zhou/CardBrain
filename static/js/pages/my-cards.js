/**
 * my-cards.js — 選卡頁：卡片縮圖 + 搜尋 modal 新增
 */

// 銀行色票
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

async function MyCardsPage() {
  const cards = await API.getCards();
  _allCards = cards;
  const myIds = Store.getMyCards();
  const myCards = cards.filter((c) => myIds.includes(c.id));

  const thumbsHtml = myCards
    .map((c) => {
      const color = BANK_COLORS[c.bank_name] || "#555";
      return `<div class="card-thumb" data-id="${c.id}" style="background:${color}">
        <span class="card-thumb-x" data-remove="${c.id}">&times;</span>
        <span class="card-thumb-bank">${c.bank_name}</span>
        <span class="card-thumb-name">${c.card_name}</span>
      </div>`;
    })
    .join("");

  return `
    <div class="mycard-section">
      <div class="mycard-title">【我的卡組合】</div>
      <div class="mycard-desc">點擊 + 新增信用卡，點擊 × 移除</div>
      <div class="mycard-thumbs" id="cardThumbs">
        ${thumbsHtml}
        <div class="card-thumb-add" id="btnAddCard">
          <span>+</span>
        </div>
      </div>
      <div class="mycard-count" id="selectedCount">已選 ${myCards.length} 張卡</div>
    </div>

    <!-- 搜尋新增 Modal -->
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

MyCardsPage.init = () => {
  const modal = document.getElementById("addCardModal");
  const searchInput = document.getElementById("cardSearchInput");
  const listEl = document.getElementById("cardSearchList");
  const thumbsEl = document.getElementById("cardThumbs");
  const countEl = document.getElementById("selectedCount");

  function refreshThumbs() {
    const myIds = Store.getMyCards();
    const myCards = _allCards.filter((c) => myIds.includes(c.id));
    const html = myCards
      .map((c) => {
        const color = BANK_COLORS[c.bank_name] || "#555";
        return `<div class="card-thumb" data-id="${c.id}" style="background:${color}">
          <span class="card-thumb-x" data-remove="${c.id}">&times;</span>
          <span class="card-thumb-bank">${c.bank_name}</span>
          <span class="card-thumb-name">${c.card_name}</span>
        </div>`;
      })
      .join("");
    thumbsEl.innerHTML =
      html + `<div class="card-thumb-add" id="btnAddCard"><span>+</span></div>`;
    countEl.textContent = `已選 ${myCards.length} 張卡`;
    // re-bindadd button
    document.getElementById("btnAddCard").addEventListener("click", openModal);
    // re-bind remove buttons
    bindRemoveButtons();
  }

  function bindRemoveButtons() {
    thumbsEl.querySelectorAll("[data-remove]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = parseInt(btn.dataset.remove, 10);
        Store.toggleCard(id);
        refreshThumbs();
      });
    });
  }

  function openModal() {
    modal.classList.add("show");
    searchInput.value = "";
    searchInput.focus();
    renderList("");
  }

  function closeModal() {
    modal.classList.remove("show");
  }

  function renderList(query) {
    const myIds = Store.getMyCards();
    const q = query.toLowerCase();
    const filtered = _allCards.filter(
      (c) =>
        !q ||
        c.bank_name.toLowerCase().includes(q) ||
        c.card_name.toLowerCase().includes(q)
    );

    // group by bank
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

  // open modal
  document.getElementById("btnAddCard").addEventListener("click", openModal);

  // close modal
  document.getElementById("modalClose").addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  // search
  searchInput.addEventListener("input", () => {
    renderList(searchInput.value.trim());
  });

  // add/remove in modal list
  listEl.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-card-id]");
    if (!btn) return;
    const id = parseInt(btn.dataset.cardId, 10);
    Store.toggleCard(id);
    renderList(searchInput.value.trim());
    refreshThumbs();
  });

  // bind remove buttons on initial load
  bindRemoveButtons();
};
