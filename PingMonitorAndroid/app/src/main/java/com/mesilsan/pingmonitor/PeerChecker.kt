package com.mesilsan.pingmonitor

import android.os.SystemClock
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.Callable
import java.util.concurrent.ExecutorService
import java.util.concurrent.TimeUnit
import kotlin.math.roundToLong

/**
 * Verifica si otro dispositivo es alcanzable:
 *  - Ping ICMP (comando `ping` del sistema, no requiere root).
 *  - "Ping" de aplicación: conexión TCP al [HeartbeatServer] de la otra tablet.
 */
object PeerChecker {

    data class Result(
        val icmpMs: Long?,
        val appMs: Long?,
        val remoteName: String?,
    ) {
        val reachable get() = icmpMs != null || appMs != null
        val appOk get() = appMs != null
        val latencyMs get() = icmpMs ?: appMs
    }

    /** Ejecuta ambas pruebas en paralelo usando [executor]. */
    fun check(executor: ExecutorService, host: String, port: Int, myName: String, timeoutMs: Int = 3000): Result {
        val icmp = executor.submit(Callable { icmpPing(host, timeoutMs) })
        val app = appPing(host, port, myName, timeoutMs)
        val icmpMs = try {
            icmp.get((timeoutMs + 5000).toLong(), TimeUnit.MILLISECONDS)
        } catch (e: Exception) {
            icmp.cancel(true)
            null
        }
        return Result(icmpMs, app?.first, app?.second)
    }

    /** Devuelve la latencia en ms, o null si no respondió. */
    private fun icmpPing(host: String, timeoutMs: Int): Long? {
        val timeoutSec = (timeoutMs / 1000).coerceAtLeast(1)
        val start = SystemClock.elapsedRealtime()
        return try {
            val process = ProcessBuilder("ping", "-c", "1", "-W", timeoutSec.toString(), host)
                .redirectErrorStream(true)
                .start()
            if (!process.waitFor(timeoutSec + 3L, TimeUnit.SECONDS)) {
                process.destroy()
                return null
            }
            val output = process.inputStream.bufferedReader().use { it.readText() }
            if (process.exitValue() != 0) return null
            Regex("time[=<]\\s*([0-9.]+)").find(output)
                ?.groupValues?.get(1)?.toDoubleOrNull()?.roundToLong()
                ?: (SystemClock.elapsedRealtime() - start)
        } catch (e: InterruptedException) {
            null
        } catch (e: Exception) {
            // Si el comando ping no existe en el dispositivo, usar el método de Java.
            try {
                if (InetAddress.getByName(host).isReachable(timeoutMs)) {
                    SystemClock.elapsedRealtime() - start
                } else {
                    null
                }
            } catch (e2: Exception) {
                null
            }
        }
    }

    /** Devuelve (latencia ms, nombre remoto) o null si la app remota no contestó. */
    private fun appPing(host: String, port: Int, myName: String, timeoutMs: Int): Pair<Long, String>? {
        return try {
            Socket().use { socket ->
                val start = SystemClock.elapsedRealtime()
                socket.connect(InetSocketAddress(host, port), timeoutMs)
                socket.soTimeout = timeoutMs
                val writer = socket.getOutputStream().bufferedWriter()
                writer.write("${HeartbeatServer.PING} ${sanitize(myName)}\n")
                writer.flush()
                val line = socket.getInputStream().bufferedReader().readLine() ?: return null
                if (!line.startsWith(HeartbeatServer.PONG)) return null
                val elapsed = SystemClock.elapsedRealtime() - start
                elapsed to line.removePrefix(HeartbeatServer.PONG).trim()
            }
        } catch (e: Exception) {
            null
        }
    }

    fun sanitize(name: String): String =
        name.replace(Regex("[\\r\\n]"), " ").trim().take(64)
}
