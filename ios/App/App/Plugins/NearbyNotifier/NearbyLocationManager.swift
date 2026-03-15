import CoreLocation
import UserNotifications
import Foundation

/**
 * iOS 背景定位 → HTTP 查附近商家 → 發通知
 * 完全不依賴 WebView JS。
 */
class NearbyLocationManager: NSObject, CLLocationManagerDelegate {

    static let shared = NearbyLocationManager()

    private let clManager = CLLocationManager()
    private var notifiedMerchants = Set<String>()
    private var lastLat: Double?
    private var lastLng: Double?
    private var lastResetTs: TimeInterval = 0
    private var notifIdCounter = 1

    private let notifyRadiusM: Double = 200.0
    private let resetDistanceM: Double = 300.0
    private let resetIntervalS: TimeInterval = 30 * 60
    private let apiBase: String = "https://jetthai-cardbrain.zeabur.app"

    private override init() {
        super.init()
        clManager.delegate = self
        clManager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        clManager.distanceFilter = 50
        clManager.allowsBackgroundLocationUpdates = true
        clManager.pausesLocationUpdatesAutomatically = false
        clManager.showsBackgroundLocationIndicator = true
    }

    func start() {
        clManager.requestAlwaysAuthorization()
        requestNotificationPermission()
        clManager.startUpdatingLocation()
    }

    func stop() {
        clManager.stopUpdatingLocation()
    }

    private func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .sound, .badge]
        ) { _, error in
            if let error = error {
                print("[NearbyLocationManager] notification permission error: \(error)")
            }
        }
    }

    // MARK: - CLLocationManagerDelegate

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        let lat = loc.coordinate.latitude
        let lng = loc.coordinate.longitude

        maybeResetNotified(lat: lat, lng: lng)
        fetchAndNotify(lat: lat, lng: lng)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("[NearbyLocationManager] location error: \(error)")
    }

    // MARK: - Core Logic

    private func maybeResetNotified(lat: Double, lng: Double) {
        let now = Date().timeIntervalSince1970
        guard let prevLat = lastLat, let prevLng = lastLng else {
            lastLat = lat
            lastLng = lng
            lastResetTs = now
            return
        }

        let dist = haversine(lat1: prevLat, lng1: prevLng, lat2: lat, lng2: lng)
        if dist >= resetDistanceM || now - lastResetTs >= resetIntervalS {
            notifiedMerchants.removeAll()
            lastResetTs = now
        }
        lastLat = lat
        lastLng = lng
    }

    private func fetchAndNotify(lat: Double, lng: Double) {
        let cardIds = UserDefaults.standard.string(forKey: "nearby_card_ids") ?? ""

        var urlStr = "\(apiBase)/api/nearby?lat=\(lat)&lng=\(lng)"
        if !cardIds.isEmpty {
            urlStr += "&card_ids=\(cardIds)"
        }

        guard let url = URL(string: urlStr) else { return }

        let task = URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let self = self,
                  let data = data,
                  error == nil,
                  let httpResp = response as? HTTPURLResponse,
                  httpResp.statusCode == 200 else { return }

            do {
                guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let nearby = json["nearby"] as? [[String: Any]] else { return }

                for item in nearby {
                    guard let merchantName = item["merchant_name"] as? String,
                          let distanceM = item["distance_m"] as? Double else { continue }

                    if distanceM > self.notifyRadiusM { continue }
                    if self.notifiedMerchants.contains(merchantName) { continue }

                    self.notifiedMerchants.insert(merchantName)

                    var body = "查看附近優惠"
                    if let topCard = item["top_card"] as? [String: Any] {
                        let bankName = topCard["bank_name"] as? String ?? ""
                        let cardName = topCard["card_name"] as? String ?? ""
                        let rate = topCard["reward_rate"] as? Double ?? 0
                        body = "建議刷 \(bankName) \(cardName)，回饋 \(rate)%"
                    }

                    self.sendNotification(merchantName: merchantName, body: body)
                }
            } catch {
                print("[NearbyLocationManager] JSON parse error: \(error)")
            }
        }
        task.resume()
    }

    private func sendNotification(merchantName: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = "附近有 \(merchantName)"
        content.body = body
        content.sound = .default
        content.userInfo = ["merchant": merchantName]

        let request = UNNotificationRequest(
            identifier: "nearby_\(notifIdCounter)",
            content: content,
            trigger: nil
        )
        notifIdCounter += 1

        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("[NearbyLocationManager] notification error: \(error)")
            }
        }
    }

    // MARK: - Haversine

    private func haversine(lat1: Double, lng1: Double, lat2: Double, lng2: Double) -> Double {
        let R = 6371000.0
        let rLat1 = lat1 * .pi / 180
        let rLat2 = lat2 * .pi / 180
        let dLat = (lat2 - lat1) * .pi / 180
        let dLng = (lng2 - lng1) * .pi / 180
        let a = sin(dLat / 2) * sin(dLat / 2)
            + cos(rLat1) * cos(rLat2) * sin(dLng / 2) * sin(dLng / 2)
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))
    }
}
