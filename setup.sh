#!/usr/bin/bash

if [ $# -eq 0 ]; then
    cat <<EOF
${0}
- init: set up a database called ${DATABASE_NAME}
- demo: load demo data into ${DATABASE_NAME}
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
    ;;
*) ;;
esac
