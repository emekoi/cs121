import os
import sys
import time
import webbrowser
import argparse

import mysql.connector
import mysql.connector.errorcode as errorcode

import pylast
import rich.console
import rich.progress


# GENERAL UTILITIES
# ------------------------------------------------------------------------------
class LastFMError(Exception):
    pass


def log(msg) -> None:
    print(msg, file=sys.stderr)


# MYSQL UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def mysql_user_exists(username: str) -> bool:
    with mysql_connection.cursor() as cursor:
        cursor.execute("SELECT sf_user_exists(%s)", (username,))
        return cursor.fetchone()[0] == 1


def mysql_user_authenticate(username: str, password: str) -> bool:
    with mysql_connection.cursor() as cursor:
        cursor.execute("SELECT sf_user_authenticate(%s, %s)", (username, password))
        return cursor.fetchone()[0] == 1


# MYSQL UTIL PROCEDURES
# ------------------------------------------------------------------------------
def mysql_user_create(username: str, password: str, session_key: str) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_user_create(%s, %s, %s)", (username, password, session_key)
        )
        mysql_connection.commit()


def mysql_user_update_session_key(username: str, session_key: str) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_user_update_session_key(%s, %s)", (username, session_key)
        )


# LASTFM UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def lastfm_init() -> pylast.LastFMNetwork:
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")

    if API_KEY is None or API_SECRET is None:
        return None

    return pylast.LastFMNetwork(API_KEY, API_SECRET)


def lastfm_user_auth(retry_count: int) -> tuple[str, str]:
    skg = pylast.SessionKeyGenerator(lastfm_network)
    url = skg.get_web_auth_url()

    webbrowser.open(url)

    with console.status("Authorizing application..."):
        while retry_count > 0:
            retry_count -= 1

            try:
                return skg.get_web_auth_session_key_username(url)
            except pylast.WSError:
                # sleep to prevent hitting rate limits
                time.sleep(1)

    log("Unable to authorize application.")
    return None


def lastfm_user_import(user: pylast.User) -> any:
    scrobbles_remaining = min(10, user.get_playcount())

    params = user._get_params()
    params["limit"] = scrobbles_remaining

    with rich.progress.Progress() as progress:
        task = progress.add_task("Importing...", total=scrobbles_remaining)

        while not progress.finished:
            for track_node in pylast._collect_nodes(
                params["limit"],
                user,
                user.ws_prefix + ".getRecentTracks",
                True,
                params,
                stream=True,
            ):
                # prevent the now playing track from sneaking in
                if track_node.hasAttribute("nowplaying"):
                    continue

                track = pylast._extract(track_node, "name")
                track_mbid = pylast._extract(track_node, "mbid")

                # artist      = pylast._extract(track_node, "artist")
                artist_mbid = track_node.getElementsByTagName("artist")[0].getAttribute(
                    "mbid"
                )

                # album      = pylast._extract(track_node, "album")
                album_mbid = track_node.getElementsByTagName("album")[0].getAttribute(
                    "mbid"
                )

                # timestamp = track_node.getElementsByTagName("date")[0].getAttribute("uts")

                print(track, track_mbid, artist_mbid, album_mbid)

                progress.update(task, advance=1)
                time.sleep(0.01)

    return None


# USER FUNCTIONS
# ------------------------------------------------------------------------------
def user_create(retry_count: int = 5) -> pylast.User:
    if lastfm_network is None:
        raise LastFMError

    if (result := lastfm_user_auth(retry_count)) is None:
        return None

    session_key, username = result

    if mysql_user_exists(username):
        mysql_user_update_session_key(username, session_key)
        log(f"User '{username}' already exists")
        return None

    print(f"Username: {username}")
    password = input("Password: ")

    mysql_user_create(username, password, session_key)
    user = lastfm_network.get_user(username)
    # lastfm_user_import(user)

    return user


def user_login(username: str, password: str) -> bool:
    return mysql_user_authenticate(username, password)


# MAIN FUNCTIONS
# ------------------------------------------------------------------------------
def menu_sign_up(args: argparse.Namespace) -> bool:
    if (user := user_create()) is None:
        log("Failed to create account.")
        return False

    log(f"Created user {user.name}")
    return True


def menu_login(args: argparse.Namespace) -> bool:
    username = input("Username: ")
    password = input("Password: ")
    if not user_login(username, password):
        log("Invalid username or password.")
        return False

    log("Sign in successful.")

    user = lastfm_network.get_user(username)
    lastfm_user_import(user)

    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    parser_login = subparsers.add_parser("login")
    parser_login.set_defaults(func=menu_login)

    parser_sign_up = subparsers.add_parser("sign-up")
    parser_sign_up.set_defaults(func=menu_sign_up)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    DATABSE_NAME = os.getenv("DATABASE_NAME")

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
    except LastFMError:
        log("Last.FM support disabled.")

    mysql_connection.commit()
    mysql_connection.close()
