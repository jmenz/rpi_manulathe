#include "rtapi.h"
#include "rtapi_app.h"
#include "hal.h"

#define MODE_SPINDLE 0
#define MODE_C_AXIS  1

static int comp_id;
static double internal_offset = 0.0;
static int prev_mode = MODE_SPINDLE;

// The HAL pin structure
struct hal_data_t {
    hal_float_t *enc_in;
    hal_float_t *motor_cmd_in;
    hal_float_t *fb_out;
    hal_bit_t   *mode;
} *hal_data;

// --- REALTIME SERVO THREAD LOGIC ---
void update_mux(void *arg, long period) {
    if (!hal_data) return;

    int current_mode = *(hal_data->mode);

    if (current_mode == MODE_SPINDLE) {
        *(hal_data->fb_out) = *(hal_data->motor_cmd_in);
    } 
    else if (current_mode == MODE_C_AXIS) {
        double scaled_enc = *(hal_data->enc_in) * 360.0;

        if (prev_mode == MODE_SPINDLE) {
            // The transition edge
            *(hal_data->fb_out) = *(hal_data->motor_cmd_in);
            internal_offset = scaled_enc - *(hal_data->motor_cmd_in);
        } else {
            // Normal interpolation
            *(hal_data->fb_out) = scaled_enc - internal_offset;
        }
    }
    
    prev_mode = current_mode;
}

MODULE_LICENSE("GPL");

// --- COMPONENT INITIALIZATION ---
int rtapi_app_main(void) {
    comp_id = hal_init("c_spindle_mux");
    if (comp_id < 0) return comp_id;

    hal_data = hal_malloc(sizeof(struct hal_data_t));
    if (!hal_data) {
        hal_exit(comp_id);
        return -1;
    }

    // Allocate the pins
    hal_pin_float_new("c_spindle_mux.enc-in", HAL_IN, &(hal_data->enc_in), comp_id);
    hal_pin_float_new("c_spindle_mux.motor-cmd-in", HAL_IN, &(hal_data->motor_cmd_in), comp_id);
    hal_pin_float_new("c_spindle_mux.fb-out", HAL_OUT, &(hal_data->fb_out), comp_id);
    hal_pin_bit_new("c_spindle_mux.mode", HAL_IN, &(hal_data->mode), comp_id);

    // Initial states
    *(hal_data->enc_in) = 0.0;
    *(hal_data->motor_cmd_in) = 0.0;
    *(hal_data->fb_out) = 0.0;
    *(hal_data->mode) = MODE_SPINDLE;

    // Export the update loop
    hal_export_funct("c_spindle_mux.update", update_mux, hal_data, 1, 0, comp_id);

    hal_ready(comp_id);
    return 0;
}

void rtapi_app_exit(void) {
    hal_exit(comp_id);
}