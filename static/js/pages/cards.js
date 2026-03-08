/**
 * cards.js — 卡片管理頁面：信用卡造型 + 回饋 tile 網格
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
const _rewardsCache = {};

function _buildCardHtml(c) {
  const color = BANK_COLORS[c.bank_name] || "#555";
  const feeText = c.annual_fee ? `年費 $${c.annual_fee}` : "免年費";
  return `
    <div class="cd-card" data-card-id="${c.id}">
      <div class="cd-card-visual" style="background:linear-gradient(135deg, ${color} 0%, ${color}cc 100%)">
        <div class="cd-card-visual-top">
          <span class="cd-card-visual-bank">${c.bank_name}</span>
          <span class="cd-card-remove" data-remove="${c.id}">&times;</span>
        </div>
        <div class="cd-card-visual-name">${c.card_name}</div>
        <div class="cd-card-visual-bottom">
          <span class="cd-card-visual-dots">•••• •••• •••• ••••</span>
          <span class="cd-card-visual-fee">${feeText}</span>
        </div>
      </div>
      ${c.note ? `<div class="cd-card-note">${c.note}</div>` : ""}
      <div class="cd-card-rewards" id="rewards-${c.id}">
        <div class="cd-loading">載入優惠中...</div>
      </div>
    </div>`;
}

function _renderRewardsInto(cardId, rewards) {
  const container = document.getElementById(`rewards-${cardId}`);
  if (!container) return;

  if (!rewards.length) {
    container.innerHTML = '<div class="cd-no-rewards">暫無回饋資料</div>';
    return;
  }

  // 按回饋率排序（高到低）
  const sorted = [...rewards].sort((a, b) => b.reward_rate - a.reward_rate);

  let html = '<div class="cd-rewards-section">';
  html += '<div class="cd-rewards-title">回饋比例</div>';
  html += '<div class="cd-rewards-grid">';

  sorted.forEach((r) => {
    const typeLabel = REWARD_TYPE_LABEL[r.reward_type] || r.reward_type;
    const rateClass = r.reward_rate >= 3 ? "high" : r.reward_rate >= 1.5 ? "mid" : "";
    const capHtml = r.reward_cap
      ? `<div class="cd-reward-tile-cap">上限 $${r.reward_cap}/月</div>`
      : "";
    const condHtml = r.conditions
      ? `<div class="cd-reward-tile-cond">${r.conditions}</div>`
      : "";

    html += `
      <div class="cd-reward-tile">
        <div class="cd-reward-tile-rate ${rateClass}">${r.reward_rate}%</div>
        <div class="cd-reward-tile-cat">${r.category_name}</div>
        <div class="cd-reward-tile-type">${typeLabel}</div>
        ${capHtml}${condHtml}
      </div>`;
  });

  html += '</div></div>';
  container.innerHTML = html;
}

async function _loadAndRenderRewards(cardId) {
  try {
    if (!_rewardsCache[cardId]) {
      _rewardsCache[cardId] = await API.getCardRewards(cardId);
    }
    _renderRewardsInto(cardId, _rewardsCache[cardId]);
  } catch (e) {
    const c = document.getElementById(`rewards-${cardId}`);
    if (c) c.innerHTML = '<div class="cd-no-rewards">載入失敗</div>';
  }
}

async function CardsPage() {
  const allCards = await (_allCards || API.getCards());
  _allCards = allCards;

  const myIds = Store.getMyCards();
  const myCards = allCards.filter((c) => myIds.includes(c.id));

  let cardsHtml = "";
  if (myCards.length) {
    myCards.forEach((c) => { cardsHtml += _buildCardHtml(c); });
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
      <div class="cd-card-list" id="cdCardList">${cardsHtml}</div>
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
  const cardListEl = document.getElementById("cdCardList");

  // ── 重建卡片清單（直接操作 DOM，不靠路由）──
  function refreshCardList() {
    const myIds = Store.getMyCards();
    const myCards = _allCards.filter((c) => myIds.includes(c.id));

    if (myCards.length) {
      cardListEl.innerHTML = myCards.map((c) => _buildCardHtml(c)).join("");
      myIds.forEach((id) => _loadAndRenderRewards(id));
    } else {
      cardListEl.innerHTML = `<div class="cd-empty">
        <div class="cd-empty-icon">💳</div>
        <div class="cd-empty-text">還沒有卡片</div>
        <div class="cd-empty-hint">點擊下方按鈕新增你的信用卡，查看各分類的回饋優惠</div>
      </div>`;
    }
  }

  // 初始載入回饋
  Store.getMyCards().forEach((id) => _loadAndRenderRewards(id));

  // ── 展開/收合 ──
  cardListEl.addEventListener("click", (e) => {
    const visual = e.target.closest(".cd-card-visual");
    if (!visual) return;
    if (e.target.closest(".cd-card-remove")) return;
    const card = visual.closest(".cd-card");
    card.classList.toggle("expanded");
  });

  // ── 移除卡片 ──
  cardListEl.addEventListener("click", (e) => {
    const removeBtn = e.target.closest(".cd-card-remove");
    if (!removeBtn) return;
    e.stopPropagation();
    Store.toggleCard(parseInt(removeBtn.dataset.remove, 10));
    refreshCardList();
  });

  // ── Modal 邏輯 ──
  function openModal() {
    modal.classList.add("show");
    cardSearchInput.value = "";
    cardSearchInput.focus();
    renderModalList("");
  }

  function closeModal() {
    modal.classList.remove("show");
  }

  function renderModalList(query) {
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
    renderModalList(cardSearchInput.value.trim());
  });
  listEl.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-card-id]");
    if (!btn) return;
    Store.toggleCard(parseInt(btn.dataset.cardId, 10));
    renderModalList(cardSearchInput.value.trim());
    refreshCardList();
  });
};
