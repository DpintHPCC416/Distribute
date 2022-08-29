from topo import Topo

topo = Topo()
while True:
    line = raw_input("host1 host2: ")
    args = line.split()
    travel_switches, travel_ips = topo.getPath(args[0], args[1], 1)
    print(travel_switches)