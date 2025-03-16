-- This function generates a specified number of characters for using
-- as a salt in passwords.
DELIMITER !
CREATE FUNCTION sf_salt_create(num_chars INT)
RETURNS VARCHAR(20) NOT DETERMINISTIC
BEGIN
  DECLARE salt VARCHAR(20) DEFAULT '';

  -- Don't want to generate more than 20 characters of salt.
  SET num_chars = LEAST(20, num_chars);

  -- Generate the salt!  Characters used are ASCII code 32 (space)
  -- through 126 ('z').
  WHILE num_chars > 0 DO
    SET salt = CONCAT(salt, CHAR(32 + FLOOR(RAND() * 95)));
    SET num_chars = num_chars - 1;
  END WHILE;

  RETURN salt;
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE FUNCTION sf_password_hash(salt CHAR(8), password VARCHAR(20))
RETURNS BINARY(64) NOT DETERMINISTIC
BEGIN
  RETURN SHA2(CONCAT(salt, password), 256);
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_user_create
  ( username VARCHAR(16)
  , password VARCHAR(20)
  , session_key BINARY(32)
  )
BEGIN
  DECLARE salt CHAR(8) DEFAULT sf_salt_create(8);
  INSERT INTO users
  VALUES
    ( username
    , salt
    , sf_password_hash(salt, password)
    , FALSE
    , session_key
    , 0
    );
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE FUNCTION sf_user_exists(username VARCHAR(16))
RETURNS TINYINT DETERMINISTIC
BEGIN
  RETURN (SELECT COUNT(*) FROM users WHERE users.user_name = username);
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE FUNCTION sf_user_authenticate(username VARCHAR(16), password VARCHAR(20))
RETURNS TINYINT DETERMINISTIC
BEGIN
  RETURN (SELECT users.user_admin
  FROM users
  WHERE users.user_name = username
    AND users.user_hash = sf_password_hash(user_salt, password));
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_user_change_password
  ( username VARCHAR(16)
  , password VARCHAR(20)
  )
BEGIN
  DECLARE salt CHAR(8) DEFAULT sf_salt_create(8);
  UPDATE users
    SET user_salt = salt,
        user_hash = sf_password_hash(salt, password)
  WHERE users.user_name = username;
END !
DELIMITER ;

-- TODO: documentation
DELIMITER !
CREATE PROCEDURE sp_user_update_session_key
  ( username VARCHAR(16)
  , session_key BINARY(32)
  )
BEGIN
  UPDATE users
     SET user_session = session_key
  WHERE users.user_name = username;
END !
DELIMITER ;
