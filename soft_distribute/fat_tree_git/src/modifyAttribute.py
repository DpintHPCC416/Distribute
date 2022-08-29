import copy
import json
topo_path = "../topo"
#switch1 and switch2 both are in form of si-pj
def findlink(switch1, switch2, links):
    for i in range(0, len(links)):
        link = links[i]
        if (link[0] == switch1 and link[1] == switch2) or (link[0] == switch2 and link[1] == switch1):
            return i
    return None

def modifyLinksAttribute():
    modifyLinks = [['s1-p3', 's3-p1',{'delay':'10ms'}],
                   ['s7-p3', 's19-p1',{'delay':'10ms'}],
                   ['s10-p1', 's9-p2', {'delay':'10ms'}],
                   ['s16-p3', 's14-p2', {'loss': 20}],
                   ['s11-p2', 's18-p2', {'loss': 15}]
                  ]

    path = topo_path + "/topo.json"
    topo = json.load(open(path))

    #modify link to satisfy congestion and blackhole
    for link in modifyLinks:
        index = findlink(link[0], link[1], topo['links'])
        if index == None:
            print 'can not find %s - %s' % (link[0], link[1])
        else:
            topo['links'][index].append(link[2])
    with open(path, 'w') as f:
        json.dump(topo, f, indent=4)

def modifyPortImbalance():
    #modify forwarding table to make port imbalance
    portImbalanceSwitches = ['s1', 's4']
    directAccessSw =  [['10.0.1.2', '10.0.1.3'], ['10.1.0.2','10.1.0.3']]
    swInSamePod = [['10.0.0.2', '10.0.0.3'], ['10.1.1.2', '10.1.1.3']]
    for i in range(0, len(portImbalanceSwitches)):
        switch = portImbalanceSwitches[i]
        path = topo_path + '/%s-runtime.json' % (switch)
        flow_tables = json.load(open(path))
        for entry in flow_tables['table_entries']:
            if entry['action_name'] == "DpintIngress.forward":
                if entry['match']['hdr.ipv4.dstAddr'][0] not in directAccessSw[i]:
                    if entry['match']['hdr.ipv4.dstAddr'][0] in swInSamePod[i]:
                        entry['action_params']['port'] = 2
                    else:
                        entry['action_params']['port'] = 3
        with open(path, 'w') as f:
            json.dump(flow_tables, f, indent=4)

def modifyLoop():
    switches = ['s15']
    destes = [['10.0.0.3', '10.1.1.3']] #h1 h7

    switch = switches[0]
    dest = destes[0]
    params = []
    path = topo_path + '/%s-runtime.json' % (switch)
    flow_tables = json.load(open(path))
    for entry in flow_tables['table_entries']:
        if entry['action_name'] == "DpintIngress.forward":
            if entry['match']['hdr.ipv4.dstAddr'][0] in dest:
                params.append(entry['action_params'])
                entry['action_params'] = {}
                entry['action_name'] = 'DpintIngress.goto_tbl_check_inport'
    flow_tables['table_entries'].append({
        "table": "DpintIngress.tbl_check_inport",
        "action_params": {'dstAddr': '08:10:03:01:01:03', 'port': 1},
        "match": {
            "standard_metadata.ingress_port": 0
        },
        "action_name": "DpintIngress.forward"
    })

    flow_tables['table_entries'].append({
        "table": "DpintIngress.tbl_check_inport",
        "action_params": params[0],
        "match": {
            "standard_metadata.ingress_port": 1
        },
        "action_name": "DpintIngress.forward"
    })
    with open(path, 'w') as f:
        json.dump(flow_tables, f, indent=4)

    #modify s13
    path = topo_path + '/%s-runtime.json' % ('s13')
    flow_tables = json.load(open(path))
    param = None
    for entry in flow_tables['table_entries']:
        if entry['action_name'] == "DpintIngress.forward":
            if entry['match']['hdr.ipv4.dstAddr'][0] in dest:
                param = entry['action_params']
                entry['action_params'] = {}
                entry['action_name'] = 'DpintIngress.goto_tbl_check_inport'
    flow_tables['table_entries'].append({
        "table": "DpintIngress.tbl_check_inport",
        "action_params": {'dstAddr': '08:10:03:03:01:01', 'port': 3},
        "match": {
            "standard_metadata.ingress_port": 3
        },
        "action_name": "DpintIngress.forward"
    })

    flow_tables['table_entries'].append({
        "table": "DpintIngress.tbl_check_inport",
        "action_params": param,
        "match": {
            "standard_metadata.ingress_port": 0
        },
        "action_name": "DpintIngress.forward"
    })

    flow_tables['table_entries'].append({
        "table": "DpintIngress.tbl_check_inport",
        "action_params": param,
        "match": {
            "standard_metadata.ingress_port": 1
        },
        "action_name": "DpintIngress.forward"
    })

    with open(path, 'w') as f:
        json.dump(flow_tables, f, indent=4)