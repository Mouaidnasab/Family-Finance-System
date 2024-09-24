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
from functions import populate_unique_values, fetch_dropdown_data, validate_transaction_row,check_for_new_logs_optimized
import json
import pandas as pd
import re


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



with open(os.path.join('static', 'dictionary.json'), 'r', encoding='utf-8') as f:
    translation_dict = json.load(f)




def translate_value(value, target_lang):
    if not value or value in ["None", "NaN", "nan"]:  # Skip if the value is None or an empty string
        return value

    if target_lang == 'en':
        # Translate Arabic to English
        return translation_dict.get('en', {}).get(value, value)  # Use the original value if no translation is found
    elif target_lang == 'ar':
        # Translate English to Arabic
        # Reverse the dictionary for translation
        reverse_dict = {v: k for k, v in translation_dict.get('en', {}).items()}
        return reverse_dict.get(value, value)  # Use the original value if no translation is found
    else:
        return value  # No translation needed



def translate_dataframe(df, target_lang):
    columns_to_translate = ['segment', 'type', 'sub_type', 'category', 'sub_category',
                            'currency', 'country_withdraw', 'country_used', 'payeer',
                            'paid_to', 'account_name']

    for col in columns_to_translate:
        if col in df.columns:
            translated_col = df[col].apply(lambda x: translate_value(x, target_lang))

            # Instead of raising an error, log the missing translations but accept None or NaN
            missing = df[col][translated_col.isnull() & df[col].notnull()].unique()  # Find only non-null values that failed to translate
            if len(missing) > 0:
                print(f"Warning: Missing translations for values: {missing}")

            # Update the DataFrame with translated values
            df[col] = translated_col

    return df




def detect_arabic(text):
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    return bool(arabic_pattern.search(text))

def is_excel_in_arabic(df, columns_to_check):
    """
    Detect if the majority of the values in the given columns of the DataFrame contain Arabic characters.
    """
    arabic_count = 0
    total_count = 0

    for col in columns_to_check:
        if col in df.columns:
            for value in df[col].dropna():  # Skip NaN values
                if isinstance(value, str) and detect_arabic(value):
                    arabic_count += 1
                total_count += 1

    # If more than 50% of the values contain Arabic, consider the file as Arabic
    return arabic_count / total_count > 0.5 if total_count > 0 else False





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

# app.py

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    # Get the current user's username
    username = current_user.username
    table_name = f"Transactions_Temp_{username}"

    try:
        # Establish the connection to the database
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()

        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file:
            try:
                # Read the first sheet of the Excel file
                df = pd.read_excel(file, sheet_name=0, dtype=str)

                # Ensure all necessary columns are present
                expected_columns = ['date', 'segment', 'type', 'sub_type', 'category', 'sub_category',
                                    'details', 'notes', 'sub_notes', 'transaction_description',
                                    'country_withdraw', 'country_used', 'account_name', 'currency',
                                    'payeer', 'paid_to', 'amount']
                for col in expected_columns:
                    if col not in df.columns:
                        flash(f'Missing column: {col}', 'error')
                        return redirect(request.url)

                # Detect if the Excel file is in Arabic and translate
                columns_to_check = ['segment', 'type', 'category', 'currency', 'country_withdraw', 'country_used']
                if is_excel_in_arabic(df, columns_to_check):
                    df = translate_dataframe(df, 'en')

                # Prepare the insert query
                insert_query = f'''
                    INSERT INTO {table_name} (date, segment, type, sub_type, category, sub_category, details, 
                    notes, sub_notes, transaction_description, country_withdraw, country_used, account_name, 
                    currency, payeer, paid_to, amount, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''

                # Iterate over the DataFrame and insert rows
                for _, row in df.iterrows():
                    row = row.where(pd.notnull(row), None)
                    row = row.tolist() + ['By uploading from website']
                    cursor.execute(insert_query, row)

                conn.commit()

                check_for_new_logs_optimized()

                flash('File uploaded and processed successfully!', 'message')

                # Emit WebSocket event to notify other clients
                socketio.emit('data_updated', {'room': table_name}, room=table_name)

                return redirect(url_for('transactions'))

            except ValueError as ve:
                conn.rollback()
                flash(f'Error processing file: {str(ve)}', 'error')
            except Exception as e:
                conn.rollback()
                flash(f'Error processing file: {str(e)}', 'error')
            finally:
                cursor.close()
                conn.close()

    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

    return redirect(url_for('transactions'))


@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    # Get the current user's username
    username = current_user.username
    table_name = f"Transactions_Temp_{username}"
    trigger_name = f"log_transaction_changes_{username}"  # Unique trigger name for each user table
    trigger_name_insert = f"log_transaction_insert_{username}"

    try:
        # Establish the connection to the database
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()

        # Create a user-specific table if it does not already exist
        create_table_query = f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            transaction_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            checkbox INT NOT NULL DEFAULT '0',
            ready INT NOT NULL DEFAULT '0',
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

        # Create a trigger if it does not already exist for updates
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
    -- Insert a log if both 'incorrect_columns' and 'ready' haven't changed
    IF NEW.incorrect_columns = OLD.incorrect_columns AND NEW.ready = OLD.ready THEN
        -- Insert a log
        INSERT INTO Transaction_Temp_Logs (username, transaction_id)
        VALUES ('{username}', NEW.transaction_id);
    END IF;
END;


            '''
            cursor.execute(create_trigger_query)
            conn.commit()

        # Create a trigger for inserts
        check_trigger_query = f'''
        SELECT COUNT(*)
        FROM information_schema.TRIGGERS
        WHERE TRIGGER_NAME = '{trigger_name_insert}' AND TRIGGER_SCHEMA = DATABASE();
        '''
        cursor.execute(check_trigger_query)
        trigger_exists_insert = cursor.fetchone()[0]

        if not trigger_exists_insert:
            create_trigger_query = f'''
            CREATE TRIGGER {trigger_name_insert}
            AFTER INSERT ON {table_name}
            FOR EACH ROW
            BEGIN
                INSERT INTO Transaction_Temp_Logs (username, transaction_id) 
                VALUES ('{username}', NEW.transaction_id);
            END;
            '''
            cursor.execute(create_trigger_query)
            conn.commit()

        # Handle any other logic you might want for transactions (like rendering the page)
        return render_template('Transactions.html')

    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

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


