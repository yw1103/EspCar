 #include "expansion.h"
 #include "battery.h"
 #include "config.h"

 #include <Arduino.h>
 #include <Wire.h>

 namespace deskcar {

 static ExpansionDevice g_devices[EXP_MAX_DEVICES];
 static int g_device_count = 0;

 static bool g_evt_pending = false;
 static volatile bool g_scan_requested = false;
 static uint32_t g_last_scan_ms = 0;
 static uint8_t  g_evt_addr = 0;
 static ExpansionEventKind g_evt_kind = ExpansionEventKind::Detached;

 static bool list_has_device(const ExpansionDevice* devices, int count, uint8_t addr) {
     for (int i = 0; i < count; ++i) {
         if (devices[i].address == addr) return true;
     }
     return false;
 }

 static void IRAM_ATTR on_exp_int() {
     // Defer I2C work to loop(); this ISR only flags the event.
     g_scan_requested = true;
 }

 void expansion_setup() {
     pinMode(PIN_EXP_INT, INPUT_PULLUP);
     attachInterrupt(digitalPinToInterrupt(PIN_EXP_INT), on_exp_int, FALLING);
     expansion_scan();
 }

 void expansion_tick() {
     uint32_t now = millis();
     if (g_scan_requested || now - g_last_scan_ms > 2000) {
         g_scan_requested = false;
         expansion_scan();
     }
 }

 void expansion_request_scan() {
     g_scan_requested = true;
 }

 void expansion_scan() {
     ExpansionDevice old_devices[EXP_MAX_DEVICES];
     int old_count = g_device_count;
     for (int i = 0; i < old_count; ++i) old_devices[i] = g_devices[i];

     g_device_count = 0;
     uint8_t ina_addr = battery_ina219_addr();
     for (uint8_t addr = 0x03; addr < 0x78 && g_device_count < EXP_MAX_DEVICES; ++addr) {
         if (addr == ina_addr) continue;
         Wire.beginTransmission(addr);
         if (Wire.endTransmission() == 0) {
             g_devices[g_device_count++] = {addr, true, millis()};
         }
     }
     if (!g_evt_pending) {
         for (int i = 0; i < g_device_count; ++i) {
             if (!list_has_device(old_devices, old_count, g_devices[i].address)) {
                 g_evt_pending = true;
                 g_evt_addr = g_devices[i].address;
                 g_evt_kind = ExpansionEventKind::Attached;
                 break;
             }
         }
     }
     if (!g_evt_pending) {
         for (int i = 0; i < old_count; ++i) {
             if (!list_has_device(g_devices, g_device_count, old_devices[i].address)) {
                 g_evt_pending = true;
                 g_evt_addr = old_devices[i].address;
                 g_evt_kind = ExpansionEventKind::Detached;
                 break;
             }
         }
     }
     g_last_scan_ms = millis();
     Serial.printf("[expansion] found %d device(s)\n", g_device_count);
 }

 int expansion_device_count() { return g_device_count; }
 const ExpansionDevice* expansion_devices() { return g_devices; }

 bool expansion_poll_event(ExpansionEvent& out) {
     if (!g_evt_pending) return false;
     g_evt_pending = false;
     out.address = g_evt_addr;
     out.kind    = g_evt_kind;
     return true;
 }

 } // namespace deskcar
