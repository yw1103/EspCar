 // DeskCar v2 firmware entry point. Wires together motor, encoder, battery,
 // charge, expansion, Wi-Fi, and HTTP/WS server. v1 H5 controller URLs are
 // preserved; v2 namespaces live under /api/v1/*.

 #include "config.h"
 #include "motor.h"
 #include "encoder.h"
 #include "battery.h"
 #include "charge.h"
 #include "expansion.h"
 #include "wifi_mgr.h"
 #include "server.h"
 #include "index_html.h"

 #include <Arduino.h>
 #include <ESPAsyncWebServer.h>
 #include <AsyncTCP.h>
 #include <soc/rtc_cntl_reg.h>
 #include <soc/soc.h>

 namespace deskcar {

 AsyncWebServer g_http(80);
 AsyncWebSocket g_ws("/api/v1/stream");

 void setup() {
     Serial.begin(115200);
     delay(200);
     Serial.println(F("\n[boot] DeskCar v2"));

     // v1 critical: disable brownout so motor inrush doesn't reset us.
     WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

     pinMode(PIN_STATUS_LED, OUTPUT);
     digitalWrite(PIN_STATUS_LED, LOW);

     motor_setup();
     encoder_setup();
     battery_setup();
     charge_setup();
     expansion_setup();

     WifiConfig cfg{};
     strncpy(cfg.ap_ssid, AP_SSID, sizeof(cfg.ap_ssid) - 1);
     strncpy(cfg.mdns_name, MDNS_NAME, sizeof(cfg.mdns_name) - 1);
     wifi_setup(cfg);

     server_setup(g_http, g_ws);
     Serial.println(F("[boot] ready"));
 }

 uint32_t g_last_state_ms = 0;
 void loop() {
     motor_tick();
     wifi_tick();
     g_ws.cleanupClients();
     uint32_t now = millis();
     if (now - g_last_state_ms > 200) {  // 5 Hz state broadcast
         g_last_state_ms = now;
         server_broadcast_state();
     }
     // Drain expansion hot-plug events into the WS stream.
     ExpansionEvent ev;
     while (expansion_poll_event(ev)) {
         // Handled by the next broadcast; nothing else to do here.
     }
 }

 } // namespace deskcar

 void setup()    { deskcar::setup(); }
 void loop()     { deskcar::loop(); }

