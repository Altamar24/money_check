import datetime
import logging
import threading
import time
import uuid
from decimal import Decimal

logger = logging.getLogger(__name__)

RENEW_AHEAD_HOURS = 24


def _process_renewals():
    from django.utils import timezone
    from .models import Payment, Subscription

    now = timezone.now()
    window_end = now + datetime.timedelta(hours=RENEW_AHEAD_HOURS)

    subs = (
        Subscription.objects
        .filter(status='active', expires_at__gt=now, expires_at__lte=window_end)
        .exclude(payment_method_id='')
        .select_related('user')
    )

    for sub in subs:
        already = Payment.objects.filter(
            user=sub.user,
            is_auto_renewal=True,
            created_at__gte=now - datetime.timedelta(hours=24),
        ).exists()
        if already:
            continue
        try:
            _charge_renewal(sub)
        except Exception:
            logger.exception('Renewal failed for user_id=%s', sub.user_id)


def _charge_renewal(sub):
    from django.conf import settings
    from yookassa import Configuration, Payment as YKPayment
    from .models import Payment

    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    yk_payment = YKPayment.create({
        'amount': {'value': '99.00', 'currency': 'RUB'},
        'capture': True,
        'payment_method_id': sub.payment_method_id,
        'description': 'Подписка MoneyCheck — автопродление',
        'metadata': {'user_id': str(sub.user_id), 'renewal': 'true'},
    }, str(uuid.uuid4()))

    Payment.objects.create(
        user=sub.user,
        yookassa_payment_id=yk_payment.id,
        amount=Decimal('99.00'),
        status='pending',
        is_auto_renewal=True,
    )
    logger.info('Renewal payment %s queued for user_id=%s', yk_payment.id, sub.user_id)


def _loop():
    time.sleep(30)
    while True:
        try:
            _process_renewals()
        except Exception:
            logger.exception('Renewal loop error')
        time.sleep(3600)


def start_renewal_thread():
    t = threading.Thread(target=_loop, name='renewal-worker', daemon=True)
    t.start()
    logger.info('Renewal worker started.')
