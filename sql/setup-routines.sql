DROP FUNCTION IF EXISTS sf_score_F;
DROP FUNCTION IF EXISTS sf_score_C;

DROP PROCEDURE IF EXISTS sp_mbid_add;
DROP PROCEDURE IF EXISTS sp_artist_add;
DROP PROCEDURE IF EXISTS sp_album_add;
DROP PROCEDURE IF EXISTS sp_track_add;
DROP PROCEDURE IF EXISTS sp_user_add_scrobble;
DROP PROCEDURE IF EXISTS sp_score_update;

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

DELIMITER !
CREATE FUNCTION sf_score_F(delta INT)
RETURNS DOUBLE
BEGIN
  -- HALF_LIFE = 1 / (60 * 60 * 24 * 30)
  RETURN POW(0.5, delta / (60 * 60 * 24 * 30));
END !
DELIMITER ;

DELIMITER !
CREATE FUNCTION sf_score_C
  ( t_delta DOUBLE
  , c_prev  DOUBLE
  )
RETURNS DOUBLE
BEGIN
  RETURN sf_score_F(0) + sf_score_F(t_delta) * c_prev;
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_score_update
  ( user_name   VARCHAR(16)
  , curr_access INT
  , mbid        CHAR(36)
  )
BEGIN
  INSERT INTO scores VALUES (user_name, mbid, curr_access, sf_score_F(0))
  ON DUPLICATE KEY UPDATE
    last_crf = sf_score_C(curr_access - last_access, last_crf),
    last_access = curr_access;
END !
DELIMITER ;
