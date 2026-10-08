from celery import Celery

from tg_bot.bot_settings import settings
from tg_bot.service.subscriptions import SEND_INTERVAL_MIN

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
    worker_pool="solo",
    beat_schedule={
        "send-subscriptions": {
            "task": "celery_app.tasks.send_subscriptions",
            "schedule": SEND_INTERVAL_MIN * 1.0,  # 1.0 - количество минут
            "options": {"expires": SEND_INTERVAL_MIN * 60 - 60},
        },
    },
)