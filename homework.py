import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()
PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
API_TELEGRAM = "5816632124:AAGHhJ9zuXsCGqTkOxCmtKF-Xo1RhCxHu4I"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания."
}

logging.basicConfig(
    level=logging.DEBUG,
    filename="main.log",
    filemode="w",
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


def check_tokens():
    """Доступность Практикум и Телеграмм токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщения пользователю в Telegram чат."""
    try:
        logging.debug("Началась отправка сообщения в Telegram")
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug("Удачная отправка сообщения в Telegram")

    except Exception as error:
        logging.error(
            f"{error} Сбой при отправке статуса проверки в Telegram."
        )


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    try:
        logging.debug("Началася запрос к API")
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={"from_date": 1549962000}
        )

    except Exception as error:
        raise Exception(f"{error} Эндпоинт недоступен")

    if response.status_code != HTTPStatus.OK:
        raise TypeError("Передано что-то неожиданное для сервиса")

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise TypeError("Запрос с недействительным или некорректным токеном")
    return response.json()


def check_response(response):
    """Ответ API на соответствие документации."""
    homeworks = response.get("homeworks")
    if not isinstance(response, dict):
        raise TypeError("Тип 'response' не словарь")

    if "homeworks" not in response:
        raise KeyError("Ключа 'homeworks' нет в словаре response")

    if "current_date" not in response:
        raise KeyError("Ключа 'current_date' нет в словаре response")

    if not isinstance(homeworks, list):
        raise TypeError("Тип переменной 'homeworks' не список")
    return homeworks


def parse_status(homeworks):
    """Извлечение информации о домашней работе из статуса этой работы."""
    homework_name = homeworks.get("homework_name")
    homework_status = homeworks.get("status")
    if "homework_name" not in homeworks:
        raise KeyError("Ключа 'homework_name' нет в словаре response")
    if "status" not in homeworks:
        raise KeyError("Ключа 'status' нет в словаре response")
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(
            "Ключа 'homework_status' нет в "
            "словаре response 'HOMEWORK_VERDICTS'"
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f"Изменился статус проверки работы '{homework_name}'. {verdict}"


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            "отсутствие обязательных переменных окружения "
            "во время запуска бота."
        )
        message = "Отсутствие обязательных переменных окружения "
        "во время запуска бота"
        logging.critical(message)
        sys.exit(message)
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    except telegram.error.TelegramError as error:
        logging.error(error)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get("current_date", timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.info("Нет домашней работы")

        except Exception as error:
            logging.error(f"Сбой в работе программы: {error}")
            message = f"Сбой в работе программы: {error}"
            send_message(bot, message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
