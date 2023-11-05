#include "body.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "driver/gpio.h"

#include "motor.h"

#define MOUTH_ENABLE GPIO_NUM_5
#define MOUTH_DIRA GPIO_NUM_18
#define MOUTH_DIRB GPIO_NUM_19

#define BODY_ENABLE GPIO_NUM_21
#define BODY_DIRA GPIO_NUM_22
#define BODY_DIRB GPIO_NUM_23

static motor_ctx_t mouth = {
    .enable = MOUTH_ENABLE,
    .dira = MOUTH_DIRA,
    .dirb = MOUTH_DIRB,
    .channel = LEDC_CHANNEL_1,
    .timer = LEDC_TIMER_1,
    .duty = 0,
};

void body_init()
{
    gpio_set_direction(BODY_ENABLE, GPIO_MODE_OUTPUT);
    gpio_set_direction(BODY_DIRA, GPIO_MODE_OUTPUT);
    gpio_set_direction(BODY_DIRB, GPIO_MODE_OUTPUT);
    gpio_set_level(BODY_ENABLE, 0);

    motor_init(&mouth);
}

void body_open_mouth()
{
    gpio_set_level(MOUTH_ENABLE, 1);
}

void body_set_mouth(unsigned char pos)
{
    /* map pos from 0-127 to 388-1023 */
    int16_t duty = pos * 5 + 388;
    motor_set_duty(&mouth, duty);
}

void body_close_mouth()
{
    gpio_set_level(MOUTH_ENABLE, 0);
}

void body_wiggle_head()
{
    gpio_set_level(BODY_DIRA, 1);
    gpio_set_level(BODY_DIRB, 0);
    gpio_set_level(BODY_ENABLE, 1);
}

void body_wiggle_tail()
{
    gpio_set_level(BODY_DIRA, 0);
    gpio_set_level(BODY_DIRB, 1);
    gpio_set_level(BODY_ENABLE, 1);
}

void body_wiggle_stop()
{
    gpio_set_level(BODY_ENABLE, 0);
}
