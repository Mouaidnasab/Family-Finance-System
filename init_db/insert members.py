import mysql.connector
import csv
import os


# Get the directory of the script
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, 'static data', 'members.csv')



# Connect to MySQL database
conn = mysql.connector.connect(
    host="localhost",
    user="mouaid_admin",
    password="0991553333",
    database="Finance"
)
cursor = conn.cursor()

# Function to convert string with commas to float
def convert_to_float(value):
    try:
        return float(value.replace(',', ''))
    except ValueError:
        return None

# Function to insert data from CSV file into the table
def insert_data_from_csv(csv_file_path):
    with open(csv_file_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Print headers read by DictReader
        headers = reader.fieldnames
        print(f"CSV Headers: {headers}")
        
        for row in reader:
            try:
                cursor.execute('''
                    INSERT INTO members (
                        member_id, first_name, last_name
                    ) VALUES (%s, %s, %s)
                ''', (
                    row['Customer_id'], row['First_Name'], row['Last_Name']
                ))
            except KeyError as e:
                print(f"KeyError: {e} - Please check your CSV file headers and ensure they match the database column names.")
            except ValueError as e:
                print(f"ValueError: {e} - Please check your data types in the CSV file.")
            except Exception as e:
                print(f"Unexpected error: {e}")

    # Commit changes and close the connection
    conn.commit()

# Example usage
insert_data_from_csv(file_path)

# Close the connection
conn.close()
