DROP TABLE IF EXISTS scores;

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
