package com.mesilsan.pingmonitor

import android.annotation.SuppressLint
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Servicio en primer plano que:
 *  1. Escucha pings de otras tablets ([HeartbeatServer]).
 *  2. Cada N segundos hace ping a cada tablet configurada.
 *  3. Notifica cuando una tablet pierde conexión y cuando se recupera.
 */
class MonitorService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val checkNow = Channel<Unit>(Channel.CONFLATED)

    private lateinit var store: PeerStore
    private var loopJob: Job? = null
    private var server: HeartbeatServer? = null
    private var serverPort = -1
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null

    /** Solo se modifica desde el ciclo de monitoreo (una corrutina a la vez). */
    private val statuses = LinkedHashMap<String, PeerStatus>()
    private var localProblem: String? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        store = PeerStore(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            store.monitoringEnabled = false
            ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }

        try {
            ServiceCompat.startForeground(
                this,
                Notifications.ID_FOREGROUND,
                Notifications.foreground(this, getString(R.string.fg_starting)),
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
                } else {
                    0
                },
            )
        } catch (e: Exception) {
            // Android puede bloquear el arranque desde segundo plano si la app
            // no está exenta de la optimización de batería.
            Log.e(TAG, "No se pudo iniciar en primer plano", e)
            stopSelf()
            return START_NOT_STICKY
        }

        store.monitoringEnabled = true
        MonitorState.setRunning(true)
        ensureServer()
        if (loopJob?.isActive != true) {
            acquireLocks()
            loopJob = scope.launch { monitorLoop() }
        } else {
            checkNow.trySend(Unit)
        }
        return START_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        server?.stop()
        server = null
        releaseLocks()
        MonitorState.statuses.value.keys.forEach { Notifications.cancelPeer(this, it) }
        Notifications.cancelLocal(this)
        MonitorState.setRunning(false)
        super.onDestroy()
    }

    /** (Re)inicia el servidor si no existe o si cambió el puerto. */
    private fun ensureServer() {
        val port = store.port
        if (server != null && port == serverPort) return
        server?.stop()
        serverPort = port
        server = HeartbeatServer(
            port = port,
            nameProvider = { store.deviceName },
            onPing = { MonitorState.recordIncoming(it) },
            onError = { MonitorState.setServerError(it) },
        ).also { it.start() }
    }

    private suspend fun monitorLoop() {
        while (scope.isActive) {
            try {
                runCycle()
            } catch (e: Exception) {
                if (e is kotlinx.coroutines.CancellationException) throw e
                Log.e(TAG, "Error en ciclo de monitoreo", e)
            }
            withTimeoutOrNull(store.intervalSec * 1000L) { checkNow.receive() }
        }
    }

    private suspend fun runCycle() {
        val peers = store.peers()
        syncPeers(peers)
        checkLocalNetwork()
        MonitorState.setStatuses(statuses.toMap())

        val myName = store.deviceName
        val port = store.port
        val results = coroutineScope {
            peers.map { peer -> async { peer to PeerChecker.check(peer.host, port, myName) } }.awaitAll()
        }

        val now = System.currentTimeMillis()
        val threshold = store.failThreshold
        val repeatMs = store.repeatAlertMin * 60_000L

        for ((peer, result) in results) {
            val prev = statuses[peer.id] ?: continue // eliminado durante la verificación
            if (prev.peer.host != peer.host) continue // editado durante la verificación
            var next: PeerStatus
            if (result.reachable) {
                next = prev.copy(
                    state = if (result.appOk) PeerState.ONLINE else PeerState.NO_APP,
                    latencyMs = result.latencyMs,
                    remoteName = result.remoteName ?: prev.remoteName,
                    lastSeen = now,
                    lastCheck = now,
                    failures = 0,
                    alerted = false,
                    lastAlertAt = null,
                )
                if (prev.alerted) Notifications.peerRecovered(this, next)
            } else {
                next = prev.copy(
                    state = PeerState.OFFLINE,
                    latencyMs = null,
                    lastCheck = now,
                    failures = prev.failures + 1,
                )
                // Si el problema es de esta tablet, solo se avisa con la alerta local.
                if (localProblem == null && next.failures >= threshold) {
                    val lastAlert = prev.lastAlertAt
                    val shouldAlert = !prev.alerted ||
                        (repeatMs > 0 && lastAlert != null && now - lastAlert >= repeatMs)
                    if (shouldAlert) {
                        Notifications.peerDown(this, next)
                        next = next.copy(alerted = true, lastAlertAt = now)
                    }
                }
            }
            statuses[peer.id] = next
        }

        syncPeers(store.peers())
        MonitorState.setStatuses(statuses.toMap())
        updateForegroundText()
    }

    /** Agrega, actualiza o elimina estados según la lista guardada. */
    private fun syncPeers(peers: List<Peer>) {
        val ids = peers.map { it.id }.toSet()
        statuses.keys.filter { it !in ids }.forEach { id ->
            statuses.remove(id)
            Notifications.cancelPeer(this, id)
        }
        for (peer in peers) {
            val current = statuses[peer.id]
            statuses[peer.id] = when {
                current == null -> PeerStatus(peer)
                current.peer.host != peer.host -> {
                    Notifications.cancelPeer(this, peer.id)
                    PeerStatus(peer)
                }
                else -> current.copy(peer = peer)
            }
        }
    }

    private fun checkLocalNetwork() {
        val problem = when {
            !NetworkUtils.hasUnderlyingNetwork(this) -> getString(R.string.local_no_network)
            !NetworkUtils.isTailscaleUp(this) -> getString(R.string.local_no_tailscale)
            else -> null
        }
        if (problem != null && problem != localProblem) {
            Notifications.localProblem(this, problem)
        } else if (problem == null && localProblem != null) {
            Notifications.localRecovered(this)
        }
        localProblem = problem
    }

    private fun updateForegroundText() {
        val text = localProblem ?: run {
            val total = statuses.size
            if (total == 0) {
                getString(R.string.fg_no_peers)
            } else {
                val online = statuses.values.count {
                    it.state == PeerState.ONLINE || it.state == PeerState.NO_APP
                }
                getString(R.string.fg_summary, online, total, store.intervalSec)
            }
        }
        Notifications.updateForeground(this, text)
    }

    @SuppressLint("WakelockTimeout")
    @Suppress("DEPRECATION")
    private fun acquireLocks() {
        val pm = getSystemService(PowerManager::class.java)
        wakeLock = pm?.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "PingMonitor:monitor")?.apply {
            setReferenceCounted(false)
            acquire()
        }
        val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        wifiLock = wm?.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "PingMonitor:wifi")?.apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun releaseLocks() {
        wakeLock?.takeIf { it.isHeld }?.release()
        wakeLock = null
        wifiLock?.takeIf { it.isHeld }?.release()
        wifiLock = null
    }

    companion object {
        const val ACTION_STOP = "com.mesilsan.pingmonitor.STOP"
        const val ACTION_CHECK_NOW = "com.mesilsan.pingmonitor.CHECK_NOW"
        private const val TAG = "MonitorService"

        fun start(context: Context, action: String? = null) {
            val intent = Intent(context, MonitorService::class.java).setAction(action)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            PeerStore(context).monitoringEnabled = false
            context.stopService(Intent(context, MonitorService::class.java))
        }
    }
}
