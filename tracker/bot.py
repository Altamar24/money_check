"""
Telegram bot polling loop — runs as a daemon thread inside Django.
Started automatically by TrackerConfig.ready() when DEBUG=True,
or when TELEGRAM_BOT_TOKEN is set.

The bot listens for /start auth_<token> messages and marks the
corresponding TelegramLoginToken as verified so the browser can
complete the login flow.
"""
import logging
import os
import threading
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_thread: threading.Thread | None = None


def start_bot_thread() -> None:
    """Start the polling thread once. Safe to call multiple times."""
    global _thread
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not bot_token:
        logger.info('TELEGRAM_BOT_TOKEN not set — Telegram bot not started.')
        return
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_poll_loop, daemon=True, name='telegram-bot-poll')
    _thread.start()
    logger.info('Telegram bot polling thread started.')


def _poll_loop() -> None:
    from tracker.models import TelegramLoginToken  # late import to avoid AppRegistry issues

    bot_token = settings.TELEGRAM_BOT_TOKEN
    api = f'https://api.telegram.org/bot{bot_token}'
    offset = 0

    while True:
        try:
            resp = requests.get(
                f'{api}/getUpdates',
                params={'offset': offset, 'timeout': 30},
                timeout=35,
            )
            data = resp.json()
        except Exception as exc:
            logger.warning('Bot getUpdates error: %s', exc)
            time.sleep(5)
            continue

        for update in data.get('result', []):
            offset = update['update_id'] + 1
            try:
                _process_update(api, update, TelegramLoginToken)
            except Exception as exc:
                logger.exception('Error processing update %s: %s', update.get('update_id'), exc)


def _process_update(api, update, TokenModel) -> None:
    message = update.get('message') or {}
    text = (message.get('text') or '').strip()
    from_user = message.get('from') or {}
    telegram_id = from_user.get('id')
    chat_id = (message.get('chat') or {}).get('id')

    if not (text and telegram_id and chat_id):
        return

    # Handles both "/start auth_TOKEN" and "/start@botname auth_TOKEN"
    parts = text.split()
    if parts and parts[0].startswith('/start'):
        payload = parts[1] if len(parts) > 1 else ''
        if payload.startswith('auth_'):
            token_value = payload[len('auth_'):]
            _handle_auth(api, token_value, telegram_id, chat_id, TokenModel)


def _handle_auth(api, token_value, telegram_id, chat_id, TokenModel) -> None:
    try:
        token_obj = TokenModel.objects.get(token=token_value, is_verified=False)
    except TokenModel.DoesNotExist:
        _send(api, chat_id, '❌ Ссылка недействительна или уже использована.')
        return

    if token_obj.is_expired():
        token_obj.delete()
        _send(api, chat_id, '❌ Ссылка устарела. Обновите страницу и попробуйте снова.')
        return

    token_obj.telegram_id = telegram_id
    token_obj.is_verified = True
    token_obj.save(update_fields=['telegram_id', 'is_verified'])
    _send(api, chat_id, '✅ Вы вошли в Money Check! Вернитесь в браузер.')


def _send(api, chat_id, text) -> None:
    try:
        requests.post(f'{api}/sendMessage', json={'chat_id': chat_id, 'text': text}, timeout=10)
    except Exception:
        pass
