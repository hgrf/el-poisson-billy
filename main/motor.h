#ifndef MOTOR_H
#define MOTOR_H

#include "driver/ledc.h"

typedef struct {
    uint16_t valid_up_to;
    uint16_t charge_duration;
    int16_t boost_value;
    uint16_t boost_duration;
    uint16_t settle_duration;
} motor_boost_params_t;

typedef struct {
    uint8_t enable;
    uint8_t dira;
    uint8_t dirb;
    ledc_channel_t channel;
    ledc_timer_t timer;
    int16_t duty;
} motor_ctx_t;

void motor_init(motor_ctx_t *ctx);
void motor_set_duty(motor_ctx_t *ctx, int16_t duty);

#endif // MOTOR_H
