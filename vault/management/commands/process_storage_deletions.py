from django.core.management.base import BaseCommand

from vault.services import process_deletions


class Command(BaseCommand):
    help = "Retry queued private file removals. Schedule every minute."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        done, failed = process_deletions(max(1, min(options["limit"], 1000)))
        self.stdout.write(f"Removed {done} objects; {failed} pending retries.")
