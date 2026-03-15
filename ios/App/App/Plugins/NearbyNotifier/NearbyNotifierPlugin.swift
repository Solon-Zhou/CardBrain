import Capacitor

@objc(NearbyNotifierPlugin)
public class NearbyNotifierPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "NearbyNotifierPlugin"
    public let jsName = "NearbyNotifier"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "start", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "stop", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "syncCards", returnType: CAPPluginReturnPromise)
    ]

    private let locationManager = NearbyLocationManager.shared

    @objc func start(_ call: CAPPluginCall) {
        locationManager.start()
        call.resolve()
    }

    @objc func stop(_ call: CAPPluginCall) {
        locationManager.stop()
        call.resolve()
    }

    @objc func syncCards(_ call: CAPPluginCall) {
        let cardIds = call.getString("cardIds") ?? ""
        UserDefaults.standard.set(cardIds, forKey: "nearby_card_ids")
        call.resolve(["synced": true])
    }
}
