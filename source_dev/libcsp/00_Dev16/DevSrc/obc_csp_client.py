#!/usr/bin/python3
import sys
import time
import struct
from datetime import datetime
import libcsp_py3 as libcsp

# ==============================
#  CONFIGURATION
# ==============================
SIMULATION = False  # Set to False for real hardware

OBC_ADDRESS = 10
EXP_ADDRESS = 11
if SIMULATION:
    CAN_INTERFACE = "vcan0"  # Virtual CAN for simulation
else:   
    CAN_INTERFACE = "can1" 
TIMEOUT = 1000          

# ==============================
#  MENU COMMANDS
# ==============================
PORTS = {
    0: "CSP_CMD",
    1: "CSP_PING",
    2: "CSP_PS",
    3: "CSP_MEM_FREE",
    4: "CSP_REBOOT",
    5: "CSP_BUF_FREE",
    6: "CSP_UPTIME",
    7: "BEE_PARAMS"
}

# BEE Control Registers
BEE_REGISTERS = {
    0x0000: {"name": "System Status", "type": "read"},
    0x0011: {"name": "TEC Power", "type": "control"},
    0x0012: {"name": "Heater Power", "type": "control"},
    0x0013: {"name": "Solenoid Valve", "type": "control"},
    0x0014: {"name": "Piezo Pump", "type": "control"},
    0x0015: {"name": "Photo Power", "type": "control"},
    0x0016: {"name": "Laser Power", "type": "control"},
    0x0080: {"name": "List Folders", "type": "file"},
    0x0081: {"name": "List Files", "type": "file"},
    0x0082: {"name": "Cat File", "type": "file"},
    0x0090: {"name": "PWM Heater Control", "type": "pwm"}
}

def send_request(port, payload=None):
    """Send CSP request and receive response"""
    if payload is None:
        payload = b"REQ"

    print(f"\n[INFO] Sending request to node {EXP_ADDRESS} port {port} ({PORTS.get(port, 'UNKNOWN')})")
    
    if port == 7 and len(payload) >= 3:
        print(f"[PAYLOAD] Hex: {payload.hex().upper()}")
        reg_addr = (payload[0] << 8) | payload[1]
        print(f"[PAYLOAD] Register: 0x{reg_addr:04X}")

    outbuf = bytearray(payload)
    inbuf = bytearray(256)

    try:
        result = libcsp.transaction(
            libcsp.CSP_PRIO_NORM,
            EXP_ADDRESS,
            port,
            TIMEOUT,
            outbuf,
            inbuf
        )
        print(f"[DEBUG] Transaction result: {result}")
        
        if result:
            return inbuf
        else:
            print("[ERROR] Transaction failed or timeout.\n")
            return None
    except Exception as e:
        print(f"[EXCEPTION] {e}\n")
        return None


def create_bee_payload(register_addr, data_bytes=b''):
    """
    Create BEE_PARAMS payload
    Format: [uint16_t addr_reg (big-endian)][data bytes...]
    """
    payload = bytearray()
    payload.append((register_addr >> 8) & 0xFF)  # High byte
    payload.append(register_addr & 0xFF)          # Low byte
    payload.extend(data_bytes)
    return bytes(payload)


def parse_folder_list(data):
    """
    Parse folder list response
    Format: [CMD=0x08][SUB=0x00][count][yy mm dd]...[padding=0xFF]
    Total length = 243 bytes
    """
    if len(data) < 3:
        print("[ERROR] Invalid response length.")
        return []
    
    cmd = data[0]
    subcmd = data[1]
    count = data[2]
    offset = 3
    folders = []

    print(f"[DEBUG] Header: CMD=0x{cmd:02X}, SUB=0x{subcmd:02X}, COUNT={count}")

    for i in range(count):
        if offset + 3 > len(data):
            print(f"[WARN] Unexpected end of data at folder {i}")
            break
        yy = data[offset]
        mm = data[offset + 1]
        dd = data[offset + 2]
        folders.append((yy, mm, dd))
        offset += 3

    pad_bytes = data[offset:]
    if any(b != 0xFF for b in pad_bytes):
        print(f"[WARN] Non-0xFF found in padding ({len(pad_bytes)} bytes)")

    return folders


