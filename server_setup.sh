sudo apt-get update

sudo apt-get install nginx  mosquitto   mosquitto-clients   openssl  postgresql-contrib   git -y
sudo apt-get install nginx-extras

sudo nano /etc/nginx/nginx.conf
uncomment the line 
server_tokens off;
###pgsql setup 
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -i -u postgres
psql
CREATE DATABASE skytrondbnew2;
CREATE USER dbadmin WITH PASSWORD 'lask1028zmnx';

\c skytrondbnew2;
GRANT USAGE ON SCHEMA public TO dbadmin;
GRANT CREATE ON SCHEMA public TO dbadmin;
GRANT ALL PRIVILEGES ON DATABASE skytrondbnew2 TO dbadmin;
GRANT ALL PRIVILEGES ON SCHEMA public TO dbadmin;

GRANT USAGE ON SCHEMA public TO dbadmin;
GRANT CREATE ON SCHEMA public TO dbadmin;



\q
exit
sudo nano /etc/postgresql/12/main/pg_hba.conf
#local   all   postgres   peer  
>>>
#local   all   all   md5
host    all     all     0.0.0.0/0       md5

sudo nano /etc/postgresql/12/main/postgresql.conf
add
#listen_addresses = '*'

sudo systemctl restart postgresql
#test
psql -U dbadmin -d skytrondbnew2 -h localhost -W


\q


psql -U dbadmin -d skytrondbnew2 -h 20.210207.21 -W
  

### Docker installation 
sudo apt-get update 
sudo apt-get install ca-certificates curl gnupg lsb-release -y
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo apt  install docker-compose -y

sudo docker run hello-world
 

### docker deployment   --add-host=host.docker.internal:host-gateway 
sudo docker build -t skytron-backend-api . 
sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api

    nc -zv 216.10.247.182 5432
#check
docker ps
#restart
sudo docker stop skytron-backend-api-container
sudo docker rm skytron-backend-api-container
docker image prune -f


#port opening
sudo ufw enable
sudo ufw allow 5432/tcp
sudo ufw allow 443/tcp
sudo ufw allow 2000/tcp
sudo ufw allow 22/tcp
sudo ufw reload
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

Save the rule persistently:

sudo apt install iptables-persistent
sudo netfilter-persistent save


###nginx configuration 
sudo cp /var/www/html/Skytrack_Backend/api.conf /etc/nginx/sites-available/
sudo cp /var/www/html/Skytrack_Backend/www.conf /etc/nginx/sites-available/
sudo cp ../api.conf /etc/nginx/sites-available/
sudo cp ../www.conf /etc/nginx/sites-available/


sudo rm /etc/nginx/sites-enabled/www.conf 
sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
sudo nano  /etc/nginx/sites-available/api.conf 


sudo rm /etc/nginx/sites-enabled/www.conf 
sudo rm /etc/nginx/sites-enabled/api.conf 
sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/api.conf /etc/nginx/sites-enabled/

sudo nginx -t
sudo systemctl reload nginx


###MQTT setup
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

sudo mkdir /etc/mosquitto/certs /etc/mosquitto/ca_certificates

openssl genpkey -algorithm RSA -out ca.key
openssl req -new -x509 -days 36500 -key ca.key -out ca.crt -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/"
openssl genpkey -algorithm RSA -out server.key
openssl req -new -key server.key -out server.csr -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/CN=4.240.90.1"


openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 36500
openssl genpkey -algorithm RSA -out client.key
openssl req -new -key client.key -out client.csr -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 36500
sudo cp ca.crt /etc/mosquitto/ca_certificates/
sudo cp server.crt /etc/mosquitto/certs/
sudo cp server.key /etc/mosquitto/certs/
sudo cp client.crt /etc/mosquitto/certs/ # Optional
sudo cp client.key /etc/mosquitto/certs/ # Optional
sudo nano /etc/mosquitto/mosquitto.conf
>pid_file /var/run/mosquitto.pid
>persistence true
>persistence_location /var/lib/mosquitto/
>log_dest file /var/log/mosquitto/mosquitto.log
>listener 8883
>cafile /etc/mosquitto/ca_certificates/ca.crt
>certfile /etc/mosquitto/certs/server.crt
>keyfile /etc/mosquitto/certs/server.key
>require_certificate false
>tls_version tlsv1.2
>include_dir /etc/mosquitto/conf.d
sudo systemctl restart mosquitto
#test
mosquitto_sub -h localhost -p 8883 --capath /var/www/html/skytron_backend/Skytronsystem -t '#'


sudo docker stop skytron-backend-api-container
sudo docker rm skytron-backend-api-container
sudo docker build -t skytron-backend-api . 
sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api

sudo docker run -d --restart=always -p 2000:2000   -e MAIL_ID=testskytrack@gmail.com  -e MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  skytron-backend-api


#ssl check
openssl x509 -in /var/www/html/Skytrack_Backend/Skytronsystem/cert.pem -text -noout
openssl rsa -in /var/www/html/Skytrack_Backend/Skytronsystem/key.pem -check
openssl x509 -noout -modulus -in  /var/www/html/Skytrack_Backend/Skytronsystem/cert.pem | openssl md5
openssl rsa -noout -modulus -in /var/www/html/Skytrack_Backend/Skytronsystem/key.pem | openssl md5






sudo docker build -t skytron-backend-api -f dockerfile.api .
 
sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 

 
sudo docker run -d  --restart=always -p 2000:2000    -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
sudo docker run -d  --restart=always -p 2000:2000    -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
 


sudo docker build -t skytron-backend-mqtt -f dockerfile.mqtt .
sudo docker run -d  --restart=always -p 2000:2000  -f dockerfile.mqtt -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 

 

mosquitto_sub -h '216.10.244.243' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key

mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key

sudo docker build -t skytron-backend-api -f dockerfile.api .
sudo docker stop skytron-backend-api-container
sudo docker rm skytron-backend-api-container
sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
<<<<<<< gromed2

=======
 
sudo docker build -t skytron-backend-gps -f dockerfile.gps .
sudo docker run -d  --restart=always -p 6000:6000   -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-gps skytron-backend-gps
 
>>>>>>> skytronV2_toNIC
