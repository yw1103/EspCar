 #include "wifi_mgr.h"
 #include "config.h"

 #include <Arduino.h>

 namespace deskcar {

 static WifiConfig g_cfg{};

 void wifi_setup(const WifiConfig& cfg) {
     g_cfg = cfg;

     // v1: AP is required for the phone H5 controller. Open network.
     WiFi.mode(WIFI_AP_STA);
     WiFi.softAP(g_cfg.ap_ssid, g_cfg.ap_pass, 1, 0, 4);

     if (g_cfg.sta_enabled && strlen(g_cfg.sta_ssid) > 0) {
         WiFi.begin(g_cfg.sta_ssid, g_cfg.sta_pass);
     } else {
         // Disable STA explicitly; saves power and avoids deauth storms.
         WiFi.mode(WIFI_AP);
     }

     if (strlen(g_cfg.mdns_name) > 0) {
         MDNS.begin(g_cfg.mdns_name);
         MDNS.addService("http", "tcp", 80);
     }

     Serial.printf("[wifi] AP SSID=%s IP=%s\n",
                   g_cfg.ap_ssid, WiFi.softAPIP().toString().c_str());
     if (g_cfg.sta_enabled) {
         Serial.printf("[wifi] STA connecting to %s\n", g_cfg.sta_ssid);
     }
 }

 bool wifi_sta_connected() {
     return WiFi.status() == WL_CONNECTED;
 }

 IPAddress wifi_ap_ip()  { return WiFi.softAPIP(); }
 IPAddress wifi_sta_ip() { return WiFi.localIP(); }
 const char* wifi_mode_str() {
     return (g_cfg.sta_enabled && wifi_sta_connected()) ? "AP+STA" : "AP";
 }

 } // namespace deskcar

