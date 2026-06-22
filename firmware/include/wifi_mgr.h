 #pragma once

 #include <Arduino.h>
 #include <ESPmDNS.h>
 #include <WiFi.h>

 namespace deskcar {

 // Two-mode Wi-Fi: AP for direct phone control (v1 compat), STA for the
 // PC SDK to talk over the home LAN. Both run concurrently; the radio
 // auto-airs between them. SDK traffic uses STA; phone H5 traffic uses AP.
 struct WifiConfig {
     char ap_ssid[32];
     char ap_pass[64];
     char sta_ssid[32];
     char sta_pass[64];
     bool sta_enabled;
     char mdns_name[32];
 };

 void wifi_setup(const WifiConfig& cfg);
 bool wifi_sta_connected();
 IPAddress wifi_ap_ip();
 IPAddress wifi_sta_ip();
 const char* wifi_mode_str();

 } // namespace deskcar

