#!/bin/bash
# 00_setup_environment.sh
# Hướng dẫn và script tự động cấu hình môi trường chuẩn cho Campus Network 3 Lớp
# Hệ điều hành: Ubuntu 22.04 tĩnh
# Chạy script bằng quyền sudo: `sudo bash 00_setup_environment.sh`

set -e

echo "==========================================================="
echo " CÀI ĐẶT MÔI TRƯỜNG MININET & FRROUTING & PYTHON (UBUNTU 22.04)"
echo "==========================================================="

# 1. Cập nhật hệ thống
echo "[1/4] Đang cập nhật danh sách Apt..."
apt update && apt upgrade -y

# 2. Cài đặt các công cụ mạng, giả lập (Mininet, iperf3, openvswitch)
echo "[2/4] Đang cài Mininet, OVS, và các công cụ network test..."
apt install -y mininet openvswitch-switch openvswitch-testcontroller \
    iperf3 iputils-ping net-tools tcpdump iptables nmap curl xterm \
    python3 python3-pip python3-dev \
    frr frr-pythontools vim sysstat

# 3. Kích hoạt IP Forwarding toàn hệ thống (Cần cho cấu hình Router Mininet Linux)
echo "[3/4] Bật IPv4 Forwarding..."
sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf || true
sysctl -p

# 4. Cài thư viện Python cho giám sát, sinh đồ thị
echo "[4/4] Cài đặt Matplotlib, Psutil dùng cho Load Balancer Python..."
pip3 install matplotlib psutil flask requests apscheduler --break-system-packages

echo "==========================================================="
echo " HOÀN TẤT!"
echo " Hãy kiểm tra bằng các lệnh sau để đảm bảo cài đặt thành công:"
echo " 1. mn --version (Mininet)"
echo " 2. frr --version (FRRouting)"
echo " 3. python3 -c \"import matplotlib; print('Matplotlib OK')\""
echo " 4. iperf3 -v"
echo "==========================================================="
