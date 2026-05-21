#!/usr/bin/env python3
"""
NovixLibrary Proxy Tester
Her bir referans kodu için thread'ler proxy havuzundan eşsiz proxy alarak test eder.
5 başarılı proxy'yi calisanproxyler.txt dosyasına kaydeder.
"""

import asyncio
import aiohttp
import json
import random
import string
import time
import os
from collections import deque
from typing import Dict, List, Set, Optional
import sys

# Gerekli kütüphaneler (ish shell için pip install):
# pip install aiohttp nest-asyncio

def random_email():
    """Rastgele geçici email oluşturur"""
    uzunluk = random.randint(6, 10)
    rastgele_kisim = ''.join(random.choices(string.ascii_lowercase + string.digits, k=uzunluk))
    domainler = ["guerrillamail.info", "mailinator.com", "10minute.net", "tempr.email"]
    return f"{rastgele_kisim}@{random.choice(domainler)}"

def load_proxies_from_file(filename: str = "dedenecekproxyler.txt") -> List[str]:
    """Proxy dosyasını okur ve geçerli proxy'leri listeler"""
    if not os.path.exists(filename):
        print(f"[!] {filename} dosyası bulunamadı!")
        return []
    
    proxies = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and ('://' in line):
                proxies.append(line)
    
    print(f"[+] {len(proxies)} proxy {filename} dosyasından yüklendi")
    return proxies

def load_successful_proxies(filename: str = "calisanproxyler.txt") -> Set[str]:
    """Daha önce çalışan proxy'leri yükler (tekrar denememek için)"""
    if not os.path.exists(filename):
        return set()
    
    successful = set()
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                successful.add(line)
    
    return successful

def save_successful_proxy(proxy: str, filename: str = "calisanproxyler.txt"):
    """Çalışan proxy'yi dosyaya kaydeder"""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(proxy + '\n')

def proxy_dict_from_string(proxy_str: str) -> Optional[Dict]:
    """Proxy string'ini aiohttp için dict formatına çevirir"""
    if '://' not in proxy_str:
        return None
    
    protocol = proxy_str.split('://')[0]
    addr = proxy_str.split('://')[1]
    
    # aiohttp socks proxy desteği için
    if protocol in ['socks4', 'socks5']:
        # aiohttp-socks kütüphanesi gerekiyor
        return {
            'http': f"{protocol}://{addr}",
            'https': f"{protocol}://{addr}"
        }
    elif protocol in ['http', 'https']:
        return {
            'http': f"{protocol}://{addr}",
            'https': f"{protocol}://{addr}"
        }
    return None

async def test_proxy_with_registration(session: aiohttp.ClientSession, 
                                        proxy: str, 
                                        referans_kodu: str,
                                        thread_id: int) -> tuple[bool, str]:
    """Tek bir proxy ile kayıt işlemini dener"""
    
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        'content-type': "application/json",
        'apikey': "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2aWRseHV4dGFrZGlkc3p4ZXVoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3MzYwNTEsImV4cCI6MjA4NzMxMjA1MX0.ffUBzkS18Yeh5njBF4qYR5xY2LIZK8KPfCTDJmFcZ_k",
        'authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2aWRseHV4dGFrZGlkc3p4ZXVoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3MzYwNTEsImV4cCI6MjA4NzMxMjA1MX0.ffUBzkS18Yeh5njBF4qYR5xY2LIZK8KPfCTDJmFcZ_k",
        'origin': "https://novixlibrary.com",
        'referer': "https://novixlibrary.com/",
        'accept-language': "tr",
        'Connection': 'close'
    }
    
    url = "https://bvidlxuxtakdidszxeuh.supabase.co/auth/v1/signup"
    params = {'redirect_to': "https://novixlibrary.com"}
    
    email = random_email()
    payload = {
        "email": email,
        "password": "den2333iz3deniz@deniz.con.tc",
        "data": {
            "display_name": f"User_{random.randint(1000, 9999)}",
            "referred_by": referans_kodu
        },
        "gotrue_meta_security": {},
        "code_challenge": None,
        "code_challenge_method": None
    }
    
    proxy_dict = proxy_dict_from_string(proxy)
    if not proxy_dict:
        return False, "Geçersiz proxy formatı"
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.post(url, params=params, json=payload,
                               headers=headers, proxy=proxy_dict.get('http'),
                               timeout=timeout, ssl=False) as response:
            
            if response.status == 200:
                try:
                    data = await response.json()
                    if 'id' in data:
                        return True, data['id']
                    else:
                        return False, "ID bulunamadı"
                except:
                    return False, "JSON parse hatası"
            else:
                text = await response.text()
                return False, f"HTTP {response.status}"
                
    except asyncio.TimeoutError:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)[:50]

