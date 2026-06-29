 #pragma once

 #include <cstdint>

 namespace deskcar {

 enum class ChargeState : uint8_t {
     Idle    = 0,  // not on dock
     Detected = 1, // charge signal/current just appeared, still debouncing
     Charging = 2, // actively receiving power
     Full    = 3,  // inferred from high voltage after charging
     Fault   = 4
 };

 void charge_setup();
 void charge_tick();
 ChargeState charge_state();
 const char* charge_state_name(ChargeState s);

 } // namespace deskcar
