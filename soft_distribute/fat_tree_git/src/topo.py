# -*- coding: UTF-8 -*-
import json
topo_path = "../topo"

def getHostPosByIndex( index):
    pod = index // 4  # pod 序号
    subnet = (index % 4) // 2  # subnet序号
    id = (index % 4) % 2  # 在subnet中的序号，从0开始
    return pod, subnet, id

def getHostPosByIP(ip):
    args = ip.split('.')
    pod = args[1]
    subnet = args[2]
    id = str(int(args[3] ) - 2)
    return pod, subnet, id

def getHostIpByIndex( index):
    pod, subnet, id = getHostPosByIndex(index)
    return '10.%d.%d.%d' % (pod, subnet, id + 2)

def getHostMacByIndex( index):
    pod, subnet, id = getHostPosByIndex(index)
    return '08:00:10:%02d:%02d:%02d' % (pod, subnet, id + 2)


def getHostGwIpByIndex( index):
    pod, subnet, id = getHostPosByIndex(index)
    return '10.%d.%d.%d' % (pod, subnet, id + 10)


def getHostGwMacByIndex( index):
    pod, subnet, id = getHostPosByIndex(index)
    return '08:00:10:%02d:%02d:%02d' % (pod, subnet, id + 10)


# 以下的index均为 aggregation 或者 edge 的序号，即0-15
def getPodSwitchPosByIndex(index):
    pod = index // 4
    subnet = index % 4
    return pod, subnet


def getPodSwitchIpByIndex( index):
    pod, subnet = getPodSwitchPosByIndex(index)
    return '10.%d.%d.1' % (pod, subnet)


def getPodSwitchPortMacByIndex( index, port):
    pod, subnet = getPodSwitchPosByIndex(index)
    return '08:10:%02d:%02d:01:%02d' % (pod, subnet, port)


def getCoreSwitchPosByIndex(index):
    mod_after_index = index % 16
    index1 = mod_after_index // 2 + 1
    index2 = mod_after_index % 2 + 1
    return index1, index2


def getCoreSwitchIpByIndex( index):
    index1, index2 = getCoreSwitchPosByIndex(index)
    return '10.4.%d.%d' % (index1, index2)


def getCoreSwitchPortMacByIndex( index, port):
    index1, index2 = getCoreSwitchPosByIndex(index)
    return '08:10:04:%02d:%02d:%02d' % (index1, index2, port)

def getPortId(port, switch):
    return switch.ports.index(port)


def getHostInSameSubNet(index):
    if index % 2 == 0:
        return index + 1
    else:
        return index - 1

class Link():
    def __init__(self):
        self.node1 = None
        self.node2 = None
        self.port1 = None
        self.port2 = None
        self.attribute = None

class Node():
    def __init__(self):
        self.ip = ''
        self.name = ''

class Port():
    def __init__(self):
        self.port_mac = ''

class Switch(Node):
    def __init__(self, index):
        Node.__init__(self)
        self.ports = []
        self.links = [None for i in range(0, 8)]
        self.flow_tables = {}
        if index < 16: #是pod switch
            self.ip = getPodSwitchIpByIndex(index)
            self.name = 's' + str(index)
            for i in range(0, 4):
                port = Port()
                port.port_mac = getPodSwitchPortMacByIndex(index, i)
                self.ports.append(port)
        else:
            self.ip = getCoreSwitchIpByIndex(index)
            self.name = 's' + str(index)
            for i in range(0, 4):
                port = Port()
                port.port_mac = getCoreSwitchPortMacByIndex(index, i)
                self.ports.append(port)
    def _ip2num(self, ip):
        args = ip.split('.')
        sum = 0
        for n in args:
            sum = sum * 256 + int(n)
        return long(sum)

    def match(self, ip, ingress_port):
        for entry in self.flow_tables['table_entries']:
            if entry['table'] == 'MyIngress.tbl_forward':
                match_bits_num = entry['match']["hdr.ipv4.dstAddr"][1]
                match_ip = entry['match']["hdr.ipv4.dstAddr"][0]
                if (self._ip2num(match_ip) >> (32 - match_bits_num)) == (self._ip2num(ip) >> (32 - match_bits_num)):
                    if entry['action_name'] == 'MyIngress.forward':
                        return int(entry['action_params']['port'])
                    elif entry['action_name'] == 'MyIngress.goto_tbl_check_inport':
                        for entry2 in self.flow_tables['table_entries']:
                            if entry2['table'] == 'MyIngress.tbl_check_inport':
                                if int(entry2['match']['standard_metadata.ingress_port']) == ingress_port:
                                    return int(entry2['action_params']['port'])

