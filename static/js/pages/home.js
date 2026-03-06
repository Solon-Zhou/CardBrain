/**
 * home.js — 首頁：我的卡組合 + 搜尋 + 分類（一頁式，仿 iCard.AI）
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

const BANK_COLORS = {
  "國泰世華": "#1A6B4B", "中國信託": "#C8102E", "玉山銀行": "#006B3F",
  "台新銀行": "#E31937", "永豐銀行": "#003DA5", "富邦銀行": "#00205B",
  "聯邦銀行": "#1B3F8B", "滙豐銀行": "#DB0011", "遠東商銀": "#003A70",
  "第一銀行": "#008751", "美國運通": "#006FCF", "星展銀行": "#E31837",
  "凱基銀行": "#B8860B", "新光銀行": "#FF6600", "華南銀行": "#003399",
  "兆豐銀行": "#0066B3", "渣打銀行": "#0072AA", "合作金庫": "#00843D",
  "台灣企銀": "#004B87",
};

// cache
let _categories = null;
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

async function HomePage() {
  const [categories, allCards] = await Promise.all([
    _categories || API.getCategories(),
    _allCards || API.getCards(),
  ]);
  _categories = categories;
  _allCards = allCards;

  const myIds = Store.getMyCards();
  const thumbsHtml = _buildThumbs(allCards);

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

  // sub-category sections
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
    <!-- 我的卡組合 -->
    <div class="mycard-section">
      <div class="mycard-title">【我的卡組合】</div>
      <div class="mycard-desc">點擊 + 新增信用卡，點擊 × 移除</div>
      <div class="mycard-thumbs" id="cardThumbs">
        ${thumbsHtml}
        <div class="card-thumb-add" id="btnAddCard"><span>+</span></div>
      </div>
    </div>

    <!-- 附近商家地圖（永遠顯示，未定位時顯示授權提示） -->
    <div class="nearby-section" id="nearbySection">
      <div class="nearby-title" id="nearbyTitle">📍 附近商家地圖</div>
      <div class="nearby-map-wrap">
        <div id="nearbyMap"></div>
        <div class="nearby-permission" id="nearbyPermission">
          <div class="nearby-permission-icon">📍</div>
          <div class="nearby-permission-text">開啟定位以探索附近商家的最佳刷卡推薦</div>
          <button class="nearby-permission-btn" id="btnGrantLocation">開啟定位</button>
        </div>
      </div>
    </div>

    <!-- 搜尋商家 -->
    <div class="search-wrapper">
      <span class="search-icon">🔍</span>
      <input class="search-input" id="searchInput"
        type="text" placeholder="搜尋商家（如：星巴克、全聯）" autocomplete="off">
      <div class="autocomplete-list" id="acList"></div>
    </div>

    <!-- 消費分類 -->
    <div class="section-title">📂 消費分類</div>
    <div class="cat-grid">${catGridHtml}</div>
    ${subSectionsHtml}

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

HomePage.init = () => {
  // ── 卡片管理 ──
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

  // ── 商家搜尋 ──
  const input = document.getElementById("searchInput");
  const acList = document.getElementById("acList");
  let debounceTimer = null;

  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (!q) { acList.classList.remove("show"); return; }
    debounceTimer = setTimeout(async () => {
      try {
        const results = await API.searchMerchants(q);
        if (!results.length) {
          acList.innerHTML = `<div class="autocomplete-item" data-q="${q}">搜尋「${q}」的推薦</div>`;
        } else {
          acList.innerHTML = results
            .map((m) =>
              `<div class="autocomplete-item" data-merchant="${m.name}">
                ${m.name}<span class="cat-tag">${m.category_name}</span>
              </div>`)
            .join("");
        }
        acList.classList.add("show");
      } catch { acList.classList.remove("show"); }
    }, 250);
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const q = input.value.trim();
      if (q) { acList.classList.remove("show"); location.hash = `#/result?type=merchant&q=${encodeURIComponent(q)}`; }
    }
  });

  acList.addEventListener("click", (e) => {
    const item = e.target.closest(".autocomplete-item");
    if (!item) return;
    const merchant = item.dataset.merchant || item.dataset.q;
    acList.classList.remove("show");
    input.value = merchant;
    location.hash = `#/result?type=merchant&q=${encodeURIComponent(merchant)}`;
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-wrapper")) acList.classList.remove("show");
  });

  // ── 分類 ──
  let openCatId = null;
  document.querySelectorAll(".cat-card").forEach((card) => {
    card.addEventListener("click", () => {
      const catId = card.dataset.catId;
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

  document.querySelectorAll(".subcat-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const subcatId = chip.dataset.subcatId;
      const name = chip.textContent.trim();
      location.hash = `#/result?type=category&category_id=${subcatId}&name=${encodeURIComponent(name)}`;
    });
  });

  // ── 附近商家地圖（Geofencing + Leaflet）──
  const nearbySection = document.getElementById("nearbySection");
  const permissionEl = document.getElementById("nearbyPermission");
  const mapEl = document.getElementById("nearbyMap");
  const titleEl = document.getElementById("nearbyTitle");
  let _nearbyMap = null;
  let _mapLayerGroup = null;

  const MERCHANT_EMOJIS = {
    "咖啡店": "☕", "超商": "🏪", "超市": "🛒",
    "量販店": "🏬", "速食": "🍔", "外送平台": "🛵",
    "餐廳": "🍽️", "早餐店": "🥐", "百貨公司": "🛍️",
    "加油": "⛽", "大眾運輸": "🚇", "高鐵": "🚄",
    "網購": "📦", "影音串流": "🎬", "訂房網站": "🏨",
    "藥妝": "💊", "寵物用品": "🐾",
  };

  function _getEmoji(categoryName) {
    return MERCHANT_EMOJIS[categoryName] || "📍";
  }

  function _showPermissionPrompt() {
    permissionEl.style.display = "";
    mapEl.style.display = "none";
    titleEl.textContent = "📍 附近商家地圖";
  }

  function _hidePermissionPrompt() {
    permissionEl.style.display = "none";
    mapEl.style.display = "";
  }

  function renderNearby(data) {
    const { userLat, userLng, nearby } = data;

    _hidePermissionPrompt();
    titleEl.textContent = nearby.length
      ? `📍 偵測到 ${nearby.length} 間附近商家`
      : "📍 你的位置（附近暫無合作商家）";

    // 初始化或重置地圖
    if (!_nearbyMap) {
      _nearbyMap = L.map("nearbyMap", {
        zoomControl: false,
        attributionControl: false,
      }).setView([userLat, userLng], 16);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
      }).addTo(_nearbyMap);
      L.control.attribution({ prefix: false, position: "bottomright" })
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>')
        .addTo(_nearbyMap);
      _mapLayerGroup = L.layerGroup().addTo(_nearbyMap);
    } else {
      _mapLayerGroup.clearLayers();
    }

    // 使用者位置 — 藍色圓形
    const userMarker = L.circleMarker([userLat, userLng], {
      radius: 10,
      fillColor: "#4A90D9",
      fillOpacity: 0.9,
      color: "#fff",
      weight: 3,
    }).bindPopup('<div class="nearby-popup"><b>你在這裡</b></div>');
    _mapLayerGroup.addLayer(userMarker);

    const bounds = L.latLngBounds([[userLat, userLng]]);

    // 商家標記
    nearby.forEach((item) => {
      if (!item.lat || !item.lng) return;
      const emoji = _getEmoji(item.category_name);
      const icon = L.divIcon({
        className: "nearby-emoji-marker",
        html: `<span>${emoji}</span>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      });

      const card = item.top_card;
      const rateUnit = card.reward_type === "miles" ? " 元/哩" :
        card.reward_type === "points" ? "% 點" : "% 回饋";
      const popupHtml = `<div class="nearby-popup">
        <div class="nearby-popup-name">${item.merchant_name}</div>
        <div class="nearby-popup-cat">${item.category_name} · ${item.distance_m}m</div>
        <div class="nearby-popup-rate">${card.reward_rate}${rateUnit}</div>
        <div class="nearby-popup-card">${card.bank_name} ${card.card_name}</div>
        <a class="nearby-popup-link" href="#/result?type=merchant&q=${encodeURIComponent(item.merchant_name)}">查看推薦 →</a>
      </div>`;

      const marker = L.marker([item.lat, item.lng], { icon })
        .bindPopup(popupHtml);
      _mapLayerGroup.addLayer(marker);
      bounds.extend([item.lat, item.lng]);
    });

    // 自動 fit bounds
    if (nearby.length) {
      _nearbyMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 17 });
    } else {
      _nearbyMap.setView([userLat, userLng], 16);
    }

    setTimeout(() => _nearbyMap.invalidateSize(), 100);

    // 推播通知（只通知第一個）
    if (nearby.length && typeof Notify !== "undefined") {
      Notify.requestPermission().then(() => {
        Notify.notifyNearby(nearby[0]);
      });
    }
  }

  function _startGeo() {
    if (typeof Geo !== "undefined") {
      Geo.startWatching(renderNearby);
    }
  }

  // 檢查定位權限狀態，決定顯示地圖或授權提示
  if (!("geolocation" in navigator)) {
    // 瀏覽器不支援定位
    permissionEl.querySelector(".nearby-permission-text").textContent = "您的瀏覽器不支援定位功能";
    permissionEl.querySelector(".nearby-permission-btn").style.display = "none";
    _showPermissionPrompt();
  } else if (navigator.permissions && navigator.permissions.query) {
    navigator.permissions.query({ name: "geolocation" }).then((result) => {
      if (result.state === "granted") {
        _hidePermissionPrompt();
        _startGeo();
      } else {
        // prompt 或 denied — 先顯示授權提示
        _showPermissionPrompt();
        if (result.state === "denied") {
          permissionEl.querySelector(".nearby-permission-text").textContent = "定位權限已被封鎖，請至瀏覽器設定中開啟";
          permissionEl.querySelector(".nearby-permission-btn").textContent = "重新整理";
          document.getElementById("btnGrantLocation").addEventListener("click", () => location.reload());
        }
      }
    });
  } else {
    // 無法查詢權限（Safari 等），直接顯示授權按鈕
    _showPermissionPrompt();
  }

  // 「開啟定位」按鈕
  document.getElementById("btnGrantLocation").addEventListener("click", () => {
    titleEl.textContent = "📍 定位中...";
    _startGeo();
  });
};
