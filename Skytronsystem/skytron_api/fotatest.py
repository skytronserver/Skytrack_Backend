"""import ftplib
import os
import time
import logging

# FTP Configurations
FTP_SERVER = '216.10.244.243'
FTP_PORT = 2121
FTP_USER = 'username1'
FTP_PASS = 'a12345678a'
FTP_REMOTE_PATH = '/V1.1.3.bin'  # Example file
LOCAL_FILE_PATH = '/local/path/to/V1.1.3.bin'  # Local storage path
BUFFER_SIZE = 1024 * 1024  # 1MB buffer size

# Global variables
ftp = None
download_state = "CLOSED"
ftp_file_size = 0
file_pos = 0

# Logging setup
logging.basicConfig(filename='/var/log/ftp_client.log', level=logging.INFO)

# Initialize FTP Connection
def ftp_login(server, port, user, password):
    global ftp
    try:
        ftp = ftplib.FTP()
        ftp.connect(server, port)
        ftp.login(user, password)
        logging.info(f"Logged into FTP Server {server}:{port}")
        return True
    except ftplib.all_errors as e:
        logging.error(f"FTP Login failed: {str(e)}")
        return False

# Retrieve File Size from the FTP server
def get_file_size(remote_path):
    global ftp_file_size
    try:
        ftp_file_size = ftp.size(remote_path)
        logging.info(f"File size of {remote_path}: {ftp_file_size} bytes")
        return ftp_file_size
    except ftplib.all_errors as e:
        logging.error(f"Failed to get file size: {str(e)}")
        return 0

# Download the file from FTP server
def download_file(remote_path, local_path):
    global file_pos, download_state
    try:
        # Open local file for writing
        with open(local_path, 'wb') as local_file:
            def write_data(data):
                local_file.write(data)
                logging.info(f"Downloaded {len(data)} bytes")

            logging.info(f"Starting file download: {remote_path}")
            ftp.retrbinary(f"RETR {remote_path}", write_data, BUFFER_SIZE)
            logging.info("FTP Download complete")
            download_state = "COMPLETED"
    except ftplib.all_errors as e:
        logging.error(f"FTP download failed: {str(e)}")
        download_state = "ERROR"

# Perform FOTA Update
def fota_update(file_path):
    try:
        if os.path.exists(file_path):
            logging.info(f"Performing FOTA update from {file_path}")
            # Simulate FOTA update process (replace with actual logic)
            logging.info(f"FOTA update complete")
            return True
        else:
            logging.error("FOTA update failed: File not found")
            return False
    except Exception as e:
        logging.error(f"FOTA update failed: {str(e)}")
        return False

# Logout from FTP Server
def ftp_logout():
    global ftp
    try:
        ftp.quit()
        logging.info("FTP Logout successful")
    except ftplib.all_errors as e:
        logging.error(f"FTP Logout failed: {str(e)}")

# Run the FTP download and FOTA process
def run_ftp_download_and_fota():
    global download_state, ftp_file_size

    # Initialize FTP session
    if not ftp_login(FTP_SERVER, FTP_PORT, FTP_USER, FTP_PASS):
        logging.error("FTP Login failed, aborting")
        return

    # Get file size
    ftp_file_size = get_file_size(FTP_REMOTE_PATH)
    if ftp_file_size == 0:
        logging.error("Cannot retrieve file size, aborting")
        ftp_logout()
        return

    # Download the file
    download_file(FTP_REMOTE_PATH, LOCAL_FILE_PATH)
    if download_state == "COMPLETED":
        logging.info(f"Downloaded file size: {os.path.getsize(LOCAL_FILE_PATH)} bytes")
        # Perform FOTA update
        if not fota_update(LOCAL_FILE_PATH):
            logging.error("FOTA Update failed, aborting")
    else:
        logging.error("File download was interrupted, aborting")

    # Logout from FTP session
    ftp_logout()

# Entry point for the FTP process
if __name__ == "__main__":
    run_ftp_download_and_fota()
"""
import ftplib
import os
import time
import logging

