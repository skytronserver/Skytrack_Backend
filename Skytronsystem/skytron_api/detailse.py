DeviceModel:[ 
  "Model Name": "ModelXYZ",
  "testAgency": "ABC Company",
  "Vendor_ID":"ATMV"
  "tacNo": "ACF895",
  "tacValidity": "2026-02-03",
  "createdby":'2'  # Manufacturer id
  "created":"2024-02-03"  # date
  "status":"Manufacuturer_OTP_Sent/Manufacuturer_OTP_Verified/StateAdminOTPSend/StateAdminApproved" 
] #Once Stateadmin Approval done There will be no ferther change in the devicemodel
DeviceCOP:[
    "deviceModel":'1',
    "copNo": "RT567",
    "copValidity": "2026-03-03",
    "createdby":'2',  # Manufacturer id
    "created":"2024-02-03",  # date
    "valid":'1',
    "latest":'1',
    "status":"Manufacuturer_OTP_Sent/Manufacuturer_OTP_Verified/StateAdminOTPSend/StateAdminApproved/" 
]

DeviceStock:  [ 
  "model": '1',
  "deviceESN": "789XXXASD",
  "iccid": "123HH999",
  "imei": "123456789000",
  "telecomProvider1": "Telecom Provider Required",
  "telecomProvider2": "Telecom Provider Optional",
  "msisdn1": "MSISDN0007 required",
  "msisdn2": "MSISDN0008 optional",
  "imsi1": "IMSI77789 requried",
  "imsi2": "IMSI8889 optional",
  "eSimValidity": "2026-02-03",
  "eSimProvider": "TeleCom In.",
  "remarks": "Working Remarks",
  "created": "2024-02-03",
  "createdby": "31"
]
stockAssignment:[
    "device":'1',
    "dealer":'1',
    "assignedBy":'1',
    "assigned":"2024-02-03",
    "shipping_remark":"shippingdetais",
    "stock_status": "in_transit_to_deler[1]/available_for_fitting[2]/fitted[3]/esimActiveReqSent[4]/esimActiveConfirmed[5]/IP_PORT_Configured[6]/SOS_GATEWAY_NO_Configured[7]/SMS_GATEWAY_NO_Configured[8]/deviceDefictive[9]/returnedTomanufacturer[10]",
]
deviceTag:[
    "device":'1',
    "vehiclOwner":'1',  
    "vehicleRegNo":"AS-01-2222",
    "engine_no":"324324325",
    "chessis_no":"3423235325",
    "vehicleMake":"Tata",
    "vehicleModel":"Indica",
    "category":"",
    "rcFile":"",
    "status":"dealerOTPSent/dealerOTPVerified/ownerOTPSent/dealerOTPVerified/RegNoConfigurationSentTodevice/RegNoConfigurationConfirmed/liveLocationConfirmed/SOSConfirmed/deviceActive/deviceNotActive/device_Untaged",
    "tagedBy":"1",
    "taged":"2024-02-03",
]


ipList:[    
  "ip1":"0.0.0.0",
  "port1":"0000",
  "ip2":"0.0.0.0",
  "port2":"0000",
  "ipIm":"0.0.0.0",
  "portIm":"0000",
  "rule":"",
  'status':'valid',  
]
 

deviceHealth:[
  "Starting_Character":'$',
  "Packet_Header":'H',
  "Vendor_ID":'ATMV',
  "Firmware_Version":'1.0.4',
  "IMEI_Number":"896576543765432",
  "Battery_percentage":'65',
  "Low_battery_threshold":'10'
  "Memory_percentage":'41',
  "Iginition_Data_interval":"10",
  "NormalDataInterval":'60',
  "DigitalIOstatus":'1111',
  "Analog1IOstatus":'10.5',
  "Analog2IOstatus":"0.06",
  "Checksum":'G5'
]






 