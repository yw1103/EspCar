 #pragma once

 #include <cstdint>

 namespace deskcar {

 // Quadrature counter per wheel. Backed by ESP32 PCNT for hardware accuracy
 // and zero CPU load in ISRs.
 struct EncoderCount {
     int32_t left;
     int32_t right;
 };

 void encoder_setup();
 EncoderCount encoder_read();        // snapshot then reset deltas
 EncoderCount encoder_read_total();  // absolute counts since boot
 void encoder_reset();

 } // namespace deskcar

