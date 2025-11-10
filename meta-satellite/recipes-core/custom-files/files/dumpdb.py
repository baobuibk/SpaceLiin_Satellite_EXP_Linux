#!/usr/bin/env python3
import sqlite3

DB_PATH = "/data/.a55_src/bee_params.db"

def dump_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Check if table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bee_param_update';")
        if not cur.fetchone():
            print("[x] Table 'bee_param_update' does not exist in database.")
            return

        print(f"{'Set':<5} | {'Address (hex)':<15} | {'Value (dec)':<12}")
        print("-" * 38)

        for addr, val in cur.execute("SELECT addr, value FROM bee_param_update ORDER BY addr;"):
            print(f"{'=':<5} | 0x{addr:04X}         | {val:<12}")

        conn.close()

    except sqlite3.Error as e:
        print(f"[x] SQLite error: {e}")
    except Exception as e:
        print(f"[x] Unexpected error: {e}")

if __name__ == "__main__":
    dump_db(DB_PATH)
