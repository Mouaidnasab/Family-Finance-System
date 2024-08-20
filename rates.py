
import requests
import mysql.connector
from datetime import datetime, timedelta, date
import config


API_KEY = 'b633d9adb0214055a41643290080e479'
BASE_URL = 'https://openexchangerates.org/api/historical/'

def get_exchange_rates(date):
    url = f"{BASE_URL}{date}.json?app_id={API_KEY}&symbols=BGN,EUR,TRY"
    response = requests.get(url)
    data = response.json()
    rates = data['rates']
    return {
        'date': date,  # Keeping the date in yyyy-mm-dd format
        'usd_to_bgn': rates['BGN'],
        'usd_to_eur': rates['EUR'],
        'usd_to_try': rates['TRY'],
        'bgn_to_usd': 1 / rates['BGN'],
        'eur_to_usd': 1 / rates['EUR'],
        'try_to_usd': 1 / rates['TRY']
    }

def get_last_date():
    conn = mysql.connector.connect(**config.db_config)

    cursor = conn.cursor()
    cursor.execute('SELECT MAX(date) FROM Rates')
    result = cursor.fetchone()
    conn.close()
    return result[0]

def save_exchange_rates(rates):
    conn = mysql.connector.connect(**config.db_config)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Rates (date, usd_to_bgn, usd_to_eur, usd_to_try, bgn_to_usd, eur_to_usd, try_to_usd)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (rates['date'], rates['usd_to_bgn'], rates['usd_to_eur'], rates['usd_to_try'], rates['bgn_to_usd'], rates['eur_to_usd'], rates['try_to_usd']))
    conn.commit()
    conn.close()

def main():
    last_date = get_last_date()
    if last_date:
        start_date = last_date + timedelta(days=1)
    else:
        start_date = datetime.strptime('2022-01-01', '%Y-%m-%d').date()

    end_date = date.today()

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        rates = get_exchange_rates(date_str)
        save_exchange_rates(rates)
        current_date += timedelta(days=1)

if __name__ == '__main__':
    main()

