

import socket
import threading
import re
import time
from urllib.parse import urlparse

BUFFER_SIZE = 8192
TIMEOUT = 5
DEFAULT_PORT = 8080


def parse_http_request(request_data):
    """Парсинг HTTP запроса для получения метода, URL и версии HTTP"""
    try:
        # Получаем первую строку запроса
        request_line = request_data.split(b'\r\n')[0].decode('utf-8')
        method, url, version = request_line.split(' ')
        return method, url, version
    except Exception as e:
        print(f"Ошибка при парсинге HTTP запроса: {e}")
        return None, None, None


def get_host_from_headers(headers_data):
    """Извлечение хоста из заголовков, если он есть"""
    headers = headers_data.decode('utf-8', errors='ignore').split('\r\n')
    for header in headers:
        if header.lower().startswith('host:'):
            return header.split(':', 1)[1].strip()
    return None


def modify_request_for_server(request_data, url):
    """Модификация запроса: замена полного URL на путь"""
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path
        if not path:
            path = "/"
        if parsed_url.query:
            path += "?" + parsed_url.query

        # Заменяем полный URL на путь в первой строке запроса
        first_line = request_data.split(b'\r\n')[0].decode('utf-8')
        method, _, version = first_line.split(' ')
        new_first_line = f"{method} {path} {version}"

        # Создаем новый запрос
        modified_request = request_data.replace(
            request_data.split(b'\r\n')[0],
            new_first_line.encode('utf-8')
        )

        return modified_request
    except Exception as e:
        print(f"Ошибка при модификации запроса: {e}")
        return request_data


def get_response_code(response_data):
    """Извлечение кода ответа из HTTP ответа"""
    try:
        first_line = response_data.split(b'\r\n')[0].decode('utf-8')
        parts = first_line.split(' ')
        if len(parts) >= 2:
            return parts[1]
        return "???"
    except:
        return "???"


def handle_client(client_socket, client_addr):
    """Обработка соединения от клиента"""
    try:
        client_request = b''
        while b'\r\n\r\n' not in client_request:
            chunk = client_socket.recv(BUFFER_SIZE)
            if not chunk:
                break
            client_request += chunk

        if not client_request:
            client_socket.close()
            return

        method, url, version = parse_http_request(client_request)
        if not url or not method:
            client_socket.close()
            return

        print(f"[->] Получен запрос: {method} {url}")

        # Определяем хост и порт для соединения
        try:
            if url.startswith('http://'):
                parsed_url = urlparse(url)
                host = parsed_url.hostname
                port = parsed_url.port or 80
            else:
                # Если URL не содержит схему, пытаемся получить хост из заголовков
                host = get_host_from_headers(client_request)
                port = 80

            if not host:
                print(f"[!] Не удалось определить хост для URL: {url}")
                client_socket.close()
                return

        except Exception as e:
            print(f"[!] Ошибка при разборе URL {url}: {e}")
            client_socket.close()
            return

        modified_request = modify_request_for_server(client_request, url)

        # Создаем соединение с целевым сервером
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.settimeout(TIMEOUT)

        try:
            server_socket.connect((host, port))
            # Отправляем модифицированный запрос
            server_socket.sendall(modified_request)

            # Получаем ответ от сервера
            server_response = b''
            response_complete = False
            start_time = time.time()

            # Буфер для чтения ответа
            while True:
                try:
                    chunk = server_socket.recv(BUFFER_SIZE)
                    if not chunk:
                        break

                    # Отправляем часть ответа клиенту
                    client_socket.sendall(chunk)

                    # Сохраняем начало ответа для анализа кода ответа
                    if not server_response:
                        server_response = chunk
                        response_code = get_response_code(server_response)
                        print(f"[<-] {url} -> {response_code}")

                    # Для долгоживущих соединений (например, потоковое аудио)
                    # устанавливаем разумный таймаут
                    if time.time() - start_time > 60:  # 60 секунд для примера
                        print(f"[i] Соединение активно в течение 60+ секунд: {url}")
                        start_time = time.time()

                except socket.timeout:
                    print(f"[!] Таймаут при чтении ответа от сервера: {url}")
                    break

        except Exception as e:
            print(f"[!] Ошибка при соединении с сервером {host}:{port}: {e}")
            error_response = f"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 21\r\n\r\nError: {str(e)[:100]}"
            client_socket.sendall(error_response.encode('utf-8'))

        finally:
            server_socket.close()

    except Exception as e:
        print(f"[!] Ошибка при обработке запроса: {e}")

    finally:
        client_socket.close()


def main():
    """Основная функция запуска прокси-сервера"""
    proxy_port = DEFAULT_PORT

    # Создаем сокет сервера
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        proxy_socket.bind(('0.0.0.0', proxy_port))
        proxy_socket.listen(100)
        print(f"[+] HTTP прокси-сервер запущен на порту {proxy_port}")
        print("[+] Для проверки установите в браузере прокси localhost:{port}".format(port=proxy_port))
        print("[+] Попробуйте открыть http://example.com/ или http://live.legendy.by:8000/legendyfm")

        while True:
            client_socket, client_addr = proxy_socket.accept()
            # Создаем отдельный поток для обработки клиента
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_addr))
            client_thread.daemon = True
            client_thread.start()

    except KeyboardInterrupt:
        print("\n[!] Прокси-сервер остановлен пользователем")

    except Exception as e:
        print(f"[!] Произошла ошибка: {e}")

    finally:
        proxy_socket.close()


if __name__ == "__main__":
    main()
