from django.db import migrations

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


def seed_categories(apps, schema_editor):
    Category = apps.get_model('tracker', 'Category')
    for name, icon, color, tx_type, order in SYSTEM_CATEGORIES:
        Category.objects.get_or_create(
            name=name,
            user=None,
            defaults={
                'icon': icon,
                'color': color,
                'transaction_type': tx_type,
                'order': order,
                'is_hidden': False,
            },
        )


def unseed_categories(apps, schema_editor):
    Category = apps.get_model('tracker', 'Category')
    Category.objects.filter(user__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
