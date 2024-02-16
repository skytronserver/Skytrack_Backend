python3 manage.py runserver 0.0.0.0:2000 >log.log 2>&1 &

#lsof -i :2000
python3 manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:2000 >log.log 2>&1 &
#python3 manage.py makemigrations
#Spython3  manage.py migrate
#./run.sh >logError.log &
#https://skytrack.tech:2000/