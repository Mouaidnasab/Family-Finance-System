from flask import Flask, request, render_template, jsonify, redirect, url_for, send_file, flash
import mysql.connector
import csv
from io import TextIOWrapper, StringIO, BytesIO
import os
import json 
from details_model.loading_model import find_most_similar
import numpy as np



app = Flask(__name__)
app.secret_key = 'your_secret_key'

db_config = {
    'user': 'mouaid_admin',
    'password': '0991553333',
    'host': 'localhost',
    'database': 'Finance'
}

def populate_unique_values():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Populate Segments
    cursor.execute('''
    INSERT INTO dd_Segments (name)
    SELECT DISTINCT Transactions.segment FROM Transactions
    WHERE Transactions.segment IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name)
    ''')

    # Populate Types
    cursor.execute('''
    INSERT INTO dd_Types (name)
    SELECT DISTINCT Transactions.type FROM Transactions
    WHERE Transactions.type IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name)
    ''')

    # Populate Sub_Types
    cursor.execute('''
    INSERT INTO dd_Sub_Types (name)
    SELECT DISTINCT Transactions.sub_type FROM Transactions
    WHERE Transactions.sub_type IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name)
    ''')

    # Populate Categories
    cursor.execute('''
    INSERT INTO dd_Categories (name)
    SELECT DISTINCT Transactions.category FROM Transactions
    WHERE Transactions.category IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name)
    ''')

    # Populate Sub_Categories
    cursor.execute('''
    INSERT INTO dd_Sub_Categories (name)
    SELECT DISTINCT Transactions.sub_category FROM Transactions
    WHERE Transactions.sub_category IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name)
    ''')


    # Populate Countries from Accounts
    cursor.execute('''
    INSERT INTO dd_Countries (name)
    SELECT DISTINCT Accounts.country FROM Accounts
    WHERE Accounts.country IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name)
    ''')

    # Populate Account_Names
    cursor.execute('''
    INSERT INTO dd_Account_Names (name)
    SELECT DISTINCT Accounts.name FROM Accounts
    WHERE Accounts.name IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name)
    ''')

    # Populate Currencies from Accounts
    cursor.execute('''
    INSERT INTO dd_Currencies (name)
    SELECT DISTINCT Accounts.currency FROM Accounts
    WHERE Accounts.currency IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name)
    ''')

    conn.commit()
    cursor.close()
    conn.close()

# Call the function to populate the tables
populate_unique_values()

@app.route('/')
def dashboard():
    return render_template('Dashboard.html')

