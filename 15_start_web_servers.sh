#!/bin/bash
# 15_start_web_servers.sh
# Khởi chạy HTTP Server trên 2 Host làm DMZ (web1 và web2)
set -e

WEB1_PID=$(ps ax | grep "mininet:web1$" | grep bash | grep -v grep | awk '{print $1}')
WEB2_PID=$(ps ax | grep "mininet:web2$" | grep bash | grep -v grep | awk '{print $1}')

if [ -z "$WEB1_PID" ] || [ -z "$WEB2_PID" ]; then
    echo "Lỗi: Không tìm thấy node web1, web2."
    exit 1
fi

echo "[WEB] Bật Server 1 (192.168.100.10) ..."
# Tạo trang html để test proxy
nsenter -m -u -i -n -p -t $WEB1_PID mkdir -p /tmp/web1
nsenter -m -u -i -n -p -t $WEB1_PID bash -c "echo '<h2>Toi la Web 1 - 192.168.100.10</h2>' > /tmp/web1/index.html"
nsenter -m -u -i -n -p -t $WEB1_PID bash -c "cd /tmp/web1 && nohup python3 -m http.server 80 > /dev/null 2>&1 &"

echo "[WEB] Bật Server 2 (192.168.100.11) ..."
nsenter -m -u -i -n -p -t $WEB2_PID mkdir -p /tmp/web2
nsenter -m -u -i -n -p -t $WEB2_PID bash -c "echo '<h2>Toi la Web 2 - 192.168.100.11</h2>' > /tmp/web2/index.html"
nsenter -m -u -i -n -p -t $WEB2_PID bash -c "cd /tmp/web2 && nohup python3 -m http.server 80 > /dev/null 2>&1 &"

echo "-> Web Servers DMZ đã sẵn sàng ở http://192.168.100.10 và http://192.168.100.11."
