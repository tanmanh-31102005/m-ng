# TÀI LIỆU THIẾT KẾ SƠ ĐỒ MẠNG LOGIC, VẬT LÝ VÀ IP PLANNING

## 1. SƠ ĐỒ MẠNG LOGIC (Logical Topology)

Mô hình thiết kế dựa trên tiêu chuẩn Campus 3 lớp (Core - Distribution - Access) và tách biệt một cụm Server vào DMZ. Cụ thể mạng được tổ chức như sau:

```text
               [ INTERNET / OUTSIDE ]
                  (203.0.113.0/24)
                         │
                 ┌───────┴───────┐
                 │    r_out      │ (ISP Gateway / NAT Biên)
                 └───────┬───────┘
                         │
                 ┌───────┴───────┐
                 │     dmz_r     │ (Firewall / DMZ Router)
                 └───────┬───────┘
         ┌───────────────┴───────────────┐
         │ (192.168.100.x)               │ Subnet OSPF Area 0
  ┌──────┴──────┐                 ┌──────┴──────┐
  │ web1 (SRV)  │                 │    core1    │ (Core Switch/Router)
  └─────────────┘                 └──────┬──────┘
  ┌─────────────┐                        │ OSPF
  │ web2 (SRV)  │                        │
  └──────┬──────┘         ┌──────────────┴──────────────┐
         │          ┌─────┴─────┐                 ┌─────┴─────┐
         └──────────┤   dist1   │ (OSPF Area 0)   │   dist2   │
                    └─────┬─────┘                 └─────┬─────┘
                          │                             │
                    ┌─────┴─────┐                 ┌─────┴─────┐
                    │   acc1    │ (Switch Access) │   acc2    │
                    └─────┬─────┘                 └─────┬─────┘
                  ┌───────┴───────┐               ┌───────┴───────┐
                  │               │               │               │
             [Host h1]       [Host h2]       [Host h3]       [Host h4]
             VLAN/Sub A      VLAN/Sub A      VLAN/Sub B      VLAN/Sub B
```

### Luồng Dữ Liệu Chính:
1. **Inside → DMZ**: Client (h1,h2...) truy cập các dịch vụ nội bộ (ping, HTTP) trên DMZ (web1, web2) qua định tuyến OSPF nội mạng. Sẽ bị kiểm soát bởi Firewall Standard/Extended ACL.
2. **Inside → Internet**: Client đi qua `dmz_r` định tuyến đẩy ra `r_out` dựa vào default route, tại r_out thực hiện PAT ngụy trang (Overload) thành public IP để ra net.
3. **Outside → DMZ**: User từ Internet gõ ip public (Static NAT: 200.0.0.10, 200.0.0.11, v.v.), Router `r_out` DNAT vào `dmz_r` và đẩy về DMZ Server `192.168.100.x`.
4. **Outside → Inside**: Default bị **chặn hoàn toàn** bởi IP Tables Firewall trên biên.

---

## 2. BẢNG THIẾT BỊ VÀ VAI TRÒ (Physical Mininet Nodes)

| Tên Node | Loại Thiết Bị Mininet | Vai Trò & Lớp (Layer) | Chức năng (Routing / Protocol) |
|---|---|---|---|
| `core1` | LinuxRouter (Host with ip_forward) | Core / Backbone | Định tuyến lõi, OSPF Area 0, Gateway |
| `dist1` | LinuxRouter / OVS | Distribution | Định hướng tới Access 1, OSPF Area 0 |
| `dist2` | LinuxRouter / OVS | Distribution | Định hướng tới Access 2, OSPF Area 0 |
| `acc1` | OVS (OpenvSwitch) | Access 1 | Switching layer 2 subnet A |
| `acc2` | OVS (OpenvSwitch) | Access 2 | Switching layer 2 subnet B |
| `dmz_r` | LinuxRouter | DMZ / Security Biên | Định tuyến giữa DMZ/Core/Outside, chạy Firewall ACL |
| `r_out` | LinuxRouter | Outside Gateway | Định tuyến biên Internet, thực thi PAT, Static NAT |
| `web1`, `web2` | Host | Server (DMZ Layer) | Đích Load Balancing HTTP Python |
| `h1`...`h4`| Host | End Users (Access) | Client phát sinh kết nối iperf/HTTP |
| `h_inet` | Host | User (Internet User) | Nằm ngoài `r_out` để test vào hệ thống |

---

## 3. KẾ HOẠCH ĐỊA CHỈ IP (IP Provisioning Plan)

| Subnet Tên / Interface | Phân lớp dải IP (CIDR) | IPv4 Gateway | Range Host cấp phát | Mô tả kết nối |
|---|---|---|---|---|
| **P2P: dmz_r -- core1** | `10.0.1.0/24` | - | `10.0.1.1` (dmz), `10.0.1.2` (core) | Đường trục L3 Backbone |
| **P2P: core1 -- dist1** | `10.0.2.0/24` | - | `10.0.2.1` (cor), `10.0.2.2` (dist) | Backbone Core-Dist |
| **P2P: core1 -- dist2** | `10.0.3.0/24` | - | `10.0.3.1` (cor), `10.0.3.2` (dist) | Backbone Core-Dist |
| **VLAN/Subnet Inside A**| `10.0.4.0/24` | `10.0.4.254` (dist1) | `10.0.4.1` - `10.0.4.253` | Cấp mạng cho `acc1` (h1, h2) |
| **VLAN/Subnet Inside B**| `10.0.5.0/24` | `10.0.5.254` (dist2) | `10.0.5.1` - `10.0.5.253` | Cấp mạng cho `acc2` (h3, h4) |
| **DMZ Server Farm** | `192.168.100.0/24` | `192.168.100.254` (dmz) | `.10` (Web1), `.11` (Web2) | Vùng máy chủ phân lập |
| **P2P: dmz_r -- r_out** | `192.168.200.0/24` | - | `.1` (dmz), `.2` (r_out) | Link lên r_out (ISP biên) |
| **Internet Simulation** | `203.0.113.0/24` | `203.0.113.254` (r_out)| `203.0.113.100` (h_inet) | Mạng Public giả lập Test NAT |
| **Public IP Pool (VIP)**| `200.0.0.0/24` | - | `.100` (PAT Out), `.10/11` (NAT) | ISP Pool dùng NAT IP |

> Dựa vào bảng này, OSPF sẽ chạy trên `core1`, `dist1`, `dist2`, `dmz_r`. Interface kết nối lên `r_out` trên `dmz_r` sẽ được redistribute default route (O\*E2).
> Load Balancer sẽ mapping Static NAT trên `r_out` Destination = `200.0.0.10` về `192.168.100.10` (Web1), qua biên dmz_r. Khi tải > 80%, rule sẽ bị LoadBalancer đè đổi sang `.11` (Web2).
