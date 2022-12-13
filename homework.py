import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
API_TELEGRAM = '5816632124:AAGHhJ9zuXsCGqTkOxCmtKF-Xo1RhCxHu4I'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


def check_tokens():
    """Доступность Практикум и Телеграмм токенов."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def send_message(bot, message):
    """Отправка сообщения пользователю в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug('Удачная отправка сообщения в Telegram')

    except Exception as error:
        logging.error(
            f'{error} Сбой при отправке статуса проверки в Telegram.'
        )


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': 0}
        )

    except Exception as error:
        logging.error(f'{error} Эндпоинт недоступен')

    if response.status_code != HTTPStatus.OK:
        raise TypeError('Передано что-то неожиданное для сервиса')

    elif response.status_code == HTTPStatus.UNAUTHORIZED:
        logging.error('Запрос с недействительным или некорректным токеном')

    else:
        response = response.json()
        return response


def check_response(response):
    """ Ответ API на соответствие документации."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error('Нет ключа "homeworks" в словаре')

    if homeworks == []:
        logging.debug(
            'В "homeworks" нет данных.'
        )
        return send_message(
            telegram.Bot(token=TELEGRAM_TOKEN),
            'Пока нет данных о результате проверки'
        )

    elif (
        type(response) != dict
        or type(homeworks) != list
        or type(homeworks[0]) != dict
    ):
        logging.error('Неожиданный ответ API')
        raise TypeError('Неожиданный ответ API')

    else:
        return parse_status(homeworks[0])


def parse_status(homework):
    """Извлечение информации о домашней работе из статуса этой работы."""
    for status, verdict in HOMEWORK_VERDICTS.items():
        try:
            homework_name = homework['homework_name']
        except KeyError:
            raise KeyError('Неверный ключ "homework_name"')
        if status == homework.get('status'):
            return (f'Изменился статус проверки работы "{homework_name}".'
                    f'{verdict}')
        if homework.get('status') not in HOMEWORK_VERDICTS:
            raise KeyError('Такого статуса нет')


def main():
    """Основная логика работы бота."""
    if check_tokens() is True:
        try:
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
        except telegram.error.TelegramError as error:
            logging.error(error)
        timestamp = int(time.time())
        while True:
            try:
                homeworks = get_api_answer(timestamp)
                message = check_response(homeworks)
                send_message(bot, message)
                time.sleep(RETRY_PERIOD)

            except Exception as error:
                logging.error(f'Сбой в работе программы: {error}')
                time.sleep(RETRY_PERIOD)
    else:
        logging.critical(
            "отсутствие обязательных переменных окружения"
            "во время запуска бота."
        )


if __name__ == '__main__':
    main()
