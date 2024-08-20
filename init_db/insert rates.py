import csv
import mysql.connector
from datetime import datetime
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


# Get the directory of the script
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, 'static data', 'rates.csv')

# Connect to the MySQL database
connection = mysql.connector.connect(**config.db_config)
cursor = connection.cursor()

# Create the rates table if it doesn't exist
create_table_query = '''
CREATE TABLE IF NOT EXISTS Rates (
    date DATE PRIMARY KEY,
    usd_to_bgn FLOAT,
    usd_to_eur FLOAT,
    usd_to_try FLOAT,
    bgn_to_usd FLOAT,
    eur_to_usd FLOAT,
    try_to_usd FLOAT
)
'''
cursor.execute(create_table_query)

# Check if the file exists and has the correct path
if not os.path.isfile(file_path):
    print(f"Error: File '{file_path}' does not exist or is not accessible.")
else:
    # Read data from CSV file
    try:
        with open(file_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader)  # Skip the header row
            data = []
            for row in csv_reader:
                # Convert date format from 'MM/DD/YYYY' to 'YYYY-MM-DD'
                date_str = row[0]
                date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
                data.append([formatted_date] + row[1:])
    except Exception as e:
        print(f"Error reading the file: {e}")

    # Insert data into the rates table
    try:
        insert_query = '''
        INSERT INTO Rates (date, usd_to_bgn, usd_to_eur, usd_to_try, bgn_to_usd, eur_to_usd, try_to_usd) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            usd_to_bgn = VALUES(usd_to_bgn),
            usd_to_eur = VALUES(usd_to_eur),
            usd_to_try = VALUES(usd_to_try),
            bgn_to_usd = VALUES(bgn_to_usd),
            eur_to_usd = VALUES(eur_to_usd),
            try_to_usd = VALUES(try_to_usd)
        '''
        cursor.executemany(insert_query, data)
        # Commit the transaction
        connection.commit()
    except Exception as e:
        print(f"Error inserting data into the database: {e}")

# Close the database connection
cursor.close()
connection.close()
