-- SELECT user_name, scrobble_time, mbid, artist, album
-- FROM scrobbles NATURAL JOIN tracks;

-- SELECT user_name, scrobble_time, mbid, artist, album
-- FROM scrobbles NATURAL JOIN tracks;

-- SELECT user_name, scrobble_time, mbid, artist, album
-- FROM scrobbles NATURAL JOIN tracks;

-- START TRANSACTION;

-- SELECT CALL sp_score_update(user_name, scrobble_time, mbid)
-- FROM scrobbles;

-- SELECT artist, sf_score_F(scrobble_time)
-- FROM scrobbles NATURAL JOIN tracks;

-- SELECT album, sf_score_F(scrobble_time)
-- FROM scrobbles NATURAL JOIN tracks WHERE album IS NOT NULL;

-- ROLLBACK;

-- SELECT * FROM scrobbles;
-- SELECT * FROM scrobbles;

-- SELECT mbid_name AS track_name, artist_name
-- FROM tracks NATURAL JOIN mbids NATURAL JOIN ();

SELECT mbid_name AS track_name, artist_name
FROM tracks
  NATURAL JOIN mbids
  NATURAL JOIN
    ( SELECT mbid AS artist, mbid_name AS artist_name
      FROM (artists NATURAL JOIN mbids)) AS ARTIST;
