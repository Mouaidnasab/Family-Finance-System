from flask import Flask, request, render_template, jsonify, redirect, url_for, send_file, flash
from flask_login import login_user, UserMixin, LoginManager, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_bcrypt import Bcrypt
import mysql.connector
import csv
from datetime import datetime
from io import TextIOWrapper, StringIO, BytesIO
import os
import json 
from details_model.loading_model import find_most_similar
import numpy as np
import config
from functions import populate_unique_values, fetch_dropdown_data, validate_transaction_row,check_for_new_logs

import jwt
import time



# Metabase variables
METABASE_SITE_URL = "http://192.168.0.103:3000"
METABASE_SECRET_KEY = "b5f7f3bba8d6e0814c70f3de3fe2b6d2749f5a3a9674e0afddf30625a3a28ccd"


# Metabase token
payload = {
  "resource": {"dashboard": 2},
  "params": {
    
    
  },
  "exp": round(time.time()) + (60 * 10) # 10 minute expiration
}
token = jwt.encode(payload, METABASE_SECRET_KEY, algorithm="HS256")

# Metabase URL
iframeUrl = METABASE_SITE_URL + "/embed/dashboard/" + token + "#bordered=true&titled=true"


# Flask app configuration
app = Flask(__name__)
app.secret_key = 'your_secret_key'



# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")








# Call the function to populate the tables
populate_unique_values()


# Initialize Bcrypt
bcrypt = Bcrypt(app) 


# Initialize Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    @classmethod
    def get_by_username(cls, username):
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT member_id, username, password FROM Members WHERE username = %s', (username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return cls(result['member_id'], result['username'], result['password'])
        return None

    @classmethod
    def get_by_id(cls, id):
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT member_id, username, password FROM Members WHERE member_id = %s', (id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return cls(result['member_id'], result['username'], result['password'])
        return None

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


# Load user
@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


# SocketIO Events
@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)
    print(f"User joined room: {room}")

@socketio.on('leave')
def handle_leave(data):
    room = data['room']
    leave_room(room)
    print(f"User left room: {room}")

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.get_by_username(username)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))  # Adjust this as necessary
        else:
            flash('Invalid username or password')
    return render_template('Login.html')


@app.route('/logout')
def logout():
    logout_user()  # Log out the current user
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    return render_template('Dashboard.html')

