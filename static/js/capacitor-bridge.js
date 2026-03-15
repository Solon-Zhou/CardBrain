/**
 * capacitor-bridge.js — Capacitor 原生功能橋接
 *
 * 瀏覽器環境：完全 no-op，不載入任何 plugin
 * Capacitor 環境：
 *   呼叫原生 NearbyNotifier plugin（定位 + API + 通知全在原生層）
 *   JS 只負責：啟動 plugin、同步 card_ids、處理通知點擊路由
 */
const CapBridge = (() => {
  // 瀏覽器環境 → 立即返回空物件
  if (!Config.isCapacitor) {
    return { init() {}, syncCards() {} };
  }

  // ── Capacitor plugin imports ──
  const { registerPlugin } = window.Capacitor;
  const NearbyNotifier = registerPlugin("NearbyNotifier");

  /**
   * 初始化：同步卡片 → 啟動原生定位服務
   */
  async function init() {
    try {
      // 1. 同步目前持有的卡片到原生層
      await syncCards();

      // 2. 啟動原生前景服務（定位 + API + 通知）
      await NearbyNotifier.start();
    } catch (e) {
      console.warn("[CapBridge] init error:", e);
    }
  }

  /**
   * 同步卡片 ID 到原生 SharedPreferences / UserDefaults
   */
  async function syncCards() {
    try {
      const ids = Store.getMyCards();
      await NearbyNotifier.syncCards({ cardIds: ids.join(",") });
    } catch (e) {
      console.warn("[CapBridge] syncCards error:", e);
    }
  }

  return { init, syncCards };
})();

// App 啟動時自動初始化
document.addEventListener("DOMContentLoaded", () => {
  if (Config.isCapacitor) {
    CapBridge.init();
  }
});
