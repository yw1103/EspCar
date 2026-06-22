 #pragma once

 #include <cstdint>

 namespace deskcar {

 enum class ChargeState : uint8_t {
     Idle    = 0,  // not on dock
     Detected = 1, // coil is on the dock, no power transfer yet
     Charging = 2, // actively receiving power
     Full    = 3,  // BQ51025B signaled charge complete
     Fault   = 4
 };

 void charge_setup();
 ChargeState charge_state();
 const char* charge_state_name(ChargeState s);

 } // namespace deskcar

