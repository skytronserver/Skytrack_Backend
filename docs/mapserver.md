sudo apt install default-jre unzip -y



cd /opt
sudo wget https://sourceforge.net/projects/geoserver/files/GeoServer/2.25.0/geoserver-2.25.0-bin.zip
sudo unzip geoserver-2.25.0-bin.zip
sudo mv geoserver-2.25.0 geoserver

cd bin
./startup.sh



Default URL in browser (from same machine):

http://localhost:8080/geoserver

Default login:

user: admin

pass: geoserver (change this later)

If your web app is on another machine, use http://<server-ip>:8080/geoserver.