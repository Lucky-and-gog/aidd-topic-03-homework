from django.core.management.base import BaseCommand

from dashboard.models import Share

SAMPLE_SHARES = [
    {
        "figi": "BBG004730N88",
        "isin": "RU0009029540",
        "name": "Сбербанк",
        "ticker": "SBER",
        "currency": "rub",
        "uid": "e6123145-9665-43e0-8413-cd61b8aa9b13",
    },
    {
        "figi": "BBG004730RP0",
        "isin": "RU0007661625",
        "name": "Газпром",
        "ticker": "GAZP",
        "currency": "rub",
        "uid": "962e2a95-02a9-4171-abd7-aa198dbe643a",
    },
    {
        "figi": "BBG000B9XRY4",
        "isin": "US0378331005",
        "name": "Apple",
        "ticker": "AAPL",
        "currency": "usd",
        "uid": "a9eb4238-eba9-488c-b102-b6140fd08e38",
    },
]


class Command(BaseCommand):
    help = "Add sample shares to DB (Tinkoff API stub)"

    def handle(self, *args, **options):
        for share in SAMPLE_SHARES:
            obj, created = Share.objects.get_or_create(
                figi=share["figi"], defaults=share
            )
            status = "created" if created else "already exists"
            self.stdout.write(f"{share['ticker']}: {status}")
