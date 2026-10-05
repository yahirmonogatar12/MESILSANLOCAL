package com.mesilsan.pingmonitor

import android.annotation.SuppressLint
import android.content.res.ColorStateList
import android.text.format.DateUtils
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.core.view.isVisible
import androidx.recyclerview.widget.RecyclerView
import com.mesilsan.pingmonitor.databinding.ItemPeerBinding

data class PeerRow(
    val status: PeerStatus,
    val incoming: IncomingPing?,
    val running: Boolean,
    val threshold: Int,
)

class PeerAdapter(
    private val onClick: (Peer) -> Unit,
) : RecyclerView.Adapter<PeerAdapter.ViewHolder>() {

    private var rows: List<PeerRow> = emptyList()

    @SuppressLint("NotifyDataSetChanged")
    fun submit(newRows: List<PeerRow>) {
        rows = newRows
        // Pocas filas y los tiempos relativos cambian siempre: refrescar todo es suficiente.
        notifyDataSetChanged()
    }

    override fun getItemCount() = rows.size

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        ViewHolder(ItemPeerBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun onBindViewHolder(holder: ViewHolder, position: Int) = holder.bind(rows[position])

    inner class ViewHolder(private val b: ItemPeerBinding) : RecyclerView.ViewHolder(b.root) {

        fun bind(row: PeerRow) {
            val ctx = b.root.context
            val s = row.status
            val now = System.currentTimeMillis()

            b.name.text = s.peer.name
            b.host.text = s.peer.host
            b.remoteName.isVisible = s.remoteName != null
            b.remoteName.text = ctx.getString(R.string.remote_name, s.remoteName ?: "")

            val (color, label) = when {
                !row.running -> R.color.status_unknown to ctx.getString(R.string.state_stopped)
                s.state == PeerState.UNKNOWN -> R.color.status_unknown to ctx.getString(R.string.state_checking)
                s.state == PeerState.ONLINE -> R.color.status_online to ctx.getString(R.string.state_online)
                s.state == PeerState.NO_APP -> R.color.status_warning to ctx.getString(R.string.state_no_app)
                s.alerted -> R.color.status_offline to ctx.getString(R.string.state_offline)
                else -> R.color.status_warning to
                    ctx.getString(R.string.state_failing, s.failures, row.threshold)
            }
            val colorInt = ContextCompat.getColor(ctx, color)
            b.statusDot.backgroundTintList = ColorStateList.valueOf(colorInt)
            b.state.text = label
            b.state.setTextColor(colorInt)

            b.latency.isVisible = row.running && s.latencyMs != null
            b.latency.text = ctx.getString(R.string.latency_ms, s.latencyMs ?: 0L)

            b.lastSeen.text = s.lastSeen?.let {
                ctx.getString(R.string.last_seen, relative(it, now))
            } ?: ctx.getString(R.string.last_seen_never)

            b.incoming.text = row.incoming?.let {
                ctx.getString(R.string.incoming_seen, relative(it.time, now))
            } ?: ctx.getString(R.string.incoming_never)

            b.root.setOnClickListener { onClick(s.peer) }
        }

        private fun relative(time: Long, now: Long): CharSequence =
            DateUtils.getRelativeTimeSpanString(
                time.coerceAtMost(now), now, DateUtils.SECOND_IN_MILLIS,
            )
    }
}
