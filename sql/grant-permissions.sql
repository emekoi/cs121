DROP USER IF EXISTS 'admin'@'localhost', 'client'@'localhost';

CREATE USER 'admin'@'localhost' IDENTIFIED BY 'admin';
CREATE USER 'client'@'localhost' IDENTIFIED BY 'client';

GRANT ALL PRIVILEGES ON * TO 'admin'@'localhost';
GRANT SELECT ON * TO 'client'@'localhost';
GRANT EXECUTE ON * TO 'client'@'localhost';
FLUSH PRIVILEGES;
