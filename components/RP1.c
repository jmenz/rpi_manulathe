#include "rtapi.h"
#include "rtapi_app.h"
#include "hal.h"

#include "RP1/rp1lib.h"
#include "RP1/rp1lib.c"
#include "RP1/gpiochip_rp1.h"
#include "RP1/gpiochip_rp1.c"
#include "RP1/spi-dw.h"
#include "RP1/spi-dw.c"

#define COMPONENT_NAME "RP1"
#define MAX_GPIOS 28

static int comp_id;

/* Module Parameters */
char *gpio_in = "";
RTAPI_MP_STRING(gpio_in, "Comma separated list of input GPIOs (e.g., '26,19')");

char *gpio_out = "";
RTAPI_MP_STRING(gpio_out, "Comma separated list of output GPIOs");

char *gpio_pull_up = "";
RTAPI_MP_STRING(gpio_pull_up, "Comma separated list of input GPIOs to pull up");

char *gpio_pull_down = "";
RTAPI_MP_STRING(gpio_pull_down, "Comma separated list of input GPIOs to pull down");

typedef struct {
    int is_used;
    int is_output;
    
    hal_bit_t *in;
    hal_bit_t *in_not;
    
    hal_bit_t *out;
    
    hal_bit_t invert_out; 
} rp1_pin_t;

static rp1_pin_t *pins;


static void parse_gpio_list(const char *list, int *array_out) {
    if (!list || list[0] == '\0') return;
    const char *p = list;
    while (*p) {
        while (*p && (*p < '0' || *p > '9')) p++; 
        if (!*p) break;
        int pin = 0;
        while (*p >= '0' && *p <= '9') {
            pin = pin * 10 + (*p - '0');
            p++;
        }
        if (pin >= 0 && pin < MAX_GPIOS) {
            array_out[pin] = 1;
        } else {
            rtapi_print_msg(RTAPI_MSG_ERR, "%s: Invalid GPIO pin %d ignored.\n", COMPONENT_NAME, pin);
        }
    }
}

static void read_gpio(void *arg, long period)
{
    rp1_pin_t *p = (rp1_pin_t *)arg;
    
    for (int i = 0; i < MAX_GPIOS; i++) {
        if (!p[i].is_used || p[i].is_output) continue;

        int level = gpio_get_level(i);
        if (level >= 0) {
            *(p[i].in) = level;
            *(p[i].in_not) = !level;
        }
    }
}

static void write_gpio(void *arg, long period)
{
    rp1_pin_t *p = (rp1_pin_t *)arg;
    
    for (int i = 0; i < MAX_GPIOS; i++) {
        if (!p[i].is_used || !p[i].is_output) continue;

        int desired_val = *(p[i].out);
        if (p[i].invert_out) {
            desired_val = !desired_val;
        }
        
        if (desired_val) {
            gpio_set(i);
        } else {
            gpio_clear(i);
        }
    }
}

/* Component initialization */
int rtapi_app_main(void)
{
    int i, ret;
    
    comp_id = hal_init(COMPONENT_NAME);
    if (comp_id < 0) {
        rtapi_print_msg(RTAPI_MSG_ERR, "%s: Failed to initialize HAL component\n", COMPONENT_NAME);
        return comp_id;
    }

    pins = hal_malloc(MAX_GPIOS * sizeof(rp1_pin_t));
    if (!pins) {
        rtapi_print_msg(RTAPI_MSG_ERR, "%s: Failed to allocate shared memory\n", COMPONENT_NAME);
        hal_exit(comp_id);
        return -1;
    }

    int pin_in_list[MAX_GPIOS] = {0};
    int pin_out_list[MAX_GPIOS] = {0};
    int pin_pu_list[MAX_GPIOS] = {0};
    int pin_pd_list[MAX_GPIOS] = {0};

    parse_gpio_list(gpio_in, pin_in_list);
    parse_gpio_list(gpio_out, pin_out_list);
    parse_gpio_list(gpio_pull_up, pin_pu_list);
    parse_gpio_list(gpio_pull_down, pin_pd_list);

    if (rp1lib_init() < 0) {
        rtapi_print_msg(RTAPI_MSG_ERR, "%s: Failed to init RP1 /dev/mem mapping.\n", COMPONENT_NAME);
        hal_exit(comp_id);
        return -1;
    }

    for (i = 0; i < MAX_GPIOS; i++) {
        if (pin_in_list[i] && pin_out_list[i]) {
            rtapi_print_msg(RTAPI_MSG_ERR, "%s: Pin %d cannot be both input and output. Ignoring.\n", COMPONENT_NAME, i);
            continue;
        }

        if (pin_in_list[i]) {
            pins[i].is_used = 1;
            pins[i].is_output = 0;

            gpio_set_fsel(i, GPIO_FSEL_INPUT);
            
            if (pin_pu_list[i]) gpio_set_pull(i, PULL_UP);
            else if (pin_pd_list[i]) gpio_set_pull(i, PULL_DOWN);
            else gpio_set_pull(i, PULL_NONE);

            ret = hal_pin_bit_newf(HAL_OUT, &(pins[i].in), comp_id, "%s.in-%02d", COMPONENT_NAME, i);
            ret |= hal_pin_bit_newf(HAL_OUT, &(pins[i].in_not), comp_id, "%s.in-%02d-not", COMPONENT_NAME, i);
            if (ret < 0) goto error;
            
        } else if (pin_out_list[i]) {
            pins[i].is_used = 1;
            pins[i].is_output = 1;

            gpio_set_fsel(i, GPIO_FSEL_OUTPUT);

            ret = hal_pin_bit_newf(HAL_IN, &(pins[i].out), comp_id, "%s.out-%02d", COMPONENT_NAME, i);

            ret |= hal_param_bit_newf(HAL_RW, &(pins[i].invert_out), comp_id, "%s.out-%02d-invert", COMPONENT_NAME, i);
            if (ret < 0) goto error;
            
            pins[i].invert_out = 0; // Default to not inverted
            *(pins[i].out) = 0;     // Default to low
        }
    }

    ret = hal_export_funct("RP1.read-gpio", read_gpio, pins, 0, 0, comp_id);
    if (ret < 0) goto error;

    ret = hal_export_funct("RP1.write-gpio", write_gpio, pins, 0, 0, comp_id);
    if (ret < 0) goto error;

    hal_ready(comp_id);
    rtapi_print_msg(RTAPI_MSG_INFO, "%s: Loaded successfully.\n", COMPONENT_NAME);
    return 0;

error:
    rp1lib_deinit();
    hal_exit(comp_id);
    return -1;
}

/* Component cleanup */
void rtapi_app_exit(void)
{
    rp1lib_deinit();
    hal_exit(comp_id);
    rtapi_print_msg(RTAPI_MSG_INFO, "%s: Exited.\n", COMPONENT_NAME);
}