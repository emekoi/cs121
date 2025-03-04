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


# LASTFM UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def lastfm_init() -> pylast.LastFMNetwork:
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")

    if API_KEY is None or API_SECRET is None:
        return None

    return pylast.LastFMNetwork(API_KEY, API_SECRET)


def lastfm_user_create() -> tuple[str, str]:
    skg = pylast.SessionKeyGenerator(lastfm_network)
    url = skg.get_web_auth_url()

    print(f"Please authorize this application to access your account: {url}\n")
    webbrowser.open(url)

    while True:
        try:
            return skg.get_web_auth_session_key_username(url)
        except pylast.WSError:
            # sleep to prevent hitting rate limits
            time.sleep(1)


# MAIN FUNCTIONS
# ------------------------------------------------------------------------------
def user_login(username: str, password: str):
    with mysql_connection.cursor() as cursor:
        cursor.execute("SELECT sp_user_authenticate(%s, %s)", (username, password))
        res = cursor.fetchone()
        print(res[0])
        return res


def user_create():
    if lastfm_network is None:
        return None

    session_key, username = lastfm_user_create()
    password = input("New Password: ")

    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_user_create(%s, %s, %s)", (username, password, session_key)
        )
        mysql_connection.commit()
        print(username, password, session_key, cursor.fetchone())
        return username


def main():
    # n = setup()
    # x = user_auth(n, 10)
    # print(f"{x}")
    # user_create()
    user_login("emekoi", "password")
    print("DONE")


if __name__ == "__main__":
    DATABSE_NAME = os.getenv("DATABSE_NAME") or "finalprojectdb"

    try:
        mysql_connection = mysql.connector.connect(
            host="localhost",
            user="root",
            port="3306",
            password="",
            database=DATABSE_NAME,
        )
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            log("Incorrect username or password when connecting to DB")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            log("Database does not exist")
        else:
            log(f"Failed to connect to DB: {err}")

        sys.exit(1)

    lastfm_network = lastfm_init()

    main()

    mysql_connection.commit()
    mysql_connection.close()
