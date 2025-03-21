sudo docker stop skytron-backend-api-container
sudo docker rm skytron-backend-api-container
sudo docker build -t skytron-backend-api -f dockerfile.api .
sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
sudo docker run -d  --restart=always -p 2000:2000    -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 


get config file from inside docker 

sudo docker exec -it skytron-app /bin/bash
cd /etc/nginx/sites-available

sudo docker cp skytron-app:/etc/nginx/conf.d/default.conf docker_nginx.conf