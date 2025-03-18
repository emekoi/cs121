-- DDL NOTES
-- 1. All MBIDs are 36 character long UUIDS. These are taken from MusicBrainz
-- and assumed to be globally unique. They are stable and guaranteed not to
-- change so we do not needs any cascading updates.

DROP TABLE IF EXISTS scrobbles;
DROP TABLE IF EXISTS scores;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tracks;
DROP TABLE IF EXISTS albums;
DROP TABLE IF EXISTS artists;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS mbids;

-- A table of all known MBIDs alsongside their name and frecency.
CREATE TABLE mbids
    -- INFO: 36 character UUID given by MusicBrainz.
  ( mbid      CHAR(36)
    -- INFO: UTF-8 encoded name as reported by MusicBrainz.
  , mbid_name VARCHAR(256) NOT NULL
    -- INFO: The type of the MBID entity.
  , mbid_type ENUM('artist', 'album', 'track') NOT NULL
  , PRIMARY KEY (mbid)
  )
;

-- A table ascribing genres to MBIDs.
CREATE TABLE genres
    -- INFO: 36 character UUID given by MusicBrainz.
  ( mbid       CHAR(36)
    -- INFO: A genre as defined by MusicBrainz.
  , genre_name VARCHAR(32) NOT NULL
  , PRIMARY KEY (mbid, genre_name)
  , FOREIGN KEY (mbid)
      REFERENCES mbids(mbid)
      ON DELETE CASCADE
  )
;

-- A restriction of mbids to just artists.
CREATE TABLE artists
    -- INFO: The MBID assigned to this artist by MusicBrainz.
  ( mbid CHAR(36)
  , PRIMARY KEY (mbid)
  , FOREIGN KEY (mbid)
      REFERENCES mbids(mbid)
      ON DELETE CASCADE
  )
;

-- A linking table between artist MBIDs and album MBIDs.
CREATE TABLE albums
    -- INFO: The MBID assigned to this album by MusicBrainz.
  ( mbid   CHAR(36)
    -- INFO: The MBID assigned to this album's artist by MusicBrainz.
  , artist CHAR(36)
  , PRIMARY KEY (mbid, artist)
  , FOREIGN KEY (mbid)
      REFERENCES mbids(mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (artist)
      REFERENCES artists(mbid)
      ON DELETE CASCADE
  )
;

-- A linking table between track MBIDs and artist MBIDs. Track length and album
-- are also recorded when they exist.
CREATE TABLE tracks
    -- INFO: The MBID assigned to this track by MusicBrainz.
  ( mbid    CHAR(36)
    -- INFO: The MBID assigned to this track's artist by MusicBrainz.
  , artist  CHAR(36)
    -- INFO: The MBID assigned to this track's album by MusicBrainz.
    -- NOTE: May be NULL for songs not released on an album/EP.
  , album   CHAR(36)
  , length  TIME     NOT NULL
  , PRIMARY KEY (mbid, artist)
  , FOREIGN KEY (mbid)
      REFERENCES mbids(mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (album)
      REFERENCES albums(mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (artist)
      REFERENCES artists(mbid)
      ON DELETE CASCADE
  )
;

-- A table of all known users
CREATE TABLE users
    -- INFO: An unique identifier of users.
  ( user_name        VARCHAR(64) NOT NULL
    -- INFO: The salt used to hash a user's password.
  , user_salt        CHAR(8)     NOT NULL
    -- INFO: The salted hash of the user's password.
  , user_hash        BINARY(64)  NOT NULL
    -- INFO: A flag determining whether a user is an admin.
  , user_admin       TINYINT     NOT NULL
    -- INFO: A user's Last.FM session key if it exists.
  , user_session     BINARY(32)
    -- INFO: A UNIX timestamp representing the time a user's scrobbles were
    -- updated.
  , user_last_update INT
  , PRIMARY KEY (user_name)
  )
;

-- A table tracking per-user reccomendation scores for MBIDs.
CREATE TABLE scores
    -- INFO: The user that scrobbled this track.
  ( user_name   VARCHAR(16) NOT NULL
    -- INFO: The MDID entity that was scrobbled.
  , mbid        CHAR(36)    NOT NULL
    -- INFO: The UNIX timestamp of the last time this entry was scrobbled.
  , last_access INT         NOT NULL
    -- INFO: A combined measure of frequency and recency used to find MBIDs that
    -- have not been scrobbled recently while supressing MBIDS that have a high
    -- total number of scrobbles.
  , last_crf    DOUBLE      NOT NULL
  , PRIMARY KEY (user_name, mbid)
  , FOREIGN KEY (mbid)
      REFERENCES mbids(mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (user_name)
      REFERENCES users(user_name)
      ON DELETE CASCADE
  )
;

-- Does using unique on username add an index.
-- A table of recorded listening events
CREATE TABLE scrobbles
    -- INFO: An unique identifier for this listening event.
    -- NOTE: This is necessary since Last.FM only reports minute in precision
    -- and some songs are shorted than 1 minute.
  ( scrobble_id   INT         NOT NULL AUTO_INCREMENT
    -- INFO: The time at which this listening event occured.
    -- NOTE: This is stored as a UNIX timestamp and clients are expected to use
    -- FROM_UNIXTIME in order to display the timestamp to users.
  , scrobble_time INT         NOT NULL
    -- INFO: The track that was listened to.
  , mbid          CHAR(36)    NOT NULL
    -- INFO: The user that listened to this track.
  , user_name     VARCHAR(16) NOT NULL
  , PRIMARY KEY (scrobble_id)
  , FOREIGN KEY (mbid)
      REFERENCES tracks(mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (user_name)
      REFERENCES users(user_name)
      ON DELETE CASCADE
  )
;
