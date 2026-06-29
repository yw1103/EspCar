 #include "charge.h"
 #include "battery.h"
 #include "config.h"

 #include <Arduino.h>

 namespace deskcar {

 static ChargeState g_charge_state = ChargeState::Idle;
 static uint32_t g_active_since_ms = 0;

 // CHRG is optional. If the charger module exposes it, active-low CHRG wins.
 // If not wired, INA219 current direction is enough for the static dock phase:
 // +mA = battery discharging, -mA = battery charging.
 void charge_setup() {
     pinMode(PIN_CHARGE_CHRG, INPUT_PULLUP);
 }

 void charge_tick() {
     bool chrg = digitalRead(PIN_CHARGE_CHRG) == LOW;  // active low
     BatteryReading b = battery_read();
     bool current_says_charging =
         b.sensor_present && b.current_ma <= CHARGE_DETECT_CURRENT_MA;

     if (chrg || current_says_charging) {
         if (g_active_since_ms == 0) g_active_since_ms = millis();
         uint32_t held_ms = millis() - g_active_since_ms;
         g_charge_state = (held_ms > 1500) ? ChargeState::Charging : ChargeState::Detected;
     } else if (
         (g_charge_state == ChargeState::Detected ||
          g_charge_state == ChargeState::Charging ||
          g_charge_state == ChargeState::Full) &&
         b.sensor_present &&
         b.voltage_v >= CHARGE_FULL_V &&
         b.current_ma <= CHARGE_IDLE_CURRENT_MA
     ) {
         g_charge_state = ChargeState::Full;
     } else {
         g_active_since_ms = 0;
         g_charge_state = ChargeState::Idle;
     }
 }

 ChargeState charge_state() {
     return g_charge_state;
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
