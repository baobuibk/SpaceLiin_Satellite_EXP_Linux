#define SIMULATION
/************************************************
 *  @file     : exp_csp.c
 *  @date     : October 2025
 *  @author   : CAO HIEU
 *  @version  : 1.0.0
 *-----------------------------------------------
 *  Description :
 *    [-]
 ************************************************/

#include "exp_csp.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sys/sysinfo.h>
#include <dirent.h>
#include <sys/stat.h>
#include <ctype.h>
#include <stddef.h>
#include <sys/reboot.h>   
#include <linux/reboot.h>
#include <errno.h>

#include <csp/csp.h>
#include <csp/arch/csp_thread.h>
#include <csp/drivers/can_socketcan.h>
#include <csp/arch/csp_system.h>
#include <csp/arch/posix/csp_system.h>
#include <csp/csp_debug.h>

#include "exp_table.h"
#include "exp_filesystem.h" 

#define CAN_BITRATE 1000000
/* ========== BEE-PROJECT Ports ========== */
#define BEE_A55_PARAMS 7
/*============================================================*/
/*                      Defines                               */
/*============================================================*/
static int imx93_reboot_hook(void) {
    csp_log_info("[exp_csp] >>> Reboot hook called (i.MX93/Linux)");
    fflush(stdout);

    sync(); 

    if (reboot(LINUX_REBOOT_CMD_RESTART) == 0) {
        return CSP_ERR_NONE;
    }

    int err = errno;
    csp_log_warn("[exp_csp] reboot() failed, errno=%d", err);
    printf("[exp_csp] reboot() failed, errno=%d\n", err);
    return CSP_ERR_INVAL;
}

static int imx93_shutdown_hook(void) {
    csp_log_info("[exp_csp] >>> Shutdown hook called (i.MX93/Linux)");
    fflush(stdout);

    sync();

    if (reboot(LINUX_REBOOT_CMD_POWER_OFF) == 0) {
        return CSP_ERR_NONE;
    }

    int err = errno;
    csp_log_warn("[exp_csp] poweroff() failed, errno=%d", err);
    printf("[exp_csp] poweroff() failed, errno=%d\n", err);
    return CSP_ERR_INVAL;
}

uint32_t get_uptime(void)
{
    struct sysinfo info;
    if (sysinfo(&info) == 0)
    {
        return (uint32_t)info.uptime;
    }
    return 0;
}

void exp_csp_linux_init(void) {
    csp_sys_set_reboot(imx93_reboot_hook);
    csp_sys_set_shutdown(imx93_shutdown_hook);

    csp_log_info("[exp_csp] Registered i.MX93/Linux reboot/shutdown hooks");
    fflush(stdout);
}

/*============================================================*/
/*              Private Function Prototypes                   */
/*============================================================*/
void handle_BEE_A55_PARAMS(csp_conn_t *conn, csp_packet_t *packet);
csp_iface_t *can_iface = NULL;
uint32_t request_count = 0;
uint32_t boot_time = 0;

csp_debug_level_t debug_level = CSP_INFO;
/*============================================================*/
/*                Function Implementations                    */
/*============================================================*/
typedef void (*exp_csp_handler_t)(csp_conn_t *conn, csp_packet_t *packet);

typedef struct {
    const char *name;
    bool bind_any;
    const exp_csp_handler_t *handlers;
    size_t handler_count;
    int listen_backlog;
} exp_csp_dispatch_conf_t;

/*============================================================*/
/*                     Handler Table                          */
/*============================================================*/

static exp_csp_handler_t exp_csp_handlers[] = {
    [CSP_CMP]           = csp_service_handler,
    [CSP_PING]          = csp_service_handler,
    [CSP_PS]            = csp_service_handler,
    [CSP_REBOOT]        = csp_service_handler,
    [CSP_BUF_FREE]      = csp_service_handler,
    [CSP_MEMFREE]       = csp_service_handler,
    [CSP_UPTIME]        = csp_service_handler,
    [BEE_A55_PARAMS]    = handle_BEE_A55_PARAMS,
};
/*============================================================*/
/*                     Dispatcher Config                      */
/*============================================================*/
static exp_csp_dispatch_conf_t exp_dispatch_conf = {
    .name           = "EXP_CSP_SERVER",
    .bind_any       = true,
    .handlers       = exp_csp_handlers,
    .handler_count  = sizeof(exp_csp_handlers) / sizeof(exp_csp_handlers[0]),
    .listen_backlog = 10,
};

/* ========== BEE Control Register Addresses ========== */

/* ========== Server Task ========== */
/**
 * @brief Dispatcher task: wait for connection, route to handlers
 */
