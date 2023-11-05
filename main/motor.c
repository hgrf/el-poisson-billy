#include "motor.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "driver/gpio.h"

/* when increasing the duty cycle, shortly switch off the motor
 * to compensate for hysteresis ("charge"), then give a short boost
 * before settling into the new duty cycle
 */
// TODO: strong oscillations at 903~923
static motor_boost_params_t boost_params_up[] = {
    {
        .valid_up_to = 603,
        .charge_duration = 0,
        .boost_value = 1023,
        .boost_duration = 10,
        .settle_duration = 51,
    },
    {
        .valid_up_to = 783,
        .charge_duration = 0,
        .boost_value = 1023,
        .boost_duration = 20,
        .settle_duration = 41,
    },
    {
        .valid_up_to = 903,
        .charge_duration = 10,
        .boost_value = 1023,
        .boost_duration = 50,
        .settle_duration = 0,
    },
    {
        .valid_up_to = 963,
        .charge_duration = 10,
        .boost_value = 1023,
        .boost_duration = 50,
        .settle_duration = 0,
    },
    {
        .valid_up_to = 1023,
        .charge_duration = 15,
        .boost_value = 1023,
        .boost_duration = 20,
        .settle_duration = 25,
    },
};

/* when decreasing the duty cycle, shortly invert the motor
 * direction at full duty to compensate for hysteresis
 */
static motor_boost_params_t boost_params_down = {
    .valid_up_to = 1024,
    .charge_duration = 0,
    .boost_value = -1023,
    .boost_duration = 5,
    .settle_duration = 56,
};

void motor_init(motor_ctx_t *ctx) {
    printf("[MOTOR] init, enable: %d, dira: %d, dirb: %d\n",
        (int) ctx->enable, (int) ctx->dira, (int) ctx->dirb
    );

    gpio_set_direction(ctx->enable, GPIO_MODE_OUTPUT);
    gpio_set_direction(ctx->dira, GPIO_MODE_OUTPUT);
    gpio_set_direction(ctx->dirb, GPIO_MODE_OUTPUT);

    /* set up MCLK signal */
    ledc_timer_config_t ledc_timer = {
        .duty_resolution = LEDC_TIMER_10_BIT,
        .freq_hz = 32000,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_num = ctx->timer
    };
    ledc_timer_config(&ledc_timer);

    ledc_channel_config_t ledc_channel = {
        .channel = ctx->channel,
        .duty = 0,
        .gpio_num = ctx->enable,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .hpoint = 0,
        .timer_sel = ctx->timer
    };
    ledc_channel_config(&ledc_channel);

    gpio_set_level(ctx->dira, 1);
    gpio_set_level(ctx->dirb, 0);

    /* loop mouth open and close */
    // for(;;) {
    //     for (int i = 343; i < 1024; i += 20)
    //         motor_set_duty(ctx, i);
    //     vTaskDelay(100 / portTICK_PERIOD_MS);
    //     for (int i = 1003; i > 463; i -= 20)
    //         motor_set_duty(ctx, i);
    //     vTaskDelay(100 / portTICK_PERIOD_MS);
    // }
}

static void motor_set(motor_ctx_t *ctx, int16_t duty, bool wait_for_duty) {
    int8_t direction = (duty >= 0) ? 1 : -1;
    duty = abs(duty);
    printf("[MOTOR] direction: %d, duty: %d\n", (int) direction, (int) duty);
    if (direction > 0) {
        gpio_set_level(ctx->dira, 1);
        gpio_set_level(ctx->dirb, 0);
    } else if (direction < 0) {
        gpio_set_level(ctx->dira, 0);
        gpio_set_level(ctx->dirb, 1);
    } else {
        gpio_set_level(ctx->dira, 0);
        gpio_set_level(ctx->dirb, 0);
    }
    ledc_set_duty(LEDC_LOW_SPEED_MODE, ctx->channel, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, ctx->channel);
    if (wait_for_duty)
        vTaskDelay(1 / portTICK_PERIOD_MS);
}

static void motor_boost_set(motor_ctx_t *ctx, int16_t duty, motor_boost_params_t *params) {
    printf(
        "[BOOST] charge: %d ms, boost: %d ms at: %d, target: %d, settle: %d ms, total: %d ms\n",
        (int) params->charge_duration,
        (int) params->boost_duration,
        (int) params->boost_value,
        (int) duty,
        (int) params->settle_duration,
        (int) params->charge_duration + 1 + params->boost_duration + 1 + params->settle_duration + 1
    );

    if (params->charge_duration) {
        motor_set(ctx, 0, true);
        vTaskDelay(params->charge_duration / portTICK_PERIOD_MS);
    } else {
        /* ensure constant delay */
        vTaskDelay(1 / portTICK_PERIOD_MS);
    }

    if (params->boost_duration) {
        motor_set(ctx, params->boost_value, true);
        vTaskDelay(params->boost_duration / portTICK_PERIOD_MS);
    } else {
        /* ensure constant delay */
        vTaskDelay(1 / portTICK_PERIOD_MS);
    }

    motor_set(ctx, duty, true);
    if (params->settle_duration)
        vTaskDelay(params->settle_duration / portTICK_PERIOD_MS);
    else
        vTaskDelay(1 / portTICK_PERIOD_MS); // make sure duty is set
}

void motor_set_duty(motor_ctx_t *ctx, int16_t duty)
{
    if (duty < ctx->duty) {
        for (int j = 0; j < sizeof(boost_params_up) / sizeof(boost_params_up[0]); j++) {
            if (duty <= boost_params_up[j].valid_up_to) {
                motor_boost_set(ctx, duty, &boost_params_up[j]);
                break;
            }
        }
    } else {
        // TODO: down should be same as up, motor parameters should be loaded
        motor_boost_set(ctx, duty, &boost_params_down);
    }
}