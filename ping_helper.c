/*
 * Copyright 2025 icecake0141
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * This file was created or modified with the assistance of an AI (Large Language Model).
 * Review required for correctness, security, and licensing.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/ip_icmp.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <sys/time.h>
#include <errno.h>

#define PACKET_SIZE 64
#define ICMP_HEADER_SIZE 8

/* Calculate ICMP checksum */
unsigned short checksum(void *b, int len) {
    unsigned short *buf = b;
    unsigned int sum = 0;
    unsigned short result;

    for (sum = 0; len > 1; len -= 2) {
        sum += *buf++;
    }
    if (len == 1) {
        sum += (*(unsigned char *)buf) << 8;
    }
    sum = (sum >> 16) + (sum & 0xFFFF);
    sum += (sum >> 16);
    result = ~sum;
    return result;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <host> <timeout_ms>\n", argv[0]);
        return 1;
    }

    const char *host = argv[1];
    int timeout_ms = atoi(argv[2]);
    
    if (timeout_ms <= 0) {
        fprintf(stderr, "Error: timeout_ms must be positive\n");
        return 2;
    }

    /* Resolve hostname */
    struct addrinfo hints, *res;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_RAW;
    hints.ai_protocol = IPPROTO_ICMP;

    int status = getaddrinfo(host, NULL, &hints, &res);
    if (status != 0) {
        fprintf(stderr, "Error: cannot resolve host %s: %s\n", host, gai_strerror(status));
        return 3;
    }

    /* Create raw socket */
    int sockfd = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (sockfd < 0) {
        fprintf(stderr, "Error: cannot create raw socket: %s\n", strerror(errno));
        fprintf(stderr, "Note: This program requires cap_net_raw capability or root privileges\n");
        freeaddrinfo(res);
        return 4;
    }

    /* Prepare ICMP echo request */
    char packet[PACKET_SIZE];
    memset(packet, 0, PACKET_SIZE);
    
    struct icmp *icmp_hdr = (struct icmp *)packet;
    icmp_hdr->icmp_type = ICMP_ECHO;
    icmp_hdr->icmp_code = 0;
    icmp_hdr->icmp_id = htons(getpid() & 0xFFFF);
    icmp_hdr->icmp_seq = htons(1);
    icmp_hdr->icmp_cksum = 0;
    icmp_hdr->icmp_cksum = checksum(icmp_hdr, PACKET_SIZE);

    struct sockaddr_in *dest_addr = (struct sockaddr_in *)res->ai_addr;

    /* Record start time */
    struct timeval start_time, end_time;
    gettimeofday(&start_time, NULL);

    /* Send ICMP echo request */
    ssize_t sent = sendto(sockfd, packet, PACKET_SIZE, 0, 
                          (struct sockaddr *)dest_addr, sizeof(*dest_addr));
    if (sent < 0) {
        fprintf(stderr, "Error: sendto failed: %s\n", strerror(errno));
        close(sockfd);
        freeaddrinfo(res);
        return 5;
    }

    /* Calculate absolute deadline for timeout */
    struct timeval deadline;
    deadline.tv_sec = start_time.tv_sec + (timeout_ms / 1000);
    deadline.tv_usec = start_time.tv_usec + ((timeout_ms % 1000) * 1000);
    if (deadline.tv_usec >= 1000000) {
        deadline.tv_sec += 1;
        deadline.tv_usec -= 1000000;
    }

    /* Expected values for matching reply */
    unsigned short expected_id = getpid() & 0xFFFF;
    unsigned short expected_seq = 1;
    uint32_t expected_addr = dest_addr->sin_addr.s_addr;

    /* Loop until we receive a matching reply or timeout */
    while (1) {
        /* Calculate remaining time until deadline */
        struct timeval now;
        gettimeofday(&now, NULL);
        
        struct timeval remaining;
        remaining.tv_sec = deadline.tv_sec - now.tv_sec;
        remaining.tv_usec = deadline.tv_usec - now.tv_usec;
        
        if (remaining.tv_usec < 0) {
            remaining.tv_sec -= 1;
            remaining.tv_usec += 1000000;
        }
        
        /* Check if timeout has already expired */
        if (remaining.tv_sec < 0 || (remaining.tv_sec == 0 && remaining.tv_usec <= 0)) {
            /* Timeout */
            close(sockfd);
            freeaddrinfo(res);
            return 7;
        }

        /* Ensure remaining time is non-negative (guards against clock adjustments) */
        if (remaining.tv_sec < 0) {
            remaining.tv_sec = 0;
            remaining.tv_usec = 0;
        }
        if (remaining.tv_usec < 0) {
            remaining.tv_usec = 0;
        }

        /* Wait for data with remaining timeout */
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(sockfd, &read_fds);

        int select_result = select(sockfd + 1, &read_fds, NULL, NULL, &remaining);
        if (select_result < 0) {
            fprintf(stderr, "Error: select failed: %s\n", strerror(errno));
            close(sockfd);
            freeaddrinfo(res);
            return 6;
        }

        if (select_result == 0) {
            /* Timeout */
            close(sockfd);
            freeaddrinfo(res);
            return 7;
        }

        /* Receive ICMP packet */
        char recv_buf[1024];
        struct sockaddr_in recv_addr;
        socklen_t addr_len = sizeof(recv_addr);
        
        ssize_t recv_len = recvfrom(sockfd, recv_buf, sizeof(recv_buf), 0,
                                    (struct sockaddr *)&recv_addr, &addr_len);
        if (recv_len < 0) {
            fprintf(stderr, "Error: recvfrom failed: %s\n", strerror(errno));
            close(sockfd);
            freeaddrinfo(res);
            return 8;
        }

        /* Parse IP header to get to ICMP header */
        struct ip *ip_hdr = (struct ip *)recv_buf;
        int ip_header_len = ip_hdr->ip_hl * 4;
        
        /* Validate IP header length is reasonable (min 20, max 60 bytes) */
        if (ip_header_len < 20 || ip_header_len > 60) {
            /* Invalid IP header length, skip packet */
            continue;
        }
        
        if (recv_len < ip_header_len + ICMP_HEADER_SIZE) {
            /* Packet too short, skip it and continue waiting */
            continue;
        }

        struct icmp *recv_icmp = (struct icmp *)(recv_buf + ip_header_len);

        /* Check if this is an ICMP ECHOREPLY */
        if (recv_icmp->icmp_type != ICMP_ECHOREPLY) {
            /* Not an echo reply, skip it and continue waiting */
            continue;
        }

        /* Check if ID matches our process */
        if (ntohs(recv_icmp->icmp_id) != expected_id) {
            /* ID mismatch, this is for another process, skip it */
            continue;
        }

        /* Check if sequence matches our request */
        if (ntohs(recv_icmp->icmp_seq) != expected_seq) {
            /* Sequence mismatch, skip it */
            continue;
        }

        /* Check if source address matches our destination */
        if (recv_addr.sin_addr.s_addr != expected_addr) {
            /* Source mismatch, skip it */
            continue;
        }

        /* This is our matching reply! Record end time and break */
        gettimeofday(&end_time, NULL);
        break;
    }

    /* Calculate RTT in milliseconds */
    double rtt_ms = (end_time.tv_sec - start_time.tv_sec) * 1000.0 +
                    (end_time.tv_usec - start_time.tv_usec) / 1000.0;

    /* Output result */
    printf("rtt_ms=%.3f\n", rtt_ms);

    close(sockfd);
    freeaddrinfo(res);
    return 0;
}
