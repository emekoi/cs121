from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timedelta
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Header, Footer, Placeholder
from typing import Self

import argparse
import os
import sys
import time
import webbrowser

import mysql.connector
import mysql.connector.errorcode as errorcode

import pylast
import pyparsing as pp
import rich.console
import rich.progress
import rich.prompt


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


# command query +x:arg1,arg2,arg3
def parse_user_command(input_str: str) -> any:
    arg = pp.Word(pp.alphas) | pp.quoted_string.set_parse_action(pp.remove_quotes)
    flag_name = pp.Regex("\\+(\\w+):", as_group_list=True).set_parse_action(
        lambda x: x[0][0]
    )
    flag_args = pp.delimited_list(arg, ",")
    flag = pp.Group(flag_name + flag_args).set_parse_action(
        lambda xs: [{"name": x[0], "args": x[1:]} for x in xs]
    )
    command = pp.Word(pp.alphas).set_results_name("command")
    query = arg.set_results_name("query")
    flags = pp.ZeroOrMore(flag).set_results_name("flags", list_all_matches=True)
    parser = command + (query & flags)

    try:
        return parser.parse_string(input_str).as_dict()
    except pp.ParseException:
        return None


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


def mysql_user_last_update(username: str) -> int:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "SELECT user_last_update FROM users WHERE user_name = %s", (username,)
        )
        return cursor.fetchone()[0]


def mysql_user_scrobble_count(username: str) -> int:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM scrobbles WHERE user_name = %s", (username,)
        )
        return cursor.fetchone()[0]


# MYSQL UTIL PROCEDURES
# ------------------------------------------------------------------------------
def mysql_user_create(username: str, password: str, session_key: str) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_user_create(%s, %s, %s)", (username, password, session_key)
        )
        mysql_connection.commit()
    mysql_connection.commit()


def mysql_user_update_session_key(username: str, session_key: str) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_user_update_session_key(%s, %s)", (username, session_key)
        )
    mysql_connection.commit()


def mysql_artist_add(mbid: str, name: str) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute("CALL sp_artist_add(%s, %s)", (mbid, name))
    mysql_connection.commit()


def mysql_album_add(mbid: str, name: str, artist: str) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute("CALL sp_album_add(%s, %s, %s)", (mbid, name, artist))
    mysql_connection.commit()


def mysql_track_add(
    mbid: str, name: str, artist: str, album: str | None, length: timedelta
) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_track_add(%s, %s, %s, %s, %s)",
            (mbid, name, artist, album, length),
        )
    mysql_connection.commit()


def mysql_scrobble_add(username: str, time: int, track: str) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_user_add_scrobble(%s, %s, %s)",
            (username, time, track),
        )
    mysql_connection.commit()


def mysql_score_update(username: str, time: int, mbid: str) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_score_update(%s, %s, %s)",
            (username, time, mbid),
        )
    mysql_connection.commit()


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


