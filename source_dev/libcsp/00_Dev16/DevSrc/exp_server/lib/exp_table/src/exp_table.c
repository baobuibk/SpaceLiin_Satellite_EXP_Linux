/************************************************
 *  @file     : exp_table.c
 *  @date     : October 2025
 *  @author   : CAO HIEU
 *  @version  : 1.0.1
 *-----------------------------------------------
 *  Description :
 *    [BEE Parameter Table + SQLite3 sync thread]
 ************************************************/
#include <time.h>
#include "exp_table.h"
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <sqlite3.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/wait.h>

static const char *DB_PATH = "/home/steven/bee_params.db";

void bee_set_db_path(const char *path) {
    DB_PATH = path;
}


#define UPDATE_PERIOD_SEC 5
// ======================================================================
//                          CALLBACK DEFINITIONS
// ======================================================================

// -------------------- TABLE 1: System Control --------------------
void cb_time_sync_write(uint16_t addr, uint32_t val) {
    (void)addr;

    bee_unix_pub_event("time_sync", val);

    time_t t = (time_t)val;
    struct tm *tm_info = gmtime(&t);
    if (!tm_info) return;

    char cmd[128];
    strftime(cmd, sizeof(cmd), "date -u -s \"%Y-%m-%d %H:%M:%S\"", tm_info);
    printf("[TIME_SYNC] Set system time: %s\n", cmd);

    int ret;
    ret = system(cmd);
    if (ret != 0)
        fprintf(stderr, "[TIME_SYNC] Failed to run '%s' (ret=%d)\n", cmd, ret);

    ret = system("hwclock -w");
    if (ret != 0)
        fprintf(stderr, "[TIME_SYNC] Failed to sync hwclock (ret=%d)\n", ret);
}

void cb_pwr_ifb_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_ifb_en (0x%04X) -> %u\n", addr, val);

    char cmd[128];
    if (val == 0) {
        // (set GPIO 17 = 1)
        snprintf(cmd, sizeof(cmd), "gpioset -t0 -c gpiochip0 17=1");
    } else if (val == 1) {
        // (set GPIO 17 = 0)
        snprintf(cmd, sizeof(cmd), "gpioset -t0 -c gpiochip0 17=0");
    } else {
        return;
    }

    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "[CB] Failed to run command: %s (ret=%d)\n", cmd, ret);
    }
}

void cb_pwr_io_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_io_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pwr_io_en", val);
}

void cb_pwr_pzp_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_pzp_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pwr_pzp_en", val);
}

void cb_pwr_htr_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_htr_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pwr_htr_en", val);
}

void cb_pwr_sln_tec_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_sln_tec_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pwr_sln_tec_en", val);
}

void cb_pwr_lda_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_lda_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pwr_lda_en", val);
}

void cb_pwr_pda_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_pda_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pwr_pda_en", val);
}

void cb_pwr_usb_0_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_usb_0_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pwr_usb_0_en", val);
}

void cb_pwr_usb_1_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pwr_usb_1_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pwr_usb_1_en", val);
}

void i2c_s_1_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] i2c_s_1_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("i2c_s_1_en", val);
}

void i2c_s_2_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] i2c_s_2_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("i2c_s_2_en", val);
}

void i2c_pwm_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] i2c_pwm_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("i2c_pwm_en", val);
}

void i2c_hd4_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] i2c_hd4_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("i2c_hd4_en", val);
}

void i2c_ld_1_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] i2c_ld_1_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("i2c_ld_1_en", val);
}

void i2c_ld_2_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] i2c_ld_2_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("i2c_ld_2_en", val);
}

void tec_0_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] tec_0_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("tec_0_en", val);
}

void tec_1_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] tec_1_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("tec_1_en", val);
}

void tec_2_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] tec_2_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("tec_2_en", val);
}

void tec_3_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] tec_3_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("tec_3_en", val);
}

void usb_led_1_write(uint16_t addr, uint32_t val)
{
    printf("[CB] usb_led_1_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("usb_led_1_set", val);
}

void usb_led_2_write(uint16_t addr, uint32_t val)
{
    printf("[CB] usb_led_2_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("usb_led_2_set", val);
}

void htr_0_write(uint16_t addr, uint32_t val)
{
    printf("[CB] htr_0_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("htr_0_set", val);
}

void htr_1_write(uint16_t addr, uint32_t val)
{
    printf("[CB] htr_1_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("htr_1_set", val);
}

void htr_2_write(uint16_t addr, uint32_t val)
{
    printf("[CB] htr_2_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("htr_2_set", val);
}

void htr_3_write(uint16_t addr, uint32_t val)
{
    printf("[CB] htr_3_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("htr_3_set", val);
}

void htr_4_write(uint16_t addr, uint32_t val)
{
    printf("[CB] htr_4_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("htr_4_set", val);
}

void htr_5_write(uint16_t addr, uint32_t val)
{
    printf("[CB] htr_5_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("htr_5_set", val);
}

void htr_6_write(uint16_t addr, uint32_t val)
{
    printf("[CB] htr_6_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("htr_6_set", val);
}

void htr_7_write(uint16_t addr, uint32_t val)
{
    printf("[CB] htr_7_set (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("htr_7_set", val);
}

void custom_cmd_write(uint16_t addr, uint32_t val)
{
    printf("[CB] custom_cmd (0x%04X) executed with value %u\n", addr, val);
}

// -------------------- TABLE 2: Fluidic Control --------------------
void cb_pump_1_ctl_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pump_1_ctl (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pump_1_ctl", val);
}

void cb_pump_1_volt_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pump_1_volt (0x%04X) -> %uV\n", addr, val);
    bee_unix_pub_event("pump_1_volt", val);
}

void cb_pump_1_freq_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pump_1_freq (0x%04X) -> %uHz\n", addr, val);
    bee_unix_pub_event("pump_1_freq", val);
}

void cb_pump_2_ctl_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pump_2_ctl (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("pump_2_ctl", val);
}

void cb_pump_2_volt_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pump_2_volt (0x%04X) -> %uV\n", addr, val);
    bee_unix_pub_event("pump_2_volt", val);
}

void cb_pump_2_freq_write(uint16_t addr, uint32_t val)
{
    printf("[CB] pump_2_freq (0x%04X) -> %uHz\n", addr, val);
    bee_unix_pub_event("pump_2_freq", val);
}

void cb_sln_0_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_0_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_0_ctl", val);
}

void cb_sln_1_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_1_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_1_ctl", val);
}

void cb_sln_2_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_2_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_2_ctl", val);
}

void cb_sln_3_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_3_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_3_ctl", val);
}

void cb_sln_4_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_4_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_4_ctl", val);
}

void cb_sln_5_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_5_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_5_ctl", val);
}

void cb_sln_6_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_6_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_6_ctl", val);
}

