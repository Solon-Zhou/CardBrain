/**
 * config.js — 環境偵測 & API 基底 URL
 * PWA (瀏覽器) → "" (相對路徑)
 * Capacitor (原生 App) → 絕對路徑指向 Zeabur 後端
 */
const Config = (() => {
  const isCapacitor = typeof window.Capacitor !== "undefined" &&
    window.Capacitor.isNativePlatform?.();

  // Capacitor 環境需要絕對 URL，因為 www/ 是 local file
  const API_BASE = isCapacitor
    ? "https://jetthai-cardbrain.zeabur.app"
    : "";

  return { isCapacitor, API_BASE };
})();
