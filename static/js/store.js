/**
 * store.js — localStorage 卡片管理
 */
const Store = (() => {
  const KEY = "cardbrain_my_cards";

  function getMyCards() {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveMyCards(ids) {
    localStorage.setItem(KEY, JSON.stringify(ids));
    _syncToNative(ids);
  }

  function toggleCard(cardId) {
    const ids = getMyCards();
    const idx = ids.indexOf(cardId);
    if (idx >= 0) {
      ids.splice(idx, 1);
    } else {
      ids.push(cardId);
    }
    saveMyCards(ids);
    return ids;
  }

  function hasCard(cardId) {
    return getMyCards().includes(cardId);
  }

  function _syncToNative(ids) {
    if (typeof CapBridge !== "undefined" && CapBridge.syncCards) {
      CapBridge.syncCards();
    }
  }

  return { getMyCards, saveMyCards, toggleCard, hasCard };
})();
