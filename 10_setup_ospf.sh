#!/bin/bash
# 10_setup_ospf.sh
# Script tự động đọc cấu hình FRR từ các file .conf và đẩy vào Mininet Namespaces

set -e

# Đảm bảo daemon frr hệ thống ngoài không can thiệp
systemctl stop frr || true
mkdir -p /tmp/frr_configs

# Ánh xạ Router Node tới file .conf
declare -A CONFS
CONFS["core1"]="Topology & Routing/04_frr_core1.conf"
CONFS["core2"]="Topology & Routing/05_frr_core2.conf"
CONFS["dist1"]="Topology & Routing/06_frr_dist1.conf"
CONFS["dist2"]="Topology & Routing/07_frr_dist2.conf"
CONFS["dmz_r"]="Topology & Routing/08_frr_dmz_r.conf"
CONFS["r_out"]="Topology & Routing/09_frr_r_out.conf"

echo "Đang tự động nạp cấu hình FRR (.conf) vào các node Mininet ..."

# R_out không chạy OSPF, chỉ chạy Core, Dist và DMZ
for ROUTER in core1 core2 dist1 dist2 dmz_r; do
  FILE_PATH="${CONFS[$ROUTER]}"
  
  # Tìm PID của node mininet
  PID=$(ps ax | grep "mininet:$ROUTER$" | grep bash | grep -v grep | awk '{print $1}')
  
  if [ -z "$PID" ]; then
    echo "Lỗi: Không tìm thấy node $ROUTER đang chạy. Mở Mininet trước."
    exit 1
  fi
  
  if [ ! -f "$FILE_PATH" ]; then
      echo "Cảnh báo: Không tìm thấy file $FILE_PATH. Xin đảm bảo chạy script từ ổ đĩa gốc campus-network."
      exit 1
  fi
  
  echo "=> Setup $ROUTER qua $FILE_PATH (PID: $PID)..."
  mkdir -p "/tmp/frr_configs/$ROUTER"
  cp "$FILE_PATH" "/tmp/frr_configs/$ROUTER/frr.conf"
  
  cat > "/tmp/frr_configs/$ROUTER/daemons" << EOF
zebra=yes
bgpd=no
ospfd=yes
ospf6d=no
ripd=no
EOF

  nsenter -m -u -i -n -p -t $PID /usr/lib/frr/zebra -d -f /tmp/frr_configs/$ROUTER/frr.conf -i /tmp/frr_configs/$ROUTER/zebra.pid -z /tmp/frr_configs/$ROUTER/zserv.api
  sleep 1
  
  nsenter -m -u -i -n -p -t $PID /usr/lib/frr/ospfd -d -f /tmp/frr_configs/$ROUTER/frr.conf -i /tmp/frr_configs/$ROUTER/ospfd.pid -z /tmp/frr_configs/$ROUTER/zserv.api
  sleep 1
done

# Fix routing ra Default Route trên DMZ_r chỏ lên r_out (Do r_out không tham gia OSPF Area)
DMZ_PID=$(ps ax | grep "mininet:dmz_r$" | grep bash | grep -v grep | awk '{print $1}')
nsenter -m -u -i -n -p -t $DMZ_PID route add default gw 192.168.200.2

# Cấu hình tĩnh cho r_out routing ngược về LAN
ROUT_PID=$(ps ax | grep "mininet:r_out$" | grep bash | grep -v grep | awk '{print $1}')
nsenter -m -u -i -n -p -t $ROUT_PID route add -net 10.0.0.0 netmask 255.0.0.0 gw 192.168.200.1
nsenter -m -u -i -n -p -t $ROUT_PID route add -net 192.168.100.0 netmask 255.255.255.0 gw 192.168.200.1

echo "==================================="
echo "HOÀN TẤT NẠP OSPF TỪ .CONF VÀ STATIC ROUTE BIÊN."
