import os
import sys
import time
import webbrowser

import mysql.connector
import mysql.connector.errorcode as errorcode

import pylast


# GENERAL UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def fatal(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


# MYSQL UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def mysql_setup() -> mysql.connector.MySQLConnection:
    """ "
    Returns a connected MySQL connector instance, if connection is successful.
    If unsuccessful, exits.
    """
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            port="3306",
            password="",
            database="finalprojectdb",
        )
    except mysql.connector.Error as err:
        # Remember that this is specific to _database_ users, not
        # application users. So is probably irrelevant to a client in your
        # simulated program. Their user information would be in a users table
        # specific to your database; hence the DEBUG use.
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR and DEBUG:
            sys.stderr("Incorrect username or password when connecting to DB.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR and DEBUG:
            sys.stderr("Database does not exist.")
        elif DEBUG:
            sys.stderr(err)
        else:
            # A fine catchall client-facing message.
            sys.stderr("An error occurred, please contact the administrator.")
        return None


# LASTFM UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def lastfm_setup() -> pylast.LastFMNetwork:
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


def lastfm_user_auth(
    network: pylast.LastFMNetwork, retry_count: int
) -> tuple[str, str]:
    pass


# MAIN FUNCTION
# ------------------------------------------------------------------------------
def main():
    n = setup()
    x = user_auth(n, 10)
    print(f"{x}")


if __name__ == "__main__":
    if (mysql_connection := mysql_setup()) is None:
        sys.exit(1)

    lastfm_network = lastfm_setup()

    main()

    mysql_connection.close()
