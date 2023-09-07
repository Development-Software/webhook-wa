import mysql.connector
import os

config_db = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE"),
}

onedrive_config = {
    "client_id": os.getenv("CLIENT_ID"),
    "scope": os.getenv("SCOPE"),
    "client_secret": os.getenv("CLIENT_SECRET"),
    "tenant_id": os.getenv("TENANT_ID"),
    "user_id": os.getenv("USER_ID"),
    "file_name": os.getenv("FILE_NAME"),
    "path": os.getenv("ONEDRIVE_PATH"),
}


def connect_db():
    db = mysql.connector.connect(**config_db)
    return db