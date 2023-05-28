#include "driver/gpio.h"

#define MOUTH_ENABLE GPIO_NUM_5
#define MOUTH_DIRA GPIO_NUM_18
#define MOUTH_DIRB GPIO_NUM_19

#define BODY_ENABLE GPIO_NUM_21
#define BODY_DIRA GPIO_NUM_22
#define BODY_DIRB GPIO_NUM_23

void body_init()
{
    gpio_set_direction(MOUTH_ENABLE, GPIO_MODE_OUTPUT);
    gpio_set_direction(MOUTH_DIRA, GPIO_MODE_OUTPUT);
    gpio_set_direction(MOUTH_DIRB, GPIO_MODE_OUTPUT);
    
    gpio_set_direction(BODY_ENABLE, GPIO_MODE_OUTPUT);
    gpio_set_direction(BODY_DIRA, GPIO_MODE_OUTPUT);
    gpio_set_direction(BODY_DIRB, GPIO_MODE_OUTPUT);

    /* mouth only opens, closing is done by spring */
    gpio_set_level(MOUTH_DIRA, 1);
    gpio_set_level(MOUTH_DIRB, 0);

    gpio_set_level(MOUTH_ENABLE, 0);
    gpio_set_level(BODY_ENABLE, 0);
}

void body_open_mouth()
{
    gpio_set_level(MOUTH_ENABLE, 1);
}

void body_close_mouth()
{
    gpio_set_level(MOUTH_ENABLE, 0);
}
