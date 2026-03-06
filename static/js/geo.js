/**
 * geo.js — 瀏覽器 Geolocation 封裝
 * 節流：60 秒間隔 + 50m 最小位移
 */
const Geo = (() => {
  let watchId = null;
  let lastLat = null;
  let lastLng = null;
  let lastFetchTime = 0;
  const MIN_INTERVAL = 60000; // 60s
  const MIN_DISTANCE = 50; // 50m

  function _distanceM(lat1, lng1, lat2, lng2) {
    const R = 6371000;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  async function _fetchNearby(lat, lng, callback) {
    try {
      const cardIds = Store.getMyCards();
      const params = new URLSearchParams({ lat, lng });
      if (cardIds.length) params.set("card_ids", cardIds.join(","));
      const res = await fetch(`/api/nearby?${params}`);
      if (!res.ok) return;
      const data = await res.json();
      callback(data.nearby || []);
    } catch {
      // 靜默降級
    }
  }

  function _onPosition(pos, callback) {
    const { latitude: lat, longitude: lng } = pos.coords;
    const now = Date.now();

    // 節流：間隔 + 位移
    if (lastLat !== null) {
      const dist = _distanceM(lastLat, lastLng, lat, lng);
      if (now - lastFetchTime < MIN_INTERVAL && dist < MIN_DISTANCE) return;
    }

    lastLat = lat;
    lastLng = lng;
    lastFetchTime = now;
    _fetchNearby(lat, lng, callback);
  }

  /**
   * 首次取位 + 持續監聽
   * @param {function} onNearby - callback(nearbyArray)
   */
  function startWatching(onNearby) {
    if (!("geolocation" in navigator)) return;

    // 首次取位
    navigator.geolocation.getCurrentPosition(
      (pos) => _onPosition(pos, onNearby),
      () => {}, // 權限被拒，靜默
      { enableHighAccuracy: false, timeout: 10000 }
    );

    // 持續監聽
    watchId = navigator.geolocation.watchPosition(
      (pos) => _onPosition(pos, onNearby),
      () => {},
      { enableHighAccuracy: false, maximumAge: 60000 }
    );
  }

  function stopWatching() {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
  }

  /**
   * 單次取位（Promise）
   */
  function requestPosition() {
    return new Promise((resolve, reject) => {
      if (!("geolocation" in navigator)) return reject(new Error("no geolocation"));
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        reject,
        { enableHighAccuracy: false, timeout: 10000 }
      );
    });
  }

  return { startWatching, stopWatching, requestPosition };
})();