# FTP Configurations
FTP_SERVER = '216.10.244.243'
FTP_PORT = 2121
FTP_USER = 'username1'
FTP_PASS = 'a12345678a'
FTP_REMOTE_PATH = 'V1.1.4N.bin'  # Example file
LOCAL_FILE_PATH = './V1.1.4N.bin'  # Local storage path
BUFFER_SIZE = 1024 * 1024  # 1MB buffer size

# Global variables
ftp = None
download_state = "CLOSED"
ftp_file_size = 0
file_pos = 0

# Logging setup
logging.basicConfig(filename='/var/log/ftp_client.log', level=logging.INFO)

# Initialize FTP Connection
def ftp_login(server, port, user, password):
    global ftp
    try:
        ftp = ftplib.FTP()
        ftp.connect(server, port)
        ftp.login(user, password)
        logging.info(f"Logged into FTP Server {server}:{port}")
        return True
    except ftplib.all_errors as e:
        logging.error(f"FTP Login failed: {str(e)}")
        return False

# Retrieve File Size from the FTP server
def get_file_size(remote_path):
    global ftp_file_size
    try:
        # Set binary mode (TYPE I) to ensure SIZE command works
        #ftp.sendcmd('TYPE I')

        ftp_file_size = ftp.size(remote_path)
        logging.info(f"File size of {remote_path}: {ftp_file_size} bytes")
        return ftp_file_size
    except ftplib.all_errors as e:
        logging.error(f"Failed to get file size: {str(e)}")
        return 0

# Download the file from FTP server
def download_file(remote_path, local_path):
    global file_pos, download_state
    try:
        # Open local file for writing
        with open(local_path, 'wb') as local_file:
            def write_data(data):
                local_file.write(data)
                logging.info(f"Downloaded {len(data)} bytes")

            logging.info(f"Starting file download: {remote_path}")
            ftp.retrbinary(f"RETR {remote_path}", write_data, BUFFER_SIZE)
            logging.info("FTP Download complete")
            download_state = "COMPLETED"
    except ftplib.all_errors as e:
        logging.error(f"FTP download failed: {str(e)}")
        download_state = "ERROR"

# Perform FOTA Update
def fota_update(file_path):
    try:
        if os.path.exists(file_path):
            logging.info(f"Performing FOTA update from {file_path}")
            # Simulate FOTA update process (replace with actual logic)
            logging.info(f"FOTA update complete")
            return True
        else:
            logging.error("FOTA update failed: File not found")
            return False
    except Exception as e:
        logging.error(f"FOTA update failed: {str(e)}")
        return False

# Logout from FTP Server
def ftp_logout():
    global ftp
    try:
        ftp.quit()
        logging.info("FTP Logout successful")
    except ftplib.all_errors as e:
        logging.error(f"FTP Logout failed: {str(e)}")

# Run the FTP download and FOTA process
def run_ftp_download_and_fota():
    global download_state, ftp_file_size

    # Initialize FTP session
    if not ftp_login(FTP_SERVER, FTP_PORT, FTP_USER, FTP_PASS):
        logging.error("FTP Login failed, aborting")
        return

    # Get file size
    ftp_file_size = get_file_size(FTP_REMOTE_PATH)
    if ftp_file_size == 0:
        logging.error("Cannot retrieve file size, aborting")
        ftp_logout()
        return

    # Download the file
    download_file(FTP_REMOTE_PATH, LOCAL_FILE_PATH)
    if download_state == "COMPLETED":
        logging.info(f"Downloaded file size: {os.path.getsize(LOCAL_FILE_PATH)} bytes")
        # Perform FOTA update
        if not fota_update(LOCAL_FILE_PATH):
            logging.error("FOTA Update failed, aborting")
    else:
        logging.error("File download was interrupted, aborting")

    # Logout from FTP session
    ftp_logout()

# Entry point for the FTP process
if __name__ == "__main__":
    run_ftp_download_and_fota()
