# TODOs
# # caching
# inmem_cache  # in-memory storage with available and blocked freexies
# cache  # persistent storage with available and blocked freexies

# # filtering
# iso_alpha2_code  # country
# anonimity  # none, anonymous, elite
# secure  # HTTPS or not

# # refereshing
# t_refresh  # -1 or float

# # check on refresh
# For more info, see https://github.com/oxylabs/Rotating-Proxies-With-Python/blob/main/rotating_multiple_proxies_async.py
# - asyncio
# - https://ip.oxylabs.io/ip
# add bad freexies to blocked


import ipaddress
import random
import requests
import typing

from bs4 import BeautifulSoup as BS


_URL_freexies = [
    "https://sslproxies.org/",
    "https://free-proxy-list.net/"
]


def is_valid_ipv4(address: str) -> bool:
    try:
        address = ipaddress.ip_address(address)
        valid_ipv4 = isinstance(address, ipaddress.IPv4Address)

        return valid_ipv4
    except ValueError:
        return False


class ProxyRotator():
    _available: typing.Set[str]
    _blocked: typing.Set[str]
    _elite_only: bool
    _https_only: bool
    _ipv4_only: bool
    _max_num_proxies: int
    _selected: typing.Optional[str]
    _verbose: bool

    def __init__(
        self, 
        *, 
        elite_only: bool = True,
        https_only: bool = True,
        ipv4_only: bool = True,
        max_num_proxies: int = -1, 
        verbose: bool = False
    ):
        self._available = set()
        self._blocked = set()
        self._elite_only = elite_only
        self._https_only = https_only
        self._ipv4_only = ipv4_only
        self._max_num_proxies = max_num_proxies
        self._selected = None
        self._verbose = verbose

        self.rotate()

    @property
    def blocked(self) -> typing.Set[str]:
        return self._blocked

    @property
    def available(self) -> typing.Set[str]:
        return self._available

    @property
    def num_available(self) -> int:
        return len(self._available)

    @property
    def selected(self) -> str:
        return self._selected

    def rotate(self) -> None:
        if self._selected is not None:
            self._blocked.add(self._selected)

        self._download_and_pop()

    def _is_valid_proxy(self, address: str, anonymity: str, https_support: str) -> bool:
        if self._elite_only:
            if anonymity != "elite proxy":
                return False

        if self._https_only:
            if https_support != "yes":
                return False

        if self._ipv4_only:
            if not is_valid_ipv4(address):
                return False

        return True

    def _download_and_pop(self) -> None:
        if self.num_available == 0:
            self._download()

        if self.num_available == 0:
            self._selected = None
            return

        self._selected = self._available.pop()

    def _download(self):
        if self._max_num_proxies == 0:
            return

        if self._verbose:
            message = "Downloading proxies..."
            print(message)

        self._available.clear()

        for endpoint in _URL_freexies:
            response = requests.get(endpoint) 
            soup = BS(response.content, "html5lib")

            addresses = soup.findAll("td")[::8]
            ports = soup.findAll("td")[1::8]
            anonymities = soup.findAll("td")[4::8]
            supports_https = soup.findAll("td")[6::8]

            available = list(zip(
                map(lambda x: x.text.lower(), addresses),
                map(lambda x: x.text.lower(), ports),
                map(lambda x: x.text.lower(), anonymities),
                map(lambda x: x.text.lower(), supports_https)
            ))

            available = [
                f"{address}:{port}" for address, port, anonymity, https_support in available
                if self._is_valid_proxy(address, anonymity, https_support)
            ]

            self._available = self._available | set(available)

        # It removes blocked proxies
        self._available = self._available - self._blocked

        abundance = self.num_available > self._max_num_proxies

        if abundance and self._max_num_proxies > -1:
            # FIXME: This conversion is highly inefficient
            self._available = tuple(self._available)
            self._available = random.sample(self._available, self._max_num_proxies)
            self._available = set(self._available)
