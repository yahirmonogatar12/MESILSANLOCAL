package com.mesilsan.pingmonitor

import android.os.Handler
import android.os.Looper
import java.util.concurrent.CopyOnWriteArraySet

/** Estado compartido entre el servicio y la pantalla. Los listeners se llaman en el hilo principal. */
object MonitorState {

    @Volatile
    var running = false
        private set

    /** Estado por id de dispositivo. */
    @Volatile
    var statuses: Map<String, PeerStatus> = emptyMap()
        private set

    /** Último ping recibido por dirección IP remota. */
    @Volatile
    var incoming: Map<String, IncomingPing> = emptyMap()
        private set

    /** Error del servidor local (p. ej. puerto ocupado), o null si funciona. */
    @Volatile
    var serverError: String? = null
        private set

    private val listeners = CopyOnWriteArraySet<() -> Unit>()
    private val mainHandler = Handler(Looper.getMainLooper())

    fun addListener(listener: () -> Unit) {
        listeners.add(listener)
    }

    fun removeListener(listener: () -> Unit) {
        listeners.remove(listener)
    }

    private fun changed() {
        mainHandler.post { listeners.forEach { it() } }
    }

    fun setRunning(value: Boolean) {
        running = value
        changed()
    }

    fun setStatuses(value: Map<String, PeerStatus>) {
        statuses = value
        changed()
    }

    @Synchronized
    fun recordIncoming(ping: IncomingPing) {
        incoming = incoming + (ping.address to ping)
        changed()
    }

    fun setServerError(value: String?) {
        serverError = value
        changed()
    }
}
