#!/usr/bin/env python3
"""
Linux PWM Control via sysfs
Properly handles enable/disable sequence to avoid "Invalid argument" errors
"""

import os
import sys
import argparse
import time

class PWMController:
    def __init__(self, chip=0, channel=2):
        self.chip = chip
        self.channel = channel
        self.base_path = f"/sys/class/pwm/pwmchip{chip}"
        self.pwm_path = f"{self.base_path}/pwm{channel}"
        
    def export(self):
        """Export PWM channel if not already exported"""
        if os.path.exists(self.pwm_path):
            print(f"PWM{self.channel} already exported")
            return True
            
        try:
            with open(f"{self.base_path}/export", 'w') as f:
                f.write(str(self.channel))
            time.sleep(0.1)  # Wait for sysfs to create files
            print(f"PWM{self.channel} exported successfully")
            return True
        except Exception as e:
            print(f"Error exporting PWM{self.channel}: {e}")
            return False
    
    def unexport(self):
        """Unexport PWM channel"""
        try:
            # Disable first
            self.disable()
            with open(f"{self.base_path}/unexport", 'w') as f:
                f.write(str(self.channel))
            print(f"PWM{self.channel} unexported")
            return True
        except Exception as e:
            print(f"Error unexporting PWM{self.channel}: {e}")
            return False
    
    def is_enabled(self):
        """Check if PWM is currently enabled"""
        try:
            with open(f"{self.pwm_path}/enable", 'r') as f:
                return int(f.read().strip()) == 1
        except:
            return False
    
    def disable(self):
        """Disable PWM output"""
        try:
            with open(f"{self.pwm_path}/enable", 'w') as f:
                f.write('0')
            return True
        except Exception as e:
            print(f"Error disabling PWM: {e}")
            return False
    
    def enable(self):
        """Enable PWM output"""
        try:
            with open(f"{self.pwm_path}/enable", 'w') as f:
                f.write('1')
            return True
        except Exception as e:
            print(f"Error enabling PWM: {e}")
            return False
    
    def set_period(self, period_ns):
        """Set PWM period in nanoseconds - MUST be disabled first"""
        try:
            with open(f"{self.pwm_path}/period", 'w') as f:
                f.write(str(period_ns))
            return True
        except Exception as e:
            print(f"Error setting period: {e}")
            return False
    
    def set_duty_cycle(self, duty_ns):
        """Set PWM duty cycle in nanoseconds"""
        try:
            with open(f"{self.pwm_path}/duty_cycle", 'w') as f:
                f.write(str(duty_ns))
            return True
        except Exception as e:
            print(f"Error setting duty cycle: {e}")
            return False
    
    def get_current_values(self):
        """Read current PWM configuration"""
        try:
            with open(f"{self.pwm_path}/period", 'r') as f:
                period = int(f.read().strip())
            with open(f"{self.pwm_path}/duty_cycle", 'r') as f:
                duty = int(f.read().strip())
            enabled = self.is_enabled()
            return period, duty, enabled
        except Exception as e:
            print(f"Error reading current values: {e}")
            return None, None, None
    
    def configure(self, frequency_hz, duty_percent, enable_output=True):
        """
        Configure PWM with proper sequence to avoid errors
        
        Args:
            frequency_hz: PWM frequency in Hz
            duty_percent: Duty cycle percentage (0-100)
            enable_output: Enable PWM after configuration
        """
        # Calculate period and duty cycle in nanoseconds
        period_ns = int(1_000_000_000 / frequency_hz)
        duty_ns = int(period_ns * duty_percent / 100)
        
        print(f"\n=== Configuring PWM{self.channel} ===")
        print(f"Frequency: {frequency_hz} Hz")
        print(f"Period: {period_ns} ns ({period_ns/1e6:.3f} ms)")
        print(f"Duty: {duty_percent}% ({duty_ns} ns)")
        
        # Get current values
        curr_period, curr_duty, curr_enabled = self.get_current_values()
        if curr_period:
            print(f"\nCurrent state:")
            print(f"  Period: {curr_period} ns")
            print(f"  Duty: {curr_duty} ns")
            print(f"  Enabled: {curr_enabled}")
        
        # CRITICAL: Disable PWM first if enabled
        if self.is_enabled():
            print("\n1. Disabling PWM...")
            if not self.disable():
                return False
            time.sleep(0.05)
        
        # 2. Set period (must be done while disabled)
        print(f"2. Setting period to {period_ns} ns...")
        if not self.set_period(period_ns):
            return False
        
        # 3. Set duty cycle (must be <= period)
        print(f"3. Setting duty cycle to {duty_ns} ns...")
        if not self.set_duty_cycle(duty_ns):
            return False
        
        # 4. Enable if requested
        if enable_output:
            print("4. Enabling PWM...")
            if not self.enable():
                return False
            print("[v] PWM enabled successfully")
        else:
            print("[v] PWM configured but left disabled")
        
        return True
    
    def stop(self):
        """Stop PWM output"""
        print(f"\n=== Stopping PWM{self.channel} ===")
        return self.disable()


