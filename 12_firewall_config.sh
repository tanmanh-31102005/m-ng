#!/bin/bash
# 12_firewall_config.sh
# Thiết lập IPTables ACL (Standard, Extended, Firewall Biên) theo mô phỏng Campus 3 Layer.

set -e

DIST2_PID=$(ps ax | grep "mininet:dist2$" | grep bash | grep -v grep | awk '{print $1}')
DMZ_PID=$(ps ax | grep "mininet:dmz_r$" | grep bash | grep -v grep | awk '{print $1}')

if [ -z "$DIST2_PID" ] || [ -z "$DMZ_PID" ]; then
    echo "Lỗi: Mininet chưa khởi chạy router (dist2, dmz_r)."
    exit 1
fi

echo "[ACL] Thiết Lập Standard ACL trên dist2 (chặn Source IP)..."
# Giả lập: Cấm 1 host từ subnet 10.0.5.0/24 (VLAN B - host h3 hoặc h4) vào DMZ
nsenter -n -t $DIST2_PID iptables -F FORWARD
nsenter -n -t $DIST2_PID iptables -A FORWARD -s 10.0.5.50/32 -d 192.168.100.0/24 -j DROP 
nsenter -n -t $DIST2_PID iptables -A FORWARD -j ACCEPT # Pass các luồng khác

# ----------------------------------------------------
# FIREWALL / EXTENDED ACL TRÊN DMZ ROUTER (dmz_r)
# eth0: DMZ
# eth1: Từ Core (Inside)
# eth2: Lên r_out (Outside / Internet)
# ----------------------------------------------------
echo "[FIREWALL] Thiết Lập Mạng DMZ trên dmz_r..."

nsenter -n -t $DMZ_PID iptables -F FORWARD
nsenter -n -t $DMZ_PID iptables -P FORWARD DROP

# --- 1. Zone INSIDE ra INTERNET và ra DMZ ---
# Cho phép Inside (từ eth1) ra Interet (qua eth2)
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth1 -o dmz_r-eth2 -j ACCEPT
# Extended ACL: Inside ra DMZ chỉ cho Web HTTP/HTTPS (Port 80/443). Nếu ping (ICMP) có thể mở để test hoặc DROP
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth1 -o dmz_r-eth0 -p tcp -m multiport --dports 80,443 -j ACCEPT
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth1 -o dmz_r-eth0 -p icmp -j ACCEPT # Cho test ping môn học
# Cấm các kết nối tcp khác từ Inside tới DMZ (SSH/RDP) & LOG
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth1 -o dmz_r-eth0 -p tcp --dport 22 -j LOG --log-prefix "FW-BLOCK-SSH: "
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth1 -o dmz_r-eth0 -j DROP

# --- 2. Zone OUTSIDE vào DMZ (Static NAT đã bóc trên r_out, từ dmz_r chỉ đường cho IP 192.168.100.10) ---
# Tích hợp Stateful Firewall & Anti-DDoS SYN Flood (Giới hạn 10 kết nối mới / giây / nguồn TCP)
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth0 -p tcp -m multiport --dports 80,443 -m state --state NEW -m limit --limit 10/s --limit-burst 20 -j ACCEPT
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth0 -p tcp -m multiport --dports 80,443 -m state --state ESTABLISHED,RELATED -j ACCEPT
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth0 -p tcp -m multiport --dports 80,443 -j LOG --log-prefix "FW-DROP-DDOS: "
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth0 -p tcp -m multiport --dports 80,443 -j DROP
# Cấm outside SSH, RDP vào DMZ (Log)
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth0 -p tcp --dport 22 -j LOG --log-prefix "FW-DROP-DMZ-SSH: "
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth0 -j DROP

# --- 3. Zone OUTSIDE vào INSIDE (Default Chặn sạch) ---
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth1 -m state --state ESTABLISHED,RELATED -j ACCEPT
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth1 -j LOG --log-prefix "FW-DROP-INSIDE: "
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth2 -o dmz_r-eth1 -j DROP

# --- 4. DMZ Giao Cắt DMZ Web 1 và 2 liên lạc hoặc trả responses ---
# Cho phép web reply lại các session.
nsenter -n -t $DMZ_PID iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
nsenter -n -t $DMZ_PID iptables -A FORWARD -i dmz_r-eth0 -o dmz_r-eth1 -j LOG --log-prefix "FW-DROP-DMZ2INSIDE: "

echo " -> Đã thiết lập xong 4 Rule Firewall Zone và 1 Extended ACL trên dmz_r"
echo "[FIREWALL] Hoàn tất bộ luật an toàn đa lớp."
