#!/bin/bash

echo "Waiting for postgres..."
while ! nc -z $DB_HOST $DB_PORT; do
    sleep 0.1
done

echo "PostgreSQL started"

echo "Running migrations..."
python3 manage.py makemigrations --settings=backend.settings.local
# python3 manage.py collectstatic --no-input --clear --settings=backend.settings.local
echo "Migrations complete"

echo "Running migrate..."
python3 manage.py migrate --settings=backend.settings.local
echo "Migrate complete"

# if [ "$FLUSH_DATABASE" = 1 ]; then
#     echo "Flushing database..."
#     python manage.py flush --no-input
#     echo "Database flushed"
# fi

exec "$@"
