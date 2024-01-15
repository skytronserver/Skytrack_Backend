python3 manage.py runserver 0.0.0.0:2000 >log.log &

lsof -i :2000

python3 manage.py makemigrations
python3  manage.py migrate