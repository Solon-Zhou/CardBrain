/**
 * planner.js — CardBrain 3.0 行程規劃
 * 旅遊目的地 + 預算 → 各類別最佳卡拆解 + 總回饋
 */

async function PlannerPage() {
  return `
    <a class="back-link" href="#/">&larr; 返回首頁</a>
    <div class="planner-header">
      <span class="planner-icon">&#128506;</span>
      <h2>行程規劃</h2>
      <p class="planner-subtitle">出國旅遊，幫你規劃最佳刷卡攻略</p>
    </div>

    <!-- 自然語言輸入 -->
    <div class="planner-nl-section">
      <div class="planner-nl-wrap">
        <input class="planner-nl-input" id="planNlInput"
          type="text" placeholder="試試：日本 10萬、韓國 5萬" autocomplete="off">
        <button class="planner-nl-btn" id="planNlBtn">規劃</button>
      </div>
      <div class="planner-quick-tags">
        <span class="planner-quick-tag" data-q="日本 10萬">日本 10萬</span>
        <span class="planner-quick-tag" data-q="韓國 5萬">韓國 5萬</span>
        <span class="planner-quick-tag" data-q="泰國 3萬">泰國 3萬</span>
      </div>
    </div>

    <!-- 手動輸入 -->
    <div class="planner-manual">
      <div class="planner-manual-title">或手動輸入</div>
      <div class="planner-field">
        <label class="planner-label">目的地</label>
        <select class="planner-select" id="planDest">
          <option value="日本">日本</option>
          <option value="韓國">韓國</option>
          <option value="泰國">泰國</option>
          <option value="歐洲">歐洲</option>
          <option value="美國">美國</option>
        </select>
      </div>
      <div class="planner-field">
        <label class="planner-label">總預算</label>
        <div class="planner-budget-wrap">
          <span class="planner-dollar">$</span>
          <input class="planner-budget-input" id="planBudget"
            type="number" placeholder="100000" inputmode="numeric">
        </div>
      </div>
      <div class="planner-breakdown" id="planBreakdown">
        <div class="planner-breakdown-title">各類別金額（選填，不填則自動分配）</div>
        <div class="planner-breakdown-row">
          <label>&#9992; 機票</label>
          <input class="planner-bd-input" data-key="flights" type="number" placeholder="自動" inputmode="numeric">
        </div>
        <div class="planner-breakdown-row">
          <label>&#127976; 住宿</label>
          <input class="planner-bd-input" data-key="hotels" type="number" placeholder="自動" inputmode="numeric">
        </div>
        <div class="planner-breakdown-row">
          <label>&#128717; 購物</label>
          <input class="planner-bd-input" data-key="shopping" type="number" placeholder="自動" inputmode="numeric">
        </div>
        <div class="planner-breakdown-row">
          <label>&#127860; 餐飲</label>
          <input class="planner-bd-input" data-key="dining" type="number" placeholder="自動" inputmode="numeric">
        </div>
        <div class="planner-breakdown-row">
          <label>&#128652; 交通</label>
          <input class="planner-bd-input" data-key="transport" type="number" placeholder="自動" inputmode="numeric">
        </div>
      </div>
      <button class="planner-go-btn" id="planGoBtn">開始規劃</button>
    </div>

    <div id="plannerResult"></div>
  `;
}

PlannerPage.init = () => {
  const nlInput = document.getElementById("planNlInput");
  const nlBtn = document.getElementById("planNlBtn");
  const destSelect = document.getElementById("planDest");
  const budgetInput = document.getElementById("planBudget");
  const goBtn = document.getElementById("planGoBtn");
  const resultEl = document.getElementById("plannerResult");

  // 自然語言查詢
  async function doNlQuery() {
    const q = nlInput.value.trim();
    if (!q) return;
    resultEl.innerHTML = '<div class="spinner">規劃中...</div>';
    try {
      const data = await API.brain({ mode: "plan", query: q });
      renderPlanResult(data);
    } catch (e) {
      resultEl.innerHTML = '<div class="result-empty">規劃失敗，請重試</div>';
    }
  }

  nlBtn.addEventListener("click", doNlQuery);
  nlInput.addEventListener("keydown", (e) => { if (e.key === "Enter") doNlQuery(); });

  // 快捷標籤
  document.querySelectorAll(".planner-quick-tag").forEach((tag) => {
    tag.addEventListener("click", () => {
      nlInput.value = tag.dataset.q;
      doNlQuery();
    });
  });

  // 手動查詢
  goBtn.addEventListener("click", async () => {
    const destination = destSelect.value;
    const budget = parseFloat(budgetInput.value);
    if (!destination || !budget) return;

    // 收集各類別金額
    const breakdown = {};
    let hasBreakdown = false;
    document.querySelectorAll(".planner-bd-input").forEach((input) => {
      const val = parseFloat(input.value);
      if (val > 0) {
        breakdown[input.dataset.key] = val;
        hasBreakdown = true;
      }
    });

    resultEl.innerHTML = '<div class="spinner">規劃中...</div>';
    try {
      const payload = { mode: "plan", destination, budget };
      if (hasBreakdown) payload.breakdown = breakdown;
      const data = await API.brain(payload);
      renderPlanResult(data);
    } catch (e) {
      resultEl.innerHTML = '<div class="result-empty">規劃失敗，請重試</div>';
    }
  });

  const CATEGORY_ICONS = {
    "flights": "&#9992;",
    "hotels": "&#127976;",
    "shopping": "&#128717;",
    "dining": "&#127860;",
    "transport": "&#128652;",
  };

  function renderPlanResult(data) {
    if (data.error) {
      resultEl.innerHTML = `<div class="result-empty">${data.error}</div>`;
      return;
    }

    const { destination, total_budget, breakdown, total_savings, cards_to_bring } = data;

    let html = `
      <div class="planner-result-hero">
        <div class="planner-hero-dest">${destination} 旅遊</div>
        <div class="planner-hero-budget">預算 $${Number(total_budget).toLocaleString()}</div>
        <div class="planner-hero-savings">預估回饋 <strong>$${total_savings.toLocaleString()}</strong></div>
      </div>

      <div class="planner-breakdown-title-result">各類別最佳卡片</div>`;

    breakdown.forEach((item) => {
      const icon = CATEGORY_ICONS[item.category] || "&#128179;";
      html += `
        <div class="planner-cat-card">
          <div class="planner-cat-icon">${icon}</div>
          <div class="planner-cat-info">
            <div class="planner-cat-label">${item.category_label}</div>
            <div class="planner-cat-amount">$${item.amount.toLocaleString()}</div>
            ${item.best_card ? `<div class="planner-cat-best">${item.best_card}</div>` : ""}
            ${item.best_rate ? `<div class="planner-cat-rate">${item.best_rate}%</div>` : ""}
          </div>
          <div class="planner-cat-savings">+$${item.savings.toLocaleString()}</div>
        </div>`;
    });

    if (cards_to_bring && cards_to_bring.length) {
      html += `<div class="planner-bring-title">&#128188; 帶這些卡出門</div>`;
      cards_to_bring.forEach((c) => {
        html += `
          <div class="planner-bring-card">
            <div class="planner-bring-name">${c.card}</div>
            <div class="planner-bring-usage">${c.usage.join("、")}</div>
          </div>`;
      });
    }

    resultEl.innerHTML = html;
  }
};
