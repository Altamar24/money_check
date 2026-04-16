"""
Fallback management command for running the Telegram bot in production
(e.g. when not using Django's runserver).

Usage: python manage.py run_telegram_bot

In development with `runserver`, the bot starts automatically — this
command is not needed there.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run Telegram bot polling loop (not needed with runserver in dev)'

    def handle(self, *args, **options):
        from tracker.bot import _poll_loop
        self.stdout.write('Telegram bot polling started. Press Ctrl+C to stop.')
        _poll_loop()
