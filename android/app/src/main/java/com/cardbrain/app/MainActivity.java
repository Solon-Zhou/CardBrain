package com.cardbrain.app;

import android.content.Intent;
import android.os.Bundle;
import android.webkit.WebView;

import com.cardbrain.plugins.nearbynotifier.NearbyNotifierPlugin;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        registerPlugin(NearbyNotifierPlugin.class);
        super.onCreate(savedInstanceState);
        handleNotificationIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        handleNotificationIntent(intent);
    }

    private void handleNotificationIntent(Intent intent) {
        if (intent == null) return;
        if (!"NEARBY_NOTIFICATION_CLICK".equals(intent.getAction())) return;

        String merchant = intent.getStringExtra("merchant_name");
        if (merchant == null || merchant.isEmpty()) return;

        // WebView 載入完成後執行 JS 導航
        getBridge().getWebView().post(() -> {
            WebView wv = getBridge().getWebView();
            String encoded = merchant.replace("'", "\\'");
            wv.evaluateJavascript(
                    "location.hash = '#/result?type=merchant&q=' + encodeURIComponent('" + encoded + "');",
                    null);
        });
    }
}
