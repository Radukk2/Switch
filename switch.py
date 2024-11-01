#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
import os
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name


my_mac_table = {}
my_configs = {}
interfaces_state = {}
is_root = True

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def create_bdpu(bridge_id, root_bridge_id, src_mac, path_cost):
    bpdu_packet = struct.pack("!6s6sIII", b"\x01\x80\xC2\x00\x00\x00", src_mac, bridge_id, path_cost, root_bridge_id)
    return bpdu_packet

def send_bdpu_every_sec(interfaces, my_bridge_id, root_bridge_id, switch_priority, src_mac):
    while True:
        # print(f"[DEBUG] Current root: {is_root} on switch {my_bridge_id}")
        if is_root:
            for i in interfaces :
                if my_configs[get_interface_name(i)] == 'T':
                    bdpu_pack = create_bdpu(switch_priority, my_bridge_id, src_mac, 0)
                    send_to_link(i, len(bdpu_pack), bdpu_pack)
                    # print(f"[DEBUG] Sent BPDU from root {my_bridge_id} on interface {i}")
        time.sleep(1)

def is_unicast_address(mac):
    return (mac[0] % 2 == 0)


def read_configs(file_path):
    priority = None
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            parts = line.split()
            if len(parts) == 1:
                priority = int(parts[0])
            else :
                my_configs[parts[0]] = parts[1]
    return priority
    
def fwd(dest_iface, length, data, vlan_id, switch_id, src_iface):
    # print(my_configs)
    name = get_interface_name(dest_iface)
    # print(vlan_id)
    if name in my_configs and my_configs[name] ==  'T':
        if my_configs[get_interface_name(src_iface)] != 'T':
            data = data[0:12] + create_vlan_tag(vlan_id) + data[12:]
            length += 4
        if  interfaces_state[get_interface_name(dest_iface)] != 'blocking':
            send_to_link(dest_iface, length, data) 
    else:
        # print(vlan_id)
        # print("vlan")
        # print(my_configs[name])
        if  vlan_id == int(my_configs[name]):
            if my_configs[get_interface_name(src_iface)] == 'T':
                data = data[0:12] + data[16:]
                length -= 4
            if interfaces_state[get_interface_name(dest_iface)] != 'blocking':
                send_to_link(dest_iface, length, data)

def on_bdpu_receive(root_bridge_id, root_path_cost, iface, interfaces, my_bridge_id, data):

    global is_root
    global interfaces_state
    format = "!6s6sIII"
    dest_mac, src_mac, bridge_id, path_cost, recv_root_bridge_id = struct.unpack(format, data)
    root_port = None

    print(f"[DEBUG] Received BPDU on iface {iface} - Root ID: {recv_root_bridge_id}, Path Cost: {path_cost}")

    #step 1
    if recv_root_bridge_id < root_bridge_id :
        root_path_cost = path_cost + 10
        root_port = iface

    #step2
        if is_root:
            for i in interfaces:
                if my_configs[get_interface_name(i)] == 'T' and i != iface :
                    interfaces_state[get_interface_name(i)] = 'blocking'
            is_root = False
        
    #step3    
        if interfaces_state[get_interface_name(root_port)] == 'blocking' :
            interfaces_state[get_interface_name(root_port)] = 'listening'
        for i in interfaces :
            if my_configs[get_interface_name(i)] == 'T' :
                sender_bridge_ID = my_bridge_id
                sender_path_cost = root_path_cost
                send_new = create_bdpu(sender_bridge_ID, recv_root_bridge_id, get_switch_mac(), sender_path_cost)
                send_to_link(i, len(send_new), send_new)
    elif recv_root_bridge_id == root_bridge_id :
        if root_port == iface and path_cost + 10 < root_path_cost :
            root_path_cost = path_cost + 10
        elif root_port != iface :
            if path_cost > root_path_cost :
                if interfaces_state[get_interface_name(iface)] != 'listening':
                    interfaces_state[get_interface_name(iface)] = 'listening'
    elif bridge_id == my_bridge_id :
        interfaces_state[get_interface_name(iface)] = 'blocking'
    if my_bridge_id == root_bridge_id :
        for i in interfaces :
            interfaces_state[get_interface_name(i)] = 'listening'

        

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]
    switch_priority = read_configs(os.path.join('configs', f'switch{switch_id}.cfg'))
    # print(my_configs)
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)
    



    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    # Create and start a new thread that deals with sending BDPU

    # Setting up STP
    for i in interfaces:
        if my_configs[get_interface_name(i)] == 'T':
            interfaces_state[get_interface_name(i)] = 'blocking'
        else :
            interfaces_state[get_interface_name(i)] = 'listening'
        # print(get_interface_name(i), ": ", interfaces_state[get_interface_name(i)])

    my_bridge_id = switch_priority
    root_bridge_id = my_bridge_id
    root_path_cost = 0

    pack = create_bdpu(my_bridge_id, root_bridge_id, get_switch_mac(), root_path_cost)
    if my_bridge_id == root_bridge_id:
        for i in interfaces:
            send_to_link(i, len(pack), pack)
    
    t = threading.Thread(target=send_bdpu_every_sec, args=(interfaces, my_bridge_id, root_bridge_id, switch_priority, get_switch_mac()))
    t.start()

    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)
        if vlan_id == -1 and my_configs[get_interface_name(interface)] != 'T':
            vlan_id = int(my_configs[get_interface_name(interface)])

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # TODO: Implement forwarding with learning
        # TODO: Implement VLAN support
        my_mac_table[src_mac] = interface
        # print(my_configs)
        if dest_mac == "01:80:c2:00:00:00" :
            on_bdpu_receive(root_bridge_id, root_path_cost, interface, interfaces, my_bridge_id, data)
            continue
        if dest_mac in my_mac_table :
            fwd(my_mac_table[dest_mac], length, data , vlan_id, switch_id, interface)
        else:
            for i in interfaces:
                if i != interface:
                    fwd(i, length, data, vlan_id, switch_id, interface)
        
        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
