-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_mbid_add
  ( mbid      CHAR(36)
  , mbid_name VARCHAR(256)
  , mbid_type ENUM('artist', 'album', 'track')
  )
BEGIN
  INSERT INTO mbids VALUES (mbid, mbid_name, mbid_type)
  ON DUPLICATE KEY UPDATE mbid = mbid;
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_artist_add
  ( artist_mbid CHAR(36)
  , artist_name VARCHAR(256)
  )
BEGIN
  CALL sp_mbid_add(artist_mbid, artist_name, 'artist');
  INSERT INTO artists VALUES (artist_mbid)
  ON DUPLICATE KEY UPDATE mbid = mbid;
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_album_add
  ( album_mbid   CHAR(36)
  , album_name   VARCHAR(256)
  , album_artist CHAR(36)
  )
BEGIN
  CALL sp_mbid_add(album_mbid, album_name, 'album');
  INSERT INTO albums VALUES (album_mbid, album_artist)
  ON DUPLICATE KEY UPDATE mbid = mbid;
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_track_add
  ( track_mbid   CHAR(36)
  , track_name   VARCHAR(256)
  , track_artist CHAR(36)
  , track_album  CHAR(36)
  , track_length TIME
  )
BEGIN
  CALL sp_mbid_add(track_mbid, track_name, 'track');
  INSERT INTO tracks VALUES (track_mbid, track_artist, track_album, track_length)
  ON DUPLICATE KEY UPDATE mbid = mbid;
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_user_add_scrobble
  ( user_name     VARCHAR(16)
  , scrobble_time INT
  , track_mbid    CHAR(36)
  )
BEGIN
  -- TODO: update scores
  INSERT INTO scrobbles
  VALUES
    ( DEFAULT
    , scrobble_time
    , track_mbid
    , user_name
    );
END !
DELIMITER ;
