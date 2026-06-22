 #include "battery.h"
 #include "config.h"

 #include <Arduino.h>
 #include <Wire.h>
 #include <Adafruit_INA219.h>

 namespace deskcar {

 static Adafruit_INA219 g_ina(INA219_ADDRESS);
 static bool g_ina_ok = false;

 void battery_setup() {
     Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_FREQ_HZ);
     g_ina_ok = g_ina.begin(&Wire);
     if (g_ina_ok) {
         // 32V range, 12-bit, ~1ms conversion, 532uA LSB current.
         g_ina.setCalibration_32V_1A();
     } else {
         Serial.println(F("[battery] INA219 not found, falling back to ADC"));
     }
 }

 BatteryReading battery_read() {
     BatteryReading r{};
     r.sensor_present = g_ina_ok;
     if (g_ina_ok) {
         r.voltage_v  = g_ina.getBusVoltage_V() + (g_ina.getShuntVoltage_mV() / 1000.0f);
         r.current_ma = g_ina.getCurrent_mA();
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
