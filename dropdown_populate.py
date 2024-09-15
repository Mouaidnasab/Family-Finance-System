import mysql.connector
import config


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
