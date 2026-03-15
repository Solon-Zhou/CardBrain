package com.cardbrain.plugins.nearbynotifier;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * NearbyNotifier Capacitor Plugin
 * JS 透過 registerPlugin("NearbyNotifier") 呼叫 start / stop / syncCards
 */
@CapacitorPlugin(name = "NearbyNotifier")
public class NearbyNotifierPlugin extends Plugin {

    @PluginMethod()
    public void start(PluginCall call) {
        Intent intent = new Intent(getContext(), NearbyLocationService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getContext().startForegroundService(intent);
        } else {
            getContext().startService(intent);
        }
        call.resolve();
    }

    @PluginMethod()
    public void stop(PluginCall call) {
        Intent intent = new Intent(getContext(), NearbyLocationService.class);
        getContext().stopService(intent);
        call.resolve();
    }

    @PluginMethod()
    public void syncCards(PluginCall call) {
        String cardIds = call.getString("cardIds", "");
        SharedPreferences prefs = getContext()
                .getSharedPreferences(NearbyLocationService.PREFS_NAME, 0);
        prefs.edit().putString(NearbyLocationService.KEY_CARD_IDS, cardIds).apply();

        JSObject result = new JSObject();
        result.put("synced", true);
        call.resolve(result);
    }
}
