import socket
import sys


class MessageHub:
    def __init__(self):
        self.host_ip = self.get_valid_ip()
        self.host_port = self.get_valid_port()
        self.clients = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            self.server_socket.bind((self.host_ip, self.host_port))
            print(f"\nСервер успешно запущен на {self.host_ip}: {self.host_port}")
            print("Ожидание пользователей...\n")
        except socket.error as e:
            print(f"Не удалось привязать сервер к {self.host_ip}:{self.host_port}: {e}")
            sys.exit(1)

    def get_valid_ip(self):
        while True:
            ip = input("Введите IP-адрес сервера (оставьте пустым для локального хоста): ").strip()
            if not ip:
                return '127.0.0.1'
            try:
                socket.inet_aton(ip)
                return ip
            except socket.error:
                print("Введен некорректный IP-адрес, попробуйте снова.")

    def get_valid_port(self):
        while True:
            try:
                port = int(input("Введите номер порта сервера (1024-65535): "))
                if 1024 <= port <= 65535:
                    return port
                print("Ошибка: номер порта должен находиться в диапазоне 1024-65535.")
            except ValueError:
                print("Ошибка: введите корректное число.")

    def send_message_to_all(self, message, sender_address=None):
        for client_address, (client_name, _, _) in self.clients.items():
            if client_address != sender_address:
                try:
                    self.server_socket.sendto(message.encode(), client_address)
                except socket.error as e:
                    print(f"Ошибка отправки сообщения пользователю {client_name}: {e}")
                    del self.clients[client_address]

    def run(self):
        while True:
            try:
                data, client_address = self.server_socket.recvfrom(1024)
                data = data.decode()

                if client_address not in self.clients:
                    if data.startswith("reg:"):
                        client_name = data.split(":")[1]
                        self.clients[client_address] = (client_name, client_address[0], client_address[1])
                        print(f"Новый пользователь {client_name} подключился ({client_address[0]}:{client_address[1]})")
                        self.send_message_to_all(f"{client_name} присоединился к беседе", client_address)
                        continue

                if data.lower() == 'exit':
                    client_name = self.clients[client_address][0]
                    del self.clients[client_address]
                    print(f"{client_name} вышел из чата.")
                    self.send_message_to_all(f"{client_name} покинул беседу", client_address)
                    continue

                client_name = self.clients[client_address][0]
                message = f"{client_name}: {data}"
                print(message)
                self.send_message_to_all(message, client_address)

            except Exception as e:
                print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    server = MessageHub()
    server.run()