def parse_file_list(data):
    """
    Parse LIST_FILES response
    Format: [0x08][0x01][High][Low]
    """
    if len(data) < 4:
        print("[ERROR] Invalid response length.")
        return None, None

    cmd_hi, cmd_lo, high, low = data[:4]
    if (cmd_hi, cmd_lo) != (0x27, 0x11):
        print(f"[ERROR] Unexpected header: 0x{cmd_hi:02X} 0x{cmd_lo:02X}")
        return None, None

    file_count = (high << 8) | low
    highest_id = file_count - 1 if file_count > 0 else 0

    print(f"[DEBUG] CMD=0x{cmd_hi:02X}{cmd_lo:02X}, Files={file_count}, Highest ID={highest_id}")
    return file_count, highest_id


def pwm_heater_menu():
    """PWM Heater control menu with frequency and duty cycle"""
    print("\n" + "="*50)
    print("  PWM Heater Control (0x0090)")
    print("="*50)
    
    # Get frequency
    print("\n[FREQUENCY]")
    print("Common values:")
    print("  1000 Hz  - Standard PWM")
    print("  2000 Hz  - Fast PWM")
    print("  500 Hz   - Slow PWM")
    
    freq_input = input("\nEnter frequency (Hz): ").strip()
    try:
        frequency = int(freq_input)
        if frequency <= 0 or frequency > 100000:
            print("[ERROR] Frequency must be between 1 and 100000 Hz")
            return
    except ValueError:
        print("[ERROR] Invalid frequency value")
        return
    
    # Get duty cycle
    print("\n[DUTY CYCLE]")
    print("Percentage (0-100):")
    print("  0%   - Always OFF")
    print("  25%  - Low power")
    print("  50%  - Medium power")
    print("  75%  - High power")
    print("  100% - Always ON")
    
    duty_input = input("\nEnter duty cycle (%): ").strip()
    try:
        duty_percent = int(duty_input)
        if duty_percent < 0 or duty_percent > 100:
            print("[ERROR] Duty cycle must be between 0 and 100")
            return
    except ValueError:
        print("[ERROR] Invalid duty cycle value")
        return
    
    # Get enable/disable
    print("\n[CONTROL]")
    action = input("Turn PWM ON (1) or OFF (0)? ").strip()
    
    if action not in ['0', '1']:
        print("[ERROR] Invalid input. Use 0 or 1.")
        return
    
    enable = int(action)
    
    # Build payload: [freq 4bytes big-endian][duty% 1byte][enable 1byte]
    payload_data = bytearray()
    payload_data.append((frequency >> 24) & 0xFF)  # Freq byte 3 (MSB)
    payload_data.append((frequency >> 16) & 0xFF)  # Freq byte 2
    payload_data.append((frequency >> 8) & 0xFF)   # Freq byte 1
    payload_data.append(frequency & 0xFF)          # Freq byte 0 (LSB)
    payload_data.append(duty_percent)              # Duty cycle %
    payload_data.append(enable)                    # Enable flag
    
    payload = create_bee_payload(0x0090, bytes(payload_data))
    
    print("\n" + "="*50)
    print("  PWM CONFIGURATION")
    print("="*50)
    print(f"Frequency: {frequency} Hz")
    print(f"Duty Cycle: {duty_percent}%")
    print(f"Action: {'ENABLE' if enable else 'DISABLE'}")
    print(f"Payload (hex): {payload.hex().upper()}")
    print("="*50)
    
    confirm = input("\nSend command? (y/n): ").strip().lower()
    if confirm != 'y':
        print("[CANCELLED] Command not sent.")
        return
    
    print(f"\n[ACTION] Configuring PWM Heater...")
    inbuf = send_request(7, payload)
    
    if inbuf:
        reply_str = inbuf.decode(errors="ignore").strip("\x00")
        print(f"\n[REPLY] {reply_str}\n")
        
        if reply_str.startswith("OK"):
            print("[SUCCESS] PWM Heater configured successfully!")
        else:
            print("[WARNING] Command may have failed. Check server logs.")
    else:
        print("[ERROR] No response from server.")

def list_folders_menu():
    """List all date folders"""
    print("\n" + "="*50)
    print("  List Date Folders")
    print("="*50)
    
    payload = create_bee_payload(0x2710)
    inbuf = send_request(7, payload)
    
    if inbuf:
        folders = parse_folder_list(inbuf)
        
        if folders:
            print(f"\n[FOLDERS] Found {len(folders)} folders:\n")
            for idx, (yy, mm, dd) in enumerate(folders, 1):
                date_str = f"{dd:02d}/{mm:02d}/20{yy:02d}"
                print(f"  {idx:2d}. {date_str}")
            return folders
        else:
            print("[INFO] No folders found.")
            return []
    else:
        print("[ERROR] Failed to retrieve folder list.")
        return []

