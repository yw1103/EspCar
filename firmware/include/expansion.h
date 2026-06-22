 #pragma once

 #include <cstdint>

 namespace deskcar {

 struct ExpansionDevice {
     uint8_t  address;     // 7-bit I2C address
     bool     present;     // ACK on probe
     uint32_t last_seen_ms;
 };

 // Capacity chosen to cover most sensor/actuator stacks we expect devs to
 // attach: OLED, IMU, ToF, motor driver, port expander, GPIO expander.
 constexpr int EXP_MAX_DEVICES = 16;

 void     expansion_setup();
 void     expansion_scan();            // I2C scan, populates internal list
 int      expansion_device_count();
 const ExpansionDevice* expansion_devices();

 // Last hot-plug event for the SDK event stream.
 enum class ExpansionEventKind : uint8_t { Attached, Detached };
 struct ExpansionEvent {
     ExpansionEventKind kind;
     uint8_t address;
 };
 bool     expansion_poll_event(ExpansionEvent& out);  // returns true if pending

 } // namespace deskcar