CSP_DEFINE_TASK(exp_csp_dispatch_task)
{
    csp_socket_t *sock = (csp_socket_t *)param;

    while (1) {
        csp_conn_t *conn = csp_accept(sock, 1000);
        if (!conn)
            continue;

        uint8_t port = csp_conn_dport(conn);
        request_count++;

        csp_log_info("[CONN] Node %u -> Port %u", csp_conn_src(conn), port);

        csp_packet_t *packet = NULL;
        while ((packet = csp_read(conn, 100)) != NULL) {
            if (port < exp_dispatch_conf.handler_count &&
                exp_dispatch_conf.handlers[port]) {

                exp_dispatch_conf.handlers[port](conn, packet);
            } else {
                csp_log_warn("[DISPATCH] Unknown port %u", port);
                csp_service_handler(conn, packet);
            }
        }

        csp_close(conn);
    }
    return CSP_TASK_RETURN;
}

/**
 * @brief Optional stats task
 */
CSP_DEFINE_TASK(task_stats) {
    while (1) {
        csp_sleep_ms(10000);
        printf("\n--- CSP Statistics ---\n");
        printf("Requests handled: %u\n", request_count);
        printf("Buffers free: %u\n", csp_buffer_remaining());
        printf("Uptime: %u s\n", get_uptime());
        printf("----------------------\n\n");
    }
    return CSP_TASK_RETURN;
}


/**
 * @brief Initialize CSP stack and interfaces
 */
void exp_csp_init(uint8_t address, bool sim_mode) {

    if (sim_mode)
        bee_set_db_path("/home/steven/bee_params.db");
    else
        bee_set_db_path("/data/.a55_src/bee_params.db");

    printf("[BEE_SQL] Using DB path: %s\n", sim_mode ? "/home/steven/bee_params.db" : "/data/.a55_src/bee_params.db");

    bee_sqlite_task_start();

    bee_unix_init();

    bee_sqlite_boot_update();

    bee_table_init();

    const char *can_interface_name = sim_mode ? "vcan0" : "can0";

    for (csp_debug_level_t i = 0; i <= CSP_LOCK; i++) {
        csp_debug_set_level(i, (i <= debug_level) ? true : false);
    }

    csp_log_info("Initializing CSP...");

    csp_conf_t conf;
    csp_conf_get_defaults(&conf);
    conf.address = address;

    int err = csp_init(&conf);
    if (err != CSP_ERR_NONE) {
        csp_log_error("csp_init() failed, err=%d", err);
        exit(1);
    }

    // Router task
    csp_route_start_task(500, 0);

    // Add CAN interface
    csp_log_info("Adding CAN interface: %s", can_interface_name);
    err = csp_can_socketcan_open_and_add_interface(
        can_interface_name,
        CSP_IF_CAN_DEFAULT_NAME,
        0, false, &can_iface
    );
    if (err != CSP_ERR_NONE) {
        csp_log_error("Failed to add CAN iface [%s], err=%d", can_interface_name, err);
        exit(1);
    }

    // Default route
    csp_rtable_set(CSP_DEFAULT_ROUTE, 0, can_iface, CSP_NO_VIA_ADDRESS);

    printf("\n--- CSP Initialized ---\n");
    csp_route_print_table();
    printf("------------------------\n\n");
}

/**
 * @brief Create dispatcher and start its task
 */
void exp_csp_start_dispatcher(void) {
    csp_log_info("[%s] Creating dispatcher...", exp_dispatch_conf.name);

    csp_socket_t *sock = csp_socket(CSP_SO_NONE);
    if (!sock) {
        csp_log_error("[%s] Failed to create socket", exp_dispatch_conf.name);
        return;
    }

    // Bind handlers
    for (uint8_t port = 0; port < exp_dispatch_conf.handler_count; port++) {
        if (exp_dispatch_conf.handlers[port]) {
            int res = csp_bind(sock, port);
            if (res != CSP_ERR_NONE) {
                csp_log_warn("[%s] csp_bind failed for port %u", exp_dispatch_conf.name, port);
            }
        }
    }

    // Bind any (optional)
    if (exp_dispatch_conf.bind_any) {
        csp_bind(sock, CSP_ANY);
    }

    csp_listen(sock, exp_dispatch_conf.listen_backlog);
    csp_log_info("[%s] Listening on all ports...", exp_dispatch_conf.name);

    // Launch dispatcher task
    csp_thread_handle_t dispatch_thread;
    csp_thread_create(exp_csp_dispatch_task, exp_dispatch_conf.name, 2048, sock, 0, &dispatch_thread);
}


/**
 * @brief Public start function (init + dispatcher + stats)
 */
void exp_csp_start(bool enable_stats) {
    exp_csp_start_dispatcher();

    if (enable_stats) {
        csp_thread_handle_t stats_handle;
        csp_thread_create(task_stats, "CSP_STATS", 1024, NULL, 0, &stats_handle);
    }
}

//-----------------------------------------------------------------------------------
/*==================== BEE_A55_PARAMS Handler ====================*/

