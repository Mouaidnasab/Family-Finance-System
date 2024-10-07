import mysql.connector
import config
from datetime import datetime,date
import time


def populate_unique_values():
    conn = mysql.connector.connect(**config.db_config)
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
    SELECT 
        CONCAT(Accounts.name, ' ', Accounts.currency) AS name_currency
    FROM 
        Accounts
    WHERE 
        Accounts.name IS NOT NULL
    ON DUPLICATE KEY UPDATE name=VALUES(name);

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

def fetch_dropdown_data(conn):
    cursor = conn.cursor(dictionary=True)
    
    dropdown_data = {}

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
    accounts = [row['name'] for row in cursor.fetchall()]
    dropdown_data['account_name'] = [row['name'] for row in cursor.fetchall()]

    # Fetch currencies
    cursor.execute('SELECT DISTINCT name FROM dd_Currencies')
    dropdown_data['currency'] = [row['name'] for row in cursor.fetchall()]

    # Fetch payeers (Members + internal accounts)
    cursor.execute("SELECT CONCAT(first_name, ' ', last_name) AS full_name FROM Members")
    members = [row['full_name'] for row in cursor.fetchall()]

    cursor.execute("SELECT name AS accountname FROM Accounts WHERE segment = 'internal'")
    dropdown_data['account_name'] = [row['accountname'] for row in cursor.fetchall()]

    # Combine both payeers and internal accounts
    dropdown_data['payeer'] = members + accounts 

    # Combine both paid_to members and internal accounts
    dropdown_data['paid_to'] = members + accounts

    return dropdown_data


# Function to validate a single transaction row
def validate_transaction_row(row, dropdown_data):
    # Define required columns
    required_columns = ['date', 'segment', 'type', 'sub_type', 'category', 'country_withdraw',
                        'country_used', 'account_name', 'currency', 'payeer', 'paid_to', 'amount']
    
    # Initialize the list of incorrect columns and the ready flag
    incorrect_columns = []
    ready = 1
    
    # Check if any required column is empty
    for column in required_columns:
        if not row.get(column):  # Check if the column is empty or None
            incorrect_columns.append(column)
    
    # Check non-empty columns against dropdown data
    for column in required_columns:
        if row.get(column):  # Only check non-empty fields
            if column == 'amount':
                continue  # Skip amount validation

            # Check for date columns and validate their format
            if column == 'date':
                try:
                    # If the value is already a date object, skip strptime
                    if isinstance(row[column], (datetime, date)):  # Check for datetime or date
                        pass  # It's already a datetime or date object, no need to parse
                    elif isinstance(row[column], str):
                        # Parse the date if it's a string
                        datetime.strptime(row[column], '%Y-%m-%d')
                    else:
                        incorrect_columns.append(column)  # Not a valid date format
                except ValueError:
                    incorrect_columns.append(column)
                continue  # Skip further validation for date columns
            
            # Map the column to its corresponding dropdown list
            if column == 'country_withdraw' or column == 'country_used':
                dropdown_list = dropdown_data.get('country', [])
            else:
                dropdown_list = dropdown_data.get(column, [])
            
            # If the value is not in the dropdown list, add it to incorrect columns
            if row[column] not in dropdown_list:
                incorrect_columns.append(column)
    
    # Set ready to 0 if there are any incorrect columns
    if incorrect_columns:
        ready = 0
    
    # Return the list of incorrect columns and the ready flag
    return incorrect_columns, ready
