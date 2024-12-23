# python3 -m pip install pyftpdlib
# sudo ufw allow 2121/tcp
# python3 -m pip install --upgrade cryptography pyOpenSSL
# curl -u username1:a12345678a ftp://216.10.244.243:2121/V1.1.3.bin -o V1.1.3.bin
#  tmux new -s gps_ftp  
# tmux attach -d -t gps_ftp
# python3 fota_ftp.py
#
"""

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



from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


def create_ftp_server(): 
    authorizer = DummyAuthorizer() 
    authorizer.add_user("username1", "a12345678a", "/var/www/html/skytron_backend/Skytronsystem/FOTAFiles/", perm="elr")
    handler = FTPHandler
    handler.authorizer = authorizer 
    handler.passive_ports = range(50000, 51000)   
    handler.masquerade_address = "216.10.244.243"   
    server = FTPServer(("0.0.0.0", 2121), handler) 
    server.serve_forever()

if __name__ == "__main__":
    create_ftp_server()
 

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import logging

def create_ftp_server(): 
    logging.basicConfig(filename='/var/log/ftp_server.log', level=logging.INFO) 
    authorizer = DummyAuthorizer()
    authorizer.add_user("username1", "a12345678a", "/var/www/html/skytron_backend/Skytronsystem/FOTAFiles/", perm="elr")
 
    handler = FTPHandler
    handler.authorizer = authorizer 
    handler.passive_ports = range(50000, 51000)   # Port range for passive mode
    handler.masquerade_address = "216.10.244.243"  # Public IP address of your server
 
    handler.timeout = 600 
    handler.log_prefix = "%(username)s@%(remote_ip)s"
 
    server = FTPServer(("0.0.0.0", 2121), handler)
 
    server.serve_forever()

if __name__ == "__main__":
    create_ftp_server()
"""
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import logging

class CustomFTPHandler(FTPHandler):
    def ftp_SIZE(self, file):
        """Override SIZE command to allow file size retrieval in both ASCII and binary modes."""
        try:
            # Get the file size using the server-side file system (ignores ASCII/Binary mode)
            size = self.run_as_current_user(self.fs.getsize, file)
            self.respond('213 %d' % size)
        except Exception as err:
            self.respond('550 SIZE command failed: %s.' % str(err))

def create_ftp_serverp(): 

    from pyftpdlib.log import config_logging
    config_logging(level='DEBUG')
    logging.basicConfig(filename='/var/log/ftp_server.log', level=logging.INFO)

    # Set up authorizer with a user
    authorizer = DummyAuthorizer()
    authorizer.add_user("username1", "a12345678a", "/var/www/html/skytron_backend/Skytronsystem/FOTAFiles/", perm="elr")
 
    # Use the custom handler to override FTP behavior
    handler = CustomFTPHandler
    handler.authorizer = authorizer 
    handler.passive_ports = range(50000, 50003)   # Port range for passive mode
    handler.masquerade_address = "216.10.244.243"  # Public IP address of your server

    handler.permit_foreign_addresses = True
 
    # Set timeout and log prefix
    handler.timeout = 600 
    handler.log_prefix = "%(username)s@%(remote_ip)s"
 
    # Create and start the FTP server
    server = FTPServer(("0.0.0.0", 2121), handler)
    server.serve_forever()
 

def create_ftp_server(): 
    import logging
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import FTPServer
    from pyftpdlib.log import config_logging
    config_logging(level='DEBUG')

    logging.basicConfig(filename='/var/log/ftp_server.log', level=logging.INFO)

    # Set up authorizer with a user
    authorizer = DummyAuthorizer()
    authorizer.add_user("username1", "a12345678a", "/var/www/html/skytron_backend/Skytronsystem/FOTAFiles/", perm="elr")
 
    # Use the default FTP handler
    handler = FTPHandler
    handler.authorizer = authorizer  
    handler.permit_foreign_addresses = True
    # Set timeout and log prefix
    handler.timeout = 600 
    handler.log_prefix = "%(username)s@%(remote_ip)s"
 
    # Create and start the FTP server
    server = FTPServer(("0.0.0.0", 2121), handler)
    server.serve_forever()

    
if __name__ == "__main__":
    create_ftp_serverp()
