ARG POSTGRES_VERSION
FROM postgres:${POSTGRES_VERSION}
ENV POSTGRES_USER=testuser
ENV POSTGRES_PASSWORD=testpassword
# ENV POSTGRES_HOST_AUTH_METHOD=trust
# ENV POSTGRES_INITDB_ARGS='--auth-host=trust --auth-local=trust --wal-level=logical --max_replication_slots=4 --max_wal_senders=4'

# Environment variables to enable logical replication
# ENV WAL_LEVEL=logical
# ENV MAX_REPLICATION_SLOTS=4
# ENV MAX_WAL_SENDERS=4

# Copy the combined database setup script into the container
COPY ./init_db.sh /docker-entrypoint-initdb.d/init_db.sh

# Ensure the script is executable
RUN chmod +x /docker-entrypoint-initdb.d/init_db.sh