def main():
    parser = argparse.ArgumentParser(
        description='Control Linux PWM via sysfs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Configure 1kHz PWM with 50% duty cycle
  %(prog)s -f 1000 -p 50 -c on
  
  # Configure but don't enable
  %(prog)s -f 1000 -p 50 -c off
  
  # Stop PWM
  %(prog)s -c off
  
  # Use different chip/channel
  %(prog)s --chip 0 --channel 3 -f 2000 -p 75 -c on
  
  # Export PWM channel
  %(prog)s --export
  
  # Unexport PWM channel
  %(prog)s --unexport
        """)
    
    parser.add_argument('--chip', type=int, default=0,
                        help='PWM chip number (default: 0)')
    parser.add_argument('--channel', type=int, default=2,
                        help='PWM channel number (default: 2)')
    parser.add_argument('-f', '--frequency', type=float,
                        help='PWM frequency in Hz')
    parser.add_argument('-p', '--duty', type=float,
                        help='Duty cycle percentage (0-100)')
    parser.add_argument('-c', '--control', choices=['on', 'off'],
                        help='Enable (on) or disable (off) PWM')
    parser.add_argument('--export', action='store_true',
                        help='Export PWM channel')
    parser.add_argument('--unexport', action='store_true',
                        help='Unexport PWM channel')
    parser.add_argument('--status', action='store_true',
                        help='Show current PWM status')
    
    args = parser.parse_args()
    
    pwm = PWMController(chip=args.chip, channel=args.channel)
    
    # Handle export/unexport
    if args.export:
        pwm.export()
        return
    
    if args.unexport:
        pwm.unexport()
        return
    
    # Show status
    if args.status:
        period, duty, enabled = pwm.get_current_values()
        if period is not None:
            freq = 1_000_000_000 / period if period > 0 else 0
            duty_pct = (duty / period * 100) if period > 0 else 0
            print(f"\n=== PWM{args.channel} Status ===")
            print(f"Period: {period} ns ({freq:.2f} Hz)")
            print(f"Duty: {duty} ns ({duty_pct:.1f}%)")
            print(f"Enabled: {enabled}")
        return
    
    # Ensure PWM is exported
    if not os.path.exists(pwm.pwm_path):
        print(f"PWM{args.channel} not exported, exporting...")
        if not pwm.export():
            sys.exit(1)
    
    # Configure PWM
    if args.frequency and args.duty is not None:
        if args.duty < 0 or args.duty > 100:
            print("Error: Duty cycle must be between 0 and 100")
            sys.exit(1)
        
        enable_output = (args.control == 'on') if args.control else True
        if not pwm.configure(args.frequency, args.duty, enable_output):
            sys.exit(1)
    
    # Just enable/disable without reconfiguring
    elif args.control:
        if args.control == 'on':
            if pwm.enable():
                print(f"PWM{args.channel} enabled")
        else:
            if pwm.disable():
                print(f"PWM{args.channel} disabled")
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