def lastfm_user_import(user: pylast.User) -> int | None:
    username = user.get_name()

    prev_scrobble_count = mysql_user_scrobble_count(username)
    curr_scrobble_count = user.get_playcount()

    last_scrobble = mysql_user_last_update(username)

    if prev_scrobble_count >= curr_scrobble_count:
        return 0

    scrobbles_remaining = curr_scrobble_count - prev_scrobble_count
    # scrobbles_remaining = min(50, scrobbles_remaining)

    params = user._get_params()
    params["limit"] = None
    params["from"] = last_scrobble + 1

    def validate_mbid(mbid: str) -> bool:
        if mbid and len(mbid) == 36:
            return mbid
        else:
            return None

    with rich.progress.Progress(transient=True) as progress:
        task = progress.add_task("Importing...", total=scrobbles_remaining)
        tracks_seen = 0

        def advance() -> bool:
            nonlocal tracks_seen

            progress.advance(task, advance=1)
            tracks_seen += 1

            if tracks_seen % 200 == 0:
                time.sleep(0.1)

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

            scrobbles_remaining -= 1

            timestamp = track_node.getElementsByTagName("date")[0].getAttribute("uts")
            timestamp = timestamp and int(timestamp)
            last_scrobble = max(last_scrobble, timestamp)

            artist = pylast._extract(track_node, "artist")
            artist_mbid = validate_mbid(
                track_node.getElementsByTagName("artist")[0].getAttribute("mbid")
            )

            if artist_mbid is None:
                advance()
                continue

            mysql_artist_add(artist_mbid, artist)
            mysql_score_update(username, timestamp, artist_mbid)

            album = pylast._extract(track_node, "album")
            album_mbid = validate_mbid(
                track_node.getElementsByTagName("album")[0].getAttribute("mbid")
            )

            if album_mbid is not None:
                mysql_album_add(album_mbid, album, artist_mbid)
                mysql_score_update(username, timestamp, album_mbid)

            track = pylast._extract(track_node, "name")
            track_mbid = validate_mbid(pylast._extract(track_node, "mbid"))

            if track_mbid is None:
                advance()
                continue

            # NOTE: ideally we would just use MBIDs here, but since
            # Last.FM's API is broken and using MBIDs doesn't work 99% of
            # the time here we are.
            duration_tries = 1
            while True:
                try:
                    duration = pylast._Request(
                        lastfm_network(),
                        "track.getInfo",
                        {"artist": artist, "track": track},
                    ).execute(True)
                    break  # success
                except Exception:
                    if duration_tries >= 3:
                        continue

                    duration_tries += 1
                    time.sleep(1)

            duration = pylast.cleanup_nodes(duration)
            duration = pylast._extract(duration, "duration")
            duration = duration and (int(duration) // 1000)

            if duration != 0:
                duration = timedelta(seconds=duration)
                mysql_track_add(track_mbid, track, artist_mbid, album_mbid, duration)
                mysql_score_update(username, timestamp, track_mbid)
                mysql_scrobble_add(username, timestamp, track_mbid)

            advance()

        if scrobbles_remaining > 0:
            progress.advance(task, advance=scrobbles_remaining)

    with mysql_connection.cursor() as cursor:
        cursor.execute(
            "UPDATE users\n"
            "SET user_last_update = GREATEST(user_last_update, %s)\n"
            "WHERE users.user_name = %s",
            (last_scrobble, username),
        )
    mysql_connection.commit()

    return tracks_seen


# SCHEMA TYPES
# ------------------------------------------------------------------------------
@dataclass
class MBEntry:
    name: str
    mbid: str
    # genres: Generator[str]


@dataclass
class Artist(MBEntry):
    def albums(self: Self) -> Generator[Album]:
        with mysql_connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT album,
                       album_name,
                FROM display_albums
                WHERE artist = %s
                """,
                (self.mbid,),
            )
            for row in cursor:
                yield Album(row["album_name"], row["album"], self)

    def tracks(self: Self) -> Generator[Track]:
        with mysql_connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT track,
                       album,
                       track_name,
                       album_name,
                       track_length
                FROM display_tracks
                WHERE artist = %s
                """,
                (self.mbid,),
            )
            for row in cursor:
                if album := row["album"]:
                    album = Album(row["album_name"], row["album"], self)
                yield Track(
                    row["track_name"], row["track"], album, self, row["track_length"]
                )


