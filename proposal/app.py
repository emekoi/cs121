"""
Student name(s): Emeka Nkurumeh
Student email(s): e.nk@caltech.edu

Allow users to query Last.FM history and generate "niche" music recommendations
based on global listening history.
"""

import sys  # to print error messages to sys.stderr
import mysql.connector
import mysql.connector.errorcode as errorcode

# Debugging flag to print errors when debugging that shouldn't be visible
# to an actual client. ***Set to False when done testing.***
DEBUG = True

ERROR = {}

# ----------------------------------------------------------------------
# SQL Utility Functions
# ----------------------------------------------------------------------
def get_conn():
    """"
    Returns a connected MySQL connector instance, if connection is successful.
    If unsuccessful, exits.
    """
    try:
        conn = mysql.connector.connect(
          host='localhost',
          user='appadmin',
          port='3306',
          password='adminpw',
          database='shelterdb'
        )
        print('Successfully connected.')
        return conn
    except mysql.connector.Error as err:
        # Remember that this is specific to _database_ users, not
        # application users. So is probably irrelevant to a client in your
        # simulated program. Their user information would be in a users table
        # specific to your database; hence the DEBUG use.
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR and DEBUG:
            sys.stderr('Incorrect username or password when connecting to DB.')
        elif err.errno == errorcode.ER_BAD_DB_ERROR and DEBUG:
            sys.stderr('Database does not exist.')
        elif DEBUG:
            sys.stderr(err)
        else:
            # A fine catchall client-facing message.
            sys.stderr('An error occurred, please contact the administrator.')
        sys.exit(1)

def sql_debug(code, fatal):
    """
    Decorator for performing error-handling on SQL queries. Handles constructing
    cursor and printing of errors based on DEBUG mode.
    """
    def decorate(f):
        def wrapper(*args, **kwargs):
            try:
                cursor = conn.cursor()
                return f(cursor, *args, **kwargs)
            except mysql.connector.Error as err:
                if DEBUG:
                    sys.stderr(err)
                    sys.exit(1)
                else:
                    if code is not None: sys.stderr(ERROR[code])
                    if fatal: sys.exit(1)
        return wrapper
    return decorate

# ----------------------------------------------------------------------
# Functions for Command-Line Options/Query Execution
# ----------------------------------------------------------------------
def login(user_name, totp):
    """
    Given a user name and TOTP, log into an account.

    user_name: The user account name.
    totp: The time passed pairing code.
    """
    raise NotImplementedError

def generate_filter(sql_query, user_filter):
    """
    Given a user-supplied predicate and SQL query, generate a new SQL query
    that filters the result of the previous query according to the predicate.

    sql_query: The original SQL query.
    user_filter: A user-supplied predicate in the TBD syntax.
    """
    raise NotImplementedError

def search(cursor, user_filter):
    """
    Given a user-supplied predicate, return all rows that match the predicate.

    user_filter: A user-supplied predicate in the TBD syntax.
    """
    raise NotImplementedError

def recommend(cursor, user_filter, count):
    """
    Given a user-supplied predicate, return at most `count` rows that match the
    predicate from among the least frecent MDIDS.

    user_filter: A user-supplied predicate in the TBD syntax.
    count: The max number of rows to return.
    """
    raise NotImplementedError

def report(cursor, user_filter, time_range):
    """
    Given a user-supplied predicate, generate listening statistics for MBIDs
    that match the predicate within the given time range.

    user_filter: A user-supplied predicate in the TBD syntax.
    time_range: The time range to generate a report for. If None a report is
    generate for all scrobbles.
    """
    raise NotImplementedError

# ----------------------------------------------------------------------
# Command-Line Functionality
# ----------------------------------------------------------------------
def show_options():
    """
    Displays options users can choose in the application, such as
    generating reports or recommendations, or searching through
    their scrobbled music.
    """
    print('What would you like to do? ')
    print('  (s) - search for an artist/album/track')
    print('  (l) - recommend an album/artist/track you haven\'t listened to in a while')
    print('  (r) - generate a listening report')
    print('  (q) - quit')
    print()
    ans = input('Enter an option: ').lower()
    if ans == 'q':
        quit_ui()
    elif ans == '':
        pass

def quit_ui():
    """
    Quits the program, printing a good bye message to the user.
    """
    print('Good bye!')
    exit()

def auth():
    """
    Log users into the application.
    """
    login(None, None)

def main():
    """
    Main function for starting things up.
    """
    auth()
    show_options()

if __name__ == '__main__':
    # This conn is a global object that other functions can access.
    # You'll need to use cursor = conn.cursor() each time you are
    # about to execute a query with cursor.execute(<sqlquery>)
    conn = get_conn()
    main()
