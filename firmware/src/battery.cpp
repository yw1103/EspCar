 #include "battery.h"
 #include "config.h"

 #include <Arduino.h>
 #include <Wire.h>
 #include <Adafruit_INA219.h>

 namespace deskcar {

 static Adafruit_INA219 g_ina(INA219_ADDR);
 static bool g_ina_ok = false;
 static uint8_t g_ina_addr = 0;
 static BatteryReading g_last_reading{};

 static bool probe_i2c(uint8_t addr) {
     Wire.beginTransmission(addr);
     return Wire.endTransmission() == 0;
 }

 void battery_setup() {
     Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_FREQ_HZ);
     delay(10);  // allow bus pull-ups to settle
     g_ina_ok = false;
     g_ina_addr = 0;
     g_last_reading = {};

     // INA219 modules may ship with A0/A1 strapped to 0x41/0x44/0x45.
     const uint8_t kAddrs[] = {INA219_ADDR, 0x41, 0x44, 0x45};
     for (uint8_t addr : kAddrs) {
         if (!probe_i2c(addr)) continue;
         g_ina = Adafruit_INA219(addr);
         if (g_ina.begin(&Wire)) {
             g_ina_ok = true;
             g_ina_addr = addr;
             g_ina.setCalibration_32V_1A();
             Serial.printf("[battery] INA219 ready at 0x%02X\n", addr);
             battery_tick();
             if (g_last_reading.voltage_v < 0.5f) {
                 Serial.println(F("[battery] voltage ~0: check VIN+/VIN- in battery loop"));
             }
             return;
         }
     }

     Serial.println(F("[battery] INA219 not found (SDA=21 SCL=22)"));
 }

 void battery_tick() {
     BatteryReading r{};
     r.sensor_present = g_ina_ok;
     if (g_ina_ok) {
         r.voltage_v  = g_ina.getBusVoltage_V() + (g_ina.getShuntVoltage_mV() / 1000.0f);
         r.current_ma = g_ina.getCurrent_mA();
         r.soc_pct    = battery_estimate_soc(r.voltage_v);
     }
     g_last_reading = r;
 }

 BatteryReading battery_read() {
     return g_last_reading;
 }

 uint8_t battery_ina219_addr() {
     return g_ina_ok ? g_ina_addr : 0;
 }

 // Li-ion 1S: 3.3V empty, 4.2V full. Piecewise linear, smoothed.
 // This is a coarse estimate; coulomb counting is the SDK's job to refine.
 uint8_t battery_estimate_soc(float voltage_v) {
     if (voltage_v <= BATTERY_EMPTY_V) return 0;
     if (voltage_v >= BATTERY_FULL_V)  return 100;
     float pct = (voltage_v - BATTERY_EMPTY_V) / (BATTERY_FULL_V - BATTERY_EMPTY_V) * 100.0f;
     return (uint8_t)constrain(pct, 0.0f, 100.0f);
 }

 } // namespace deskcar
