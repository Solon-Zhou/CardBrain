#import <Capacitor/Capacitor.h>

CAP_PLUGIN(NearbyNotifierPlugin, "NearbyNotifier",
    CAP_PLUGIN_METHOD(start, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(stop, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(syncCards, CAPPluginReturnPromise);
)
