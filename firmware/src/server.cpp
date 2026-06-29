 #include "server.h"
 #include "config.h"
 #include "motor.h"
 #include "encoder.h"
 #include "battery.h"
 #include "charge.h"
 #include "expansion.h"
 #include "wifi_mgr.h"
 #include "index_html.h"
 #include "protocol.h"
 #include <Arduino.h>
 #include <ArduinoJson.h>
 #include <AsyncTCP.h>
 #include <ESPAsyncWebServer.h>

 namespace deskcar {

 namespace {

 AsyncWebSocket* g_ws = nullptr;
 int g_speed_cap = 200;  // global PWM cap, v1 compatibility

 void add_wifi_status(JsonDocument& doc) {
     auto ws = wifi_status();
     doc["wifi"] = wifi_mode_str();
     doc["ip"] = ws.sta_connected ? ws.sta_ip.toString() : ws.ap_ip.toString();
     doc["ap_ip"] = ws.ap_ip.toString();
     doc["sta_ip"] = ws.sta_connected ? ws.sta_ip.toString() : "";
     doc["ssid"] = ws.sta_configured ? ws.sta_ssid : "";
     doc["sta_configured"] = ws.sta_configured;
 }

 void add_state_payload(JsonDocument& doc) {
     auto r = battery_read();
     auto c = charge_state();
     int  n = expansion_device_count();

     doc["type"]   = "state";
     doc["ts"]     = millis();
     doc["v"]      = r.voltage_v;
     doc["i"]      = r.current_ma;
     doc["soc"]    = r.soc_pct;
     doc["charge"] = charge_state_name(c);
     JsonArray exp = doc["exp"].to<JsonArray>();
     for (int i = 0; i < n; ++i) {
         JsonObject o = exp.add<JsonObject>();
         o["addr"] = expansion_devices()[i].address;
     }
     add_wifi_status(doc);
     doc["speed"]  = g_speed_cap;
 }

 void on_ws_event(AsyncWebSocket* server, AsyncWebSocketClient* client,
                  AwsEventType type, void* arg, uint8_t* data, size_t len) {
     if (type != WS_EVT_DATA) return;
     auto* info = (AwsFrameInfo*)arg;
     if (!info->final || info->index != 0) return;
     if (info->opcode != WS_TEXT) return;

     JsonDocument doc;
     if (deserializeJson(doc, data, len)) return;
     const char* cmd = doc["type"] | "";
     if (!strcmp(cmd, "drive")) {
         int l = doc["left"]  | 0;
         int r = doc["right"] | 0;
         motor_drive(constrain(l, -g_speed_cap, g_speed_cap),
                     constrain(r, -g_speed_cap, g_speed_cap));
     } else if (!strcmp(cmd, "set_speed")) {
         g_speed_cap = constrain(doc["value"] | 200, 0, 255);
     } else if (!strcmp(cmd, "stop")) {
         motor_stop();
     } else if (!strcmp(cmd, "scan_expansion")) {
         expansion_request_scan();
     } else if (!strcmp(cmd, "reset")) {
         ESP.restart();
     }
 }

 void broadcast_state() {
     if (!g_ws) return;

     JsonDocument doc;
     add_state_payload(doc);

     String out;
     serializeJson(doc, out);
     g_ws->textAll(out);
 }

 } // namespace

 void server_setup(AsyncWebServer& http, AsyncWebSocket& ws) {
     g_ws = &ws;
     ws.onEvent(on_ws_event);
     http.addHandler(&ws);

     // ---- v1 legacy endpoints (phone H5 controller) ----------------
     http.on("/", HTTP_GET, [](AsyncWebServerRequest* req) {
         req->send(200, "text/html", INDEX_HTML);
     });
     http.on("/wifi", HTTP_GET, [](AsyncWebServerRequest* req) {
         req->send(200, "text/html", WIFI_HTML);
     });
     http.on("/setup", HTTP_GET, [](AsyncWebServerRequest* req) {
         req->send(200, "text/html", WIFI_HTML);
     });
     http.on("/control", HTTP_GET, [](AsyncWebServerRequest* req) {
         if (!req->hasParam("dir")) { req->send(400); return; }
         char d = req->getParam("dir")->value()[0];
         switch (d) {
             case 'F': motor_drive( g_speed_cap,  g_speed_cap); break;
             case 'B': motor_drive(-g_speed_cap, -g_speed_cap); break;
             case 'L': motor_drive(-g_speed_cap,  g_speed_cap); break;
             case 'R': motor_drive( g_speed_cap, -g_speed_cap); break;
             case 'S': motor_stop(); break;
             default:  req->send(400); return;
         }
         Serial.printf("[control] dir=%c cap=%d\n", d, g_speed_cap);
         req->send(200, "text/plain", "ok");
     });
     http.on("/speed", HTTP_GET, [](AsyncWebServerRequest* req) {
         if (!req->hasParam("val")) { req->send(400); return; }
         g_speed_cap = constrain(req->getParam("val")->value().toInt(), 0, 255);
         req->send(200, "text/plain", "ok");
     });
     http.on("/data", HTTP_GET, [](AsyncWebServerRequest* req) {
         auto e = encoder_read_total();
         char buf[64];
         snprintf(buf, sizeof(buf), "{\"left\":%ld,\"right\":%ld}",
                  (long)e.left, (long)e.right);
         req->send(200, "application/json", buf);
     });

     // ---- v2 SDK endpoints ----------------------------------------
     http.on("/api/v1/state", HTTP_GET, [](AsyncWebServerRequest* req) {
         JsonDocument doc;
         add_state_payload(doc);
         String out;
         serializeJson(doc, out);
         req->send(200, "application/json", out);
     });
     http.on("/api/v1/devices", HTTP_GET, [](AsyncWebServerRequest* req) {
         JsonDocument doc;
         JsonArray arr = doc["devices"].to<JsonArray>();
         for (int i = 0; i < expansion_device_count(); ++i) {
             JsonObject o = arr.add<JsonObject>();
             o["addr"] = expansion_devices()[i].address;
         }
         String out;
         serializeJson(doc, out);
         req->send(200, "application/json", out);
     });
     http.on("/api/v1/wifi", HTTP_GET, [](AsyncWebServerRequest* req) {
         JsonDocument doc;
         add_wifi_status(doc);
         String out;
         serializeJson(doc, out);
         req->send(200, "application/json", out);
     });
     http.on("/api/v1/wifi", HTTP_DELETE, [](AsyncWebServerRequest* req) {
         wifi_clear_sta_credentials();
         req->send(200, "application/json", "{\"ok\":true,\"restart_required\":true}");
     });
     http.on("/api/v1/wifi", HTTP_POST,
         [](AsyncWebServerRequest* req) {},
         nullptr,
         [](AsyncWebServerRequest* req, uint8_t* data, size_t len, size_t, size_t) {
             JsonDocument doc;
             if (deserializeJson(doc, data, len)) { req->send(400); return; }
             const char* ssid = doc["ssid"] | "";
             const char* pass = doc["pass"] | "";
             if (!wifi_save_sta_credentials(ssid, pass)) {
                 req->send(400, "application/json", "{\"ok\":false,\"error\":\"bad credentials\"}");
                 return;
             }
             req->send(200, "application/json", "{\"ok\":true,\"restart_required\":true}");
         });
     http.on("/api/v1/move", HTTP_POST,
         [](AsyncWebServerRequest* req) {},
         nullptr,
         [](AsyncWebServerRequest* req, uint8_t* data, size_t len, size_t, size_t) {
             JsonDocument doc;
             if (deserializeJson(doc, data, len)) { req->send(400); return; }
             int l = doc["left"]  | 0;
             int r = doc["right"] | 0;
             motor_drive(constrain(l, -255, 255), constrain(r, -255, 255));
             req->send(200, "application/json", "{\"ok\":true}");
         });

     http.begin();
 }

 void server_broadcast_state() { broadcast_state(); }

 void server_broadcast_expansion_event(const ExpansionEvent& ev) {
     if (!g_ws) return;
     JsonDocument doc;
     doc["type"] = ev.kind == ExpansionEventKind::Attached
         ? "device_attached"
         : "device_detached";
     doc["address"] = ev.address;
     String out;
     serializeJson(doc, out);
     g_ws->textAll(out);
 }

 } // namespace deskcar
