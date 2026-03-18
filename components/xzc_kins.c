#include "rtapi.h"
#include "rtapi_app.h"
#include "kinematics.h"
#include "hal.h"

static int current_kinstype = 0; // 0 = Lathe, 1 = Mill
static int transition_flag = 0;
static int comp_id;
static float internal_offset = 0;

// Data structure with the dual command pins you suggested
struct hal_data_t {
    hal_float_t *enc_in;         // From Mesa hardware encoder
    hal_float_t *motor_cmd_in;   // From joint.2.motor-pos-cmd (Includes offset)
    hal_float_t *fb_out;         // To joint.2.motor-pos-fb
} *hal_data;

// --------------------------------------------------------
// 1. FORWARD KINEMATICS
// --------------------------------------------------------
int kinematicsForward(const double *joints, EmcPose *pos,
                      const KINEMATICS_FORWARD_FLAGS *fflags,
                      KINEMATICS_INVERSE_FLAGS *iflags) {
    pos->tran.x = joints[0];
    pos->tran.z = joints[1];
    
    if (current_kinstype != 0) pos->c = joints[2];
    
    return 0;
}

// --------------------------------------------------------
// 2. INVERSE KINEMATICS & HAL ROUTING
// --------------------------------------------------------
int kinematicsInverse(const EmcPose *pos, double *joints,
                      const KINEMATICS_INVERSE_FLAGS *iflags,
                      KINEMATICS_FORWARD_FLAGS *fflags) {
    joints[0] = pos->tran.x;
    joints[1] = pos->tran.z;
    joints[2] = pos->c;
    
    if (!hal_data) return 0;

    if (current_kinstype == 0) {
        *(hal_data->fb_out) = *(hal_data->motor_cmd_in);
    } 
    else {
        double scaled_enc = *(hal_data->enc_in) * 360.0;

        if (transition_flag == 1) {
            *(hal_data->fb_out) = *(hal_data->motor_cmd_in); 
            internal_offset = scaled_enc - *(hal_data->motor_cmd_in);
            
            transition_flag = 0; 
        } else {
            *(hal_data->fb_out) = scaled_enc - internal_offset;
        }
    }
    
    return 0;
}

// --------------------------------------------------------
// 3. SWITCH EVENT
// --------------------------------------------------------
KINEMATICS_TYPE kinematicsType(void) { return KINEMATICS_IDENTITY; }
int kinematicsSwitchable(void) { return 1; }

int kinematicsSwitch(int switchkins_type) {
    current_kinstype = switchkins_type;
    if (switchkins_type == 1) transition_flag = 1;
    return 0;
}

// --------------------------------------------------------
// 4. MODULE INITIALIZATION
// --------------------------------------------------------
EXPORT_SYMBOL(kinematicsType);
EXPORT_SYMBOL(kinematicsForward);
EXPORT_SYMBOL(kinematicsInverse);
EXPORT_SYMBOL(kinematicsSwitchable);
EXPORT_SYMBOL(kinematicsSwitch);
MODULE_LICENSE("GPL");

int rtapi_app_main(void) {
    comp_id = hal_init("xzc_kins");
    if (comp_id < 0) return comp_id;

    hal_data = hal_malloc(sizeof(struct hal_data_t));
    if (!hal_data) { hal_exit(comp_id); return -1; }

    hal_pin_float_new("xzc_kins.enc-in", HAL_IN, &(hal_data->enc_in), comp_id);
    hal_pin_float_new("xzc_kins.motor-cmd-in", HAL_IN, &(hal_data->motor_cmd_in), comp_id);
    hal_pin_float_new("xzc_kins.fb-out", HAL_OUT, &(hal_data->fb_out), comp_id);

    *(hal_data->enc_in) = 0.0;
    *(hal_data->motor_cmd_in) = 0.0;
    *(hal_data->fb_out) = 0.0;

    hal_ready(comp_id);
    return 0;
}

void rtapi_app_exit(void) { hal_exit(comp_id); }