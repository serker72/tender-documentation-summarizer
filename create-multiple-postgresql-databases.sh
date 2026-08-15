#!/bin/bash
###############################################################################
# PostgreSQL Docker multiple databases creation script:
#  postgres:
#    image: postgres:15
#    environment:
#      POSTGRES_MULTIPLE_DATABASES: db1::u1::p1|db2::u2::p2|db3::u3::p3
#      POSTGRES_PASSWORD: postgres
#    ports:
#      - "5432:5432"
#    volumes:
#      - ./create-multiple-postgresql-databases.sh:/docker-entrypoint-initdb.d/create-multiple-postgresql-databases.sh
###############################################################################
set -e
set -u

function create_user_and_database() {
	local database=$(echo $1 | tr '::' ' ' | awk  '{print $1}')
	local owner=$(echo $1 | tr '::' ' ' | awk  '{print $2}')
	local pass=$(echo $1 | tr '::' ' ' | awk  '{print $3}')
	echo "  Creating user '$owner' and database '$database'"
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
	    CREATE USER $owner WITH SUPERUSER PASSWORD '$pass';
	    CREATE DATABASE $database;
      GRANT ALL ON DATABASE $database TO $owner;
      ALTER DATABASE $database OWNER TO $owner;
      GRANT ALL ON SCHEMA PUBLIC TO $owner;
EOSQL
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
	echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
	for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr '|' ' '); do
		create_user_and_database $db
	done
	echo "Multiple databases created"
fi
