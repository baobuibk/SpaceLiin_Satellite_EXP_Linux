/************************************************
 *  @file     : exp_filesystem.h
 *  @date     : October 2025
 *  @author   : CAO HIEU
 *  @version  : 1.0.0
 *-----------------------------------------------
 *  Description :
 *    [-]
 ************************************************/

#ifndef exp_filesystem_H
#define exp_filesystem_H

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================*/
/*                        Includes                            */
/*============================================================*/
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>


bool fs_zmq_init(const char *endpoint);     // ví dụ: "tcp://127.0.0.1:5560"
void fs_zmq_term(void);

// Gọi RPC: addr=0x0700..0x0706, in/payload đầu vào, out/payload đầu ra
// Trả 0 nếu OK, <0 nếu lỗi. outlen được điền thực tế.
int fs_zmq_call(uint16_t addr, const uint8_t *in, size_t inlen,
                uint8_t *out, size_t *outlen, int timeout_ms);

int fs_handle_cmd(uint16_t addr, const uint8_t *in, size_t inlen,
                  uint8_t *out, size_t *outlen);
                
#ifdef __cplusplus
}
#endif

#endif /* exp_filesystem_H */