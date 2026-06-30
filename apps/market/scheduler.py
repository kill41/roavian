import threading
import time
import logging
from django.conf import settings
from django.db import OperationalError

logger = logging.getLogger(__name__)


class PriceScheduler:
    _thread = None
    _stop = False

    @classmethod
    def start(cls, interval=60):
        if cls._thread and cls._thread.is_alive():
            cls.stop()
            cls._thread.join(timeout=5)
        cls._stop = False

        def run():
            time.sleep(5)
            from django.core.management import call_command
            for attempt in range(3):
                try:
                    call_command('fetch_prices')
                    break
                except OperationalError:
                    time.sleep(2)
            while not cls._stop:
                time.sleep(interval)
                for attempt in range(3):
                    try:
                        call_command('fetch_prices')
                        break
                    except OperationalError:
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f'Price fetch error: {e}')
                        break

        cls._thread = threading.Thread(target=run, daemon=True)
        cls._thread.start()
        logger.info('PriceScheduler started')

    @classmethod
    def stop(cls):
        cls._stop = True
        logger.info('PriceScheduler stopped')
