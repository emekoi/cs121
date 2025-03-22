from __future__ import annotations

from asyncio import sleep
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

import os
import sys

import mysql.connector
import mysql.connector.errorcode as errorcode

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.content import Content
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.widgets import DataTable, Static, ProgressBar
from textual.widgets import Header, Footer
from textual.widgets import Button, Input

import pylast
import pyparsing as pp


# GLOBAL VARIABLES
# ------------------------------------------------------------------------------
__lastfm_network: pylast.LastFMNetwork = None


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
            "CALL sp_user_create_client(%s, %s, %s)", (username, password, session_key)
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

    try:
        return pylast.LastFMNetwork(API_KEY, API_SECRET)
    except Exception:
        return None


def lastfm_network() -> pylast.LastFMNetwork:
    if __lastfm_network is None:
        raise pylast.PyLastError
    return __lastfm_network


# TYPES
# ------------------------------------------------------------------------------
@dataclass
class Filter:
    name: str
    regex: str

    # +x:arg1,arg2,arg3
    @classmethod
    def parse(cls, input_str: str) -> list[Self]:
        arg = pp.Word(pp.alphas) | pp.quoted_string.set_parse_action(pp.remove_quotes)
        name = pp.Regex(
            "\\+(track|album|artist):", as_group_list=True
        ).set_parse_action(lambda x: x[0][0])

        flag = pp.Group(name + arg).set_parse_action(
            lambda xs: [cls(x[0].lower(), x[1]) for x in xs]
        )

        try:
            return pp.ZeroOrMore(flag).parse_string(input_str, parse_all=True)
        except pp.ParseException:
            return None

    def to_sql(self) -> str:
        escaped = mysql_connection._cmysql.escape_string(self.regex)
        return f"{self.name}_name RLIKE '{escaped.decode()}'"


@dataclass
class MBEntry:
    name: str
    mbid: str


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
class Scrobble:
    track: Track
    time: datetime


@dataclass
class User:
    name: str
    admin: bool = False

    @classmethod
    def login(cls: any, username: str, password: str) -> Self | None:
        is_admin = mysql_user_authenticate(username, password)
        if is_admin is None:
            return None
        else:
            if is_admin:
                ADMIN_DATABASE_USER = os.getenv("ADMIN_DATABASE_USER")
                ADMIN_DATABASE_PASSWORD = os.getenv("ADMIN_DATABASE_PASSWORD")
                mysql_connection.cmd_change_user(
                    ADMIN_DATABASE_USER, ADMIN_DATABASE_PASSWORD, DATABSE_NAME
                )
            return cls(username, is_admin)

    def lastfm(self: Self) -> pylast.User:
        return lastfm_network().get_user(self.name)

    def scrobbles(self: Self, filters: list[Filter]) -> Generator[Scrobble]:
        with mysql_connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                f"""
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
                  {"\n".join(map(lambda x: "AND " + x.to_sql(), filters))}
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

    def find_tracks(self: Self, filters: list[Filter]) -> Generator[Scrobble]:
        with mysql_connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                f"""
                SELECT track,
                       album,
                       artist,
                       track_name,
                       album_name,
                       artist_name,
                       track_length,
                       last_access
                FROM display_tracks
                  JOIN scores ON (mbid = track)
                WHERE user_name = %s
                  {"\n".join(map(lambda x: "AND " + x.to_sql(), filters))}
                ORDER BY last_crf ASC
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
                    datetime.fromtimestamp(row["last_access"]),
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
            result = await self.app.push_screen_wait(LoginScreen())
        else:
            result = await self.app.push_screen_wait(SignupScreen())

        self.dismiss(result)