@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    # Get the current user's username
    username = current_user.username  # Assuming `current_user` is from Flask-Login
    table_name = f"Transactions_Temp_{username}"
    trigger_name = f"log_transaction_changes_{username}"  # Unique trigger name for each user table

    print(table_name)

    try:
        # Establish the connection to the database
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()

        # Create a user-specific table if it does not already exist
        create_table_query = f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            transaction_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            checkbox int NOT NULL DEFAULT '0',
            ready int NOT NULL DEFAULT '0',
            incorrect_columns VARCHAR(255),
            source TEXT,
            date DATE DEFAULT NULL,
            segment VARCHAR(255) DEFAULT NULL,
            type VARCHAR(255) DEFAULT NULL,
            sub_type VARCHAR(255) DEFAULT NULL,
            category VARCHAR(255) DEFAULT NULL,
            sub_category VARCHAR(255) DEFAULT NULL,
            details TEXT,
            notes TEXT,
            sub_notes TEXT,
            transaction_description TEXT,
            country_withdraw VARCHAR(255) DEFAULT NULL,
            country_used VARCHAR(255) DEFAULT NULL,
            account_name VARCHAR(255) DEFAULT NULL,
            currency VARCHAR(255) DEFAULT NULL,
            payeer VARCHAR(255) DEFAULT NULL,
            paid_to VARCHAR(255) DEFAULT NULL,
            amount DOUBLE DEFAULT NULL
        )
        '''
        cursor.execute(create_table_query)
        conn.commit()

        # Create a trigger if it does not already exist
        check_trigger_query = f'''
        SELECT COUNT(*)
        FROM information_schema.TRIGGERS
        WHERE TRIGGER_NAME = '{trigger_name}' AND TRIGGER_SCHEMA = DATABASE();
        '''
        cursor.execute(check_trigger_query)
        trigger_exists = cursor.fetchone()[0]

        if not trigger_exists:
            create_trigger_query = f'''
            CREATE TRIGGER {trigger_name}
            AFTER UPDATE ON {table_name}
            FOR EACH ROW
            BEGIN
                INSERT INTO Transaction_Temp_Logs (username, transaction_id) 
                VALUES ('{username}', NEW.transaction_id);
            END;
            '''
            cursor.execute(create_trigger_query)
            conn.commit()

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
                    csv_reader = csv.reader(TextIOWrapper(file.stream, encoding='utf-8'))
                    headers = next(csv_reader)  # Skip the header row

                    # Insert query specific to the user's table
                    insert_query = f'''
                        INSERT INTO {table_name} (date, segment, type, sub_type, category, sub_category, details, notes, sub_notes, transaction_description, country_withdraw, country_used, account_name, currency, payeer, paid_to, amount, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    '''
                    
                    for row in csv_reader:
                        row = [col if col else None for col in row]
                        row += ['By uploading from website']  # Add the source column value
                        cursor.execute(insert_query, row)

                    conn.commit()
                    flash('File uploaded and processed successfully!', 'message')

                    # Emit WebSocket event to notify other clients
                    socketio.emit('data_updated', {'room': table_name}, room=table_name)

                except Exception as e:
                    conn.rollback()
                    flash(f'Error processing file: {str(e)}', 'error')
                finally:
                    cursor.close()
                    conn.close()

                return redirect(url_for('transactions'))

    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    # Render the template without passing any rows
    return render_template('Transactions.html')


@app.route('/get_transactions_data', methods=['GET'])
@login_required
def get_transactions_data():
    try:
        username = current_user.username
        table_name = f"Transactions_Temp_{username}"

        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f'SELECT * FROM {table_name}')
        rows = cursor.fetchall()

        # Replace None with an empty string for frontend display purposes
        for row in rows:
            for key, value in row.items():
                if value is None:
                    row[key] = ''
        # print(rows)

        return jsonify({'status': 'success', 'data': rows})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()



@app.route('/reports')
@login_required
def reports():
    return render_template('Reports.html')


@app.route('/download')
@login_required
def download_file():
    # Get the current user's username
    username = current_user.username  # Assuming `current_user` is defined via Flask-Login
    table_name = f"Transactions_Temp_{username}"

    try:
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()

        # Fetch data from the user-specific table
        query = f'SELECT * FROM {table_name}'
        print(f"Executing query: {query}")  # Debugging: Print the query to check if it is correct
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        if not rows:
            flash('No data available for download', 'error')
            return redirect(url_for('transactions'))

    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        print(f"Error during file download: {str(e)}")  # Debugging: Print the error message
        return redirect(url_for('transactions'))

    finally:
        cursor.close()
        conn.close()

    # Write the data to CSV format
    output = StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(columns)  # Write the headers (column names)
    csv_writer.writerows(rows)    # Write the data rows
    output.seek(0)

    # Convert the output to bytes and send as a file download
    byte_output = BytesIO(output.getvalue().encode('utf-8'))
    return send_file(byte_output, download_name=f'{table_name}.csv', as_attachment=True, mimetype='text/csv')

@app.route('/template_download')
@login_required
def template_download():
    try:
        template_path = 'static/Transactions_Templete.xlsx'
        return send_file(template_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading template: {str(e)}', 'error')
        return redirect(url_for('transactions'))

# Update `/update_transaction` to emit WebSocket events upon successful updates
@app.route('/update_transaction', methods=['POST'])
@login_required
def update_transaction():
    # Get the current user's username
    username = current_user.username  # Assuming Flask-Login provides current_user
    table_name = f"Transactions_Temp_{username}"
    print(f"Table name: {table_name}")

    # Parse the JSON data from the request
    data = request.get_json()
    transaction_id = data['id']  # Get transaction ID
    field = data['field']        # Get field to update
    value = data['value']        # Get new value

    try:
        # Establish database connection
        connection = mysql.connector.connect(**config.db_config)
        cursor = connection.cursor()

        # Construct dynamic update query based on the field and transaction ID
        update_query = f"UPDATE {table_name} SET {field} = %s WHERE transaction_id = %s"
        cursor.execute(update_query, (value, transaction_id))

        # Optionally call a stored procedure if required
        cursor.execute("CALL finalize_transactions_status()")

        # Commit changes to the database
        connection.commit()
        check_for_new_logs()    
        # Emit WebSocket event to notify other clients about the update
        socketio.emit('data_updated', {'room': table_name}, room=table_name)

        # Return success message
        return jsonify(success=True)

    except Exception as e:
        # Handle and log errors
        print(f"Error updating transaction: {str(e)}")  # Debugging: print the error message
        return jsonify(success=False, error=str(e))

    finally:
        # Close cursor and connection
        cursor.close()
        connection.close()


@app.route('/insert_transaction', methods=['POST'])
@login_required
def insert_transaction():
    # Get the current user's username
    username = current_user.username  # Assuming Flask-Login is providing current_user
    table_name = f"Transactions_Temp_{username}"  # Create user-specific table name

    # Parse the incoming JSON data
    data = request.get_json()

    try:
        # Establish the database connection
        connection = mysql.connector.connect(**config.db_config)
        cursor = connection.cursor()

        # Construct the insert query with the user-specific table name
        insert_query = f'''
            INSERT INTO {table_name} (date, segment, type, sub_type, category, sub_category, details, notes, sub_notes, transaction_description, country_withdraw, country_used, account_name, currency, payeer, paid_to, amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''

        # Execute the insert query with the data provided
        cursor.execute(insert_query, (
            data.get('date'), data.get('segment'), data.get('type'), data.get('sub_type'), data.get('category'),
            data.get('sub_category'), data.get('details'), data.get('notes'), data.get('sub_notes'), data.get('transaction_description'),
            data.get('country_withdraw'), data.get('country_used'), data.get('account_name'), data.get('currency'),
            data.get('payeer'), data.get('paid_to'), data.get('amount')
        ))

        # Commit the transaction
        connection.commit()

        # Return a success response
        return jsonify(success=True)

    except Exception as e:
        # Rollback in case of an error and log the error message
        connection.rollback()
        print(f"Error inserting transaction: {str(e)}")  # Debugging: Print the error
        return jsonify(success=False, error=str(e))

    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()


@app.route('/clear_content', methods=['POST'])
@login_required
def clear_content():
    # Get the current user's username
    username = current_user.username  # Assuming Flask-Login is providing current_user
    table_name = f"Transactions_Temp_{username}"  # Create user-specific table name

    try:
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()

        # Check if the table exists before attempting to clear it
        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        table_exists = cursor.fetchone()

        if not table_exists:
            return jsonify({'status': 'error', 'message': f'Table {table_name} does not exist!'})

        # Dynamically delete content from the user-specific Transactions_Temp_<username> table
        cursor.execute(f'DELETE FROM {table_name}')
        conn.commit()

        # Return a success response
        return jsonify({'status': 'success', 'message': 'Content cleared successfully!'})

    except Exception as e:
        # Rollback in case of an error and log the error message
        conn.rollback()
        print(f"Error clearing content: {str(e)}")  # Debugging: Print the error message
        return jsonify({'status': 'error', 'message': f'Error clearing content: {str(e)}'})

    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()


@app.route('/UpdateTransactionsTemp')
@login_required
def call_procedure_update_transactions_temp():
    # Get the current user's username
    username = current_user.username  # Assuming Flask-Login is providing current_user
    table_name = f"Transactions_Temp_{username}"  # Create user-specific table name

    try:
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch all rows from the user-specific Transactions_Temp_<username> table
        cursor.execute(f'SELECT * FROM {table_name}')
        transactions = cursor.fetchall()

        for transaction in transactions:
            description = transaction.get('transaction_description')

            if description:
                # Use the find_most_similar function to get the most similar row
                similar_row, similarity_score = find_most_similar(description)
                direct_check = 0
                if similar_row.get('sub_type') == 'Direct':
                    direct_check = 1
                for key, value in similar_row.items():
                    print(key, value)  # Debugging: Print the key-value pair being processed
                    if direct_check == 1 and key in transaction and key != "Combined" and key != "country_used" and not transaction[key]:  
                        # Check if the type is 'Direct' and the cell is empty
                        if isinstance(value, float) and np.isnan(value):  # Check if the value is NaN
                            value = None  # Replace NaN with None (or empty string if preferred)
                        update_query = f"UPDATE {table_name} SET {key} = %s WHERE transaction_id = %s"
                        cursor.execute(update_query, (value, transaction['transaction_id']))

        # Commit the transaction after updates
        conn.commit()
        flash('Auto-fill completed successfully!', 'message')

    except Exception as e:
        # Rollback in case of an error and log the error message
        conn.rollback()
        flash(f'Error during auto-fill: {str(e)}', 'error')
        print(f"Error during auto-fill: {str(e)}")  # Debugging: print the error message

    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()

    return redirect(url_for('transactions'))

@app.route('/check_all', methods=['POST'])
@login_required
def check_all():
    username = current_user.username
    table_name = f"Transactions_Temp_{username}"
    
    try:
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()
        
        # Update all rows to set checkbox = 1 (checked)
        cursor.execute(f'UPDATE {table_name} SET checkbox = 1')
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'All transactions checked.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'Error checking all: {str(e)}'})
    finally:
        cursor.close()
        conn.close()


@app.route('/uncheck_all', methods=['POST'])
@login_required
def uncheck_all():
    username = current_user.username
    table_name = f"Transactions_Temp_{username}"
    
    try:
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()
        
        # Update all rows to set checkbox = 0 (unchecked)
        cursor.execute(f'UPDATE {table_name} SET checkbox = 0')
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'All transactions unchecked.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'Error unchecking all: {str(e)}'})
    finally:
        cursor.close()
        conn.close()



@app.route('/dropdown_data')
@login_required
def dropdown_data():
    try:
        # Establish a connection to the MySQL database
        conn = mysql.connector.connect(**config.db_config)

        # Use the fetch_dropdown_data function to get dropdown data
        dropdown_data = fetch_dropdown_data(conn)

    except Exception as e:
        # Return error response in case of any exception
        return jsonify({'status': 'error', 'message': str(e)})

    finally:
        # Ensure the connection is closed
        conn.close()

    # Return success response with the fetched dropdown data
    return jsonify({'status': 'success', 'data': dropdown_data})

@app.route('/add_rows', methods=['POST'])
@login_required
def add_rows():
    # Get the current user's username
    username = current_user.username  # Assuming Flask-Login is providing current_user
    table_name = f"Transactions_Temp_{username}"  # Create user-specific table name

    # Get the number of rows to add from the JSON request
    data = request.json
    row_count = data.get('rows', 1)  # Default to 1 row if not provided
    source_value = ["Empty_Row_Added_From_Website"]  # Static value for how the row was added

    try:
        # Connect to the database
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()

        # Construct the insert query with the dynamic table name
        insert_query = f'''INSERT INTO {table_name} (source) 
                           VALUES (%s)'''

        # Insert the specified number of rows
        for _ in range(row_count):
            cursor.execute(insert_query, source_value)
        
        # Commit the transaction
        conn.commit()

        # Return a success response
        return jsonify({'status': 'success', 'message': f'{row_count} rows added successfully!'})

    except Exception as e:
        # Rollback in case of an error and log the error message
        conn.rollback()
        print(f"Error adding rows: {str(e)}")  # Debugging: print the error
        return jsonify({'status': 'error', 'message': f'Error adding rows: {str(e)}'})

    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()

@app.route('/finalize')
@login_required
def finalize_transactions():
    # Get the current user's username
    username = current_user.username  # Assuming Flask-Login is providing current_user
    table_name = f"Transactions_Temp_{username}"  # Create user-specific table name

    try:
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch only the rows where the checkbox column is set (checked)
        cursor.execute(f'SELECT * FROM {table_name} WHERE checkbox = 1')
        rows = cursor.fetchall()

        if not rows:
            flash('No checked transactions to finalize.', 'error')
            return redirect(url_for('transactions'))

        # Fetch existing accounts and members
        cursor.execute('SELECT account_id, name, currency FROM Accounts')
        accounts_data = cursor.fetchall()
        accounts_dict = {(acc['name'], acc['currency']): acc['account_id'] for acc in accounts_data}

        cursor.execute('SELECT member_id, first_name, last_name FROM Members')
        members_data = cursor.fetchall()
        members_dict = {f"{member['first_name'].lower()} {member['last_name'].lower()}": member['member_id'] for member in members_data}

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
        external_account_counter = 100000

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

        # Helper function to split account name and currency
        def split_account_name_currency(account_str):
            parts = account_str.rsplit(' ', 1)
            if len(parts) == 2 and parts[1] in ['SR', 'USD', 'BGN', 'TRY', 'SRY']:
                return parts[0], parts[1]
            return account_str, None

        # Iterate over the rows where checkbox is checked and move them to Transactions table
        for row in rows:
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
                        paid_to_id = get_or_create_external_account(paid_to_name, paid_to_currency, "external", "General")
                        accounts_dict[paid_to_key] = paid_to_id

                # Fetch exchange rates for the transaction date
                cursor.execute('''
                    SELECT usd_to_bgn, usd_to_eur, usd_to_try, bgn_to_usd, eur_to_usd, try_to_usd
                    FROM Rates
                    WHERE date = %s
                ''', (row['date'],))
                exchange_rates = cursor.fetchone()
                if not exchange_rates:
                    continue  # Skip if exchange rates are not found for the date

                # Calculate VAT
                country_used_lower = row['country_used'].lower()
                vat = vat_percentages.get(country_used_lower, 0)

                # Calculate amounts in USD and SR
                amount_in_usd = None
                currency = row['currency'].lower()
                if row['amount'] is not None:
                    amount = float(row['amount'])

                    if currency == 'usd':
                        amount_in_usd = amount
                    elif currency == 'bgn':
                        amount_in_usd = amount * exchange_rates['bgn_to_usd']
                    elif currency == 'eur':
                        amount_in_usd = amount * exchange_rates['eur_to_usd']
                    elif currency == 'try':
                        amount_in_usd = amount * exchange_rates['try_to_usd']
                    elif currency == 'sr':
                        amount_in_usd = amount * sr_to_usd_rate
                    elif currency == 'sry':
                        amount_in_usd = amount * sry_to_usd_rate

                amount_in_sr = amount_in_usd * 3.75 if amount_in_usd else None

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

        # After successfully moving rows, delete them from the temp table
        cursor.execute(f'DELETE FROM {table_name} WHERE checkbox = 1')
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
@login_required
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
        conn = mysql.connector.connect(**config.db_config)
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
@login_required
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
        conn = mysql.connector.connect(**config.db_config)
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
    socketio.run(app, debug=True, host="0.0.0.0", port=4300)



