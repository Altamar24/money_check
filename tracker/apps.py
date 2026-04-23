import os

from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'

    def ready(self):
        import sys
        # Django dev server (runserver) starts twice: autoreloader parent + worker child.
        # RUN_MAIN=true only in the child — skip the parent to avoid two bot threads.
        # In Gunicorn RUN_MAIN is never set, so we always start there.
        is_reloader_parent = (
            'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true'
        )
        if is_reloader_parent:
            return
        from .bot import start_bot_thread
        start_bot_thread()
