package com.mesilsan.pingmonitor

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.isVisible
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.GridLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.mesilsan.pingmonitor.databinding.ActivityMainBinding
import com.mesilsan.pingmonitor.databinding.DialogPeerBinding
import com.mesilsan.pingmonitor.databinding.DialogSettingsBinding
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var store: PeerStore
    private lateinit var adapter: PeerAdapter
    private var updatingSwitch = false

    private val notificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (!granted) openNotificationSettings()
            render()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        store = PeerStore(this)
        adapter = PeerAdapter(onClick = { showPeerDialog(it) })
        binding.peerList.layoutManager =
            GridLayoutManager(this, resources.getInteger(R.integer.grid_columns))
        binding.peerList.adapter = adapter

        binding.fabAdd.setOnClickListener { showPeerDialog(null) }
        binding.btnNotifications.setOnClickListener { requestNotifications() }
        binding.btnBattery.setOnClickListener { requestBatteryExemption() }
        binding.switchMonitoring.setOnCheckedChangeListener { _, checked ->
            if (updatingSwitch) return@setOnCheckedChangeListener
            if (checked) startMonitoring() else MonitorService.stop(this)
        }

        if (savedInstanceState == null) {
            if (!Notifications.canNotify(this)) requestNotifications()
            // Si estaba activo (p. ej. la app fue cerrada a la fuerza), reanudar.
            if (store.monitoringEnabled && !MonitorState.running.value) startMonitoring()
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch { MonitorState.running.collect { render() } }
                launch { MonitorState.statuses.collect { render() } }
                launch { MonitorState.incoming.collect { render() } }
                launch { MonitorState.serverError.collect { render() } }
                launch {
                    // Refresca "hace X segundos" y la IP de Tailscale.
                    while (true) {
                        delay(2000)
                        render()
                    }
                }
            }
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean = when (item.itemId) {
        R.id.action_check_now -> {
            if (MonitorState.running.value) {
                MonitorService.start(this, MonitorService.ACTION_CHECK_NOW)
            } else {
                Toast.makeText(this, R.string.monitoring_off_hint, Toast.LENGTH_SHORT).show()
            }
            true
        }
        R.id.action_settings -> {
            showSettingsDialog()
            true
        }
        else -> super.onOptionsItemSelected(item)
    }

    private fun render() {
        val running = MonitorState.running.value

        binding.deviceName.text = store.deviceName
        binding.tailscaleIp.text = NetworkUtils.tailscaleIp()
            ?.let { getString(R.string.tailscale_ip, it) }
            ?: getString(R.string.tailscale_ip_missing)
        binding.port.text = getString(R.string.listening_port, store.port)
        val serverError = MonitorState.serverError.value
        binding.serverError.isVisible = running && serverError != null
        binding.serverError.text = getString(R.string.server_error, serverError ?: "")

        updatingSwitch = true
        binding.switchMonitoring.isChecked = running
        updatingSwitch = false

        val needsNotifications = !Notifications.canNotify(this)
        val needsBattery = !isIgnoringBatteryOptimizations()
        binding.warningsCard.isVisible = needsNotifications || needsBattery
        binding.btnNotifications.isVisible = needsNotifications
        binding.btnBattery.isVisible = needsBattery

        val statuses = MonitorState.statuses.value
        val incoming = MonitorState.incoming.value.values
        val threshold = store.failThreshold
        val rows = store.peers().map { peer ->
            val status = statuses[peer.id]?.takeIf { it.peer.host == peer.host }
                ?.copy(peer = peer) ?: PeerStatus(peer)
            val fromPeer = incoming
                .filter { normalize(it.address) == peer.host || (status.remoteName != null && it.name == status.remoteName) }
                .maxByOrNull { it.time }
            PeerRow(status, fromPeer, running, threshold)
        }
        adapter.submit(rows)
        binding.emptyText.isVisible = rows.isEmpty()
    }

    private fun normalize(address: String) = address.removePrefix("::ffff:").substringBefore('%')

    private fun startMonitoring() {
        if (store.peers().isEmpty()) {
            Toast.makeText(this, R.string.no_peers_hint, Toast.LENGTH_LONG).show()
        }
        MonitorService.start(this)
    }

    private fun reloadService() {
        if (MonitorState.running.value) MonitorService.start(this, MonitorService.ACTION_CHECK_NOW)
        render()
    }

    private fun showPeerDialog(peer: Peer?) {
        val dialogBinding = DialogPeerBinding.inflate(layoutInflater)
        peer?.let {
            dialogBinding.inputName.setText(it.name)
            dialogBinding.inputHost.setText(it.host)
        }
        val builder = MaterialAlertDialogBuilder(this)
            .setTitle(if (peer == null) R.string.add_peer else R.string.edit_peer)
            .setView(dialogBinding.root)
            .setPositiveButton(R.string.save, null)
            .setNegativeButton(R.string.cancel, null)
        if (peer != null) {
            builder.setNeutralButton(R.string.delete) { _, _ -> confirmDelete(peer) }
        }
        val dialog = builder.create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val name = dialogBinding.inputName.text?.toString()?.trim().orEmpty()
                val host = dialogBinding.inputHost.text?.toString()?.trim().orEmpty()
                dialogBinding.layoutName.error =
                    if (name.isEmpty()) getString(R.string.error_required) else null
                dialogBinding.layoutHost.error = when {
                    host.isEmpty() -> getString(R.string.error_required)
                    !HOST_REGEX.matches(host) -> getString(R.string.error_host)
                    else -> null
                }
                if (dialogBinding.layoutName.error != null || dialogBinding.layoutHost.error != null) {
                    return@setOnClickListener
                }
                if (peer == null) {
                    store.addPeer(name, host)
                } else {
                    store.updatePeer(peer.copy(name = name, host = host))
                }
                dialog.dismiss()
                reloadService()
            }
        }
        dialog.show()
    }

    private fun confirmDelete(peer: Peer) {
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.delete_peer_title)
            .setMessage(getString(R.string.delete_peer_message, peer.name))
            .setPositiveButton(R.string.delete) { _, _ ->
                store.removePeer(peer.id)
                Notifications.cancelPeer(this, peer.id)
                reloadService()
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }

    private fun showSettingsDialog() {
        val d = DialogSettingsBinding.inflate(layoutInflater)
        d.inputDeviceName.setText(store.deviceName)
        d.inputInterval.setText(store.intervalSec.toString())
        d.inputThreshold.setText(store.failThreshold.toString())
        d.inputRepeat.setText(store.repeatAlertMin.toString())
        d.inputPort.setText(store.port.toString())

        val dialog = MaterialAlertDialogBuilder(this)
            .setTitle(R.string.settings)
            .setView(d.root)
            .setPositiveButton(R.string.save, null)
            .setNegativeButton(R.string.cancel, null)
            .create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val name = d.inputDeviceName.text?.toString()?.trim().orEmpty()
                val interval = d.inputInterval.text?.toString()?.toIntOrNull()
                val threshold = d.inputThreshold.text?.toString()?.toIntOrNull()
                val repeat = d.inputRepeat.text?.toString()?.toIntOrNull()
                val port = d.inputPort.text?.toString()?.toIntOrNull()

                d.layoutDeviceName.error = if (name.isEmpty()) getString(R.string.error_required) else null
                d.layoutInterval.error =
                    if (interval == null || interval < PeerStore.MIN_INTERVAL || interval > PeerStore.MAX_INTERVAL) {
                        getString(R.string.error_range, PeerStore.MIN_INTERVAL, PeerStore.MAX_INTERVAL)
                    } else null
                d.layoutThreshold.error =
                    if (threshold == null || threshold !in 1..100) getString(R.string.error_range, 1, 100) else null
                d.layoutRepeat.error =
                    if (repeat == null || repeat !in 0..1440) getString(R.string.error_range, 0, 1440) else null
                d.layoutPort.error =
                    if (port == null || port !in 1024..65535) getString(R.string.error_range, 1024, 65535) else null
                if (listOf(d.layoutDeviceName, d.layoutInterval, d.layoutThreshold, d.layoutRepeat, d.layoutPort)
                        .any { it.error != null }
                ) {
                    return@setOnClickListener
                }

                store.deviceName = name
                store.intervalSec = interval!!
                store.failThreshold = threshold!!
                store.repeatAlertMin = repeat!!
                store.port = port!!
                dialog.dismiss()
                reloadService()
            }
        }
        dialog.show()
    }

    private fun requestNotifications() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            openNotificationSettings()
        }
    }

    private fun openNotificationSettings() {
        val intent = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
        try {
            startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
        }
    }

    private fun isIgnoringBatteryOptimizations(): Boolean =
        getSystemService(PowerManager::class.java)?.isIgnoringBatteryOptimizations(packageName) ?: true

    private fun requestBatteryExemption() {
        try {
            startActivity(
                Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName"))
            )
        } catch (e: ActivityNotFoundException) {
            try {
                startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
            } catch (_: ActivityNotFoundException) {
            }
        }
    }

    companion object {
        /** IPv4, IPv6 o nombre MagicDNS. */
        private val HOST_REGEX = Regex("^[A-Za-z0-9.:\\-]+$")
    }
}
