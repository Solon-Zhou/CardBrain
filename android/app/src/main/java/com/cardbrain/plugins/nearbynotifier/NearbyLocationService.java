package com.cardbrain.plugins.nearbynotifier;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.location.Location;
import android.os.Build;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;
import androidx.core.app.ServiceCompat;

import com.cardbrain.app.MainActivity;
import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationCallback;
import com.google.android.gms.location.LocationRequest;
import com.google.android.gms.location.LocationResult;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.location.Priority;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 前景服務：背景定位 → HTTP 查附近商家 → 發通知
 * 完全不依賴 WebView JS，App 進背景後仍持續運作。
 */
public class NearbyLocationService extends Service {

    private static final String TAG = "NearbyLocationSvc";
    private static final String CHANNEL_FG = "nearby_fg";
    private static final String CHANNEL_MERCHANT = "nearby_merchant";
    private static final int FG_NOTIFICATION_ID = 9001;
    private static final float DISTANCE_FILTER = 50f;
    private static final double NOTIFY_RADIUS_M = 200.0;
    private static final double RESET_DISTANCE_M = 300.0;
    private static final long RESET_INTERVAL_MS = 30 * 60 * 1000L;

    public static final String PREFS_NAME = "NearbyNotifierPrefs";
    public static final String KEY_CARD_IDS = "card_ids";
    public static final String KEY_API_BASE = "api_base";

    private FusedLocationProviderClient fusedClient;
    private LocationCallback locationCallback;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    private final Set<String> notifiedMerchants = new HashSet<>();
    private double lastLat = Double.NaN;
    private double lastLng = Double.NaN;
    private long lastResetTs = 0;
    private int notifIdCounter = 1;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannels();
        fusedClient = LocationServices.getFusedLocationProviderClient(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForegroundService();
        startLocationUpdates();
        return START_STICKY;
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (locationCallback != null) {
            fusedClient.removeLocationUpdates(locationCallback);
        }
        executor.shutdown();
    }

    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = getSystemService(NotificationManager.class);

            NotificationChannel fgChannel = new NotificationChannel(
                    CHANNEL_FG, "背景偵測", NotificationManager.IMPORTANCE_LOW);
            fgChannel.setDescription("定位偵測附近商家");
            nm.createNotificationChannel(fgChannel);

            NotificationChannel merchantChannel = new NotificationChannel(
                    CHANNEL_MERCHANT, "附近商家", NotificationManager.IMPORTANCE_HIGH);
            merchantChannel.setDescription("附近有優惠商家通知");
            nm.createNotificationChannel(merchantChannel);
        }
    }

    private void startForegroundService() {
        Notification notification = new NotificationCompat.Builder(this, CHANNEL_FG)
                .setContentTitle("CardBrain")
                .setContentText("偵測附近商家中...")
                .setSmallIcon(android.R.drawable.ic_dialog_map)
                .setOngoing(true)
                .build();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            ServiceCompat.startForeground(this, FG_NOTIFICATION_ID, notification,
                    android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION);
        } else {
            startForeground(FG_NOTIFICATION_ID, notification);
        }
    }

    @SuppressWarnings("MissingPermission")
    private void startLocationUpdates() {
        LocationRequest request = new LocationRequest.Builder(
                Priority.PRIORITY_BALANCED_POWER_ACCURACY, 30_000L)
                .setMinUpdateDistanceMeters(DISTANCE_FILTER)
                .setMinUpdateIntervalMillis(10_000L)
                .build();

        locationCallback = new LocationCallback() {
            @Override
            public void onLocationResult(LocationResult result) {
                Location loc = result.getLastLocation();
                if (loc != null) {
                    onLocation(loc.getLatitude(), loc.getLongitude());
                }
            }
        };

        fusedClient.requestLocationUpdates(request, locationCallback, Looper.getMainLooper());
    }

    private void onLocation(double lat, double lng) {
        maybeResetNotified(lat, lng);
        executor.execute(() -> fetchAndNotify(lat, lng));
    }

    private void maybeResetNotified(double lat, double lng) {
        long now = System.currentTimeMillis();
        if (Double.isNaN(lastLat)) {
            lastLat = lat;
            lastLng = lng;
            lastResetTs = now;
            return;
        }
        double dist = haversine(lastLat, lastLng, lat, lng);
        if (dist >= RESET_DISTANCE_M || now - lastResetTs >= RESET_INTERVAL_MS) {
            notifiedMerchants.clear();
            lastResetTs = now;
        }
        lastLat = lat;
        lastLng = lng;
    }

    private void fetchAndNotify(double lat, double lng) {
        try {
            SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
            String cardIds = prefs.getString(KEY_CARD_IDS, "");
            String apiBase = prefs.getString(KEY_API_BASE, "https://jetthai-cardbrain.zeabur.app");

            StringBuilder urlStr = new StringBuilder(apiBase)
                    .append("/api/nearby?lat=").append(lat)
                    .append("&lng=").append(lng);
            if (!cardIds.isEmpty()) {
                urlStr.append("&card_ids=").append(cardIds);
            }

            HttpURLConnection conn = (HttpURLConnection) new URL(urlStr.toString()).openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(10_000);
            conn.setReadTimeout(10_000);

            int code = conn.getResponseCode();
            if (code != 200) {
                conn.disconnect();
                return;
            }

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            reader.close();
            conn.disconnect();

            JSONObject json = new JSONObject(sb.toString());
            JSONArray nearby = json.optJSONArray("nearby");
            if (nearby == null) return;

            for (int i = 0; i < nearby.length(); i++) {
                JSONObject item = nearby.getJSONObject(i);
                String merchantName = item.getString("merchant_name");
                double distanceM = item.getDouble("distance_m");

                if (distanceM > NOTIFY_RADIUS_M) continue;
                if (notifiedMerchants.contains(merchantName)) continue;

                notifiedMerchants.add(merchantName);

                JSONObject topCard = item.optJSONObject("top_card");
                String body;
                if (topCard != null) {
                    String bankName = topCard.optString("bank_name", "");
                    String cardName = topCard.optString("card_name", "");
                    double rate = topCard.optDouble("reward_rate", 0);
                    body = "建議刷 " + bankName + " " + cardName + "，回饋 " + rate + "%";
                } else {
                    body = "查看附近優惠";
                }

                sendMerchantNotification(merchantName, body);
            }
        } catch (Exception e) {
            Log.w(TAG, "fetchAndNotify error", e);
        }
    }

    private void sendMerchantNotification(String merchantName, String body) {
        Intent intent = new Intent(this, MainActivity.class);
        intent.setAction("NEARBY_NOTIFICATION_CLICK");
        intent.putExtra("merchant_name", merchantName);
        intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);

        PendingIntent pi = PendingIntent.getActivity(this, notifIdCounter,
                intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification notification = new NotificationCompat.Builder(this, CHANNEL_MERCHANT)
                .setContentTitle("附近有 " + merchantName)
                .setContentText(body)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setAutoCancel(true)
                .setContentIntent(pi)
                .build();

        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.notify(notifIdCounter++, notification);
    }

    private static double haversine(double lat1, double lng1, double lat2, double lng2) {
        double R = 6371000;
        double rLat1 = Math.toRadians(lat1);
        double rLat2 = Math.toRadians(lat2);
        double dLat = Math.toRadians(lat2 - lat1);
        double dLng = Math.toRadians(lng2 - lng1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(rLat1) * Math.cos(rLat2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }
}