@app.route('/transactions', methods=['GET', 'POST'])
def transactions():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file:
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                csv_reader = csv.reader(TextIOWrapper(file.stream, encoding='utf-8'))
                headers = next(csv_reader)  # Skip the header row

                insert_query = '''
                    INSERT INTO Transactions_Temp (date, segment, type, sub_type, category, sub_category, details, notes, sub_notes, transaction_description, country_withdraw, country_used, account_name, currency, payeer, paid_to, amount, how_it_is_inserted)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                
                for row in csv_reader:
                    # Ensure row has exactly 17 columns, fill missing with None
                    row = [col if col else None for col in row]
                    row += ['By uploading from website']
                    print(row)
                    cursor.execute(insert_query, row)
                
                conn.commit()
                flash('File uploaded and processed successfully!', 'message')
            except Exception as e:
                conn.rollback()
                flash(f'Error processing file: {str(e)}', 'error')
            finally:
                cursor.close()
                conn.close()
            return redirect(url_for('transactions'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM Transactions_Temp')
        rows = cursor.fetchall()
        
        # Replace None with empty string
        for row in rows:
            for key, value in row.items():
                if value is None:
                    row[key] = ''
        
    except Exception as e:
        flash(f'Error fetching data: {str(e)}', 'error')
        rows = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('Transactions.html', rows=rows)

@app.route('/reports')
def reports():
    return render_template('Reports.html')

@app.route('/download')
def download_file():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Transactions_Temp')
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('transactions'))
    finally:
        cursor.close()
        conn.close()

    output = StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(columns)
    csv_writer.writerows(rows)
    output.seek(0)
    
    byte_output = BytesIO(output.getvalue().encode('utf-8'))
    return send_file(byte_output, download_name='Transactions_Temp.csv', as_attachment=True, mimetype='text/csv')

@app.route('/template_download')
def template_download():
    try:
        template_path = os.path.join('static', 'Transactions_Template.xlsx')
        return send_file(template_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading template: {str(e)}', 'error')
        return redirect(url_for('transactions'))

@app.route('/update_transaction', methods=['POST'])
def update_transaction():
    data = request.get_json()
    transaction_id = data['id']
    field = data['field']
    value = data['value']

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    update_query = f"UPDATE Transactions_Temp SET {field} = %s WHERE transaction_id = %s"
    cursor.execute(update_query, (value, transaction_id))
    cursor.execute("CALL finalize_transactions_status()")
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify(success=True)

@app.route('/insert_transaction', methods=['POST'])
def insert_transaction():
    data = request.get_json()

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    insert_query = '''
        INSERT INTO Transactions_Temp (date, segment, type, sub_type, category, sub_category, details, notes, sub_notes, transaction_description, country_withdraw, country_used, account_name, currency, payeer, paid_to, amount)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    cursor.execute(insert_query, (
        data.get('date'), data.get('segment'), data.get('type'), data.get('sub_type'), data.get('category'),
        data.get('sub_category'), data.get('details'), data.get('notes'), data.get('sub_notes'), data.get('transaction_description'),
        data.get('country_withdraw'), data.get('country_used'), data.get('account_name'), data.get('currency'),
        data.get('payeer'), data.get('paid_to'), data.get('amount')
    ))
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify(success=True)

@app.route('/clear_content', methods=['POST'])
def clear_content():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM Transactions_Temp')
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Content cleared successfully!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'Error clearing content: {str(e)}'})
    finally:
        cursor.close()
        conn.close()

