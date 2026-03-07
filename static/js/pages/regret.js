/**
 * regret.js — CardBrain 3.0 後悔計算機
 * 多筆交易比較「你用的卡 vs 最佳卡」，算出總後悔金額
 */

let _regretCards = null;

async function RegretPage() {
  const allCards = _regretCards || await API.getCards();
  _regretCards = allCards;

  const myIds = Store.getMyCards();
  const myCards = allCards.filter((c) => myIds.includes(c.id));

  const cardOptionsHtml = myCards.length
    ? myCards.map((c) => `<option value="${c.id}">${c.bank_name} ${c.card_name}</option>`).join("")
    : allCards.map((c) => `<option value="${c.id}">${c.bank_name} ${c.card_name}</option>`).join("");

  return `
    <a class="back-link" href="#/">&larr; 返回首頁</a>
    <div class="regret-header">
      <span class="regret-icon">&#128561;</span>
      <h2>後悔計算機</h2>
      <p class="regret-subtitle">看看你少賺了多少回饋金</p>
    </div>

    <div class="regret-form" id="regretForm">
      <div class="regret-row" data-row="0">
        <input class="regret-merchant" placeholder="商家" autocomplete="off">
        <div class="regret-amount-wrap">
          <span class="regret-dollar">$</span>
          <input class="regret-amount" type="number" placeholder="金額" inputmode="numeric">
        </div>
        <select class="regret-card-select">${cardOptionsHtml}</select>
      </div>
    </div>

    <div class="regret-actions">
      <button class="regret-add-btn" id="addRowBtn">+ 新增一筆</button>
      <button class="regret-calc-btn" id="calcBtn">開始計算</button>
    </div>

    <div id="regretResult"></div>
  `;
}

RegretPage.init = () => {
  const form = document.getElementById("regretForm");
  const addBtn = document.getElementById("addRowBtn");
  const calcBtn = document.getElementById("calcBtn");
  const resultEl = document.getElementById("regretResult");
  let rowCount = 1;

  // 取得卡片選項 HTML（從第一列複製）
  const firstSelect = form.querySelector(".regret-card-select");
  const optionsHtml = firstSelect ? firstSelect.innerHTML : "";

  addBtn.addEventListener("click", () => {
    const row = document.createElement("div");
    row.className = "regret-row";
    row.dataset.row = rowCount++;
    row.innerHTML = `
      <input class="regret-merchant" placeholder="商家" autocomplete="off">
      <div class="regret-amount-wrap">
        <span class="regret-dollar">$</span>
        <input class="regret-amount" type="number" placeholder="金額" inputmode="numeric">
      </div>
      <select class="regret-card-select">${optionsHtml}</select>
      <span class="regret-remove-btn">&times;</span>
    `;
    form.appendChild(row);
    row.querySelector(".regret-remove-btn").addEventListener("click", () => row.remove());
  });

  calcBtn.addEventListener("click", async () => {
    const rows = form.querySelectorAll(".regret-row");
    const transactions = [];
    rows.forEach((row) => {
      const merchant = row.querySelector(".regret-merchant").value.trim();
      const amount = parseFloat(row.querySelector(".regret-amount").value);
      const cardId = parseInt(row.querySelector(".regret-card-select").value, 10);
      if (merchant && amount && cardId) {
        transactions.push({ merchant, amount, card_id: cardId });
      }
    });

    if (!transactions.length) return;

    resultEl.innerHTML = '<div class="spinner">精算中...</div>';
    try {
      const data = await API.brain({ mode: "regret", transactions });
      renderRegretResult(data);
    } catch (e) {
      resultEl.innerHTML = '<div class="result-empty">計算失敗，請重試</div>';
    }
  });

  function renderRegretResult(data) {
    if (data.error) {
      resultEl.innerHTML = `<div class="result-empty">${data.error}</div>`;
      return;
    }

    const { details, total_your_reward, total_best_reward, total_regret } = data;

    let html = `
      <div class="regret-summary">
        <div class="regret-summary-title">計算結果</div>
        <div class="regret-summary-grid">
          <div class="regret-summary-item">
            <div class="regret-summary-label">你實際獲得</div>
            <div class="regret-summary-value green">$${total_your_reward.toLocaleString()}</div>
          </div>
          <div class="regret-summary-item">
            <div class="regret-summary-label">最佳組合可得</div>
            <div class="regret-summary-value green">$${total_best_reward.toLocaleString()}</div>
          </div>
        </div>
        <div class="regret-total">
          <div class="regret-total-label">你少賺了</div>
          <div class="regret-total-value ${total_regret > 0 ? "red" : "green"}">$${total_regret.toLocaleString()}</div>
        </div>
      </div>

      <div class="regret-details-title">逐筆明細</div>`;

    details.forEach((d) => {
      const hasRegret = d.regret > 0;
      html += `
        <div class="regret-detail-card ${hasRegret ? "has-regret" : ""}">
          <div class="regret-detail-header">
            <span class="regret-detail-merchant">${d.merchant}</span>
            <span class="regret-detail-amount">$${d.amount.toLocaleString()}</span>
          </div>
          <div class="regret-detail-compare">
            <div class="regret-detail-your">
              <div class="regret-detail-label">你用的</div>
              <div class="regret-detail-card-name">${d.your_card || "未知卡片"}</div>
              <div class="regret-detail-reward">$${d.your_reward}</div>
            </div>
            <div class="regret-detail-vs">VS</div>
            <div class="regret-detail-best">
              <div class="regret-detail-label">最佳</div>
              <div class="regret-detail-card-name">${d.best_card || "-"}</div>
              <div class="regret-detail-reward accent">$${d.best_reward}</div>
            </div>
          </div>
          ${hasRegret ? `<div class="regret-detail-diff">少賺 $${d.regret}</div>` : '<div class="regret-detail-ok">&#10003; 最佳選擇</div>'}
        </div>`;
    });

    resultEl.innerHTML = html;
  }
};
