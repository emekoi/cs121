-- DDL NOTES
-- 1. All MBIDs are 36 character long UUIDS. These are taken from MusicBrainz
-- and assumed to be globally unique. They are stable and guaranteed not to
-- change so we do not needs any cascading updates.

DROP TABLE IF EXISTS scrobbles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tracks;
DROP TABLE IF EXISTS albums;
DROP TABLE IF EXISTS artists;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS mbids;

-- A table of all known MBIDs alsongside their name and frecency.
CREATE TABLE mbids
    -- INFO: 36 character UUID given by MusicBrainz.
  ( mbid CHAR(36)
    -- INFO: UTF-8 encoded name as reported by MusicBrainz.
  , name VARCHAR(256) NOT NULL
    -- INFO: A combined measure of frequency and recency used to find MBIDs that
    -- have not been scrobbled recently while supressing MBIDS that have a high
    -- total number of scrobbles. This is shared across all users.
  , frecency INT
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
  ( artist_mbid CHAR(36)
  , PRIMARY KEY (artist_mbid)
  , FOREIGN KEY (artist_mbid)
      REFERENCES mbids(mbid)
      ON DELETE CASCADE
  )
;

-- A linking table between artist MBIDs and album MBIDs.
CREATE TABLE albums
    -- INFO: The MBID assigned to this album by MusicBrainz.
  ( album_mbid CHAR(36)
    -- INFO: The MBID assigned to this album's artist by MusicBrainz.
  , artist_mbid CHAR(36)
  , PRIMARY KEY (album_mbid, artist_mbid)
  , FOREIGN KEY (album_mbid)
      REFERENCES mbids(mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (artist_mbid)
      REFERENCES artists(artist_mbid)
      ON DELETE CASCADE
  )
;

-- A linking table between track MBIDs and artist MBIDs. Track length and album
-- are also recorded when they exist.
CREATE TABLE tracks
    -- INFO: The MBID assigned to this track by MusicBrainz.
  ( track_mbid   CHAR(36)
    -- INFO: The MBID assigned to this track's album by MusicBrainz.
    -- NOTE: May be NULL for songs not released on an album/EP.
  , album_mbid   CHAR(36)
    -- INFO: The MBID assigned to this track's artist by MusicBrainz.
  , artist_mbid  CHAR(36)
  , track_length TIME     NOT NULL
  , PRIMARY KEY (track_mbid, artist_mbid)
  , FOREIGN KEY (track_mbid)
      REFERENCES mbids(mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (album_mbid)
      REFERENCES albums(album_mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (artist_mbid)
      REFERENCES artists(artist_mbid)
      ON DELETE CASCADE
  )
;

-- A table of all known users
CREATE TABLE users
    -- INFO: An unique identifier of users.
  ( user_id   INT         NOT NULL AUTO_INCREMENT
    -- INFO: An user-facing account name.
  , user_name VARCHAR(16) NOT NULL
  , PRIMARY KEY (user_id)
  )
;

-- A table of recorded listening events
CREATE TABLE scrobbles
    -- INFO: An unique identifier for this listening event.
    -- NOTE: This is necessary since Last.FM only reports minute in precision
    -- and some songs are shorted than 1 minute.
  ( scrobble_id   INT      NOT NULL AUTO_INCREMENT
    -- INFO: The time at which this listening event occured.
  , scrobble_time DATETIME NOT NULL
    -- INFO: The track that was listened to.
  , track_mbid    CHAR(36) NOT NULL
    -- INFO: The user that listened to this track.
  , user_id       INT      NOT NULL
  , PRIMARY KEY (scrobble_id)
  , FOREIGN KEY (track_mbid)
      REFERENCES tracks(track_mbid)
      ON DELETE CASCADE
  , FOREIGN KEY (user_id)
      REFERENCES users(user_id)
      ON DELETE CASCADE
  )
;
