package com.mesilsan.pingmonitor

/** Dispositivo remoto (otra tablet) que se vigila por Tailscale. */
data class Peer(
    val id: String,
    val name: String,
    /** IP de Tailscale (100.x.y.z) o nombre MagicDNS. */
    val host: String,
)

enum class PeerState {
    /** Aún no se ha hecho ninguna verificación. */
    UNKNOWN,

    /** Responde al ping y la app PingMonitor del otro lado contesta. */
    ONLINE,

    /** Responde al ping; el otro equipo no tiene la app (PC, otro Android) o está cerrada. */
    NO_APP,

    /** No responde: sin conexión. */
    OFFLINE,
}

data class PeerStatus(
    val peer: Peer,
    val state: PeerState = PeerState.UNKNOWN,
    val latencyMs: Long? = null,
    /** Nombre que reporta la app remota. */
    val remoteName: String? = null,
    /** Última vez (epoch ms) que respondió. */
    val lastSeen: Long? = null,
    /** Última vez (epoch ms) que se verificó. */
    val lastCheck: Long? = null,
    /** Fallos consecutivos. */
    val failures: Int = 0,
    /** Ya se envió la notificación de "sin conexión". */
    val alerted: Boolean = false,
    /** Última vez (epoch ms) que se notificó la caída (para repetir la alerta). */
    val lastAlertAt: Long? = null,
)

/** Ping recibido desde otra tablet hacia este dispositivo. */
data class IncomingPing(
    val address: String,
    val name: String,
    val time: Long,
)
