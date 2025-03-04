import os
import sys
import time
import webbrowser

import mysql.connector
import mysql.connector.errorcode as errorcode

import pylast
import rich.console


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

    webbrowser.open(url)

    with console.status("Authorizing Application..."):
        while True:
            try:
                return skg.get_web_auth_session_key_username(url)
            except pylast.WSError:
                # sleep to prevent hitting rate limits
                time.sleep(1)


# USER FUNCTIONS
# ------------------------------------------------------------------------------
def user_login(username: str, password: str):
    with mysql_connection.cursor() as cursor:
        cursor.execute("SELECT sp_user_authenticate(%s, %s)", (username, password))
        return cursor.fetchone()[0] == 1


def user_create():
    if lastfm_network is None:
        return None

    session_key, username = lastfm_user_create()
    print(f"Username: {username}")
    password = input("Password: ")

    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_user_create(%s, %s, %s)", (username, password, session_key)
        )
        mysql_connection.commit()
        return username


# MAIN FUNCTIONS
# ------------------------------------------------------------------------------
def menu_sign_up(args):
    username = user_create()
    log(f"Created user {username}")


def menu_login(args):
    username = input("Username: ")
    password = input("Password: ")
    if not user_login(username, password):
        log("Invalid username or password.")
    log("Sign in successful.")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    parser_login = subparsers.add_parser("login")
    parser_login.set_defaults(func=menu_login)

    parser_sign_up = subparsers.add_parser("sign-up")
    parser_sign_up.set_defaults(func=menu_sign_up)

    args = parser.parse_args()
    args.func(args)


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
    console = rich.console.Console()

    try:
        main()
    except KeyboardInterrupt:
        pass

    mysql_connection.commit()
    mysql_connection.close()