def list_files_menu():
    """List files in a specific folder - returns file count and highest ID"""
    print("\n" + "="*50)
    print("  List Files in Folder (LowResolution only)")
    print("="*50)
    
    # First, get folder list
    folders = list_folders_menu()
    if not folders:
        return
    
    # Select folder
    try:
        choice = int(input("\nSelect folder number: ").strip())
        if choice < 1 or choice > len(folders):
            print("[ERROR] Invalid folder number.")
            return
        
        yy, mm, dd = folders[choice - 1]
        print(f"\n[SELECTED] {dd:02d}/{mm:02d}/20{yy:02d}")
        
    except ValueError:
        print("[ERROR] Invalid input.")
        return

    # Build payload: [0x08][0x01][DD][MM][YY]
    payload = bytes([0x27, 0x11, dd, mm, yy])
    print(f"[DEBUG] Payload: {[f'0x{x:02X}' for x in payload]}")

    print("\n[INFO] Requesting file list...")
    inbuf = send_request(7, payload)

    if inbuf:
        file_count, highest_id = parse_file_list(inbuf)
        
        if file_count is not None:
            print("\n" + "="*50)
            print("  FILE LIST SUMMARY")
            print("="*50)
            print(f"Total Files: {file_count}")
            print(f"Highest ID: {highest_id} (newest file)")
            print(f"ID Range: 0000 - {highest_id:04d}")
            print("="*50)
            
            return (yy, mm, dd), file_count, highest_id
        else:
            print("[ERROR] Failed to parse file list.")
    else:
        print("[ERROR] Failed to retrieve file list.")


def cat_file_menu():
    """
    Select and load a file (0x0802 + 0x0803)
    Supports both High and Low resolution.
    """
    print("\n" + "="*50)
    print("  Cat File - Display File Info (New Protocol)")
    print("="*50)
    print("[NOTE] The file content will be written to I2C (exprom-file) on SERVER.\n")

    # Step 1: Select folder and file
    result = list_files_menu()
    if not result:
        return

    (yy, mm, dd), file_count, highest_id = result

    if file_count == 0:
        print("[INFO] No files found in this folder.")
        return

    # Choose resolution
    print("\nResolution:")
    print("  0: High Resolution")
    print("  1: Low Resolution")
    res = input("Select resolution (0/1): ").strip()
    if res not in ['0', '1']:
        print("[ERROR] Invalid resolution.")
        return
    type_flag = int(res)

    # Input file ID
    print(f"\n[INFO] Enter file ID (0 - {highest_id})")
    try:
        file_id_int = int(input("File ID: ").strip())
        if file_id_int < 0 or file_id_int > highest_id:
            print("[ERROR] File ID out of range.")
            return
    except ValueError:
        print("[ERROR] Invalid ID format.")
        return

    id_high = (file_id_int >> 8) & 0xFF
    id_low = file_id_int & 0xFF

    # Build request for 0x0802
    payload = bytes([0x27, 0x12, dd, mm, yy, type_flag, id_high, id_low])
    print(f"[DEBUG] Send Select File Payload: {[hex(b) for b in payload]}")

    print("\n[INFO] Requesting file info from server...")
    inbuf = send_request(7, payload)
    if not inbuf:
        print("[ERROR] No response received.")
        return

    if len(inbuf) < 30 or inbuf[0:2] != b'\x27\x12':
        print(f"[ERROR] Invalid 0x2712 response: {inbuf}")
        return

    # Parse select_file_to_load response
    file_size = (inbuf[2]<<24)|(inbuf[3]<<16)|(inbuf[4]<<8)|inbuf[5]
    num_parts = (inbuf[6]<<24)|(inbuf[7]<<16)|(inbuf[8]<<8)|inbuf[9]
    filename = inbuf[10:30].decode('ascii', errors='ignore').rstrip('\x00')

    print("\n" + "="*50)
    print("  FILE INFORMATION")
    print("="*50)
    print(f"Date: {dd:02d}/{mm:02d}/20{yy:02d}")
    print(f"File ID: {file_id_int:04d}")
    print(f"Filename: {filename}")
    print(f"File Size: {file_size} bytes ({file_size/1024:.2f} KB)")
    print(f"Number of Parts: {num_parts}")
    print(f"Resolution: {'High' if type_flag==0 else 'Low'}")
    print("="*50)

    # Step 2: Request 0x0803 (part=0)
    print("\n[INFO] Loading file part 0 (cat to I2C)...")
    part_no = 0
    payload2 = bytes([
        0x27, 0x13, dd, mm, yy, type_flag,
        id_high, id_low,
        (part_no >> 24) & 0xFF,
        (part_no >> 16) & 0xFF,
        (part_no >> 8) & 0xFF,
        part_no & 0xFF
    ])

    print(f"[DEBUG] Send Load Part Payload: {[hex(b) for b in payload2]}")
    inbuf2 = send_request(7, payload2)

    if not inbuf2:
        print("[ERROR] No response for 0x2713.")
        return

    if len(inbuf2) < 16 or inbuf2[0:2] != b'\x27\x13':
        print(f"[ERROR] Invalid 0x2713 response: {inbuf2}")
        return

    # Parse response
    ret_id = (inbuf2[2] << 8) | inbuf2[3]
    ret_part = (inbuf2[4] << 24) | (inbuf2[5] << 16) | (inbuf2[6] << 8) | inbuf2[7]
    size_part = (inbuf2[8] << 24) | (inbuf2[9] << 16) | (inbuf2[10] << 8) | inbuf2[11]
    crc_part = (inbuf2[12] << 24) | (inbuf2[13] << 16) | (inbuf2[14] << 8) | inbuf2[15]

    print("\n" + "="*50)
    print("  FILE PART STATUS")
    print("="*50)
    print(f"File ID: {ret_id:04d}")
    print(f"Part No: {ret_part}")
    print(f"Part Size: {size_part} bytes")
    print(f"CRC32: 0x{crc_part:08X}")
    print(f"Resolution: {'High' if type_flag==0 else 'Low'}")
    print("[INFO] File content successfully written to I2C (server side).")
    print("="*50)

