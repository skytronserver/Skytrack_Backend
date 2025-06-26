python3 manage.py runserver 0.0.0.0:2000 >log.log 2>&1 &

#lsof -i :2000
lsof -i :5001
lsof -i :6000
cd Skytronsystem/
python3 manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:2000 >log.log 2>&1 &
nohup python3 manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:2000 > log.log 2>&1 &
#python3 manage.py makemigrations
#python3  manage.py migrate
#./run.sh >logError.log &
#https://skytrack.tech:2000/
#export MAIL_ID=testskytrack@gmail.com
#export MAIL_PW=zmzmexdnrlmsqrlr

tmux new -s run_main
cd Skytronsystem/
gunicorn --certfile=cert.pem  --keyfile=key.pem -b 0.0.0.0:2000 Skytronsystem.wsgi:application

tmux new -s run_gps
cd Skytronsystem/
 python3 manage.py tcp_serverd 

source ../venv/bin/activate
tmux new -s run_em
cd Skytronsystem/
python3 em_server.py

tmux new -s run_fota
cd Skytronsystem/skytron_api/
python3 fota_ftp.py

tmux new -s run_mqtt
cd Skytronsystem/
python3 mqttClienttrack.py


tmux attach -d -t run_main
gunicorn Skytronsystem.wsgi:application

gunicorn -c gunicorn.conf.py Skytronsystem.wsgi:application

python3 722767 root    7u  IPv4  9337826      0t0  TCP *:cisco-sccp (LISTEN)
python3 725033 root    7u  IPv4  9337826      0t0  TCP *:cisco-sccp (LISTEN)
python3 725033 root    8u  IPv4  9337826      0t0  TCP *:cisco-sccp (LISTEN)
python3 725033 root    9u  IPv4 10026146      0t0  TCP admiring-solomon.216-10-244-243.plesk.page:cisco-sccp->internettl.org:49380 (ESTABLISHED)



tmux new -s run_em
tmux attach -d -t run_main

nohup gunicorn --certfile=cert.pem  --keyfile=key.pem -b 0.0.0.0:2000 Skytronsystem.wsgi:application 
 --static-map /var/www/html/skytron_backend/staticfiles
--static-map /static=/var/www/html/skytron_backend/Skytronsystem/skytron_api/static

nohup  python3 manage.py tcp_server --traceback >logtcp.log 2>&1 &
nohup gunicorn --certfile=cert.pem  --keyfile=key.pem -b 0.0.0.0:2000 Skytronsystem.wsgi:application 

nohup  python3 em_server.py > tcplogem.log 2>&1 &
#export MAIL_ID=testskytrack@gmail.com
#export MAIL_PW=zmzmexdnrlmsqrlr

IMEI:868019065935497
regNo:DL-01-0002

IMEI:868960065434082
regNo:L89_001-0000

IMEI:868960065505253
regNo:GEM1205-05-000

IMEI:868960065504918
regNo:GEM1205-04-00

hCAPTCHA
sitekey :156ecd3a-9f4e-4549-a7d2-b8274bb9ed59

sitekey  :ES_6fc59979a06246568e25f281986eb133



pgsql   
dbadmin
lask1028zmnx
createdb skytrondb;
skytron_main_db
GRANT ALL PRIVILEGES ON DATABASE skytrondb TO dbadmin;
GRANT ALL PRIVILEGES ON DATABASE skytron_main_db TO dbadmin;


python3  manage.py migrate




216.10.244.243   lask1028zmnx
pg_dump -U dbadmin -h 216.10.244.243 -p 5432 -F c -b -v -f skytrondbnew2_backup.dump skytrondbnew2
pg_dump -U dbadmin -h 216.10.244.243 -p 5432 -F c -b -v -f  skytron_main_db_backup.dump  skytron_main_db
pg_dump -U dbadmin -h 216.10.244.243 -p 5432 -F c -b -v -f  skytrondbnew_backup.dump  skytrondbnew
pg_dump -U dbadmin -h 216.10.244.243 -p 5432 -F c -b -v -f skytrondb_backup.dump skytrondb 



CREATE DATABASE skytron_main_db;
GRANT ALL PRIVILEGES ON DATABASE skytron_main_db TO dbadmin;

CREATE DATABASE skytrondbnew2;
GRANT ALL PRIVILEGES ON DATABASE skytrondbnew2 TO dbadmin;

CREATE DATABASE skytrondb;
GRANT ALL PRIVILEGES ON DATABASE skytrondb TO dbadmin;
CREATE DATABASE skytrondbnew;
GRANT ALL PRIVILEGES ON DATABASE skytrondbnew TO dbadmin;
\q

lask1028zmnx
pg_restore -U dbadmin -h localhost -p 5432 -d skytrondb -v skytrondb_backup.dump
pg_restore -U dbadmin -h localhost -p 5432 -d skytrondbnew -v skytrondbnew_backup.dump
pg_restore -U dbadmin -h localhost -p 5432 -d skytrondbnew2 -v skytrondbnew2_backup.dump
pg_restore -U dbadmin -h localhost -p 5432 -d skytron_main_db -v skytron_main_db_backup.dump