class ProxyWorker:
    """Her thread için proxy yöneticisi"""
    def __init__(self, thread_id: int, referans_kodu: str, target_success: int = 5):
        self.thread_id = thread_id
        self.referans_kodu = referans_kodu
        self.target_success = target_success
        self.successful_proxies = []
        self.tested_proxies = []
        
    async def run(self, proxy_queue: deque, proxy_lock: asyncio.Lock, 
                  global_successful: Set[str], session: aiohttp.ClientSession):
        """Thread'i çalıştırır"""
        
        print(f"[Thread-{self.thread_id}] Başladı. Hedef: {self.target_success} başarılı proxy")
        
        while len(self.successful_proxies) < self.target_success:
            # Sıradaki proxy'yi al
            async with proxy_lock:
                if not proxy_queue:
                    print(f"[Thread-{self.thread_id}] Proxy kalmadı! ({len(self.successful_proxies)}/{self.target_success})")
                    break
                current_proxy = proxy_queue.popleft()
            
            # Bu proxy daha önce global olarak çalıştı mı?
            if current_proxy in global_successful:
                print(f"[Thread-{self.thread_id}] Proxy zaten çalışanlar listesinde, atlanıyor: {current_proxy[:40]}")
                continue
            
            self.tested_proxies.append(current_proxy)
            
            # Proxy'yi test et
            print(f"[Thread-{self.thread_id}] Test ediliyor: {current_proxy[:40]}...")
            success, result = await test_proxy_with_registration(session, current_proxy, 
                                                                  self.referans_kodu, 
                                                                  self.thread_id)
            
            if success:
                print(f"[Thread-{self.thread_id}] ✓ BAŞARILI! {current_proxy[:40]} -> {result[:8]}...")
                self.successful_proxies.append(current_proxy)
                # Global listeye ekle
                async with proxy_lock:
                    global_successful.add(current_proxy)
                # Dosyaya hemen kaydet
                save_successful_proxy(current_proxy)
            else:
                print(f"[Thread-{self.thread_id}] ✗ BAŞARISIZ: {current_proxy[:40]} -> {result}")
            
            # Rate limiting için küçük bir bekleme
            await asyncio.sleep(0.5)
        
        print(f"[Thread-{self.thread_id}] Tamamlandı! {len(self.successful_proxies)} başarılı proxy bulundu.")
        return self.successful_proxies

async def main_async(referans_kodu: str, thread_count: int, proxy_list: List[str]):
    """Ana asenkron fonksiyon"""
    
    print("\n" + "=" * 70)
    print(f"NOVIXLIBRARY PROXY TESTER")
    print(f"Referans Kodu: {referans_kodu}")
    print(f"Thread Sayısı: {thread_count}")
    print(f"Proxy Havuzu: {len(proxy_list)} proxy")
    print(f"Hedef: Thread başına 5 başarılı proxy")
    print("=" * 70 + "\n")
    
    # Daha önce çalışan proxy'leri yükle
    global_successful = load_successful_proxies("calisanproxyler.txt")
    print(f"[!] Önceden çalışan {len(global_successful)} proxy yüklendi (bunlar tekrar test edilmeyecek)\n")
    
    # Proxy kuyruğu oluştur (her thread aynı kuyruktan çekecek)
    proxy_queue = deque(proxy_list)
    proxy_lock = asyncio.Lock()
    
    # Thread'leri oluştur
    workers = []
    async with aiohttp.ClientSession() as session:
        for i in range(thread_count):
            worker = ProxyWorker(thread_id=i+1, referans_kodu=referans_kodu, target_success=5)
            workers.append(worker.run(proxy_queue, proxy_lock, global_successful, session))
        
        # Tüm thread'leri bekle
        results = await asyncio.gather(*workers)
    
    # Rapor
    print("\n" + "=" * 70)
    print("İŞLEM TAMAMLANDI!")
    print("=" * 70)
    
    total_success = sum(len(r) for r in results)
    print(f"\n[+] Toplam Başarılı Proxy: {total_success}")
    print(f"[+] Kalan Proxy: {len(proxy_queue)}")
    print(f"[+] Toplam Test Edilen: {len(proxy_list) - len(proxy_queue)}")
    
    print("\n[✓] Çalışan proxy'ler 'calisanproxyler.txt' dosyasına kaydedildi.")
    print("[!] Bu proxy'leri artık diğer scriptinizde kullanabilirsiniz.\n")
    
    return results

def main():
    """Ana fonksiyon"""
    print("=" * 70)
    print("NOVIXLIBRARY PROXY TESTER")
    print("Bu araç, dedenecekproxyler.txt'deki proxy'leri test eder")
    print("5 başarılı istek yapan proxy'leri calisanproxyler.txt'ye kaydeder")
    print("=" * 70)
    
    # Kullanıcıdan referans kodu al
    referans_kodu = input("\n[*] Referans Kodunu Girin: ").strip().upper()
    if not referans_kodu:
        print("[X] Referans kodu boş olamaz!")
        return
    
    # Kullanıcıdan thread sayısını al
    try:
        thread_count = int(input("[*] Thread Sayısını Girin (1-20): ").strip())
        if thread_count < 1 or thread_count > 20:
            print("[X] Thread sayısı 1-20 arasında olmalı!")
            return
    except ValueError:
        print("[X] Geçerli bir sayı girin!")
        return
    
    # Proxy'leri yükle
    proxy_list = load_proxies_from_file("dedenecekproxyler.txt")
    if not proxy_list:
        print("[X] Proxy bulunamadı! Önce proxy toplama scriptini çalıştırın.")
        return
    
    print(f"\n[!] {thread_count} thread ile çalışılıyor...")
    print("[!] Her thread 5 başarılı proxy bulmaya çalışacak")
    print("[!] Aynı proxy iki farklı thread tarafından asla kullanılmayacak\n")
    
    # Ana işlemi başlat
    start_time = time.time()
    
    try:
        # asyncio'yu çalıştır
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        results = asyncio.run(main_async(referans_kodu, thread_count, proxy_list))
        
        elapsed = time.time() - start_time
        print(f"\n[✓] Toplam Süre: {elapsed:.1f} saniye ({elapsed/60:.1f} dakika)")
        
    except KeyboardInterrupt:
        print("\n\n[!] İşlem kullanıcı tarafından durduruldu!")
    except Exception as e:
        print(f"\n[X] Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
