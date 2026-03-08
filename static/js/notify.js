/**
 * notify.js — Notification API 封裝
 * 推播「偵測到附近的 XXX，建議刷 YYY 卡」
 */
const Notify = (() => {
  // 已通知過的商家（避免重複推播）
  const _notified = new Set();

  function isSupported() {
    // Capacitor 環境由 capacitor-bridge.js 處理原生通知
    if (Config.isCapacitor) return false;
    return "Notification" in window;
  }

  async function requestPermission() {
    if (!isSupported()) return "denied";
    if (Notification.permission === "granted") return "granted";
    if (Notification.permission === "denied") return "denied";
    return await Notification.requestPermission();
  }

  /**
   * 推播附近商家通知
   * @param {object} item - { merchant_name, category_name, top_card: { bank_name, card_name, reward_rate } }
   */
  function notifyNearby(item) {
    if (!isSupported() || Notification.permission !== "granted") return;
    if (_notified.has(item.merchant_name)) return;
    _notified.add(item.merchant_name);

    const card = item.top_card;
    const n = new Notification(`附近有 ${item.merchant_name}`, {
      body: `建議刷 ${card.bank_name} ${card.card_name}，回饋 ${card.reward_rate}%`,
      icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧠</text></svg>",
      tag: `nearby-${item.merchant_name}`,
    });

    n.onclick = () => {
      window.focus();
      location.hash = `#/result?type=merchant&q=${encodeURIComponent(item.merchant_name)}`;
      n.close();
    };
  }

  /**
   * 清除已通知記錄（位置大幅變動時呼叫）
   */
  function clearNotified() {
    _notified.clear();
  }

  return { isSupported, requestPermission, notifyNearby, clearNotified };
})();