def reboot_remote_node(node_id):
    """Send CSP reboot command to remote node"""
    CSP_REBOOT_MAGIC = 0x80078007  # from libcsp/include/csp/csp_services.h
    payload = struct.pack(">I", CSP_REBOOT_MAGIC)  # 4 bytes big-endian

    print(f"\n[REBOOT] Sending reboot request to node {node_id}...")
    print(f"[REBOOT] Magic word: 0x{CSP_REBOOT_MAGIC:08X}")

    outbuf = bytearray(payload)
    inbuf = bytearray(8)

    result = libcsp.transaction(
        libcsp.CSP_PRIO_HIGH,
        node_id,
        4,               # port CSP_REBOOT
        1000,            # timeout ms
        outbuf,
        inbuf
    )

    if result:
        print("[SUCCESS] Reboot command sent successfully.")
    else:
        print("[ERROR] Failed to send reboot command or timeout.")

def file_management_menu():
    """File management submenu"""
    while True:
        print("\n" + "="*50)
        print("  File Management Menu")
        print("="*50)
        print("\n[Operations]")
        print("  1: List Date Folders")
        print("  2: List Files in Folder (Count + Highest ID)")
        print("  3: Cat File Content (by File ID)")
        print("  B: Back to main menu")
        
        choice = input("\nSelect option: ").strip().upper()
        
        if choice == 'B':
            return
        elif choice == '1':
            list_folders_menu()
        elif choice == '2':
            list_files_menu()
        elif choice == '3':
            cat_file_menu()
        else:
            print("[ERROR] Invalid choice.")


