"""Measure an authorized workspace over HTTP using stdlib only."""

import argparse
import getpass
import http.cookiejar
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        parser.error("Supply an HTTP(S) application URL.")
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        parser.error("Plain HTTP is allowed only for local loopback.")
    email = input(f"Sign-in email for {base}: ").strip()
    password = getpass.getpass("Password (not printed or saved): ")
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    opener.open(base + "/accounts/login/", timeout=15).close()
    csrf = next(cookie.value for cookie in jar if cookie.name == "csrftoken")
    request = Request(
        base + "/accounts/login/",
        data=urlencode(
            {"username": email, "password": password, "csrfmiddlewaretoken": csrf}
        ).encode(),
        headers={"Referer": base + "/accounts/login/"},
    )
    with opener.open(request, timeout=15) as response:
        if "/dashboard/" not in response.url:
            raise SystemExit("Sign-in failed or the account is not verified/approved.")
    cookie_header = "; ".join(f"{cookie.name}={cookie.value}" for cookie in jar)

    def sample(index):
        path = ["/dashboard/", "/vault/", "/vault/?q=Scale"][index % 3]
        started = time.perf_counter()
        try:
            # Independent openers avoid shared mutable cookie-jar state.
            with build_opener().open(
                Request(base + path, headers={"Cookie": cookie_header}), timeout=20
            ) as response:
                response.read()
                status = response.status
        except Exception as exc:
            status = type(exc).__name__
        return status, time.perf_counter() - started

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 20))) as pool:
        results = list(pool.map(sample, range(max(1, min(args.requests, 1000)))))
    timings = sorted(duration for _, duration in results)
    counts = {
        str(status): sum(1 for result, _ in results if result == status) for status, _ in results
    }
    print(
        json.dumps(
            {
                "requests": len(results),
                "workers": args.workers,
                "status_counts": counts,
                "median_ms": round(statistics.median(timings) * 1000, 2),
                "p95_ms": round(timings[min(len(timings) - 1, int(len(timings) * 0.95))] * 1000, 2),
            },
            indent=2,
        )
    )
    if any(status != 200 for status, _ in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
