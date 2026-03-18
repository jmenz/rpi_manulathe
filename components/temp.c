#include "rtapi.h"
#include "rtapi_app.h"
#include "kinematics.h"
#include "hal.h"

int current_kinstype = 0; // 0 = Lathe, 1 = Mill
int comp_id;
double encoder_offset = 0.0;

// The data structure for our custom HAL clutch pins
struct hal_data_t {
    hal_float_t *enc_in;
    hal_float_t *cmd_in;
    hal_float_t *fb_out;
} *hal_data;

// --------------------------------------------------------
// 1. THE KINEMATICS (The Trajectory Math)
// --------------------------------------------------------
int kinematicsForward(const double *joints, EmcPose *pos,
                      const KINEMATICS_FORWARD_FLAGS *fflags,
                      KINEMATICS_INVERSE_FLAGS *iflags) {
    pos->tran.x = joints[0];
    pos->tran.z = joints[1];
    
    if (current_kinstype == 0) pos->c = 0.0; 
    else pos->c = joints[2];
    
    return 0;
}

int kinematicsInverse(const EmcPose *pos, double *joints,
                      const KINEMATICS_INVERSE_FLAGS *iflags,
                      KINEMATICS_FORWARD_FLAGS *fflags) {
    joints[0] = pos->tran.x;
    joints[1] = pos->tran.z;
    
    if (current_kinstype == 1) joints[2] = pos->c;
    
    return 0;
}

KINEMATICS_TYPE kinematicsType(void) { return KINEMATICS_IDENTITY; } // Keeps Touchy happy
int kinematicsSwitchable(void) { return 1; }

int kinematicsSwitch(int switchkins_type) {
    current_kinstype = switchkins_type;
    return 0;
}

// --------------------------------------------------------
// 2. THE HARDWARE CLUTCH (The Realtime Loop)
// --------------------------------------------------------
void update_clutch(void *arg, long period) {
    if (current_kinstype == 0) {
        // Lathe Mode: Mux the frozen command directly to the feedback
        *(hal_data->fb_out) = *(hal_data->cmd_in);
        // Silently track the distance the spindle spins away from the command
        encoder_offset = *(hal_data->enc_in) - *(hal_data->cmd_in);
    } else {
        // Mill Mode: Subtract the exact frozen offset from the real encoder
        *(hal_data->fb_out) = *(hal_data->enc_in) - encoder_offset;
    }
}

// --------------------------------------------------------
// 3. MODULE EXPORTS & INITIALIZATION
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

    // Allocate memory for our custom pins
    hal_data = hal_malloc(sizeof(struct hal_data_t));
    if (!hal_data) {
        hal_exit(comp_id);
        return -1;
    }

    // Create the three pins for the encoder clutch
    hal_pin_float_new("xzc_kins.enc-in", HAL_IN, &(hal_data->enc_in), comp_id);
    hal_pin_float_new("xzc_kins.cmd-in", HAL_IN, &(hal_data->cmd_in), comp_id);
    hal_pin_float_new("xzc_kins.fb-out", HAL_OUT, &(hal_data->fb_out), comp_id);

    // Export our clutch function so it can be added to the servo-thread
    hal_export_funct("xzc_kins.update", update_clutch, hal_data, 1, 0, comp_id);

    hal_ready(comp_id);
    return 0;
}

void rtapi_app_exit(void) { hal_exit(comp_id); }