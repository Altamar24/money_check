"""
Management command: create_recurring

Creates overdue recurring transactions.
Run via cron once daily:
    0 0 * * * /path/to/venv/bin/python /path/to/manage.py create_recurring
"""

import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from tracker.models import RecurringRule, Transaction


class Command(BaseCommand):
    help = 'Create all overdue recurring transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = datetime.date.today()
        created_count = 0

        rules = RecurringRule.objects.filter(
            is_active=True, next_date__lte=today
        ).select_related('user', 'category')

        for rule in rules:
            # Create all missed occurrences
            current_date = rule.next_date
            while current_date <= today:
                if not dry_run:
                    with transaction.atomic():
                        Transaction.objects.create(
                            user=rule.user,
                            transaction_type=rule.transaction_type,
                            amount=rule.amount,
                            category=rule.category,
                            date=current_date,
                            note=rule.note,
                            is_recurring=True,
                            recurring_rule=rule,
                        )
                    self.stdout.write(
                        f'  Created: {rule.user.email} | {current_date} | '
                        f'{rule.amount} | {rule.category}'
                    )
                else:
                    self.stdout.write(
                        f'  [dry-run] Would create: {rule.user.email} | {current_date} | '
                        f'{rule.amount} | {rule.category}'
                    )

                created_count += 1
                current_date = _next_date(current_date, rule)

            if not dry_run:
                rule.next_date = current_date
                rule.save(update_fields=['next_date'])

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. {"Would create" if dry_run else "Created"} {created_count} transaction(s).'
            )
        )


def _next_date(from_date: datetime.date, rule: RecurringRule) -> datetime.date:
    if rule.interval == 'monthly':
        month = from_date.month + 1
        year = from_date.year
        if month > 12:
            month = 1
            year += 1
        day = rule.day_of_month or from_date.day
        day = min(day, 28)
        return datetime.date(year, month, day)
    else:  # weekly
        return from_date + datetime.timedelta(weeks=1)
