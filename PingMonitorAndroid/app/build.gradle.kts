plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.mesilsan.pingmonitor"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.mesilsan.pingmonitor"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            // Firma con la llave debug para poder instalar el APK release directamente
            // en las tablets sin configurar un keystore. Cámbialo si publicas la app.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

// Sin dependencias externas: solo APIs de Android y la librería estándar de Kotlin.