void cb_sln_7_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_7_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_7_ctl", val);
}

void cb_sln_8_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_8_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_8_ctl", val);
}

void cb_sln_9_ctl_write (uint16_t addr, uint32_t val)
{
    printf("[CB] sln_9_ctl  (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_9_ctl", val);
}

void cb_sln_10_ctl_write(uint16_t addr, uint32_t val)
{
    printf("[CB] sln_10_ctl (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_10_ctl", val);
}

void cb_sln_11_ctl_write(uint16_t addr, uint32_t val)
{
    printf("[CB] sln_11_ctl (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_11_ctl", val);
}

void cb_sln_valve_1_ctl_write(uint16_t addr, uint32_t val)
{
    printf("[CB] sln_valve_1_ctl (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_valve_1_ctl", val);
}

void cb_sln_valve_2_ctl_write(uint16_t addr, uint32_t val)
{
    printf("[CB] sln_valve_2_ctl (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("sln_valve_2_ctl", val);
}

// ======================================================================
//                  TABLE 3: Thermal Profile Configurations
// ======================================================================

void cb_temp_master_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_master_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_master_en", val);
}

void cb_temp_p_1_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_1_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_1_en", val);
}

void cb_temp_p_2_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_2_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_2_en", val);
}

void cb_temp_p_3_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_3_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_3_en", val);
}

void cb_temp_p_4_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_4_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_4_en", val);
}

void cb_temp_p_5_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_5_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_5_en", val);
}

void cb_temp_p_6_en_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_6_en (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_6_en", val);
}

// -------------------- Profile 1 --------------------
void cb_temp_p_1_setpoint_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_1_setpoint (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_1_setpoint", val);
}

void cb_temp_p_1_ntcp_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_1_ntcp (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_1_ntcp", val);
}

void cb_temp_p_1_ntcs_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_1_ntcs (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_1_ntcs", val);
}

void cb_temp_p_1_htr_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_1_htr (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_1_htr", val);
}

void cb_temp_p_1_tec_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_1_tec (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_1_tec", val);
}

// -------------------- Profile 2 --------------------
void cb_temp_p_2_setpoint_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_2_setpoint (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_2_setpoint", val);
}

void cb_temp_p_2_ntcp_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_2_ntcp (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_2_ntcp", val);
}

void cb_temp_p_2_ntcs_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_2_ntcs (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_2_ntcs", val);
}

void cb_temp_p_2_htr_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_2_htr (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_2_htr", val);
}

void cb_temp_p_2_tec_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_2_tec (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_2_tec", val);
}

// -------------------- Profile 3 --------------------
void cb_temp_p_3_setpoint_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_3_setpoint (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_3_setpoint", val);
}

void cb_temp_p_3_ntcp_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_3_ntcp (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_3_ntcp", val);
}

void cb_temp_p_3_ntcs_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_3_ntcs (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_3_ntcs", val);
}

void cb_temp_p_3_htr_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_3_htr (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_3_htr", val);
}

void cb_temp_p_3_tec_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_3_tec (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_3_tec", val);
}

// -------------------- Profile 4 --------------------
void cb_temp_p_4_setpoint_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_4_setpoint (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_4_setpoint", val);
}

void cb_temp_p_4_ntcp_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_4_ntcp (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_4_ntcp", val);
}

void cb_temp_p_4_ntcs_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_4_ntcs (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_4_ntcs", val);
}

void cb_temp_p_4_htr_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_4_htr (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_4_htr", val);
}

void cb_temp_p_4_tec_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_4_tec (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_4_tec", val);
}

// -------------------- Profile 5 --------------------
void cb_temp_p_5_setpoint_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_5_setpoint (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_5_setpoint", val);
}

void cb_temp_p_5_ntcp_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_5_ntcp (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_5_ntcp", val);
}

void cb_temp_p_5_ntcs_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_5_ntcs (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_5_ntcs", val);
}

void cb_temp_p_5_htr_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_5_htr (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_5_htr", val);
}

void cb_temp_p_5_tec_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_5_tec (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_5_tec", val);
}

// -------------------- Profile 6 --------------------
void cb_temp_p_6_setpoint_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_6_setpoint (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_6_setpoint", val);
}

void cb_temp_p_6_ntcp_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_6_ntcp (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_6_ntcp", val);
}

void cb_temp_p_6_ntcs_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_6_ntcs (0x%04X) -> 0x%08X\n", addr, val);
    bee_unix_pub_event("temp_p_6_ntcs", val);
}

