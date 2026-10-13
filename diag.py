# Практическая работа «Диагностика сети средствами Python»
# ФИО:     ____________________
# Группа:  ____________________
# Вариант: 1

import socket
import time
import subprocess
import math
import ipaddress
import platform

VARIANT = 1

# Исходные данные варианта 1
HOST = "google.com"
NETWORK = "192.168.1.0/24"
NEEDS = {"Продажи": 50, "Бухгалтерия": 25, "Серверная": 10, "Линк": 2}


# ЗАДАНИЕ 1. Проверка DNS
def check_dns(host):
    try:
        ip = socket.gethostbyname(host)
        print(f"[DNS ] {host} -> {ip}")
        return ip
    except socket.gaierror as e:
        print(f"[DNS ] ОШИБКА: не удалось определить IP-адрес для {host} ({e})")
        return None


# ЗАДАНИЕ 2. Проверка TCP-соединения
def check_tcp(ip, port, timeout=3):
    start = time.perf_counter()
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            ms = (time.perf_counter() - start) * 1000
            print(f"[TCP ] {ip}:{port} открыт, соединение за {ms:.0f} мс")
            return True
    except socket.timeout:
        print(f"[TCP ] {ip}:{port} ТАЙМАУТ: нет ответа за {timeout} с")
    except ConnectionRefusedError:
        print(f"[TCP ] {ip}:{port} ОТКАЗ: узел отвечает, но порт закрыт")
    except OSError as e:
        print(f"[TCP ] {ip}:{port} ОШИБКА: {e}")
    return False


# ЗАДАНИЕ 3. Проверка HTTP
def check_http(host, port=80, timeout=5):
    request = f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(request.encode())
            data = s.recv(1024).decode(errors="replace")
            status = data.split("\r\n")[0]
            print(f"[HTTP] {host}:{port} -> {status}")
            return status
    except OSError as e:
        print(f"[HTTP] {host}:{port} ОШИБКА: {e}")
        return None


# ЗАДАНИЕ 4. Объединение проверок
def diagnose(host, tcp_port=443, http_port=80):
    print(f"=== Диагностика {host} ===")

    ip = check_dns(host)
    if ip is None:
        print("ВЫВОД: проблема на прикладном уровне (DNS)")
        return

    if not check_tcp(ip, tcp_port):
        print("ВЫВОД: проблема на транспортном/межсетевом уровне (TCP-соединение)")
        return

    if check_http(host, http_port) is None:
        print("ВЫВОД: проблема на прикладном уровне (HTTP)")
        return

    print("ВЫВОД: все проверенные уровни работают")


# ЗАДАНИЕ 5. Расчёт подсетей VLSM
def vlsm(network, needs):
    base = ipaddress.ip_network(network)
    start = int(base.network_address)
    result = []

    for name, hosts in sorted(needs.items(), key=lambda kv: kv[1], reverse=True):
        h = math.ceil(math.log2(hosts + 2))  # 2^h - 2 >= hosts
        prefix = 32 - h
        sub = ipaddress.ip_network((start, prefix))
        result.append((name, hosts, sub))
        start = int(sub.broadcast_address) + 1

    return result


def print_vlsm(result):
    print(f"{'Отдел':<14}{'Треб.':<6}{'Сеть':<18}{'Маска':<16}{'Первый IP':<14}{'Последний IP':<14}Broadcast")
    for name, hosts, sub in result:
        h = list(sub.hosts())
        print(f"{name:<14}{hosts:<6}{str(sub):<18}{str(sub.netmask):<16}"
              f"{str(h[0]):<14}{str(h[-1]):<14}{sub.broadcast_address}")


def check_vlsm(network, result):
    """Самопроверка: готовая функция, писать не нужно."""
    base = ipaddress.ip_network(network)
    prev_end = None
    for name, hosts, sub in result:
        assert sub.subnet_of(base), f"{name}: подсеть вне базовой сети"
        assert len(list(sub.hosts())) >= hosts, f"{name}: адресов не хватает"
        assert sub.num_addresses // 2 - 2 < hosts, f"{name}: блок больше необходимого"
        if prev_end is not None:
            assert int(sub.network_address) == prev_end + 1, f"{name}: между блоками есть пропуск или наложение"
        prev_end = int(sub.broadcast_address)
    print("Самопроверка VLSM: ВСЁ ВЕРНО")


# ЗАДАНИЕ 6. Проверка ping через subprocess
def check_ping(host, count=3):
    # В Windows у ping другие ключи: -n (число запросов) и -w (ожидание в мс)
    if platform.system() == "Windows":
        cmd = ["ping", "-n", str(count), "-w", "2000", host]
    else:
        cmd = ["ping", "-c", str(count), "-W", "2", host]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        print("[PING] утилита ping не найдена")
        return None
    except subprocess.TimeoutExpired:
        print("[PING] ТАЙМАУТ выполнения команды")
        return False

    if r.returncode == 0:
        print(f"[PING] {host} отвечает")
        return True
    else:
        print(f"[PING] {host} НЕ отвечает (код {r.returncode})")
        return False


if __name__ == "__main__":
    print("----- Задание 1 -----")
    check_dns(HOST)
    check_dns("qwerty12345.invalid")

    print("\n----- Задание 2 -----")
    ip = check_dns(HOST)
    check_tcp(ip, 443)                 # порт HTTPS
    check_tcp("127.0.0.1", 65000)      # порт, который никто не слушает
    # Опыт по желанию: check_tcp("10.255.255.1", 80, timeout=2)

    print("\n----- Задание 3 -----")
    check_http(HOST)
    check_http("localhost", port=65000)

    print("\n----- Задание 4 -----")
    diagnose(HOST)
    print()
    diagnose("qwerty12345.invalid")
    print()
    diagnose("localhost", tcp_port=65000)

    print("\n----- Задание 5 -----")
    res = vlsm(NETWORK, NEEDS)
    print_vlsm(res)                    # готовая функция: печатает таблицу
    check_vlsm(NETWORK, res)           # готовая самопроверка

    print("\nОпыт: отдел «Продажи» с 62, 63 и 64 узлами")
    for n in (62, 63, 64):
        needs = dict(NEEDS, Продажи=n)
        for name, hosts, sub in vlsm(NETWORK, needs):
            if name == "Продажи":
                print(f"Продажи = {n}: {sub}, узлов в блоке {sub.num_addresses - 2}")

    print("\n----- Задание 6 -----")
    check_ping("127.0.0.1")
    check_ping(HOST)
    diagnose(HOST)
