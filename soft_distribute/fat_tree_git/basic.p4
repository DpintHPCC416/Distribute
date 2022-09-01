#include <core.p4>
#include <v1model.p4>
#define ETHERTYPE_IPV4 0x0800
#define IP_PROTOCOLS_UDP 17
#define DECIDER_HASH_UPBOUND 999
#define GLOBAL_HASH_UPBOUND 65535
#define QUERY_NUMBER 4
#define BATCH_NUMBER 5
#define FLOW_ID_UPBOUND 65535

header ethernet_h
{
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}


header ipv4_h
{
    bit<4> version;
    bit<4> ihl;
    bit<6> dscp;
    bit<2> ecn;
    bit<16> totalLen;
    bit<16> identification;
    bit<3> flags;
    bit<13> fragOffset;
    bit<8> ttl;
    bit<8> protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
}

header udp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<16> hdr_length;
    bit<16> checksum;
    bit<64> result;
}

struct headers
{
    ethernet_h ethernet;
    ipv4_h ipv4;
    udp_h udp;
}
 

struct distribute_metadata_t{
    bit<32> out_port;
    bit<48> approximation;
    bit<32> hash_value1;
    bit<32> hash_value2;
    bit<32> register_index1;
    bit<32> register_index2;
    bit<1> is_hit1;
    bit<1> is_hit2;

}

parser IngressParser(packet_in pkt,
                    out headers hdr,
                    inout distribute_metadata_t distribute_meta,
                    inout standard_metadata_t standard_metadata
)
{
    state start{
        transition parse_ethernet;
    }
    
    state parse_ethernet
    {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType)
        {
            ETHERTYPE_IPV4: parse_ipv4;
            _:accept;
        }
    }

    state parse_ipv4
    {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol)
        {
            IP_PROTOCOLS_UDP: parse_udp;
            _:accept;
        }
    }

    state parse_udp
    {
        pkt.extract(hdr.udp);
        transition accept;
    }
}

control MyVerifyChecksum(inout headers hdr, inout distribute_metadata_t distribute_meta) {
    apply {  }
}



control MyIngress(inout headers hdr, inout distribute_metadata_t distribute_meta, inout standard_metadata_t standard_metadata)
{
    
    
    action drop() {
        mark_to_drop(standard_metadata);
    }
    
    action forward(bit<48> dstAddr ,bit<9> port)
    {
        hdr.ipv4.ecn = 1;
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table tbl_forward
    {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = 
        {
            forward;
            drop;
            NoAction;
        }
        default_action = drop();
    }

    apply
    {   
        tbl_forward.apply();
    }
}




control MyComputeChecksum(inout headers  hdr, inout distribute_metadata_t distribute_meta) {
     apply {
    update_checksum(
        hdr.ipv4.isValid(),
            { hdr.ipv4.version,
          hdr.ipv4.ihl,
              hdr.ipv4.dscp,
              hdr.ipv4.ecn,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

control MyDeparser(packet_out pkt, in headers hdr)
{
    apply{
        pkt.emit(hdr.ethernet);
        pkt.emit(hdr.ipv4);
        pkt.emit(hdr.udp);
    }
    
}



control MyEgress(inout headers hdr, inout distribute_metadata_t distribute_meta, inout standard_metadata_t standard_metadata)
{
    
    action hit_bucket1(bit<32> first,bit<32> weight,bit<8> index)
    {

	bit<32> molecule = distribute_meta.hash_value1 - first - 1;
	bit<32> temp_value1 = molecule * weight;
	temp_value1 = temp_value1 >> index;
        distribute_meta.register_index1 = temp_value1 + 1;
        distribute_meta.is_hit1 = 1;
    }
    action miss_bucket1()
    {
        distribute_meta.is_hit1 = 0;
    }

    table update_SSC1
    {
        key = 
        {
	    hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
            distribute_meta.hash_value1: range;
        }
        actions =
        {
            hit_bucket1;
            miss_bucket1;
        }
        default_action = miss_bucket1();
    }

    action hit_bucket2(bit<32> first,bit<32> weight,bit<8> index)
    {

		bit<32> molecule = distribute_meta.hash_value2 - first - 1;
		bit<32> temp_value1 = molecule * weight;
		temp_value1 = temp_value1 >> index;
        distribute_meta.register_index2 = temp_value1 + 1;
        distribute_meta.is_hit2 = 1;

    }
    action miss_bucket2()
    {
        distribute_meta.is_hit2 = 0;
    }

    table update_SSC2
    {
        key = 
        {
            hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
            distribute_meta.hash_value2: range;
        }
        actions =
        {
            hit_bucket2;
            miss_bucket2;
        }
        default_action = miss_bucket2();
    }




    register <bit<32>> (65535) register_bucket1;
    register <bit<32>> (65535) register_bucket2;


    // register <bit<48>> (65535) global_timestamp_reg;     //last global timestamp  //because every flow need to update a timestamp when each packet arrives
    // register <bit<32>> (65535) flow_packet_number;     //packet number of a flow

    apply
    {
        hash(distribute_meta.hash_value1, HashAlgorithm.crc32, (bit<1>)0, {hdr.ipv4.srcAddr,hdr.ipv4.dstAddr,hdr.udp.src_port,hdr.udp.dst_port,hdr.ipv4.protocol},(bit<48>)FLOW_ID_UPBOUND);
        hash(distribute_meta.hash_value2, HashAlgorithm.crc16, (bit<1>)0, {hdr.ipv4.srcAddr,hdr.ipv4.dstAddr,hdr.udp.src_port,hdr.udp.dst_port,hdr.ipv4.protocol},(bit<48>)FLOW_ID_UPBOUND);
        
        
        update_SSC1.apply();
        update_SSC2.apply();
        if(distribute_meta.is_hit1 == 1){
            bit<32> register_value;
            register_bucket1.read(register_value,distribute_meta.register_index1);
            register_value = register_value + 1;
            register_bucket1.write(distribute_meta.register_index1,register_value);
            hdr.udp.result[63:32] = register_value;
        }

        if(distribute_meta.is_hit2 == 1){
            bit<32> register_value;
            register_bucket2.read(register_value,distribute_meta.register_index2);
            register_value = register_value + 1;
            register_bucket2.write(distribute_meta.register_index2,register_value);
            hdr.udp.result[31:0] = register_value;
        }



    }
}

V1Switch(
    IngressParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
)main;

