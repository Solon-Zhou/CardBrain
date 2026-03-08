/**
 * compare.js — 卡片比對頁面：選 2 張卡片逐分類比較回饋
 */

let _cmpAllCards = null;

async function ComparePage() {
  return `
    <div class="cmp-page">
      <div class="page-title">🔍 卡片比對</div>
      <div class="cmp-slots">
        <div class="cmp-slot" id="cmpSlot0">
          <span class="cmp-slot-icon">💳</span>
          <span class="cmp-slot-label">選擇卡片 A</span>
        </div>
        <div class="cmp-slot" id="cmpSlot1">
          <span class="cmp-slot-icon">💳</span>
          <span class="cmp-slot-label">選擇卡片 B</span>
        </div>
      </div>
      <div id="cmpResult">
        <div class="cmp-empty-table">請選擇兩張卡片開始比對</div>
      </div>
    </div>

    <!-- 選卡 Modal -->
    <div class="modal-overlay" id="cmpModal">
      <div class="modal-content">
        <div class="modal-header">
          <span class="modal-close" id="cmpModalClose">&times;</span>
          <span class="modal-title">選擇卡片</span>
        </div>
        <div class="modal-search">
          <input class="modal-search-input" id="cmpSearchInput"
            type="text" placeholder="搜尋銀行或卡片名稱" autocomplete="off">
          <span class="modal-search-icon">🔍</span>
        </div>
        <div class="modal-list" id="cmpCardList"></div>
      </div>
    </div>
  `;
}