def bee_params_menu():
    """Interactive menu for BEE_PARAMS control"""
    
    while True:
        print("\n" + "="*50)
        print("  BEE_PARAMS Control Menu (Port 7)")
        print("="*50)
        
        print("\n[Read Operations]")
        print("  0: Get System Status (0x0000)")
        
        print("\n[Power Control]")
        print("  1: TEC Power Control (0x0011)")
        print("  2: Heater Power Control (0x0012)")
        print("  3: Solenoid Valve Control (0x0013)")
        print("  4: Piezoelectric Pump Control (0x0014)")
        print("  5: Photo Power Control (0x0015)")
        print("  6: Laser Power Control (0x0016)")

        print("\n[PWM Control]")
        print("  9: PWM Heater Control (0x0090) - Freq + Duty + On/Off")
        
        print("\n[File Management]")
        print("  F: File Management (0x0080-0x0082)")
        
        print("\n[Quick Actions]")
        print("  A: Turn ALL devices ON")
        print("  D: Turn ALL devices OFF")
        
        print("\n[Other]")
        print("  C: Custom payload (manual hex input)")
        print("  B: Back to main menu")
        
        choice = input("\nSelect option: ").strip().upper()
        
        if choice == 'B':
            return
        
        elif choice == '0':
            print("\n--- Reading System Status (uptime + epoch) ---")
            payload = create_bee_payload(0x0000, b'\x00')
            inbuf = send_request(7, payload)
            
            if not inbuf:
                print("[ERROR] No response received.\n")
                continue

            data = bytes(inbuf[:9])  
            if len(data) < 9:
                print(f"[ERROR] Invalid data length: {len(data)} bytes (expected 9)\n")
                continue

            flag = data[0]
            uptime = int.from_bytes(data[1:5], "little")
            epoch = int.from_bytes(data[5:9], "little")

            print(f"\n[STATUS] Flag: {flag}")
            print(f"[STATUS] Uptime : {uptime} s ({uptime/3600:.2f} h)")
            print(f"[STATUS] Epoch  : {epoch}")
            print(f"[STATUS] Time   : {datetime.fromtimestamp(epoch).strftime('%Y-%m-%d %H:%M:%S')}\n")

            if flag != 0:
                print("[WARNING] System reported non-zero status flag!\n")
        
        elif choice in ['1', '2', '3', '4', '5', '6']:
            reg_map = {
                '1': (0x0011, "TEC"),
                '2': (0x0012, "Heater"),
                '3': (0x0013, "Solenoid Valve"),
                '4': (0x0014, "Piezo Pump"),
                '5': (0x0015, "Photo"),
                '6': (0x0016, "Laser")
            }
            
            reg_addr, device_name = reg_map[choice]
            
            print(f"\n--- {device_name} Control ---")
            action = input("Turn ON (1) or OFF (0)? ").strip()
            
            if action in ['0', '1']:
                data = int(action)
                payload = create_bee_payload(reg_addr, bytes([data]))
                print(f"\n[ACTION] {'Turning ON' if data else 'Turning OFF'} {device_name}...")
                inbuf = send_request(7, payload)
                if inbuf:
                    reply_str = inbuf.decode(errors="ignore").strip("\x00")
                    print(f"[REPLY] {reply_str}\n")
            else:
                print("[ERROR] Invalid input. Use 0 or 1.")
        elif choice == '9':
            pwm_heater_menu()

        elif choice == 'F':
            file_management_menu()
        
        elif choice == 'A':
            print("\n--- Turning ALL Devices ON ---")
            for reg_addr in [0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016]:
                device_name = BEE_REGISTERS[reg_addr]["name"]
                payload = create_bee_payload(reg_addr, bytes([1]))
                print(f"\n[{device_name}]")
                inbuf = send_request(7, payload)
                if inbuf:
                    reply_str = inbuf.decode(errors="ignore").strip("\x00")
                    print(f"[REPLY] {reply_str}")
                time.sleep(0.2)
        
        elif choice == 'D':
            print("\n--- Turning ALL Devices OFF ---")
            for reg_addr in [0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016]:
                device_name = BEE_REGISTERS[reg_addr]["name"]
                payload = create_bee_payload(reg_addr, bytes([0]))
                print(f"\n[{device_name}]")
                inbuf = send_request(7, payload)
                if inbuf:
                    reply_str = inbuf.decode(errors="ignore").strip("\x00")
                    print(f"[REPLY] {reply_str}")
                time.sleep(0.2)
        
        elif choice == 'C':
            print("\n--- Custom Payload ---")
            print("Format: AABBCC (hex bytes)")
            print("  AA BB = Register address (big-endian)")
            print("  CC... = Data values")
            print("Example: 001101 = Register 0x0011, Data 0x01 (TEC ON)")
            
            hex_input = input("\nEnter hex payload: ").strip().replace(" ", "")
            
            try:
                if len(hex_input) < 4:
                    print("[ERROR] Payload too short. Need at least 4 hex digits (2 bytes).")
                    continue
                
                payload = bytes.fromhex(hex_input)
                print(f"\n[PAYLOAD] Sending {len(payload)} bytes: {payload.hex().upper()}")
                inbuf = send_request(7, payload)
                if inbuf:
                    print("\n[REPLY] Raw response:")
                    for i, b in enumerate(inbuf):
                        # Dừng khi gặp chuỗi toàn 0x00 ở cuối để tránh in rác
                        if i > 0 and all(x == 0 for x in inbuf[i:]):
                            break
                        ch = chr(b) if 32 <= b <= 126 else '.'
                        print(f"  Payload[{i}] = 0x{b:02X} ('{ch}')")
                    print()
                else:
                    print("[ERROR] No response received.\n")
                
            except ValueError:
                print("[ERROR] Invalid hex input.")

        elif choice == 'M':
            print("\n--- Manual Register Access ---")
            try:
                addr_str = input("Enter register address (e.g. 0301): ").strip()
                if not addr_str:
                    print("[ERROR] Empty input.")
                    continue

                addr = int(addr_str, 16)
                rw_mode = input("Read (R) or Write (W)? ").strip().upper()
                if rw_mode not in ["R", "W"]:
                    print("[ERROR] Invalid mode, must be R or W.")
                    continue

                if rw_mode == "R":
                    # BEE read command format: [addr_hi][addr_lo][0x01]
                    payload = create_bee_payload(addr, b"\x01")
                    print(f"[READ] Sending read request for 0x{addr:04X}")
                    inbuf = send_request(7, payload)
                    if inbuf:
                        val = int.from_bytes(inbuf[2:6], "big", signed=False)
                        print(f"[REPLY] Addr 0x{addr:04X} = 0x{val:08X} ({val})\n")
                    else:
                        print("[ERROR] No response received.\n")

                elif rw_mode == "W":
                    val_str = input("Enter 32-bit value (hex or dec): ").strip()
                    if val_str.lower().startswith("0x"):
                        val = int(val_str, 16)
                    else:
                        val = int(val_str)

                    data_bytes = val.to_bytes(4, "big")
                    payload = create_bee_payload(addr, data_bytes)
                    print(f"[WRITE] Sending 0x{val:08X} to 0x{addr:04X}")
                    inbuf = send_request(7, payload)
                    if inbuf:
                        reply_str = inbuf.decode(errors="ignore").strip("\x00")
                        print(f"[REPLY] {reply_str}\n")
                    else:
                        print("[ERROR] No response received.\n")

            except ValueError:
                print("[ERROR] Invalid number format.")
            except Exception as e:
                print(f"[EXCEPTION] {e}")

        
        else:
            print("[ERROR] Invalid choice.")


