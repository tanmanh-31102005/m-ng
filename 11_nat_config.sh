#!/bin/bash
# 11_nat_config.sh
# Thực hiện PAT (Overload) cho người dùng Inside ra Internet và Static NAT hướng về Cụm Web.
# Chạy thủ công trên Terminal 2 sau khi có Mininet và OSPF bật.

set -e

# Tìm PID của router cấp Internet r_out và dmz_r
ROUT_PID=$(ps ax | grep "mininet:r_out$" | grep bash | grep -v grep | awk '{print $1}')
DMZ_PID=$(ps ax | grep "mininet:dmz_r$" | grep bash | grep -v grep | awk '{print $1}')

if [ -z "$ROUT_PID" ] || [ -z "$DMZ_PID" ]; then
    echo "Lỗi: Mininet chưa chạy Router r_out hoặc dmz_r."
    exit 1
fi

echo "[NAT] Cấu hình NAT trên r_out (PID: $ROUT_PID)..."

# Xóa các luật NAT rác cũ
nsenter -n -t $ROUT_PID iptables -t nat -F
nsenter -n -t $ROUT_PID iptables -t nat -X

# --- 1. PAT (SNAT) CHO INSIDE VÀ DMZ RA NGOÀI INTERNET (eth1 của r_out là cổng internet) ---
# Tức là Traffic đi khỏi 203.0.113.254 (interface rout-eth1)
nsenter -n -t $ROUT_PID iptables -t nat -A POSTROUTING -o rout-eth1 -s 10.0.0.0/8 -j MASQUERADE
nsenter -n -t $ROUT_PID iptables -t nat -A POSTROUTING -o rout-eth1 -s 192.168.100.0/24 -j MASQUERADE
echo " -> Áp dụng PAT cho dải 10.x.x.x và 192.168.100.x ra cổng rout-eth1"

# --- 2. STATIC DESTINATION NAT CHO INTERNET VÀO WEB SERVER DMZ (200.0.0.10 -> Web1/2) ---
# Địa chỉ công cộng tĩnh là 200.0.0.10:80 (Web1) và 200.0.0.11:80 (Web2)
# Khách từ Interface h_inet gõ ping/curl vào 200.0.0.10 sẽ được dịch dích DNAT
nsenter -n -t $ROUT_PID iptables -t nat -A PREROUTING -i rout-eth1 -d 200.0.0.10 -p tcp --dport 80 -j DNAT --to-destination 192.168.100.10:80
nsenter -n -t $ROUT_PID iptables -t nat -A PREROUTING -i rout-eth1 -d 200.0.0.11 -p tcp --dport 80 -j DNAT --to-destination 192.168.100.11:80
echo " -> Áp dụng PREROUTING DNAT 200.0.0.10, 200.0.0.11 cổng 80 vào DMZ Servers"

# --- 3. LOGGING CHO NAT (Cho phép tracking để parse CSV report) ---
nsenter -n -t $ROUT_PID iptables -t nat -A POSTROUTING -m limit --limit 5/min -j LOG --log-prefix "NAT-PAT-OUT: " --log-level 4
nsenter -n -t $ROUT_PID iptables -t nat -A PREROUTING -m limit --limit 5/min -j LOG --log-prefix "NAT-DNAT-IN: " --log-level 4
echo " -> Đã bật Linux Kernel Logging cho NAT rule (check dmesg / var/log/syslog)"

echo "[NAT] Cấu hình hoàn tất. Để kiểm tra: sudo nsenter -n -t $ROUT_PID iptables -t nat -L -v"
