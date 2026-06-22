 #include "encoder.h"
 #include "config.h"

 #include <Arduino.h>
 #include <driver/pcnt.h>
 #include <soc/pcnt_reg.h>

 namespace deskcar {

 // Map wheel -> PCNT unit / channel / control pin.
 struct PcntMapping {
     pcnt_unit_t   unit;
     pcnt_channel_t channel;
     int           pin_a;
     int           pin_b;
 };

 static const PcntMapping LEFT  = {PCNT_UNIT_0, PCNT_CHANNEL_0, PIN_LEFT_ENC_A,  PIN_LEFT_ENC_B};
 static const PcntMapping RIGHT = {PCNT_UNIT_1, PCNT_CHANNEL_0, PIN_RIGHT_ENC_A, PIN_RIGHT_ENC_B};

 static int32_t g_prev_left  = 0;
 static int32_t g_prev_right = 0;

 void encoder_setup() {
     for (const auto& m : {LEFT, RIGHT}) {
         pcnt_config_t cfg = {};
         cfg.pulse_gpio_num = m.pin_a;
         cfg.ctrl_gpio_num  = m.pin_b;
         cfg.lctrl_mode     = PCNT_MODE_KEEP;
         cfg.hctrl_mode     = PCNT_MODE_REVERSE;
         cfg.pos_mode       = PCNT_COUNT_INC;
         cfg.neg_mode       = PCNT_COUNT_DEC;
         cfg.counter_h_lim  = 32767;
         cfg.counter_l_lim  = -32768;
         cfg.unit           = m.unit;
         cfg.channel        = m.channel;
         pcnt_unit_config(&cfg);
         pcnt_counter_pause(m.unit);
         pcnt_counter_clear(m.unit);
         pcnt_counter_resume(m.unit);
         // Filter pulses shorter than 1000 APB cycles — debounces encoder bounce.
         pcnt_set_filter_value(m.unit, 1000);
         pcnt_filter_enable(m.unit);
     }
 }

 static int32_t read_unit(pcnt_unit_t unit) {
     int16_t v = 0;
     pcnt_get_counter_value(unit, &v);
     return v;
 }

 EncoderCount encoder_read() {
     int32_t l = read_unit(LEFT.unit);
     int32_t r = read_unit(RIGHT.unit);
     EncoderCount delta{l - g_prev_left, r - g_prev_right};
     g_prev_left  = l;
     g_prev_right = r;
     return delta;
 }

 EncoderCount encoder_read_total() {
     return {read_unit(LEFT.unit), read_unit(RIGHT.unit)};
 }

 void encoder_reset() {
     pcnt_counter_clear(LEFT.unit);
     pcnt_counter_clear(RIGHT.unit);
     g_prev_left = g_prev_right = 0;
 }

 } // namespace deskcar

