from django.core.management.base import BaseCommand

# from tinkoff.invest import Client
# from config.settings import TINKOFF_TOKEN
from dashboard.models import Share


class Command(BaseCommand):
    help = "Add shares to DB (mock: no external API call)"

    def handle(self, *args, **options):
        self.stdout.write("Mock add_shares: Tinkoff API disabled, no shares loaded.")


