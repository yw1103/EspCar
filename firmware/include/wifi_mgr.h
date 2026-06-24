 #pragma once

 #include <Arduino.h>
 #include <ESPmDNS.h>
 #include <WiFi.h>

 namespace deskcar {

 constexpr uint16_t DISCOVERY_PORT = 30303;

 // Product Wi-Fi model:
 // - first boot / failed STA: open AP for provisioning and v1 H5 fallback
 // - configured network: STA is preferred so users keep normal internet
 // - AP remains available as a recovery path while STA is connected
 struct WifiConfig {
     char ap_ssid[32];
     char ap_pass[64];
     char sta_ssid[32];
     char sta_pass[64];
     bool sta_enabled;
     char mdns_name[32];
 };

 struct WifiStatus {
     bool sta_configured;
     bool sta_connected;
     bool ap_active;
     char sta_ssid[32];
     IPAddress ap_ip;
     IPAddress sta_ip;
 };

 void wifi_setup(const WifiConfig& cfg);
 void wifi_tick();
 bool wifi_save_sta_credentials(const char* ssid, const char* pass);
 void wifi_clear_sta_credentials();
 WifiStatus wifi_status();
 bool wifi_sta_connected();
 IPAddress wifi_ap_ip();
 IPAddress wifi_sta_ip();
 const char* wifi_mode_str();

 } // namespace deskcar
