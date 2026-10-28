"""Isolated 10k-record render/concurrency benchmark; never touches your workspace DB."""

import json
import os
import secrets
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix="wefiles-benchmark-") as directory:
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
        os.environ["DATABASE_URL"] = f"sqlite:///{directory}/benchmark.sqlite3"
        os.environ["SECRET_KEY"] = secrets.token_urlsafe(64)
        import django

        django.setup()
        from django.contrib.auth import get_user_model
        from django.core.management import call_command
        from django.db import connections
        from django.test import Client
        from django.utils import timezone

        from vault.models import File, Folder

        call_command("migrate", verbosity=0)
        user = get_user_model().objects.create_user(
            "benchmark@example.test",
            secrets.token_urlsafe(20),
            username="benchmark",
            status="approved",
            email_verified_at=timezone.now(),
        )
        folders = Folder.objects.bulk_create(
            [Folder(name=f"Folder {i:03}", creator=user) for i in range(100)]
        )
        File.objects.bulk_create(
            [
                File(
                    owner=user,
                    name=f"Scale document {i:05}.txt",
                    folder=folders[i % 100] if i % 3 == 0 else None,
                    blob=f"benchmark/{i}",
                    size_bytes=100,
                    content_type="text/plain",
                )
                for i in range(10000)
            ],
            batch_size=500,
        )
        client = Client()
        client.force_login(user, backend="accounts.backends.EmailBackend")
        session_id = client.cookies["sessionid"].value
        paths = ["/dashboard/", "/vault/", "/vault/?q=Scale&sort=name"]
        for path in paths:
            assert client.get(path).status_code == 200

        def measure(index):
            local = Client()
            local.cookies["sessionid"] = session_id
            start = time.perf_counter()
            try:
                response = local.get(paths[index % len(paths)])
                return response.status_code, (time.perf_counter() - start) * 1000
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(measure, range(60)))
        durations = sorted(duration for _, duration in results)
        output = {
            "synthetic_file_records": 10000,
            "folders": 100,
            "requests": 60,
            "workers": 4,
            "status_200": sum(status == 200 for status, _ in results),
            "median_ms": round(statistics.median(durations), 2),
            "p95_ms": round(durations[56], 2),
            "max_ms": round(max(durations), 2),
            "scope": "Django test-client rendering with isolated SQLite; excludes network, browser assets, and physical downloads",
        }
        print(json.dumps(output, indent=2))
        connections.close_all()
        if output["status_200"] != 60:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
