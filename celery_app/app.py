from celery import Celery

from tg_bot.bot_settings import settings
from tg_bot.service.subscriptions import TICK_SECONDS

celery = Celery(
    "rw_by",
    broker=settings.redis_url,
    include=["celery_app.tasks"],
)

celery.conf.update(
    timezone="Europe/Minsk",
    enable_utc=True,
    task_ignore_result=True,          # результаты нам пока не нужны
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_pool="solo",  # для windows
    beat_schedule={
        "send-subscriptions": {
            "task": "celery_app.tasks.send_subscriptions",
            "schedule": float(TICK_SECONDS),
            "options": {"expires": TICK_SECONDS - 10},
        },
    },
)
