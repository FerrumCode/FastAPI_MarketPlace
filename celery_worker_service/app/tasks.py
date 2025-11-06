from __future__ import annotations
from decimal import Decimal
from prometheus_client import Counter, Histogram, start_http_server
from sqlalchemy import select, update
from .celery_app import celery_app
from .services import rates as rates_service
from .services.delivery import calc_delivery
from .models.order import Order
from .db import SessionLocal
from .logging_conf import setup_logging

log = setup_logging()

# Метрики Prometheus
start_http_server(9101)  # /metrics для воркера
TASKS_TOTAL = Counter("celery_tasks_total", "Total executed celery tasks", ["task"])
TASK_DURATION = Histogram("task_duration_seconds", "Task duration seconds", ["task"])

def _get_order(session, order_id):
    return session.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()

@celery_app.task(name="app.tasks.fetch_exchange_rates")
def fetch_exchange_rates():
    with TASK_DURATION.labels(task="fetch_exchange_rates").time():
        TASKS_TOTAL.labels(task="fetch_exchange_rates").inc()
        r = rates_service.refresh_rates_sync()
        log.info("rates_refreshed", rates=r)
        return r

@celery_app.task(name="app.tasks.process_order_created")
def process_order_created(order_id: str):
    with TASK_DURATION.labels(task="process_order_created").time():
        TASKS_TOTAL.labels(task="process_order_created").inc()

        # 1) гарантируем, что курсы есть в кэше
        r = rates_service.get_rates()
        log.info("rates_used", usd_rub=str(r["USD_RUB"]), eur_rub=str(r["EUR_RUB"]))

        # 2) читаем заказ и считаем доставку
        with SessionLocal() as session:
            order = _get_order(session, order_id)
            if not order:
                log.error("order_not_found", order_id=order_id)
                return {"ok": False, "reason": "order_not_found"}

            cart_price_rub = Decimal(order.cart_price)  # предположим cart_price уже в RUB
            delivery = calc_delivery(cart_price_rub)
            total = cart_price_rub + delivery

            session.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(delivery_price=delivery, total_price=total, status="processing")
            )
            session.commit()

            log.info("order_updated", order_id=order_id, delivery=str(delivery), total=str(total))

        # 3) при желании можно послать событие ORDER_UPDATED
        try:
            from .services.kafka_producer import send_order_updated
            send_order_updated(order_id, status="processing")
        except Exception as e:
            log.error("kafka_produce_failed", error=str(e))

        return {"ok": True, "order_id": order_id}
