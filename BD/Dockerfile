FROM postgres:18-alpine
COPY ./init-scripts/ /docker-entrypoint-initdb.d/
ENV POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=12358 \
    POSTGRES_DB=pulkovo
EXPOSE 5432
# -v pgdata_volume:/var/lib/postgresql
