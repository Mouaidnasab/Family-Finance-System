import mysql.connector
from flask_bcrypt import Bcrypt
from flask import Flask
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


app = Flask(__name__)
bcrypt = Bcrypt(app)



def hash_and_update_passwords():
    try:
        # Connect to the database
        cnx = mysql.connector.connect(**config.db_config)
        cursor = cnx.cursor()
        
        # Select all members and their plaintext passwords
        select_query = "SELECT member_id, password FROM Members"
        cursor.execute(select_query)
        members = cursor.fetchall()

        # Hash each password and update the database
        for member_id, plaintext_password in members:
            hashed_password = bcrypt.generate_password_hash(plaintext_password).decode('utf-8')
            update_query = "UPDATE Members SET password = %s WHERE member_id = %s"
            cursor.execute(update_query, (hashed_password, member_id))
        
        # Commit the changes to the database
        cnx.commit()
        print("All passwords have been hashed and updated successfully.")
    
    except Exception as e:
        # Rollback in case of error
        cnx.rollback()
        print("Failed to update passwords: ", str(e))
    
    finally:
        # Close the cursor and the connection
        cursor.close()
        cnx.close()

if __name__ == '__main__':
    with app.app_context():
        hash_and_update_passwords()
