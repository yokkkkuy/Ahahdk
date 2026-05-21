import requests
import os

# Dosya adı
FILE_NAME = "dedenecekproxyler.txt"

def get_proxies_from_url(url):
    """Verilen URL'den proxy listesini alır, her satırda protokol://ip:port formatında."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        # Satırları al ve boş satırları temizle
        proxies = [line.strip() for line in response.text.splitlines() if line.strip()]
        return proxies
    except Exception as e:
        print(f"[-] {url} adresinden proxy alınamadı: {e}")
        return []

def get_last_position():
    """Dosyanın son satırını ve o satırdan itibaren başlanacak index'i bulur."""
    if not os.path.exists(FILE_NAME):
        return 0, None  # Dosya yoksa baştan başla
    
    with open(FILE_NAME, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        return 0, None
    
    # En son satırı al
    last_line = lines[-1].strip()
    # Son satırda yazılı olan proxy'yi bul
    # (Dosyadaki son proxy, başlangıç noktası olarak kullanılacak)
    if last_line:
        return len(lines), last_line  # Satır sayısı ve son proxy
    else:
        # Son satır boşsa bir önceki geçerli satırı bul
        for i in range(len(lines)-1, -1, -1):
            if lines[i].strip():
                return i+1, lines[i].strip()
        return 0, None

def append_proxies(new_proxies, start_after=None):
    """Proxy'leri dosyaya ekler. start_after verilmişse o proxyden sonra eklemeye başlar."""
    if not new_proxies:
        print("[-] Eklenecek proxy yok.")
        return
    
    # start_after varsa, o proxyden sonraki index'i bul
    start_index = 0
    if start_after and start_after in new_proxies:
        start_index = new_proxies.index(start_after) + 1
    elif start_after:
        # Dosyadaki son proxy listede yoksa (güncel değilse) baştan ekle
        print("[!] Dosyadaki son proxy mevcut listede bulunamadı, baştan ekleniyor.")
        start_index = 0
    
    proxies_to_add = new_proxies[start_index:]
    
    if not proxies_to_add:
        print("[i] Yeni eklenecek proxy yok (hepsi daha önce eklenmiş).")
        return
    
    # Dosyaya ekle
    with open(FILE_NAME, 'a', encoding='utf-8') as f:
        for proxy in proxies_to_add:
            f.write(proxy + '\n')
    
    print(f"[+] {len(proxies_to_add)} yeni proxy eklendi. Toplam {len(proxies_to_add) + (start_index if start_after else 0)} proxy kontrol edildi.")

def main():
    print("[i] Proxy toplama işlemi başladı...")
    
    # API URL'leri
    url1 = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text"
    url2 = "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
    
    # 1. API'den proxy al
    print("[1] Proxyscape'den proxy'ler alınıyor...")
    proxies1 = get_proxies_from_url(url1)
    print(f"    {len(proxies1)} proxy alındı.")
    
    # 2. API'den proxy al (sayfaları gezerek)
    print("[2] Geonode'dan proxy'ler alınıyor...")
    proxies2 = []
    page = 1
    while True:
        url = f"https://proxylist.geonode.com/api/proxy-list?limit=500&page={page}&sort_by=lastChecked&sort_type=desc"
        data = get_proxies_from_url(url)
        if not data:
            break
        
        # Gelen veri JSON değil, direkt proxy listesi mi kontrol et
        # API aslında JSON döndüğü için özel işlem yapalım
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            json_data = response.json()
            if 'data' in json_data and json_data['data']:
                for item in json_data['data']:
                    if 'protocol' in item and 'ip' in item and 'port' in item:
                        proxy_str = f"{item['protocol']}://{item['ip']}:{item['port']}"
                        proxies2.append(proxy_str)
                page += 1
            else:
                break
        except:
            # JSON değilse veya hata varsa çık
            break
    
    print(f"    {len(proxies2)} proxy alındı.")
    
    # Tüm proxy'leri birleştir ve benzersiz yap
    all_proxies = list(dict.fromkeys(proxies1 + proxies2))
    print(f"[i] Toplam {len(all_proxies)} benzersiz proxy toplandı.")
    
    # Dosyadaki son durumu kontrol et
    line_count, last_proxy = get_last_position()
    
    if line_count == 0:
        print("[i] Dosya boş veya yok. Tüm proxy'ler ekleniyor.")
        append_proxies(all_proxies)
    else:
        print(f"[i] Dosyada {line_count} satır var. Son proxy: {last_proxy}")
        append_proxies(all_proxies, start_after=last_proxy)
    
    print("[✓] İşlem tamamlandı.")

if __name__ == "__main__":
    main()
