/**
 * capacitor-bridge.js — Capacitor 原生功能橋接
 *
 * 瀏覽器環境：完全 no-op，不載入任何 plugin
 * Capacitor 環境：
 *   1. 背景地理定位 (@capacitor-community/background-geolocation)
 *   2. 本地通知 (@capacitor/local-notifications)
 *   3. 使用者點通知 → 開啟 App 跳轉 #/result
 */
const CapBridge = (() => {
  // 瀏覽器環境 → 立即返回空物件
  if (!Config.isCapacitor) {
    return { init() {} };
  }

  // ── Capacitor plugin imports ──
  const { LocalNotifications, BackgroundGeolocation } =
    window.Capacitor.Plugins;

  // 已通知過的商家（避免重複）
  const _notified = new Set();
  let _notifId = 1;
  let _watcherId = null;
  let _lastLat = null;
  let _lastLng = null;
  let _lastResetTs = 0;
  const RESET_DISTANCE = 300; // 300m 移動後重置已通知
  const RESET_INTERVAL = 30 * 60 * 1000; // 30 分鐘定期重置

  // ── DEBUG: 用通知當 log，測完刪掉 ──
  const _DEBUG = true;
  function _dbg(msg) {
    if (!_DEBUG) return;
    LocalNotifications.schedule({
      notifications: [{ id: _notifId++, title: "CB DEBUG", body: msg }],
    }).catch(() => {});
  }

  /**
   * 初始化背景定位 + 通知
   */
  async function init() {
    // 1. 請求通知權限
    await _requestNotificationPermission();

    // 2. 監聽通知點擊
    LocalNotifications.addListener(
      "localNotificationActionPerformed",
      (event) => {
        const data = event.notification?.extra;
        if (data?.merchant) {
          location.hash = `#/result?type=merchant&q=${encodeURIComponent(data.merchant)}`;
        }
      }
    );

    // 3. 啟動背景定位
    await _startBackgroundGeolocation();
  }

  async function _requestNotificationPermission() {
    try {
      const perm = await LocalNotifications.checkPermissions();
      if (perm.display !== "granted") {
        await LocalNotifications.requestPermissions();
      }
    } catch (e) {
      console.warn("[CB] notification permission error:", e);
    }
  }

  async function _startBackgroundGeolocation() {
    try {
      if (!BackgroundGeolocation) {
        _dbg("1 ❌ plugin 不存在，用 fallback");
        _fallbackForegroundWatch();
        return;
      }

      // addWatcher: 前景+背景都會收到位置更新
      _watcherId = await BackgroundGeolocation.addWatcher(
        {
          backgroundMessage: "偵測附近商家中...",
          backgroundTitle: "CardBrain",
          requestPermissions: true,
          stale: false,
          distanceFilter: 50, // 50m 最小位移
        },
        // callback: 每次位置更新觸發
        (location, error) => {
          if (error) {
            _dbg("2 ❌ 定位錯誤: " + (error.code || error.message));
            return;
          }
          if (location) {
            _dbg("2 ✅ 收到位置: " + location.latitude.toFixed(4) + ", " + location.longitude.toFixed(4));
            _onLocation(location.latitude, location.longitude);
          }
        }
      );
      _dbg("1 ✅ watcher 啟動成功");

    } catch (e) {
      _dbg("1 ❌ watcher 啟動失敗: " + e.message);
      _fallbackForegroundWatch();
    }
  }

  /**
   * Plugin 不可用時，改用瀏覽器 Geolocation watchPosition
   * （只在 App 前景時有效）
   */
  function _fallbackForegroundWatch() {
    if (!("geolocation" in navigator)) return;
    navigator.geolocation.watchPosition(
      (pos) => _onLocation(pos.coords.latitude, pos.coords.longitude),
      () => {},
      { enableHighAccuracy: true, maximumAge: 60000 }
    );
  }

  /**
   * 收到位置更新 → 查附近商家 → 發通知
   */
  async function _onLocation(lat, lng) {
    try {
      _maybeResetNotified(lat, lng);

      const cardIds = Store.getMyCards();
      const params = new URLSearchParams({ lat, lng });
      if (cardIds.length) params.set("card_ids", cardIds.join(","));

      const url = `${Config.API_BASE}/api/nearby?${params}`;

      const res = await fetch(url);
      if (!res.ok) {
        _dbg("3 ❌ API 失敗: HTTP " + res.status);
        return;
      }

      const data = await res.json();
      const nearby = data.nearby || [];
      _dbg("3 ✅ API 回傳 " + nearby.length + " 筆");

      for (const item of nearby) {
        if (_notified.has(item.merchant_name)) continue;
        if (item.distance_m > 200) continue; // 200m 內才通知

        _notified.add(item.merchant_name);
        const card = item.top_card;

        await LocalNotifications.schedule({
          notifications: [
            {
              id: _notifId++,
              title: `附近有 ${item.merchant_name}`,
              body: `建議刷 ${card.bank_name} ${card.card_name}，回饋 ${card.reward_rate}%`,
              extra: { merchant: item.merchant_name },
            },
          ],
        });
      }
    } catch (e) {
      _dbg("3 ❌ onLocation 錯誤: " + e.message);
    }
  }

  // 位置大幅變動或經過一定時間後重置已通知清單，避免跨區域無法再推播
  function _maybeResetNotified(lat, lng) {
    const now = Date.now();
    if (_lastLat === null) {
      _lastLat = lat;
      _lastLng = lng;
      _lastResetTs = now;
      return;
    }
    const dist = _haversine(_lastLat, _lastLng, lat, lng);
    if (dist >= RESET_DISTANCE || now - _lastResetTs >= RESET_INTERVAL) {
      _notified.clear();
      _lastResetTs = now;
    }
    _lastLat = lat;
    _lastLng = lng;
  }

  function _haversine(lat1, lng1, lat2, lng2) {
    const R = 6371000;
    const rlat1 = lat1 * Math.PI / 180;
    const rlat2 = lat2 * Math.PI / 180;
    const dlat = (lat2 - lat1) * Math.PI / 180;
    const dlng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dlat / 2) ** 2 + Math.cos(rlat1) * Math.cos(rlat2) * Math.sin(dlng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  return { init };
})();

// App 啟動時自動初始化
document.addEventListener("DOMContentLoaded", () => {
  if (Config.isCapacitor) {
    CapBridge.init();
  }
});
