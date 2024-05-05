from zeep import Client

# Create a client for the SOAP service
wsdl_url = '/var/www/html/skytron_backend/Skytronsystem/dataportws.wsdl'  # Or URL if it's hosted remotely
from zeep import Client 
client = Client(wsdl=wsdl_url)

# Process the response
print( client.service.getVltdInfoByIMEI("1234"))