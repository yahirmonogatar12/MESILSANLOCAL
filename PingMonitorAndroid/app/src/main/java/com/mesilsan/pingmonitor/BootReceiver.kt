package com.mesilsan.pingmonitor

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/** Reinicia el monitoreo al encender la tablet o al actualizar la app. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED &&
            intent.action != Intent.ACTION_MY_PACKAGE_REPLACED
        ) {
            return
        }
        if (!PeerStore(context).monitoringEnabled) return
        try {
            MonitorService.start(context)
        } catch (e: Exception) {
            Log.e("BootReceiver", "No se pudo iniciar el monitoreo", e)
        }
    }
}
