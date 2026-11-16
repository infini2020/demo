// Android 4.4 (API 19) legacy shim for erika_flutter's ErikaMediaSession.
//
// Upstream ErikaMediaSession is built entirely on API 21+/26+ types:
//   android.media.session.MediaSession        (API 21)
//   android.media.session.PlaybackState       (API 21)
//   android.media.MediaMetadata               (API 21)
//   NotificationChannel                       (API 26)
//   Notification.MediaStyle                   (API 21)
//
// ErikaFlutterPlugin constructs it unconditionally in onAttachedToEngine, so on
// API 19 plugin registration aborts with:
//   java.lang.NoClassDefFoundError: android.media.session.MediaSession
//     at dev.aimesoft.erika_flutter.ErikaMediaSession.<init>
//     at dev.aimesoft.erika_flutter.ErikaFlutterPlugin.onAttachedToEngine
//     at io.flutter.plugins.GeneratedPluginRegistrant.registerWith
//
// GeneratedPluginRegistrant throws there, so every plugin registered after
// erika_flutter is skipped and the Dart side blocks before the first frame —
// the app launches into a permanent black screen.
//
// This shim keeps the exact public surface the plugin uses (constructor,
// update/dispatch/clear/release and the companion constants referenced by
// ErikaMediaCommandReceiver and AndroidEventPollPolicy) but performs no work,
// so media-session notifications/transport controls are simply unavailable in
// the 4.4 build. Only injected for NIPAPLAY_LEGACY builds.

package dev.aimesoft.erika_flutter

import android.content.Context

internal interface ErikaMediaCommandHandler {
    fun play(playerId: Long)
    fun pause(playerId: Long)
    fun stop(playerId: Long)
    fun seek(playerId: Long, positionMicros: Long)
    fun previous(playerId: Long)
    fun next(playerId: Long)
}

internal class ErikaMediaSession(
    @Suppress("UNUSED_PARAMETER") context: Context,
    @Suppress("UNUSED_PARAMETER") private val commands: ErikaMediaCommandHandler,
) {
    fun update(state: AndroidMediaState) {
        // No media session / notification support on API 19.
    }

    fun dispatch(action: String) {
        // No media session / notification support on API 19.
    }

    fun clear(playerId: Long) {
        // No media session / notification support on API 19.
    }

    fun release() {
        // No media session / notification support on API 19.
    }

    companion object {
        const val ACTION_PLAY = "dev.aimesoft.erika_flutter.action.PLAY"
        const val ACTION_PAUSE = "dev.aimesoft.erika_flutter.action.PAUSE"
        const val ACTION_STOP = "dev.aimesoft.erika_flutter.action.STOP"
        const val PLAYING_STATE = 3
        const val CLOSED_STATE = 6
        const val ERROR_STATE = 7
    }
}
