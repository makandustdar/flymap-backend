from __future__ import annotations

from django.core.management.base import BaseCommand

from sites.models import FlyingSite
from sites.services.forecast import ingest_all_active, ingest_site


class Command(BaseCommand):
    help = "Ingest Windy forecasts for active (or one) flying site(s)."

    def add_arguments(self, parser):
        parser.add_argument("--site", type=str, default=None, help="Site id")

    def handle(self, *args, **options):
        site_id = options.get("site")
        if site_id:
            try:
                site = FlyingSite.objects.get(pk=site_id)
            except FlyingSite.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Unknown site: {site_id}"))
                return
            summary = ingest_site(site)
            self.stdout.write(self.style.SUCCESS(str(summary)))
            return

        results = ingest_all_active()
        for r in results:
            self.stdout.write(str(r))
        self.stdout.write(self.style.SUCCESS(f"Ingested {len(results)} site(s)"))
