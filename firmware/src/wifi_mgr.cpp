#include "wifi_mgr.h"
#include "config.h"
#include "protocol.h"

#include <Arduino.h>
#include <Preferences.h>
#include <WiFiUdp.h>

namespace deskcar {

 static WifiConfig g_cfg{};
 static Preferences g_prefs;
 static WiFiUDP g_udp;
 static bool g_ap_active = false;
 static bool g_udp_started = false;

 namespace {

 constexpr uint32_t STA_CONNECT_TIMEOUT_MS = 8000;
 constexpr char DISCOVERY_MAGIC[] = "DESKCAR_DISCOVER_V1\r\n";

 void copy_str(char* dst, size_t n, const String& src) {
     if (n == 0) return;
     strncpy(dst, src.c_str(), n - 1);
     dst[n - 1] = '\0';
 }

 void start_ap() {
     if (g_ap_active) return;
     WiFi.softAP(g_cfg.ap_ssid, g_cfg.ap_pass, 1, 0, 4);
     g_ap_active = true;
     Serial.printf("[wifi] AP SSID=%s IP=%s\n",
                   g_cfg.ap_ssid, WiFi.softAPIP().toString().c_str());
 }

 void load_sta_credentials() {
     g_prefs.begin("deskcar-wifi", true);
     String ssid = g_prefs.getString("ssid", "");
     String pass = g_prefs.getString("pass", "");
     g_prefs.end();
     copy_str(g_cfg.sta_ssid, sizeof(g_cfg.sta_ssid), ssid);
     copy_str(g_cfg.sta_pass, sizeof(g_cfg.sta_pass), pass);
     g_cfg.sta_enabled = ssid.length() > 0;
 }

 void start_mdns() {
     if (strlen(g_cfg.mdns_name) == 0) return;
     if (MDNS.begin(g_cfg.mdns_name)) {
         MDNS.addService("http", "tcp", 80);
         Serial.printf("[wifi] mDNS http://%s.local\n", g_cfg.mdns_name);
     }
 }

 void start_discovery() {
     if (g_udp_started) return;
     if (g_udp.begin(DISCOVERY_PORT)) {
         g_udp_started = true;
         Serial.printf("[wifi] UDP discovery listening on %u\n", DISCOVERY_PORT);
     }
 }

 void send_discovery_reply(IPAddress remote_ip, uint16_t remote_port) {
     IPAddress host = wifi_sta_connected() ? WiFi.localIP() : WiFi.softAPIP();
     String name = strlen(g_cfg.mdns_name) > 0 ? String(g_cfg.mdns_name) : String("deskcar");
     String out = "{";
     out += "\"host\":\"" + host.toString() + "\",";
     out += "\"port\":80,";
     out += "\"name\":\"" + name + "\",";
     out += "\"v\":" + String(PROTOCOL_VERSION);
     out += "}";
     g_udp.beginPacket(remote_ip, remote_port);
     g_udp.write(reinterpret_cast<const uint8_t*>(out.c_str()), out.length());
     g_udp.endPacket();
 }

 } // namespace

 void wifi_setup(const WifiConfig& cfg) {
     g_cfg = cfg;
     load_sta_credentials();

     WiFi.persistent(false);
     WiFi.setSleep(false);

     if (g_cfg.sta_enabled && strlen(g_cfg.sta_ssid) > 0) {
         WiFi.mode(WIFI_AP_STA);
         start_ap();
         WiFi.begin(g_cfg.sta_ssid, g_cfg.sta_pass);
         Serial.printf("[wifi] STA connecting to %s\n", g_cfg.sta_ssid);

         uint32_t started = millis();
         while (WiFi.status() != WL_CONNECTED &&
                millis() - started < STA_CONNECT_TIMEOUT_MS) {
             delay(100);
         }

         if (WiFi.status() == WL_CONNECTED) {
             Serial.printf("[wifi] STA connected IP=%s\n",
                           WiFi.localIP().toString().c_str());
         } else {
             Serial.println(F("[wifi] STA failed; AP fallback remains active"));
         }
     } else {
         WiFi.mode(WIFI_AP);
         start_ap();
         Serial.println(F("[wifi] no STA credentials; AP provisioning mode"));
     }

     start_mdns();
     start_discovery();
 }

 void wifi_tick() {
     if (!g_udp_started) return;
     int packet_size = g_udp.parsePacket();
     if (packet_size <= 0) return;

     char buf[32] = {};
     int n = g_udp.read(buf, sizeof(buf) - 1);
     if (n <= 0) return;
     buf[n] = '\0';
     if (!strcmp(buf, DISCOVERY_MAGIC)) {
         send_discovery_reply(g_udp.remoteIP(), g_udp.remotePort());
     }
 }

 bool wifi_save_sta_credentials(const char* ssid, const char* pass) {
     if (ssid == nullptr || strlen(ssid) == 0 || strlen(ssid) >= sizeof(g_cfg.sta_ssid)) {
         return false;
     }
     if (pass != nullptr && strlen(pass) >= sizeof(g_cfg.sta_pass)) {
         return false;
     }
     g_prefs.begin("deskcar-wifi", false);
     bool ok = g_prefs.putString("ssid", ssid) > 0;
     ok = g_prefs.putString("pass", pass == nullptr ? "" : pass) > 0 && ok;
     g_prefs.end();
     return ok;
 }

 void wifi_clear_sta_credentials() {
     g_prefs.begin("deskcar-wifi", false);
     g_prefs.remove("ssid");
     g_prefs.remove("pass");
     g_prefs.end();
 }

 WifiStatus wifi_status() {
     WifiStatus st{};
     st.sta_configured = g_cfg.sta_enabled && strlen(g_cfg.sta_ssid) > 0;
     st.sta_connected = wifi_sta_connected();
     st.ap_active = g_ap_active;
     strncpy(st.sta_ssid, g_cfg.sta_ssid, sizeof(st.sta_ssid) - 1);
     st.ap_ip = WiFi.softAPIP();
     st.sta_ip = WiFi.localIP();
     return st;
 }

 bool wifi_sta_connected() {
     return WiFi.status() == WL_CONNECTED;
 }

 IPAddress wifi_ap_ip()  { return WiFi.softAPIP(); }
 IPAddress wifi_sta_ip() { return WiFi.localIP(); }
 const char* wifi_mode_str() {
     if (wifi_sta_connected() && g_ap_active) return "AP+STA";
     if (wifi_sta_connected()) return "STA";
     return "AP";
 }

 } // namespace deskcar
