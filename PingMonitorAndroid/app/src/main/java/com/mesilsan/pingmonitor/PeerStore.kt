package com.mesilsan.pingmonitor

import android.content.Context
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/** Configuración y lista de dispositivos, guardada en SharedPreferences. */
class PeerStore(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences("ping_monitor", Context.MODE_PRIVATE)

    fun peers(): List<Peer> {
        val raw = prefs.getString(KEY_PEERS, null) ?: return emptyList()
        return try {
            val array = JSONArray(raw)
            (0 until array.length()).map { i ->
                val o = array.getJSONObject(i)
                Peer(o.getString("id"), o.getString("name"), o.getString("host"))
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    private fun savePeers(peers: List<Peer>) {
        val array = JSONArray()
        peers.forEach {
            array.put(JSONObject().put("id", it.id).put("name", it.name).put("host", it.host))
        }
        prefs.edit().putString(KEY_PEERS, array.toString()).apply()
    }

    fun addPeer(name: String, host: String): Peer {
        val peer = Peer(UUID.randomUUID().toString(), name, host)
        savePeers(peers() + peer)
        return peer
    }

    fun updatePeer(peer: Peer) {
        savePeers(peers().map { if (it.id == peer.id) peer else it })
    }

    fun removePeer(id: String) {
        savePeers(peers().filterNot { it.id == id })
    }

    var deviceName: String
        get() = prefs.getString(KEY_DEVICE_NAME, null) ?: "${Build.MANUFACTURER} ${Build.MODEL}"
        set(value) = prefs.edit().putString(KEY_DEVICE_NAME, value).apply()

    /** Segundos entre cada verificación. */
    var intervalSec: Int
        get() = prefs.getInt(KEY_INTERVAL, DEFAULT_INTERVAL)
        set(value) = prefs.edit().putInt(KEY_INTERVAL, value.coerceIn(MIN_INTERVAL, MAX_INTERVAL)).apply()

    /** Fallos consecutivos antes de notificar la desconexión. */
    var failThreshold: Int
        get() = prefs.getInt(KEY_THRESHOLD, DEFAULT_THRESHOLD)
        set(value) = prefs.edit().putInt(KEY_THRESHOLD, value.coerceIn(1, 100)).apply()

    /** Puerto TCP donde escucha la app (debe ser el mismo en todas las tablets). */
    var port: Int
        get() = prefs.getInt(KEY_PORT, DEFAULT_PORT)
        set(value) = prefs.edit().putInt(KEY_PORT, value.coerceIn(1024, 65535)).apply()

    /** Minutos para repetir la alerta mientras siga caído (0 = no repetir). */
    var repeatAlertMin: Int
        get() = prefs.getInt(KEY_REPEAT, 0)
        set(value) = prefs.edit().putInt(KEY_REPEAT, value.coerceIn(0, 1440)).apply()

    /** Si el monitoreo debe estar activo (se usa para reiniciarlo al encender la tablet). */
    var monitoringEnabled: Boolean
        get() = prefs.getBoolean(KEY_ENABLED, false)
        set(value) = prefs.edit().putBoolean(KEY_ENABLED, value).apply()

    companion object {
        const val DEFAULT_PORT = 47800
        const val DEFAULT_INTERVAL = 10
        const val DEFAULT_THRESHOLD = 3
        const val MIN_INTERVAL = 3
        const val MAX_INTERVAL = 3600

        private const val KEY_PEERS = "peers"
        private const val KEY_DEVICE_NAME = "device_name"
        private const val KEY_INTERVAL = "interval_sec"
        private const val KEY_THRESHOLD = "fail_threshold"
        private const val KEY_PORT = "port"
        private const val KEY_REPEAT = "repeat_alert_min"
        private const val KEY_ENABLED = "monitoring_enabled"
    }
}
