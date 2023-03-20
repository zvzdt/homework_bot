import logging
import requests
import time
import sys
from http import HTTPStatus

import os
import telegram

from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PT')
TELEGRAM_TOKEN = os.getenv('TT')
TELEGRAM_CHAT_ID = os.getenv('TCI')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError:
        logger.error('Ошибака, сообщение не отправлено')
    else:
        logger.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API."""
    timestamp = int(time.time())
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception:
        raise telegram.error.NetworkError('Эндпоинт недоступен')
    if response.status_code != HTTPStatus.OK:
        raise requests.exceptions.HTTPError(
            'Получен неправильный код ответа API'
        )
    return response.json()


def check_response(response):
    """Ответ API на соответствие документации."""
    if not isinstance(response, dict):
        error_msg = 'неправильный тип данных'
        raise TypeError(error_msg)
    if 'homeworks' not in response or 'current_date' not in response:
        error_msg = 'неправильный ключ'
        raise KeyError(error_msg)
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        error_msg = 'нет такого ключа'
        raise KeyError(error_msg)
    if 'status' not in homework:
        error_msg = 'нет такого ключа'
        raise KeyError(error_msg)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('неизвестный статус')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        error_msg = 'Отсутствуют необходиме переменные окружения'
        logger.critical(error_msg)
        sys.exit(error_msg)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    prev_message = ''

    while True:
        logger.info('Бот запущен')
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logger.info('статус проверки не измениля')
            else:
                message = parse_status(homeworks[0])
                if message != prev_message:
                    send_message(bot, message)
                    prev_message = message
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
