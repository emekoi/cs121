# Data Source

my data comes from Last.FM which sources its data from users and MusicBrainz.
all the "scrobbles" (times songs were listened to) included in the data are my
own. please don't flame my music taste.

# Setup and Running

This project requires Python 3.3+. You can run `bash cs121.sh` or manually use
the following commands.

``` shell
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

DATABASE_NAME=emekafinalprojectdb bash run.sh setup
DATABASE_NAME=emekafinalprojectdb python app.py
```

# Notes
- RUN IN FULLSCREEN! textual starts having weird issues if the screen is too
  small.
  
- this may or may not work in Windows. i haven't checked.

- you can press <kbd>f</kbd> to filter by track/artist/album name. the syntax is
  `+(track|artist|album):(<regex>|'<regex>'|"<regex>")`. the quotes can be left
  off if the regex pattern only consists of alphanumeric characters with no
  spaces. some good queries to try are "+album:world" or "+artist:kenny".

- there are 5 accounts:
  | Username | Password  | Type   |
  |----------|-----------|--------|
  | admin    | admin     | admin  |
  | emekoi   | password  | client |
  | dummy1   | dummy1    | client |
  | dummy2   | dummy2    | client |
  | dummy3   | dummy3    | client |

- account creation is disabled since i'm not uploading my API keys to github.
  for the same reason the `session_key` field in the `users` table is `NULL` as
  well. if you want to enable account creation, export the environment variables
  `API_SECRET` and `API_KEY` which contain your API secret and key respectively.
  these can be obtained [here](https://www.last.fm/api/account/create). or you
  can check the file `secrets.txt` i've included in my submission. pretty please
  don't share those.

- if something looks frozen, please wait. the UI framework i am using is async
  but the SQL interface i'm using is synchronous so it causes the UI to block
  sometimes. in the future i plan to switching to the async mysql connector.

- the import is a MySQL dump since i couldn't get MySQL to import data correctly
  otherwise. i ran into issues with string encodings and foreign-key constraints
  which where impossible to debug when i have roughly 25k rows.