# app.py

@app.route('/download')
@login_required
def download_file():
    # Get the current user's username
    username = current_user.username  # Assuming `current_user` is defined via Flask-Login
    table_name = f"Transactions_Temp_{username}"
    lang = request.args.get('lang', 'en')  # Get the language parameter, default to 'en'
    
    if lang not in ['en', 'ar']:
        lang = 'en'  # Default to English if invalid language is provided

    try:
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor(dictionary=True)  # Use dictionary cursor for easier handling

        # Fetch data from the user-specific table
        query = f'SELECT * FROM {table_name} ORDER BY date DESC'
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

    # Convert the rows to a DataFrame
    df = pd.DataFrame(rows)

    # Define the columns you want to download
    to_download = ['date','segment', 'type', 'sub_type', 'category', 'sub_category','details', 'notes', 'sub_notes', 'transaction_description', 'account_name',
                   'currency', 'country_withdraw', 'country_used', 'payeer',
                   'paid_to', 'amount']

    # Ensure you only keep the columns you want
    df = df[to_download]

    # Translate data if language is Arabic
    if lang == 'ar':
        try:
            df = translate_dataframe(df, 'ar')  # Translate to Arabic before downloading
        except ValueError as ve:
            flash(f'Error translating data: {str(ve)}', 'error')
            return redirect(url_for('transactions'))
        except Exception as e:
            flash(f'Error translating data: {str(e)}', 'error')
            return redirect(url_for('transactions'))

    # Write the data to an Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)

    # Determine the download filename
    download_filename = f'{table_name}.xlsx'

    return send_file(output, download_name=download_filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/template_download', methods=['GET'])
@login_required
def template_download():
    try:
        lang = request.args.get('lang', 'en')  # Get selected language from the frontend
        if lang == 'ar':
            template_path = 'static/Transactions_Template_ar.xlsx'
        else:
            template_path = 'static/Transactions_Template_en.xlsx'
        return send_file(template_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading template: {str(e)}', 'error')
        return redirect(url_for('transactions'))
    

@app.route('/get_column_headers', methods=['GET'])
@login_required
def get_column_headers():
    try:
        # Get the current user's username
        username = current_user.username  # Assuming `current_user` is provided by Flask-Login
        table_name = f"Transactions_Temp_{username}"  # Table name for the current user

        # Connect to the database
        conn = mysql.connector.connect(**config.db_config)
        cursor = conn.cursor()

        # Query the column headers for the user-specific table
        cursor.execute(f'SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = %s', (table_name,))
        column_headers = [row[0] for row in cursor.fetchall()]

        if not column_headers:
            return jsonify({'status': 'error', 'message': 'No column headers found for the specified table.'}), 404

        return jsonify({'status': 'success', 'data': column_headers})

    except Exception as e:
        # Handle any errors that occur
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# Route to get row count dynamically from user-specific table
@app.route('/get_row_count', methods=['GET'])
@login_required
def get_row_count():
    try:
        # Construct the user-specific table name based on the logged-in user's username
        username = current_user.username  # Get the current user's username
        table_name = f"Transactions_Temp_{username}"  # Table name for the current user

        # Establish a database connection
        connection = mysql.connector.connect(**config.db_config)
        cursor = connection.cursor()

        # Prepare and execute the SQL query to count rows
        query = f"SELECT COUNT(*) FROM `{table_name}`"
        cursor.execute(query)
        
        # Fetch the row count result
        row_count = cursor.fetchone()[0]

        # Return the result as JSON
        return jsonify({'row_count': row_count})

    except mysql.connector.Error as err:
        return jsonify({'error': f"Database error: {str(err)}"}), 500

    except Exception as e:
        return jsonify({'error': f"Error: {str(e)}"}), 500

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Update `/update_transaction` to emit WebSocket events upon successful updates
@app.route('/update_transaction', methods=['POST'])
@login_required
def update_transaction():
    # Get the current user's username
    username = current_user.username  # Assuming Flask-Login provides current_user
    table_name = f"Transactions_Temp_{username}"

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
        check_for_new_logs_optimized()    
        # Emit WebSocket event to notify other clients about the update
        socketio.emit('data_updated', {'room': table_name}, room=table_name)

        # Return success message
        return jsonify(success=True)

    except Exception as e:
        # Handle and log errors
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
        cursor.execute(f'UPDATE {table_name} SET checkbox = 1 where ready = 1')
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
    print("Finalizing transactions...")
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



