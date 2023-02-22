import cloudscraper
import sys

sys.path.insert(0, '/usr/lib/chromium-browser/chromedriver')

from selenium import webdriver

from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.proxy import ProxyType

import random
import requests
import time
import threading

from bs4 import BeautifulSoup as bs

from joblib import delayed
from joblib import Parallel

from typing import *

# Module imports
from proxyrotator import ProxyRotator


class CFWebScraper():
    _URL_og_address: str = 'https://httpbin.org/ip'

    _cfscraper: cloudscraper.CloudScraper
    _drivers: List[webdriver.chrome.webdriver.WebDriver]
    _keep_proxy: bool
    _og_address: str
    _proxyrotator: ProxyRotator

    def __init__(self, ndrivers: int = 4,
                 nproxies: int = -1):
        self._init_cfscraper()
        self._init_drivers(ndrivers)
        
        self._keep_proxy   = False
        self._og_address   = self._get_og_address()
        self._proxyrotator = ProxyRotator(nproxies)

    @property
    def og_address(self) -> str:
        return self._og_address

    @property
    def uses_proxy(self) -> bool:
        return self._proxyrotator.nproxies > 0

    def data_extraction(self, url: str,
                        ntries: int = 10,
                        tsleep: int = 3,
                        s: float = 0.33) -> Tuple[int, Any]:
        """
        Scrape a Cloudfare-protected URL by either:
          a) Using the original IP address with probability `s`
          b) Using the cached IP address proxy
          c) Using `ntries` IP address proxies
        """
        # a
        if random.random() < s:
            res = self._cfscraper.get(url)

            if res.status_code == 200:
                return res.status_code, res

        if not self.uses_proxy:
            return 500, None

        for _ in range(ntries):
            # c
            if not self._keep_proxy:
                self._proxyrotator.renew()

            res = self._cfscraper.get(
                url, proxies=self._proxyrotator
                                 .proxies)
            
            # b
            if res.status_code == 200:
                self._keep_proxy = True
                break

            self._keep_proxy = False
            self._proxyrotator.block()

            time.sleep(tsleep)
            
        if res.status_code != 200:
            return res.status_code, None

        return res.status_code, res

    def data_processing(self, res: Any,
                        treeproc_func: Callable,
                        dataproc_func: Callable,
                        driver_func: Callable) -> Any:
        # a. HTML tree processing
        reslist = treeproc_func(res)

        # b. Data processing
        if dataproc_func is not None:
            reslist = Parallel(n_jobs=-1)(
                delayed(dataproc_func)(_res)
                for _res in reslist)
        
        # c. Dynamic processing
        if driver_func is not None:
            self._drivers = self._make_drivers()

        drivers  = {}
        ndrivers = len(self._drivers)

        def scheduling(driver_func: Callable,
                       *args: Dict):
            t = threading.current_thread().name

            try:
                driver = drivers[t]
            except KeyError:
                drivers[t] = self._drivers.pop()
                driver = drivers[t]

            return driver_func(driver, args)

        reslist = Parallel(n_jobs=len(self._drivers),
                           backend="threading")(
            delayed(scheduling)
                (driver_func, _res)
            for _res in reslist)

        self._init_drivers(ndrivers)

        return reslist

    def scrape(self, url: str,
               ntries: int = 10,
               tsleep: int = 3,
               **kwargs) -> Tuple[int, Any]:
        status_code, res = \
            self.data_extraction(url, 
                                 ntries, 
                                 tsleep)

        if status_code != 200:
            return status_code, None
        
        treeproc_func = kwargs.get('treeproc', None)

        if treeproc_func is None:
            return 200, res

        try:
            if len(self._drivers) == 0:
                driver_func = None

            dataproc_func = kwargs.get('dataproc', None)
            driver_func   = kwargs.get('driver', None)

            reslist = \
                self.data_processing(res,
                                     treeproc_func,
                                     dataproc_func,
                                     driver_func) 

            return 200, reslist
        except Exception:
            return 500, None

    @staticmethod
    def _get_cfscraper_options() -> Dict[str, Any]:
        return {'browser': 'chrome',
                'platform': 'linux',
                'desktop': True}

    @staticmethod
    def _get_driver_options() -> webdriver.chrome.options.Options:
        options = webdriver.ChromeOptions()

        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        return options

    def _get_og_address(self):
        response = requests.get(self._URL_og_address)
        assert response.status_code == 200

        return response.json()['origin']

    def _init_cfscraper(self):
        self._cfscraper = \
                cloudscraper.create_scraper(
            browser=self._get_cfscraper_options()
        )

    def _init_drivers(self, n: int):
        self._drivers = [None]*n

    def _make_drivers(self):
        capabilities = None
        options = self._get_driver_options()

        if self.uses_proxy \
                and self._keep_proxy:
            # Configure proxy options
            proxy = Proxy()
            proxy.proxy_type = ProxyType.MANUAL

            # IP address and port
            proxy.http_proxy  = self._proxyrotator.proxy
            proxy.socks_proxy = self._proxyrotator.proxy
            proxy.ssl_proxy   = self._proxyrotator.proxy

            # Configure capabilities 
            capabilities = webdriver.DesiredCapabilities.CHROME
            proxy.add_to_capabilities(capabilities)

        self._drivers = [webdriver.Chrome('chromedriver',
                                          options=options,
                                          desired_capabilities=capabilities)
                         for _ in range(len(self._drivers))]