def main():
    print("="*50)
    print("  OBC Interactive Menu - CSP Commander")
    print("="*50)
    print(f"\nOBC Node: {OBC_ADDRESS}")
    print(f"Target Node (EXP): {EXP_ADDRESS}")
    print(f"Interface: {CAN_INTERFACE}\n")

    print("[INIT] Initializing CSP...")
    libcsp.init(OBC_ADDRESS, "OBC", "Ground", "1.0", 10, 300)
    libcsp.can_socketcan_init(CAN_INTERFACE)
    libcsp.rtable_load("0/0 CAN")
    libcsp.route_start_task()
    time.sleep(0.2)
    print("[INIT] CSP initialized successfully!\n")

    while True:
        print("\n" + "="*50)
        print("  Main Menu")
        print("="*50)
        print("\n[Standard CSP Ports]")
        print("  0: CSP_CMD - Command")
        print("  1: CSP_PING - Ping test")
        print("  2: CSP_PS - Process info")
        print("  3: CSP_MEM_FREE - Memory info")
        print("  4: CSP_REBOOT - Reboot command")
        print("  5: CSP_BUF_FREE - Buffer info")
        print("  6: CSP_UPTIME - System uptime")
        
        print("\n[BEE Project]")
        print("  7: BEE_PARAMS - Device Control & File Management")
        
        print("\n[System]")
        print("  Q: Quit")

        choice = input("\nSelect option: ").strip().upper()
        
        if choice == 'Q':
            print("\n[EXIT] Goodbye!")
            break

        if choice == '7':
            bee_params_menu()
            continue

        if choice == '4':
            confirm = input("\n⚠️  Confirm reboot target node? (y/n): ").strip().lower()
            if confirm == 'y':
                reboot_remote_node(EXP_ADDRESS)
            continue

        if not choice.isdigit() or int(choice) not in PORTS:
            print("[ERROR] Invalid choice, try again.")
            continue

        port = int(choice)

        print(f"\n[INFO] Sending request to port {port} ({PORTS[port]})")
        inbuf = send_request(port)
        if inbuf:
            reply_str = inbuf.decode(errors="ignore").strip("\x00")
            print(f"[REPLY] {reply_str}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[EXIT] Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
