from django.db import models
from django.contrib.auth.models import User


SYSTEM_CATEGORIES = [
    # (name, icon, color, transaction_type, order)
    ('Еда и рестораны', '🍔', '#f59e0b', 'expense', 1),
    ('Продукты', '🛒', '#10b981', 'expense', 2),
    ('Транспорт', '🚌', '#3b82f6', 'expense', 3),
    ('Топливо', '⛽', '#6366f1', 'expense', 4),
    ('Жильё / аренда', '🏠', '#ec4899', 'expense', 5),
    ('Коммунальные', '💡', '#f97316', 'expense', 6),
    ('Здоровье', '💊', '#ef4444', 'expense', 7),
    ('Одежда', '👕', '#8b5cf6', 'expense', 8),
    ('Развлечения', '🎬', '#14b8a6', 'expense', 9),
    ('Подписки', '📱', '#0ea5e9', 'expense', 10),
    ('Образование', '📚', '#84cc16', 'expense', 11),
    ('Прочее', '📦', '#94a3b8', 'expense', 12),
    ('Зарплата', '💼', '#16a34a', 'income', 13),
    ('Прочий доход', '💰', '#22c55e', 'income', 14),
]

COLOR_CHOICES = [
    ('#ef4444', 'Красный'),
    ('#f97316', 'Оранжевый'),
    ('#f59e0b', 'Жёлтый'),
    ('#16a34a', 'Зелёный'),
    ('#0ea5e9', 'Синий'),
    ('#8b5cf6', 'Фиолетовый'),
    ('#ec4899', 'Розовый'),
    ('#94a3b8', 'Серый'),
]


class Category(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('expense', 'Расход'),
        ('income', 'Доход'),
        ('both', 'Оба'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='categories'
    )
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='box')
    color = models.CharField(max_length=7, default='#94a3b8')
    transaction_type = models.CharField(
        max_length=10, choices=TRANSACTION_TYPE_CHOICES, default='expense'
    )
    is_hidden = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'is_hidden']),
        ]
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name

    @property
    def is_system(self):
        return self.user_id is None


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('expense', 'Расход'),
        ('income', 'Доход'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='transactions'
    )
    date = models.DateField()
    note = models.CharField(max_length=500, blank=True, default='')
    is_recurring = models.BooleanField(default=False)
    recurring_rule = models.ForeignKey(
        'RecurringRule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'transaction_type']),
        ]
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'

    def __str__(self):
        return f'{self.get_transaction_type_display()} {self.amount} — {self.category}'


class RecurringRule(models.Model):
    INTERVAL_CHOICES = [
        ('monthly', 'Ежемесячно'),
        ('weekly', 'Еженедельно'),
    ]
    TRANSACTION_TYPE_CHOICES = [
        ('expense', 'Расход'),
        ('income', 'Доход'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_rules')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    note = models.CharField(max_length=500, blank=True, default='')
    interval = models.CharField(max_length=20, choices=INTERVAL_CHOICES)
    day_of_month = models.IntegerField(null=True, blank=True)  # 1-28, for monthly
    day_of_week = models.IntegerField(null=True, blank=True)   # 0-6, for weekly
    next_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['next_date']
        verbose_name = 'Повторяющееся правило'
        verbose_name_plural = 'Повторяющиеся правила'

    def __str__(self):
        return f'{self.get_interval_display()} — {self.amount} ({self.category})'


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    month = models.IntegerField()   # 1-12
    year = models.IntegerField()
    limit_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = [('user', 'year', 'month')]
        verbose_name = 'Бюджет'
        verbose_name_plural = 'Бюджеты'

    def __str__(self):
        return f'Бюджет {self.year}-{self.month:02d}: {self.limit_amount}'


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('expired', 'Истекла'),
        ('cancelled', 'Отменена'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='expired')
    expires_at = models.DateTimeField(null=True, blank=True)
    payment_method_id = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    @property
    def is_active(self):
        from django.utils import timezone
        return self.status == 'active' and bool(self.expires_at) and timezone.now() < self.expires_at

    def __str__(self):
        return f'{self.user} — {self.status}'


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('succeeded', 'Успешен'),
        ('cancelled', 'Отменён'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    yookassa_payment_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_auto_renewal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'

    def __str__(self):
        return f'{self.user} — {self.amount}₽ ({self.status})'


class TelegramLoginToken(models.Model):
    """One-time token for bot-based login flow."""
    token = models.CharField(max_length=64, unique=True)
    telegram_id = models.BigIntegerField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Токен входа Telegram'
        verbose_name_plural = 'Токены входа Telegram'

    def is_expired(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).total_seconds() > 300  # 5 минут


class TelegramProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='telegram_profile')
    telegram_id = models.BigIntegerField(unique=True)
    telegram_username = models.CharField(max_length=255, blank=True, null=True)
    telegram_first_name = models.CharField(max_length=255, blank=True, null=True)
    telegram_last_name = models.CharField(max_length=255, blank=True, null=True)
    telegram_photo_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram профиль"
        verbose_name_plural = "Telegram профили"

    def __str__(self):
        return f"{self.user.email} — @{self.telegram_username or self.telegram_id}"
