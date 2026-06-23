 #include "motor.h"
 #include "config.h"

 #include <Arduino.h>

 namespace deskcar {

 // LEDC channel assignment (left = ch0/ch1, right = ch2/ch3)
 constexpr int LEDC_CH_LEFT_1  = 0;
 constexpr int LEDC_CH_LEFT_2  = 1;
 constexpr int LEDC_CH_RIGHT_1 = 2;
 constexpr int LEDC_CH_RIGHT_2 = 3;

 static int g_current_left  = 0;
 static int g_current_right = 0;
 static int g_target_left   = 0;
 static int g_target_right  = 0;

 void motor_setup() {
     // Configure all 4 channels with the same timer settings.
     ledcSetup(LEDC_CH_LEFT_1,  PWM_FREQ_HZ, PWM_RES_BITS);
     ledcSetup(LEDC_CH_LEFT_2,  PWM_FREQ_HZ, PWM_RES_BITS);
     ledcSetup(LEDC_CH_RIGHT_1, PWM_FREQ_HZ, PWM_RES_BITS);
     ledcSetup(LEDC_CH_RIGHT_2, PWM_FREQ_HZ, PWM_RES_BITS);
     ledcAttachPin(PIN_LEFT_PWM_1,  LEDC_CH_LEFT_1);
     ledcAttachPin(PIN_LEFT_PWM_2,  LEDC_CH_LEFT_2);
     ledcAttachPin(PIN_RIGHT_PWM_1, LEDC_CH_RIGHT_1);
     ledcAttachPin(PIN_RIGHT_PWM_2, LEDC_CH_RIGHT_2);
     motor_stop();
 }

 // Linear ramp: walk from `prev` to `target` over PWM_RAMP_MS, never
 // jumping. Honors v1 spec — no step changes that would trip brownout.
 static int ramp_clamp(int prev, int target) {
     int span = (PWM_MAX * PWM_RAMP_MS) / 1000;  // units per ms
     int max_step = span > 1 ? span : 1;
     if (target > prev + max_step) return prev + max_step;
     if (target < prev - max_step) return prev - max_step;
     return target;
 }

 // Drive a single wheel: pwm1 = forward, pwm2 = reverse, both 0 = coast.
 static void drive_wheel(int pwm1_ch, int pwm2_ch, int speed) {
     if (speed > 0) {
         ledcWrite(pwm1_ch, speed);
         ledcWrite(pwm2_ch, 0);
     } else if (speed < 0) {
         ledcWrite(pwm1_ch, 0);
         ledcWrite(pwm2_ch, -speed);
     } else {
         ledcWrite(pwm1_ch, 0);
         ledcWrite(pwm2_ch, 0);
     }
 }

 void motor_drive(int left_speed, int right_speed) {
     g_target_left  = constrain(left_speed,  -PWM_MAX, PWM_MAX);
     g_target_right = constrain(right_speed, -PWM_MAX, PWM_MAX);
 }

 void motor_tick() {
     g_current_left  = ramp_clamp(g_current_left,  g_target_left);
     g_current_right = ramp_clamp(g_current_right, g_target_right);
     drive_wheel(LEDC_CH_LEFT_1,  LEDC_CH_LEFT_2,  g_current_left);
     drive_wheel(LEDC_CH_RIGHT_1, LEDC_CH_RIGHT_2, g_current_right);
 }

 void motor_stop() {
     // v1 critical: must use ledcWrite(0) to release LEDC channels,
     // digitalWrite(LOW) would be ignored by the LEDC peripheral.
     ledcWrite(LEDC_CH_LEFT_1,  0);
     ledcWrite(LEDC_CH_LEFT_2,  0);
     ledcWrite(LEDC_CH_RIGHT_1, 0);
     ledcWrite(LEDC_CH_RIGHT_2, 0);
     g_current_left  = 0;
     g_current_right = 0;
     g_target_left   = 0;
     g_target_right  = 0;
 }

 } // namespace deskcar

