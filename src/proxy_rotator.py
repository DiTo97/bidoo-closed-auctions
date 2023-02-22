import ipaddress
import random
import requests

from bs4 import BeautifulSoup as bs
from typing import *


class ProxyRotator():
    _STR_download: str = 'Downloading HTTPS proxies...'

    _URL_freexies: List[str] = [
        'https://sslproxies.org/',
        'https://free-proxy-list.net/'
    ]

    _blocked: Set[str]
    _proxies: Set[str]
    _proxy: Optional[str]
    _n: int

    def __init__(self, n: int = -1):
        self._blocked = set()
        self._proxies = set()
        self._proxy = None
        self._n = n

        self._download()

    @property
    def blocked(self) -> Set[str]:
        return self._blocked

    @property
    def nproxies(self) -> int:
        return len(self._proxies)

    @property
    def proxies(self) -> Dict[str, str]:
        if self._proxy is None:
            return None
            
        return {'https': self._proxy}

    @property
    def proxy(self) -> str:
        return self._proxy

    @staticmethod
    def is_https(text: str) -> bool:
        if text is None:
            return False

        return text.lower() == 'yes'

    @staticmethod
    def is_valid_ipv4(address: str) -> bool:
        try:
            ip = ipaddress.ip_address(address)

            return isinstance(ip,
                              ipaddress.IPv4Address)
        except ValueError:
            return False

    def block(self):
        self._blocked.add(self._proxy)

    def renew(self) -> Optional[str]:
        if self.nproxies == 0:
            print(self._STR_download)
            self._download()

        if self.nproxies == 0:
            self._proxy = None

        self._proxy = self._proxies.pop()

    def _download(self):
        if self._n == 0:
            return

        self._proxies.clear()

        for url in self._URL_freexies:
            res  = requests.get(url) 
            soup = bs(res.content, 'html5lib') 

            # 1. Extract data from IP table
            addresses = soup.findAll('td')[::8]
            ports = soup.findAll('td')[1::8]
            https = soup.findAll('td')[6::8]

            # 2. Filter for IPv4 addresses only
            addresses = [a for a in addresses
                           if self.is_valid_ipv4(a.text)]

            # 3. Zip IP, port and HTTPS data
            proxies = list(zip(map(lambda x: x.text, addresses),
                               map(lambda x: x.text, ports),
                               map(lambda x: x.text, https)))
            
            # 4. a) Filter for HTTPS proxies only
            #    b) Merge IP and port data
            proxies = [a + ':' + p
                           for a, p, h in proxies
                           if self.is_https(h)]

            self._proxies = self._proxies | set(proxies)

        # Remove blacklisted proxies
        self._proxies = self._proxies - self._blocked

        if self._n > -1 \
                and self.nproxies > self._n:
            self._proxies = set(random.sample(
                                    self._proxies,
                                    self._n))