@app.route('/UpdateTransactionsTemp')
def call_procedure_update_transactions_temp():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch all rows from Transactions_Temp
        cursor.execute('SELECT * FROM Transactions_Temp')
        transactions = cursor.fetchall()

        for transaction in transactions:
            description = transaction.get('transaction_description')

            if description:
                # Use the find_most_similar function to get the most similar row
                similar_row, similarity_score = find_most_similar(description)
 

                for key, value in similar_row.items():
                    if transaction['sub_type'] == 'Direct' and key in transaction and not transaction[key]:  # Check if the type is 'Direct' and the cell is empty
                        if isinstance(value, float) and np.isnan(value):  # Check if the value is nan
                            value = None  # or value = '' if you prefer to store an empty string
                        update_query = f"UPDATE Transactions_Temp SET {key} = %s WHERE transaction_id = %s"
                        cursor.execute(update_query, (value, transaction['transaction_id']))

        conn.commit()
        flash('Auto-fill completed successfully!', 'message')

    except Exception as e:
        conn.rollback()
        flash(f'Error during auto-fill: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('transactions'))

@app.route('/add_transaction_detail', methods=['POST'])
def add_transaction_detail():
    data = request.get_json()

    insert_query = '''
        INSERT INTO Transactions_Details (unique_description, transaction_description, segment, type, sub_type, category, sub_category, country_used) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    '''
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(insert_query, (
            data.get('unique_description'), data.get('transaction_description'), data.get('segment'), data.get('type'), data.get('sub_type'),
            data.get('category'), data.get('sub_category'), data.get('country_used')
        ))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Transaction details added successfully!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()


@app.route('/dropdown_data')
def dropdown_data():
    dropdown_data = {}

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch segments
        cursor.execute('SELECT DISTINCT name FROM dd_Segments')
        dropdown_data['segment'] = [row['name'] for row in cursor.fetchall()]

        # Fetch types
        cursor.execute('SELECT DISTINCT name FROM dd_Types')
        dropdown_data['type'] = [row['name'] for row in cursor.fetchall()]

        # Fetch sub_types
        cursor.execute('SELECT DISTINCT name FROM dd_Sub_Types')
        dropdown_data['sub_type'] = [row['name'] for row in cursor.fetchall()]

        # Fetch categories
        cursor.execute('SELECT DISTINCT name FROM dd_Categories')
        dropdown_data['category'] = [row['name'] for row in cursor.fetchall()]

        # Fetch sub_categories
        cursor.execute('SELECT DISTINCT name FROM dd_Sub_Categories')
        dropdown_data['sub_category'] = [row['name'] for row in cursor.fetchall()]

        # Fetch countries
        cursor.execute('SELECT DISTINCT name FROM dd_Countries')
        dropdown_data['country'] = [row['name'] for row in cursor.fetchall()]

        # Fetch account names
        cursor.execute('SELECT DISTINCT name FROM dd_Account_Names')
        dropdown_data['account_name'] = [row['name'] for row in cursor.fetchall()]

        # Fetch currencies
        cursor.execute('SELECT DISTINCT name FROM dd_Currencies')
        dropdown_data['currency'] = [row['name'] for row in cursor.fetchall()]

        # Fetch unique details
        cursor.execute('SELECT DISTINCT details FROM Details')
        dropdown_data['details'] = [row['details'] for row in cursor.fetchall()]

        # Fetch unique notes
        cursor.execute('SELECT DISTINCT notes FROM Details')
        dropdown_data['notes'] = [row['notes'] for row in cursor.fetchall()]

        # Fetch unique sub_notes
        cursor.execute('SELECT DISTINCT sub_notes FROM Details')
        dropdown_data['sub_notes'] = [row['sub_notes'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT CONCAT(first_name, ' ', last_name) AS full_name FROM Members")
        dropdown_data['member_name'] = [row['full_name'] for row in cursor.fetchall()]

        # Fetch unique transaction descriptions
        cursor.execute('SELECT DISTINCT transaction_description FROM Details')
        dropdown_data['transaction_description'] = [row['transaction_description'] for row in cursor.fetchall()]

        # Fetch unique amounts
        cursor.execute('SELECT DISTINCT amount FROM Amounts')
        dropdown_data['amount'] = [row['amount'] for row in cursor.fetchall()]

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

    finally:
        cursor.close()
        conn.close()

    return jsonify({'status': 'success', 'data': dropdown_data})


@app.route('/add_rows', methods=['POST'])
def add_rows():
    data = request.json
    row_count = data.get('rows', 1)
    how_it_is_inserted_value = ["Empty_Row_Added_From_Website"]  # Static value for How_It_Is_Inserted
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        insert_query = '''INSERT INTO Transactions_Temp ( How_It_Is_Inserted) 
                          VALUES ( %s)'''
        for _ in range(row_count):
            cursor.execute(insert_query, how_it_is_inserted_value)
        conn.commit()
        return jsonify({'status': 'success', 'message': f'{row_count} rows added successfully!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'Error adding rows: {str(e)}'})
    finally:
        cursor.close()
        conn.close()

@app.route('/finalize')
def finalize_transactions():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM Transactions_Temp')
        rows = cursor.fetchall()
        
        required_columns = [
            'date', 'segment', 'type', 'sub_type', 'category',
            'country_used', 'account_name', 'currency', 'payeer', 'paid_to', 'amount'
        ]

        # Check for missing fields and skip empty rows
        valid_rows = []
        for row in rows:
            # Ignore the 'how_it_is_inserted' column
            row_without_inserted = {k: v for k, v in row.items() if k not in ['how_it_is_inserted', 'transaction_id']}
            is_row_empty = all(value in [None, ''] for value in row_without_inserted.values())
            if is_row_empty:
                continue  # Skip the row if all cells are empty

            if any(row[col] is None or row[col] == '' for col in required_columns):
                flash('Some fields are missing. Please correct them before finalizing.', 'error')
                return redirect(url_for('transactions'))
            
            valid_rows.append(row)

        # Fetch existing accounts and members
        cursor.execute('SELECT account_id, name, currency FROM Accounts')
        accounts_data = cursor.fetchall()

        # Debugging: Print fetched accounts data
        # print("Fetched Accounts Data:", accounts_data)

        # Create a dictionary for account lookup
        accounts_dict = {(acc['name'], acc['currency']): acc['account_id'] for acc in accounts_data}

        # Debugging: Print the accounts dictionary
        # print("Accounts Dictionary:", accounts_dict)

        cursor.execute('SELECT member_id, first_name, last_name FROM Members')
        members_data = cursor.fetchall()

        # Debugging: Print fetched members data
        # print("Fetched Members Data:", members_data)

        members_dict = {f"{member['first_name'].lower()} {member['last_name'].lower()}": member['member_id'] for member in members_data}

        # Debugging: Print the members dictionary
        # print("Members Dictionary:", members_dict)

        # VAT percentages by country
        vat_percentages = {
            "saudi arabia": 0.15,
            "bulgaria": 0.20,
            "turkey": 0.18,
            "syria": 0.10,
        }

        # Static conversion rates
        sr_to_usd_rate = 0.2667
        sry_to_usd_rate = 0.00006

        # Function to get or create external account
        external_account_counter = 100000000

        def get_or_create_external_account(account_name, currency, segment, country):
            nonlocal external_account_counter

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
            
        # Function to fetch exchange rates
        def fetch_exchange_rates(date):
            cursor.execute('''
                SELECT usd_to_bgn, usd_to_eur, usd_to_try, bgn_to_usd, eur_to_usd, try_to_usd
                FROM Rates
                WHERE date = %s
            ''', (date,))
            result = cursor.fetchone()
            if result:
                return {key: float(value) for key, value in result.items()}
            return None

        # Helper function to split account name and currency
        def split_account_name_currency(account_str):
            parts = account_str.rsplit(' ', 1)
            if len(parts) == 2 and parts[1] in ['SR', 'USD', 'BGN', 'TRY', 'SRY']:
                return parts[0], parts[1]
            return account_str, None

        # Iterate over the valid rows and insert data into respective tables
        for row in valid_rows:
            try:
                # Handle missing data by filling with None
                row = {k: (v if v != '' else None) for k, v in row.items()}

                # Get account_id based on account_name and currency
                account_key = (row['account_name'], row['currency'])
                if account_key in accounts_dict:
                    account_id = accounts_dict[account_key]
                else:
                    flash(f"Account {row['account_name']} with currency {row['currency']} does not exist.", 'error')
                    return redirect(url_for('transactions'))
                # Get or create account_id for payeer
                payeer_name, payeer_currency = split_account_name_currency(row['payeer'])
                if not payeer_currency:
                    payeer_currency = row['currency']
                payeer_key = (payeer_name, payeer_currency)
                if payeer_key in accounts_dict:
                    payeer_id = accounts_dict[payeer_key]
                else:
                    payeer_id = get_or_create_external_account(payeer_name, payeer_currency, "external", row['country_withdraw'])
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
                        paid_to_id = get_or_create_external_account(paid_to_name, paid_to_currency, "external", row['country_used'])
                        accounts_dict[paid_to_key] = paid_to_id
                # Fetch exchange rates for the transaction date
                exchange_rates = fetch_exchange_rates(row['date'])
                if not exchange_rates:
                    continue  # Skip if exchange rates are not found for the date
                
                # Extract exchange rates from the dictionary
                bgn_to_usd = exchange_rates['bgn_to_usd']
                eur_to_usd = exchange_rates['eur_to_usd']
                try_to_usd = exchange_rates['try_to_usd']

                # Calculate VAT
                country_used_lower = row['country_used'].lower()
                vat = vat_percentages.get(country_used_lower, 0)
                # Calculate amounts in USD and SR
                amount_in_usd = None
                currency = row['currency'].lower()  # Convert currency to lower case

                if row['amount'] is not None:  # Check if amount is not None
                    amount = float(row['amount'])  # Convert amount to float

                    if currency == 'usd':
                        amount_in_usd = amount
                    elif currency == 'bgn':
                        amount_in_usd = amount * bgn_to_usd
                    elif currency == 'eur':
                        amount_in_usd = amount * eur_to_usd
                    elif currency == 'try':
                        amount_in_usd = amount * try_to_usd
                    elif currency == 'sr':
                        amount_in_usd = amount * sr_to_usd_rate
                    elif currency == 'sry':
                        amount_in_usd = amount * sry_to_usd_rate

                else:
                    amount_in_usd = None


                amount_in_sr = amount_in_usd * 3.75 if amount_in_usd else None
                # print('Transactions: ',account_id, row['date'], row['segment'], row['type'], row['sub_type'], row['category'], row['sub_category'], row['country_used'], payeer_id, paid_to_id, to_whom_id)
                # print('Amounts: ', row['amount'], vat, amount_in_usd, amount_in_sr)
                # print('Details: ', row['details'], row['notes'], row['sub_notes'], row['transaction_description'])

                # Insert into Transactions table
                cursor.execute('''
                    INSERT INTO Transactions (account_id, date, segment, type, sub_type, category, sub_category, country_used, payeer_id, paid_to_id, to_whom_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (account_id, row['date'], row['segment'], row['type'], row['sub_type'], row['category'], row['sub_category'], row['country_used'], payeer_id, paid_to_id, to_whom_id))

                transaction_id = cursor.lastrowid

                # Insert into Amounts table
                cursor.execute('''
                    INSERT INTO Amounts (transaction_id, amount, vat, in_usd, in_sr)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (transaction_id, row['amount'], vat, amount_in_usd, amount_in_sr))

                # Insert into Details table
                cursor.execute('''
                    INSERT INTO Details (transaction_id, details, notes, sub_notes, transaction_description)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (transaction_id, row['details'], row['notes'], row['sub_notes'], row['transaction_description']))

            except Exception as e:
                conn.rollback()
                print('Error processing row: ', str(e))
                flash(f'Error processing row: {str(e)}', 'error')
                return redirect(url_for('transactions'))

        cursor.execute('TRUNCATE TABLE Transactions_Temp')
        conn.commit()
        flash('Transactions successfully finalized!', 'message')
    except Exception as e:
        conn.rollback()
        flash(f'Error finalizing transactions: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('transactions'))



@app.route('/filter_transactions', methods=['POST'])
def filter_transactions():
    filters = request.json
    print('Received filters:', filters)  # Debugging line to print received filters
    query = '''
        SELECT 
            Transactions.date, 
            Transactions.segment, 
            Transactions.type, 
            Transactions.sub_type, 
            Transactions.category, 
            Transactions.sub_category, 
            Details.details, 
            Details.notes, 
            Details.sub_notes, 
            Details.transaction_description, 
            Transactions.country_used, 
            Accounts.name as account_name, 
            Accounts.currency, 
            payeer.name as payeer, 
            paid_to.name as paid_to, 
            Amounts.amount
        FROM 
            Transactions
        LEFT JOIN 
            Details ON Transactions.transaction_id = Details.transaction_id
        LEFT JOIN 
            Amounts ON Transactions.transaction_id = Amounts.transaction_id
        LEFT JOIN 
            Accounts ON Transactions.account_id = Accounts.account_id
        LEFT JOIN 
            Accounts as payeer ON Transactions.payeer_id = payeer.account_id
        LEFT JOIN 
            Accounts as paid_to ON Transactions.paid_to_id = paid_to.account_id
        WHERE 1=1
    '''

    query_params = []
    for column, value in filters.items():
        if value:
            table_column = column.lower()
            if column in ['date']:
                table_column = f'Transactions.{table_column}'
                date_range = value.split(' to ')
                if len(date_range) == 2:
                    query += f' AND {table_column} BETWEEN %s AND %s'
                    query_params.extend(date_range)
                continue
            elif column in ['segment', 'type', 'sub_type', 'category', 'sub_category']:
                table_column = f'Transactions.{table_column}'
            elif column in ['details', 'notes', 'sub_notes', 'transaction_description']:
                table_column = f'Details.{table_column}'
            elif column == 'country':
                table_column = f'Transactions.country_used'
            elif column in ['currency']:
                table_column = f'Accounts.{table_column}'
            elif column in ['account_name']:
                table_column = f'Accounts.name'
            elif column in ['payeer']:
                table_column = f'payeer.name'
            elif column in ['paid_to']:
                table_column = f'paid_to.name'
            elif column == 'amount':
                table_column = f'Amounts.{table_column}'

            query += f' AND {table_column} LIKE %s'
            query_params.append(f'%{value}%')

    print('Final query:', query)  # Debugging line to print the final query
    print('Query params:', query_params)  # Debugging line to print the query parameters

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
    except Exception as e:
        print('Error:', str(e))  # Debugging line to print errors
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

    # Replace None with empty string
    for row in rows:
        for key, value in row.items():
            if value is None:
                row[key] = ''

    response = jsonify({'status': 'success', 'data': rows})
    response.headers.add('Content-Type', 'application/json')
    return response



@app.route('/download_filtered', methods=['POST'])
def download_filtered():
    filters = request.form.get('filters')
    filters = json.loads(filters)

    query = '''
        SELECT 
            Transactions.date, 
            Transactions.segment, 
            Transactions.type, 
            Transactions.sub_type, 
            Transactions.category, 
            Transactions.sub_category, 
            Details.details, 
            Details.notes, 
            Details.sub_notes, 
            Details.transaction_description, 
            Transactions.country_used, 
            Accounts.name as account_name, 
            Accounts.currency, 
            payeer.name as payeer, 
            paid_to.name as paid_to, 
            Amounts.amount
        FROM 
            Transactions
        LEFT JOIN 
            Details ON Transactions.transaction_id = Details.transaction_id
        LEFT JOIN 
            Amounts ON Transactions.transaction_id = Amounts.transaction_id
        LEFT JOIN 
            Accounts ON Transactions.account_id = Accounts.account_id
        LEFT JOIN 
            Accounts as payeer ON Transactions.payeer_id = payeer.account_id
        LEFT JOIN 
            Accounts as paid_to ON Transactions.paid_to_id = paid_to.account_id
        WHERE 1=1
    '''

    query_params = []
    for column, value in filters.items():
        if value:
            table_column = column.lower()
            if column in ['segment', 'type', 'sub_type', 'category', 'sub_category']:
                table_column = f'Transactions.{table_column}'
            elif column in ['details', 'notes', 'sub_notes', 'transaction_description']:
                table_column = f'Details.{table_column}'
            elif column == 'country':
                table_column = f'Transactions.country_used'
            elif column in ['currency']:
                table_column = f'Accounts.{table_column}'
            elif column in ['account_name']:
                table_column = f'Accounts.name'
            elif column in ['payeer']:
                table_column = f'payeer.name'
            elif column in ['paid_to']:
                table_column = f'paid_to.name'
            elif column == 'amount':
                table_column = f'Amounts.{table_column}'

            query += f' AND {table_column} LIKE %s'
            query_params.append(f'%{value}%')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    except Exception as e:
        flash(f'Error downloading filtered data: {str(e)}', 'error')
        return redirect(url_for('reports'))
    finally:
        cursor.close()
        conn.close()

    output = StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(columns)
    csv_writer.writerows(rows)
    output.seek(0)
    
    byte_output = BytesIO(output.getvalue().encode('utf-8'))
    return send_file(byte_output, download_name='Filtered_Transactions.csv', as_attachment=True, mimetype='text/csv')


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=4500)


