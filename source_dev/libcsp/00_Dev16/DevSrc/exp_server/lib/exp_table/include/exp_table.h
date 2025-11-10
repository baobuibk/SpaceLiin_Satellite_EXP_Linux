/************************************************
 *  @file     : exp_table.h
 *  @date     : October 2025
 *  @author   : CAO HIEU
 *  @version  : 1.0.0
 *-----------------------------------------------
 *  Description :
 *    [-]
 ************************************************/

#ifndef exp_table_H
#define exp_table_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h> 
#include <stddef.h>   

typedef enum {
    BEE_ACCESS_R  = 1 << 0,
    BEE_ACCESS_W  = 1 << 1,
    BEE_ACCESS_RW = BEE_ACCESS_R | BEE_ACCESS_W,
} bee_access_t;

typedef struct {
    uint16_t addr;           
    const char *name;               
    uint32_t value;               
    bee_access_t access;             
    void (*on_read)(uint16_t addr); 
    void (*on_write)(uint16_t addr, uint32_t val);
} bee_param_t;

bee_param_t *bee_param_lookup(uint16_t addr);

void bee_sqlite_task_start(void);
void bee_sqlite_task_stop(void);
void bee_sqlite_update_value(uint16_t addr, uint32_t val);

void bee_set_db_path(const char *path);

void bee_unix_init(void);
void bee_unix_pub_param(uint16_t addr, uint32_t val);
void bee_unix_pub_event(const char *name, uint32_t val);
void bee_param_value_changed(uint16_t addr, uint32_t val);

void bee_table_init(void);
void bee_sqlite_boot_update(void);
#ifdef __cplusplus
}
#endif

#endif /* exp_table_H */