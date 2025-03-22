-- sql/setup-views.sql, line 6
-- pair up artists MBIDs with human readable names.
SELECT mbid AS artist,
       mbid_name AS artist_name
FROM artists NATURAL JOIN mbids;

-- sql/setup-views.sql, line 11
-- pair up album MBIDs with human readable names.
SELECT mbid AS album,
       mbid_name AS album_name,
       display_artists.artist,
       display_artists.artist_name
FROM albums
  NATURAL JOIN mbids
  INNER JOIN display_artists USING (artist);

-- sql/setup-views.sql, line 20
-- pair up track MBIDs with human readable names.
SELECT mbid AS track,
       mbid_name AS track_name,
       display_albums.album,
       display_albums.album_name,
       display_artists.artist,
       display_artists.artist_name,
       length AS track_length
FROM tracks
  NATURAL JOIN mbids
  INNER JOIN display_artists USING (artist)
  LEFT JOIN display_albums USING (album);

-- app.py, line 46
-- check if there is a user with a given username in the database.
SELECT sf_user_exists('dummy4');

-- app.py, line 52
-- return 0/1/NULL if a user is a client/admin/does not exist.
SELECT sf_user_authenticate('admin', 'admin');

-- app.py, line 63
-- retrieve the timestamp for the last time we imported scrobbles from Last.FM.
SELECT user_last_update FROM users WHERE user_name = 'emekoi';

-- app.py, line 71
-- retrieve the number of scrobbles for a given user in the database.
SELECT COUNT(*) FROM scrobbles WHERE user_name = 'emekoi';

-- app.py, line 239
-- for every one of a user's scrobbles, pair it up with it's human readble names
-- (track/album/artist), the scrobble time, the length of the song, and a unique
-- identifier, sorting the list from most to least recent.
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
WHERE user_name = 'emekoi'
ORDER BY scrobble_time DESC;

-- app.py, line 274
SELECT track,
       album,
       artist,
       track_name,
       album_name,
       artist_name,
       track_length,
       COUNT(*) AS scrobble_count
FROM display_tracks
  JOIN scrobbles ON (mbid = track)
WHERE user_name = 'emekoi'
GROUP BY mbid
ORDER BY scrobble_count DESC;

-- app.py, line 306
-- for every one of a user's scrobbled tracks, pair it up with it's human
-- readble names (track/album/artist), the most recent scrobble time, and the
-- length of the song sorting the list by its combined recency-frequency score
-- from lowest to highest (most popular to least popular for a given user).
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
WHERE user_name = 'emekoi'
ORDER BY last_crf ASC;

-- app.py, line 861
-- pair up every user with a string describing their role.
SELECT user_name,
       IF(user_admin, 'Admin', 'Client') AS user_status
FROM users;
