"""
base_engine.py — Resilient Base HTTP Scraper Client
company_info / engines
"""

from __future__ import annotations
import time
import random
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
from company_info.config import USER_AGENTS, DEFAULT_HEADERS, DEFAULT_TIMEOUT_SEC, DEFAULT_MAX_RETRIES


class BaseScraper:
    """
    Base HTTP client with automated header rotation, retry with exponential backoff,
    thread-isolated sessions, and rate limit protection.
    """

    def __init__(
        self,
        timeout: int = 6,
        max_retries: int = 2,
        rate_limit_delay: float = 0.25,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        self._local = threading.local()

    def _get_session(self) -> requests.Session:
        """Retrieve or initialize thread-local Session with connection pooling."""
        if not hasattr(self._local, "session"):
            session = requests.Session()
            adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=Retry(total=1, backoff_factor=0.2))
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            self._local.session = session
            self._local.last_request_time = 0.0
        return self._local.session

    def _throttle(self) -> None:
        """Enforce rate limit delay per thread."""
        self._get_session()
        last_t = getattr(self._local, "last_request_time", 0.0)
        elapsed = time.time() - last_t
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._local.last_request_time = time.time()

    def get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Construct request headers with a randomly selected modern desktop user agent."""
        headers = dict(DEFAULT_HEADERS)
        headers["User-Agent"] = random.choice(USER_AGENTS)
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def fetch_get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Optional[requests.Response]:
        """Execute a robust GET request with retries and exponential backoff."""
        self._throttle()
        session = self._get_session()
        for attempt in range(1, self.max_retries + 1):
            try:
                headers = self.get_headers(custom_headers)
                resp = session.get(url, params=params, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in (429, 503):
                    # Rate limited or temporarily unavailable -> backoff
                    sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                    time.sleep(sleep_time)
                else:
                    return resp
            except Exception:
                if attempt == self.max_retries:
                    return None
                time.sleep(0.5 * attempt)
        return None

    def fetch_post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Optional[requests.Response]:
        """Execute a robust POST request with retries."""
        self._throttle()
        session = self._get_session()
        for attempt in range(1, self.max_retries + 1):
            try:
                headers = self.get_headers(custom_headers)
                resp = session.post(url, data=data, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in (429, 503):
                    time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))
                else:
                    return resp
            except Exception:
                if attempt == self.max_retries:
                    return None
                time.sleep(0.5 * attempt)
        return None
