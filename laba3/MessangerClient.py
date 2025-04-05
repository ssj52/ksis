import socket
import sys
from threading import Thread, Event
import time


class MessengerClient:
    def __init__(self):
        self.user_nickname = input("Введите ваш никнейм: ").strip()
        self.host_ip = self.get_valid_ip()
        self.host_port = self.get_valid_port("сервера")
        self.local_port = self.get_valid_port("клиента")
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stop_event = Event()
        try:
            self.client_socket.bind(('', self.local_port))
            print(f"\n{self.user_nickname}, вы подключены на локальном порту {self.local_port}")
            print("Отправьте сообщение (для выхода введите 'exit'):\n")
        except socket.error as err:
            print(f"Ошибка при привязке к порту {self.local_port}: {err}")
            sys.exit(1)

    def get_valid_ip(self):
        while True:
            ip_address = input("Адрес сервера: ").strip()
            octets = ip_address.split(".")
            if len(octets) != 4:
                print("IP-адрес должен содержать 4 числовых сегмента")
                continue
            try:
                if not all(0 <= int(octet) <= 255 for octet in octets):
                    print("Каждый сегмент IP должен быть в пределах 0-255")
                    continue
                return ip_address
            except ValueError:
                print("Некорректный IP-адрес")

    def get_valid_port(self, target):
        while True:
            try:
                port_number = int(input(f"Введите номер порта {target} (1024-65535): "))
                if 1024 <= port_number <= 65535:
                    return port_number
                print("Порт должен быть в диапазоне 1024-65535")
            except ValueError:
                print("Введите числовое значение")

    def receive_messages(self):
        while not self.stop_event.is_set():
            try:
                message, _ = self.client_socket.recvfrom(1024)
                print(message.decode())
            except socket.error as err:
                if not self.stop_event.is_set():
                    print(f"\nПотеря соединения: {err}")
                break

    def start(self):
        receiver_thread = Thread(target=self.receive_messages, daemon=True)
        receiver_thread.start()

        self.client_socket.sendto(f"reg:{self.user_nickname}".encode(), (self.host_ip, self.host_port))

        try:
            while True:
                text_message = input()
                if not text_message:
                    continue
                if text_message.lower() == 'exit':
                    self.client_socket.sendto(b'exit', (self.host_ip, self.host_port))
                    break
                self.client_socket.sendto(text_message.encode(), (self.host_ip, self.host_port))
        finally:
            self.stop_event.set()
            time.sleep(0.1)
            self.client_socket.close()
            print("\nОтключение от сервера завершено")


if __name__ == "__main__":
    messenger_client = MessengerClient()
    messenger_client.start()
