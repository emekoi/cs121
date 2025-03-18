from __future__ import annotations

from asyncio import sleep
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

import argparse
import webbrowser
import os
import sys
import time

import mysql.connector
import mysql.connector.errorcode as errorcode

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal, Container
from textual.screen import Screen
from textual.widgets import DataTable, Placeholder, Static
from textual.widgets import Header, Footer
from textual.widgets import Label, Button, Input

from rich.status import Status

import rich.console
import rich.progress
import rich.prompt
import rich.text

import pylast
import pyparsing as pp


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
    def create(cls: any, session_key: str, username: str) -> Self | None:
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
                ORDER BY scrobble_time DESC
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

                yield Scrobble(
                    track,
                    datetime.fromtimestamp(row["scrobble_time"]),
                )


# UI
# ------------------------------------------------------------------------------
class StartScreen(Screen):
    CSS = """
    StartScreen {
        align: center middle;
    }

    Button {
        width: 50%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("Sign Up", id="sign-up")
        yield Button("Login", id="login")

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login":
            self.dismiss(await self.app.push_screen_wait(LoginScreen()))
        else:
            self.dismiss(await self.app.push_screen(SignupScreen()))


class LoginScreen(Screen):
    CSS = """
    LoginScreen {
        align: center middle;
    }

    * {
        width: 50%;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="USERNAME", id="username")
        yield Input(placeholder="PASSWORD", id="password", password=True)
        yield Button("Login")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value
        if username != "" and password != "":
            if user := User.login(username, password):
                self.dismiss(user)
            else:
                self.notify("Invalid username or password.", severity="error")
        else:
            self.notify("Invalid username or password.", severity="error")


class SignupScreen(Screen):
    CSS = """
    SignupScreen {
        align: center middle;
    }

    #dialog {
        width: 50%;
        height: auto;
    }

    Button {
        width: 100%;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    @work(exclusive=True)
    async def authenticate(self) -> None:
        skg = pylast.SessionKeyGenerator(lastfm_network())
        url = skg.get_web_auth_url()
        webbrowser.open(url)

        while True:
            try:
                result = skg.get_web_auth_session_key_username(url)
                self.session_key, self.username = result

                if mysql_user_exists(self.username):
                    mysql_user_update_session_key(self.username, self.session_key)
                    self.notify(
                        f"User '{self.username}' already exists.", severity="error"
                    )
                    self.app.pop_screen()
                else:
                    self.query_one("#dialog").loading = False
            except pylast.WSError:
                await sleep(1)

    def compose(self) -> ComposeResult:
        yield Container(
            Input(placeholder="PASSWORD", id="password", password=True),
            Button("Sign Up"),
            id="dialog",
        )

    def on_mount(self) -> None:
        input = self.query_one("#dialog")
        input.loading = True
        self.authenticate()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        password = self.query_one("#password", Input).value
        if password != "":
            mysql_user_create(self.username, self.password, self.session_key)
            self.dismiss(User(self.username))
        else:
            self.notify("Invalid password.", severity="error")


class SearchScreen(Screen):
    CSS = """
    DataTable {
        width: 100%;
        text-overflow: ellipsis;  # Overflowing text is truncated with an ellipsis
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(cursor_type="row", zebra_stripes=True)
        yield Footer()

    @work
    async def load_scrobbles(self, table: DataTable) -> None:
        for s in self.app.user.scrobbles():
            table.add_row(s.time, rich.text.Text(s.track.name), s.track.artist.name)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Date", "Track", "Artist")
        self.load_scrobbles(table)


class ReportScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Report Screen")
        yield Footer()


class RecommendScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Recommendation Screen")
        yield Footer()


class Main(App):
    TITLE = "Scrobble Browser"

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("s", "switch_mode('search')", "Search"),
        ("r", "switch_mode('report')", "Report"),
        ("R", "switch_mode('recommend')", "Recommend"),
    ]

    MODES = {
        "search": SearchScreen,
        "report": ReportScreen,
        "recommend": RecommendScreen,
    }

    @work
    async def on_mount(self) -> None:
        self.user = await self.push_screen_wait(StartScreen())
        self.switch_mode("search")


# MAIN FUNCTIONS
# ------------------------------------------------------------------------------
def menu_sign_up(args: argparse.Namespace) -> None:
    user = User.create()
    if user is None:
        log("Failed to create account.")
        return None

    log(f"Created user {user.name}")

    count = lastfm_user_import(user.lastfm())
    print(f"Processed {count} scrobbles.")
    return None


def menu_info(args: argparse.Namespace) -> None:
    Main().run()
    return None


def migration(args: argparse.Namespace) -> None:
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    parser_sign_up = subparsers.add_parser("sign-up")
    parser_sign_up.set_defaults(func=menu_sign_up)

    parser_login = subparsers.add_parser("info")
    parser_login.set_defaults(func=menu_info)

    # parser_login = subparsers.add_parser("migration")
    # parser_login.set_defaults(func=migration)

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
