
sudo docker build -t skytron-backend-api -f dockerfile.api .
sudo docker stop skytron-backend-api-container
sudo docker rm skytron-backend-api-container
#sudo docker run -d  -p 2000:2000  -e  MAIL_ID=noreply@skytron.in  -e  MAIL_PW=Developer@18062025  --name skytron-backend-api-container skytron-backend-api
sudo docker run -d  --restart=always -p 2000:2000    -e  MAIL_ID=noreply@skytron.in  -e  MAIL_PW=Developer@18062025  --name skytron-backend-api-container skytron-backend-api 

 
#sudo docker stop skytron-backend-mqtt-container
#sudo docker rm skytron-backend-mqtt-container
#sudo docker build -t skytron-backend-mqtt -f dockerfile.mqtt .
#sudo docker run -d  --restart=always     -e  MAIL_ID=noreply@skytron.in  -e  MAIL_PW=Developer@18062025  --name skytron-backend-mqtt-container skytron-backend-mqtt 

 





#get config file from inside docker 

#sudo docker exec -it skytron-app /bin/bash
#cd /etc/nginx/sites-available

#sudo docker cp skytron-app:/etc/nginx/conf.d/default.conf docker_nginx.conf