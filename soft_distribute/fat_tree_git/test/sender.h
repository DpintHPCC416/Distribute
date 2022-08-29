#ifndef __SENDER_H_
#define __SENDER_H_

#include <stdlib.h>
#include <stdint.h>

uint8_t SRC_MAC[] = {0xb8, 0x81, 0x98, 0x25, 0xc2, 0xfe};
uint8_t DST_MAC[] = {0x8c, 0x8c, 0xaa, 0x74, 0xea, 0x2c};
char* dest_ip = "10.0.1.2";
char* src_ip = "10.0.0.2";
struct eth_header {
    uint8_t dmac[6];
    uint8_t smac[6];
    uint16_t ethType;
};

struct ipv4_hdr {
	uint8_t  version_ihl;		/**< version and header length */
	uint8_t  type_of_service;	/**< type of service */
	uint16_t total_length;		/**< length of packet */
	uint16_t packet_id;		/**< packet ID */
	uint16_t fragment_offset;	/**< fragmentation offset */
	uint8_t  time_to_live;		/**< time to live */
	uint8_t  next_proto_id;		/**< protocol ID */
	uint16_t hdr_checksum;		/**< header checksum */
	uint32_t src_addr;		/**< source address */
	uint32_t dst_addr;		/**< destination address */
} __attribute__((__packed__));

struct udp_hdr {
	uint16_t src_port;    /**< UDP source port. */
	uint16_t dst_port;    /**< UDP destination port. */
	uint16_t dgram_len;   /**< UDP datagram length */
	uint16_t dgram_cksum; /**< UDP datagram checksum */
	uint16_t result;
} __attribute__((__packed__));

struct dune_header
{

} __attribute__((__packed__));

#endif
