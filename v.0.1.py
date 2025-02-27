from datetime import date
import csv
import requests
import telebot

# авторизация для запросов к Jira API
headers = {
    'Authorization': 'Bearer xxx'  # замени на свой токен
}

# URL для API-запросов к Jira
url = 'https://jira.croc.ru/rest/api/2/search'

# словарь с ценами для различных компонентов
component_prices = {
    'Восстановление доступа (Сброс пароля)': 40,
    'Консультация нестандартная': 320,
    'Консультация стандартная': 150,
    'Отправка уведомлений (массовая)': 150,
    'Отправка уведомления одному заказчику (точечная рассылка)': 90,
    'Работа с внутренними проектами': 130,
    'Работа с инфраструктурой заказчиков': 350,
    'Сдача смены': 15,
    'Сентри биллинг': 30,
    'Создание и работа с отчетами': 130,
    'Создание ресурсов в биллинге': 150,
    'Создание, удаление пользователей': 55,
    'Уведомление заказчика об алерте звонком': 40,
    'Увеличение лимитов для заказчика': 70,
    'Эскалация алерта 1го приоритета на ГСИ': 15,
    'Эскалация алерта 2го или 3го приоритета на ГСИ': 10,
    'Эскалация алерта в чат заказчику': 10,
    'Эскалация алерта в чат заказчику + действия после ответа': 15,
    'Эскалация алерта и в чат заказчику и в почту': 15,
    'Эскалация в Jira + сторонняя тикетная система': 30,
    'Эскалация заявок от заказчика на ГСИ': 35,
    'Эскалация менеджеру проекта': 50,
    'Эскалация на внешние группы': 30,
    'Эскалация Облако': 60,
    'Эскалация подрядчику в почте': 40
}

# создаем объект бота с токеном
bot = telebot.TeleBot('xxx:xxx')     # замени на свой токен

# функция для вычисления текущего квартала
def get_quarter_dates():
    today = date.today()
    year = today.year
    if today.month in [1, 2, 3]:
        return f"{year}-01-01", f"{year}-03-31"
    elif today.month in [4, 5, 6]:
        return f"{year}-04-01", f"{year}-06-30"
    elif today.month in [7, 8, 9]:
        return f"{year}-07-01", f"{year}-09-30"
    else:
        return f"{year}-10-01", f"{year}-12-31"

# обработчик команд для бота
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text == '/start':
        bot.send_message(message.from_user.id, "Привет!\nЯ бот для подсчета квартальной премии.\nИспользуйте команду /bonus для просмотра результатов, а /update для обновления выгрузки.")
    elif message.text == '/update':
        bot.send_message(message.from_user.id, "Обновляю выгрузку...\nДанный процесс завершится в фоновом режиме.")

        # Получение дат текущего квартала
        start_date, end_date = get_quarter_dates()
        jql_query = f'project = CS AND issuetype in ("Service Request", "Техническая поддержка") ' \
                    f'AND status in (Resolved, Closed) AND resolution = Fixed ' \
                    f'AND resolved >= {start_date} AND resolved <= {end_date} ORDER BY created ASC'

        # список для хранения всех тикетов и начальный индекс для постраничной загрузки ч
        issues = []
        start_at = 0

        # запрашиваем тикеты из Jira
        while True:
            response = requests.get(url, params={'jql': jql_query, 'startAt': start_at}, headers=headers)
            if response.status_code == 200:
                data = response.json()
                issues.extend(data['issues'])
                total_issues = data['total']
                if len(issues) >= total_issues:
                    break
                start_at += len(data['issues'])
            else:
                print(f"Failed to fetch issues. Status code: {response.status_code}")
                break

        # сохраняем данные в CSV-файл
        with open('L1.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            writer.writerow(['Assignee', 'Components'])

            for issue in issues:
                assignee = issue['fields']['assignee']['displayName'] if issue['fields']['assignee'] else ''
                components = ', '.join(component['name'] for component in issue['fields']['components'])
                writer.writerow([assignee, components])

    elif message.text == '/bonus':
        bonus = ''
        engineer_totals = {}

        # читаем данные из CSV-файла
        with open('L1.csv', 'r', newline='', encoding='utf-8') as file:
            csv_reader = csv.reader(file, delimiter=',')
            for row in csv_reader:
                Assignee = row[0]
                if Assignee not in engineer_totals:
                    engineer_totals[Assignee] = 0
                for component in row[1:]:
                    engineer_totals[Assignee] += component_prices.get(component, 0)

        engineer_totals = {k: v for k, v in sorted(
            engineer_totals.items(), key=lambda item: item[1], reverse=True) if v != 0}

        for engineer, total in engineer_totals.items():
            bonus += (f"{engineer}: {total}₽\n")
        bot.send_message(message.from_user.id, bonus)
    else:
        bot.send_message(message.from_user.id, 'Напиши /start')

# Запускаем бота
bot.polling(none_stop=True, interval=0)
