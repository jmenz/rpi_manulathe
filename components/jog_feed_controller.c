#include "rtapi.h"
#include "rtapi_app.h"
#include "hal.h"
#include "rtapi_math.h"
#include "rtapi_string.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("jmenz");
MODULE_DESCRIPTION("Hybrid Joystick (Velocity) and MPG (Position) Mixer");

#define MAX_INSTANCES 8

// Prints 'fmt' message only once every 1000 calls (approx 1 second)
#define DEBUG_MSG(fmt, ...) \
    do { \
        static int __limiter = 0; \
        if (++__limiter > 1000) { \
            rtapi_print_msg(RTAPI_MSG_ERR, fmt, ##__VA_ARGS__); \
            __limiter = 0; \
        } \
    } while(0)

// --- Module Parameters ---
static char *names[MAX_INSTANCES] = {0,};
RTAPI_MP_ARRAY_STRING(names, MAX_INSTANCES, "Names of instances (e.g. names=x,z)");

// --- Data Structure ---
typedef struct {
    // PINS
    hal_s32_t   *mpg_in;
    hal_float_t *mpg_scale;
    hal_float_t *joy_in;
    hal_bit_t   *joy_btn;

    hal_bit_t   *feed_positive;
    hal_bit_t   *feed_negative;
    hal_float_t *spindle_pos;
    hal_float_t *feed_per_rev;
    
    hal_s32_t   *counts_out;
    hal_bit_t   *vel_mode_out;
    hal_bit_t   *fast_mode_out;

    // PARAMETERS
    hal_float_t joy_deadband;
    hal_float_t joy_speed_slow;
    hal_float_t joy_speed_fast;
    hal_float_t jog_scale;

    // INTERNAL VARIABLES
    hal_s32_t   last_mpg;
    double      internal_accumulator;
    double      last_spindle_pos;
    int         first_run;
    int         last_btn_state;
    int         fast_mode;

} comp_data_t;

static int comp_id;
static comp_data_t *instance_data[MAX_INSTANCES];

static void toggleJogSpeed(comp_data_t *data) {
    hal_bit_t btn_state = *(data->joy_btn);

    // Detect Rising Edge
    if (btn_state && !data->last_btn_state) {
        data->fast_mode = !data->fast_mode;
    }
    
    // Update State
    data->last_btn_state = btn_state;
    *(data->fast_mode_out) = data->fast_mode;
}

static float getJoyValue(comp_data_t *data) {
    float raw_val = *(data->joy_in);
    
    if (raw_val > -data->joy_deadband && raw_val < data->joy_deadband) {
        return 0.0f;
    }

    if (raw_val > 0) 
        return raw_val - data->joy_deadband;
    else             
        return raw_val + data->joy_deadband;
}

static double getJogAccumulatedValue(comp_data_t *data, float joy_val) {
    double delta = 0.0;
    hal_s32_t current_mpg = *(data->mpg_in);

    if (joy_val != 0.0f) {
        // [ MODE: JOYSTICK ]
        *(data->vel_mode_out) = 1; 

        // Calculate velocity increment
        float speed = data->fast_mode ? data->joy_speed_fast : data->joy_speed_slow;
        delta = joy_val * speed;

        data->last_mpg = current_mpg; 
        
    } else {
        // [ MODE: MPG ]
        *(data->vel_mode_out) = 0;

        // Calculate Position Delta
        int mpg_diff = current_mpg - data->last_mpg;

        delta = (double)mpg_diff * *(data->mpg_scale);

        data->last_mpg = current_mpg;
    }

    return delta;
}

static int getFeedDirection(comp_data_t *data) {
    if (*(data->feed_positive)) {
        return 1;
    }

    if (*(data->feed_negative)) {
        return -1;
    }

    return 0;
}

static double getFeedValue(comp_data_t *data) {

    if (data->jog_scale < 0.0000001) return 0.0;

    double current_spindle_pos = *(data->spindle_pos);
    double spindle_rev = current_spindle_pos - data->last_spindle_pos;
    data->last_spindle_pos = current_spindle_pos;

    int feed_dir = getFeedDirection(data);
    if (feed_dir != 0) {
        return spindle_rev * *(data->feed_per_rev) * (1 / data->jog_scale) * feed_dir;
    }

    return 0;
}

static void update(void *arg, long period) {
    comp_data_t *data = (comp_data_t *)arg;

    if (data->first_run) {
        data->last_mpg = *(data->mpg_in);
        data->last_spindle_pos = *(data->spindle_pos);
        data->internal_accumulator = 0.0;
        data->first_run = 0;
    }

    toggleJogSpeed(data);
    float joy_val = getJoyValue(data);
    double move_delta = getJogAccumulatedValue(data, joy_val);
    double feed_data = getFeedValue(data);

    data->internal_accumulator += move_delta + feed_data;

    *(data->counts_out) = (hal_s32_t)data->internal_accumulator;
}

int rtapi_app_main(void) {
    int res = 0;
    int i;
    char name_buf[HAL_NAME_LEN + 1];

    comp_id = hal_init("jog_feed_controller");
    if (comp_id < 0) return comp_id;

    if (names[0] == 0) names[0] = "0";

    for (i = 0; i < MAX_INSTANCES && names[i] != 0; i++) {
        comp_data_t *data = hal_malloc(sizeof(comp_data_t));
        if (!data) goto error;
        instance_data[i] = data;

        // Init Data Defaults
        data->joy_deadband = 0.05;
        data->joy_speed_slow = 100.0;
        data->joy_speed_fast = 5000.0;
        data->jog_scale = 0.0001;
        data->first_run = 1;
        data->internal_accumulator = 0.0;
        data->fast_mode = 1;

        #define PIN_NAME(suffix) rtapi_snprintf(name_buf, sizeof(name_buf), "%s.%s", names[i], suffix)

        PIN_NAME("mpg-in");         res += hal_pin_s32_new(name_buf, HAL_IN, &(data->mpg_in), comp_id);
        PIN_NAME("mpg-scale");      res += hal_pin_float_new(name_buf, HAL_IN, &(data->mpg_scale), comp_id);
        PIN_NAME("joy-in");         res += hal_pin_float_new(name_buf, HAL_IN, &(data->joy_in), comp_id);
        PIN_NAME("joy-btn");        res += hal_pin_bit_new(name_buf, HAL_IN, &(data->joy_btn), comp_id);

        PIN_NAME("feed-positive");  res += hal_pin_bit_new(name_buf, HAL_IN, &(data->feed_positive), comp_id);
        PIN_NAME("feed-negative");  res += hal_pin_bit_new(name_buf, HAL_IN, &(data->feed_negative), comp_id);
        PIN_NAME("spindle-pos");    res += hal_pin_float_new(name_buf, HAL_IN, &(data->spindle_pos), comp_id);
        PIN_NAME("feed-per-rev");    res += hal_pin_float_new(name_buf, HAL_IN, &(data->feed_per_rev), comp_id);

        PIN_NAME("counts-out");     res += hal_pin_s32_new(name_buf, HAL_OUT, &(data->counts_out), comp_id);
        PIN_NAME("vel-mode-out");   res += hal_pin_bit_new(name_buf, HAL_OUT, &(data->vel_mode_out), comp_id);
        PIN_NAME("fast-mode-out");  res += hal_pin_bit_new(name_buf, HAL_OUT, &(data->fast_mode_out), comp_id);

        PIN_NAME("joy-deadband");   res += hal_param_float_new(name_buf, HAL_RW, &(data->joy_deadband), comp_id);
        PIN_NAME("joy-speed-slow"); res += hal_param_float_new(name_buf, HAL_RW, &(data->joy_speed_slow), comp_id);
        PIN_NAME("joy-speed-fast"); res += hal_param_float_new(name_buf, HAL_RW, &(data->joy_speed_fast), comp_id);
        PIN_NAME("jog-scale");      res += hal_param_float_new(name_buf, HAL_RW, &(data->jog_scale), comp_id);

        if (res != 0) goto error;

        PIN_NAME("update");
        res = hal_export_funct(name_buf, update, data, 1, 0, comp_id);
        if (res != 0) goto error;
    }

    hal_ready(comp_id);
    return 0;

error:
    rtapi_print_msg(RTAPI_MSG_ERR, "JOG_MIXER: Setup failed\n");
    hal_exit(comp_id);
    return -1;
}

void rtapi_app_exit(void) {
    hal_exit(comp_id);
}