@dataclass
class Album(MBEntry):
    artist: Artist

    def tracks(self: Self) -> Generator[Track]:
        with mysql_connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT track,
                       track_name,
                       track_length
                FROM display_tracks
                WHERE album = %s
                """,
                (self.mbid,),
            )
            for row in cursor:
                yield Track(
                    row["track_name"],
                    row["track"],
                    self,
                    self.artist,
                    row["track_length"],
                )


@dataclass
class Track(MBEntry):
    album: Album | None
    artist: Artist
    length: timedelta


@dataclass
class Score:
    entry: MBEntry
    score: float


@dataclass
class Scrobble:
    track: Track
    time: datetime


@dataclass
class User:
    name: str
    admin: bool = False

    @classmethod
    def create(cls: any, retry_count: int = 5) -> Self | None:
        result = lastfm_user_auth(retry_count)
        if result is None:
            return None

        session_key, username = result

        if mysql_user_exists(username):
            mysql_user_update_session_key(username, session_key)
            log(f"User '{username}' already exists")
            return None

        print(f"Username: {username}")
        password = rich.prompt.Prompt.ask("Password", password=True)

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

    def scrobbles(self: Self) -> Generator[Scrobble]:
        with mysql_connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT track,
                       album,
                       artist,
                       track_name,
                       album_name,
                       artist_name,
                       scrobble_time,
                       track_length,
                       scrobble_id
                FROM display_tracks
                  JOIN scrobbles ON (mbid = track)
                WHERE user_name = %s
                """,
                (self.name,),
            )
            for row in cursor:
                artist = Artist(row["artist_name"], row["artist"])
                if album := row["album"]:
                    album = Album(row["album_name"], row["album"], self)
                track = Track(
                    row["track_name"], row["track"], album, artist, row["track_length"]
                )
                # yield Scrobble(track, time), rows['scrobble_id']
                yield Scrobble(track, datetime.fromtimestamp(row["scrobble_time"]))


class TableApp(App):
    BINDINGS = [Binding("ctrl+q", "quit", "Quit", show=True, priority=True)]

    CSS = """
    Screen {
        align: center middle;
    }

    DataTable {
        width: 100%;
        height: 40%;
    }

    """

    ENABLE_COMMAND_PALETTE = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        ROWS = [
            ("lane", "swimmer", "country", "time"),
            (4, "Joseph Schooling", "Singapore", 50.39),
            (2, "Michael Phelps", "United States", 51.14),
            (5, "Chad le Clos", "South Africa", 51.14),
            (6, "László Cseh", "Hungary", 51.14),
            (3, "Li Zhuhao", "China", 51.26),
            (8, "Mehdy Metella", "France", 51.58),
            (7, "Tom Shields", "United States", 51.73),
            (1, "Aleksandr Sadovnikov", "Russia", 51.84),
            (10, "Darren Burns", "Scotland", 51.84),
        ]

        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(*ROWS[0])
        table.add_rows(ROWS[1:])


class DashboardScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Dashboard Screen")
        yield Footer()


class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Settings Screen")
        yield Footer()


class HelpScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Placeholder("Help Screen")
        yield Footer()


class Main(App):
    TITLE = "Scrobble Browser"

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
        ("d", "switch_mode('dashboard')", "Dashboard"),
        ("s", "switch_mode('settings')", "Settings"),
        ("h", "switch_mode('help')", "Help"),
    ]

    MODES = {
        "dashboard": DashboardScreen,
        "settings": SettingsScreen,
        "help": HelpScreen,
    }

    def on_mount(self) -> None:
        self.switch_mode("dashboard")


# MAIN FUNCTIONS
# ------------------------------------------------------------------------------
def menu_sign_up(args: argparse.Namespace) -> bool:
    user = User.create()
    if user is None:
        log("Failed to create account.")
        return False

    log(f"Created user {user.name}")

    count = lastfm_user_import(user.lastfm())
    print(f"Processed {count} scrobbles.")

    return True


def menu_login() -> User | None:
    # username = rich.prompt.Prompt.ask("Username")
    # password = rich.prompt.Prompt.ask("Password", password=False)
    username = "emekoi"
    password = "password"

    user = User.login(username, password)

    if user is None:
        log("Invalid username or password.")
        return None

    log("Sign in successful.")

    count = lastfm_user_import(user.lastfm())
    print(f"Processed {count} scrobbles.")

    return user


def menu_info(args: argparse.Namespace) -> bool:
    user = menu_login()
    if user is None:
        return False

    # print(list(user.scrobbles()))

    Main().run()

    return True


def migration(args: argparse.Namespace) -> bool:
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    parser_sign_up = subparsers.add_parser("sign-up")
    parser_sign_up.set_defaults(func=menu_sign_up)

    parser_login = subparsers.add_parser("info")
    parser_login.set_defaults(func=menu_info)

    parser_login = subparsers.add_parser("migration")
    parser_login.set_defaults(func=migration)

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
    except mysql.connector.Error as err:
        log(f"{err}")

    mysql_connection.commit()
    mysql_connection.close()
