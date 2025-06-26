sudo apt-get install mosquitto mosquitto-clients -y

sudo systemctl start mosquitto
sudo systemctl enable mosquitto
sudo mkdir /etc/mosquitto/certs /etc/mosquitto/ca_certificates
sudo apt-get install openssl
openssl genpkey -algorithm RSA -out ca.key
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=YourCA"
openssl genpkey -algorithm RSA -out server.key
openssl req -new -key server.key -out server.csr -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=135.235.166.209"

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650
openssl genpkey -algorithm RSA -out client.key
openssl req -new -key client.key -out client.csr -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=ClientName"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 3650
sudo cp ca.crt /etc/mosquitto/ca_certificates/
sudo cp server.crt /etc/mosquitto/certs/
sudo cp server.key /etc/mosquitto/certs/
sudo cp client.crt /etc/mosquitto/certs/ # Optional
sudo cp client.key /etc/mosquitto/certs/ # Optional
sudo nano /etc/mosquitto/mosquitto.conf

sudo systemctl restart mosquitto
python3 -m pip install paho-mqtt
sudo apt-get install mosquitto-clients
mosquitto_sub -h localhost -p 8883 --capath /var/www/html/skytron_backend/Skytronsystem/mqttKeys -t '#'


mosquitto_sub -h '135.235.166.209' -p 8883 -t '#' --cafile ca.crt --cert client.crt --key client.key

mosquitto_sub -h '4.240.90.1' -p 8883 -t '#' --cafile /home/azureuser/Skytrack_Backend/Skytronsystem/mqttKeys/ca.crt --cert /home/azureuser/Skytrack_Backend/Skytronsystem/mqttKeys/client.crt --key /home/azureuser/Skytrack_Backend/Skytronsystem/mqttKeys/client.key


4.240.90.1