 #pragma once

 #include "expansion.h"

 #include <ESPAsyncWebServer.h>

 namespace deskcar {

 // Bind all HTTP + WS routes to the AsyncWebServer.
 //
 // Backwards-compatible with v1: /, /control, /speed, /data.
 // v2 namespaces: /api/v1/state, /api/v1/move, /api/v1/stream (WS), /api/v1/devices.
 void server_setup(AsyncWebServer& http, AsyncWebSocket& ws);

 // Periodic WS broadcast of car state. Call from loop() at 5 Hz.
 void server_broadcast_state();
 void server_broadcast_expansion_event(const ExpansionEvent& ev);

 } // namespace deskcar
