from datetime import datetime, timezone

from config.settings import logger


def get_last_data(share):
    """Заглушка вместо Tinkoff Invest API: возвращает фиктивную цену."""
    logger.info(f"[STUB] Get last data for share with id {share.id}")
    return [100.0, datetime.now(timezone.utc)]
