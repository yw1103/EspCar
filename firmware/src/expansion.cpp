 #include "expansion.h"
 #include "config.h"

 #include <Arduino.h>
 #include <Wire.h>
 #include <freertos/FreeRTOS.h>

 namespace deskcar {

 static ExpansionDevice g_devices[EXP_MAX_DEVICES];
 static int g_device_count = 0;

 static volatile bool     g_evt_pending = false;
 static volatile uint8_t  g_evt_addr    = 0;
 static volatile ExpansionEventKind g_evt_kind = ExpansionEventKind::Detached;

 static void IRAM_ATTR on_exp_int() {
     // Defer I2C work to loop(); this ISR only flags the event.
     g_evt_pending = true;
 }

 void expansion_setup() {
     pinMode(PIN_EXP_INT, INPUT_PULLUP);
     attachInterrupt(digitalPinToInterrupt(PIN_EXP_INT), on_exp_int, FALLING);
     expansion_scan();
 }

 void expansion_scan() {
     g_device_count = 0;
     for (uint8_t addr = 0x03; addr < 0x78 && g_device_count < EXP_MAX_DEVICES; ++addr) {
         Wire.beginTransmission(addr);
         if (Wire.endTransmission() == 0) {
             g_devices[g_device_count++] = {addr, true, millis()};
         }
     }
     Serial.printf("[expansion] found %d device(s)\n", g_device_count);
 }

 int expansion_device_count() { return g_device_count; }
 const ExpansionDevice* expansion_devices() { return g_devices; }

 bool expansion_poll_event(ExpansionEvent& out) {
     if (!g_evt_pending) return false;
     g_evt_pending = false;
     out.address = g_evt_addr;
     out.kind    = g_evt_kind;
     // Re-scan so the device list reflects new topology.
     expansion_scan();
     return true;
 }

 } // namespace deskcar

