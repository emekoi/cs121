DROP VIEW IF EXISTS display_tracks;
DROP VIEW IF EXISTS display_albums;
DROP VIEW IF EXISTS display_artists;

CREATE VIEW display_artists AS
  SELECT mbid AS artist,
         mbid_name AS artist_name
  FROM artists NATURAL JOIN mbids;

CREATE VIEW display_albums AS
  SELECT mbid AS album,
         mbid_name AS album_name,
         display_artists.artist,
         display_artists.artist_name
  FROM albums
    NATURAL JOIN mbids
    INNER JOIN display_artists USING (artist);

CREATE VIEW display_tracks AS
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
