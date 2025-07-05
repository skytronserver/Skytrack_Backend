    1  sudo docker-compose build
    2  sudo docker-compose up -d
    3  sud docker ps 
    4  sudo docker ps 
    5  sudo docker-compose build
    6  sudo docker-compose up -d
    7  sudo docker ps 
    8  sudo docker-compose up -d
    9  sudo docker ps 
   10  sudo docker-compose build
   11  sudo docker-compose up -d
   12  sudo docker-compose build
   13  sudo docker-compose up -d
   14  sudo docker-compose build
   15  sudo docker-compose up -d
   16  sudo docker-compose build
   17  docker-compose down -v
   18  sudo docker-compose down -v
   19  sudo docker image prune -a
   20  sudo docker container prune
   21  sudo docker-compose build
   22  sudo docker-compose up -d
   23  cd Skytronsystem/
   24  ls
   25  sudo docker build -t skytron-backend-api . 
   26  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
   27  sudo docker ps 
   28  sudo docker logs skytron-backend-api-container
   29  sudo cp ../www.conf /etc/nginx/sites-available/
   30  ls
   31  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
   32  sudo nginx -t
   33  sudo systemctl reload nginx
   34  sudo rm /etc/nginx/sites-available/www.conf 
   35  sudo rm /etc/nginx/sites-enabled/www.conf 
   36  sudo cp ../www.conf /etc/nginx/sites-available/
   37  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
   38  sudo systemctl reload nginx
   39  sudo docker stop skytron-backend-api
   40  sudo docker ps
   41  sudo docker stop skytron-backend-api-container
   42  sudo docker rm skytron-backend-api-container
   43  sudo docker build -t skytron-backend-api . 
   44  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
   45  sudo apt-get update
   46  sudo apt-get install nginx  mosquitto   mosquitto-clients   openssl  postgresql-contrib   git -y
   47  sudo systemctl start postgresql
   48  sudo systemctl enable postgresql
   49  sudo -i -u postgres
   50  sudo nano /etc/postgresql/12/main/pg_hba.conf
   51  sudo nano /etc/postgresql/14/main/pg_hba.conf
   52  sudo nano /etc/postgresql/14/main/postgresql.conf
   53  sudo systemctl restart postgresql
   54  sudo apt-get update 
   55  sudo apt-get install ca-certificates curl gnupg lsb-release -y
   56  sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
   57  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
   58  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   59  sudo apt-get update
   60  sudo apt-get install docker-ce docker-ce-cli containerd.io -y
   61  sudo apt-get install -y docker-ce docker-ce-cli containerd.io
   62  sudo apt  install docker-compose -y
   63  sudo docker run hello-world
   64  sudo rm /etc/nginx/sites-enabled/www.conf 
   65  cd Skytronsystem/
   66  sudo cp ../www.conf /etc/nginx/sites-available/
   67  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
   68  sudo systemctl reload nginx
   69  cd ../
   70  SRC_HOST="216.10.244.243"
   71  SRC_PORT="5432"
   72  SRC_DB="skytrondbnew2"
   73  SRC_USER="dbadmin"
   74  SRC_PASS="lask1028zmnx"
   75  DEST_HOST="localhost"
   76  DEST_PORT="5432"
   77  DEST_DB="skytrondbnew2"
   78  DEST_USER="dbadmin"
   79  DEST_PASS="lask1028zmnx"
   80  export PGPASSWORD="$SRC_PASS"
   81  pg_dump -h "$SRC_HOST" -p "$SRC_PORT" -U "$SRC_USER" -Fc "$SRC_DB" | PGPASSWORD="$DEST_PASS" pg_restore -h "$DEST_HOST" -p "$DEST_PORT" -U "$DEST_USER" -d "$DEST_DB" --clean --create
   82  pg_dump -h "$SRC_HOST" -p "$SRC_PORT" -U "$SRC_USER" -Fc "$SRC_DB" | PGPASSWORD="$DEST_PASS" pg_restore -h "$DEST_HOST" -p "$DEST_PORT" -U "$DEST_USER" -d "$DEST_DB"
   83  sudo -i -u postgres
   84  pg_dump -h "$SRC_HOST" -p "$SRC_PORT" -U "$SRC_USER" -Fc "$SRC_DB" | PGPASSWORD="$DEST_PASS" pg_restore -h "$DEST_HOST" -p "$DEST_PORT" -U "$DEST_USER" -d "$DEST_DB"
   85  sudo docker stop skytron-backend-api-container
   86  sudo docker rm skytron-backend-api-container
   87  sudo docker build -t skytron-backend-api . 
   88  cd Skytrack_Backend/Skytronsystem/
   89  sudo docker build -t skytron-backend-api . 
   90  sudo docker run -d --restart=always -p 2000:2000   -e MAIL_ID=testskytrack@gmail.com  -e MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  skytron-backend-api
   91  sudo docker ps 
   92  sudo docker logs skytron-backend-api-container
   93  sudo docker stop skytron-backend-api-container
   94  sudo docker rm skytron-backend-api-container
   95  docker image prune -f
   96  sudo docker image prune -f
   97  python3 manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:2000 
   98  export DB_NAME=skytrondbnew2
   99  export DB_USER=dbadmin
  100  export DB_PASSWORD=lask1028zmnx
  101  export DB_HOST=4.240.90.1
  102  export DB_PORT=5432
  103  export MAIL_ID=testskytrack@gmail.com
  104  export MAIL_PW=zmzmexdnrlmsqrlr
  105  export DEBUG=False
  106  export SECRET_KEY=django-insecure-j4+*w3&%@iy2r)-7dz%_mk10%)4gjx1w5n&mve&=zfwx@)f2ql
  107  export DATABASE_URL=postgres://dbadmin:lask1028zmnx@localhost:5432/skytrondbnew2
  108  export EMAIL_HOST_USER=testskytrack@gmail.com
  109  export EMAIL_HOST_PASSWORD=zmzmexdnrlmsqrlr
  110  export ALLOWED_HOSTS="api.skytron.in, skytron.in, dev.skytron.in, api-dev.skytron.in, skytrack.tech, skytrack.tech:2000, localhost,localhost:2000"
  111  export DB_NAME=skytrondbnew2
  112  export DB_USER=dbadmin
  113  export DB_PASSWORD=lask1028zmnx
  114  export DB_HOST=4.240.90.1
  115  export DB_PORT=5432
  116  export MAIL_ID=testskytrack@gmail.com
  117  export MAIL_PW=zmzmexdnrlmsqrlr
  118  export DEBUG=False
  119  export SECRET_KEY="django-insecure-j4+*w3&%@iy2r)-7dz%_mk10%)4gjx1w5n&mve&=zfwx@)f2ql"
  120  export DATABASE_URL=postgres://dbadmin:lask1028zmnx@localhost:5432/skytrondbnew2
  121  export EMAIL_HOST_USER=testskytrack@gmail.com
  122  export EMAIL_HOST_PASSWORD=zmzmexdnrlmsqrlr
  123  export ALLOWED_HOSTS="api.skytron.in, skytron.in, dev.skytron.in, api-dev.skytron.in, skytrack.tech, skytrack.tech:2000, localhost,localhost:2000"
  124  python3 manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:2000 
  125  sudo docker build -t skytron-backend-api . 
  126  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  127  sudo docker logs skytron-backend-api-container
  128  sudo docker stop skytron-backend-api-container
  129  sudo docker rm skytron-backend-api-container
  130  sudo docker build -t skytron-backend-api . 
  131  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  132  sudo docker stop skytron-backend-api-container
  133  sudo docker rm skytron-backend-api-container
  134  sudo docker build -t skytron-backend-api . 
  135  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  136  sudo docker logs skytron-backend-api-container
  137  sudo docker stop skytron-backend-api-container
  138  sudo docker rm skytron-backend-api-container
  139  sudo docker build -t skytron-backend-api . 
  140  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  141  sudo docker stop skytron-backend-api-container
  142  sudo docker rm skytron-backend-api-container
  143  sudo docker build -t skytron-backend-api . 
  144  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  145  sudo docker stop skytron-backend-api-container
  146  sudo docker rm skytron-backend-api-container
  147  sudo docker build -t skytron-backend-api . 
  148  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  149  sudo docker stop skytron-backend-api-container
  150  sudo docker rm skytron-backend-api-container
  151  sudo docker build -t skytron-backend-api . 
  152  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  153  sudo docker stop skytron-backend-api-container
  154  sudo docker rm skytron-backend-api-container
  155  sudo docker build -t skytron-backend-api . 
  156  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  157  sudo docker stop skytron-backend-api-container
  158  sudo docker rm skytron-backend-api-container
  159  sudo docker build -t skytron-backend-api . 
  160  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  161  sudo apt  install docker-compose -y
  162  sudo docker-compose build
  163  sudo docker-compose up -d
  164  docker compose down -v
  165  sudo docker compose down -v
  166  docker image prune -a
  167  sudo docker image prune -a
  168  sudo docker-compose build
  169  sudo docker-compose up -d
  170  sudo mkdir -p /var/lib/openproject/{pgdata,assets}
  171  sudo docker run -d -p 5000:80 --name openproject   -e OPENPROJECT_HOST__NAME=pm.skytrack.tech   -e OPENPROJECT_SECRET_KEY_BASE=secret   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   openproject/openproject:15
  172  ls
  173  cd..
  174  cd ..
  175  ls
  176  cd openproject/
  177  sudo cp /etc/nginx/sites-available/www.conf /etc/nginx/sites-available/cp.conf 
  178  sudo cp /etc/nginx/sites-available/www.conf /etc/nginx/sites-available/pm.conf 
  179  sudo chmod 777 /etc/nginx/sites-available/pm.conf 
  180  sudo ln -s /etc/nginx/sites-available/pm.conf /etc/nginx/sites-enabled/
  181  sudo systemctl reload nginx
  182  curl --location 'https://staging.parivahan.gov.in/vltdmakerws/dataportws?wsdl=null' --header 'Content-Type: text/xml; charset=utf-8' --data-raw '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.web.homologation.transport.nic/">
  183     <soapenv:Header/>
  184     <soapenv:Body>
  185        <ser:getVltdInfoByIMEI>          
  186           <userId>asbackendtest</userId>
  187           <transactionPass>Asbackend@123</transactionPass>       
  188           <imeiNo>862273046827366</imeiNo>
  189        </ser:getVltdInfoByIMEI>
  190     </soapenv:Body>
  191  </soapenv:Envelope>'
  192  sudo rm  /etc/nginx/sites-enabled/pm.conf 
  193  sudo ln -s /etc/nginx/sites-available/pm.conf /etc/nginx/sites-enabled/
  194  sudo systemctl reload nginx
  195  sudo nano /home/azureuser/cert_st_old.pem
  196  /home/azureuser/cert_st_all.pem
  197  sudo nano /home/azureuser/cert_st_all.pem
  198  sudo nano /home/azureuser/key_st_all.pem
  199  sudo rm  /etc/nginx/sites-enabled/pm.conf 
  200  sudo ln -s /etc/nginx/sites-available/pm.conf /etc/nginx/sites-enabled/
  201  sudo systemctl reload nginx
  202  journalctl -xeu nginx.service
  203  sudo systemctl reload nginx
  204  sudo rm  /etc/nginx/sites-enabled/pm.conf 
  205  sudo systemctl reload nginx
  206  sudo chmod 777 /home/azureuser/key_st_all.pem
  207  sudo chmod 777  /home/azureuser/cert_st_all.pem
  208  sudo ln -s /etc/nginx/sites-available/pm.conf /etc/nginx/sites-enabled/
  209  sudo nginx -t
  210  /home/azureuser/Skytrack_Backend/Skytronsystem/cert.pem
  211  sudo docker pm 
  212  sudo docker ps
  213  sudo docker stop  skytron-app
  214  python3 -m http.server 3000
  215  sudo docker start  skytron-app
  216  sudo docker-compose build
  217  sudo docker-compose up -d
  218  sudo docker ps 
  219  sudo docker-compose up -d
  220  sudo docker ps 
  221  sudo docker-compose build
  222  sudo docker-compose up -d
  223  sudo docker ps 
  224  sudo docker-compose up -d
  225  sudo docker ps 
  226  sudo docker-compose build
  227  sudo docker-compose up -d
  228  sudo docker-compose build
  229  sudo docker-compose up -d
  230  ls
  231  sudo docker ps
  232  sudo docker stop skytron-app
  233  sudo docker stop openproject
  234  python -m SimpleHTTPServer 5000
  235  python3 -m SimpleHTTPServer 5000
  236  python3 -m http.server 5000
  237  python3 -m http.server 3000
  238  sudo docker rm skytron-app
  239  sudo docker rm openproject
  240  sudo docker system prune
  241  sudo docker run -d -p 5000:80 --name openproject   -e OPENPROJECT_HOST__NAME=pm.skytrack.tech   -e OPENPROJECT_SECRET_KEY_BASE=secret   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   openproject/openproject:15
  242  sudo docker ps 
  243  sudo docker stop openproject
  244  sudo docker rm  openproject
  245  sudo docker run -d -p 5000:80 --name openproject   -e OPENPROJECT_HOST__NAME=op.gromed.in   -e OPENPROJECT_SECRET_KEY_BASE=secret   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   openproject/openproject:15
  246  sudo docker stop openproject
  247  sudo docker rm  openproject
  248  sudo docker run -d -p 5000:80 --name openproject   -e OPENPROJECT_SECRET_KEY_BASE=secret   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   openproject/openproject:15
  249  cp .env.example .env
  250  sudo mkdir -p /var/openproject/assets
  251  sudo chown 1000:1000 -R /var/openproject/assets
  252  OPENPROJECT_HTTPS=false docker compose up -d --build --pull always
  253  sudo OPENPROJECT_HTTPS=false docker compose up -d --build --pull always
  254  sudo rm /etc/nginx/sites-enabled/www.conf 
  255  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  256  sudo systemctl reload nginx
  257  sudo chmod 777  /home/azureuser/cert_st_all.pem
  258  sudo rm /etc/nginx/sites-enabled/www.conf 
  259  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  260  sudo systemctl reload nginx
  261  sudo rm /etc/nginx/sites-enabled/www.conf 
  262  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  263  sudo systemctl reload nginx
  264  ls /var/log/nginx/error.log
  265  sudo rm /etc/nginx/sites-enabled/www.conf 
  266  sudo systemctl reload nginx
  267  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  268  sudo systemctl reload nginx
  269  tail /var/log/nginx/error.log
  270  ls /home/azureuser/Skytrack_Backend/Skytronsystem/key_old.pem
  271  ls /home/azureuser/Skytrack_Backend/Skytronsystem/cert_old.pem
  272  sudo rm /etc/nginx/sites-enabled/www.conf 
  273  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  274  sudo systemctl reload nginx
  275  tail /var/log/nginx/error.log
  276  sudo systemctl reload nginx
  277  tail /var/log/nginx/error.log
  278  sudo systemctl reload nginx
  279  tail /var/log/nginx/error.log
  280  tail /var/log/nginx/access.log
  281  sudo rm /etc/nginx/sites-enabled/www.conf 
  282  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  283  sudo systemctl reload nginx
  284  sudo rm /etc/nginx/sites-enabled/www.conf 
  285  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  286  sudo systemctl reload nginx
  287  tail /var/log/nginx/access.log
  288  tail /var/log/nginx/error.log
  289  sudo rm /etc/nginx/sites-enabled/www.conf 
  290  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  291  sudo systemctl reload nginx
  292  sudo chmod 777 -R /etc/nginx/sites-available/
  293  sudo ln -s /etc/nginx/sites-available/api.conf /etc/nginx/sites-enabled/
  294  sudo systemctl reload nginx
  295  sudo rm /etc/nginx/sites-enabled/api.conf 
  296  sudo rm /etc/nginx/sites-enabled/www.conf 
  297  sudo ln -s /etc/nginx/sites-available/api.conf /etc/nginx/sites-enabled/
  298  /etc/nginx/sites-available/www.conf
  299  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  300  sudo systemctl reload nginx
  301  sudo rm /etc/nginx/sites-enabled/www.conf 
  302  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  303  sudo systemctl reload nginx
  304  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  305  sudo systemctl reload nginx
  306  sudo rm /etc/nginx/sites-enabled/www.conf 
  307  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  308  sudo systemctl reload nginx
  309  sudo rm /etc/nginx/sites-enabled/www.conf 
  310  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  311  sudo systemctl reload nginx
  312  sudo rm /etc/nginx/sites-enabled/www.conf 
  313  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  314  sudo systemctl reload nginx
  315  sudo rm /etc/nginx/sites-enabled/www.conf 
  316  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  317  sudo systemctl reload nginx
  318  sudo rm /etc/nginx/sites-enabled/www.conf 
  319  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  320  sudo systemctl reload nginx
  321  sudo rm /etc/nginx/sites-enabled/www.conf 
  322  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  323  sudo systemctl reload nginx
  324  sudo rm /etc/nginx/sites-enabled/www.conf 
  325  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  326  sudo systemctl reload nginx
  327  sudo rm /etc/nginx/sites-enabled/www.conf 
  328  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  329  sudo systemctl reload nginx
  330  tail /var/log/nginx/access.log
  331  tail /var/log/nginx/error.log
  332  sudo systemctl reload nginx
  333  tail /var/log/nginx/error.log
  334  sudo systemctl reload nginx
  335  tail /var/log/nginx/error.log
  336  sudo rm /etc/nginx/sites-enabled/www.conf 
  337  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  338  sudo systemctl reload nginx
  339  sudo ln -s /etc/nginx/sites-available/op.conf /etc/nginx/sites-enabled/
  340  sudo systemctl reload nginx
  341  sudo rm /etc/nginx/sites-enabled/op.conf 
  342  sudo ln -s /etc/nginx/sites-available/op.conf /etc/nginx/sites-enabled/
  343  sudo systemctl reload nginx
  344  sudo rm /etc/nginx/sites-enabled/www.conf 
  345  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  346  sudo systemctl reload nginx
  347  sudo rm /etc/nginx/sites-enabled/www.conf 
  348  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  349  sudo systemctl reload nginx
  350  sudo rm /etc/nginx/sites-enabled/www.conf 
  351  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  352  sudo systemctl reload nginx
  353  sudo docker build -t skytron-backend-api . 
  354  cd Skytronsystem/
  355  sudo docker build -t skytron-backend-api . 
  356  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  357  sudo docker stop skytron-backend-api-container
  358  sudo docker rm skytron-backend-api-container
  359  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  360  sudo rm /etc/nginx/sites-enabled/www.conf 
  361  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  362  sudo systemctl reload nginx
  363  sudo rm /etc/nginx/sites-enabled/www.conf 
  364  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  365  sudo systemctl reload nginx
  366  sudo rm /etc/nginx/sites-enabled/www.conf 
  367  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  368  sudo systemctl reload nginx
  369  sudo rm /etc/nginx/sites-enabled/www.conf 
  370  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  371  sudo systemctl reload nginx
  372  tail /var/log/nginx/error.log
  373  sudo systemctl reload nginx
  374  sudo rm /etc/nginx/sites-enabled/www.conf 
  375  sudo ln -s /etc/nginx/sites-available/gt.conf /etc/nginx/sites-enabled/
  376  sudo systemctl reload nginx
  377  sudo ln -s /etc/nginx/sites-available/pm.conf /etc/nginx/sites-enabled/
  378  ls /etc/nginx/sites-available/www.conf 
  379  sudo chmod 777  /etc/nginx/sites-available/www.conf 
  380  sudo nginx -t
  381  sudo rm  /etc/nginx/sites-enabled/pm.conf 
  382  sudo rm  /etc/nginx/sites-enabled/www.conf 
  383  sudo ln -s /etc/nginx/sites-available/www.conf /etc/nginx/sites-enabled/
  384  sudo nginx -t
  385  sudo systemctl reload nginx
  386  sudo docker-compose build
  387  sudo docker-compose up -d
  388  sudo docker system prune
  389  sudo docker-compose up -d
  390  sudo chown -R 999:999 /var/lib/openproject/postgres-data
  391  sudo chmod -R 700 /var/lib/openproject/postgres-data
  392  sudo docker stop openproject
  393  sudo docker rm  openproject
  394  sudo docker run -d   --name openproject   -p 5000:80   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/postgres-data:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  395  sudo docker logs openproject 
  396  sudo docker stop openproject
  397  sudo docker rm  openproject
  398  sudo docker run -d   --name openproject   -p 5000:80   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/postgres-data:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  399  sudo docker logs openproject 
  400  ls /etc/nginx/sites-enabled/
  401  docker-compose build
  402  sudo docker-compose build
  403  sudo docker system purge 
  404  sudo docker system prune
  405  sudo docker-compose build
  406  ls /var/lib/openproject/pgdata
  407  sudo chmod /var/lib/openproject/pgdata 777
  408  ls /var/lib/openproject/
  409  sudo chmod 777 - R /var/lib/openproject/pgdata
  410  sudo chmod 777 -R /var/lib/openproject/pgdata
  411  ls /var/lib/openproject/
  412  sudo chmod 777 -R /var/lib/openproject
  413  sudo docker-compose build
  414  sudo mkdir -p /var/lib/openproject/postgres-data
  415  sudo mkdir -p /var/lib/openproject/assets
  416  sudo mkdir -p /var/lib/openproject/log
  417  sudo docker ps 
  418  sudo docker run -d -p 5000:80 --name openproject   -e OPENPROJECT_SECRET_KEY_BASE=secret   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:latest
  419  sudo docker-compose build
  420  sudo docker run -d -p 5000:80 --name openproject   -e OPENPROJECT_SECRET_KEY_BASE=secret   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:latest
  421  docker pull openproject/community:latest
  422  sudo docker pull openproject/community:latest
  423  sudo docker pull openproject/community:15
  424  docker build -t openproject:latest .
  425  sudo docker build -t openproject:latest .
  426  cd ../ 
  427  ls 
  428  sudo rm openproject/ -r
  429  sudo  docker run -d -p 5000:80 --name openproject   -e OPENPROJECT_SECRET_KEY_BASE=secret   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:latest
  430  sudo docker run -d -p 5000:80 --name openproject   -e OPENPROJECT_SECRET_KEY_BASE=secret   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/community:latest
  431  sudo docker run -d --name openproject   -p 5000:80   openproject/community:latest
  432  docker run -it -p 8080:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:8080   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   openproject/openproject:15
  433  sudo docker run -it -p 8080:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:8080   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   openproject/openproject:15
  434  sudo   docker run -it -p 5000:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:8080   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  435  sudo docker system prune 
  436  sudo   docker run -it -p 5000:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:8080   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  437  docker run -it -p 5000:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:5000   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  438  sudo docker run -it -p 5000:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:5000   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  439  sudo docker system prune 
  440  sudo docker run -it -p 5000:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:5000   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  441  docker stop openproject
  442  docker rm openproject
  443  sudo docker stop openproject
  444  docker rm openproject
  445  sudo docker rm openproject
  446  ls /var/lib/openproject/pgdata
  447  sudo rm /var/lib/openproject/pgdata/* -r
  448  ls /var/lib/openproject/pgdata
  449  sudo rm /var/lib/openproject/assets/*
  450  sudo rm /var/lib/openproject/assets/* -R
  451  sudo rm /var/lib/openproject/log/*  -r
  452  sudo docker system prune 
  453  sudo docker run -it -p 5000:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:5000   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  454  sudo docker run -d -p 5000:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=localhost:5000   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  455  sudo docker ps 
  456  sudo docker stop elated_hawking
  457  sudo docker run -d -p 5000:5000   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=op.gromed.in:5000   -e OPENPROJECT_HTTPS=false   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  458  sudo docker ps 
  459  sudo docker stop vibrant_sammet
  460  sudo docker run -d -p 5000:80   -e OPENPROJECT_SECRET_KEY_BASE=secret   -e OPENPROJECT_HOST__NAME=op.gromed.in   -e OPENPROJECT_HTTPS=true   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/pgdata:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  461  ls /etc/nginx/sites-available/
  462  ls /etc/nginx/sites-available/op.conf 
  463  sudo docker ps 
  464  sudo docker stop  keen_cerf
  465  sudo docker run -d   --name openproject   -p 80:80   -v /var/lib/openproject/postgres-data:/var/lib/postgresql/data   -v /var/lib/openproject/assets:/var/db/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/community:latest
  466  sudo docker run -d   --name openproject   -p 80:80   -v /var/lib/openproject/postgres-data:/var/lib/postgresql/data   -v /var/lib/openproject/assets:/var/db/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  467  sudo docker run -d   --name openproject   -p 5000:80   -v /var/lib/openproject/postgres-data:/var/lib/postgresql/data   -v /var/lib/openproject/assets:/var/db/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  468  sudo docker stop openproject
  469  sudo docker rm openproject
  470  sudo docker run -d   --name openproject   -p 5000:80   -v /var/lib/openproject/postgres-data:/var/lib/postgresql/data   -v /var/lib/openproject/assets:/var/db/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  471  sudo docker stop openproject
  472  sudo docker start openproject
  473  sudo docker logs openproject
  474  sudo docker stop openproject
  475  sudo docker rm openproject
  476  sudo docker run -d   --name openproject   -p 5000:80   -v /var/lib/openproject/postgres-data:/var/lib/postgresql/data   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  477  sudo docker logs openproject
  478  sudo docker stop openproject
  479  sudo docker rm openproject
  480  sudo docker run -d   --name openproject   -p 5000:80   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/postgres-data:/var/lib/postgresql/data   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  481  sudo docker logs openproject
  482  cd Skytronsystem/
  483  ls
  484  sudo docker ps
  485  sudo docker build -t skytron-backend-api . 
  486  sudo docker stop skytron-backend-api-container
  487  sudo docker rm skytron-backend-api-container
  488  sudo docker run -d  -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api
  489  sudo docker ps
  490  sudo docker ps 
  491  sudo docker container
  492  sudo docker ps -s
  493  sudo docker ps -a
  494  sudo docker start skytron-backend-api-container
  495  sudo docker start openproject
  496  sudo docker start skytron-app
  497  sudo docker rm keen_cerf
  498  sudo docker rm vibrant_sammet
  499  sudo docker rm elated_hawking
  500  sudo docker ps -a
  501  sudo docker rm vigilant_nightingale
  502  sudo docker ps -a
  503  htops
  504  htop
  505  sudo docker stop openproject
  506  sudo docker run -d --restart=always openproject
  507  sudo docker stop skytron-backend-api-container
  508  sudo docker rm  skytron-backend-api-container
  509  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  510  sudo docker stop skytron-app
  511  sudo docker-compose up -d  --restart=always 
  512  sudo docker-compose up -d  
  513  sudo docker-compose build
  514  sudo docker-compose up -d 
  515  sudod docker ps 
  516  sudo docker ps 
  517  sudo docker stop openproject
  518  sudo docker ps 
  519  sudo docker start openproject
  520  sudo docker ps 
  521  sudo docker systems prune
  522  sudo docker system prune
  523  sudo docker-compose up -d 
  524  sudod docker ps 
  525  sudo docker ps
  526  sudo dockder stop sopenproject 
  527  sudo docker stop sopenproject 
  528  sudo docker stop openproject 
  529  sudo docker rename openproject openproject2
  530  sudo docker ps -a
  531  sudo docker run -d --restart always  --name openproject   -p 5000:80   -e OPENPROJECT_DEFAULT__LANGUAGE=en   -v /var/lib/openproject/postgres-data:/var/openproject/pgdata   -v /var/lib/openproject/assets:/var/openproject/assets   -v /var/lib/openproject/log:/var/log/openproject   openproject/openproject:15
  532  sudo docker logs openproject
  533  cd Skytronsystem/
  534  sudo docker stop skytron-backend-api-container
  535  sudo docker rm  skytron-backend-api-container
  536  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  537  sudo docker stop skytron-backend-api-container
  538  sudo docker rm  skytron-backend-api-container
  539  sudo docker build -t skytron-backend-api . 
  540  cd  Skytronsystem/
  541  ls
  542  cd ../
  543  sudo docker ps 
  544  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  545  curl --location 'https://staging.parivahan.gov.in/vltdmakerws/dataportws?wsdl=null' --header 'Content-Type: text/xml; charset=utf-8' --data-raw '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.web.homologation.transport.nic/">
  546     <soapenv:Header/>
  547     <soapenv:Body>
  548        <ser:getVltdInfoByIMEI>          
  549           <userId>asbackendtest</userId>
  550           <transactionPass>Asbackend@123</transactionPass>       
  551           <imeiNo>862273046827366</imeiNo>
  552        </ser:getVltdInfoByIMEI>
  553     </soapenv:Body>
  554  </soapenv:Envelope>'
  555  cd Skytronsystem/
  556  ls
  557  ipconfig 
  558  ifconfig 
  559  sudo apt install net-tools
  560  ifconfig 
  561  sudo docker build -t skytron-backend-mqtt -f dockerfile.mqtt .
  562  sudo docker run -d  --restart=always -p 2000:2000  -f dockerfile.mqtt -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  563  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  564  sudo docker run -d  --restart=always  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  565  sudo docker stop skytron-backend-mqtt-container
  566  sudo docker rm skytron-backend-mqtt-container
  567  sudo docker stop skytron-backend-mqtt-container
  568  sudo docker rm skytron-backend-mqtt-container
  569  sudo dokcer ps
  570  sudo docker ps 
  571  sudo docker stop skytron-backend-mqtt-container
  572  sudo docker kill skytron-backend-mqtt-container
  573  sudo docker rm skytron-backend-mqtt-container
  574  sudo docker rm -f skytron-backend-mqtt-container
  575  sudo docker run -d  --restart=always -f dockerfile.mqtt -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  576  sudo docker run -d  --restart=always   -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  577  sudo docker logs  skytron-backend-mqtt 
  578  sudo docker logs  skytron-backend-mqtt-container
  579  sudo docker kill skytron-backend-mqtt-container
  580  sudo docker rm -f skytron-backend-mqtt-container
  581  sudo docker run -d  --restart=always   -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  582  sudo docker kill skytron-backend-mqtt-container
  583  sudo docker build -t skytron-backend-mqtt -f dockerfile.mqtt .
  584  sudo docker run -d  --restart=always   -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  585  sudo rm /skytron-backend-mqtt-container
  586  sudo docker rm  skytron-backend-mqtt-container
  587  sudo docker run -d  --restart=always   -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  588  sudo docker logs  skytron-backend-mqtt-container
  589  sudo docker kill skytron-backend-mqtt-container
  590  sudo docker rm  skytron-backend-mqtt-container
  591  sudo docker build -t skytron-backend-mqtt -f dockerfile.mqtt .
  592  sudo docker run -d  --restart=always   -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-mqtt-container skytron-backend-mqtt 
  593  sudo docker logs  skytron-backend-mqtt-container
  594  tail -f /var/log/mosquitto/mosquitto.log
  595  sudo  tail -f /var/log/mosquitto/mosquitto.log
  596  sudo systemctl restart mosquitto
  597  sudo systemctl status mosquitto
  598  sudo systemctl restart mosquitto
  599  sudo systemctl status mosquitto
  600  sudo cat /var/log/mosquitto/mosquitto.log
  601  sudo mkdir /etc/mosquitto/certs /etc/mosquitto/ca_certificates
  602  mosquitto_sub -h localhost -p 8883 --capath /home/azureuser/Skytrack_Backend/Skytronsystem/mqttKeys -t '#'
  603  ls /etc/mosquitto/certs/
  604  cd mqttKeys/
  605  sudo cp ca.crt /etc/mosquitto/ca_certificates/
  606  sudo cp server.crt /etc/mosquitto/certs/
  607  sudo cp server.key /etc/mosquitto/certs/
  608  sudo cp client.crt /etc/mosquitto/certs/ # Optional
  609  sudo cp client.key /etc/mosquitto/certs/
  610  sudo nano /etc/mosquitto/mosquitto.conf
  611  sudo nano /etc/mosquitto/conf.d/tls.conf
  612  sudo systemctl restart mosquitto
  613  sudo systemctl status mosquitto.service
  614  sudo  journalctl -xeu mosquitto.service
  615  sudo nano /etc/mosquitto/conf.d/tls.conf
  616  sudo systemctl restart mosquitto
  617  sudo systemctl status mosquitto.service
  618  mosquitto_sub -h localhost -p 8883 --capath /home/azureuser/Skytrack_Backend/Skytronsystem/mqttKeys -t '#'
  619  sudo cat /var/log/mosquitto/mosquitto.log
  620  sudo nano /etc/mosquitto/conf.d/tls.conf
  621  sudo systemctl restart mosquitto
  622  mosquitto_sub -h localhost -p 8883 --capath /home/azureuser/Skytrack_Backend/Skytronsystem/mqttKeys -t '#'
  623  sudo cat /var/log/mosquitto/mosquitto.log
  624  mosquitto_sub -h localhost -p 8883 --capath /home/azureuser/Skytrack_Backend/Skytronsystem/mqttKeys -t '#'
  625  sudo cat /var/log/mosquitto/mosquitto.log
  626  cd Skytronsystem/
  627  sudo docker ps
  628  sudo docker stop  skytron-backend-api-container
  629  sudo docker rm  skytron-backend-api-container
  630  sudo docker build -t skytron-backend-api . 
  631  ls
  632  sudo docker build -t skytron-backend-api -f dockerfile.api .
  633  sudo docker run -d  --restart=always -p 2000:2000  -f dockerfile.api -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  634  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  635  sudo docker stop  skytron-backend-api-container
  636  sudo docker rm  skytron-backend-api-container
  637  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  638  sudo docker stop  skytron-backend-api-container
  639  sudo docker rm  skytron-backend-api-container
  640  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  641  sudo docker stop  skytron-backend-api-container
  642  sudo docker rm  skytron-backend-api-container
  643  sudo docker build -t skytron-backend-api . 
  644  sudo docker build -t skytron-backend-api -f dockerfile.api .
  645  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  646  curl --location 'https://staging.parivahan.gov.in/vltdmakerws/dataportws?wsdl=null' --header 'Content-Type: text/xml; charset=utf-8' --data-raw '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.web.homologation.transport.nic/">
  647     <soapenv:Header/>
  648     <soapenv:Body>
  649        <ser:getVltdInfoByIMEI>          
  650           <userId>asbackendtest</userId>
  651           <transactionPass>Asbackend@123</transactionPass>       
  652           <imeiNo>861850060252547</imeiNo>
  653        </ser:getVltdInfoByIMEI>
  654     </soapenv:Body>
  655  </soapenv:Envelope>'
  656  cd Skytronsystem/
  657  ls
  658  sudo docker ps 
  659  sudo docker logs skytron-backend-api-container
  660  sudo dh
  661  sudo htop
  662  df -h
  663  sudo docker restart  skytron-backend-api-container
  664  sudo docker logs skytron-backend-api-container
  665  sudo docker stop  skytron-backend-api-container
  666  sudo docker start   skytron-backend-api-container
  667  sudo docker logs skytron-backend-api-container
  668  sudo docker stop skytron-backend-api-container
  669  sudo docker rm skytron-backend-api-container
  670  sudo docker build -t skytron-backend-api -f dockerfile.api .
  671  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container skytron-backend-api 
  672  sudo docker logs skytron-backend-api-container
  673  sudo docker stop skytron-backend-api-container
  674  sudo docker rm skytron-backend-api-container
  675  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g --workers 2 skytron-backend-api 
  676  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory 2g --workers 2 skytron-backend-api 
  677  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory 2g skytron-backend-api 
  678  sudo docker logs skytron-backend-api-container
  679  sudo docker stop skytron-backend-api-container
  680  sudo docker rm skytron-backend-api-container
  681  sudo docker build -t skytron-backend-api -f dockerfile.api .
  682  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory 2g skytron-backend-api 
  683  sudo docker logs skytron-backend-api-container
  684  sudo reboot
  685  htop
  686  ls
  687  htop
  688  sudo docker ps -a
  689  sudo docker start openproject
  690  sudo docker-compose build
  691  sudo docker-compose up -d
  692  suod cp /etc/nginx/sites-available/api.conf /etc/nginx/sites-available/dwarpal.conf
  693  sudo cp /etc/nginx/sites-available/api.conf /etc/nginx/sites-available/dwarpal.conf
  694  sudo chmod 777 -R /etc/nginx/sites-available/
  695  sudo ln -s /etc/nginx/sites-available/dwarpal.conf /etc/nginx/sites-enabled/
  696  sudo systemctl reload nginx
  697  sudo docker-compose build
  698  sudo docker-compose up -d
  699  sudo docker system prune 
  700  sudo docker-compose up -d
  701  sudo git config --global user.email "kishalaychakraborty1@gmail.com" 
  702  git config --global user.email "kishalaychakraborty1@gmail.com" 
  703  git config --global user.emnamekishalaychakraborty1@gmail.com" 
  704  git config --global user.name "kishalaychakraborty1@gmail.com"
  705  sudo  git config --global user.name "kishalaychakraborty1@gmail.com"
  706  sudo docker ps 
  707  sudo docker ps -a
  708  ls
  709  sudo docker-compose build
  710  sudo docker logs skytron-backend-api-container
  711  ls
  712  sudo ls /etc/nginx/sites-enabled/api.conf 
  713  sudo docker stop skytron-backend-api-container
  714  sudo docker rm skytron-backend-api-container
  715  sudo docker build -t skytron-backend-api -f dockerfile.api .
  716  cd Skytronsystem/
  717  sudo docker build -t skytron-backend-api -f dockerfile.api .
  718  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  719  sudo docker logs skytron-backend-api-container
  720  sudo docker build -t skytron-backend-api -f dockerfile.api .
  721  sudo docker stop skytron-backend-api-container
  722  sudo docker rm skytron-backend-api-container
  723  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  724  sudo docker logs skytron-backend-api-container
  725  sudo docker stop skytron-backend-api-container
  726  sudo docker rm skytron-backend-api-container
  727  sudo docker build -t skytron-backend-api -f dockerfile.api .
  728  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  729  sudo docker build -t skytron-backend-api -f dockerfile.api .
  730  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  731  sudo docker stop skytron-backend-api-container
  732  sudo docker rm skytron-backend-api-container
  733  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  734  sudo docker stop skytron-backend-api-container
  735  sudo docker rm skytron-backend-api-container
  736  sudo docker build -t skytron-backend-api -f dockerfile.api .
  737  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  738  sudo docker rm skytron-backend-api-container
  739  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  740  sudo docker build -t skytron-backend-api -f dockerfile.api .
  741  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  742  sudo docker rm skytron-backend-api-container
  743  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  744  sudo docker build -t skytron-backend-api -f dockerfile.api .
  745  sudo docker logs skytron-backend-api-container
  746  sudo docker build -t skytron-backend-api -f dockerfile.api .
  747  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  748  sudo docker rm skytron-backend-api-container
  749  sudo docker stop skytron-backend-api-container
  750  sudo docker rm skytron-backend-api-container
  751  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  752  sudo docker logs skytron-backend-api-container
  753  sudo docker-compose up -d
  754  sudo docker system prune
  755  sudo docker-compose up -d
  756  cd Skytronsystem/
  757  sudo docker build -t skytron-backend-api -f dockerfile.api .
  758  sudo docker stop skytron-backend-api-container
  759  sudo docker rm skytron-backend-api-container
  760  sudo docker run -d  --restart=always -p 2000:2000  -e  MAIL_ID=testskytrack@gmail.com  -e  MAIL_PW=zmzmexdnrlmsqrlr  --name skytron-backend-api-container  --memory=2g skytron-backend-api 
  761  sudo -i -u postgres
  762  sudo nano /etc/mosquitto/mosquitto.conf
  763  sudo systemctl restart mosquitto
  764  sudo rm /etc/mosquitto/ca_certificates/ca.crt
  765  sudo nano /etc/mosquitto/ca_certificates/ca.crt
  766  sudo nano /etc/mosquitto/certs/server.crt
  767  sudo rm /etc/mosquitto/certs/server.crt
  768  sudo nano /etc/mosquitto/certs/server.crt
  769  sudo rm /etc/mosquitto/certs/server.csr 
  770  sudo nano /etc/mosquitto/certs/server.csr 
  771  sudo rm /etc/mosquitto/certs/server.key
  772  sudo nano /etc/mosquitto/certs/server.key
  773  sudo rm /etc/mosquitto/certs/client.key
  774  sudo nano /etc/mosquitto/certs/client.key
  775  sudo rm /etc/mosquitto/certs/client.crt
  776  sudo nano /etc/mosquitto/certs/client.crt
  777  sudo systemctl restart mosquitto
  778  mosquitto_sub -h '216.10.244.243' -p 8883 -t '#' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  779  mosquitto_sub -h '216.10.244.243' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  780  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  781  ls 
  782  ls cd Skytronsystem/
  783  cd mqttKeys
  784  cd mqttKeys 
  785  cd /home/azureuser/Skytrack_Backend/Skytronsystem/mqttKeys
  786  ls
  787  sudo rm *.key
  788  sudo rm *.crt
  789  sudo rm *.csr
  790  ls
  791  sudo rm *.srl
  792  ls
  793  openssl genpkey -algorithm RSA -out ca.key
  794  openssl req -new -x509 -days 36500 -key ca.key -out ca.crt -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/"
  795  openssl genpkey -algorithm RSA -out server.key
  796  openssl req -new -key server.key -out server.csr -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/"
  797  openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 36500
  798  openssl genpkey -algorithm RSA -out client.key
  799  openssl req -new -key client.key -out client.csr -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/"
  800  openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 36500
  801  sudo cp ca.crt /etc/mosquitto/ca_certificates/
  802  sudo cp server.crt /etc/mosquitto/certs/
  803  sudo cp server.key /etc/mosquitto/certs/
  804  sudo cp client.crt /etc/mosquitto/certs/ # Optional
  805  sudo cp client.key /etc/mosquitto/certs/ # Optional
  806  sudo nano /etc/mosquitto/mosquitto.conf
  807  sudo cp server.crt /etc/mosquitto/certs/
  808  sudo cp server.key /etc/mosquitto/certs/
  809  sudo cp client.crt /etc/mosquitto/certs/ # Optional
  810  sudo cp client.key /etc/mosquitto/certs/ 
  811  sudo systemctl restart mosquitto
  812  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  813  openssl s_client -connect 4.240.90.1:8883 -CAfile /etc/mosquitto/ca_certificates/ca.crt -cert /etc/mosquitto/certs/client.crt -key /etc/mosquitto/certs/client.key
  814  sudo nano /etc/mosquitto/mosquitto.conf
  815  sudo systemctl restart mosquitto
  816  openssl s_client -connect 4.240.90.1:8883 -CAfile /etc/mosquitto/ca_certificates/ca.crt -cert /etc/mosquitto/certs/client.crt -key /etc/mosquitto/certs/client.key
  817  sudo cp ca.crt /etc/mosquitto/ca_certificates/
  818  sudo cp server.crt /etc/mosquitto/certs/
  819  sudo cp server.key /etc/mosquitto/certs/
  820  sudo cp client.crt /etc/mosquitto/certs/ # Optional
  821  sudo cp client.key /etc/mosquitto/certs/ # Optional
  822  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  823  openssl s_client -connect 4.240.90.1:8883 -CAfile /etc/mosquitto/ca_certificates/ca.crt -cert /etc/mosquitto/certs/client.crt -key /etc/mosquitto/certs/client.key
  824  cd "../mqttKeys copy"/
  825  sudo cp ca.crt /etc/mosquitto/ca_certificates/
  826  sudo cp server.crt /etc/mosquitto/certs/
  827  sudo cp server.key /etc/mosquitto/certs/
  828  sudo cp client.crt /etc/mosquitto/certs/ # Optional
  829  sudo cp client.key /etc/mosquitto/certs/ # Optional
  830  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  831  sudo systemctl restart mosquitto
  832  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  833  openssl s_client -connect 4.240.90.1:8883 -CAfile /etc/mosquitto/ca_certificates/ca.crt -cert /etc/mosquitto/certs/client.crt -key /etc/mosquitto/certs/client.key
  834  openssl s_client -connect 4.240.90.1:8883 -CAfile /etc/mosquitto/ca_certificates/ca.crt -cert /etc/mosquitto/certs/client.crt -key /etc/mosquitto/certs/client.key -verify 0
  835  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key -verify 0
  836  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  837  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key --insecure
  838  openssl req -new -x509 -days 36500 -key ca.key -out ca.crt -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/CN=4.240.90.1"
  839  openssl genpkey -algorithm RSA -out server.key
  840  openssl req -new -key server.key -out server.csr -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/CN=4.240.90.1"
  841  openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 36500
  842  openssl genpkey -algorithm RSA -out client.key
  843  openssl req -new -key client.key -out client.csr -subj "/C=IN/ST=Assam/L=Guwahati/O=Skytron/OU=OrgUnit/CN=4.240.90.1"
  844  openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 36500
  845  sudo cp ca.crt /etc/mosquitto/ca_certificates/
  846  sudo cp server.crt /etc/mosquitto/certs/
  847  sudo cp server.key /etc/mosquitto/certs/
  848  sudo cp client.crt /etc/mosquitto/certs/ # Optional
  849  sudo cp client.key /etc/mosquitto/certs/ # Optional
  850  sudo systemctl restart mosquitto
  851  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key --insecure
  852  mosquitto_sub -h '4.240.90.1' -p 8883 -t 'gps' --cafile /etc/mosquitto/ca_certificates/ca.crt --insecure
  853  openssl s_client -connect 4.240.90.1:8883 -CAfile /etc/mosquitto/certs/ca.crt
  854  openssl s_client -connect 4.240.90.1:8883 -CAfile /etc/mosquitto/ca_certificates/ca.crt
  855  mosquitto_sub -h 4.240.90.1 -p 8883 -t 'test/topic' --cafile /etc/mosquitto/ca_certificates/ca.crt
  856  openssl genpkey -algorithm RSA -out ca.key
  857  openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/C=US/ST=State/L=City/O=YourOrg/OU=OrgUnit/CN=YourCA"
  858  # Generate the server private key:
  859  openssl genpkey -algorithm RSA -out server.key
  860  # Generate a CSR for the server certificate (use your server's domain or IP as the CN):
  861  openssl req -new -key server.key -out server.csr -subj "/C=US/ST=State/L=City/O=YourOrg/OU=OrgUnit/CN=4.240.90.1"
  862  # Sign the server certificate with your CA:
  863  openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650
  864  sudo nano /etc/mosquitto/mosquitto.conf
  865  sudo cp ca.crt /etc/mosquitto/ca_certificates/
  866  sudo cp server.crt /etc/mosquitto/certs/
  867  sudo cp server.key /etc/mosquitto/certs/
  868  sudo nano /etc/mosquitto/mosquitto.conf
  869  sudo systemctl restart mosquitto
  870  mosquitto_sub -h 4.240.90.1 -p 8883 -t 'test/topic' --cafile /etc/mosquitto/ca_certificates/ca.crt
  871  mosquitto_sub -h 4.240.90.1 -p 8883 -t 'test/topic' --cafile /etc/mosquitto/ca_certificates/ca.crt --cert /etc/mosquitto/certs/client.crt --key /etc/mosquitto/certs/client.key
  872  ls
  873  mkdir video_stream
  874  cd video_stream/
  875  curl -X POST      -F "frame=@test.jpg"      https://4.240.90.1:445/upload/testDevice      -k   
  876  npx create-react-app streaming-dn-server
  877  npm install -g create-react-app
  878  sudo npm install -g create-react-app
  879  sudo npx create-react-app streaming-dn-server
  880  sudo npm install -g n
  881  sudo n stable
  882  sudo npx create-react-app streaming-dn-server
  883  cd streaming-dn-server/
  884  ls
  885  sudo chmod 777 -R ./
  886  npm start
  887  npm install
  888  npm instal
  889  node -v
  890  sudo npm instal
  891  sudo npm start
  892  mkdir streaming-up-server
  893  cd streaming-up-server
  894  npm init -y
  895  sudo apt install npm
  896  npm init -y
  897  ls ../../
  898  ls ../../Skytrack_Backend/Skytronsystem/
  899  node server.js
  900  npm install express multer
  901  node server.js
  902  openssl req -newkey rsa:2048 -nodes -keyout key.pem -x509 -days 365 -out cert.crt
  903  node server.js
  904  openssl req -newkey rsa:2048 -nodes -keyout /home/azureuser/video_stream/streaming-up-server/key.pem -x509 -days 365 -out /home/azureuser/video_stream/streaming-up-server/cert.crt
  905  node server.js
  906  sudo node server.js
  907  sudo ufw status
  908  sudo node server.js
  909  sudo docker ps 
  910  sudo node server.js
  911  node:events:496
  912  Error: listen EADDRINUSE: address already in use :::80
  913  Emitted 'error' event on Server instance at:
  914  }
  915  Node.js v22.14.0
  916  sudo node server.js
  917  node:events:496
  918  Error: listen EADDRINUSE: address already in use :::80
  919  Emitted 'error' event on Server instance at:
  920  }
  921  Node.js v2
  922  sudo lsof -i :80
  923  sudo grep -R "listen 80" /etc/nginx/
  924  sudo rm /etc/nginx/sites-enabled/default
  925  sudo systemctl reload nginx
  926  sudo lsof -i :80
  927  sudo node server.js
  928  ls
  929  cd streaming-up-server/
  930  ls
  931  sudo node server.js
  932  cd streaming-dn-server/
  933  sudo npm start
  934  sudo docker ps 
  935  sudo docker restart skytron-backend-mqtt-container
  936  history >hist.sh
