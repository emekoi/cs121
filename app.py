import os
import sys
import time
import webbrowser

import mysql.connector
import mysql.connector.errorcode as errorcode

import pylast


# GENERAL UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def log(msg):
    print(msg, file=sys.stderr)


# MYSQL UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def mysql_init(database: str) -> mysql.connector.MySQLConnection:
    # attempt to connect to MySQL
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        port="3306",
        password="",
    )

    try:
        # attempt to connect to the specified database
        connection.databse = database
    except mysql.connector.Error as err:
        # if the database doesn't exist, attempt to create it and connect
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            with connection.cursor() as cursor:
                cursor.execute("CREATE DATABASE %s", (database,))
                connection.databse = database
                # TODO: setup database here
        else:
            raise err

    return connection

# LASTFM UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def lastfm_init() -> pylast.LastFMNetwork:
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")

    if API_KEY is None or API_SECRET is None:
        return None

    return pylast.LastFMNetwork(API_KEY, API_SECRET)


def lastfm_user_create(
    network: pylast.LastFMNetwork, retry_count: int
) -> tuple[str, str]:
    skg = pylast.SessionKeyGenerator(network)
    url = skg.get_web_auth_url()

    print(f"Please authorize this script to access your account: {url}\n")
    webbrowser.open(url)

    while retry_count > 0:
        retry_count -= 1
        try:
            return skg.get_web_auth_session_key(url)
        except pylast.WSError:
            # sleep to prevent hitting
            time.sleep(1)


# MAIN FUNCTIONS
# ------------------------------------------------------------------------------
def user_auth(username: str, password: str):
    with mysql_connection.cursor() as cursor:
        cursor.execute("SELECT @@version")
        res = cur.fetchone()
        print(res[0])

def main():
    # n = setup()
    # x = user_auth(n, 10)
    # print(f"{x}")
    print(10)

if __name__ == "__main__":
    try:
        mysql_connection = mysql_init("finalprojectdb")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            log("Incorrect username or password when connecting to DB")
        else:
            log(f"Failed to connect to DB: {err}")

        sys.exit(1)

    lastfm_network = lastfm_init()

    main()

    mysql_connection.close()
