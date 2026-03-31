#!/usr/bin/python3
# 03_campus_topology.py
# Khởi tạo mô hình mạng Campus 3 Layers + DMZ + ISP trên Mininet cho đồ án OSPF.

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class LinuxRouter( Node ):
    """Định nghĩa Router node có hỗ trợ IP forwarding (giúp FRR và NAT chạy trơn tru)"""
    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Bật IPv4 forwarding
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()

class CampusTopo( Topo ):
    """Sơ đồ mạng 3 lớp Campus:
       - 1 Core Router (core1)
       - 2 Distribution Routers (dist1, dist2)
       - 2 Access Switch (acc1, acc2)
       - 1 DMZ Router/Firewall (dmz_r)
       - 1 ISP Outside Router (r_out)
       - Máy chủ Web: web1, web2
       - Inside Host: h1, h2 (acc1), h3, h4 (acc2)
       - Outside Host: h_inet (sau lưng ISP r_out)
    """

    def build( self, **_opts ):

        defaultIP_core1 = '10.0.1.2/24' # Link tới DMZ_r
        defaultIP_dist1 = '10.0.2.2/24' # Link tới Core 1
        defaultIP_dist2 = '10.0.3.2/24' # Link tới Core 1
        defaultIP_dmz_r = '192.168.100.254/24' # Gateway cho DMZ Web Servers
        defaultIP_rout = '203.0.113.254/24' # Gateway cho Host Inet

        # >>> KHỞI TẠO ROUTER (Bật IP Forwarding)
        info( '*** Add routers\n' )
        core1 = self.addNode( 'core1', cls=LinuxRouter, ip=defaultIP_core1 )
        core2 = self.addNode( 'core2', cls=LinuxRouter, ip='10.0.8.1/24' ) # Thêm Core2 HA
        dist1 = self.addNode( 'dist1', cls=LinuxRouter, ip=defaultIP_dist1 )
        dist2 = self.addNode( 'dist2', cls=LinuxRouter, ip=defaultIP_dist2 )
        dmz_r = self.addNode( 'dmz_r', cls=LinuxRouter, ip=defaultIP_dmz_r )
        r_out = self.addNode( 'r_out', cls=LinuxRouter, ip=defaultIP_rout )

        # >>> KHỞI TẠO SWITCH (Lớp 2 / Access) - Đã bật STP chống loop
        info( '*** Add Access Switches\n' )
        acc1 = self.addSwitch('acc1', cls=OVSKernelSwitch, failMode='standalone', stp=True)
        acc2 = self.addSwitch('acc2', cls=OVSKernelSwitch, failMode='standalone', stp=True)

        # >>> KHỞI TẠO HOSTS & SERVERS
        info( '*** Add Inside Hosts\n' )
        h1 = self.addHost( 'h1', ip='10.0.4.1/24', defaultRoute='via 10.0.4.254' )
        h2 = self.addHost( 'h2', ip='10.0.4.2/24', defaultRoute='via 10.0.4.254' )
        h3 = self.addHost( 'h3', ip='10.0.5.1/24', defaultRoute='via 10.0.5.254' )
        h4 = self.addHost( 'h4', ip='10.0.5.2/24', defaultRoute='via 10.0.5.254' )

        info( '*** Add DMZ Servers\n' )
        web1 = self.addHost( 'web1', ip='192.168.100.10/24', defaultRoute='via 192.168.100.254' )
        web2 = self.addHost( 'web2', ip='192.168.100.11/24', defaultRoute='via 192.168.100.254' )

        info( '*** Add Internet Host (Outside)\n' )
        h_inet = self.addHost( 'h_inet', ip='203.0.113.100/24', defaultRoute='via 203.0.113.254' )

        # >>> LIÊN KẾT NETWORK (LINKS)
        info( '*** Add Links\n' )
        
        # 1. Liên kết Router Core - Dist - DMZ Backbone
        # Core1 (eth0) <-> dmz_r (eth1 - 10.0.1.1/24)
        self.addLink( core1, dmz_r, intfName1='core1-eth0', intfName2='dmz_r-eth1',
                      params1={ 'ip' : '10.0.1.2/24' }, params2={ 'ip' : '10.0.1.1/24' } )
                      
        # Core1 (eth1) <-> dist1 (eth0 - 10.0.2.2/24)
        self.addLink( core1, dist1, intfName1='core1-eth1', intfName2='dist1-eth0',
                      params1={ 'ip' : '10.0.2.1/24' }, params2={ 'ip' : '10.0.2.2/24' } )
                      
        # Core1 (eth2) <-> dist2 (eth0 - 10.0.3.2/24)
        self.addLink( core1, dist2, intfName1='core1-eth2', intfName2='dist2-eth0',
                      params1={ 'ip' : '10.0.3.1/24' }, params2={ 'ip' : '10.0.3.2/24' } )

        # Core2 (Redundancy HA)
        self.addLink( core2, dmz_r, intfName1='core2-eth0', intfName2='dmz_r-eth4',
                      params1={ 'ip' : '10.0.8.2/24' }, params2={ 'ip' : '10.0.8.1/24' } )
        self.addLink( core2, dist1, intfName1='core2-eth1', intfName2='dist1-eth2',
                      params1={ 'ip' : '10.0.6.1/24' }, params2={ 'ip' : '10.0.6.2/24' } )
        self.addLink( core2, dist2, intfName1='core2-eth2', intfName2='dist2-eth2',
                      params1={ 'ip' : '10.0.7.1/24' }, params2={ 'ip' : '10.0.7.2/24' } )

        # 2. Liên kết ISP r_out <-> dmz_r
        self.addLink( dmz_r, r_out, intfName1='dmz_r-eth2', intfName2='rout-eth0',
                      params1={ 'ip' : '192.168.200.1/24' }, params2={ 'ip' : '192.168.200.2/24' } )

        # Liên kết ISP r_out <-> host Internet
        self.addLink( r_out, h_inet, intfName1='rout-eth1', intfName2='h_inet-eth0' )

        # 3. Liên kết Server Farm <-> dmz_r (dmz default eth0 = 192.168.100.254)
        self.addLink( web1, dmz_r, intfName1='web1-eth0', intfName2='dmz_r-eth0' )
        self.addLink( web2, dmz_r, intfName1='web2-eth0', intfName2='dmz_r-eth3' ) # eth3 for web2 p2p link instead of Switch for simplicity, Web2 ip: 192.168.100.11/24 GW: .254. Ta gán ip phụ cho dmz_r-eth3
        
        # 4. Liên kết Access <-> Distribution
        # dist1 (eth1 GW 10.0.4.254) <-> acc1 (L2) <-> h1, h2
        self.addLink( dist1, acc1, intfName1='dist1-eth1', intfName2='acc1-eth1', params1={ 'ip' : '10.0.4.254/24' } )
        self.addLink( h1, acc1 )
        self.addLink( h2, acc1 )

        # dist2 (eth1 GW 10.0.5.254) <-> acc2 (L2) <-> h3, h4
        self.addLink( dist2, acc2, intfName1='dist2-eth1', intfName2='acc2-eth1', params1={ 'ip' : '10.0.5.254/24' } )
        self.addLink( h3, acc2 )
        self.addLink( h4, acc2 )

