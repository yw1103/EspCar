 #pragma once

 #include <cstdint>

 // DeskCar v2 — pin mapping & build-time config
 // Inherits v1 (handover doc) constraints; never use input-only pins as outputs.

 namespace deskcar {

 // ---- v1 motor / encoder pins (do not change) --------------------------
 constexpr int PIN_LEFT_PWM_1   = 14;  // DRV8833 AIN1
 constexpr int PIN_LEFT_PWM_2   = 27;  // DRV8833 AIN2
 constexpr int PIN_RIGHT_PWM_1  = 16;  // DRV8833 BIN1  (RX2, no strapping limit)
 constexpr int PIN_RIGHT_PWM_2  = 17;  // DRV8833 BIN2  (TX2, no strapping limit)
 constexpr int PIN_LEFT_ENC_A   = 34;  // input-only
 constexpr int PIN_LEFT_ENC_B   = 35;  // input-only
 constexpr int PIN_RIGHT_ENC_A  = 32;
 constexpr int PIN_RIGHT_ENC_B  = 33;

 // ---- v2 expansion & power -------------------------------------------
 constexpr int PIN_I2C_SDA      = 21;
 constexpr int PIN_I2C_SCL      = 22;
 constexpr int PIN_CHARGE_CHRG  = 25;  // BQ51025B CHRG, INPUT_PULLUP
 constexpr int PIN_EXP_INT      = 26;  // expansion INT, INPUT_PULLUP
 constexpr int PIN_BTN_UNDOCK   = 4;   // active-low button
 constexpr int PIN_STATUS_LED   = 13;  // on-board LED, output

 // ---- motion limits ---------------------------------------------------
 constexpr int PWM_FREQ_HZ      = 20000;
 constexpr int PWM_RES_BITS     = 8;
 constexpr int PWM_MAX          = 255;
 constexpr int PWM_RAMP_MS      = 80;   // v1 spec: 50-100ms soft start
 constexpr int ENCODER_PPR      = 7;    // physical PPR (×4 quadrature = 28 cpr)

 // ---- I2C bus (shared by INA219 + expansion) --------------------------
 constexpr uint32_t I2C_FREQ_HZ  = 400000;
 constexpr uint8_t  INA219_ADDR  = 0x40;

 // ---- network ---------------------------------------------------------
 constexpr char AP_SSID[]       = "ESP32_Car_Control";
 constexpr char AP_PASS[]       = "";            // open AP for direct phone control
 constexpr char MDNS_NAME[]     = "deskcar";

 // ---- battery (v2: 1S Li-ion 3.7V 1000mAh) ---------------------------
 constexpr float  BATTERY_NOMINAL_V  = 3.7f;
 constexpr float  BATTERY_FULL_V     = 4.2f;
 constexpr float  BATTERY_EMPTY_V    = 3.3f;
 constexpr int    BATTERY_CAPACITY_MAH = 1000;

 // INA219 current convention: +mA = battery discharging, -mA = charging.
 // Keep a small deadband so sensor zero-drift does not look like charging.
 constexpr float  CHARGE_DETECT_CURRENT_MA = -20.0f;
 constexpr float  CHARGE_IDLE_CURRENT_MA   = 20.0f;
 constexpr float  CHARGE_FULL_V            = 4.15f;

 } // namespace deskcar
