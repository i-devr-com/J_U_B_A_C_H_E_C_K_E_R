import unittest
from pathlib import Path
import tempfile
import os
from juba_checker import CredentialChecker, ProxyManager


class TestProxyManager(unittest.TestCase):
    def test_load_proxies(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("http://proxy1.com:8080\n")
            f.write("http://proxy2.com:3128\n")
            proxy_file = f.name
        
        try:
            pm = ProxyManager(proxy_file)
            self.assertEqual(len(pm.proxies), 2)
        finally:
            os.unlink(proxy_file)
    
    def test_proxy_rotation(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("http://proxy1.com:8080\n")
            f.write("http://proxy2.com:3128\n")
            proxy_file = f.name
        
        try:
            pm = ProxyManager()
            pm.proxies = ["http://proxy1.com:8080", "http://proxy2.com:3128"]
            
            proxy1 = pm.get_next_proxy()
            proxy2 = pm.get_next_proxy()
            proxy3 = pm.get_next_proxy()
            
            self.assertIsNotNone(proxy1)
            self.assertIsNotNone(proxy2)
            self.assertEqual(proxy1, proxy3)
        finally:
            os.unlink(proxy_file)


class TestCredentialChecker(unittest.TestCase):
    def test_parse_credential_line(self):
        checker = CredentialChecker()
        
        result = checker.parse_credential_line("example.com:user@email.com:password123")
        self.assertEqual(result, ("example.com", "user@email.com", "password123"))
        
        result = checker.parse_credential_line("domain.com:user:pass:word:with:colons")
        self.assertEqual(result, ("domain.com", "user", "pass:word:with:colons"))
        
        result = checker.parse_credential_line("invalid")
        self.assertIsNone(result)
    
    def test_normalize_domain(self):
        checker = CredentialChecker()
        
        self.assertEqual(checker.normalize_domain("example.com"), "https://example.com")
        self.assertEqual(checker.normalize_domain("http://example.com"), "http://example.com")
        self.assertEqual(checker.normalize_domain("https://example.com"), "https://example.com")
    
    def test_process_file_dry_run(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("example.com:user1:pass1\n")
            f.write("test.com:user2:pass2\n")
            test_file = f.name
        
        try:
            checker = CredentialChecker()
            checker.process_file(test_file, dry_run=True)
        finally:
            os.unlink(test_file)


class TestFileOperations(unittest.TestCase):
    def test_result_saving(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = CredentialChecker()
            checker.save_result("example.com", "testuser", "testpass", tmpdir)
            
            result_file = Path(tmpdir) / "example.com" / "results.txt"
            self.assertTrue(result_file.exists())
            
            with open(result_file, 'r') as f:
                content = f.read()
                self.assertIn("example.com:testuser:testpass", content)


if __name__ == '__main__':
    unittest.main()
