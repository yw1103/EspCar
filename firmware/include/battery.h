 #pragma once

 #include <cstdint>

 namespace deskcar {

 struct BatteryReading {
     float voltage_v;       // 0 if sensor missing
     float current_ma;      // +ve = discharge, -ve = charge
     float soc_pct;         // 0-100, -1 if unknown
     bool  sensor_present;  // false => caller should fall back to ADC divider
 };

 void     battery_setup();
 BatteryReading battery_read();
 uint8_t  battery_ina219_addr();  // 0 when INA219 is not present
 uint8_t  battery_estimate_soc(float voltage_v);  // 0-100

 } // namespace deskcar
