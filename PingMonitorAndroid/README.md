# Ping Monitor (Android · Kotlin)

App para tablets/teléfonos Android que vigila si **otra tablet responde al ping
por Tailscale** y **manda una notificación cuando una pierde conexión** (y otra
cuando se recupera).

Se instala la misma app en ambas tablets; cada una vigila a la otra, así que la
comunicación es en los dos sentidos.

## Cómo funciona

Cada tablet corre un servicio en primer plano que:

1. **Escucha** en el puerto TCP `47800` y contesta `PONG <nombre>` a cada
   `PING <nombre>` que le llega de la otra tablet.
2. **Cada N segundos (10 por defecto)** verifica cada dispositivo configurado con:
   - Ping ICMP real (comando `ping` del sistema, no requiere root).
   - Ping de aplicación (TCP al puerto 47800 de la otra tablet).
3. Tras **N fallos seguidos (3 por defecto)** lanza una notificación de alta
   prioridad con sonido y vibración: `⚠ Sin conexión: Tablet X`.
4. Cuando vuelve a responder, reemplaza la alerta con `✓ Conexión recuperada`.
5. Si quien perdió la red es **esta** tablet (sin Wi‑Fi o Tailscale apagado),
   avisa con `⚠ Esta tablet perdió conexión` en lugar de culpar a la otra.

Estados que muestra la pantalla por dispositivo:

| Color | Estado | Significado |
|---|---|---|
| 🟢 | En línea | Responde al ping y la app del otro lado contesta |
| 🟢 | En línea (ping) | Responde al ping; el equipo no tiene la app (PC, otro Android…) |
| 🟡 | Sin respuesta (1/3) | Falló, aún no llega al límite para alertar |
| 🔴 | SIN CONEXIÓN | Se envió la notificación de desconexión |

También muestra cuándo fue la última vez que **la otra tablet nos hizo ping**,
para confirmar que la comunicación funciona en ambos sentidos.

## Instalación

1. Instala y conecta **Tailscale** en ambas tablets (misma tailnet).
2. Instala el APK en ambas tablets (ver "Compilar").
3. Abre la app en cada tablet:
   - Arriba aparece **su propia IP de Tailscale** (100.x.x.x).
   - Toca **Permitir notificaciones** y **Quitar optimización de batería**
     (necesario para que siga funcionando con la pantalla apagada y arranque
     sola al reiniciar).
   - Toca **+ Agregar** y escribe el nombre e IP de Tailscale (o el
     nombre MagicDNS) de la **otra** tablet.
   - Activa **Monitoreo activo**.

El monitoreo se reinicia solo al encender la tablet.

### Configuración (ícono ⚙)

- Nombre de este dispositivo (lo que verá la otra tablet).
- Intervalo de verificación (3–3600 s).
- Fallos seguidos antes de alertar (evita falsas alarmas por un ping perdido).
- Repetir la alerta cada X minutos mientras siga caído (0 = solo una vez).
- Puerto (debe ser el mismo en todas las tablets).

## Compilar

### Opción A: Android Studio

Abre la carpeta del proyecto en Android Studio (Koala o más reciente)
y ejecuta **Run** o **Build › Build APK(s)**.

### Opción B: línea de comandos

```bash
cd PingMonitorAndroid
./gradlew assembleRelease
# APK: app/build/outputs/apk/release/app-release.apk
```

Requiere JDK 17 y el Android SDK (plataforma 34).

### Opción C: GitHub Actions

El workflow `.github/workflows/ping-monitor-android.yml` compila la app en cada
push que cambie esta carpeta. El APK se descarga desde la pestaña **Actions** →
la ejecución → artefacto **PingMonitor-apk**.

> Si instalas un APK firmado con otra llave (p. ej. el compilado por Claude y
> luego uno de Android Studio), desinstala primero la versión anterior.
>
> El APK release se firma con la llave *debug* para poder instalarlo directo
> (sideload). Si se va a publicar, configura un keystore propio en
> `app/build.gradle.kts`.

## Dependencias

Ninguna librería externa: solo APIs de Android y la librería estándar de
Kotlin (sin AndroidX ni Material). Así el APK es pequeño (~0.8 MB) y se puede
compilar incluso sin acceso al repositorio Maven de Google.

## Requisitos

- Android 8.0 (API 26) o superior. Diseño adaptable a tablet (2–3 columnas en
  pantallas grandes) y a teléfono.
- Tailscale instalado y conectado en ambos dispositivos.

## Estructura

```
app/src/main/java/com/mesilsan/pingmonitor/
├── MainActivity.kt      Pantalla principal, tarjetas de estado y diálogos
├── MonitorService.kt    Servicio en primer plano: ciclo de ping + alertas
├── HeartbeatServer.kt   Servidor TCP que responde PONG
├── PeerChecker.kt       Ping ICMP + ping TCP de aplicación
├── Notifications.kt     Canales y notificaciones
├── NetworkUtils.kt      IP de Tailscale y estado de la red local
├── PeerStore.kt         Configuración guardada (SharedPreferences)
├── MonitorState.kt      Estado compartido servicio ↔ pantalla
├── BootReceiver.kt      Reinicia el monitoreo al encender
└── Models.kt
```
