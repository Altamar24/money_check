import uuid
from decimal import Decimal

from django.conf import settings

PRICE = Decimal('99.00')
CURRENCY = 'RUB'


def _configure():
    from yookassa import Configuration
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def create_first_payment(user, return_url):
    from yookassa import Payment as YKPayment
    _configure()
    return YKPayment.create({
        'amount': {'value': str(PRICE), 'currency': CURRENCY},
        'confirmation': {
            'type': 'redirect',
            'return_url': return_url,
        },
        'capture': True,
        'save_payment_method': True,
        'description': 'Подписка MoneyCheck — 1 месяц',
        'metadata': {'user_id': str(user.id)},
    }, str(uuid.uuid4()))


def create_renewal_payment(user, payment_method_id):
    from yookassa import Payment as YKPayment
    _configure()
    return YKPayment.create({
        'amount': {'value': str(PRICE), 'currency': CURRENCY},
        'capture': True,
        'payment_method_id': payment_method_id,
        'description': 'Подписка MoneyCheck — автопродление',
        'metadata': {'user_id': str(user.id), 'renewal': 'true'},
    }, str(uuid.uuid4()))
