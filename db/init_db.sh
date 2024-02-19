#!/bin/bash
set -e

# Create the testdb database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE testdb;
EOSQL

# Connect to testdb and set up the sysconf table
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname testdb <<-EOSQL
    CREATE TABLE sysconf (
        key VARCHAR(255) PRIMARY KEY,
        value TEXT NOT NULL
    );
    INSERT INTO sysconf (key, value) VALUES
    ('app_name', 'MyApplication'),
    ('app_version', '1.0.0'),
    ('maintenance_mode', 'false');
EOSQL
