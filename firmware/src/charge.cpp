 #include "charge.h"
 #include "battery.h"
 #include "config.h"

 #include <Arduino.h>

 namespace deskcar {

 // CHRG is optional. If the charger module exposes it, active-low CHRG wins.
 // If not wired, INA219 current direction is enough for the static dock phase:
 // +mA = battery discharging, -mA = battery charging.
 void charge_setup() {
     pinMode(PIN_CHARGE_CHRG, INPUT_PULLUP);
 }

 ChargeState charge_state() {
     static ChargeState last = ChargeState::Idle;
     static uint32_t active_since_ms = 0;

     bool chrg = digitalRead(PIN_CHARGE_CHRG) == LOW;  // active low
     BatteryReading b = battery_read();
     bool current_says_charging =
         b.sensor_present && b.current_ma <= CHARGE_DETECT_CURRENT_MA;

     if (chrg || current_says_charging) {
         if (active_since_ms == 0) active_since_ms = millis();
         uint32_t held_ms = millis() - active_since_ms;
         last = (held_ms > 1500) ? ChargeState::Charging : ChargeState::Detected;
     } else if (
         (last == ChargeState::Detected ||
          last == ChargeState::Charging ||
          last == ChargeState::Full) &&
         b.sensor_present &&
         b.voltage_v >= CHARGE_FULL_V &&
         b.current_ma <= CHARGE_IDLE_CURRENT_MA
     ) {
         last = ChargeState::Full;
     } else {
         active_since_ms = 0;
         last = ChargeState::Idle;
     }
     return last;
 }

 const char* charge_state_name(ChargeState s) {
     switch (s) {
         case ChargeState::Idle:     return "idle";
         case ChargeState::Detected: return "detected";
         case ChargeState::Charging: return "charging";
         case ChargeState::Full:     return "full";
         case ChargeState::Fault:    return "fault";
     }
     return "unknown";
 }

 } // namespace deskcar