void cb_temp_p_6_htr_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_6_htr (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_6_htr", val);
}

void cb_temp_p_6_tec_write(uint16_t addr, uint32_t val)
{
    printf("[CB] temp_p_6_tec (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("temp_p_6_tec", val);
}


// -------------------- TABLE 5: Experiment Control --------------------
void cb_test_ls_current_write(uint16_t addr, uint32_t val)
{
    printf("[CB] test_ls_current (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("test_ls_current", val);
}

void cb_test_fluidic_seq_write(uint16_t addr, uint32_t val)
{
    printf("[CB] test_fluidic_seq (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("test_fluidic_seq", val);
}

void cb_exp_fluidic_seq_write(uint16_t addr, uint32_t val)
{
    printf("[CB] exp_fluidic_seq (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("exp_fluidic_seq", val);
}

void cb_exp_mon_delay_start(uint16_t addr, uint32_t val)
{
    printf("[CB] exp_mon_start (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("exp_mon_start", val);
}

void cb_exp_mon_delay_write(uint16_t addr, uint32_t val)
{
    printf("[CB] exp_mon_delay (0x%04X) -> %u sec\n", addr, val);
    bee_unix_pub_event("exp_mon_delay", val);
}

void cb_exp_mon_interval_write(uint16_t addr, uint32_t val)
{
    printf("[CB] exp_mon_interval (0x%04X) -> %u sec\n", addr, val);
    bee_unix_pub_event("exp_mon_interval", val);
}

void cb_dls_ls_intensity_write(uint16_t addr, uint32_t val)
{
    printf("[CB] dls_ls_intensity (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("dls_ls_intensity", val);
}

void cb_cam_ls_intensity_write(uint16_t addr, uint32_t val)
{
    printf("[CB] cam_ls_intensity (0x%04X) -> %u%%\n", addr, val);
    bee_unix_pub_event("cam_ls_intensity", val);
}

void cb_exp_samp_rate_write(uint16_t addr, uint32_t val)
{
    printf("[CB] exp_samp_rate (0x%04X) -> %u KSPS\n", addr, val);
    bee_unix_pub_event("exp_samp_rate", val);
}

void cb_exp_pre_time_write(uint16_t addr, uint32_t val)
{
    printf("[CB] exp_pre_time (0x%04X) -> %u sec\n", addr, val);
    bee_unix_pub_event("exp_pre_time", val);
}

void cb_exp_samp_time_write(uint16_t addr, uint32_t val)
{
    printf("[CB] exp_samp_time (0x%04X) -> %u sec\n", addr, val);
    bee_unix_pub_event("exp_samp_time", val);
}

void cb_exp_post_time_write(uint16_t addr, uint32_t val)
{
    printf("[CB] exp_post_time (0x%04X) -> %u sec\n", addr, val);
    bee_unix_pub_event("exp_post_time", val);
}

void cb_custom_ctl_write(uint16_t addr, uint32_t val)
{
    printf("[CB] custom_ctl (0x%04X) -> %u\n", addr, val);
    bee_unix_pub_event("custom_ctl", val);
}

void cb_cis_cam_capture_write(uint16_t addr, uint32_t val)
{
    printf("[CB] cis_cam_capture (0x%04X) -> %u\n", addr, val);

    if (val == 1) {
        printf("[CB] Start CIS camera capture sequence (CAM0–CAM3)...\n");

        // Chụp lần lượt 4 cam mỗi 10s
        for (int cam = 0; cam < 4; cam++) {
            char cmd[256];
            snprintf(cmd, sizeof(cmd),
                     "python3 /home/root/tools/capture.py %d --oneshot", cam);
            printf(" → %s\n", cmd);
            int ret = system(cmd);
            if (ret != 0)
                fprintf(stderr, "[CB] capture.py CAM%d failed (ret=%d)\n", cam, ret);

            sleep(10); // chờ 10s giữa các camera
        }

        // Reset thanh ghi về 0 sau khi xong
        bee_param_t *p = bee_param_lookup(addr);
        if (p) p->value = 0;
        printf("[CB] cis_cam_capture sequence done → reset to 0\n");
    }
}

void cb_usb_cam_capture_write(uint16_t addr, uint32_t val)
{
    printf("[CB] usb_cam_capture (0x%04X) -> %u\n", addr, val);

    if (val == 1) {
        printf("[CB] Start USB camera capture...\n");
        char cmd[256];
        snprintf(cmd, sizeof(cmd),
                 "python3 /home/root/tools/capture.py 4 --oneshot");
        printf(" → %s\n", cmd);
        int ret = system(cmd);
        if (ret != 0)
            fprintf(stderr, "[CB] capture.py USB failed (ret=%d)\n", ret);

        // Reset lại 0
        bee_param_t *p = bee_param_lookup(addr);
        if (p) p->value = 0;
        printf("[CB] usb_cam_capture done → reset to 0\n");
    }
}
// -------------------- TABLE 7: Data Size Configuration --------------------
static void cb_data_size_cfg_write(uint16_t addr, uint32_t val) {
    (void)addr;
    printf("[TABLE7] data_size_config (RAM only) set to %u bytes\n", val);
}

//---------------------------------------------------------------------------------------------------------
// ===================== TABLE 1 =====================
static bee_param_t bee_table1[] = {
    {0x0100, "time_sync",     0, BEE_ACCESS_RW, NULL,       cb_time_sync_write},
    {0x0101, "pwr_ifb_en",    0, BEE_ACCESS_W,  NULL,       cb_pwr_ifb_en_write},
    {0x0102, "pwr_io_en",     0, BEE_ACCESS_W,  NULL,       cb_pwr_io_en_write},
    {0x0103, "pwr_pzp_en",    0, BEE_ACCESS_W,  NULL,       cb_pwr_pzp_en_write},
    {0x0104, "pwr_htr_en",    0, BEE_ACCESS_W,  NULL,       cb_pwr_htr_en_write},
    {0x0105, "pwr_sln_tec_en",0, BEE_ACCESS_W,  NULL,       cb_pwr_sln_tec_en_write},
    {0x0106, "pwr_lda_en",    0, BEE_ACCESS_W,  NULL,       cb_pwr_lda_en_write},
    {0x0107, "pwr_pda_en",    0, BEE_ACCESS_W,  NULL,       cb_pwr_pda_en_write},
    {0x0108, "pwr_usb_0_en",  0, BEE_ACCESS_W,  NULL,       cb_pwr_usb_0_en_write},
    {0x0109, "pwr_usb_1_en",  0, BEE_ACCESS_W,  NULL,       cb_pwr_usb_1_en_write},
    {0x0120, "i2c_s_1_en",    0, BEE_ACCESS_W,  NULL,       i2c_s_1_en_write},
    {0x0121, "i2c_s_2_en",    0, BEE_ACCESS_W,  NULL,       i2c_s_2_en_write},
    {0x0122, "i2c_pwm_en",    0, BEE_ACCESS_W,  NULL,       i2c_pwm_en_write},
    {0x0123, "i2c_hd4_en",    0, BEE_ACCESS_W,  NULL,       i2c_hd4_en_write},
    {0x0124, "i2c_ld_1_en",   0, BEE_ACCESS_W,  NULL,       i2c_ld_1_en_write},
    {0x0125, "i2c_ld_2_en",   0, BEE_ACCESS_W,  NULL,       i2c_ld_2_en_write},
    {0x0127, "tec_0_en",      0, BEE_ACCESS_W,  NULL,       tec_0_en_write},
    {0x0128, "tec_1_en",      0, BEE_ACCESS_W,  NULL,       tec_1_en_write},
    {0x0129, "tec_2_en",      0, BEE_ACCESS_W,  NULL,       tec_2_en_write},
    {0x012A, "tec_3_en",      0, BEE_ACCESS_W,  NULL,       tec_3_en_write},
    {0x012B, "usb_led_1_set", 0, BEE_ACCESS_RW, NULL,       usb_led_1_write},
    {0x012C, "usb_led_2_set", 0, BEE_ACCESS_RW, NULL,       usb_led_2_write},
    {0x0130, "htr_0_set",     0, BEE_ACCESS_RW, NULL,       htr_0_write},
    {0x0131, "htr_1_set",     0, BEE_ACCESS_RW, NULL,       htr_1_write},
    {0x0132, "htr_2_set",     0, BEE_ACCESS_RW, NULL,       htr_2_write},
    {0x0133, "htr_3_set",     0, BEE_ACCESS_RW, NULL,       htr_3_write},
    {0x0134, "htr_4_set",     0, BEE_ACCESS_RW, NULL,       htr_4_write},
    {0x0135, "htr_5_set",     0, BEE_ACCESS_RW, NULL,       htr_5_write},
    {0x0136, "htr_6_set",     0, BEE_ACCESS_RW, NULL,       htr_6_write},
    {0x0137, "htr_7_set",     0, BEE_ACCESS_RW, NULL,       htr_7_write},
    {0x0140, "custom_cmd",    0, BEE_ACCESS_RW, NULL,       custom_cmd_write},
};
static const int bee_table1_count = sizeof(bee_table1) / sizeof(bee_table1[0]);

// ===================== TABLE 2 =====================
static bee_param_t bee_table2[] = {
    {0x0200, "pump_1_ctl",     0,   BEE_ACCESS_RW, NULL,      cb_pump_1_ctl_write},
    {0x0201, "pump_1_volt",    100, BEE_ACCESS_RW, NULL,      cb_pump_1_volt_write},
    {0x0202, "pump_1_freq",    100, BEE_ACCESS_RW, NULL,      cb_pump_1_freq_write},
    {0x0203, "pump_2_ctl",     0, BEE_ACCESS_RW, NULL,      cb_pump_2_ctl_write},
    {0x0204, "pump_2_volt",    0, BEE_ACCESS_RW, NULL,      cb_pump_2_volt_write},
    {0x0205, "pump_2_freq",    0, BEE_ACCESS_RW, NULL,      cb_pump_2_freq_write},
    {0x0210, "sln_0_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_0_ctl_write},
    {0x0211, "sln_1_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_1_ctl_write},
    {0x0212, "sln_2_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_2_ctl_write},
    {0x0213, "sln_3_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_3_ctl_write},
    {0x0214, "sln_4_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_4_ctl_write},
    {0x0215, "sln_5_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_5_ctl_write},
    {0x0216, "sln_6_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_6_ctl_write},
    {0x0217, "sln_7_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_7_ctl_write},
    {0x0218, "sln_8_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_8_ctl_write},
    {0x0219, "sln_9_ctl",      0, BEE_ACCESS_RW, NULL,      cb_sln_9_ctl_write},
    {0x021A, "sln_10_ctl",     0, BEE_ACCESS_RW, NULL,      cb_sln_10_ctl_write},
    {0x021B, "sln_11_ctl",     0, BEE_ACCESS_RW, NULL,      cb_sln_11_ctl_write},
    {0x021C, "sln_valve_1_ctl",0, BEE_ACCESS_RW, NULL,      cb_sln_valve_1_ctl_write},
    {0x021D, "sln_valve_2_ctl",0, BEE_ACCESS_RW, NULL,      cb_sln_valve_2_ctl_write},
};
static const int bee_table2_count = sizeof(bee_table2) / sizeof(bee_table2[0]);

// ===================== TABLE 3 =====================
// Thermal Profile Configurations (0x0300–0x03FF)
static bee_param_t bee_table3[] = {
    {0x0300, "temp_master_en",     1,           BEE_ACCESS_RW, NULL, cb_temp_master_en_write},
    {0x0301, "temp_p_1_en",        0,           BEE_ACCESS_RW, NULL, cb_temp_p_1_en_write},
    {0x0302, "temp_p_2_en",        0,           BEE_ACCESS_RW, NULL, cb_temp_p_2_en_write},
    {0x0303, "temp_p_3_en",        0,           BEE_ACCESS_RW, NULL, cb_temp_p_3_en_write},
    {0x0304, "temp_p_4_en",        0,           BEE_ACCESS_RW, NULL, cb_temp_p_4_en_write},
    {0x0305, "temp_p_5_en",        0,           BEE_ACCESS_RW, NULL, cb_temp_p_5_en_write},
    {0x0306, "temp_p_6_en",        0,           BEE_ACCESS_RW, NULL, cb_temp_p_6_en_write},

    // ===== Profile 1 =====
    {0x0310, "temp_p_1_setpoint",  200,         BEE_ACCESS_RW, NULL, cb_temp_p_1_setpoint_write},
    {0x0311, "temp_p_1_ntcp",      0,           BEE_ACCESS_RW, NULL, cb_temp_p_1_ntcp_write},
    {0x0312, "temp_p_1_ntcs",      1,           BEE_ACCESS_RW, NULL, cb_temp_p_1_ntcs_write},
    {0x0313, "temp_p_1_htr",       0,           BEE_ACCESS_RW, NULL, cb_temp_p_1_htr_write},
    {0x0314, "temp_p_1_tec",       0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_1_tec_write},

    // ===== Profile 2 =====
    {0x0315, "temp_p_2_setpoint",  200,         BEE_ACCESS_RW, NULL, cb_temp_p_2_setpoint_write},
    {0x0316, "temp_p_2_ntcp",      4,           BEE_ACCESS_RW, NULL, cb_temp_p_2_ntcp_write},
    {0x0317, "temp_p_2_ntcs",      5,           BEE_ACCESS_RW, NULL, cb_temp_p_2_ntcs_write},
    {0x0318, "temp_p_2_htr",       1,           BEE_ACCESS_RW, NULL, cb_temp_p_2_htr_write},
    {0x0319, "temp_p_2_tec",       0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_2_tec_write},

    // ===== Profile 3 =====
    {0x031A, "temp_p_3_setpoint",  250,         BEE_ACCESS_RW, NULL, cb_temp_p_3_setpoint_write},
    {0x031B, "temp_p_3_ntcp",      6,           BEE_ACCESS_RW, NULL, cb_temp_p_3_ntcp_write},
    {0x031C, "temp_p_3_ntcs",      7,           BEE_ACCESS_RW, NULL, cb_temp_p_3_ntcs_write},
    {0x031D, "temp_p_3_htr",       3,           BEE_ACCESS_RW, NULL, cb_temp_p_3_htr_write},
    {0x031E, "temp_p_3_tec",       0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_3_tec_write},

    // ===== Profile 4 =====
    {0x031F, "temp_p_4_setpoint",  0,           BEE_ACCESS_RW, NULL, cb_temp_p_4_setpoint_write},
    {0x0320, "temp_p_4_ntcp",      0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_4_ntcp_write},
    {0x0321, "temp_p_4_ntcs",      0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_4_ntcs_write},
    {0x0322, "temp_p_4_htr",       0,           BEE_ACCESS_RW, NULL, cb_temp_p_4_htr_write},
    {0x0323, "temp_p_4_tec",       0,           BEE_ACCESS_RW, NULL, cb_temp_p_4_tec_write},

    // ===== Profile 5 =====
    {0x0324, "temp_p_5_setpoint",  0,           BEE_ACCESS_RW, NULL, cb_temp_p_5_setpoint_write},
    {0x0325, "temp_p_5_ntcp",      0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_5_ntcp_write},
    {0x0326, "temp_p_5_ntcs",      0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_5_ntcs_write},
    {0x0327, "temp_p_5_htr",       0,           BEE_ACCESS_RW, NULL, cb_temp_p_5_htr_write},
    {0x0328, "temp_p_5_tec",       0,           BEE_ACCESS_RW, NULL, cb_temp_p_5_tec_write},

    // ===== Profile 6 =====
    {0x0329, "temp_p_6_setpoint",  0,           BEE_ACCESS_RW, NULL, cb_temp_p_6_setpoint_write},
    {0x032A, "temp_p_6_ntcp",      0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_6_ntcp_write},
    {0x032B, "temp_p_6_ntcs",      0xFFFFFFFF,  BEE_ACCESS_RW, NULL, cb_temp_p_6_ntcs_write},
    {0x032C, "temp_p_6_htr",       0,           BEE_ACCESS_RW, NULL, cb_temp_p_6_htr_write},
    {0x032D, "temp_p_6_tec",       0,           BEE_ACCESS_RW, NULL, cb_temp_p_6_tec_write},
};

static const int bee_table3_count = sizeof(bee_table3) / sizeof(bee_table3[0]);

// ===================== TABLE 5 =====================
static bee_param_t bee_table5[] = {
    {0x0500, "test_ls_current",  0,             BEE_ACCESS_RW, NULL, cb_test_ls_current_write},
    {0x0501, "test_fluidic_seq", 0,             BEE_ACCESS_RW, NULL, cb_test_fluidic_seq_write},
    {0x0502, "exp_fluidic_seq",  0,             BEE_ACCESS_RW, NULL, cb_exp_fluidic_seq_write},
    {0x0503, "exp_mon_start",    0,             BEE_ACCESS_RW, NULL, cb_exp_mon_delay_start},
    {0x0510, "exp_mon_delay",    0,             BEE_ACCESS_RW, NULL, cb_exp_mon_delay_write},
    {0x0511, "exp_mon_interval", 28800,         BEE_ACCESS_RW, NULL, cb_exp_mon_interval_write}, //sec -> 8h
    {0x0512, "dls_ls_intensity", 25,            BEE_ACCESS_RW, NULL, cb_dls_ls_intensity_write}, // 
    {0x0513, "cam_ls_intensity", 15,            BEE_ACCESS_RW, NULL, cb_cam_ls_intensity_write}, // 15%
    {0x0514, "exp_samp_rate",    100,           BEE_ACCESS_RW, NULL, cb_exp_samp_rate_write},
    {0x0515, "exp_pre_time",     1,             BEE_ACCESS_RW, NULL, cb_exp_pre_time_write},
    {0x0516, "exp_samp_time",    100,           BEE_ACCESS_RW, NULL, cb_exp_samp_time_write},
    {0x0517, "exp_post_time",    1,             BEE_ACCESS_RW, NULL, cb_exp_post_time_write},
    {0x0520, "custom_ctl",       0,             BEE_ACCESS_RW, NULL, cb_custom_ctl_write},
    {0x0521, "cis_cam_capture",  0,             BEE_ACCESS_RW, NULL, cb_cis_cam_capture_write},
    {0x0522, "usb_cam_capture",  0,             BEE_ACCESS_RW, NULL, cb_usb_cam_capture_write},
};

static const int bee_table5_count = sizeof(bee_table5) / sizeof(bee_table5[0]);

// ===================== TABLE 6 =====================
static bee_param_t bee_table6[] = {
    {0x0600, "sys_status",      0, BEE_ACCESS_R, NULL, NULL},
    {0x0601, "boot_cnt",        0, BEE_ACCESS_R, NULL, NULL},
    {0x0602, "temp_exp",        0, BEE_ACCESS_R, NULL, NULL},
    {0x0603, "temp_ntc_0",      0, BEE_ACCESS_R, NULL, NULL},
    {0x0604, "temp_ntc_1",      0, BEE_ACCESS_R, NULL, NULL},
    {0x0605, "temp_ntc_2",      0, BEE_ACCESS_R, NULL, NULL},
    {0x0606, "temp_ntc_3",      0, BEE_ACCESS_R, NULL, NULL},
    {0x0607, "temp_ntc_4",      0, BEE_ACCESS_R, NULL, NULL},
    {0x0608, "temp_ntc_5",      0, BEE_ACCESS_R, NULL, NULL},
    {0x0609, "temp_ntc_6",      0, BEE_ACCESS_R, NULL, NULL},
    {0x060A, "temp_ntc_7",      0, BEE_ACCESS_R, NULL, NULL},
    {0x060B, "temp_ntc_8",      0, BEE_ACCESS_R, NULL, NULL},
    {0x060C, "temp_ntc_9",      0, BEE_ACCESS_R, NULL, NULL},
    {0x060D, "temp_ntc_10",     0, BEE_ACCESS_R, NULL, NULL},
    {0x060E, "temp_ntc_11",     0, BEE_ACCESS_R, NULL, NULL},
    {0x0610, "sen1_data_0",     0, BEE_ACCESS_R, NULL, NULL},
    {0x0611, "sen1_data_1",     0, BEE_ACCESS_R, NULL, NULL},
    {0x0612, "sen2_data_0",     0, BEE_ACCESS_R, NULL, NULL},
    {0x0613, "sen2_data_1",     0, BEE_ACCESS_R, NULL, NULL},
    {0x0614, "current_12_tot",  0, BEE_ACCESS_R, NULL, NULL},
    {0x0615, "current_12_lda",  0, BEE_ACCESS_R, NULL, NULL},
    {0x0616, "current_12_pda",  0, BEE_ACCESS_R, NULL, NULL},
    {0x0617, "current_5_io",    0, BEE_ACCESS_R, NULL, NULL},
    {0x0618, "current_5_tec",   0, BEE_ACCESS_R, NULL, NULL},
    {0x0619, "current_5_cam",   0, BEE_ACCESS_R, NULL, NULL},
    {0x061A, "current_5_hd",    0, BEE_ACCESS_R, NULL, NULL},
};

static const int bee_table6_count = sizeof(bee_table6) / sizeof(bee_table6[0]);

// ===================== TABLE 7 =====================
static bee_param_t bee_table7[] = {
    {0x0700, "data_size_config", 512, BEE_ACCESS_RW, NULL, cb_data_size_cfg_write},
    {0x0704, "load_next_file_counter", 0, BEE_ACCESS_RW, NULL, NULL},
};
static const int bee_table7_count = sizeof(bee_table7)/sizeof(bee_table7[0]);

//---------------------------------------------------------------------------------------------------------

void bee_table_init(void)
{
    printf("=== BEE Parameter Tables ===\n");
    printf("Table1 count: %d\n", bee_table1_count);
    printf("Table2 count: %d\n", bee_table2_count);
    printf("Table3 count: %d\n", bee_table3_count);
    printf("Table5 count: %d\n", bee_table5_count);
    printf("Table6 count: %d\n", bee_table6_count);
    printf("Table7 count: %d\n", bee_table7_count);
    printf("=============================\n");
}

/*-----------------------------------------------
 *  SQLite Management
 *---------------------------------------------*/
static pthread_t sqlite_thread;
static int sqlite_thread_running = 0;

/* Helper: ensure database and table exist */
static void bee_sqlite_init(sqlite3 *db) {
    char *errmsg = NULL;
    sqlite3_exec(db, "PRAGMA journal_mode=WAL;", NULL, NULL, NULL);
    sqlite3_busy_timeout(db, 200);
    const char *sql =
        "CREATE TABLE IF NOT EXISTS bee_param_update ("
        "addr INTEGER PRIMARY KEY,"
        "value INTEGER);";
    if (sqlite3_exec(db, sql, NULL, NULL, &errmsg) != SQLITE_OK) {
        fprintf(stderr, "[BEE_SQL] Init error: %s\n", errmsg);
        sqlite3_free(errmsg);
    }
}

/* Helper: sync RAM → DB for one parameter */
static void bee_sqlite_write_param(sqlite3 *db, uint16_t addr, uint32_t val) {
    sqlite3_stmt *stmt;
    const char *sql = "REPLACE INTO bee_param_update (addr, value) VALUES (?, ?);";
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_int(stmt, 1, addr);
        sqlite3_bind_int(stmt, 2, val);
        sqlite3_step(stmt);
        sqlite3_finalize(stmt);
    }
}

/* Thread: periodically sync DB → RAM */
static void *bee_sqlite_update_task(void *arg) {
    sqlite3 *db = NULL;
    while (sqlite_thread_running) {
        if (sqlite3_open(DB_PATH, &db) != SQLITE_OK) {
            fprintf(stderr, "[BEE_SQL] Cannot open DB: %s\n", sqlite3_errmsg(db));
            sleep(UPDATE_PERIOD_SEC);
            continue;
        }

        bee_sqlite_init(db);

        const char *sql = "SELECT addr, value FROM bee_param_update;";
        sqlite3_stmt *stmt;
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
            while (sqlite3_step(stmt) == SQLITE_ROW) {
                uint16_t addr = (uint16_t)sqlite3_column_int(stmt, 0);
                uint32_t val  = (uint32_t)sqlite3_column_int(stmt, 1);

                if (addr == 0x0100)
                    continue;

                bee_param_t *param = bee_param_lookup(addr);
                if (param) {
                    if (param->value != val) {
                        param->value = val;
                        if (param->on_write)
                            param->on_write(addr, val);
                        printf("[BEE_SQL] Sync DB→RAM 0x%04X (%s)=0x%08X\n",
                               addr, param->name, val);
                    }
                }
            }
            sqlite3_finalize(stmt);
        }
        sqlite3_close(db);
        sleep(UPDATE_PERIOD_SEC);
    }
    return NULL;
}

/*-----------------------------------------------
 *  Public Functions
 *---------------------------------------------*/

bee_param_t *bee_param_lookup(uint16_t addr)
{
    // ---- Table 1 ----
    for (int i = 0; i < bee_table1_count; i++) {
        if (bee_table1[i].addr == addr)
            return &bee_table1[i];
    }

    // ---- Table 2 ----
    for (int i = 0; i < bee_table2_count; i++) {
        if (bee_table2[i].addr == addr)
            return &bee_table2[i];
    }

    // ---- Table 3 ----
    for (int i = 0; i < bee_table3_count; i++) {
        if (bee_table3[i].addr == addr)
            return &bee_table3[i];
    }

    // ---- Table 5 ----
    for (int i = 0; i < bee_table5_count; i++) {
        if (bee_table5[i].addr == addr)
            return &bee_table5[i];
    }

    // ---- Table 6 ----
    for (int i = 0; i < bee_table6_count; i++) {
        if (bee_table6[i].addr == addr)
            return &bee_table6[i];
    }

    // ---- Table 7 ----
    for (int i = 0; i < bee_table7_count; i++) {
        if (bee_table7[i].addr == addr)
            return &bee_table7[i];
    }

    return NULL;
}

/* Start background thread */
void bee_sqlite_task_start(void) {
    if (sqlite_thread_running)
        return;
    sqlite_thread_running = 1;
    pthread_create(&sqlite_thread, NULL, bee_sqlite_update_task, NULL);
    printf("[BEE_SQL] SQLite sync thread started\n");
}

/* Stop thread cleanly */
void bee_sqlite_task_stop(void) {
    if (!sqlite_thread_running)
        return;
    sqlite_thread_running = 0;
    pthread_join(sqlite_thread, NULL);
    printf("[BEE_SQL] SQLite sync thread stopped\n");
}

/* Called from WRITE handler to sync DB immediately */
void bee_sqlite_update_value(uint16_t addr, uint32_t val) {
    sqlite3 *db;
    if (sqlite3_open(DB_PATH, &db) != SQLITE_OK) {
        fprintf(stderr, "[BEE_SQL] open fail: %s\n", sqlite3_errmsg(db));
        return;
    }
    bee_sqlite_init(db);
    bee_sqlite_write_param(db, addr, val);
    sqlite3_close(db);
}


/*-----------------------------------------------
 *  UNIX Socket PUB/SUB Replacement (Dual sockets)
 *---------------------------------------------*/
#define UNIX_SOCK_TX_PATH "/tmp/bee_to_rpmsg.sock"   // TX: C -> Python
#define UNIX_SOCK_RX_PATH "/tmp/rpmsg_to_bee.sock"   // RX: Python -> C

static int unix_pub_sock = -1;
static int unix_sub_sock = -1;
static pthread_t unix_sub_thread;
static int unix_sub_running = 0;

/* Gửi tin nhắn PARAM (thay cho ZMQ publish) */
void bee_unix_pub_param(uint16_t addr, uint32_t val) {
    if (unix_pub_sock < 0) return;

    struct sockaddr_un addr_u = {0};
    addr_u.sun_family = AF_UNIX;
    strncpy(addr_u.sun_path, UNIX_SOCK_TX_PATH, sizeof(addr_u.sun_path) - 1);

    char msg[128];
    snprintf(msg, sizeof(msg), "PARAM 0x%04X 0x%08X", addr, val);
    sendto(unix_pub_sock, msg, strlen(msg), 0,
           (struct sockaddr*)&addr_u, sizeof(addr_u));
}   

void bee_unix_pub_event(const char *name, uint32_t val) {
    if (unix_pub_sock < 0 || !name) return;

    struct sockaddr_un addr_u = {0};
    addr_u.sun_family = AF_UNIX;
    strncpy(addr_u.sun_path, UNIX_SOCK_TX_PATH, sizeof(addr_u.sun_path) - 1);

    char msg[128];
    snprintf(msg, sizeof(msg), "EVENT %s %u", name, val);
    sendto(unix_pub_sock, msg, strlen(msg), 0, (struct sockaddr*)&addr_u, sizeof(addr_u));
}

/* Thread nhận CMD (thay cho ZMQ SUB) */
static void *bee_unix_sub_task(void *arg) {
    char buf[128];
    while (unix_sub_running) {
        int n = recv(unix_sub_sock, buf, sizeof(buf) - 1, 0);
        if (n <= 0) continue;
        buf[n] = '\0';

        char cmd[8], s_addr[32], s_val[32];
        if (sscanf(buf, "%7s %31s %31s", cmd, s_addr, s_val) == 3 &&
            strcasecmp(cmd, "CMD") == 0) {

            uint16_t addr = 0; uint32_t val = 0;
            sscanf(s_addr, "%hx", &addr);
            sscanf(s_val, "%x", &val);

            bee_param_t *p = bee_param_lookup(addr);
            if (p && (p->access & BEE_ACCESS_W)) {
                p->value = val;
                if (p->on_write) p->on_write(addr, val);
                bee_sqlite_update_value(addr, val);
                printf("[BEE_UNIX] CMD SET 0x%04X=0x%08X\n", addr, val);
                bee_unix_pub_param(addr, val);
            }
        }
    }
    return NULL;
}

/* Khởi tạo Unix socket */
void bee_unix_init(void) {
    unlink(UNIX_SOCK_RX_PATH);

    unix_pub_sock = socket(AF_UNIX, SOCK_DGRAM, 0);
    unix_sub_sock = socket(AF_UNIX, SOCK_DGRAM, 0);

    struct sockaddr_un addr = {0};
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, UNIX_SOCK_RX_PATH, sizeof(addr.sun_path) - 1);
    bind(unix_sub_sock, (struct sockaddr*)&addr, sizeof(addr));

    unix_sub_running = 1;
    pthread_create(&unix_sub_thread, NULL, bee_unix_sub_task, NULL);

    printf("[BEE_UNIX] TX→%s, RX←%s\n", UNIX_SOCK_TX_PATH, UNIX_SOCK_RX_PATH);
}

/* Dừng socket */
void bee_unix_term(void) {
    unix_sub_running = 0;
    pthread_join(unix_sub_thread, NULL);
    close(unix_pub_sock);
    close(unix_sub_sock);
    unlink(UNIX_SOCK_RX_PATH);
    printf("[BEE_UNIX] Terminated\n");
}

/* Gọi khi giá trị param thay đổi */
void bee_param_value_changed(uint16_t addr, uint32_t val) {
    bee_unix_pub_param(addr, val);
}

/*-----------------------------------------------
 *  Boot Counter Management
 *---------------------------------------------*/
void bee_sqlite_boot_update(void) {
    sqlite3 *db;
    uint32_t boot_cnt = 0;

    if (sqlite3_open(DB_PATH, &db) != SQLITE_OK) {
        fprintf(stderr, "[BEE_SQL] open fail: %s\n", sqlite3_errmsg(db));
        return;
    }

    bee_sqlite_init(db);

    sqlite3_stmt *stmt;
    if (sqlite3_prepare_v2(db,
            "SELECT value FROM bee_param_update WHERE addr=0x0601;",
            -1, &stmt, NULL) == SQLITE_OK) {
        if (sqlite3_step(stmt) == SQLITE_ROW)
            boot_cnt = (uint32_t)sqlite3_column_int(stmt, 0);
        sqlite3_finalize(stmt);
    }

    boot_cnt++;

    sqlite3_stmt *stmt2;
    if (sqlite3_prepare_v2(db,
            "REPLACE INTO bee_param_update (addr, value) VALUES (0x0601, ?);",
            -1, &stmt2, NULL) == SQLITE_OK) {
        sqlite3_bind_int(stmt2, 1, boot_cnt);
        sqlite3_step(stmt2);
        sqlite3_finalize(stmt2);
    }

    sqlite3_close(db);

    bee_param_t *p = bee_param_lookup(0x0601);
    if (p) {
        p->value = boot_cnt;
        printf("[BEE_SQL] Boot count = %u (synced to RAM)\n", boot_cnt);
    } else {
        printf("[BEE_SQL] Boot count updated in DB but addr 0x0601 not found in RAM!\n");
    }
}

