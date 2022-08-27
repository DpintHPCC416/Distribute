import os
import json
import sys

from p4utils.utils.topology import Topology

class TopoAllocator:
	def __init__(self, length):
		self.length = length
		self.b_value = 255
		self.all_switches = set()
		self.all_links = set()
		self.data = {}
		for i in range(0,length):
			self.all_switches.add("s"+str(i))

		for i in range(0,length-1):
			self.all_links.add(("s"+str(i),"s"+str(i+1)))

		self.links = []

	def load_sample(self):
		with open('p4app_sample.json') as json_file:
			self.data = json.load(json_file)

		self.data["pcap_dump"] = True
		self.data["enable_log"] = True
		self.data["topology"]["switches"] = {}
		self.data["topology"]["hosts"] = {}
		self.data["program"] = "p4src/single.p4"
		self.data["switch"] = "simple_switch"
	def generate_topo(self):
		for switch in self.all_switches:
			self.data["topology"]["switches"][switch]={}
			self.data["topology"]["switches"][switch]["cli_input"]="rules/"+switch+"-commands.txt"
			host=switch.replace("s","h")
			self.data["topology"]["hosts"][host]={}
			self.links.append([switch,host])
		for link in self.all_links:
			node_1=link[0]
			node_2=link[1]
			self.links.append([node_1,node_2])


		self.data["topology"]["links"]=self.links

		fw=open("p4app.json","w")
		fw.write(json.dumps(self.data, indent=4))
		fw.close()

length=int(sys.argv[1])

topo = TopoAllocator(length)
topo.load_sample()
topo.generate_topo()
print "Run: sudo p4run --config p4app.json"
