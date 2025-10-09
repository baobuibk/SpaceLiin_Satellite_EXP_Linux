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

===== EXP-SATELLITE LINUX [Rev 1.0.1] =====
Uptime     : $(uptime)
Hostname   : $(hostname)
Disk Usage : $(df -h | awk '/\/$/ {print $3 " used of " $2}')
Memory     : $(free | awk '/Mem:/ {printf "%.1fM used of %.1fM", $3/1024, $2/1024}')
"
export PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin
