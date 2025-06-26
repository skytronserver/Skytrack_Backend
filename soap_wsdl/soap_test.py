import zeep

wsdl = "dataportws.wsdl"#'dataportws.xsd_12.xsd'#'soap_wsdl/dataportws2.wsdl'#
client = zeep.Client(wsdl=wsdl)
print(client )
 

response = client.service.getVltdInfo(
    userId='asbackendtest',
    transactionPass='Asbackend@123',
    deviceSerialNo='DS122'
)

# Print the response
print(response)