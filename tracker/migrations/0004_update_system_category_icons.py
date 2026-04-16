from django.db import migrations

# Maps category name → Tabler icon name (ASCII, used as ti-{name} class)
ICON_MAP = {
    'Еда и рестораны': 'tools-kitchen-2',
    'Продукты':        'shopping-cart',
    'Транспорт':       'bus',
    'Топливо':         'gas-station',
    'Жильё / аренда':  'home',
    'Коммунальные':    'bulb',
    'Здоровье':        'pill',
    'Одежда':          'hanger',
    'Развлечения':     'movie',
    'Подписки':        'device-mobile',
    'Образование':     'book',
    'Прочее':          'box',
    'Зарплата':        'briefcase',
    'Прочий доход':    'coins',
}


def update_icons(apps, schema_editor):
    Category = apps.get_model('tracker', 'Category')
    for name, icon in ICON_MAP.items():
        Category.objects.filter(name=name, user__isnull=True).update(icon=icon)


def revert_icons(apps, schema_editor):
    # Revert to original emoji
    original = {
        'Еда и рестораны': '🍔',
        'Продукты':        '🛒',
        'Транспорт':       '🚌',
        'Топливо':         '⛽',
        'Жильё / аренда':  '🏠',
        'Коммунальные':    '💡',
        'Здоровье':        '💊',
        'Одежда':          '👕',
        'Развлечения':     '🎬',
        'Подписки':        '📱',
        'Образование':     '📚',
        'Прочее':          '📦',
        'Зарплата':        '💼',
        'Прочий доход':    '💰',
    }
    Category = apps.get_model('tracker', 'Category')
    for name, icon in original.items():
        Category.objects.filter(name=name, user__isnull=True).update(icon=icon)


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_alter_category_icon_length'),
    ]

    operations = [
        migrations.RunPython(update_icons, revert_icons),
    ]