class Host(Node):
    def __init__(self, index):
        Node.__init__(self)
        self.ip = getHostIpByIndex(index)
        self.mac = getHostMacByIndex(index)
        self.name = 'h' + str(index)
        self.gw_ip = getHostGwIpByIndex(index)
        self.gw_mac = getHostGwMacByIndex(index)
        self.port = Port()
        self.port.port_mac = getHostMacByIndex(index)
        self.link = None


class Topo():
    #以下的index均为host的序号，即0-15
    def __init__(self):
        self.hosts = {}
        self.switches = {}
        self.links = []
        self.initHosts()
        self.initSwitches()
        self.initLinks()
        self.initFlowTable()


    def initHosts(self):
        for i in range(0,16):
            host = Host(i)
            self.hosts[host.name] = host

    def initSwitches(self):
        for i in range(0, 20):
            switch = Switch(i)
            self.switches[switch.name] = switch


    def initLinks(self):
        #初始化host和edge switch之间的link
        for i in range(0, 16):
            node1 = 'h' + str(i)
            pod, subnet, id = getHostPosByIndex(i)
            node2 = 's' + str(pod * 4 + subnet)
            link = Link()
            link.node1 = self.hosts[node1]
            link.node2 = self.switches[node2]
            link.port1 = self.hosts[node1].port
            link.port2 = self.switches[node2].ports[id]
            self.hosts[node1].link = link
            self.switches[node2].links[id] = link
            self.links.append(link)

        #初始化edge和aggregation之间的link
        for i in range(0, 4):
            for j in range(0, 2):
                index = i * 4 + j
                node1 = 's' + str(index)
                for k in range(2, 4):
                    node2 = 's' + str(i * 4 + k)
                    link = Link()
                    link.node1 = self.switches[node1]
                    link.node2 = self.switches[node2]
                    link.port1 = self.switches[node1].ports[k]
                    link.port2 = self.switches[node2].ports[j]
                    self.switches[node1].links[k] = link
                    self.switches[node2].links[j] = link
                    self.links.append(link)

        #初始化aggregation和core之间的link
        for i in range(0, 4):
            for j in range(0, 2):
                index = i * 4 + j + 2
                node1 = 's' + str(index)
                for k in range(0, 2):
                    node2 = 's' + str(16 + j * 2 + k)
                    link = Link()
                    link.node1 = self.switches[node1]
                    link.node2 = self.switches[node2]
                    link.port1 = self.switches[node1].ports[2 + k]
                    link.port2 = self.switches[node2].ports[i]
                    self.switches[node1].links[k + 2] = link
                    self.switches[node2].links[i] = link
                    self.links.append(link)
        #     link.attribute = e[2]
    def initFlowTable(self):
        for i in range(0, 4): # pod i
            for j in range(0, 2): # subnet j
                data = json.load(open('example_flow_table.json'))
                index = i * 4 + j
                node1 = 's' + str(index)
                #初始化发往直连host的流表
                linked_host = []
                cur_switch = self.switches[node1]
                for k in range(0, 2):
                    entry = {"table": "MyIngress.tbl_forward"}
                    link = cur_switch.links[k]
                    host = None
                    switch = None
                    switch_port = 0
                    if isinstance(link.node1, Host):
                        host = link.node1
                        switch = link.node2
                        switch_port = link.port2
                    elif isinstance(link.node2, Host):
                        host = link.node2
                        switch = link.node1
                        switch_port = link.port1
                    else:
                        exit()
                    linked_host.append(host)
                    entry['match'] = {"hdr.ipv4.dstAddr": ['%s' % (host.ip), 32]}
                    entry['action_name'] =  "MyIngress.forward"
                    egress_port_id = getPortId(switch_port, switch)
                    entry["action_params"] = {'dstAddr' : host.mac, 'port' : egress_port_id}
                    data["table_entries"].append(entry)
                for k in range(0, 16):
                    hostName = 'h' + str(k)
                    if self.hosts[hostName] not in linked_host:
                        curHost = self.hosts[hostName]
                        entry = {"table": "MyIngress.tbl_forward"}
                        entry['match'] = {"hdr.ipv4.dstAddr": ['%s' % (curHost.ip), 32]}
                        entry['action_name'] = "MyIngress.forward"
                        pod, subnet, id = getHostPosByIndex(k)
                        egress_port = (id + j) % 2 + 2
                        link = cur_switch.links[egress_port]
                        connected_node_port = None
                        if link.node1 == cur_switch:
                            connected_node_port = link.port2
                        else:
                            connected_node_port = link.port1
                        entry["action_params"] = {'dstAddr': connected_node_port.port_mac, 'port': egress_port}
                        data["table_entries"].append(entry)
                self.switches[node1].flow_tables = data
        #初始化aggregation switch
        for i in range(0, 4): #pod
            for j in range(0, 2):
                data = json.load(open('example_flow_table.json'))
                index = i * 4 + j + 2
                node1 = 's' + str(index)
                cur_switch = self.switches[node1]
                for subnet in range(0, 2):
                    entry = {"table": "MyIngress.tbl_forward"}
                    entry['match'] = {"hdr.ipv4.dstAddr": ['10.%d.%d.0' % (i, subnet), 24]}
                    entry['action_name'] = "MyIngress.forward"
                    egress_port = subnet
                    link = cur_switch.links[egress_port]
                    connected_node_port = None
                    if link.node1 == cur_switch:
                        connected_node_port = link.port2
                    else:
                        connected_node_port = link.port1
                    entry["action_params"] = {'dstAddr': connected_node_port.port_mac, 'port': egress_port}
                    data["table_entries"].append(entry)
                for k in range(0, 16):
                    pod, subnet, id = getHostPosByIndex(k)
                    if pod != i:
                        curHost = self.hosts['h' + str(k)]
                        entry = {"table": "MyIngress.tbl_forward"}
                        entry['match'] = {"hdr.ipv4.dstAddr": ['%s' % (curHost.ip), 32]}
                        entry['action_name'] = "MyIngress.forward"
                        egress_port = (id + j + 2) % 2 + 2
                        link = cur_switch.links[egress_port]
                        connected_node_port = None
                        if link.node1 == cur_switch:
                            connected_node_port = link.port2
                        else:
                            connected_node_port = link.port1
                        entry["action_params"] = {'dstAddr': connected_node_port.port_mac, 'port': egress_port}
                        data["table_entries"].append(entry)
                self.switches[node1].flow_tables = data
        #初始化core switch
        for i in range(0, 4):
            data = json.load(open('example_flow_table.json'))
            index = 16 + i
            node1 = 's' + str(index)
            cur_switch = self.switches[node1]
            for pod in range(0, 4):
                entry = {"table": "MyIngress.tbl_forward"}
                entry['match'] = {"hdr.ipv4.dstAddr": ['10.%d.0.0' % (pod), 16]}
                entry['action_name'] = "MyIngress.forward"
                egress_port = pod
                link = cur_switch.links[egress_port]
                connected_node_port = None
                if link.node1 == cur_switch:
                    connected_node_port = link.port2
                else:
                    connected_node_port = link.port1
                entry["action_params"] = {'dstAddr': connected_node_port.port_mac, 'port': egress_port}
                data["table_entries"].append(entry)
            self.switches[node1].flow_tables = data
        