void handle_BEE_A55_TABLE7(csp_conn_t *conn, csp_packet_t *packet, uint16_t addr, uint8_t op_type) {
    printf("[BEE_A55_TABLE7] addr=0x%04X op=%s len=%u\n",
           addr, (op_type == 0x1) ? "READ" : "WRITE", packet->length);

    // Chuẩn bị buffer phản hồi
    uint8_t outbuf[1024];
    size_t outlen = 0;

    // Tùy theo READ/WRITE: xác định payload thực gửi vào fs_handle_cmd()
    const uint8_t *payload = NULL;
    size_t paylen = 0;

    if (op_type == 0x0) { // WRITE
        if (packet->length > 2) {
            payload = &packet->data[2];
            paylen  = packet->length - 2;
        }
    } else if (op_type == 0x1) { // READ
        // Không truyền dữ liệu vào, fs_handle_cmd() sẽ tự xử lý
        payload = NULL;
        paylen  = 0;
    }

    int rc = fs_handle_cmd(addr, payload, paylen, outbuf, &outlen);

    if (rc < 0) {
        printf("[BEE_A55_TABLE7] fs_handle_cmd failed (%d)\n", rc);
        csp_buffer_free(packet);
        return;
    }

    packet->data[0] = (addr >> 8) & 0xFF;
    packet->data[1] = addr & 0xFF;
    memcpy(&packet->data[2], outbuf, outlen);
    packet->length = 2 + outlen;

    printf("[BEE_A55_TABLE7] RESP len=%zu rc=%d\n", outlen, rc);

    if (!csp_send(conn, packet, 0))
        csp_buffer_free(packet);
}

static void handle_BEE_RW_common(csp_conn_t *conn, csp_packet_t *packet,
                                 uint16_t addr, uint8_t op_type) {
    bee_param_t *param = bee_param_lookup(addr);

    if (!param) {
        printf("[BEE] Unknown addr 0x%04X\n", addr);
        csp_buffer_free(packet);
        return;
    }

    // --- WRITE ---
    if (op_type == 0x0) {
        if (!(param->access & BEE_ACCESS_W)) {
            printf("[BEE] Addr 0x%04X is Read-Only → ignore\n", addr);
            csp_buffer_free(packet);
            return;
        }
        if (packet->length < 6) {
            printf("[BEE] Invalid write len\n");
            csp_buffer_free(packet);
            return;
        }

        uint32_t val = ((uint32_t)packet->data[2] << 24) |
                       ((uint32_t)packet->data[3] << 16) |
                       ((uint32_t)packet->data[4] << 8) |
                       packet->data[5];

        if (addr == 0x0100) {
            param->value = val;
            printf("[BEE] WRITE time_sync = %u (epoch)\n", val);
            if (param->on_write)
                param->on_write(addr, val);
        } else {
            param->value = val;
            if (param->on_write)
                param->on_write(addr, val);
            printf("[BEE] WRITE 0x%04X (%s)=0x%08X\n", addr, param->name, val);
        }
    }

    // --- READ ---
    else if (op_type == 0x1) {
        if (!(param->access & BEE_ACCESS_R)) {
            printf("[BEE] Addr 0x%04X is Write-Only → ignore\n", addr);
            csp_buffer_free(packet);
            return;
        }

        uint32_t val;

        if (addr == 0x0100) {
            val = (uint32_t)time(NULL); 
            printf("[BEE] READ time_sync → %u (epoch)\n", val);
        } else {
            if (param->on_read)
                param->on_read(addr);
            val = param->value;
            printf("[BEE] READ 0x%04X (%s)=0x%08X\n", addr, param->name, val);
        }

        packet->data[0] = (addr >> 8) & 0xFF;
        packet->data[1] = addr & 0xFF;
        packet->data[2] = (val >> 24) & 0xFF;
        packet->data[3] = (val >> 16) & 0xFF;
        packet->data[4] = (val >> 8) & 0xFF;
        packet->data[5] = val & 0xFF;
        packet->length = 6;
    }

    if (!csp_send(conn, packet, 0))
        csp_buffer_free(packet);
}


void handle_BEE_A55_PARAMS(csp_conn_t *conn, csp_packet_t *packet) {
    uint8_t addr_H = packet->data[0];
    uint8_t addr_L = packet->data[1];

    uint8_t op_type = (addr_H & 0xF0) >> 4;  
    uint16_t addr = (((uint16_t)(addr_H & 0x0F)) << 8) | addr_L;

    printf("[BEE_A55_PARAMS] rawH=0x%02X addr=0x%04X op=%s len=%u\n",
           addr_H, addr, (op_type == 0x1) ? "READ" : "WRITE", packet->length);

    if (((addr & 0xFF00) == 0x0700) && (addr != 0x0700)) {
        handle_BEE_A55_TABLE7(conn, packet, addr, op_type);
        return;
    }

    handle_BEE_RW_common(conn, packet, addr, op_type);
}


