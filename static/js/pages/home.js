/**
 * home.js — 首頁：搜尋 + 分類入口 + 我的卡片列
 */

const CAT_EMOJIS = {
  "常用消費": "🛒",
  "繳費與保險": "🧾",
  "百貨購物": "🛍️",
  "餐飲外送": "🍽️",
  "通勤交通": "🚗",
  "娛樂休閒": "🎮",
  "旅遊住宿": "✈️",
  "其他": "📦",
};

// cache
let _categories = null;
let _allCards = null;

async function HomePage() {
  // load data in parallel
  const [categories, allCards] = await Promise.all([
    _categories || API.getCategories(),
    _allCards || API.getCards(),
  ]);
  _categories = categories;
  _allCards = allCards;

  const myIds = Store.getMyCards();
  const myCards = allCards.filter((c) => myIds.includes(c.id));

  // chips
  const chipsHtml = myCards.length
    ? myCards.map((c) => `<span class="chip">${c.bank_name} ${c.card_name}</span>`).join("")
    : '<span class="chip-empty">尚未選擇卡片，點「我的卡」新增</span>';

  // category grid
  const catGridHtml = categories
    .map(
      (cat) =>
        `<div class="cat-card" data-cat-id="${cat.id}">
          <span class="cat-emoji">${CAT_EMOJIS[cat.name] || "📁"}</span>
          <span class="cat-name">${cat.name}</span>
        </div>`
    )
    .join("");

  // sub-category sections (hidden by default)
  const subSectionsHtml = categories
    .map(
      (cat) =>
        `<div class="subcat-list" id="subcat-${cat.id}">
          ${cat.children
            .map(
              (sub) =>
                `<span class="subcat-chip" data-subcat-id="${sub.id}">${sub.name}</span>`
            )
            .join("")}
        </div>`
    )
    .join("");

  return `
    <div class="search-wrapper">
      <span class="search-icon">🔍</span>
      <input class="search-input" id="searchInput"
        type="text" placeholder="搜尋商家（如：星巴克、全聯）" autocomplete="off">
      <div class="autocomplete-list" id="acList"></div>
    </div>

    <div class="section-title">💳 我的卡片 (${myCards.length})</div>
    <div class="chip-scroll">${chipsHtml}</div>

    <div class="section-title">📂 消費分類</div>
    <div class="cat-grid">${catGridHtml}</div>
    ${subSectionsHtml}
  `;
}

HomePage.init = () => {
  const input = document.getElementById("searchInput");
  const acList = document.getElementById("acList");
  let debounceTimer = null;

  // search autocomplete
  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (!q) {
      acList.classList.remove("show");
      return;
    }
    debounceTimer = setTimeout(async () => {
      try {
        const results = await API.searchMerchants(q);
        if (!results.length) {
          acList.innerHTML = `<div class="autocomplete-item" data-q="${q}">搜尋「${q}」的推薦</div>`;
        } else {
          acList.innerHTML = results
            .map(
              (m) =>
                `<div class="autocomplete-item" data-merchant="${m.name}">
                  ${m.name}<span class="cat-tag">${m.category_name}</span>
                </div>`
            )
            .join("");
        }
        acList.classList.add("show");
      } catch {
        acList.classList.remove("show");
      }
    }, 250);
  });

  // enter key
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const q = input.value.trim();
      if (q) {
        acList.classList.remove("show");
        location.hash = `#/result?type=merchant&q=${encodeURIComponent(q)}`;
      }
    }
  });

  // click autocomplete item
  acList.addEventListener("click", (e) => {
    const item = e.target.closest(".autocomplete-item");
    if (!item) return;
    const merchant = item.dataset.merchant || item.dataset.q;
    acList.classList.remove("show");
    input.value = merchant;
    location.hash = `#/result?type=merchant&q=${encodeURIComponent(merchant)}`;
  });

  // close autocomplete on outside click
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-wrapper")) {
      acList.classList.remove("show");
    }
  });

  // category grid click — toggle sub-categories
  let openCatId = null;
  document.querySelectorAll(".cat-card").forEach((card) => {
    card.addEventListener("click", () => {
      const catId = card.dataset.catId;
      // close previous
      if (openCatId && openCatId !== catId) {
        const prev = document.getElementById(`subcat-${openCatId}`);
        if (prev) prev.classList.remove("show");
      }
      const subList = document.getElementById(`subcat-${catId}`);
      if (subList) {
        subList.classList.toggle("show");
        openCatId = subList.classList.contains("show") ? catId : null;
      }
    });
  });

  // sub-category click → result page
  document.querySelectorAll(".subcat-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const subcatId = chip.dataset.subcatId;
      const name = chip.textContent.trim();
      location.hash = `#/result?type=category&category_id=${subcatId}&name=${encodeURIComponent(name)}`;
    });
  });
};