def process_transaction_changes_in_batch(logs, dropdown_data):
    # Connect to the database
    conn = mysql.connector.connect(**config.db_config)
    cursor = conn.cursor(dictionary=True)

    log_ids_to_delete = []

    for log in logs:
        log_id, username, transaction_id = log

        # Pull the changed row from the user-specific table Transactions_Temp_{username}
        table_name = f"Transactions_Temp_{username}"
        cursor.execute(f"SELECT * FROM {table_name} WHERE transaction_id = %s", (transaction_id,))
        transaction_row = cursor.fetchone()

        if transaction_row:
            # Run validation
            incorrect_columns, ready = validate_transaction_row(transaction_row, dropdown_data)

            # Convert the list of incorrect columns to a comma-separated string
            incorrect_columns_str = ', '.join(incorrect_columns)

            # Check if 'incorrect_columns' or 'ready' fields have actually changed
            if incorrect_columns_str != transaction_row['incorrect_columns'] or ready != transaction_row['ready']:
                # Only update the table if necessary to prevent unnecessary trigger activation
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET incorrect_columns = %s, ready = %s
                    WHERE transaction_id = %s
                """, (incorrect_columns_str, ready, transaction_id))

            # Track processed log for deletion
            log_ids_to_delete.append(log_id)

    # Commit all updates
    conn.commit()

    # Remove processed logs in bulk
    if log_ids_to_delete:
        delete_logs_in_bulk(cursor, log_ids_to_delete)
        conn.commit()

    cursor.close()
    conn.close()


def delete_logs_in_bulk(cursor, log_ids):
    # Perform a bulk delete for processed logs
    format_strings = ','.join(['%s'] * len(log_ids))
    cursor.execute(f"DELETE FROM Transaction_Temp_Logs WHERE log_id IN ({format_strings})", log_ids)
    


def check_for_new_logs_optimized():
    print("Checking for new logs...")
    # Connect to the database using the global config
    conn = mysql.connector.connect(**config.db_config)
    
    cursor = conn.cursor()

    # Fetch logs that haven't been processed yet in a batch
    cursor.execute("SELECT log_id, username, transaction_id FROM Transaction_Temp_Logs")
    logs = cursor.fetchall()

    # Fetch dropdown data once for the batch
    dropdown_data = fetch_dropdown_data(conn)

    # Process all logs in batch
    if logs:
        process_transaction_changes_in_batch(logs, dropdown_data)

    cursor.close()
    conn.close()










# # Test case setup
# def run_tests():
#     # Sample dropdown data from the database
#     conn = mysql.connector.connect(**config.db_config)
#     print("Connection established")

#     # Use the fetch_dropdown_data function to get dropdown data
#     dropdown_data = fetch_dropdown_data(conn)

#     conn.close()

#     # Test Case 1: All fields valid
#     print("Test Case 1: All fields valid")
#     transaction_row_1 = {
#         'date': '2024-09-16',
#         'segment': 'Personal',
#         'type': 'Income',
#         'sub_type': 'Direct',
#         'category': 'Fun & Vacation',
#         'country_withdraw': 'Saudi Arabia',
#         'country_used': 'Saudi Arabia',
#         'account_name': 'IS Bank Ahmad',
#         'currency': 'SR',
#         'payeer': 'IS Bank Ahmad USD',
#         'paid_to': 'IS Bank Ahmad USD',
#         'amount': 150.00
#     }
#     incorrect_columns, ready = validate_transaction_row(transaction_row_1, dropdown_data)
#     print(f"Incorrect Columns: {incorrect_columns} , Ready: {ready}\n")
    
#     # Test Case 2: Missing all required fields
#     print("Test Case 2: Missing all required fields")
#     transaction_row_2 = {
#         'date': None,
#         'segment': None,
#         'type': None,
#         'sub_type': None,
#         'category': None,
#         'country_withdraw': None,
#         'country_used': None,
#         'account_name': None,
#         'currency': None,
#         'payeer': None,
#         'paid_to': None,
#         'amount': None
#     }
#     incorrect_columns, ready = validate_transaction_row(transaction_row_2, dropdown_data)
#     print(f"Incorrect Columns: {incorrect_columns}, Ready: {ready}\n")
    
#     # Test Case 3: Some fields missing
#     print("Test Case 3: Some fields missing")
#     transaction_row_3 = {
#         'date': '2024-09-16',
#         'segment': 'Retail',
#         'type': 'Sale',
#         'sub_type': None,  # Missing
#         'category': 'Clothing',
#         'country_withdraw': 'Saudi Arabia',
#         'country_used': 'Saudi Arabia',
#         'account_name': None,  # Missing
#         'currency': 'SAR',
#         'payeer': 'John Doe',
#         'paid_to': 'Vendor XYZ',
#         'amount': 150.00
#     }
#     incorrect_columns, ready = validate_transaction_row(transaction_row_3, dropdown_data)
#     print(f"Incorrect Columns: {incorrect_columns}, Ready: {ready}\n")
    
#     # Test Case 4: Invalid dropdown values
#     print("Test Case 4: Invalid dropdown values")
#     transaction_row_4 = {
#         'date': '2024-09-16',
#         'segment': 'Invalid Segment',  # Not in dropdown
#         'type': 'Invalid Type',  # Not in dropdown
#         'sub_type': 'Invalid Sub_Type',  # Not in dropdown
#         'category': 'Invalid Category',  # Not in dropdown
#         'country_withdraw': 'Invalid Country',  # Not in dropdown
#         'country_used': 'Invalid Country',  # Not in dropdown
#         'account_name': 'Invalid Account',  # Not in dropdown
#         'currency': 'Invalid Currency',  # Not in dropdown
#         'payeer': 'Invalid Payeer',  # Not in dropdown
#         'paid_to': 'Invalid Paid_To',  # Not in dropdown
#         'amount': 500.00  # Not in dropdown
#     }
#     incorrect_columns, ready = validate_transaction_row(transaction_row_4, dropdown_data)
#     print(f"Incorrect Columns: {incorrect_columns}, Ready: {ready}\n")
    
#     # Test Case 5: All fields empty except valid ones
#     print("Test Case 5: Some valid values")
#     transaction_row_5 = {
#         'date': None,
#         'segment': 'Retail',
#         'type': None,
#         'sub_type': 'Offline',
#         'category': None,
#         'country_withdraw': None,
#         'country_used': 'United States',
#         'account_name': 'Secondary Account',
#         'currency': 'USD',
#         'payeer': None,
#         'paid_to': None,
#         'amount': 200.00
#     }
#     incorrect_columns, ready = validate_transaction_row(transaction_row_5, dropdown_data)
#     print(f"Incorrect Columns: {incorrect_columns}, Ready: {ready}\n")

# # Run the test cases
# if __name__ == "__main__":
#     run_tests()
