 #include "battery.h"
 #include "config.h"

 #include <Arduino.h>
 #include <Wire.h>
 #include <Adafruit_INA219.h>

 namespace deskcar {

 static Adafruit_INA219* g_ina = nullptr;
 static bool g_ina_ok = false;

 static bool probe_i2c(uint8_t addr) {
     Wire.beginTransmission(addr);
     return Wire.endTransmission() == 0;
 }

 void battery_setup() {
     Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_FREQ_HZ);
     delay(10);  // allow bus pull-ups to settle

     // INA219 modules may ship with A0/A1 strapped to 0x41/0x44/0x45.
     const uint8_t kAddrs[] = {INA219_ADDR, 0x41, 0x44, 0x45};
     for (uint8_t addr : kAddrs) {
         if (!probe_i2c(addr)) continue;
         delete g_ina;
         g_ina = new Adafruit_INA219(addr);
         if (g_ina->begin(&Wire)) {
             g_ina_ok = true;
             g_ina->setCalibration_32V_1A();
             Serial.printf("[battery] INA219 ready at 0x%02X\n", addr);
             if (battery_read().voltage_v < 0.5f) {
                 Serial.println(F("[battery] voltage ~0: check VIN+/VIN- in battery loop"));
             }
             return;
         }
         delete g_ina;
         g_ina = nullptr;
     }

     Serial.println(F("[battery] INA219 not found (SDA=21 SCL=22)"));
 }

 BatteryReading battery_read() {
     BatteryReading r{};
     r.sensor_present = g_ina_ok;
     if (g_ina_ok && g_ina) {
         r.voltage_v  = g_ina->getBusVoltage_V() + (g_ina->getShuntVoltage_mV() / 1000.0f);
         r.current_ma = g_ina->getCurrent_mA();
         r.soc_pct    = battery_estimate_soc(r.voltage_v);
     }
     return r;
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
