 #pragma once

 namespace deskcar {

 // Initialise LEDC channels and release the motors.
 void motor_setup();

 // Drive left/right with signed PWM in [-255, 255]. Soft-ramps internally
 // to avoid the brownout-on-step described in v1 doc.
 void motor_drive(int left_speed, int right_speed);

 // Emergency stop: releases LEDC channels (analogWrite(0) under the hood).
 void motor_stop();

 } // namespace deskcar

