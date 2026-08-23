import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def create_users_table():
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,

                    username VARCHAR(50) UNIQUE NOT NULL,

                    email VARCHAR(255) UNIQUE NOT NULL,

                    password_hash TEXT NOT NULL,

                    email_verified BOOLEAN DEFAULT FALSE,

                    verification_token TEXT,

                    verification_token_expiry TIMESTAMP,

                    reset_token TEXT,

                    reset_token_expiry TIMESTAMP,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

        connection.commit()

        print("Users table created successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    create_users_table()