###########################################################################
# ############# write your entries here ###################################
# #########################################################################
# #########################################################################
# ############# this is a example from h0 to h2  ##########################
# 
#       
        # s0
        switch = self.switches["s0"]
        temp_dict = {}
        temp_dict["table"] = "MyEgress.update_SSC1"
        temp_dict["priority"] = 1
        para_dict = {}
        para_dict["first"] = 0
        para_dict["weight"] = 1
        para_dict["index"] = 4
        temp_dict["action_params"] = para_dict
        match_dict = {}
        match_dict["hdr.ipv4.srcAddr"] = "10.0.0.2"
        match_dict["hdr.ipv4.dstAddr"] = "10.0.1.2"
        match_dict["distribute_meta.hash_value1"] = (0,16383)
        temp_dict["match"] = match_dict
        temp_dict["action_name"] = "MyEgress.hit_bucket1"
        
        switch.flow_tables['table_entries'].append(temp_dict)

        switch = self.switches["s0"]
        temp_dict = {}
        temp_dict["table"] = "MyEgress.update_SSC2"
        temp_dict["priority"] = 1
        para_dict = {}
        para_dict["first"] = 0
        para_dict["weight"] = 1
        para_dict["index"] = 4
        temp_dict["action_params"] = para_dict
        match_dict = {}
        match_dict["hdr.ipv4.srcAddr"] = "10.0.0.2"
        match_dict["hdr.ipv4.dstAddr"] = "10.0.1.2"
        match_dict["distribute_meta.hash_value2"] = (0,16383)
        temp_dict["match"] = match_dict
        temp_dict["action_name"] = "MyEgress.hit_bucket2"
        switch.flow_tables['table_entries'].append(temp_dict)
        # s3
        
        switch = self.switches["s3"]
        temp_dict = {}
        temp_dict["table"] = "MyEgress.update_SSC1"
        temp_dict["priority"] = 1
        para_dict = {}
        para_dict["first"] = 16384
        para_dict["weight"] = 1
        para_dict["index"] = 4
        temp_dict["action_params"] = para_dict
        match_dict = {}
        match_dict["hdr.ipv4.srcAddr"] = "10.0.0.2"
        match_dict["hdr.ipv4.dstAddr"] = "10.0.1.2"
        match_dict["distribute_meta.hash_value1"] = (16374,49151)
        temp_dict["match"] = match_dict
        temp_dict["action_name"] = "MyEgress.hit_bucket1"
        switch.flow_tables['table_entries'].append(temp_dict)

        switch = self.switches["s3"]
        temp_dict = {}
        temp_dict["table"] = "MyEgress.update_SSC2"
        temp_dict["priority"] = 1
        para_dict = {}
        para_dict["first"] = 16384
        para_dict["weight"] = 1
        para_dict["index"] = 4
        temp_dict["action_params"] = para_dict
        match_dict = {}
        match_dict["hdr.ipv4.srcAddr"] = "10.0.0.2"
        match_dict["hdr.ipv4.dstAddr"] = "10.0.1.2"
        match_dict["distribute_meta.hash_value2"] = (16374,49151)
        temp_dict["match"] = match_dict
        temp_dict["action_name"] = "MyEgress.hit_bucket2"
        switch.flow_tables['table_entries'].append(temp_dict)


        # s1

        switch = self.switches["s1"]
        temp_dict = {}
        temp_dict["table"] = "MyEgress.update_SSC1"
        temp_dict["priority"] = 1
        para_dict = {}
        para_dict["first"] = 49152
        para_dict["weight"] = 1
        para_dict["index"] = 4
        temp_dict["action_params"] = para_dict
        match_dict = {}
        match_dict["hdr.ipv4.srcAddr"] = "10.0.0.2"
        match_dict["hdr.ipv4.dstAddr"] = "10.0.1.2"
        match_dict["distribute_meta.hash_value1"] = (49152,65535)
        temp_dict["match"] = match_dict
        temp_dict["action_name"] = "MyEgress.hit_bucket1"
        switch.flow_tables['table_entries'].append(temp_dict)

        switch = self.switches["s1"]
        temp_dict = {}
        temp_dict["table"] = "MyEgress.update_SSC2"
        temp_dict["priority"] = 1
        para_dict = {}
        para_dict["first"] = 49152
        para_dict["weight"] = 1
        para_dict["index"] = 4
        temp_dict["action_params"] = para_dict
        match_dict = {}
        match_dict["hdr.ipv4.srcAddr"] = "10.0.0.2"
        match_dict["hdr.ipv4.dstAddr"] = "10.0.1.2"
        match_dict["distribute_meta.hash_value2"] = (49152,65535)
        temp_dict["match"] = match_dict
        temp_dict["action_name"] = "MyEgress.hit_bucket2"
        switch.flow_tables['table_entries'].append(temp_dict)


    def generateTopo(self):
        data = json.load(open('example.json'))
        data_links = data['links']
        data_hosts = data['hosts']
        data_switches = data['switches']
        for i in range(0, 16):
            host_name = 'h' + str(i)
            host = self.hosts.get(host_name)
            command = []
            command.append('route add default gw %s dev eth0' % (host.gw_ip))
            command.append('arp -i eth0 -s %s %s' % (host.gw_ip, host.gw_mac))
            host_in_same_net = self.hosts['h' + str(getHostInSameSubNet(i))]
            command.append('arp -i eth0 -s %s %s' % (host_in_same_net.ip, host_in_same_net.mac))
            entry = {'ip' : '%s/24' % (host.ip), 'mac' : host.mac, 'commands' : command}
            data_hosts[host.name] = entry
        for switch_name in self.switches.keys():
            switch = self.switches.get(switch_name)
            data_switches[switch.name] = {'runtime_json' : 'topo/%s-runtime.json' % (switch.name)}
        for link in self.links:
            entry = []
            if isinstance(link.node1, Host):
                entry.append(link.node1.name)
            elif isinstance(link.node1, Switch):
                port_id = getPortId(link.port1, link.node1)
                entry.append('%s-p%d' % (link.node1.name, port_id ))
            if isinstance(link.node2, Host):
                entry.append(link.node2.name)
            elif isinstance(link.node2, Switch):
                port_id = getPortId(link.port2, link.node2)
                entry.append('%s-p%d' % (link.node2.name, port_id))
            if link.attribute != None:
                entry.append(link.attribute)
            data_links.append(entry)
        with open('../topo/topo.json', 'w') as f:
            json.dump(data, f, indent=4)
    def generateRuntime(self):
        for switch in self.switches:
            path = '../topo/%s-runtime.json' % (switch)
            with open(path, 'w') as f:
                json.dump(self.switches[switch].flow_tables, f, indent=4)


    def getPath(self, host1, host2, opt):
        src = {}
        dst = {}
        if opt == 0:
            pod, subnet, id = getHostPosByIP(host1)
            host1_name = 'h' + (pod * 4 + subnet * 2 + id)
            pod, subnet, id = getHostPosByIP(host2)
            host2_name = 'h' + (pod * 4 + subnet * 2 + id)
            src = {'name': host1_name, 'ip': host1}
            dst = {'name': host2_name, 'ip': host2}
        elif opt == 1:
            host1_index = int(host1[1:])
            host2_index = int(host2[1:])
            host1_ip = getHostIpByIndex(host1_index)
            host2_ip = getHostIpByIndex(host2_index)
            src = {'name': host1, 'ip': host1_ip}
            dst = {'name': host2, 'ip': host2_ip}
        travel_switches = []
        travel_ips = []
        cur_hop = self.hosts[src['name']]
        ingress_port = 0
        while cur_hop.name != dst['name']:
            if isinstance(cur_hop, Host):
                link = cur_hop.link
            else:
                egress_port = cur_hop.match(dst['ip'], ingress_port)
                link = cur_hop.links[egress_port]

            if link.node2.name != cur_hop.name:
                cur_hop = link.node2
                if isinstance(cur_hop, Switch):
                    ingress_port = getPortId(link.port2, link.node2)
            else:
                cur_hop = link.node1
                if isinstance(cur_hop, Switch):
                    ingress_port = getPortId(link.port1, link.node1)
            if isinstance(cur_hop, Switch):
                travel_switches.append(cur_hop.name)
                travel_ips.append(cur_hop.ip)
        return travel_switches, travel_ips


if __name__ == '__main__':
    topo = Topo()
    topo.generateTopo()
    topo.generateRuntime()
    # #modifyAttribute()
    # while True:
    #     line = raw_input("host1 host2: ")
    #     args = line.split()
    #     travel_switches, travel_ips = topo.getPath(args[0], args[1], 1)
    #     print(travel_switches)
