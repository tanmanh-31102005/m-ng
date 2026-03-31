# HƯỚNG DẪN TRIỂN KHAI CAMPUS 3-TIER NETWORK VỚI DMZ - TỪ A-Z

Đây là tài liệu chỉ nam cho **đồ án Mininet Campus 3 Lớp**. Hãy thực hiện lần lượt các bước và sao chép lệnh y hệt.

## MỤC LỤC
1. CHUẨN BỊ MÔI TRƯỜNG & TOPOLOGY
2. CẤU HÌNH ĐỊNH TUYẾN
3. BẢO MẬT & CÂN BẰNG TẢI
4. CHẠY MÔ PHỎNG VÀ VẼ ĐỒ THỊ
5. ĐO LƯỜNG VÀ KIỂM THỬ ACL

---

### PHẦN 1 & 2: Cài Đặt và Khởi Trình

**Bước 1:** Bật Terminal 1 (làm thư mục chứa source). Chạy Script Cài Đặt.
```bash
sudo bash 00_setup_environment.sh
```

**Bước 2:** Bật sơ đồ vật lý Mininet.
```bash
sudo python3 03_campus_topology.py
```
> Giao diện Mininet (`mininet>`) sẽ dừng. Đừng tắt nó, hãy qua Terminal 2.

---

### PHẦN 3 & 4: Định Tuyến OSPF (FRRouting)

**Bước 3:** Ở Terminal 2, chạy cấu hình các Router Node thông qua bash nsenter. Script này tự động trích xuất PID mạng của Mininet để chèn Cấu hình FRR.
```bash
sudo bash 10_setup_ospf.sh
```

*(Kiểm tra nhanh OSPF trong Terminal 1 bằng `mininet> h1 ping h3` (Inside - Inside VLAN B))*

---

### PHẦN 5 & 6: Khởi Chạy DMZ Server, Cấu hình NAT (PAT, DNAT) và Firewall ACL

**Bước 4:** Bật Web Server trên Web1 (IP 192.168.100.10) và Web2 (192.168.100.11)
```bash
sudo bash 15_start_web_servers.sh
```

**Bước 5:** Thực thi PAT trên Cổng Ngoài Out (r_out) cho 10.x ra net và Static DNAT VIP `200.0.0.10` vào `192.168.100.x` Web1.
```bash
sudo bash 11_nat_config.sh
```

**Bước 6:** Thực thi Extended vả Standard Firewall chặn PING/SSH/RDP linh tinh.
```bash
sudo bash 12_firewall_config.sh
```

---

### PHẦN 7 & 8: ĐO LƯỜNG VÀ CÂN BẰNG TẢI PYTHON DỰA THEO BANDWIDTH (Ngưỡng 80%)

Để mô phỏng, phần code `13_load_balancer.py` được thiết kế đọc mức nghẽn mạng băng thông L2 để phán đoán. 

**Bước 7:** Khởi chạy Monitor Balancer tại Terminal 2 (Để nó tự in ra Traffic)
```bash
sudo python3 13_load_balancer.py --duration 120 --interval 2 --high-threshold 80 --low-threshold 20 --max-bw 800
```
*(Tham số `max-bw 800`: tức là Max Bandwidth iperf tạo ra khoảng ~800Mbps trên Mininet ubuntu local)*

**Bước 8:** Sinh tải (Quay lại Terminal 1 Mininet). Sinh Tải bằng `iperf` qua IP Virtual NAT (giả lập Client Inet xả Traffic vào Web1).
```bash
# Ở mininet:
mininet> web1 iperf3 -s -D
mininet> h_inet iperf3 -c 200.0.0.10 -t 30 -b 900M
```
> Lập tức ở Terminal 2, bạn sẽ thấy throughput MBps của web1 vọt lên >80%, bộ Python sẽ gõ lệnh xoá DNAT Web1 và gán vào Web2 ngay tức thì. Terminal in log Load.

**Bước 9:** Tắt giả lập, vẽ đồ thị.
```bash
# Chờ Monitor (Terminal 2) hết giờ 120s hoặc ấn Ctr+C
sudo python3 14_plot_load.py --log load_log.csv
```
> Lúc này có file `load_chart.png` (sơ đồ đường tải) và `load_stats.txt` cho giáo viên.  *(Do chạy `iperf` nên load sẽ vọt lên rất sâu và đồ thị Switch sang Cổng 2).*

---

### BÁO CÁO NHẬT KÝ (PHẦN 8 BỔ SUNG)

**1. Đo Throughput Ping và Bandwidth Iperf (So sánh trước và sau NAT/ACL)**
```bash
mininet> h1 ping -c 5 h2  # (Trong mạng LAN)
mininet> h_inet ping -c 5 200.0.0.10 # (Qua PAT/DNAT DMZ_R & R_OUT)
mininet> h_inet iperf3 -c 200.0.0.10 -t 10 # Đo Bandwidth thực tế qua biên độ.
```

**2. Test Logging của Firewall ACL (Port SSH)**
Bạn hãy dùng host h1 ssh (cổng 22 mặc định Firewal DROP) vào DMZ Web.
```bash
mininet> h1 xterm  #(Bật xterm host)
# Trong xterm h1 gõ: nc -zv 192.168.100.10 22
```
Để xem Log (Bị rớt bởi ACL) ở Terminal host:
```bash
cat /var/log/syslog | grep "FW-BLOCK-SSH:"
cat /var/log/kern.log | grep "NAT-DNAT-IN:"
```
File report sẽ có các bằng chứng rõ ràng của bảng NAT Log.
Mọi chi tiết xin làm theo các bước trên máy ảo Ubuntu 22.04 LTS (RAM min 4GB cho Mininet FRRouting Python3). Đã cấu hình đủ!
