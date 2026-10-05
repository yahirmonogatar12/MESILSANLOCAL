package com.mesilsan.pingmonitor

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/** Estado compartido entre el servicio y la pantalla. */
object MonitorState {

    private val _running = MutableStateFlow(false)
    val running: StateFlow<Boolean> = _running.asStateFlow()

    /** Estado por id de dispositivo. */
    private val _statuses = MutableStateFlow<Map<String, PeerStatus>>(emptyMap())
    val statuses: StateFlow<Map<String, PeerStatus>> = _statuses.asStateFlow()

    /** Último ping recibido por dirección IP remota. */
    private val _incoming = MutableStateFlow<Map<String, IncomingPing>>(emptyMap())
    val incoming: StateFlow<Map<String, IncomingPing>> = _incoming.asStateFlow()

    /** Error del servidor local (p. ej. puerto ocupado), o null si funciona. */
    private val _serverError = MutableStateFlow<String?>(null)
    val serverError: StateFlow<String?> = _serverError.asStateFlow()

    fun setRunning(value: Boolean) {
        _running.value = value
    }

    fun setStatuses(value: Map<String, PeerStatus>) {
        _statuses.value = value
    }

    fun recordIncoming(ping: IncomingPing) {
        _incoming.update { it + (ping.address to ping) }
    }

    fun setServerError(value: String?) {
        _serverError.value = value
    }
}
