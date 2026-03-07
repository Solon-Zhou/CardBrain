/**
 * nearby.js — 附近商家地圖頁面
 */

async function NearbyPage() {
  return `
    <div class="nearby-page">
      <div class="page-title">📍 附近商家</div>
      <div class="nearby-map-wrap">
        <div id="nearbyMap"></div>
        <div class="nearby-permission" id="nearbyPermission">
          <div class="nearby-permission-icon">📍</div>
          <div class="nearby-permission-text">開啟定位以探索附近商家的最佳刷卡推薦</div>
          <button class="nearby-permission-btn" id="btnGrantLocation">開啟定位</button>
        </div>
      </div>
    </div>
  `;
}

NearbyPage.init = () => {
  const permissionEl = document.getElementById("nearbyPermission");
  const mapEl = document.getElementById("nearbyMap");
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
  }

  function _hidePermissionPrompt() {
    permissionEl.style.display = "none";
    mapEl.style.display = "";
  }

  function renderNearby(data) {
    const { userLat, userLng, nearby, accuracy } = data;

    _hidePermissionPrompt();

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
    _startGeo();
  });
};
