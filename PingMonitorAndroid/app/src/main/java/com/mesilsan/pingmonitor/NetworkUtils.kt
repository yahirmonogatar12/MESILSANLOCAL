package com.mesilsan.pingmonitor

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import java.net.Inet4Address
import java.net.NetworkInterface

object NetworkUtils {

    /** IP de Tailscale (rango 100.64.0.0/10) de este dispositivo, si existe. */
    fun tailscaleIp(): String? {
        return try {
            NetworkInterface.getNetworkInterfaces()?.toList().orEmpty()
                .filter { it.isUp }
                .flatMap { it.inetAddresses.toList() }
                .filterIsInstance<Inet4Address>()
                .firstOrNull { isTailscale(it) }
                ?.hostAddress
        } catch (e: Exception) {
            null
        }
    }

    private fun isTailscale(address: Inet4Address): Boolean {
        val bytes = address.address
        val first = bytes[0].toInt() and 0xFF
        val second = bytes[1].toInt() and 0xFF
        return first == 100 && second in 64..127
    }

    /** true si hay alguna red física (Wi‑Fi, Ethernet, datos) conectada. */
    @Suppress("DEPRECATION")
    fun hasUnderlyingNetwork(context: Context): Boolean {
        val cm = context.getSystemService(ConnectivityManager::class.java) ?: return false
        return cm.allNetworks.any { network ->
            val caps = cm.getNetworkCapabilities(network) ?: return@any false
            !caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN) &&
                caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
        }
    }

    /** true si Tailscale (VPN) está activo en este dispositivo. */
    @Suppress("DEPRECATION")
    fun isTailscaleUp(context: Context): Boolean {
        if (tailscaleIp() != null) return true
        val cm = context.getSystemService(ConnectivityManager::class.java) ?: return false
        return cm.allNetworks.any { network ->
            cm.getNetworkCapabilities(network)?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) == true
        }
    }
}
