 #pragma once

 namespace deskcar {

 // Initialise LEDC channels and release the motors.
 void motor_setup();

 // Set left/right target PWM in [-255, 255]. Actual output soft-ramps in
 // motor_tick() to avoid the brownout-on-step described in v1 doc.
 void motor_drive(int left_speed, int right_speed);

 // Apply one ramp step toward the current target. Call from loop().
 void motor_tick();

 // Emergency stop: releases LEDC channels (analogWrite(0) under the hood).
 void motor_stop();

 } // namespace deskcar

