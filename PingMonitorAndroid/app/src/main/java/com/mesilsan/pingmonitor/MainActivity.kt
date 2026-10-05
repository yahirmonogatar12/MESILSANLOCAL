package com.mesilsan.pingmonitor

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.provider.Settings
import android.text.format.DateUtils
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {

    private lateinit var store: PeerStore

    private lateinit var deviceName: TextView
    private lateinit var tailscaleIp: TextView
    private lateinit var portText: TextView
    private lateinit var serverError: TextView
    private lateinit var switchMonitoring: Switch
    private lateinit var warningsCard: View
    private lateinit var btnNotifications: Button
    private lateinit var btnBattery: Button
    private lateinit var peersContainer: LinearLayout
    private lateinit var emptyText: TextView

    private var updatingSwitch = false
    private var openSettingsIfDenied = false

    private val handler = Handler(Looper.getMainLooper())
    private val stateListener: () -> Unit = { render() }
    private val ticker = object : Runnable {
        override fun run() {
            // Refresca "hace X segundos" y la IP de Tailscale.
            render()
            handler.postDelayed(this, 2000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        store = PeerStore(this)

        deviceName = findViewById(R.id.deviceName)
        tailscaleIp = findViewById(R.id.tailscaleIp)
        portText = findViewById(R.id.port)
        serverError = findViewById(R.id.serverError)
        switchMonitoring = findViewById(R.id.switchMonitoring)
        warningsCard = findViewById(R.id.warningsCard)
        btnNotifications = findViewById(R.id.btnNotifications)
        btnBattery = findViewById(R.id.btnBattery)
        peersContainer = findViewById(R.id.peersContainer)
        emptyText = findViewById(R.id.emptyText)

        findViewById<Button>(R.id.btnAdd).setOnClickListener { showPeerDialog(null) }
        btnNotifications.setOnClickListener {
            openSettingsIfDenied = true
            requestNotifications()
        }
        btnBattery.setOnClickListener { requestBatteryExemption() }
        switchMonitoring.setOnCheckedChangeListener { _, checked ->
            if (updatingSwitch) return@setOnCheckedChangeListener
            if (checked) startMonitoring() else MonitorService.stop(this)
        }

        if (savedInstanceState == null) {
            if (!Notifications.canNotify(this)) requestNotifications()
            // Si estaba activo (p. ej. la app fue cerrada a la fuerza), reanudar.
            if (store.monitoringEnabled && !MonitorState.running) startMonitoring()
        }
    }

    override fun onStart() {
        super.onStart()
        MonitorState.addListener(stateListener)
        handler.post(ticker)
    }

    override fun onStop() {
        MonitorState.removeListener(stateListener)
        handler.removeCallbacks(ticker)
        super.onStop()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean = when (item.itemId) {
        R.id.action_check_now -> {
            if (MonitorState.running) {
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

    @Deprecated("Deprecated in Java")
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_NOTIFICATIONS) {
            val granted = grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
            if (!granted && openSettingsIfDenied) openNotificationSettings()
            openSettingsIfDenied = false
            render()
        }
    }

    private fun render() {
        val running = MonitorState.running

        deviceName.text = store.deviceName
        tailscaleIp.text = NetworkUtils.tailscaleIp()
            ?.let { getString(R.string.tailscale_ip, it) }
            ?: getString(R.string.tailscale_ip_missing)
        portText.text = getString(R.string.listening_port, store.port)
        val error = MonitorState.serverError
        serverError.visibility = if (running && error != null) View.VISIBLE else View.GONE
        serverError.text = getString(R.string.server_error, error ?: "")

        updatingSwitch = true
        switchMonitoring.isChecked = running
        updatingSwitch = false

        val needsNotifications = !Notifications.canNotify(this)
        val needsBattery = !isIgnoringBatteryOptimizations()
        warningsCard.visibility = if (needsNotifications || needsBattery) View.VISIBLE else View.GONE
        btnNotifications.visibility = if (needsNotifications) View.VISIBLE else View.GONE
        btnBattery.visibility = if (needsBattery) View.VISIBLE else View.GONE

        val statuses = MonitorState.statuses
        val incoming = MonitorState.incoming.values
        val threshold = store.failThreshold
        val peers = store.peers()
        val columns = resources.getInteger(R.integer.grid_columns).coerceAtLeast(1)

        peersContainer.removeAllViews()
        peers.chunked(columns).forEach { chunk ->
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            for (i in 0 until columns) {
                val peer = chunk.getOrNull(i)
                val cell = if (peer == null) {
                    View(this)
                } else {
                    val status = statuses[peer.id]?.takeIf { it.peer.host == peer.host }
                        ?.copy(peer = peer) ?: PeerStatus(peer)
                    val fromPeer = incoming
                        .filter {
                            normalize(it.address) == peer.host ||
                                (status.remoteName != null && it.name == status.remoteName)
                        }
                        .maxByOrNull { it.time }
                    peerCard(row, status, fromPeer, running, threshold)
                }
                row.addView(cell, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            }
            peersContainer.addView(row)
        }
        emptyText.visibility = if (peers.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun peerCard(
        parent: LinearLayout,
        s: PeerStatus,
        incoming: IncomingPing?,
        running: Boolean,
        threshold: Int,
    ): View {
        val card = layoutInflater.inflate(R.layout.item_peer, parent, false)
        val now = System.currentTimeMillis()

        card.findViewById<TextView>(R.id.name).text = s.peer.name
        card.findViewById<TextView>(R.id.host).text = s.peer.host
        card.findViewById<TextView>(R.id.remoteName).apply {
            visibility = if (s.remoteName != null) View.VISIBLE else View.GONE
            text = getString(R.string.remote_name, s.remoteName ?: "")
        }

        val (color, label) = when {
            !running -> R.color.status_unknown to getString(R.string.state_stopped)
            s.state == PeerState.UNKNOWN -> R.color.status_unknown to getString(R.string.state_checking)
            s.state == PeerState.ONLINE -> R.color.status_online to getString(R.string.state_online)
            // Responde al ping aunque no tenga la app (PC, otro Android, etc.): está en línea.
            s.state == PeerState.NO_APP -> R.color.status_online to getString(R.string.state_online_ping)
            s.alerted -> R.color.status_offline to getString(R.string.state_offline)
            else -> R.color.status_warning to getString(R.string.state_failing, s.failures, threshold)
        }
        val colorInt = getColor(color)
        card.findViewById<View>(R.id.statusDot).backgroundTintList = ColorStateList.valueOf(colorInt)
        card.findViewById<TextView>(R.id.state).apply {
            text = label
            setTextColor(colorInt)
        }
        card.findViewById<TextView>(R.id.latency).apply {
            visibility = if (running && s.latencyMs != null) View.VISIBLE else View.GONE
            text = getString(R.string.latency_ms, s.latencyMs ?: 0L)
        }
        card.findViewById<TextView>(R.id.lastSeen).text = s.lastSeen
            ?.let { getString(R.string.last_seen, relative(it, now)) }
            ?: getString(R.string.last_seen_never)
        card.findViewById<TextView>(R.id.incoming).text = incoming
            ?.let { getString(R.string.incoming_seen, relative(it.time, now)) }
            ?: getString(R.string.incoming_never)

        card.setOnClickListener { showPeerDialog(s.peer) }
        return card
    }

    private fun relative(time: Long, now: Long): CharSequence =
        DateUtils.getRelativeTimeSpanString(time.coerceAtMost(now), now, DateUtils.SECOND_IN_MILLIS)

    private fun normalize(address: String) = address.removePrefix("::ffff:").substringBefore('%')

    private fun startMonitoring() {
        if (store.peers().isEmpty()) {
            Toast.makeText(this, R.string.no_peers_hint, Toast.LENGTH_LONG).show()
        }
        MonitorService.start(this)
    }

    private fun reloadService() {
        if (MonitorState.running) MonitorService.start(this, MonitorService.ACTION_CHECK_NOW)
        render()
    }

    private fun showPeerDialog(peer: Peer?) {
        val view = layoutInflater.inflate(R.layout.dialog_peer, null)
        val inputName = view.findViewById<EditText>(R.id.inputName)
        val inputHost = view.findViewById<EditText>(R.id.inputHost)
        peer?.let {
            inputName.setText(it.name)
            inputHost.setText(it.host)
        }
        val builder = AlertDialog.Builder(this)
            .setTitle(if (peer == null) R.string.add_peer else R.string.edit_peer)
            .setView(view)
            .setPositiveButton(R.string.save, null)
            .setNegativeButton(R.string.cancel, null)
        if (peer != null) {
            builder.setNeutralButton(R.string.delete) { _, _ -> confirmDelete(peer) }
        }
        val dialog = builder.create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val name = inputName.text.toString().trim()
                val host = inputHost.text.toString().trim()
                var ok = true
                if (name.isEmpty()) {
                    inputName.error = getString(R.string.error_required)
                    ok = false
                }
                if (host.isEmpty()) {
                    inputHost.error = getString(R.string.error_required)
                    ok = false
                } else if (!HOST_REGEX.matches(host)) {
                    inputHost.error = getString(R.string.error_host)
                    ok = false
                }
                if (!ok) return@setOnClickListener
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
        AlertDialog.Builder(this)
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
        val view = layoutInflater.inflate(R.layout.dialog_settings, null)
        val inputDeviceName = view.findViewById<EditText>(R.id.inputDeviceName)
        val inputInterval = view.findViewById<EditText>(R.id.inputInterval)
        val inputThreshold = view.findViewById<EditText>(R.id.inputThreshold)
        val inputRepeat = view.findViewById<EditText>(R.id.inputRepeat)
        val inputPort = view.findViewById<EditText>(R.id.inputPort)
        inputDeviceName.setText(store.deviceName)
        inputInterval.setText(store.intervalSec.toString())
        inputThreshold.setText(store.failThreshold.toString())
        inputRepeat.setText(store.repeatAlertMin.toString())
        inputPort.setText(store.port.toString())

        val dialog = AlertDialog.Builder(this)
            .setTitle(R.string.settings)
            .setView(view)
            .setPositiveButton(R.string.save, null)
            .setNegativeButton(R.string.cancel, null)
            .create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val name = inputDeviceName.text.toString().trim()
                if (name.isEmpty()) inputDeviceName.error = getString(R.string.error_required)
                val interval = readInt(inputInterval, PeerStore.MIN_INTERVAL, PeerStore.MAX_INTERVAL)
                val threshold = readInt(inputThreshold, 1, 100)
                val repeat = readInt(inputRepeat, 0, 1440)
                val port = readInt(inputPort, 1024, 65535)
                if (name.isEmpty() || interval == null || threshold == null || repeat == null || port == null) {
                    return@setOnClickListener
                }
                store.deviceName = name
                store.intervalSec = interval
                store.failThreshold = threshold
                store.repeatAlertMin = repeat
                store.port = port
                dialog.dismiss()
                reloadService()
            }
        }
        dialog.show()
    }

    /** Lee un entero en [min, max]; si no es válido marca el error y devuelve null. */
    private fun readInt(input: EditText, min: Int, max: Int): Int? {
        val value = input.text.toString().trim().toIntOrNull()
        return if (value == null || value < min || value > max) {
            input.error = getString(R.string.error_range, min, max)
            null
        } else {
            value
        }
    }

    private fun requestNotifications() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQUEST_NOTIFICATIONS)
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

    @Suppress("BatteryLife")
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
        private const val REQUEST_NOTIFICATIONS = 10

        /** IPv4, IPv6 o nombre MagicDNS. */
        private val HOST_REGEX = Regex("^[A-Za-z0-9.:\\-]+$")
    }
}
