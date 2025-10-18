#!/bin/sh
echo "
   ___   ____ ____     ___ ___   ___   ____
  / _ ) / __// __/____<  // _ \ / _ \ / __/
 / _  |/ _/ / _/ /___// // // // // // _ \ 
/____//___//___/     /_/ \___/ \___/ \___/ 
   ___   ___ __  __      ____ _  __ ___    
  / _ \ / _ |\ \/ /____ / __/| |/_// _ \   
 / ___// __ | \  //___// _/ _>  < / ___/   
/_/   /_/ |_| /_/     /___//_/|_|/_/  

======== PAY-EXP LINUX [Rev 1.1.0] ========
Uptime     : $(uptime)
Hostname   : $(hostname)
Disk Usage : $(df -h | awk '/\/$/ {print $3 " used of " $2}')
Memory     : $(free | awk '/Mem:/ {printf "%.1fM used of %.1fM", $3/1024, $2/1024}')
"
export PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/root/.a55_src/00_src/libcsp/00_Dev16/DevSrc
alias exp_run='/home/root/.a55_src/00_src/libcsp/00_Dev16/DevBuild/exp_csp_client'
alias obc_run='/usr/bin/python3 /home/root/.a55_src/00_src/libcsp/00_Dev16/DevSrc/obc_csp_host.py'
alias m33_run='bash /home/root/tools/run_m33.sh'
alias m33_stop='bash /home/root/tools/stop_m33.sh'
alias m33_state='bash /home/root/tools/state_m33.sh'
alias fw='rm /home/root/*.elf && m33_stop && rz'
alias m33_fw='bash /home/root/tools/fw_recv_and_run.sh'

echo "Available aliases:"
alias | grep -E 'exp_run|obc_run'

echo "===========================================
"
