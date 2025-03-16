from __future__ import annotations
from typing import NamedTuple
from typing import Self
from collections.abc import Generator
import getpass

import os
import sys
import time
import webbrowser
import argparse
import datetime

import mysql.connector
import mysql.connector.errorcode as errorcode

import pylast
import rich.console
import rich.progress


# GLOBAL VARIABLES
# ------------------------------------------------------------------------------
DATABSE_NAME = os.getenv("DATABASE_NAME")

__lastfm_network: pylast.LastFMNetwork = None

__console: rich.console.Console = None


# GENERAL UTILITIES
# ------------------------------------------------------------------------------
class LastFMError(Exception):
    pass


def log(msg) -> None:
    print(msg, file=sys.stderr)


def input_password(prompt: str) -> str:
    return getpass.getpass(prompt) if False else input(prompt)


# MYSQL UTIL FUNCTIONS
# ------------------------------------------------------------------------------
def mysql_user_exists(username: str) -> bool:
    with mysql_connection.cursor() as cursor:
        cursor.execute("SELECT sf_user_exists(%s)", (username,))
        return cursor.fetchone()[0] == 1


def mysql_user_authenticate(username: str, password: str) -> bool | None:
    with mysql_connection.cursor() as cursor:
        cursor.execute("SELECT sf_user_authenticate(%s, %s)", (username, password))
        result = cursor.fetchone()[0]
        if result is None:
            return None
        else:
            return result == 1


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


def lastfm_network() -> pylast.LastFMNetwork:
    if __lastfm_network is None:
        raise LastFMError
    return __lastfm_network


def lastfm_user_auth(retry_count: int) -> tuple[str, str] | None:
    skg = pylast.SessionKeyGenerator(lastfm_network())
    url = skg.get_web_auth_url()

    webbrowser.open(url)

    with __console.status("Authorizing application..."):
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

                artist = pylast._extract(track_node, "artist")
                artist_mbid = track_node.getElementsByTagName("artist")[0].getAttribute(
                    "mbid"
                )

                album = pylast._extract(track_node, "album")
                album_mbid = track_node.getElementsByTagName("album")[0].getAttribute(
                    "mbid"
                )

                track = pylast._extract(track_node, "name")
                track_mbid = pylast._extract(track_node, "mbid")

                timestamp = track_node.getElementsByTagName("date")[0].getAttribute(
                    "uts"
                )

                print(track, track_mbid, artist_mbid, album_mbid)
                # print(track)

                progress.update(task, advance=1)

            time.sleep(0.01)

    return None


# SCHEMA TYPES
# ------------------------------------------------------------------------------
class MBEntry(NamedTuple):
    mbid: str
    name: str
    # genres: Generator[str]


class Artist(MBEntry):
    def get_albums(self: Self):
        pass


class Album(MBEntry):
    artist: Artist

    def get_tracks(self: Self):
        pass


class Track(MBEntry):
    album: Album | None
    artist: Artist
    length: datetime.time


class User(NamedTuple):
    name: str
    admin: bool = False

    @classmethod
    def create(cls: any, retry_count: int = 5) -> Self | None:
        if (result := lastfm_user_auth(retry_count)) is None:
            return None

        session_key, username = result

        if mysql_user_exists(username):
            mysql_user_update_session_key(username, session_key)
            log(f"User '{username}' already exists")
            return None

        print(f"Username: {username}")
        password = input_password("Password: ")

        mysql_user_create(username, password, session_key)

        return cls(username)

    @classmethod
    def login(cls: any, username: str, password: str) -> Self | None:
        is_admin = mysql_user_authenticate(username, password)
        if is_admin is None:
            return None
        else:
            return cls(username, is_admin)

    def lastfm(self: Self) -> pylast.User:
        return lastfm_network().get_user(self.name)


class Score(NamedTuple):
    user: User
    entry: MBEntry
    score: int


class Scrobble(NamedTuple):
    time: datetime.datetime
    track: Track
    user: User


# MAIN FUNCTIONS
# ------------------------------------------------------------------------------
def menu_sign_up(args: argparse.Namespace) -> bool:
    if (user := User.create()) is None:
        log("Failed to create account.")
        return False

    log(f"Created user {user.name}")
    return True


def menu_login(args: argparse.Namespace) -> bool:
    username = input("Username: ")
    password = input_password("Password: ")
    user = User.login(username, password)

    if user is None:
        log("Invalid username or password.")
        return False

    log("Sign in successful.")

    # lastfm_user_import(user.lastfm())

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

    __lastfm_network = lastfm_init()
    __console = rich.console.Console()

    try:
        main()
    except KeyboardInterrupt:
        pass
    except LastFMError:
        log("Last.FM support disabled.")

    mysql_connection.commit()
    mysql_connection.close()
