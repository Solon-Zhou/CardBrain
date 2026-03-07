/**
 * home.js — 首頁：我的卡組合 + Agent 聊天 + 附近商家地圖
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

// cache
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
  const allCards = await (_allCards || API.getCards());
  _allCards = allCards;

  const thumbsHtml = _buildThumbs(allCards);

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

    <!-- Agent 聊天區 -->
    <div class="agent-section">
      <div class="agent-messages" id="agentMessages">
        <div class="agent-bubble bot">
          <div class="agent-avatar">🧠</div>
          <div class="agent-text">嗨！我是 CardBrain Agent，告訴我你的消費情境，我幫你找最划算的卡。<br><br>試試看：「星巴克 300」、「全聯 2000」、「日本旅遊 10萬」</div>
        </div>
      </div>
      <div class="agent-quick-tags" id="agentQuickTags">
        <span class="agent-tag" data-msg="星巴克 300">☕ 星巴克 300</span>
        <span class="agent-tag" data-msg="全聯 2000">🛒 全聯 2000</span>
        <span class="agent-tag" data-msg="日本旅遊 10萬">✈️ 日本 10萬</span>
        <span class="agent-tag" data-msg="加油 1500">⛽ 加油 1500</span>
      </div>
      <div class="agent-input-bar">
        <input class="agent-input" id="agentInput"
          type="text" placeholder="輸入消費情境，例如「星巴克 300」" autocomplete="off">
        <button class="agent-send-btn" id="agentSendBtn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    </div>

    <!-- 附近商家地圖 -->
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

  // ── Agent 聊天 ──
  const messagesEl = document.getElementById("agentMessages");
  const agentInput = document.getElementById("agentInput");
  const sendBtn = document.getElementById("agentSendBtn");
  const quickTags = document.getElementById("agentQuickTags");
  let _sending = false;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function addBubble(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `agent-bubble ${role}`;
    if (role === "bot") {
      bubble.innerHTML = `<div class="agent-avatar">🧠</div><div class="agent-text">${text}</div>`;
    } else {
      bubble.innerHTML = `<div class="agent-text">${escapeHtml(text)}</div>`;
    }
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
  }

  function addTyping() {
    const bubble = document.createElement("div");
    bubble.className = "agent-bubble bot";
    bubble.id = "agentTyping";
    bubble.innerHTML = `<div class="agent-avatar">🧠</div><div class="agent-text agent-typing"><span></span><span></span><span></span></div>`;
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById("agentTyping");
    if (el) el.remove();
  }

  function formatReply(text) {
    return escapeHtml(text).replace(/\n/g, "<br>");
  }

  async function sendMessage(text) {
    if (_sending || !text.trim()) return;
    _sending = true;
    agentInput.value = "";
    sendBtn.disabled = true;

    // 隱藏快捷標籤
    quickTags.style.display = "none";

    addBubble("user", text);
    addTyping();

    try {
      const res = await API.agent(text);
      removeTyping();
      const replyHtml = formatReply(res.reply || "抱歉，我無法理解你的問題。");

      // 若有結構化數據，附加精算卡片
      let extraHtml = "";
      if (res.data && !res.data.error) {
        extraHtml = _buildDataCard(res.mode, res.data);
      }

      addBubble("bot", replyHtml + extraHtml);
    } catch (err) {
      removeTyping();
      addBubble("bot", "抱歉，發生了一點問題，請稍後再試。");
    }

    _sending = false;
    sendBtn.disabled = false;
    agentInput.focus();
  }

  agentInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.isComposing) {
      e.preventDefault();
      sendMessage(agentInput.value);
    }
  });
  sendBtn.addEventListener("click", () => sendMessage(agentInput.value));
  quickTags.addEventListener("click", (e) => {
    const tag = e.target.closest(".agent-tag");
    if (tag) sendMessage(tag.dataset.msg);
  });

  // ── 附近商家地圖（Geofencing + Leaflet）──
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
    const { userLat, userLng, nearby, accuracy } = data;

    _hidePermissionPrompt();
    const accText = accuracy ? `（精度 ~${Math.round(accuracy)}m）` : "";
    titleEl.textContent = nearby.length
      ? `📍 偵測到 ${nearby.length} 間附近商家`
      : `📍 你的位置${accText}（附近暫無合作商家）`;

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

    if (accuracy) {
      const accCircle = L.circle([userLat, userLng], {
        radius: accuracy,
        fillColor: "#4A90D9",
        fillOpacity: 0.1,
        color: "#4A90D9",
        weight: 1,
      });
      _mapLayerGroup.addLayer(accCircle);
    }
    const userMarker = L.circleMarker([userLat, userLng], {
      radius: 10,
      fillColor: "#4A90D9",
      fillOpacity: 0.9,
      color: "#fff",
      weight: 3,
    }).bindPopup(`<div class="nearby-popup"><b>你在這裡</b>${accuracy ? `<br><span style="font-size:11px;color:#636E72">精度 ~${Math.round(accuracy)}m</span>` : ""}</div>`);
    _mapLayerGroup.addLayer(userMarker);

    const bounds = L.latLngBounds([[userLat, userLng]]);

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

    if (nearby.length) {
      _nearbyMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 17 });
    } else {
      _nearbyMap.setView([userLat, userLng], 16);
    }

    setTimeout(() => _nearbyMap.invalidateSize(), 100);

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

  if (!("geolocation" in navigator)) {
    permissionEl.querySelector(".nearby-permission-text").textContent = "您的瀏覽器不支援定位功能";
    permissionEl.querySelector(".nearby-permission-btn").style.display = "none";
    _showPermissionPrompt();
  } else if (navigator.permissions && navigator.permissions.query) {
    navigator.permissions.query({ name: "geolocation" }).then((result) => {
      if (result.state === "granted") {
        _hidePermissionPrompt();
        _startGeo();
      } else {
        _showPermissionPrompt();
        if (result.state === "denied") {
          permissionEl.querySelector(".nearby-permission-text").textContent = "定位權限已被封鎖，請至瀏覽器設定中開啟";
          permissionEl.querySelector(".nearby-permission-btn").textContent = "重新整理";
          document.getElementById("btnGrantLocation").addEventListener("click", () => location.reload());
        }
      }
    });
  } else {
    _showPermissionPrompt();
  }

  document.getElementById("btnGrantLocation").addEventListener("click", () => {
    titleEl.textContent = "📍 定位中...";
    _startGeo();
  });
};

// ── 精算結果卡片渲染 ──
function _buildDataCard(mode, data) {
  if (mode === "instant") return _buildInstantCard(data);
  if (mode === "plan") return _buildPlanCard(data);
  if (mode === "regret") return _buildRegretCard(data);
  return "";
}

function _buildInstantCard(data) {
  const results = data.results || [];
  if (!results.length) return "";
  const best = results[0];
  const rtype = best.reward_type || "cashback";
  const unit = rtype === "cashback" ? "回饋" : (rtype === "miles" ? "哩程" : "點");

  let html = `<div class="agent-data-card">`;
  html += `<div class="agent-data-best">
    <div class="agent-data-best-label">最佳推薦</div>
    <div class="agent-data-best-name">${best.bank_name} ${best.card_name}</div>
    <div class="agent-data-best-reward">$${(best.actual_reward || 0).toFixed(1)} <small>${unit}</small></div>
    <div class="agent-data-best-rate">${best.reward_rate}%</div>
  </div>`;

  if (results.length > 1) {
    html += `<div class="agent-data-others">`;
    results.slice(1, 4).forEach((r, i) => {
      html += `<div class="agent-data-other">
        <span class="agent-data-rank">#${i + 2}</span>
        <span class="agent-data-other-name">${r.bank_name} ${r.card_name}</span>
        <span class="agent-data-other-reward">$${(r.actual_reward || 0).toFixed(1)}</span>
      </div>`;
    });
    html += `</div>`;
  }
  html += `</div>`;
  return html;
}

function _buildPlanCard(data) {
  const cards = data.cards_to_bring || [];
  const savings = data.total_savings || 0;
  let html = `<div class="agent-data-card">`;
  html += `<div class="agent-data-plan-hero">
    <span>預估省下</span>
    <strong>$${savings.toFixed(0)}</strong>
  </div>`;
  if (cards.length) {
    html += `<div class="agent-data-bring">帶卡清單：`;
    cards.forEach((c) => {
      const usage = (c.usage || []).join("、");
      html += `<div class="agent-data-bring-item">${c.card} → ${usage}</div>`;
    });
    html += `</div>`;
  }
  html += `</div>`;
  return html;
}

function _buildRegretCard(data) {
  const regret = data.total_regret || 0;
  const yourReward = data.total_your_reward || 0;
  const bestReward = data.total_best_reward || 0;
  let html = `<div class="agent-data-card">`;
  html += `<div class="agent-data-regret-summary">
    <div><span>你的回饋</span><strong>$${yourReward.toFixed(1)}</strong></div>
    <div><span>最佳回饋</span><strong class="green">$${bestReward.toFixed(1)}</strong></div>
    <div><span>少賺</span><strong class="red">$${regret.toFixed(1)}</strong></div>
  </div>`;
  html += `</div>`;
  return html;
}
