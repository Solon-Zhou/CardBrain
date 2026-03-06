/**
 * result.js — 結果頁：推薦排序列表
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

function _renderCard(r, rank, isTop) {
  const badgeCls = BADGE_CLASS[r.reward_type] || "badge-cashback";
  const badgeLbl = BADGE_LABEL[r.reward_type] || r.reward_type;
  const capStr = r.reward_cap ? `上限 $${r.reward_cap}/月` : "無上限";
  const condStr = r.conditions ? r.conditions : "";

  return `
    <div class="result-card ${isTop ? "top" : ""}">
      <span class="result-rank">${rank}</span>
      <div class="result-bank">${r.bank_name}</div>
      <div class="result-name">${r.card_name}</div>
      <div class="result-rate">${r.reward_rate}%
        <span class="result-rate-unit">${badgeLbl}</span>
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

  // If user has selected cards, split into "my cards" vs "others"
  // We need the full unfiltered list for "others" section
  let mySection = "";
  let otherSection = "";

  if (myIds.length) {
    // results currently only contains user's cards (API filtered)
    // fetch all cards for "other" section
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
    // no cards selected — show all
    mySection = results
      .map((r, i) => _renderCard(r, i + 1, i === 0))
      .join("");
  }

  return `
    <a class="back-link" href="#/">← 返回首頁</a>
    <div class="result-header">${title}</div>
    ${mySection}
    ${otherSection}`;
}

ResultPage.init = () => {};
