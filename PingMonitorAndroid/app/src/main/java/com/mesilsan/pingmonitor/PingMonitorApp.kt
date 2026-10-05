package com.mesilsan.pingmonitor

import android.app.Application

class PingMonitorApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Notifications.createChannels(this)
    }
}
