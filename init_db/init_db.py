import mysql.connector
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def initialize_db():
    # Connect to the MySQL database
    conn = mysql.connector.connect(**config.db_config)
    cursor = conn.cursor()

    # SQL script to drop and create the tables
    cursor.execute("DROP TABLE IF EXISTS Details;")
    cursor.execute("DROP TABLE IF EXISTS Amounts;")
    cursor.execute("DROP TABLE IF EXISTS Transactions;")
    cursor.execute("DROP TABLE IF EXISTS Rates;")
    cursor.execute("DROP TABLE IF EXISTS Transactions_Details;")
    cursor.execute("DROP TABLE IF EXISTS Transactions_Temp;")
    cursor.execute("DROP TABLE IF EXISTS dd_Segments;")
    cursor.execute("DROP TABLE IF EXISTS dd_Types;")
    cursor.execute("DROP TABLE IF EXISTS dd_Sub_Types;")
    cursor.execute("DROP TABLE IF EXISTS dd_Categories;")
    cursor.execute("DROP TABLE IF EXISTS dd_Sub_Categories;")
    cursor.execute("DROP TABLE IF EXISTS dd_Countries;")
    cursor.execute("DROP TABLE IF EXISTS dd_Account_Names;")
    cursor.execute("DROP TABLE IF EXISTS dd_Currencies;")
    cursor.execute("DROP TABLE IF EXISTS Accounts;")
    cursor.execute("DROP TABLE IF EXISTS Members;")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Members (
            member_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,
            username VARCHAR(255) NOT NULL default '' unique,
            password VARCHAR(255) NOT NULL default ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Accounts (
            account_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            segment VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            country VARCHAR(255) NOT NULL,
            currency VARCHAR(10) NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Transactions (
            transaction_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            account_id INT DEFAULT NULL,
            date DATE NOT NULL,
            segment VARCHAR(255) DEFAULT NULL,
            type VARCHAR(255) DEFAULT NULL,
            sub_type VARCHAR(255) DEFAULT NULL,
            category VARCHAR(255) DEFAULT NULL,
            sub_category VARCHAR(255) DEFAULT NULL,
            country_used VARCHAR(255) DEFAULT NULL,
            payeer_id INT DEFAULT NULL,
            paid_to_id INT DEFAULT NULL,
            to_whom_id INT DEFAULT NULL,
            KEY account_id (account_id),
            CONSTRAINT transactions_ibfk_1 FOREIGN KEY (account_id) REFERENCES Accounts (account_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Details (
            transaction_id INT NOT NULL PRIMARY KEY,
            details TEXT,
            notes TEXT,
            sub_notes TEXT,
            transaction_description TEXT,
            how_it_is_inserted TEXT,
            CONSTRAINT details_ibfk_1 FOREIGN KEY (transaction_id) REFERENCES Transactions (transaction_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Amounts (
            transaction_id INT NOT NULL PRIMARY KEY,
            amount DECIMAL(10,2) NOT NULL,
            vat DECIMAL(10,2) DEFAULT NULL,
            in_usd DECIMAL(10,2) DEFAULT NULL,
            in_sr DECIMAL(10,2) DEFAULT NULL,
            CONSTRAINT amounts_ibfk_1 FOREIGN KEY (transaction_id) REFERENCES Transactions (transaction_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Rates (
            date DATE NOT NULL PRIMARY KEY,
            usd_to_bgn FLOAT DEFAULT NULL,
            usd_to_eur FLOAT DEFAULT NULL,
            usd_to_try FLOAT DEFAULT NULL,
            bgn_to_usd FLOAT DEFAULT NULL,
            eur_to_usd FLOAT DEFAULT NULL,
            try_to_usd FLOAT DEFAULT NULL
        )
    ''')


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Transactions_Temp (
            transaction_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            checkbox int NOT NULL DEFAULT '0',
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
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dd_Segments (
            segment_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dd_Types (
            type_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dd_Sub_Types (
            sub_type_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dd_Categories (
            category_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dd_Sub_Categories (
            sub_category_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dd_Countries (
            country_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dd_Account_Names (
            account_name_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dd_Currencies (
            currency_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        )
    ''')

    # Commit and close the connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()
    print("Database initialized successfully.")
