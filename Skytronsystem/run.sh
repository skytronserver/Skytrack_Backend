python3 manage.py runserver 0.0.0.0:2000 >log.log 2>&1 &

#lsof -i :2000
cd Skytronsystem/
python3 manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:2000 >log.log 2>&1 &
nohup python3 manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:2000 > log.log 2>&1 &
#python3 manage.py makemigrations
#Spython3  manage.py migrate
#./run.sh >logError.log &
#https://skytrack.tech:2000/

gunicorn Skytronsystem.wsgi:application

gunicorn -c gunicorn.conf.py Skytronsystem.wsgi:application


nohup gunicorn --certfile=cert.pem  --keyfile=key.pem -b 0.0.0.0:2000 Skytronsystem.wsgi:application &