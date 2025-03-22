#!/usr/bin/bash

if [ $# -eq 0 ]; then
    cat <<EOF
${0}
- setup   : set up a database called ${DATABASE_NAME}
- backup  : backup ${DATABASE_NAME}
EOF
    exit 1
fi

case "$1" in
setup)
    mysql -u root <<EOF
DROP DATABASE IF EXISTS ${DATABASE_NAME};
CREATE DATABASE ${DATABASE_NAME} DEFAULT CHARSET = utf8mb4 DEFAULT COLLATE = utf8mb4_unicode_ci;
USE ${DATABASE_NAME};
SOURCE sql/setup.sql;
SOURCE sql/setup.sql;
SOURCE sql/setup-views.sql;
SOURCE sql/setup-routines.sql;
SOURCE sql/setup-passwords.sql;

CALL sp_user_create_admin('admin', 'admin');
CALL sp_user_create_client('dummy1', 'dummy1', NULL);
CALL sp_user_create_client('dummy2', 'dummy2', NULL);
CALL sp_user_create_client('dummy3', 'dummy3', NULL);

SOURCE sql/load-data.sql;
SOURCE sql/grant-permissions.sql;
SHOW WARNINGS;
EOF
    ;;

backup)
    mkdir -p backup
    suffix="$(date '+%Y%m%d-%H%M%S' | tr -d '\n')"
    mysqldump -u root --databases "${DATABASE_NAME}" >"backup/backup-${suffix}.sql"
    cp "backup/backup-${suffix}.sql" "sql/load-data.sql"
    ;;
*) ;;
esac
