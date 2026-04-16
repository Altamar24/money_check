import os

from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'

    def ready(self):
        # Django's dev server starts the process twice (reloader + worker).
        # RUN_MAIN=true is only set in the actual worker process, so we start
        # the bot thread only there to avoid two competing polling loops.
        if os.environ.get('RUN_MAIN') != 'true':
            return
        from .bot import start_bot_thread
        start_bot_thread()
