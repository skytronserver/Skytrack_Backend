# python3 -m pip install pyftpdlib
# sudo ufw allow 2121/tcp
# python3 -m pip install --upgrade cryptography pyOpenSSL
# curl -u username1:a12345678a ftp://216.10.244.243:2121/V1.1.3.bin -o V1.1.3.bin
#  tmux new -s gps_ftp  
# tmux attach -d -t gps_ftp
# python3 fota_ftp.py
#
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


def create_ftp_server(): 
    authorizer = DummyAuthorizer() 
    authorizer.add_user("username1", "a12345678a", "/var/www/html/skytron_backend/Skytronsystem/FOTAFiles/", perm="elr")

    handler = FTPHandler
    handler.authorizer = authorizer 
    server = FTPServer(("0.0.0.0", 2121), handler) 
    server.serve_forever() 
if __name__ == "__main__":
    create_ftp_server()


