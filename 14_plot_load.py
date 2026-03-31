#!/usr/bin/env python3
# 14_plot_load.py
# Vẽ đồ thị đường phân phối Tải Server từ load_log.csv
import matplotlib.pyplot as plt
import csv
import sys
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Vẽ Đồ Thị Load Balancer DMZ")
    parser.add_argument('--log', type=str, default="load_log.csv", help='File CSV đầu vào (thường là load_log.csv)')
    parser.add_argument('--output', type=str, default="load_chart.png", help='Tên hình xuất ra')
    parser.add_argument('--stats', type=str, default="load_stats.txt", help='File báo cáo tóm tắt text')
    args = parser.parse_args()

    timestamps = []
    web1_loads = []
    web2_loads = []
    actions = []

    try:
        with open(args.log, 'r') as file:
            reader = csv.reader(file)
            header = next(reader)
            for row in reader:
                try:
                    # Parse timestamp format: "YYYY-MM-DD HH:MM:SS.mmm"
                    ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f")
                    timestamps.append(ts)
                    web1_loads.append(float(row[1]))
                    web2_loads.append(float(row[2]))
                    actions.append(row[4])
                except Exception as e:
                	continue
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file nhật ký {args.log}. Vui lòng chạy 13_load_balancer.py trước.")
        sys.exit(1)

    if not timestamps:
        print("Không có log phù hợp.")
        sys.exit(0)

    # 1. Vẽ đồ thị Matplotlib
    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, web1_loads, label='Web1 (192.168.100.10)', color='blue')
    plt.plot(timestamps, web2_loads, label='Web2 (192.168.100.11)', color='orange')
    
    # Kẻ các đường ngưỡng High/Low
    plt.axhline(y=80, color='r', linestyle='--', label='Max Threshold (80%)')
    plt.axhline(y=20, color='g', linestyle='--', label='Min Threshold (20%)')
    
    # Đánh dấu các mốc Switch Server
    for i, action in enumerate(actions):
        if action == "switch":
            plt.axvline(x=timestamps[i], color='k', linestyle=':', alpha=0.5)

    plt.xlabel('Thời gian')
    plt.ylabel('Load Giả lập theo Băng thông (%)')
    plt.title('Dashboard Cân Bằng Tải Cụm DMZ (Round Robin bằng Ngưỡng)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(args.output)
    print(f"-> Đã xuất Đồ thị tại {args.output}")

    # 2. Phát sinh Report File Dạng Text
    try:
        with open(args.stats, 'w', encoding='utf-8') as sf:
            sf.write("="*80 + "\n")
            sf.write("📊 LOAD BALANCING STATISTICS REPORT\n")
            sf.write("="*80 + "\n\n")
            
            w1_avg = sum(web1_loads)/len(web1_loads)
            w2_avg = sum(web2_loads)/len(web2_loads)
            
            sf.write("📈 LOAD CHUNG:\n")
            sf.write(f"  Total Data Points: {len(timestamps)}\n")
            sf.write(f"  Switch Server Events: {actions.count('switch')}\n\n")
            
            sf.write("📈 WEB1 THỐNG KÊ:\n")
            sf.write(f"  Max Load: {max(web1_loads)}%\n")
            sf.write(f"  Avr Load: {w1_avg:.2f}%\n\n")
            
            sf.write("📈 WEB2 THỐNG KÊ:\n")
            sf.write(f"  Max Load: {max(web2_loads)}%\n")
            sf.write(f"  Avr Load: {w2_avg:.2f}%\n\n")
            
            sf.write("================================================================================\n")
        print(f"-> Đã xuất tóm tắt text tại {args.stats}")
        
    except IOError as e:
        print(f"Lỗi khi viết file báo cáo: {e}")

if __name__ == "__main__":
    main()
