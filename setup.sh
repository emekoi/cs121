#!/usr/bin/bash

if [ $# -eq 0 ]; then
    cat <<EOF
${0}
- init    : set up a database called ${DATABASE_NAME}
- backup  : backup ${DATABASE_NAME}
- restore : restore ${DATABASE_NAME}
EOF
    exit 1
fi

case "$1" in
init)
    mysql -u root <<EOF
DROP DATABASE IF EXISTS ${DATABASE_NAME};
CREATE DATABASE ${DATABASE_NAME};
USE ${DATABASE_NAME};
SOURCE sql/setup.sql;
SOURCE sql/setup-routines.sql;
SOURCE sql/setup-passwords.sql;
EOF
    python app.py sign-up
    ;;
backup)
    mkdir -p backup
    suffix="$(date '+%Y%m%d-%H%M%S' | tr -d '\n')"
    mysqldump -u root --databases "${DATABASE_NAME}" >"backup/backup-${suffix}.sql"
    ;;
restore)
    mysql -u root <"$2"
    ;;
*)
    mysql -u root <"sql/${1}"
    ;;
esac