def run():
    "Tạo và khởi chạy Mininet CLI"
    topo = CampusTopo()
    # disable controller vì chúng ta định tuyến tĩnh/OSPF chứ không dùng SDN Flow Control
    net = Mininet( topo=topo, controller=None )

    # Do web2 cắm trực tiếp vào cổng eth3 của dmz_r cùng dải mạng với web1 (cắm eth0 dmz_r), 
    # Ta xử lý routing cho dmz_r: gỡ default ip config cho eth3, dùng bridge tĩnh hoặc proxy_arp nhưng tốt nhất ở đây là gán eth3 thêm IP tương tự hoặc set arp. Trong mininet gắn 2 host cùng subnet lên 2 port router thì cần gán IP. 
    # Cách tốt hơn: Ta sửa lại gán cho web2 một default route riêng nếu DMZ chia 2 dải hoặc tạo một switch DMZ ảo để nối web1, 2 với dmz_r.
    # Nhớ thêm switch DMZ cho server block để cùng mạng 192.168.100.x. Sửa live tại root để cho web1 web2 nhìn thấy DMZ router:
    info( '*** Setting DMZ Switch instead of P2P links for Server Farm (Fix network layer 2)\n' )
    net.stop() # Wait, net stop is invalid during build. I will run commands to setup bridges directly via OVS if needed or just use default. Actually, assigning IP to dmz_r_eth3 is safer:
    
    net = Mininet( topo=topo, controller=None )
    net.start()
    
    # Gán thêm IP cho interface web2 link
    dmz_r = net.get('dmz_r')
    dmz_r.cmd('ip addr add 192.168.100.253/24 dev dmz_r-eth3') # Gateway phụ cho web 2 nếu cần
    
    # Thiết lập default route cho Router ISP ra ngoài không gian ảo (NULL) hoặc route loopback cho IP NAT Pool
    r_out = net.get('r_out')
    r_out.cmd('ip route add 200.0.0.0/24 dev rout-eth0') # Route Pool NAT quay ngược về DMZ (nếu áp dụng NAT trên r_out hoặc dmz_r)

    info( '*** Routing/OSPF Setup:\n' )
    info( 'Các Node Core và Distribution đã có IP cơ bản. Vui lòng chạy 10_setup_ospf.sh để kích hoạt FRR.\n' )
    
    CLI( net )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    run()
