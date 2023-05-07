//tcp version

#include <core.p4>
#if __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif

#include "common/headers.p4"
#include "common/util.p4"

#define FLOW_ID_UPBOUND 65535
//means sketch_w is 2^(10-1)
#define SWITCH_SIZE 10

struct metadata_t { 
    bit<16> hash_value1;
    bit<16> hash_value2;
    bit<16> index1;
    bit<16> index2;
    bit<1>  hit_flag;
    bit<32> result;
}




// ---------------------------------------------------------------------------
// Ingress parser
// ---------------------------------------------------------------------------
parser SwitchIngressParser(
        packet_in pkt,
        out header_t hdr,
        out metadata_t distribute_meta,
        out ingress_intrinsic_metadata_t ig_intr_md) {

    TofinoIngressParser() tofino_parser;

    state start {
        tofino_parser.apply(pkt, ig_intr_md);
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4 : parse_ipv4;
            default : accept;
        }
    }


    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            6 : parse_tcp;
            default : reject;
        }
    }

    state parse_tcp {
        pkt.extract(hdr.tcp);
        transition accept;
    }
}

// ---------------------------------------------------------------------------
// Ingress Deparser
// ---------------------------------------------------------------------------

control SwitchIngressDeparser(
        packet_out pkt,
        inout header_t hdr,
        in metadata_t distribute_meta,
        in ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md) {

    apply {
        pkt.emit(hdr);
    }
}

control SwitchIngress(
        inout header_t hdr,
        //inout metadata_t ig_md,
        inout metadata_t distribute_meta,
        in ingress_intrinsic_metadata_t ig_intr_md,
        in ingress_intrinsic_metadata_from_parser_t ig_prsr_md,
        inout ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md,
        inout ingress_intrinsic_metadata_for_tm_t ig_tm_md
        ) {

// ---------------------------------------------------------------------------
// use 5-tuple to hash
// ---------------------------------------------------------------------------
    // Define a custom hash func with CRC polynomial parameters of crc32.
    // crc32 is available in Python and therefore a good candidate for testing.
    CRCPolynomial<bit<32>>(32w0x04C11DB7, // polynomial
                           true,          // reversed
                           false,         // use msb?
                           false,         // extended?
                           32w0xFFFFFFFF, // initial shift register value
                           32w0xFFFFFFFF  // result xor
                           ) poly1;
    Hash<bit<32>>(HashAlgorithm_t.CUSTOM, poly1) hash_func1;

    CRCPolynomial<bit<32>>(32w0x04C11111, 
                           false, 
                           false, 
                           false, 
                           32w0xFFFFFFFF,
                           32w0xFFFFFFFF
                           ) poly2;
    Hash<bit<32>>(HashAlgorithm_t.CUSTOM, poly2) hash_func2;


    action apply_hash(){

        distribute_meta.index1 = (FLOW_ID_UPBOUND - distribute_meta.hash_value1);
        distribute_meta.index2 = (FLOW_ID_UPBOUND - distribute_meta.hash_value2);

    }
    table table_hash{
        actions = {
            apply_hash;
        }
        const default_action = apply_hash;
        size = 1024;
    }



// ---------------------------------------------------------------------------
// range match
// ---------------------------------------------------------------------------

    Register<bit<32>, bit<SWITCH_SIZE>>(size=1<<(SWITCH_SIZE)) register_table1;
    RegisterAction<bit<32>,bit<SWITCH_SIZE>,bit<32>>(register_table1) register_table1_action = {
        void apply(inout bit<32> value , out bit<32> result){
            value = value + 1;
            result = value;
            
            //distribute_meta.result = value;
        }
    };

    action hit_range1(bit<SWITCH_SIZE> idx){
        // ---------------------------------------------------------------------------
        // register
        // ---------------------------------------------------------------------------
        register_table1_action.execute(distribute_meta.index1[15:6]);
    }
    action miss_range1(){
        
    }
    table range_match1 {
        key = {
            hdr.ipv4.src_addr : exact;
            hdr.ipv4.dst_addr : exact;
            distribute_meta.hash_value1 : range;
        }
        actions = {
            hit_range1;
            miss_range1;
        }
        size = 1024;
    }


    Register<bit<32>, bit<SWITCH_SIZE>>(size=1<<(SWITCH_SIZE)) register_table2;
    RegisterAction<bit<32>,bit<SWITCH_SIZE>,bit<32>>(register_table2) register_table2_action = {
        void apply(inout bit<32> value , out bit<32> result){
            value = value + 1;
            result = value;
            
            //distribute_meta.result = value;
        }
    };

    action hit_range2(bit<SWITCH_SIZE> idx){
        // ---------------------------------------------------------------------------
        // register
        // ---------------------------------------------------------------------------
        register_table2_action.execute(distribute_meta.index2[15:6]);

    }
    action miss_range2(){
        
    }
    table range_match2 {
        key = {
            hdr.ipv4.src_addr : exact;
            hdr.ipv4.dst_addr : exact;
            distribute_meta.hash_value2 : range;
        }
        actions = {
            hit_range2;
            miss_range2;
        }
        size = 1024;
    }


    action forward(PortId_t port){
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        ig_tm_md.ucast_egress_port = port;

    }
    action drop(){
        ig_dprsr_md.drop_ctl = 0x1;
    }
    table table_forward{
        key = {
            hdr.ipv4.dst_addr : exact;
        }

        actions = {
            forward;
            drop;
        }
        const default_action = forward(140);
        size = 1024;
    }




// ---------------------------------------------------------------------------
// apply
// ---------------------------------------------------------------------------


    apply{
        distribute_meta.hash_value1 = hash_func1.get({hdr.ipv4.dst_addr,
        hdr.ipv4.src_addr,
        hdr.tcp.dst_port,
        hdr.tcp.src_port,
        hdr.ipv4.protocol })[15:0];

        distribute_meta.hash_value2 = hash_func2.get({hdr.ipv4.dst_addr,
        hdr.ipv4.src_addr,
        hdr.tcp.dst_port,
        hdr.tcp.src_port,
        hdr.ipv4.protocol })[15:0];
        
        
        table_hash.apply();

        range_match1.apply();
        range_match2.apply();

        table_forward.apply();
        ig_tm_md.bypass_egress = 1w1;


    }



}


// ---------------------------------------------------------------------------
// Apply
// ---------------------------------------------------------------------------


Pipeline(SwitchIngressParser(),
       SwitchIngress(),
       SwitchIngressDeparser(),
       EmptyEgressParser(),
       EmptyEgress(),
       EmptyEgressDeparser()) pipe;

Switch(pipe) main;

