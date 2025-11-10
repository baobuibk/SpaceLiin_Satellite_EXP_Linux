/*
 * Interface: CAN0 @ 1000.000
 * EXP-SATELLITE ESAT93
 */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>

#include "exp_csp.h"
#include "exp_server.h"
#include "exp_handler.h"
#include "exp_table.h"

/* ========== Client ========== */
#define OBC_CLIENT_ADDRESS     1 

/* ========== EXP-SAT ========== */
#define EXP_A55_SERVER_ADDRESS 11

/*============================================================*/
/*              Private Function Prototypes                   */
/*============================================================*/
bool is_simulation = false;

static void ex_idle(int ms)
{
    usleep(ms * 1000);
}

/*============================================================*/
/*                Function Implementations                    */
/*============================================================*/
int main(int argc, char * argv[])
{
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-sim") == 0) {
            is_simulation = true;
            break;
        }
    }

    printf("Simulation mode: %s\n", is_simulation ? "ON" : "OFF");

    // preparing_hardware(&exp_server);

    // init_microservices_framework();

    // init_handlers(&exp_server);

    // init_mem_table(&exp_server);

    // Initialize CSP
    
    exp_csp_init(EXP_A55_SERVER_ADDRESS, is_simulation);

    exp_csp_linux_init();

    exp_csp_start(false);

    // Start console for handling commands.
    // gs_console_start(GS_BUILD_INFO_APPNAME, 0);

    while (1) {
        ex_idle(1000);
    }

    return 0;
}


