/**
 * result.js — 結果頁：推薦排序列表 + 回饋計算機
 */

const BADGE_CLASS = {
  cashback: "badge-cashback",
  points: "badge-points",
  miles: "badge-miles",
};
const BADGE_LABEL = {
  cashback: "現金回饋",
  points: "點數",
  miles: "哩程",
};
const REWARD_UNIT = {
  cashback: "元",
  points: "點",
  miles: "哩",
};

function _renderCard(r, rank, isTop) {
  const badgeCls = BADGE_CLASS[r.reward_type] || "badge-cashback";
  const badgeLbl = BADGE_LABEL[r.reward_type] || r.reward_type;
  const capStr = r.reward_cap ? `上限 $${r.reward_cap}/月` : "無上限";
  const condStr = r.conditions ? r.conditions : "";
  const unit = REWARD_UNIT[r.reward_type] || "元";

  return `
    <div class="result-card ${isTop ? "top" : ""}" data-rate="${r.reward_rate}" data-cap="${r.reward_cap || ""}" data-type="${r.reward_type}">
      <span class="result-rank">${rank}</span>
      <div class="result-bank">${r.bank_name}</div>
      <div class="result-name">${r.card_name}</div>
      <div class="result-rate">${r.reward_rate}%
        <span class="result-rate-unit">${badgeLbl}</span>
      </div>
      <div class="result-calc" style="display:none">
        <span class="calc-arrow">→</span>
        <span class="calc-value">0</span>
        <span class="calc-unit">${unit}</span>
        <span class="calc-cap-warn"></span>
      </div>
      <div class="result-meta">
        <span class="result-badge ${badgeCls}">${badgeLbl}</span>
        ${capStr}${condStr ? " · " + condStr : ""}
      </div>
      ${r.category_name ? `<div class="result-meta">分類：${r.category_name}</div>` : ""}
    </div>`;
}

function _dedup(results) {
  const seen = new Set();
  return results.filter((r) => {
    const key = `${r.card_id}-${r.category_name}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

async function ResultPage(params) {
  const { type, q, category_id, name } = params;
  const myIds = Store.getMyCards();

  let results = [];
  let title = "";

  if (type === "merchant" && q) {
    title = `「${q}」推薦卡片`;
    results = await API.recommendByMerchant(q, myIds);
  } else if (type === "category" && category_id) {
    title = `「${name || "分類"}」推薦卡片`;
    results = await API.recommendByCategory(category_id, myIds);
  }

  results = _dedup(results);

  if (!results.length) {
    return `
      <a class="back-link" href="#/">← 返回首頁</a>
      <div class="result-header">${title}</div>
      <div class="result-empty">找不到推薦結果，試試其他關鍵字或分類</div>`;
  }

  let mySection = "";
  let otherSection = "";

  if (myIds.length) {
    let allResults = [];
    if (type === "merchant" && q) {
      allResults = await API.recommendByMerchant(q, []);
    } else if (type === "category" && category_id) {
      allResults = await API.recommendByCategory(category_id, []);
    }
    allResults = _dedup(allResults);

    const myResults = results;
    const otherResults = allResults.filter(
      (r) => !myIds.includes(r.card_id)
    );

    if (myResults.length) {
      mySection = `<div class="result-section-title">💳 我有的卡</div>`;
      mySection += myResults
        .map((r, i) => _renderCard(r, i + 1, i === 0))
        .join("");
    }

    if (otherResults.length) {
      otherSection = `<div class="result-section-title">🔍 其他推薦</div>`;
      otherSection += otherResults
        .slice(0, 10)
        .map((r, i) => _renderCard(r, i + 1, false))
        .join("");
    }
  } else {
    mySection = results
      .map((r, i) => _renderCard(r, i + 1, i === 0))
      .join("");
  }

  return `
    <a class="back-link" href="#/">← 返回首頁</a>
    <div class="result-header">${title}</div>

    <div class="calc-bar">
      <label class="calc-label">🧮 消費金額</label>
      <div class="calc-input-wrap">
        <span class="calc-dollar">$</span>
        <input class="calc-input" id="calcInput" type="number" inputmode="numeric" placeholder="輸入金額，即時試算回饋" min="0">
      </div>
    </div>

    ${mySection}
    ${otherSection}`;
}

ResultPage.init = () => {
  const input = document.getElementById("calcInput");
  if (!input) return;

  input.addEventListener("input", () => {
    const amount = parseFloat(input.value) || 0;
    document.querySelectorAll(".result-card").forEach((card) => {
      const rate = parseFloat(card.dataset.rate) || 0;
      const cap = parseFloat(card.dataset.cap) || 0;
      const type = card.dataset.type;
      const calcEl = card.querySelector(".result-calc");
      const valEl = card.querySelector(".calc-value");
      const warnEl = card.querySelector(".calc-cap-warn");

      if (amount > 0) {
        let reward = Math.round(amount * rate) / 100;
        let hitCap = false;
        if (cap > 0 && reward > cap) {
          reward = cap;
          hitCap = true;
        }
        // points/miles show as integer
        const display = type === "cashback"
          ? reward.toFixed(1)
          : Math.round(reward);
        valEl.textContent = display;
        warnEl.textContent = hitCap ? "（已達上限）" : "";
        calcEl.style.display = "flex";
      } else {
        calcEl.style.display = "none";
      }
    });
  });
};