class LoginScreen(Screen):
    TITLE = "Login"

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
    TITLE = "Sign Up"

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
        try:
            skg = pylast.SessionKeyGenerator(lastfm_network())
            url = skg.get_web_auth_url()
            self.app.open_url(url)

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
                        self.query_one("#username").value = self.username
                        self.query_one("#dialog").loading = False
                except pylast.WSError:
                    await sleep(1)
        except Exception:
            self.notify("Unable to reach Last.FM.", severity="error")
            self.app.pop_screen()

    def compose(self) -> ComposeResult:
        yield Container(
            Input(id="username", disabled=True),
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
        if len(password) == 0:
            self.notify("Invalid password.", severity="error")
        elif len(password) > 16:
            self.notify("Password too long.", severity="error")
        else:
            mysql_user_create(self.username, password, self.session_key)
            self.notify(f"Created user '{self.username}'.")
            self.dismiss(User(self.username))


class ImportScreen(Screen):
    TITLE = "Import"

    CSS = """
    ImportScreen {
        align: center middle;
    }

    #dialog {
        width: auto;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Importing..."),
            ProgressBar(),
            id="dialog",
        )

    @work(exclusive=True)
    async def lastfm_import(self, scrobble_count: int) -> None:
        progress = self.query_one(ProgressBar)

        user = self.app.user.lastfm()
        username = user.get_name()

        prev_scrobble_count = mysql_user_scrobble_count(username)
        curr_scrobble_count = scrobble_count

        last_scrobble = mysql_user_last_update(username)

        if prev_scrobble_count >= curr_scrobble_count:
            self.dismiss()
            return None

        scrobbles_remaining = curr_scrobble_count - prev_scrobble_count

        params = user._get_params()
        params["limit"] = None
        params["from"] = last_scrobble + 1

        def validate_mbid(mbid: str) -> bool:
            if mbid and len(mbid) == 36:
                return mbid
            else:
                return None

        scrobbles_seen = 0

        async def advance() -> bool:
            nonlocal scrobbles_seen

            progress.advance(advance=1)
            scrobbles_seen += 1

            if scrobbles_seen % 200 == 0:
                await sleep(0.1)
            else:
                self.query_one(Static).update(
                    content=f"Importing {scrobbles_seen}/{scrobble_count} scrobbles."
                )
                # NOTE: yield control back to control loop to update display
                await sleep(0)

        try:
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
                if scrobbles_remaining < 0:
                    break

                timestamp = track_node.getElementsByTagName("date")[0].getAttribute(
                    "uts"
                )
                timestamp = timestamp and int(timestamp)
                last_scrobble = max(last_scrobble, timestamp)

                artist = pylast._extract(track_node, "artist")
                artist_mbid = validate_mbid(
                    track_node.getElementsByTagName("artist")[0].getAttribute("mbid")
                )

                if artist_mbid is None:
                    await advance()
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
                    await advance()
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
                        if duration_tries >= 5:
                            continue

                        duration_tries += 1
                        await sleep(1)

                duration = pylast.cleanup_nodes(duration)
                duration = pylast._extract(duration, "duration")
                duration = duration and (int(duration) // 1000)

                if duration != 0:
                    duration = timedelta(seconds=duration)
                    mysql_track_add(
                        track_mbid, track, artist_mbid, album_mbid, duration
                    )
                    mysql_score_update(username, timestamp, track_mbid)
                    mysql_scrobble_add(username, timestamp, track_mbid)

                await advance()

        except pylast.PyLastError:
            pass

        finally:
            if scrobbles_remaining > 0:
                progress.advance(advance=scrobbles_remaining)

            self.dismiss()

    @work
    async def on_mount(self) -> None:
        try:
            scrobble_count = self.app.user.lastfm().get_playcount()
            # scrobble_count = min(10, scrobble_count)
        except pylast.PyLastError:
            self.notify("Unable to reach Last.FM.", severity="error")
            self.dismiss()
            return None

        self.query_one(Static).update(
            content=f"Importing 0/{scrobble_count} scrobbles."
        )
        self.query_one(ProgressBar).update(total=scrobble_count)

        # NOTE: yield control back to control loop to update display
        await sleep(0)

        self.lastfm_import(scrobble_count)


class FilterScreen(ModalScreen):
    TITLE = "Filter"

    CSS = """
    FilterScreen {
        align: center middle;
    }

    Input {
        width: 50%;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="FILTER", id="filter")

    def on_input_submitted(self, e: Input.Submitted) -> None:
        if len(e.value) == 0:
            self.app.filters = []
            self.dismiss()
        elif filters := Filter.parse(e.value):
            self.app.filters = filters
            self.dismiss()
        else:
            self.notify("Invalid filter.")


# TODO: Remove
class InfoScreen(ModalScreen):
    CSS = """
    InfoScreen {
        align: center middle;
    }

    Input {
        width: 50%;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Input(placeholder="FILTER", id="filter")


class ClientScreen(Screen):
    pass


class ViewScreen(ClientScreen):
    TITLE = "Scrobbles"

    CSS = """
    #box {
        width: 100%;
        height: 100%;
    }

    DataTable {
        width: 100%;
        text-overflow: ellipsis;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(DataTable(cursor_type="row", zebra_stripes=True), id="box")
        yield Footer()

    @work
    async def load_scrobbles(self, table: DataTable) -> None:
        for s in self.app.user.scrobbles(self.app.filters):
            track = Content(s.track.name).truncate(48, ellipsis=True)
            artist = Content(s.track.artist.name).truncate(32, ellipsis=True)
            table.add_row(s.time, track, artist)
        self.query_one("#box").loading = False

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Date", "Track", "Artist")

        def on_filter_change() -> None:
            self.query_one("#box").loading = True
            table.clear()
            self.load_scrobbles(table)

        self.watch(self.app, "filters", on_filter_change)
        on_filter_change()


class ReportScreen(ClientScreen):
    TITLE = "Report"

    CSS = """
    #box {
        width: 100%;
        height: 100%;
    }

    DataTable {
        width: 100%;
        text-overflow: ellipsis;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="box"):
            yield DataTable(cursor_type="row", zebra_stripes=True)
        yield Footer()

    @work
    async def load_scrobbles(self, table: DataTable) -> None:
        for s in self.app.user.scrobbles(self.app.filters):
            track = Content(s.track.name).truncate(48, ellipsis=True)
            artist = Content(s.track.artist.name).truncate(32, ellipsis=True)
            table.add_row(s.time, track, artist)
        self.query_one("#box").loading = False

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Date", "Track", "Artist")

        def on_filter_change() -> None:
            self.query_one("#box").loading = True
            table.clear()
            self.load_scrobbles(table)

        self.watch(self.app, "filters", on_filter_change)
        on_filter_change()


class FindScreen(ClientScreen):
    TITLE = "Recommendations"

    CSS = """
    #box {
        width: 100%;
        height: 100%;
    }

    DataTable {
        width: 100%;
        text-overflow: ellipsis;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(DataTable(cursor_type="row", zebra_stripes=True), id="box")
        yield Footer()

    @work
    async def load_scrobbles(self, table: DataTable) -> None:
        for s in self.app.user.find_tracks(self.app.filters):
            track = Content(s.track.name).truncate(48, ellipsis=True)
            artist = Content(s.track.artist.name).truncate(32, ellipsis=True)
            table.add_row(s.time, track, artist)
        self.query_one("#box").loading = False

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Date", "Track", "Artist")

        def on_filter_change() -> None:
            self.query_one("#box").loading = True
            table.clear()
            self.load_scrobbles(table)

        self.watch(self.app, "filters", on_filter_change)
        on_filter_change()


class AdminScreen(Screen):
    TITLE = "Users"

    CSS = """
    #box {
        width: 100%;
        height: 100%;
    }

    DataTable {
        width: 100%;
        text-overflow: ellipsis;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="box"):
            yield DataTable(cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("User", "Admin")

        with mysql_connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                f"""
                SELECT user_name,
                       IF(user_admin, 'Admin', 'Client') AS user_status
                FROM users
                """
            )

            for row in cursor:
                table.add_row(row["user_name"], row["user_status"])


class Main(App):
    TITLE = "Scrobble Browser"

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
    ]

    CLIENT_BINDINGS = [
        ("f", "app.push_screen('filter')", "Filter"),
        ("ctrl+v", "switch_mode('view')", "View"),
        ("ctrl+r", "switch_mode('report')", "Report"),
        ("ctrl+f", "switch_mode('find')", "Find"),
    ]

    ADMIN_BINDINGS = []

    SCREENS = {"filter": FilterScreen}

    MODES = {
        "view": ViewScreen,
        "report": ReportScreen,
        "find": FindScreen,
    }

    filters = reactive([])

    @work
    async def on_mount(self) -> None:
        self.user = await self.push_screen_wait(StartScreen())
        if self.user.admin:
            for k, a, d in self.CLIENT_BINDINGS:
                self.bind(k, a, description=d)
            self.push_screen(AdminScreen())
        else:
            await self.push_screen_wait(ImportScreen())
            for k, a, d in self.CLIENT_BINDINGS:
                self.bind(k, a, description=d)
            self.switch_mode("view")


# ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    DATABSE_NAME = os.getenv("DATABASE_NAME")
    CLIENT_DATABASE_USER = os.getenv("CLIENT_DATABASE_USER")
    CLIENT_DATABASE_PASSWORD = os.getenv("CLIENT_DATABASE_PASSWORD")

    try:
        mysql_connection = mysql.connector.connect(
            host="localhost",
            user=CLIENT_DATABASE_USER,
            port="3306",
            password=CLIENT_DATABASE_PASSWORD,
            database=DATABSE_NAME,
        )
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print(
                "Incorrect username or password when connecting to DB", file=sys.stderr
            )
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist", file=sys.stderr)
        else:
            print(f"Failed to connect to DB: {err}", file=sys.stderr)

        sys.exit(1)

    __lastfm_network = lastfm_init()

    try:
        Main().run()
    except Exception:
        print(
            "Something unexpected happened. Please contact support",
            file=sys.stderr,
        )

    mysql_connection.commit()
    mysql_connection.close()
