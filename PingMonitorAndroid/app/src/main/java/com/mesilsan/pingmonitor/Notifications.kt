package com.mesilsan.pingmonitor

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.drawable.Icon
import android.os.Build
import android.text.format.DateFormat
import java.util.Date

object Notifications {

    private const val CHANNEL_SERVICE = "monitor_service"
    private const val CHANNEL_ALERTS = "connection_alerts"
    private const val CHANNEL_RECOVERY = "connection_recovery"

    const val ID_FOREGROUND = 1
    private const val ID_LOCAL = 2
    private const val PEER_ID_BASE = 1000

    private fun manager(context: Context) = context.getSystemService(NotificationManager::class.java)

    fun createChannels(context: Context) {
        val nm = manager(context) ?: return
        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_SERVICE,
                context.getString(R.string.channel_service),
                NotificationManager.IMPORTANCE_LOW,
            ).apply { setShowBadge(false) }
        )
        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ALERTS,
                context.getString(R.string.channel_alerts),
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = context.getString(R.string.channel_alerts_desc)
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 500, 250, 500, 250, 500)
                enableLights(true)
            }
        )
        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_RECOVERY,
                context.getString(R.string.channel_recovery),
                NotificationManager.IMPORTANCE_DEFAULT,
            )
        )
    }

    private fun openAppIntent(context: Context): PendingIntent =
        PendingIntent.getActivity(
            context,
            0,
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

    fun foreground(context: Context, text: String): Notification {
        val stop = PendingIntent.getService(
            context,
            1,
            Intent(context, MonitorService::class.java).setAction(MonitorService.ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val builder = Notification.Builder(context, CHANNEL_SERVICE)
            .setSmallIcon(R.drawable.ic_stat_ping)
            .setContentTitle(context.getString(R.string.fg_title))
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setShowWhen(false)
            .setContentIntent(openAppIntent(context))
            .addAction(
                Notification.Action.Builder(
                    Icon.createWithResource(context, R.drawable.ic_stat_ping),
                    context.getString(R.string.stop),
                    stop,
                ).build()
            )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            builder.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE)
        }
        return builder.build()
    }

    fun updateForeground(context: Context, text: String) {
        notify(context, ID_FOREGROUND, foreground(context, text))
    }

    private fun alertBuilder(context: Context, title: String, text: String) =
        Notification.Builder(context, CHANNEL_ALERTS)
            .setSmallIcon(R.drawable.ic_stat_ping)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setColor(context.getColor(R.color.status_offline))
            .setCategory(Notification.CATEGORY_ERROR)
            .setAutoCancel(false)
            .setContentIntent(openAppIntent(context))

    private fun recoveryBuilder(context: Context, title: String, text: String) =
        Notification.Builder(context, CHANNEL_RECOVERY)
            .setSmallIcon(R.drawable.ic_stat_ping)
            .setContentTitle(title)
            .setContentText(text)
            .setColor(context.getColor(R.color.status_online))
            .setAutoCancel(true)
            .setContentIntent(openAppIntent(context))

    fun peerDown(context: Context, status: PeerStatus) {
        val since = status.lastSeen?.let {
            context.getString(R.string.alert_down_since, formatTime(context, it))
        } ?: context.getString(R.string.alert_down_never)
        val notification = alertBuilder(
            context,
            context.getString(R.string.alert_down_title, status.peer.name),
            context.getString(R.string.alert_down_text, status.peer.host, since),
        ).build()
        notify(context, peerNotificationId(status.peer.id), notification)
    }

    fun peerRecovered(context: Context, status: PeerStatus) {
        val notification = recoveryBuilder(
            context,
            context.getString(R.string.alert_up_title, status.peer.name),
            context.getString(
                R.string.alert_up_text, status.peer.host, formatTime(context, System.currentTimeMillis()),
            ),
        ).build()
        // Mismo id: reemplaza la alerta de "sin conexión".
        notify(context, peerNotificationId(status.peer.id), notification)
    }

    fun localProblem(context: Context, problem: String) {
        notify(context, ID_LOCAL, alertBuilder(context, context.getString(R.string.local_down_title), problem).build())
    }

    fun localRecovered(context: Context) {
        val notification = recoveryBuilder(
            context,
            context.getString(R.string.local_up_title),
            context.getString(R.string.local_up_text),
        ).build()
        notify(context, ID_LOCAL, notification)
    }

    fun cancelPeer(context: Context, peerId: String) {
        manager(context)?.cancel(peerNotificationId(peerId))
    }

    fun cancelLocal(context: Context) {
        manager(context)?.cancel(ID_LOCAL)
    }

    private fun hasPermission(context: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    fun canNotify(context: Context): Boolean =
        hasPermission(context) && manager(context)?.areNotificationsEnabled() == true

    private fun notify(context: Context, id: Int, notification: Notification) {
        if (!hasPermission(context)) return
        try {
            manager(context)?.notify(id, notification)
        } catch (e: SecurityException) {
            // Permiso revocado mientras corría.
        }
    }

    private fun peerNotificationId(peerId: String) = PEER_ID_BASE + (peerId.hashCode() and 0x0FFFFFFF)

    private fun formatTime(context: Context, time: Long): String =
        DateFormat.getTimeFormat(context).format(Date(time))
}
