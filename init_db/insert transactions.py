import pandas as pd
import mysql.connector
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config



# Get the directory of the script
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, 'static data', 'transactions Mustafa 2024.08.03.xlsx')



conn = mysql.connector.connect(**config.db_config)

cursor = conn.cursor()

# Read a specific sheet from the Excel file and convert all column names to lowercase
df = pd.read_excel(file_path, sheet_name='everthing')
df.columns = df.columns.str.lower()
print("Columns after .lower():", df.columns)

# Load internal accounts from the Accounts table
cursor.execute('SELECT account_id, name, currency FROM Accounts')
accounts_data = cursor.fetchall()
accounts_dict = {(name, currency): account_id for account_id, name, currency in accounts_data}

# Load member data from the Members table
cursor.execute('SELECT member_id, first_name, last_name FROM Members')
members_data = cursor.fetchall()
members_dict = {f"{first_name.lower()} {last_name.lower()}": member_id for member_id, first_name, last_name in members_data}
print("Members dictionary keys after .lower():", list(members_dict.keys()))

# VAT percentages by country
vat_percentages = {
    "saudi arabia": 0.15,
    "bulgaria": 0.20,  # Bulgaria
    "turkey": 0.18,  # Turkey
    "syria": 0.10,  # Syria
    # Add more countries and their VAT percentages as needed
}

# Static conversion rates
sr_to_usd_rate = 0.2667
sry_to_usd_rate = 0.00006

# Function to get or create account_id for external accounts
external_account_counter = 100000

def get_or_create_external_account(account_name, currency, segment, country):
    global external_account_counter

    cursor.execute('''
        SELECT account_id FROM Accounts WHERE name = %s AND currency = %s AND segment = %s
    ''', (account_name, currency, segment))

    account_id = cursor.fetchone()
    if account_id:
        return account_id[0]
    else:
        account_id = external_account_counter
        cursor.execute('''
            INSERT INTO Accounts (account_id, name, currency, segment, country) VALUES (%s, %s, %s, %s, %s)
        ''', (account_id, account_name, currency, segment, country))
        external_account_counter += 1
        return account_id

# Function to get member_id for to_whom_id based on first and last name
def get_member_id(full_name):
    print("Getting member ID for:", full_name)
    return members_dict.get(full_name.lower())

# Function to fetch exchange rates
def fetch_exchange_rates(date):
    cursor.execute('''
        SELECT usd_to_bgn, usd_to_eur, usd_to_try, bgn_to_usd, eur_to_usd, try_to_usd
        FROM Rates
        WHERE date = %s
    ''', (date,))
    return cursor.fetchone()

# Helper function to split account name and currency
def split_account_name_currency(account_str):
    parts = account_str.rsplit(' ', 1)
    if len(parts) == 2 and parts[1] in ['SR', 'USD', 'BGN', 'TRY', 'SRY']:
        return parts[0], parts[1]
    return account_str, None

# Iterate over the rows in the DataFrame and insert data into the respective tables
for index, row in df.iterrows():
    try:
        # Handle missing data by filling with None
        row = row.where(pd.notnull(row), None)

        # Get account_id based on account_name and currency
        account_key = (row['account_name'], row['currency'])
        if account_key in accounts_dict:
            account_id = accounts_dict[account_key]
        else:
            print(f"Skipping row {index}: Internal account not found for {account_key}")
            continue  # If account_id is not found in internal accounts, skip this row

        # Get or create account_id for payeer
        payeer_name, payeer_currency = split_account_name_currency(row['payeer'])
        if not payeer_currency:
            payeer_currency = row['currency']
        payeer_key = (payeer_name, payeer_currency)
        if payeer_key in accounts_dict:
            payeer_id = accounts_dict[payeer_key]
        else:
            payeer_id = get_or_create_external_account(payeer_name, payeer_currency, "external", "General")
            accounts_dict[payeer_key] = payeer_id

        # Get or create account_id for paid_to
        paid_to_id = None
        to_whom_id = None
        paid_to_name, paid_to_currency = split_account_name_currency(row['paid_to'])
        if not paid_to_currency:
            paid_to_currency = row['currency']
        if paid_to_name and paid_to_name.lower() in members_dict:
            to_whom_id = members_dict[paid_to_name.lower()]
        else:
            paid_to_key = (paid_to_name, paid_to_currency)
            if paid_to_key in accounts_dict:
                paid_to_id = accounts_dict[paid_to_key]
            else:
                paid_to_id = get_or_create_external_account(paid_to_name, paid_to_currency, "external","General")
                accounts_dict[paid_to_key] = paid_to_id

        # Fetch exchange rates for the transaction date
        exchange_rates = fetch_exchange_rates(row['date'])
        if not exchange_rates:
            print(f"Skipping row {index}: Exchange rates not found for date {row['date']}")
            continue  # If exchange rates are not found for the date, skip this row

        usd_to_bgn, usd_to_eur, usd_to_try, bgn_to_usd, eur_to_usd, try_to_usd = exchange_rates

        # Calculate VAT
        location_used_lower = row['location_used'].lower()
        vat = vat_percentages.get(location_used_lower, 0)

        # Calculate amounts in USD and SR
        amount_in_usd = None
        if row['currency'] == 'USD':
            amount_in_usd = row['amount']
        elif row['currency'] == 'BGN':
            amount_in_usd = row['amount'] * bgn_to_usd if row['amount'] else None
        elif row['currency'] == 'EUR':
            amount_in_usd = row['amount'] * eur_to_usd if row['amount'] else None
        elif row['currency'] == 'TRY':
            amount_in_usd = row['amount'] * try_to_usd if row['amount'] else None
        elif row['currency'] == 'SR':
            amount_in_usd = row['amount'] * sr_to_usd_rate if row['amount'] else None
        elif row['currency'] == 'SRY':
            amount_in_usd = row['amount'] * sry_to_usd_rate if row['amount'] else None

        amount_in_sr = amount_in_usd * 3.75 if amount_in_usd else None

        # Insert into Transactions table
        cursor.execute('''
            INSERT INTO Transactions (account_id, date, segment, type, sub_type, category, sub_category, country_used, payeer_id, paid_to_id, to_whom_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (account_id, row['date'], row['segment'], row['type'], row['sub_type'], row['category'], row['sub_category'],row['location_used'] , payeer_id, paid_to_id, to_whom_id))

        transaction_id = cursor.lastrowid

        # Insert into Amounts table
        cursor.execute('''
            INSERT INTO Amounts (transaction_id, amount, vat, in_usd, in_sr)
            VALUES (%s, %s, %s, %s, %s)
        ''', (transaction_id, row['amount'], vat, amount_in_usd, amount_in_sr))

        cursor.execute('''
            INSERT INTO Details (transaction_id, details, notes, sub_notes, transaction_description)
            VALUES (%s, %s, %s, %s, %s)
        ''', (transaction_id, row['details'], row['notes'], row['sub_notes'], row['transaction_description']))


    except Exception as e:
        print(f"Error processing row {index}: {e}")

conn.commit()
cursor.close()
conn.close()
