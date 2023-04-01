import logging
import random
import struct
import sys
import os
sys.path.append(os.path.expandvars('$SDE/install/lib/python3.8/site-packages/tofino/'))
sys.path.append(os.path.expandvars('$SDE/install/lib/python3.8/site-packages/p4testutils/'))
sys.path.append(os.path.expandvars('$SDE/install/lib/python3.8/site-packages/bf-ptf/'))
from ptf import config
import ptf.testutils as testutils
from bfruntime_client_base_tests import BfRuntimeTest
from bfrt_grpc import client
GRPC_CLIENT=client.ClientInterface(grpc_addr="localhost:50052", client_id=0,device_id=0)
bfrt_info=GRPC_CLIENT.bfrt_info_get(p4_name=None)
GRPC_CLIENT.bind_pipeline_config(p4_name=bfrt_info.p4_name)
tables = bfrt_info.table_dict
forward_table = bfrt_info.table_get("SwitchIngress.table_forward")
# forward_table.info.key_field_annotation_add("hdr.ipv4.dst_addr", "ipv4")
target = client.Target(device_id=0, pipe_id=0xFFFF)


p4_program_name = "distribute"

match_table1 = bfrt_info.table_get("SwitchIngress.range_match1")
match_table1.info.key_field_annotation_add("hdr.ipv4.dst_addr", "ipv4")
match_table1.info.key_field_annotation_add("hdr.ipv4.src_addr", "ipv4")
try:
    match_table1.entry_add(
        target,
        [match_table1.make_key([
            client.KeyTuple("hdr.ipv4.src_addr","10.0.0.4"),
            client.KeyTuple("hdr.ipv4.dst_addr","10.0.0.3"),
            client.KeyTuple("distribute_meta.hash_value1",low=1,high=30000)

        ])],
        [match_table1.make_data([
            client.DataTuple("idx",0)],
            action_name = "SwitchIngress.hit_range1")]
    )
    
finally:
    pass

match_table2 = bfrt_info.table_get("SwitchIngress.range_match2")
match_table2.info.key_field_annotation_add("hdr.ipv4.dst_addr", "ipv4")
match_table2.info.key_field_annotation_add("hdr.ipv4.src_addr", "ipv4")
try:
    match_table2.entry_add(
        target,
        [match_table2.make_key([
            client.KeyTuple("hdr.ipv4.src_addr","10.0.0.4"),
            client.KeyTuple("hdr.ipv4.dst_addr","10.0.0.3"),
            client.KeyTuple("distribute_meta.hash_value2",low=1,high=30000)

        ])],
        [match_table2.make_data([
            client.DataTuple("idx",0)],
            action_name = "SwitchIngress.hit_range2")]
    )
    
finally:
    pass
    
    
    
    
    

# table_forward
forward_table = bfrt_info.table_get("SwitchIngress.table_forward")
forward_table.info.key_field_annotation_add("hdr.ipv4.dst_addr", "ipv4")

try:
    forward_table.entry_add(
        target,
        [forward_table.make_key([
            client.KeyTuple("hdr.ipv4.dst_addr","10.0.0.3")

        ])],
        [forward_table.make_data([
            client.DataTuple("port",148)],
            action_name = "forward")]
    )
finally:
    pass

entrys=match_table1.entry_get(target)
for e in entrys:
  for item in e:
    print(str(item))
    
entrys=match_table2.entry_get(target)
for e in entrys:
  for item in e:
    print(str(item))


entrys=forward_table.entry_get(target)
for e in entrys:
  for item in e:
    print(str(item))
