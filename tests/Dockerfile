# Builds an empty postgres database
FROM postgres:latest
ENV POSTGRES_USER=testuser
ENV POSTGRES_PASSWORD=testpassword
RUN echo "#!/bin/bash\nset -e\npsql -v ON_ERROR_STOP=1 --username \"\$POSTGRES_USER\" <<-EOSQL\n    CREATE DATABASE testdb;\nEOSQL" > /docker-entrypoint-initdb.d/create_db.sh && chmod +x /docker-entrypoint-initdb.d/create_db.sh