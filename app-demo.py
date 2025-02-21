"""
Code demo from Final Project Lecture 22wi, providing
an example of using MySQL with Python for an animal adoption
agency database (inspired by 21wi midterm).
"""
import sys  # to print error messages to sys.stderr
import mysql.connector
# To get error codes from the connector, useful for user-friendly
# error-handling
import mysql.connector.errorcode as errorcode

# Debugging flag to print errors when debugging that shouldn't be visible
# to an actual client. Set to False when done testing.
DEBUG = True


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
          # Find port in MAMP or MySQL Workbench GUI or with
          # SHOW VARIABLES WHERE variable_name LIKE 'port';
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
        # specific to your database.
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR and DEBUG:
            sys.stderr('Incorrect username or password when connecting to DB.')
        elif err.errno == errorcode.ER_BAD_DB_ERROR and DEBUG:
            sys.stderr('Database does not exist.')
        elif DEBUG:
            sys.stderr(err)
        else:
            sys.stderr('An error occurred, please contact the administrator.')
        sys.exit(1)


# ----------------------------------------------------------------------
# Functions for Command-Line Options/Query Execution
# ----------------------------------------------------------------------
def show_animals():
    """
    Prompts the user to choose a breed to filter a search for all animals
    in the database, then shows a list of animals with the date of their
    assignment at a shelter, their name, and their animal type.
    Results are sorted by date in descending order.
    
    Note that more functionality can be easily added to give other
    filters/sorting options to clients.
    """
    ans = input('Do you want to search by breed? ')
    breed = None
    if ans and ans.lower()[0] == 'y':
       breed = input('What breed to you want to look for? ')
    if breed:
        sql = """
SELECT name, animal_type, join_date 
FROM animals 
WHERE animal_type LIKE '%s' 
ORDER BY join_date DESC;
""" % (breed, ) # escape parameters for secure execution
    else:
        sql = 'SELECT name, animal_type, join_date FROM animals ORDER BY join_date DESC;'
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
    except mysql.connector.Error as err:
        if DEBUG:
            sys.stderr(err)
            sys.exit(1)
        else:
            sys.stderr('An error occurred when searching for available animals.')
            return
    if not rows:
        print('No results found.')
    else:
        if breed:
            print(f'\'{breed}\' animals in the database (newest first):')
        else: 
            print(f'Animals in database (newest first):')
        for row in rows:
            (name, breed, app_time) = row
            print('  ', app_time, f'"{name}"', f'({breed})')


def show_applications(status=None):
    print('Application listing unimplemented.')


def update_application():
    # TODO: Call accept_application procedure defined in MySQL
    print('Application updating (via procedure call) unimplemented.')


# ----------------------------------------------------------------------
# Functions for Logging Users In
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Command-Line Functionality
# ----------------------------------------------------------------------
def show_options():
    """
    Displays options users can choose in the application, such as
    viewing <x>, filtering results with a flag (e.g. -s to sort),
    sending a request to do <x>, etc.
    """
    print('What would you like to do? ')
    print('  (l) - login')
    print('  (a) - show available animals')
    print('  (q) - quit')
    print()
    while True:
        ans = input('Enter an option: ')[0].lower()
        if ans == 'q':
            quit_ui()
        elif ans == 'a':
            show_animals()
        elif ans == 'l':
            print('Login functionality unimplemented.')
        else:
            print('Unknown option.')


# You may choose to support admin vs. client features in the same program, or
# separate the two as different client and admin Python programs using the same
# database.
def show_admin_options():
    """
    Displays options specific for admins, such as adding new data <x>,
    modifying <x> based on a given id, removing <x>, etc.
    """
    print('What would you like to do? ')
    print('  (a) - ')
    print('  (p) - show pending applications')
    print('  (u) - update application status')
    print('  (q) - quit')
    print()
    while True:
        ans = input('Enter an option: ')[0].lower()
        if ans == 'q':
            quit_ui()
        elif ans == 'p':
            show_applications('pending')
            pass
        elif ans == 'u':
            update_application()
        else:
            print('Unknown option.')


def quit_ui():
    """
    Quits the program, printing a good bye message to the user.
    """
    print('Good bye!')
    exit()


def main():
    """
    Main function for starting things up.
    """
    show_options()


if __name__ == '__main__':
    # This conn is a global object that other functinos can access.
    # You'll need to use cursor = conn.cursor() each time you are
    # about to execute a query with cursor.execute(<sqlquery>)
    conn = get_conn()
    main()
