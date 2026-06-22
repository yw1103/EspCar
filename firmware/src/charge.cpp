 #include "charge.h"
 #include "config.h"

 #include <Arduino.h>

 namespace deskcar {

 // BQ51025B CHRG pin is open-drain, active-low. The dock inductor is
 // always powered but only delivers current when coupled, so we infer
 // presence from CHRG toggling.
 void charge_setup() {
     pinMode(PIN_CHARGE_CHRG, INPUT_PULLUP);
 }

 ChargeState charge_state() {
     static ChargeState last = ChargeState::Idle;
     static uint32_t low_since_ms = 0;

     bool chrg = digitalRead(PIN_CHARGE_CHRG) == LOW;  // active low
     if (chrg) {
         if (low_since_ms == 0) low_since_ms = millis();
         uint32_t held_ms = millis() - low_since_ms;
         if (held_ms > 1500) {
             last = (held_ms < 30000) ? ChargeState::Charging : ChargeState::Full;
         } else {
             last = ChargeState::Detected;
         }
     } else {
         low_since_ms = 0;
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

