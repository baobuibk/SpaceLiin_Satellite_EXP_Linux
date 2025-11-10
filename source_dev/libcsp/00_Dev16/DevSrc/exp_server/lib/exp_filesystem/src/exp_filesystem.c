#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <stdint.h>
#include <sys/types.h>
#include "exp_table.h"

/* forward declarations from your project */
extern bee_param_t *bee_param_lookup(uint16_t addr);
void bee_sqlite_update_value(uint16_t addr, uint32_t val);

/* constants */
#define PYTHON_EXEC_PATH "/data/.a55_src/scripts/python_exec.py"
#define MAX_OUT_READ (64 * 1024)

static int exec_table7(uint16_t addr, const char *arg1, const char *arg2,
                       uint8_t *out, size_t *outlen) {
    // arg1/arg2 are optional arguments passed to python_exec.py after addr
    // Build argv: {"python3", PYTHON_EXEC_PATH, "<addr_str>", arg1?, arg2?, NULL}
    char addr_str[8]; // "0701" etc
    snprintf(addr_str, sizeof(addr_str), "%04X", addr);

    // prepare argv list (max 6 entries)
    const char *argv[6];
    int argc = 0;
    argv[argc++] = "python3";
    argv[argc++] = PYTHON_EXEC_PATH;
    argv[argc++] = addr_str;
    if (arg1) argv[argc++] = arg1;
    if (arg2) argv[argc++] = arg2;
    argv[argc] = NULL;

    int pipefd[2];
    if (pipe(pipefd) != 0) return -1;

    pid_t pid = fork();
    if (pid < 0) {
        close(pipefd[0]); close(pipefd[1]);
        return -2;
    }

    if (pid == 0) {
        // child
        // redirect stdout -> pipe write
        dup2(pipefd[1], STDOUT_FILENO);
        // optionally redirect stderr to /dev/null or keep for debug
        // dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[0]); close(pipefd[1]);

        // exec python3 ... (no shell)
        execvp("python3", (char * const *)argv);
        // if exec fails
        _exit(127);
    }

    // parent: read child's stdout
    close(pipefd[1]);
    size_t total = 0;
    ssize_t n;
    while ((n = read(pipefd[0], out + total, MAX_OUT_READ - total)) > 0) {
        total += (size_t)n;
        if (total >= MAX_OUT_READ) break;
    }
    close(pipefd[0]);

    int status = 0;
    waitpid(pid, &status, 0);
    *outlen = total;

    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return -3;
}

/* fs_handle_cmd replacement */
int fs_handle_cmd(uint16_t addr, const uint8_t *in, size_t inlen,
                  uint8_t *out, size_t *outlen) {

    if (!out || !outlen) return -1;
    *outlen = 0;

    /* Get RAM chunk size from param 0x0700 */
    uint32_t chunk = 512; /* default */
    bee_param_t *p0700 = bee_param_lookup(0x0700);
    if (p0700) chunk = (uint32_t) p0700->value;

    char arg_buf1[512] = {0};
    char arg_buf2[512] = {0};

    int rc = -1;

    switch (addr) {
        case 0x0701:
            // python_exec.py 0701
            rc = exec_table7(addr, NULL, NULL, out, outlen);
            break;

        case 0x0702:
            // python_exec.py 0702 <chunk>
            snprintf(arg_buf1, sizeof(arg_buf1), "%u", chunk);
            rc = exec_table7(addr, arg_buf1, NULL, out, outlen);
            break;

        case 0x0703:
            // payload is relative path string (not binary)
            if (in && inlen > 0 && inlen < sizeof(arg_buf1)) {
                memcpy(arg_buf1, in, inlen);
                arg_buf1[inlen] = '\0';
                // pass chunk as second arg
                snprintf(arg_buf2, sizeof(arg_buf2), "%u", chunk);
                rc = exec_table7(addr, arg_buf1, arg_buf2, out, outlen);
            } else {
                // invalid payload
                rc = -4;
            }
            break;

        case 0x0704: {
            // Behavior: if payload contains 4B BE file_id, use it and write to DB before call.
            // Else, try to read current value from param lookup (bee_param_lookup) if exists.
            uint32_t file_id = 0;
            if (in && inlen >= 4) {
                file_id = ((uint32_t)in[0] << 24) | ((uint32_t)in[1] << 16) |
                          ((uint32_t)in[2] << 8) | (uint32_t)in[3];
            } else {
                bee_param_t *p0704 = bee_param_lookup(0x0704);
                if (p0704) file_id = (uint32_t)p0704->value;
            }

            // persist file_id into DB so other components can see it
            bee_sqlite_update_value(0x0704, file_id);

            // call python: python_exec.py 0704 <file_id> <chunk>
            snprintf(arg_buf1, sizeof(arg_buf1), "%u", file_id);
            snprintf(arg_buf2, sizeof(arg_buf2), "%u", chunk);
            rc = exec_table7(addr, arg_buf1, arg_buf2, out, outlen);

            // if python returned success (rc == 0), increment file_id and save back to DB
            if (rc == 0) {
                uint32_t next_id = file_id + 1;
                bee_sqlite_update_value(0x0704, next_id);
            }
            break;
        }

        case 0x0705:
            // payload is 4B part_no (big-endian)
            if (in && inlen >= 4) {
                uint32_t part_no = ((uint32_t)in[0] << 24) | ((uint32_t)in[1] << 16) |
                                   ((uint32_t)in[2] << 8) | (uint32_t)in[3];
                snprintf(arg_buf1, sizeof(arg_buf1), "%u", part_no);
                rc = exec_table7(addr, arg_buf1, NULL, out, outlen);
            } else {
                rc = -5;
            }
            break;

        case 0x0706:
            // payload is relative path string for delete
            if (in && inlen > 0 && inlen < sizeof(arg_buf1)) {
                memcpy(arg_buf1, in, inlen);
                arg_buf1[inlen] = '\0';
                rc = exec_table7(addr, arg_buf1, NULL, out, outlen);
            } else {
                rc = -6;
            }
            break;

        case 0x0707:
            // payload: 3 byte YY MM DD
            if (in && inlen >= 3) {
                unsigned yy = in[0];
                unsigned mm = in[1];
                unsigned dd = in[2];
                // Gói thành "YYMMDD" để python nhận 1 tham số
                snprintf(arg_buf1, sizeof(arg_buf1), "%02u%02u%02u", yy, mm, dd);
                rc = exec_table7(addr, arg_buf1, NULL, out, outlen);
            } else {
                rc = -7;
            }            
            break;

        case 0x0710:
            // python_exec.py 0710
            rc = exec_table7(addr, NULL, NULL, out, outlen);
            break;

        case 0x0711:
        case 0x0712:
            // payload là 4 byte BE part_no
            if (in && inlen >= 4) {
                uint32_t part_no = ((uint32_t)in[0] << 24) |
                                   ((uint32_t)in[1] << 16) |
                                   ((uint32_t)in[2] << 8)  |
                                    (uint32_t)in[3];
                snprintf(arg_buf1, sizeof(arg_buf1), "%u", part_no);
                rc = exec_table7(addr, arg_buf1, NULL, out, outlen);
            } else {
                rc = -8;
            }
            break;

        case 0x0777: {
            uint32_t old_val = 0;
            bee_param_t *p0704 = bee_param_lookup(0x0704);
            if (p0704)
                old_val = (uint32_t)p0704->value;

            printf("[FS_CMD] Resetting 0x0704 counter (old=%u)\n", old_val);

            bee_sqlite_update_value(0x0704, 0);

            *outlen = 0;
            }
            break;

        default:
            rc = -99;
            break;


    }

    return rc;
}
