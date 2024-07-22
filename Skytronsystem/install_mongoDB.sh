wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod 
sudo systemctl status mongod
sudo systemctl enable mongod 
python3 -m pip install djongo
python3 -m pip  install djongo pymongo

python3 manage.py dumpdata > data.json




mongo


use admin
db.createUser({
  user: "admin1",
  pwd: "adminpassword",
  roles: [ { role: "userAdminAnyDatabase", db: "admin" } ]
});
mongo -u admin1 -p adminpassword --authenticationDatabase admin


>use sktrondatabase
>db.createUser({
  user: "admin",
  pwd: "0o8iu7y73er43e",
  roles: [{ role: "readWrite", db: "sktrondatabase" }]
});

db.auth("admin","0o8iu7y73er43e")

python3 manage.py makemigrations
python3 manage.py migrate











###############working part next 
pip install mongoengine