ComparePage.init = () => {
  const modal = document.getElementById("cmpModal");
  const searchInput = document.getElementById("cmpSearchInput");
  const listEl = document.getElementById("cmpCardList");
  const resultEl = document.getElementById("cmpResult");

  const selected = [null, null]; // 兩個 slot 的卡片物件
  let activeSlot = 0;

  // 載入全部卡片
  async function ensureCards() {
    if (!_cmpAllCards) {
      _cmpAllCards = await API.getCards();
    }
    return _cmpAllCards;
  }

  // ── 渲染 slot 狀態 ──
  function updateSlot(index) {
    const el = document.getElementById(`cmpSlot${index}`);
    if (!el) return;
    const card = selected[index];
    if (card) {
      const color = BANK_COLORS[card.bank_name] || "#555";
      el.className = "cmp-slot filled";
      el.innerHTML = `
        <span class="cmp-slot-icon" style="color:${color}">💳</span>
        <span class="cmp-slot-name">${card.card_name}</span>
        <span class="cmp-slot-bank">${card.bank_name}</span>
      `;
    } else {
      el.className = "cmp-slot";
      el.innerHTML = `
        <span class="cmp-slot-icon">💳</span>
        <span class="cmp-slot-label">選擇卡片 ${index === 0 ? "A" : "B"}</span>
      `;
    }
  }

  // ── Modal 邏輯 ──
  function openModal(slotIndex) {
    activeSlot = slotIndex;
    modal.classList.add("show");
    searchInput.value = "";
    searchInput.focus();
    renderModalList("");
  }

  function closeModal() {
    modal.classList.remove("show");
  }

  async function renderModalList(query) {
    const cards = await ensureCards();
    const q = query.toLowerCase();
    const filtered = cards.filter(
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
        const color = BANK_COLORS[bank] || "#555";
        const isSelected =
          (selected[0] && selected[0].id === c.id) ||
          (selected[1] && selected[1].id === c.id);
        html += `
          <div class="modal-card-item">
            <div class="modal-card-icon" style="background:${color}">
              <span>${bank.substring(0, 1)}</span>
            </div>
            <div class="modal-card-info">
              <div class="modal-card-name">${c.card_name}</div>
              <div class="modal-card-bank">${bank}</div>
            </div>
            <button class="modal-card-btn ${isSelected ? "added" : ""}"
              data-card-id="${c.id}">${isSelected ? "已選" : "選擇"}</button>
          </div>`;
      });
    });

    if (!filtered.length) {
      html = '<div class="modal-empty">找不到符合的卡片</div>';
    }
    listEl.innerHTML = html;
  }

  // ── 比較邏輯 ──
  async function runCompare() {
    if (!selected[0] || !selected[1]) {
      resultEl.innerHTML = '<div class="cmp-empty-table">請選擇兩張卡片開始比對</div>';
      return;
    }
    if (selected[0].id === selected[1].id) {
      resultEl.innerHTML = '<div class="cmp-empty-table">請選擇兩張不同的卡片</div>';
      return;
    }

    resultEl.innerHTML = '<div class="spinner">比對中...</div>';

    try {
      const [rewards0, rewards1] = await Promise.all([
        API.getCardRewards(selected[0].id),
        API.getCardRewards(selected[1].id),
      ]);

      // 建立分類 → 回饋率的 map
      const map0 = {};
      rewards0.forEach((r) => {
        const key = r.category_name;
        if (!map0[key] || r.reward_rate > map0[key].rate) {
          map0[key] = { rate: r.reward_rate, type: r.reward_type };
        }
      });

      const map1 = {};
      rewards1.forEach((r) => {
        const key = r.category_name;
        if (!map1[key] || r.reward_rate > map1[key].rate) {
          map1[key] = { rate: r.reward_rate, type: r.reward_type };
        }
      });

      // 合併所有分類
      const allCats = [...new Set([...Object.keys(map0), ...Object.keys(map1)])];
      allCats.sort();

      if (!allCats.length) {
        resultEl.innerHTML = '<div class="cmp-empty-table">這兩張卡片暫無回饋資料</div>';
        return;
      }

      // 統計勝負
      let wins0 = 0, wins1 = 0;
      const rows = allCats.map((cat) => {
        const r0 = map0[cat] ? map0[cat].rate : 0;
        const r1 = map1[cat] ? map1[cat].rate : 0;
        if (r0 > r1) wins0++;
        else if (r1 > r0) wins1++;
        return { cat, r0, r1 };
      });

      const name0 = selected[0].card_name.length > 8
        ? selected[0].card_name.substring(0, 8) + "…"
        : selected[0].card_name;
      const name1 = selected[1].card_name.length > 8
        ? selected[1].card_name.substring(0, 8) + "…"
        : selected[1].card_name;

      let html = `
        <div class="cmp-table">
          <div class="cmp-table-header">
            <div>分類</div>
            <div>${name0}</div>
            <div>${name1}</div>
          </div>`;

      rows.forEach(({ cat, r0, r1 }) => {
        const class0 = r0 > r1 ? "winner" : "";
        const class1 = r1 > r0 ? "winner" : "";
        html += `
          <div class="cmp-row">
            <div>${cat}</div>
            <div><span class="cmp-rate ${class0}">${r0 ? r0 + "%" : "—"}</span></div>
            <div><span class="cmp-rate ${class1}">${r1 ? r1 + "%" : "—"}</span></div>
          </div>`;
      });

      html += `</div>`;

      // 簡短總結
      let summary = "";
      if (wins0 > wins1) {
        summary = `<b>${selected[0].card_name}</b> 在 ${wins0} 個分類勝出`;
      } else if (wins1 > wins0) {
        summary = `<b>${selected[1].card_name}</b> 在 ${wins1} 個分類勝出`;
      } else {
        summary = "兩張卡片旗鼓相當";
      }
      html += `<div style="text-align:center;padding:12px;font-size:13px;color:var(--text-light)">${summary}</div>`;

      resultEl.innerHTML = html;
    } catch (e) {
      console.error(e);
      resultEl.innerHTML = '<div class="cmp-empty-table">比對失敗，請重試</div>';
    }
  }

  // ── 事件綁定 ──
  document.getElementById("cmpSlot0").addEventListener("click", () => openModal(0));
  document.getElementById("cmpSlot1").addEventListener("click", () => openModal(1));
  document.getElementById("cmpModalClose").addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  searchInput.addEventListener("input", () => {
    renderModalList(searchInput.value.trim());
  });

  listEl.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-card-id]");
    if (!btn) return;
    const cardId = parseInt(btn.dataset.cardId, 10);
    const cards = await ensureCards();
    const card = cards.find((c) => c.id === cardId);
    if (!card) return;

    selected[activeSlot] = card;
    updateSlot(activeSlot);
    closeModal();
    runCompare();
  });
};
