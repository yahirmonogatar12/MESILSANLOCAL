package com.mesilsan.pingmonitor

import android.util.Log
import java.io.IOException
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Servidor TCP mínimo: responde "PONG <nombre>" a cada "PING <nombre>".
 * Así la otra tablet sabe que este dispositivo y la app siguen activos.
 */
class HeartbeatServer(
    private val port: Int,
    private val nameProvider: () -> String,
    private val onPing: (IncomingPing) -> Unit,
    private val onError: (String?) -> Unit,
) {
    @Volatile
    private var serverSocket: ServerSocket? = null

    @Volatile
    private var stopped = false

    private val executor: ExecutorService = Executors.newCachedThreadPool()

    fun start() {
        executor.execute {
            try {
                val ss = ServerSocket().apply {
                    reuseAddress = true
                    bind(InetSocketAddress(port))
                }
                serverSocket = ss
                onError(null)
                while (!stopped) {
                    val client = ss.accept()
                    executor.execute { handle(client) }
                }
            } catch (e: IOException) {
                if (!stopped) {
                    Log.e(TAG, "Error en servidor", e)
                    onError(e.message ?: e.javaClass.simpleName)
                }
            } catch (e: java.util.concurrent.RejectedExecutionException) {
                // Servidor detenido mientras aceptaba una conexión.
            }
        }
    }

    private fun handle(client: Socket) {
        try {
            client.use { socket ->
                socket.soTimeout = 5000
                val line = socket.getInputStream().bufferedReader().readLine() ?: return
                if (!line.startsWith(PING)) return
                val writer = socket.getOutputStream().bufferedWriter()
                writer.write("$PONG ${PeerChecker.sanitize(nameProvider())}\n")
                writer.flush()
                val address = socket.inetAddress?.hostAddress ?: "?"
                onPing(IncomingPing(address, line.removePrefix(PING).trim(), System.currentTimeMillis()))
            }
        } catch (e: IOException) {
            // Cliente se desconectó; no es importante.
        }
    }

    fun stop() {
        stopped = true
        try {
            serverSocket?.close()
        } catch (_: IOException) {
        }
        executor.shutdownNow()
    }

    companion object {
        const val PING = "PING"
        const val PONG = "PONG"
        private const val TAG = "HeartbeatServer"
    }
}
