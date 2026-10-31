from pathlib import Path

root = Path("unpacked/discipline_app/android/app/src/main")
manifest = root / "AndroidManifest.xml"
receiver = root / "java/com/ak/discipline/ReminderReceiver.java"
main = root / "java/com/ak/discipline/MainActivity.java"

m = manifest.read_text()
m = m.replace('<uses-permission android:name="android.permission.WAKE_LOCK" />',
'''<uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />''')
m = m.replace('</application>', '''<service
            android:name=".AlarmSoundService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="mediaPlayback" />
    </application>''')
manifest.write_text(m)

r = receiver.read_text()
r = r.replace('''        showNotification(context,id,name,type,false);
        // Schedule the next occurrence.''', '''        Intent ring = new Intent(context, AlarmSoundService.class);
        ring.setAction(AlarmSoundService.ACTION_START);
        ring.putExtra("id", id);
        ring.putExtra("name", name == null ? "Reminder" : name);
        ring.putExtra("type", type == null ? "Reminder" : type);
        try {
            if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(ring);
            else context.startService(ring);
        } catch (Exception ignored) { }
        // Schedule the next occurrence.''')
receiver.write_text(r)

service = r'''package com.ak.discipline;

import android.app.*;
import android.content.*;
import android.media.*;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;

public class AlarmSoundService extends Service {
    public static final String ACTION_START = "com.ak.discipline.ALARM_START";
    public static final String ACTION_STOP = "com.ak.discipline.ALARM_STOP";
    private static final String CHANNEL = "ak_os_alarm_ring";
    private static final int NOTIFICATION_ID = 88128;
    private MediaPlayer player;
    private Vibrator vibrator;

    @Override public void onCreate() {
        super.onCreate();
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "Alarm ringing", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("Continuous alarm sound until you stop it");
            ch.setSound(null, null);
            ch.enableVibration(true);
            ch.setVibrationPattern(new long[]{0, 700, 300, 700});
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(ch);
        }
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopAlarm();
            return START_NOT_STICKY;
        }
        String label = intent == null ? "Your reminder" : intent.getStringExtra("name");
        if (label == null || label.trim().isEmpty()) label = "Your reminder";
        startForeground(NOTIFICATION_ID, buildNotification(label));
        startLoopingAlarmSound();
        startVibration();
        return START_STICKY;
    }

    private Notification buildNotification(String label) {
        Intent stop = new Intent(this, AlarmSoundService.class);
        stop.setAction(ACTION_STOP);
        PendingIntent stopPi = PendingIntent.getService(this, 88129, stop,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Intent open = new Intent(this, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPi = PendingIntent.getActivity(this, 88130, open,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
            ? new Notification.Builder(this, CHANNEL) : new Notification.Builder(this);
        return b.setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setContentTitle("⏰ ALARM · " + label)
            .setContentText("Alarm is ringing. Tap STOP when finished.")
            .setContentIntent(openPi)
            .addAction(android.R.drawable.ic_media_pause, "STOP ALARM", stopPi)
            .setCategory(Notification.CATEGORY_ALARM)
            .setPriority(Notification.PRIORITY_MAX)
            .setOngoing(true)
            .setAutoCancel(false)
            .build();
    }

    private void startLoopingAlarmSound() {
        releasePlayer();
        try {
            Uri alarm = Settings.System.getDefaultUri(Settings.System.TYPE_ALARM);
            if (alarm == null) alarm = Settings.System.DEFAULT_NOTIFICATION_URI;
            player = new MediaPlayer();
            player.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ALARM)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build());
            player.setDataSource(this, alarm);
            player.setLooping(true);
            player.setVolume(1.0f, 1.0f);
            player.setOnPreparedListener(MediaPlayer::start);
            player.setOnErrorListener((mp, what, extra) -> { releasePlayer(); return true; });
            player.prepareAsync();
        } catch (Exception e) {
            releasePlayer();
        }
    }

    private void startVibration() {
        try {
            if (Build.VERSION.SDK_INT >= 31) {
                VibratorManager vm = (VibratorManager)getSystemService(VIBRATOR_MANAGER_SERVICE);
                vibrator = vm == null ? null : vm.getDefaultVibrator();
            } else vibrator = (Vibrator)getSystemService(VIBRATOR_SERVICE);
            if (vibrator != null && vibrator.hasVibrator()) {
                long[] pattern = {0, 700, 300, 700, 300};
                if (Build.VERSION.SDK_INT >= 26)
                    vibrator.vibrate(VibrationEffect.createWaveform(pattern, 0));
                else vibrator.vibrate(pattern, 0);
            }
        } catch (Exception ignored) { }
    }

    private void stopAlarm() {
        try { if (vibrator != null) vibrator.cancel(); } catch (Exception ignored) { }
        releasePlayer();
        stopForeground(true);
        stopSelf();
    }

    private void releasePlayer() {
        try { if (player != null) { if (player.isPlaying()) player.stop(); player.release(); } } catch (Exception ignored) { }
        player = null;
    }

    @Override public void onDestroy() {
        try { if (vibrator != null) vibrator.cancel(); } catch (Exception ignored) { }
        releasePlayer();
        super.onDestroy();
    }

    @Override public android.os.IBinder onBind(Intent intent) { return null; }
}
'''
(root / "java/com/ak/discipline/AlarmSoundService.java").write_text(service)
from pathlib import Path
p=Path("unpacked/discipline_app/android/app/build.gradle")
s=p.read_text().replace("versionCode 3", "versionCode 4").replace("versionName '1.3.0'", "versionName '1.4.1'")
p.write_text(s)
print("Applied continuous alarm service patch and set version 1.4.1")
