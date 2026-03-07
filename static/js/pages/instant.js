/**
 * instant.js — CardBrain 3.0 即時推薦頁
 * 輸入商家 + 金額 → 顯示按實際回饋金額排序的最佳卡片
 */

async function InstantPage() {
  return `
    <a class="back-link" href="#/">&larr; 返回首頁</a>
    <div class="instant-header">
      <span class="instant-icon">&#9889;</span>
      <h2>即時推薦</h2>
      <p class="instant-subtitle">輸入消費資訊，算出真實回饋金額</p>
    </div>

    <!-- 自然語言輸入 -->
    <div class="instant-nl-section">
      <div class="instant-nl-wrap">
        <input class="instant-nl-input" id="nlInput"
          type="text" placeholder="試試：星巴克 300、全聯 2000" autocomplete="off">
        <button class="instant-nl-btn" id="nlBtn">查詢</button>
      </div>
      <div class="instant-quick-tags">
        <span class="instant-quick-tag" data-q="全聯 2000">全聯 2000</span>
        <span class="instant-quick-tag" data-q="星巴克 300">星巴克 300</span>
        <span class="instant-quick-tag" data-q="momo 5000">momo 5000</span>
        <span class="instant-quick-tag" data-q="中油 1500">中油 1500</span>
      </div>
    </div>

    <!-- 手動輸入 -->
    <div class="instant-manual">
      <div class="instant-manual-title">或手動輸入</div>
      <div class="instant-manual-row">
        <input class="instant-merchant-input" id="merchantInput"
          type="text" placeholder="商家名稱" autocomplete="off">
        <div class="instant-amount-wrap">
          <span class="instant-dollar">$</span>
          <input class="instant-amount-input" id="amountInput"
            type="number" placeholder="金額" inputmode="numeric">
        </div>
        <button class="instant-go-btn" id="manualBtn">GO</button>
      </div>
    </div>

    <!-- 結果區 -->
    <div id="instantResult"></div>
  `;
}

InstantPage.init = () => {
  const nlInput = document.getElementById("nlInput");
  const nlBtn = document.getElementById("nlBtn");
  const merchantInput = document.getElementById("merchantInput");
  const amountInput = document.getElementById("amountInput");
  const manualBtn = document.getElementById("manualBtn");
  const resultEl = document.getElementById("instantResult");

  // 自然語言查詢
  async function doNlQuery() {
    const q = nlInput.value.trim();
    if (!q) return;
    resultEl.innerHTML = '<div class="spinner">精算中...</div>';
    try {
      const data = await API.brain({ mode: "instant", query: q });
      renderInstantResult(data);
    } catch (e) {
      resultEl.innerHTML = '<div class="result-empty">查詢失敗，請重試</div>';
    }
  }

  nlBtn.addEventListener("click", doNlQuery);
  nlInput.addEventListener("keydown", (e) => { if (e.key === "Enter") doNlQuery(); });

  // 快捷標籤
  document.querySelectorAll(".instant-quick-tag").forEach((tag) => {
    tag.addEventListener("click", () => {
      nlInput.value = tag.dataset.q;
      doNlQuery();
    });
  });

  // 手動查詢
  async function doManualQuery() {
    const merchant = merchantInput.value.trim();
    const amount = parseFloat(amountInput.value);
    if (!merchant || !amount) return;
    resultEl.innerHTML = '<div class="spinner">精算中...</div>';
    try {
      const data = await API.brain({ mode: "instant", merchant, amount });
      renderInstantResult(data);
    } catch (e) {
      resultEl.innerHTML = '<div class="result-empty">查詢失敗，請重試</div>';
    }
  }

  manualBtn.addEventListener("click", doManualQuery);
  amountInput.addEventListener("keydown", (e) => { if (e.key === "Enter") doManualQuery(); });

  function renderInstantResult(data) {
    if (data.error) {
      resultEl.innerHTML = `<div class="result-empty">${data.error}</div>`;
      return;
    }
    const results = data.results || [];
    if (!results.length) {
      resultEl.innerHTML = '<div class="result-empty">找不到推薦結果</div>';
      return;
    }

    const best = results[0];
    const rest = results.slice(1);
    const myIds = Store.getMyCards();

    let html = `
      <div class="instant-result-summary">
        在 <strong>${data.merchant || "此商家"}</strong> 消費 <strong>$${Number(data.amount).toLocaleString()}</strong>
      </div>
      <div class="instant-best-card">
        <div class="instant-best-label">最佳選擇</div>
        <div class="instant-best-reward">$${best.actual_reward.toLocaleString()}</div>
        <div class="instant-best-rate">${best.reward_rate}% ${_rewardTypeLabel(best.reward_type)}</div>
        <div class="instant-best-name">${best.bank_name} ${best.card_name}</div>
        ${best.reward_cap ? `<div class="instant-best-cap">月上限 $${best.reward_cap.toLocaleString()}</div>` : ""}
        ${best.conditions ? `<div class="instant-best-cond">${best.conditions}</div>` : ""}
        ${myIds.includes(best.card_id) ? '<div class="instant-best-mine">&#10003; 我的卡片</div>' : ""}
      </div>`;

    if (rest.length) {
      html += '<div class="instant-others-title">其他選項</div>';
      rest.forEach((r, i) => {
        const isMine = myIds.includes(r.card_id);
        html += `
          <div class="instant-other-card ${isMine ? "mine" : ""}">
            <div class="instant-other-rank">${i + 2}</div>
            <div class="instant-other-info">
              <div class="instant-other-name">${r.bank_name} ${r.card_name}</div>
              <div class="instant-other-meta">${r.reward_rate}% ${_rewardTypeLabel(r.reward_type)}${r.conditions ? " · " + r.conditions : ""}</div>
            </div>
            <div class="instant-other-reward">$${r.actual_reward.toLocaleString()}</div>
          </div>`;
      });
    }

    resultEl.innerHTML = html;
  }

  function _rewardTypeLabel(type) {
    return type === "miles" ? "哩程" : type === "points" ? "點數" : "回饋";
  }
};
