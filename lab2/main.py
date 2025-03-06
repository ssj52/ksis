import socket
import struct
import time
import sys

ICMP_REQUEST_TYPE = 8
ICMP_TIME_EXCEEDED = 11
ICMP_HOST_UNREACHABLE = 3


def calculate_checksum(packet_data):
    checksum = 0
    length = (len(packet_data) // 2) * 2
    index = 0

    while index < length:
        word = packet_data[index + 1] * 256 + packet_data[index]
        checksum += word
        checksum &= 0xffffffff
        index += 2

    if index < len(packet_data):
        checksum += packet_data[-1]
        checksum &= 0xffffffff

    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum += (checksum >> 16)
    final_checksum = ~checksum & 0xffff
    return (final_checksum >> 8) | ((final_checksum << 8) & 0xff00)


def create_icmp_packet(packet_id, packet_seq_num):
    header = struct.pack("!BBHHH", ICMP_REQUEST_TYPE, 0, 0, packet_id, packet_seq_num)
    payload = struct.pack("d", time.time())
    checksum = calculate_checksum(header + payload)
    header = struct.pack("!BBHHH", ICMP_REQUEST_TYPE, 0, checksum, packet_id, packet_seq_num)
    return header + payload


def run_traceroute(target, max_hops=30, timeout=2, packets_per_hop=3, max_consecutive_timeouts=10):
    try:
        target_ip = socket.gethostbyname(target)
    except socket.gaierror:
        print(f"Ошибка: не удалось разрешить имя хоста {target}")
        return

    print(f"трассировка к {target} ({target_ip}), максимальное число хопов: {max_hops}, тайм-ауты {timeout * 1000} мс\n")

    try:
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        recv_socket.settimeout(timeout)
    except PermissionError:
        print("Ошибка: запустите программу с правами администратора (root)")
        return
    except Exception as err:
        print(f"Ошибка при создании сокетов: {err}")
        return

    packet_id = id(target_ip) & 0xffff
    seq_num = 0
    consecutive_timeouts = 0

    try:
        for hop in range(1, max_hops + 1):
            try:
                send_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
                send_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, hop)
            except Exception as err:
                print(f"Ошибка при создании сокета для отправки: {err}")
                break

            hop_times = []
            hop_ips = set()
            hop_timeouts = 0

            for _ in range(packets_per_hop):
                seq_num += 1
                try:
                    start_time = time.time()
                    icmp_packet = create_icmp_packet(packet_id, seq_num)
                    send_socket.sendto(icmp_packet, (target_ip, 0))

                    response_data, response_addr = recv_socket.recvfrom(1024)
                    end_time = time.time()
                    round_trip_time = (end_time - start_time) * 1000

                    icmp_response = response_data[20:28]
                    icmp_type, _, _, _, _ = struct.unpack("!BBHHH", icmp_response)

                    if icmp_type == ICMP_TIME_EXCEEDED:
                        hop_ips.add(response_addr[0])
                        hop_times.append(f"{round_trip_time:.2f} ms")
                    elif icmp_type == ICMP_HOST_UNREACHABLE:
                        hop_ips.add(response_addr[0])
                        hop_times.append(f"{round_trip_time:.2f} ms")
                        if response_addr[0] == target_ip:
                            print(f"{hop:<4} {response_addr[0]:<15} {' '.join(hop_times)} (Хост недоступен!)")
                            send_socket.close()
                            recv_socket.close()
                            return
                    else:
                        hop_times.append("*")

                    if icmp_type == 0 and response_addr[0] == target_ip:
                        print(f"{hop:<4} {response_addr[0]:<15} {' '.join(hop_times)} ")
                        send_socket.close()
                        recv_socket.close()
                        return

                except socket.timeout:
                    hop_times.append("*")
                    hop_timeouts += 1
                except Exception as err:
                    print(f"Ошибка на хопе {hop}: {err}")
                    hop_times.append("*")

            if hop_timeouts == packets_per_hop:
                consecutive_timeouts += 1
            else:
                consecutive_timeouts = 0

            if consecutive_timeouts >= max_consecutive_timeouts:
                print("Превышено количество подряд идущих тайм-аутов. Завершение трассировки.")
                break

            hop_ip_output = ' '.join(hop_ips) if hop_ips else "*"
            print(f"{hop:<4} {hop_ip_output:<15} {' '.join(hop_times)}")
            send_socket.close()

    except KeyboardInterrupt:
        print("\nТрассировка прервана пользователем.")

    print("Цель не достигнута за максимальное количество хопов.")
    recv_socket.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_address = sys.argv[1]
    else:
        target_address = input("Введите адрес для трассировки (например, google.com): ").strip()

    if target_address:
        run_traceroute(target_address)
    else:
        print("Ошибка: адрес не указан.")
        sys.exit(1)
