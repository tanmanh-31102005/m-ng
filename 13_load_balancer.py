#!/usr/bin/env python3
# 13_load_balancer.py
# Đo thông lượng Load Server và Cân bằng tải DNAT trên r_out
import time
import subprocess
import csv
import argparse
import sys
from datetime import datetime

# Lấy Pid của r_out (Nơi duy trì Static NAT)
def get_rout_pid():
    try:
        pid = subprocess.check_output("ps ax | grep 'mininet:r_out$' | grep bash | grep -v grep | awk '{print $1}'", shell=True).decode().strip()
        if not pid:
            raise ValueError("Empty PID")
        return pid
    except:
        print("Lỗi: Không tìm thấy node r_out của Mininet. Vui lòng chạy 03_campus_topology.py trước.")
        sys.exit(1)

ROUT_PID = get_rout_pid()

def run_ns(cmd):
    """Chạy lệnh trong namespace của r_out"""
    full_cmd = f"nsenter -m -u -i -n -p -t {ROUT_PID} {cmd}"
    return subprocess.check_output(full_cmd, shell=True).decode()

def get_bytes(interface="rout-eth1"):
    """Lấy tổng byte rx/tx từ card mạng r_out"""
    try:
        rx = int(run_ns(f"cat /sys/class/net/{interface}/statistics/rx_bytes").strip())
        tx = int(run_ns(f"cat /sys/class/net/{interface}/statistics/tx_bytes").strip())
        return rx + tx
    except:
        return 0

def update_dnat(primary="web1"):
    """Thay thế luật iptables DNAT PREROUTING 200.0.0.10 về Web đang trống"""
    print(f"[*] CẬP NHẬT IPTABLES: Chuyển hướng traffic sang {primary.upper()}")
    # Xoá luật DNAT cổng 80 cũ cho IP .10 (Web1 Proxy Virtual IP)
    run_ns("iptables -t nat -D PREROUTING -i rout-eth1 -d 200.0.0.10 -p tcp --dport 80 -j DNAT --to-destination 192.168.100.10:80 2>/dev/null || true")
    run_ns("iptables -t nat -D PREROUTING -i rout-eth1 -d 200.0.0.10 -p tcp --dport 80 -j DNAT --to-destination 192.168.100.11:80 2>/dev/null || true")
    
    # App luật NAT mới cho Virtual IP 200.0.0.10
    dest_ip = "192.168.100.10" if primary == "web1" else "192.168.100.11"
    run_ns(f"iptables -t nat -A PREROUTING -i rout-eth1 -d 200.0.0.10 -p tcp --dport 80 -j DNAT --to-destination {dest_ip}:80")

def main():
    parser = argparse.ArgumentParser(description="Load Balancer DNS / NAT bằng Python")
    parser.add_argument('--duration', type=int, default=300, help='Thời gian chạy test (giây)')
    parser.add_argument('--interval', type=int, default=5, help='Chu kỳ check (giây)')
    parser.add_argument('--high-threshold', type=int, default=80, help='Ngưỡng MAX % (Chuyển sang Web2)')
    parser.add_argument('--low-threshold', type=int, default=20, help='Ngưỡng MIN % (Hồi về Web1)')
    parser.add_argument('--max-bw', type=int, default=100, help='Băng thông tối đa giả định (Mbps)')
    args = parser.parse_args()

    # Mở Log CSV
    csv_file = open("load_log.csv", "w", newline='')
    writer = csv.writer(csv_file)
    writer.writerow(["timestamp", "web1_load(%)", "web2_load(%)", "primary_server", "action", "note"])
    
    current_primary = "web1"
    end_time = time.time() + args.duration
    
    print("=====================================================")
    print(f" BẮT ĐẦU THEO DÕI LOAD BALANCER (Thời gian: {args.duration}s)")
    print(f" - Primary: Web1 (192.168.100.10) | Secondary: Web2 (192.168.100.11)")
    print(f" - High: {args.high_threshold}% | Low: {args.low_threshold}%")
    print("=====================================================")

    prev_bytes = get_bytes()
    time.sleep(1)

    # Đảm bảo ban đầu trỏ về Web1
    update_dnat("web1")

    # Lưu biến mock_load để làm mượt biểu đồ. Ta dùng Throughput thực tế.
    # Trong Mininet nếu bạn dùng IPerf, có thể load nhảy lên 99% ngay lập tức.
    while time.time() < end_time:
        curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        curr_bytes = get_bytes()
        
        # Calculate Throughput in Mbps
        bytes_diff = curr_bytes - prev_bytes
        mbps = (bytes_diff * 8) / (1000 * 1000) / args.interval
        prev_bytes = curr_bytes
        
        # Giới hạn Load 100%
        load_pct = min(100.0, (mbps / args.max_bw) * 100)
        
        # Khởi tạo mức Load hiển thị cho cả 2 server cho Biểu đồ
        w1_load = load_pct if current_primary == "web1" else 5.0 # Background ping/noise
        w2_load = load_pct if current_primary == "web2" else 5.0
        
        # Tuy nhiên nếu chưa có iperf/curl được gọi, traffic là 0. 
        # Cấu trúc Script cho phép mock nhẹ bằng Request nếu Throughput L2 = 0
        if load_pct < 1.0:
            pass # Chờ user chạy sinh tải (bước 7)
            
        action = "monitor"
        note = ""

        # Logic Thay Đổi DNAT (Failover/Fallback Thresholds)
        if current_primary == "web1" and w1_load > args.high_threshold:
            current_primary = "web2"
            action = "switch"
            note = f"web1 overloaded ({w1_load:.2f}%)"
            update_dnat("web2")
            
        elif current_primary == "web2" and w2_load < args.low_threshold:
            current_primary = "web1"
            action = "switch"
            note = f"web2 load dropped ({w2_load:.2f}%), back to web1"
            update_dnat("web1")

        print(f"[{curr_time}] W1_Load: {w1_load:5.2f}% | W2_Load: {w2_load:5.2f}% | Mode: {current_primary} | {action} | {note}")
        writer.writerow([curr_time, f"{w1_load:.2f}", f"{w2_load:.2f}", current_primary, action, note])
        csv_file.flush()

        time.sleep(args.interval)

    csv_file.close()
    print("Đã hoàn tất theo dõi Load.")

if __name__ == "__main__":
    main()
