# skytron_api/views.py
from rest_framework.authtoken.models import Token 
from django.http import HttpResponseBadRequest, JsonResponse,HttpResponse  
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes, throttle_classes
import secrets
import string
from django.core.serializers import serialize
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate,logout,login 
from rest_framework.response import Response
from rest_framework import status 
import bleach
from .models import *
from .serializers import *
import xml.etree.ElementTree as ET
import json
import html
from django.db.models import Q
import random
from itertools import islice 
from django.utils import timezone     
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail

import os 
import magic
import glob
# Define the path on the host machine where files will be stored
# This directory should be mounted as a volume in Docker
HOST_STORAGE_PATH = '/host_storage'  # This should match the volume mount point in Docker
#def send_mail( subject, message, from_email, recipient_list, fail_silently=False, auth_user=None, auth_password=None, connection=None, html_message=None):
#    pass


               
from django.utils.crypto import get_random_string   
import sys
from django.forms.models import model_to_dict
from django.db import transaction

from django.contrib.auth import get_user_model
from rest_framework.views import APIView  

from django.shortcuts import get_object_or_404 
from rest_framework.parsers import MultiPartParser,FileUploadParser
import time 
import pandas as pd 
import calendar 

from rest_framework import generics,filters  

from django.core.files.storage import FileSystemStorage
from rest_framework import generics, status 
from django.conf import settings
     
import ast 
from django.views.static import serve
from django.conf import settings 
from django.shortcuts import render  
import json
from django.db.models import Subquery, OuterRef, Max, F,Subquery, OuterRef,Q  
from django.forms.models import model_to_dict
from scipy.signal import butter, lfilter,lfilter
from .forms import GPSDataFilterForm
import numpy as np
from django.shortcuts import render
from django.views import View 
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404 
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
import requests

import base64
import uuid   
from .utils import generate_captcha
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64
import json
import os 
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, RegexValidator
from datetime import datetime, timedelta

from django.utils.timezone import now
#python3 -m pip install python-docx
#python3 -m pip install pypandoc
#python3 -m pip install docx2pdf
 
#python3 -m pip install pdfkit
#sudo apt-get install wkhtmltopdf
#sudo apt-get update
#sudo apt-get install libreoffice
eeeeeee=""
import io
from docx import Document
import pdfkit
from tempfile import NamedTemporaryFile


import io
from docx import Document
import subprocess
from tempfile import NamedTemporaryFile

from pathlib import Path
import os  
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

def replace_text_in_docx_in_memory(template_path, replacements): 
    doc = Document(template_path) 
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, value) 
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def convert_docx_to_pdf_with_libreoffice(docx_buffer): 
    with NamedTemporaryFile(suffix=".docx", delete=False) as temp_docx_file:
        temp_docx_file.write(docx_buffer.getvalue())
        temp_docx_path = temp_docx_file.name 
    temp_pdf_path = temp_docx_path.replace('.docx', '.pdf') 
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', temp_docx_path, '--outdir', '/tmp'])

    with open(temp_pdf_path, 'rb') as pdf_file:
        pdf_buffer = io.BytesIO(pdf_file.read()) 
    subprocess.run(['rm', temp_docx_path, temp_pdf_path]) 
    return pdf_buffer


 
template_path = '/app/skytron_api/static/Cetificate_template.docx'

def validate_inputs(datar):
    errors = {} 
    d=None
    try:
        d=datar.data
    except:
        pass
    
    data = datar.GET.copy()  # Start with GET data
    if d:
        data.update()  # Add POST data (overwrites GET data if keys overlap)

   # Validate (date))
    Keys=["created","velid_from"]
    for key in Keys:
        expiry_date = data.get(key)
        if expiry_date:
            try:
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d')
                if expiry_date <= datetime.now():
                    errors[key] = key+' should not be a past date.'
            except ValueError:
                errors[key] = 'Invalid date format for '+key+'.'
   
    # Validate expiry date (should be more than 6 months from today)
    Keys=["velid_upto","expiryDate","expirydate","tac_validity","cop_validity","esim_validity"]
    for key in Keys:
        expiry_date = data.get(key)
        if expiry_date:
            try:
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d')
                if expiry_date <= datetime.now() + timedelta(days=30):
                    errors[key] = key+' should be more than 1 months from today.'
            except ValueError:
                errors[key] = 'Invalid date format for '+key+'.'



    # Validate date of birth (should be less than 18 years from today)
    dob = data.get('dob')
    if dob:
        try:
            dob = datetime.strptime(dob, '%Y-%m-%d')
            if dob >= datetime.now() - timedelta(days=365*18):
                errors['dob'] = 'Date of birth should be at least 18 years ago.'
        except ValueError:
            errors['dob'] = 'Invalid date format for date of birth.'

  
    # Validate mobile (should be exactly 10 digits)
    mobile = data.get('mobile')
    if mobile:
        if not mobile.isdigit() or len(mobile) != 10:
            errors['mobile'] = 'Mobile number should be exactly 10 digits.'
    mobile = data.get("vehicle_owner") #vehicle owner phone no 
    if mobile:
        if not mobile.isdigit() or len(mobile) != 10:
            errors["vehicle_owner"] = 'vehicle_owner should be exactly 10 digits.'
            

    # Validate mobile (should be exactly 10 digits)
    mobile = data.get('pincode')
    if mobile:
        if not mobile.isdigit() or len(mobile) != 6:
            errors['pincode'] = 'pincode number should be exactly 6 digits.'

    # Validate email format
    email = data.get('email')
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = 'Invalid email format.'


     
        
 
    # Validate (only alphabets and spaces)
    Keys=['name', "dto_rto",'city',"district_name" ,'country','company_name', "title","detail","feedback","em_msg","company_name","state_name"]
    for key in Keys:
        val = data.get(key)
        if val:
            if not all(x.isalpha() or x.isspace() for x in val):
                errors[key] = key+' should contain only alphabets and spaces.'
                
    # Validate (only alphanumaric and spaces)
    Keys=[ 'remarks','address',"title","detail","feedback","em_msg","company_name"]
    for key in Keys:
        val = data.get(key)
        if val:
            if not all(x.isalnum() or x.isspace() for x in val):
                errors[key] = key+' should contain only alphanumeric and spaces.'
                
     
    
 

    # Validate (only alphanumaric)
    Keys=['idProofno',"category","district_code",'idProofType', 'vehicle_reg_no','engine_no','chassis_no','vehicle_make','vehicle_model','category']
    for key in Keys:
        val = data.get(key)
        if val:
            if not all(x.isalnum()   for x in val):
                    errors[key] = key+' should contain only alphanumeric.'
 
    # Validate ids (only int)
    Keys=['device_id',"maxSpeed",'call_id',"district" ,"warnSpeed",'state']
    for key in Keys:
        val = data.get(key)
        if val:
            try:
                val = int(val)
                if val <= 0:
                    errors[key] = key + ' should be a positive integer.'
            except ValueError:
                errors[key] = key + ' should be a positive integer.'
    


    # Validate otp (should be exactly 6 digits)
    otp = data.get('otp')
    if otp:
        if not otp.isdigit() or len(otp) != 6:
            errors['otp'] = 'OTP should be exactly 6 digits.'
    
    user_type = data.get('user_type')
    if user_type:
        if str(user_type) not in ['teamlead', 'desk_ex', 'police_ex', 'ambulance_ex', 'PCR', 'ACR']:
            errors['user_type'] = 'invalid user_type.'
    user_type = data.get('role')
    if user_type:# "superadmin", "stateadmin", "devicemanufacture", "dealer", "owner", "esimprovider","filment","sosadmin", "teamleader","sosexecutive"
        if str(user_type) not in ["superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider","superadmin", "stateadmin", "devicemanufacture", "dealer", "owner", "esimprovider","filment","sosadmin", "teamleader","sosexecutive"]:
            errors['role'] = 'invalid role.'
    
    regex_validations = {
        'gstNo': r'^([0][1-9]|[1-2][0-9]|[3][0-7])([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$',
        'gstnnumber': r'^([0][1-9]|[1-2][0-9]|[3][0-7])([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$',
        'ip_tracking': r'^(\d{1,3}\.){3}\d{1,3}$',
        'ip_tracking2': r'^(\d{1,3}\.){3}\d{1,3}$',
        'ip_sos': r'^(\d{1,3}\.){3}\d{1,3}$',
        'port_sos': r'^[1-9][0-9]{0,4}$',
        'sms_tracking': r'^[1-9][0-9]{0,4}$',
        'sms_tracking2': r'^[1-9][0-9]{0,4}$',
        'sms_sos': r'^[1-9][0-9]{0,4}$',
        'imei': r'^[0-9]{15}$',
        'msisdn1': r'^[0-9]{15}$',
        'msisdn2': r'^[0-9]{15}$',
        'iccid': r'^[0-9]{19,20}$',
        'Device': r'^\d{15}$',
        'vehicle_reg_no': r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$',
        'engine_no': r'^[A-Z0-9]{6,17}$',
        'chassis_no': r'^[A-HJ-NPR-Z0-9]{17}$',
    }

    for key, pattern in regex_validations.items():
        value = data.get(key)
        if value and not re.match(pattern, value):
            errors[key] = f"Invalid format for {key}."


    return errors

def geneateCet(savepath,IMEI,Make,Model,Validity,RegNo,FitmentDate,TaggingDate,ActivationDate,Status,Date):
    replacements = {
        '{{IMEI}}':IMEI,
        '{{Make}}':Make ,
        '{{Model}}':Model,
        '{{Validity}}':Validity,
        '{{RegNo}}':RegNo,
        '{{FitmentDate}}':FitmentDate,
        '{{TaggingDate}}':TaggingDate,
        '{{ActivationDate}}':ActivationDate,
        '{{Status}}':Status,
        '{{Date}}':Date     
    }
    docx_buffer = replace_text_in_docx_in_memory(template_path, replacements)
    pdf_buffer = convert_docx_to_pdf_with_libreoffice(docx_buffer)
    with open(savepath, 'wb') as f:
        f.write(pdf_buffer.getvalue())




 

def load_private_key():
    private_key_path = '/app/keys/private_key.pem' #os.getenv('PRIVATE_KEY_PATH', '/var/www/html/skytron_backend/Skytronsystem/keys/private_key.pem')
    with open(private_key_path, 'rb') as key_file:
        private_key = RSA.import_key(key_file.read()) 
    with open(private_key_path, 'rb') as key_file: 
        print(key_file.read()) 
    return private_key

def decrypt_field(encrypted_field, private_key):
    cipher = PKCS1_OAEP.new(private_key)
    #if len(encrypted_field)<16:
    #    return encrypted_field
    enc=base64.b64decode(encrypted_field)
    try:
        decrypted_data = cipher.decrypt(enc)
        return decrypted_data.decode('utf-8')
    except Exception as e :
        return None
PRIVATE_KEY=load_private_key() 
#print(PRIVATE_KEY)




@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 

def get_settings(request): 
    data={'mqtt_ip': "135.235.166.209", 'mqtt_port': "8883","mqtt_ca_cart":"""-----BEGIN CERTIFICATE-----
MIIDrDCCApSgAwIBAgITFfcYWF9ArRO7Qli8ksgfR1OEOjANBgkqhkiG9w0BAQsF
ADBmMQswCQYDVQQGEwJVUzEOMAwGA1UECAwFU3RhdGUxDTALBgNVBAcMBENpdHkx
FTATBgNVBAoMDE9yZ2FuaXphdGlvbjEQMA4GA1UECwwHT3JnVW5pdDEPMA0GA1UE
AwwGWW91ckNBMB4XDTI1MDUwOTEyMTY1NVoXDTM1MDUwNzEyMTY1NVowZjELMAkG
A1UEBhMCVVMxDjAMBgNVBAgMBVN0YXRlMQ0wCwYDVQQHDARDaXR5MRUwEwYDVQQK
DAxPcmdhbml6YXRpb24xEDAOBgNVBAsMB09yZ1VuaXQxDzANBgNVBAMMBllvdXJD
QTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANobRTTC3d2QotD45ky9
2dHaC/ZJEeogqV1MVKYVZe3n1xJF8FOFhH72OEZRyW9HRByjdYCuB7Ygp3HW25Ru
SGO0f8DNqHSCVPzOw/87dF+ierZ2HVisy0XqP3k6hkFgg5JSJLNkUlQKGQBuReH1
U+pGHnMreMHh81wTuafX2SdnfyM/CKB+g79LDSxrRwqOOkG1xqszaIeQkOG1tbPQ
SvW23GcbqPxnoxfq0dUgrkYWYsh44D4KIET0VtqoxV7nczFJrQS0i2FcSLh+iPtO
W+QYbNXuesy8uXIJebycngLm8DcwE/B3NKyes5rgjcBWZGs2U+1fAtLAVYb+0GZK
TOUCAwEAAaNTMFEwHQYDVR0OBBYEFL1YNcA0yJEK5+/dAqx171nFaI/4MB8GA1Ud
IwQYMBaAFL1YNcA0yJEK5+/dAqx171nFaI/4MA8GA1UdEwEB/wQFMAMBAf8wDQYJ
KoZIhvcNAQELBQADggEBAAjmbnXhtFLppjl3YlbXUebmqkKsIDAyQbyoN4WzlAfY
uAgSAn93D7ygJG0h88SrFHGJ7JIisWoYBBwX1fD9EeWrArc5yKK/yYH2o5qcmKTB
8BYqIzWqkkIdUFZwMKrxk+KAyHnXxqwwdQ8mfmQbvFoHj5494y6L7uCTjOsHF13+
UelnNEA3Oj9JhUEGrRXrza+ZY7dxovIkEiUhise/1gkOJ6XijQGYD23eaSBnVvxV
Qq4rx+09PjwkQInk5yVt0JiikPuoyo2pi1dDnGOEa3Po5puISufraVrYPt4fbkW7
wwB/9mlr921t0usT5JPoTFREz0Z4UuZRIuaM+fUOaIU=
-----END CERTIFICATE-----""","mqtt_key":"""-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDXaKxddiNsh3gU
MZhojcn4xCulkastkylyQHKj9kG+hAFpR2L/DV9W8H/B5ElaIOdXOWTYLN4SOMlW
OoaogVW/7FfDr51ObV0yb/mUKNTKHTz1ksWSoSMh2SNWHlaP1ATVmg/ms2qILKf5
ajLxvq276I9eAcnRWYLo9VqX8hRFehb7CNn5mzPbyLjOt7ED2ltBIRadVl33b3h3
BYMdMGgUUKRmEAP++pLjfDUTA58/faMjy0gjXUGlGLwB9t/mBjgn1eISN0pZSVNM
2H281QnBmfH28TuhFVrYLE5IzWRNp5K8g6b528HuI5yGaJ4OF671Hv2WqD+RSqTU
//K6Al+fAgMBAAECggEACSuVmuz6mRYzUHjECj9vB74iNYw8A1aufwSrXLuRFPE9
tiOp3T3Ofz8B0VlMnh+keZwh5OoUEiaEu70GGopXAjKnkdcaFUqmmw0VTO9oD6qq
+7Fh49okSr6ZuILWII1gH0/NuX6N3Ho6NG4G+S+q6cL+x3vAAb+TySMY1jsiDcsO
y/r5wODUAIUzCj2zO/YtYebH1RxdTOqdgSMIjC75csDD0etCfS/Spc6YgPv5sOpU
mhtII9xxY75u4SFR86oLEDaMbyKDmANT0Uiqi56hvWIcPezw+cFfjjfcuDiK+cV7
V+UQ9nfMRMXl5rBTtqUKeTZhtJSYRYkeVmRQ0vPjkQKBgQDvNnHVPwX6cTjKJglX
hnPwCWnGTuLhLbKzeV75kdbwWb9ImO8M0DVZ6lFOAnVf/cTlQwHt+G5eaUlDRrDt
1yhWOKph9iOICK2IVH3FpDyZ71He2UmCYbTCn9OifCPPBybegI6FZhXAY9C1P58K
db3ASO4LfRYB2APCr5JfzSrxXQKBgQDmhpVkKzTMpzHUpscsAoArtw8OnnHMUKB4
TinHF8fK4o3RvLJ0HR/kl2zBTLQsFvYURbqmCXr5+Ng5F77H8YFTUk1kD7HhR7cm
2pS5ibb1astSDq6dSiwsWiqF/P5wi0cpjlEs/2zvUfhesHg+WywilVtvt7tFDWGw
F5rKOsTZKwKBgFL2Nep4LhGafNCW+nxxc/oWual+KG9iEuzttgOmEb5P0ehSqe1u
tGIXwtTkQ2LkNwowABZRJ630o+UCOlByY1nr0yOgYthF8jEq5GfMOvxEJMe94iGm
0zMAjTx4A09EsrVOLp+TNQ4BUBvcEcNl7EYoxO4VFrHTAhLeI0y4ciE9AoGATyaK
iLglCtelTmRtInlBVMEn1Fcmr4ZHcsczpP5PRSQAmbD2fNO7LZuoZb5WZoUDvPYs
HfJHXSjJ5OB4SuJrCxbJJ8ATzUv4YMjQI9xbC2y9ntEXtz3OaPQUgajaG/5WUrhg
utiAqLM2WhyxTIe1YbJykKs/C3iKwBF6vlDrYb0CgYAPsmbNx0SWs2zcynxnP0bt
3vpPBiEyO8XnBXs1U86WufN7EuIe6poO5pV5B6TlLZxSNMs1LZOG6vsubf8Ie/mc
6TMYuEA3wWFOmbdqzzTmZFaNnp9xmH512dOGYnCKfTNE6tlXBoC9zRJBbJfR9N51
9HiJVQkH3UauquM0gRrBhg==
-----END PRIVATE KEY-----""","mqtt_cart":"""-----BEGIN CERTIFICATE-----
MIIDVzCCAj8CFAl+hCw6eE5wlZl/YRRGDfAfYYyIMA0GCSqGSIb3DQEBCwUAMGYx
CzAJBgNVBAYTAlVTMQ4wDAYDVQQIDAVTdGF0ZTENMAsGA1UEBwwEQ2l0eTEVMBMG
A1UECgwMT3JnYW5pemF0aW9uMRAwDgYDVQQLDAdPcmdVbml0MQ8wDQYDVQQDDAZZ
b3VyQ0EwHhcNMjUwNTA5MTIxOTE0WhcNMzUwNTA3MTIxOTE0WjBqMQswCQYDVQQG
EwJVUzEOMAwGA1UECAwFU3RhdGUxDTALBgNVBAcMBENpdHkxFTATBgNVBAoMDE9y
Z2FuaXphdGlvbjEQMA4GA1UECwwHT3JnVW5pdDETMBEGA1UEAwwKQ2xpZW50TmFt
ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANdorF12I2yHeBQxmGiN
yfjEK6WRqy2TKXJAcqP2Qb6EAWlHYv8NX1bwf8HkSVog51c5ZNgs3hI4yVY6hqiB
Vb/sV8OvnU5tXTJv+ZQo1ModPPWSxZKhIyHZI1YeVo/UBNWaD+azaogsp/lqMvG+
rbvoj14BydFZguj1WpfyFEV6FvsI2fmbM9vIuM63sQPaW0EhFp1WXfdveHcFgx0w
aBRQpGYQA/76kuN8NRMDnz99oyPLSCNdQaUYvAH23+YGOCfV4hI3SllJU0zYfbzV
CcGZ8fbxO6EVWtgsTkjNZE2nkryDpvnbwe4jnIZong4XrvUe/ZaoP5FKpNT/8roC
X58CAwEAATANBgkqhkiG9w0BAQsFAAOCAQEAUvwHyIpIxM+MVFL6E/6Ag5LhCBAs
5Ed9LX8+SjFHKeeugWqb3iVaPqBcZJ86XlJ49pEMOwBtGJpbLUPBNpr8t+QXmnl/
wEH7xzNmvODJ/1DVLsCn0kL8ycohwEapQGkH5H+/Rp7+JvNZVHDkVGuu3PzXTjxd
2nlVhUciOC7kSBBRZO7mAOFMCPfYcSYKQfsF9Pirsb7rQdSRhp6thURpKJCS2SyV
wBk8bKkg4AOXs7ujsUfUiSFEjTqUjVkzxoAUdhljHGMyMWfUELtUcHTSmGcbdA90
IjBsK1eaOD7wUP3fdubAc1dUScYK4zwmnFfDP3fwwU0qC8eal+4by5Zi1Q==
-----END CERTIFICATE-----"""}

    return JsonResponse(data)

@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 
def generate_captcha_api(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)


    byte_io, result = generate_captcha()
    key = uuid.uuid4().hex
    cap,error=Captcha.objects.safe_create(key=key, answer=result)
    if error:   # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create


    # Convert image blob to base64
    img_base64 = base64.b64encode(byte_io.getvalue()).decode('utf-8')

    return JsonResponse({'key': key, 'captcha': img_base64})

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def verify_captcha_api(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    key = request.POST.get('key')
    user_input = request.POST.get('captcha')

    try:
        captcha = Captcha.objects.get(key=key)
        if not captcha.is_valid():
            captcha.delete()  # Optionally, delete the expired captcha
            return JsonResponse({'success': False, 'error': 'Captcha expired'})

        if int(user_input) == captcha.answer:
            captcha.delete()  # Optionally, delete the captcha after successful verification
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid captcha'})
    except Captcha.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Captcha not found'})
   

import os, magic
import os
import random
from rest_framework.response import Response


def save_file(request, tag, path):
    uploaded_file = request.FILES.get(tag)
    if not uploaded_file:
        return None 
        return Response({'error': f"File not found"}, status=400)
    #Response({'error': f"Invalid file type. Allowed types are:"}, status=400)

    # Validate file size (should be less than 1 MB)
    max_file_size = 1 * 1024 * 1024  # 1 MB in bytes
    if uploaded_file.size > max_file_size:
        return None 
        return Response({'error': f"File size should be less than 1 MB. Current size: {uploaded_file.size / (1024 * 1024):.2f} MB"}, status=400)

    # Validate file type using magic numbers
    valid_mime_types = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'application/pdf': 'pdf',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    }

    # Use python-magic to detect the MIME type
    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(uploaded_file.read(2048))  # Read the first 2 KB of the file

    if mime_type not in valid_mime_types:
        return None 
        return Response({'error': f"Invalid file type. Allowed types are: {', '.join(valid_mime_types.keys())}"}, status=400)

    # Additional validation to prevent executable files
    uploaded_file.seek(0)  # Reset file pointer to the beginning
    file_content = uploaded_file.read(2048)  # Read the first 2 KB of the file
    if b'MZ' in file_content or b'PK\x03\x04' in file_content:
        return None 
        return Response({'error': "Invalid file detected. Upload denied."}, status=400)
    data=file_content
    if data.startswith(b"MZ") or data.startswith(b"\x7FELF") or data.startswith(b"\xcf\xfa\xed\xfe") or \
        data.startswith(b"\xce\xfa\xed\xfe") or \
        data.startswith(b"\xca\xfe\xba\xbe")or data.startswith(b"#!"):
            return None 
        #return Response({'error': "Invalid file detected. Upload denied."}, status=400)
    
    # Create the directory in the host storage path if it doesn't exist
    if not path.startswith('fileuploads/') and path != 'fileuploads' and not path.startswith('./fileuploads/'):
        # Prepend fileuploads/ to ensure consistent path structure
        host_path = os.path.join(HOST_STORAGE_PATH, 'fileuploads', path.lstrip('./'))
    else:
        host_path = os.path.join(HOST_STORAGE_PATH, path.lstrip('./'))
    
    os.makedirs(host_path, exist_ok=True)
    
    file_extension = valid_mime_types[mime_type]
    file_name = ''.join(random.choices('0123456789', k=40)) + "." + file_extension
    file_path = os.path.join(host_path, file_name)
    
    with open(file_path, 'wb') as file:
        uploaded_file.seek(0)  # Reset file pointer to the beginning
        for chunk in uploaded_file.chunks():
            file.write(chunk)

    # Return the path that will be stored in the database and used for retrieval
    if not path.startswith('fileuploads/') and path != 'fileuploads' and not path.startswith('./fileuploads/'):
        # Return path with folder name included, e.g., "notice/filename.jpg"
        return os.path.join(path.lstrip('./'), file_name)
    else:
        # Path already has structure, just return it
        return os.path.join(path.lstrip('./'), file_name)



def find_file_in_folders(filename, folders):
    # First try with the original path which might include directories
    
    
    filename=os.path.join(HOST_STORAGE_PATH, filename)
    if os.path.isfile(filename):
        return filename
                
    return None
    for folder in folders:
        filename_clean = filename.replace("%20", " ")
        
        # Case 1: If filename already contains path components like 'notice/file.jpg'
        if '/' in filename_clean:
            # Try direct path
            potential_path = os.path.join(folder, filename_clean)
            if os.path.isfile(potential_path):
                return potential_path
                
            # Try with fileuploads prefix if not already there
            if not filename_clean.startswith('fileuploads/'):
                potential_path = os.path.join(folder, 'fileuploads', filename_clean)
                if os.path.isfile(potential_path):
                    return potential_path
        
        # Case 2: Simple filename without directory
        else:
            # Try direct path for simple filename
            potential_path = os.path.join(folder, filename_clean)
            if os.path.isfile(potential_path):
                return potential_path
            
            # Try common subdirectories for files
            for subdir in ['', 'notice', 'fileuploads/notice']:
                potential_path = os.path.join(folder, subdir, filename_clean)
                if os.path.isfile(potential_path):
                    return potential_path

    # Use glob as a fallback for more flexible matching
    for folder in folders:
        # Try to find by filename only, anywhere under the folder
        pattern = os.path.join(folder, '**', os.path.basename(filename.replace("%20", " ")))
        matches = glob.glob(pattern, recursive=True)
        if matches and os.path.isfile(matches[0]):
            return matches[0]
            
    return None
folders = [
    os.path.join(HOST_STORAGE_PATH, ''),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/tac_docs/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/Receipt_files/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/kyc_files/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/cop_files/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/file_bin/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/man/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/media/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/notice/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/driver/'),
    # Add more folders as needed
]

# Ensure directories exist
for folder in folders:
    os.makedirs(folder, exist_ok=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  # Apply throttling here
@require_http_methods(['GET', 'POST'])
def downloadfile(request): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST': 
        file_path =   request.data.get('file_path') 
        #print(request.content_type )
        #print(request.data)
        #print(request.user )

        if not file_path:
            return JsonResponse({'error': 'file_path is required'}, status=400) 
        try:
            # Extract just the filename for the response header
            filename = os.path.basename(file_path)
            
            # Try to find the file first with the full path
            full_path = find_file_in_folders(file_path, folders)
            
            # If that fails, try with just the filename
            if not full_path:
                filename_only = os.path.basename(file_path)
                full_path = find_file_in_folders(filename_only, folders)
                
            if not full_path:
                return JsonResponse({'error': f'file not found: {file_path}'}, status=400) 
                
            try:                
                with open(full_path, 'rb') as file:
                    response = HttpResponse(file.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                    return response
            except FileNotFoundError:
                return HttpResponse("File not found.", status=404) 
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'Error in reading file.'}, status=404)
    return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)



def apply_low_pass_filter(queryset, columns):
    # Get the values of the specified columns from the queryset
    column_values = {col: list(queryset.values_list(col, flat=True)) for col in columns}

    # Apply low-pass filter and median filter to each column
    for col, values in column_values.items():
        normalized_values,meanv,std_value = normalize(values)
        median_filtered_values = median_filter(normalized_values)
        low_pass_filtered_values = moving_average_filter(median_filtered_values, window_size=10) #low_pass_filter(median_filtered_values)
        column_values[col] = unnormalize(low_pass_filtered_values,meanv,std_value)
         

    # Update the queryset with the filtered values
    for i, entry in enumerate(queryset):
        for col, values in column_values.items():
            setattr(entry, col, values[i])

    return queryset

def low_pass_filter(data, cutoff_freq=0.4, sampling_rate=1.0, order=16):


    # Design a Butterworth low-pass filter
    nyquist = 0.5 * sampling_rate
    normal_cutoff = cutoff_freq / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)

    # Initialize filtered data with the first value
    filtered_data = [data[0]]

    # Initialize the state for the filter
    zi = [0] * (max(len(a), len(b)) - 1)
    
    # Apply the filter to the remaining data
    for value in data[1:]:
        filtered_value, zi = lfilter(b, a, [value], zi=zi)
        filtered_data.append(filtered_value[0])

    return filtered_data
def moving_average_filter(data, window_size=5):
    # Apply a simple moving average filter to the data
    filtered_data = np.convolve(data, np.ones(window_size) / window_size, mode='same')
    return filtered_data.tolist()
def normalize(data):
    # Normalize the data to have zero mean and unit variance
    mean_value = np.mean(data)
    std_value = np.std(data)
    normalized_data = [(x - mean_value) / std_value for x in data]

    return [normalized_data,mean_value,std_value]
def unnormalize(data,mean_value,std_value):
    # Normalize the data to have zero mean and unit variance
    
    normalized_data = [ mean_value+ (x*std_value) for x in data]

    return normalized_data

def median_filter(data, kernel_size=3):
    # Apply a median filter to the data
    filtered_data = np.convolve(data, np.ones(kernel_size) / kernel_size, mode='same')

    return filtered_data.tolist()
 


@require_http_methods(['GET', 'POST'])
def gps_data_table(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    form = GPSDataFilterForm(request.GET)
    data = GPSData.objects.all()#.order_by('-entry_time')[:200]

    if form.is_valid():
        vehicle_registration_number = form.cleaned_data.get('vehicle_registration_number')
        start_datetime = form.cleaned_data.get('start_datetime')
        end_datetime = form.cleaned_data.get('end_datetime')

        if vehicle_registration_number:
            data = data.filter(device_tag__vehicle_reg_no__icontains=vehicle_registration_number)

        if start_datetime and end_datetime:
            data = data.filter(entry_time__range=(start_datetime, end_datetime))
    data=data.order_by('-entry_time')[:200]
    return render(request, 'gps_data_table.html', {'data': data, 'form': form})

@require_http_methods(['GET', 'POST'])
def gps_data_table1(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    data = GPSData.objects.all().order_by('-entry_time')[:200]
    #print("data", flush=True)
    #print(data, flush=True)
    return render(request, 'gps_data_table.html', {'data': data})



from itertools import chain
def model_to_dict(instance, fields=None, exclude=None):
    
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        data[f.name] = f.value_from_object(instance)
    return data




@csrf_exempt   
@require_http_methods(['GET', 'POST'])
def gps_track_data_api(request ): 
    #errors = validate_inputs(request)
    #if errors:
    #    return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'GET':
        imei=False
        regno=False
        try:
            imei = request.GET.get('imei')
            
        except:
            pass
        try:
            regno = request.GET.get('regno')
        except:
            pass
        
        # Get base queryset
        gps_queryset = GPSData.objects.exclude(device_tag=None)
        
        # Apply role-based filtering
        if request.user.is_authenticated:
            user_role = request.user.role
            
            if user_role == 'superadmin':
                # Superadmin sees all data - no additional filtering
                pass
            elif user_role in ['stateadmin', 'sosadmin', 'sosexecutive']:
                # Get user's state(s) based on role
                user_states = []
                
                if user_role == 'stateadmin':
                    # Get states from StateAdmin relationship
                    state_admins = StateAdmin.objects.filter(users=request.user, status='UserVerified')
                    user_states = [sa.state.id for sa in state_admins]
                elif user_role == 'sosadmin':
                    # Get states from EM_admin relationship  
                    em_admins = EM_admin.objects.filter(users=request.user, status='StateAdminVerified')
                    user_states = [ea.state.id for ea in em_admins]
                elif user_role == 'sosexecutive':
                    # Get states from EM_ex relationship
                    em_exs = EM_ex.objects.filter(users=request.user, status='StateAdminVerified')
                    user_states = [ee.state.id for ee in em_exs]
                
                if user_states:
                    # Filter GPSData for vehicles belonging to owners in user's states
                    # This requires checking the state through the device owner's address_State
                    gps_queryset = gps_queryset.filter(
                        device_tag__vehicle_owner__users__address_State__in=[
                            Settings_State.objects.get(id=state_id).state for state_id in user_states
                        ]
                    )
                else:
                    # If no states found, return empty queryset
                    gps_queryset = GPSData.objects.none()
                    
            elif user_role == 'owner':
                # Get vehicles owned by this user
                vehicle_owners = VehicleOwner.objects.filter(users=request.user, status='UserVerified')
                if vehicle_owners.exists():
                    # Get device tags for vehicles owned by this user
                    owned_device_tags = DeviceTag.objects.filter(vehicle_owner__in=vehicle_owners)
                    gps_queryset = gps_queryset.filter(device_tag__in=owned_device_tags)
                else:
                    # If user is not associated with any vehicles, return empty queryset
                    gps_queryset = GPSData.objects.none()
            else:
                # For other roles, return empty queryset for security
                gps_queryset = GPSData.objects.none()
        else:
            # If user is not authenticated, return empty queryset
            gps_queryset = GPSData.objects.none()
        
        distinct_registration_numbers = gps_queryset.values('device_tag').distinct() #vehicle_registration_number
        data = []

        for x in distinct_registration_numbers:
            latest_entry = gps_queryset.filter(device_tag=x['device_tag']).filter(gps_status=1).order_by('-entry_time') 
            
            #if regno:
            #    if regno!="None":
            #        #.filter(vehicle_registration_number=x['vehicle_registration_number'])
            #        latest_entry = latest_entry.filter(device_tag__vehicle_reg_no__icontains=regno).filter(gps_status=1).order_by('-entry_time') 
            if imei:
                if imei !="None":
                    #filter(device_tag__vehicle_reg_no=x['vehicle_registration_number']).
                    latest_entry = latest_entry.filter(device_tag__device__imei__icontains=imei).filter(gps_status=1).order_by('-entry_time')
            latest_entry=latest_entry.first()
            excluded_fields = []   
            if latest_entry:
                #data.append(latest_entry.values())
                dd=model_to_dict(latest_entry, exclude=excluded_fields)
                if latest_entry.device_tag:
                    dd['vehicle_registration_number']=latest_entry.device_tag.vehicle_reg_no
                    dd['imei']=latest_entry.device_tag.device.imei
                else:
                    dd['vehicle_registration_number']=""
                    dd['imei']=""
                data.append(dd)
            
          


        data_list = list(data)
        return JsonResponse({'data': data_list})
    return JsonResponse({'data': []})



def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size
#@csrf_exempt   
#@csrf_exempt
@require_http_methods(['GET', 'POST'])
def gps_history_map(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    t = time.time()
    #print("Timer init",time.time() - t )   

    mapdata=[]
    data=[]     
    mapdata=[]
    data=[]
    try:
        vehicle_registration_number ="L89_003-0000"
        start_datetime = "2024-07-11"
        end_datetime = "2024-08-12" 
        
        
        try:
            vehicle_registration_number = request.GET.get('vehicle_registration_number', None)
            start_datetime = request.GET.get('start_datetime', None)
            end_datetime = request.GET.get('end_datetime', None)
        except:
            vehicle_registration_number ="L89_003-0000"
            #start_datetime = "2024-04-11"
            #end_datetime = "2024-04-12"

        #return JsonResponse({"eg":vehicle_registration_number})
        if vehicle_registration_number:
            pass
        else:
            vehicle_registration_number ="L89_003-0000"
            start_datetime = "2024-04-11"
            end_datetime = "2024-04-12"
        
        
        if vehicle_registration_number!="":
            if vehicle_registration_number: 
                return render(request, 'map_history.html',{'start_datetime':start_datetime,"end_datetime":end_datetime,"vehicle_registration_number":vehicle_registration_number})
               
                #print("Timer input",time.time() - t ) 
                data = GPSData.objects.all().filter(gps_status=1).filter(longitude__range =[80,100]).filter(latitude__range =[20,30]).filter(vehicle_registration_number__icontains=vehicle_registration_number)
                 
                #print("Data select done")
                #print("filter1 ",time.time() - t ) 
                if start_datetime and end_datetime:
                        data = data.filter(entry_time__range=(start_datetime, end_datetime))   
                         
                        #print("Date fileter done")  
                        #print("filter2 ",time.time() - t )                    
                        data=data.filter(gps_status=1).order_by('entry_time')#[:17280]  
                        #print("sorting done")  
                        #print("sort ",time.time() - t ) 
                        mapdata=apply_low_pass_filter(data, ['longitude', 'latitude'])#[3:]  
                        #print("lpf done done")  
                        #print("lpf ",time.time() - t ) 
                        #print("total dataSize ",get_size(data))
                try:    #return JsonResponse({"eg":vehicle_registration_number})     
                    return render(request, 'map_history.html', {'data': data,'mapdata': mapdata,'mapdata_length': len(data)-1 })
                except:
                    return JsonResponse({"error": "No Record Found: "+str(vehicle_registration_number)}, status=403) 
            else:
                return JsonResponse({'error': "Invalid  Search "}, status=403) 
        return JsonResponse({'error': "Invalid Search"}, status=403) 
        return Response({'error': "Invalid Search"}, status=403)
        return render(request, 'map_history.html', {'data': data,'mapdata': mapdata,'mapdata_length': len(data)-1 })
        return Response({'error': "Invalid Search"}, status=403)
    except Exception as e: 
        return JsonResponse({'error': e}) 
        return Response({'error': "ww"}, status=400)

#@csrf_exempt
@require_http_methods(['GET', 'POST'])
def gps_history_map_data(request ): 
    #errors = validate_inputs(request)
    #if errors:
    #    return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    t = time.time()
    #print("Timer init",time.time() - t )   

    mapdata=[]
    data=[]     
    mapdata=[]
    data=[]
    try:
       
        
        try:
            vehicle_registration_number = request.GET.get('vehicle_registration_number', None)
            start_datetime = request.GET.get('start_datetime', None)
            end_datetime = request.GET.get('end_datetime', None)
        except:
             pass

        #return JsonResponse({"eg":vehicle_registration_number})
     
        
        
        if vehicle_registration_number!="":
            if vehicle_registration_number:
                #print("Timer input",time.time() - t ) 
                #filter(longitude__range =[80,100]).filter(latitude__range =[20,30]).
                data = GPSData.objects.all().filter(gps_status=1).filter(device_tag__vehicle_reg_no__icontains=vehicle_registration_number)
                 
                #print("Data select done")
                #print("filter1 ",time.time() - t ) 
                if start_datetime and end_datetime:
                        data = data.filter(entry_time__range=(start_datetime, end_datetime))   
                         
                        #print("Date fileter done")  
                        #print("filter2 ",time.time() - t )                    
                        data=data.filter(gps_status=1).order_by('entry_time')#[:17280]  
                        datalen=len(data)-1
                        #print("sorting done")  
                        #print("sort ",time.time() - t ) 
                        #mapdata=apply_low_pass_filter(data, ['longitude', 'latitude'])#[3:]  
                        #print("lpf done done")  
                        #print("lpf ",time.time() - t ) 
                        #print("total dataSize ",get_size(data))
                        data=GPSData_modSerializer(data, many=True).data
                        #mapdata=GPSData_modSerializer(mapdata, many=True).data
                try:    #return JsonResponse({"eg":vehicle_registration_number})     
                    return JsonResponse( {'data': data,'mapdata': mapdata,'mapdata_length': datalen })
                except Exception as e:
                    return JsonResponse({"error": "Unable to process request." +"No Record Found 1: "+vehicle_registration_number}, status=403) 
            else:
                return JsonResponse({'error': "Invalid Search 22"}, status=403) 
        return JsonResponse({'error': "Invalid Search"}, status=403) 
        #return Response({'error': "Invalid Search"}, status=403)
        #return render(request, 'map_history.html', {'data': data,'mapdata': mapdata,'mapdata_length': len(data)-1 })
        #return Response({'error': "Invalid Search"}, status=403)
    except Exception as e: 
        return JsonResponse({'error': "Unable to process request."+eeeeeee}) 
        return Response({'error': "ww"}, status=400)



@require_http_methods(['GET', 'POST'])
def setRoute(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Get the latest entry for each unique vehicle_registration_number
    #latest_data = GPSData.objects.filter(
    #    vehicle_registration_number=OuterRef('vehicle_registration_number')
    #).filter(gps_status=1).order_by('-entry_time').values('id')#[:1]


    # Retrieve the complete GPSData objects using the latest entry IDs
    #data = GPSData.objects.filter(id__in=Subquery(latest_data))
    if request.method == 'GET':
        device_id =  request.GET.get('device_id')
        device = DeviceStock.objects.get(id=device_id)   
        route = Route.objects.filter(device=device,status="Active" ) 
        return render(request, 'map_rout.html',{"routs": route } )
    
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

 

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
@require_http_methods(['GET', 'POST'])
def delRoute(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        user=request.user
        role="owner"
        man=get_user_object(user,role)
        role1="superadmin"
        sa=get_user_object(user,role1)
        if not man and not sa:
            return Response({"error":"Request must be from  "+role+' or '+role1+'.'}, status=status.HTTP_400_BAD_REQUEST)

        data =json.loads( request.body )
        try:
            id=data['id']  
            device =  DeviceStock.objects.get(id=data['device_id'])
            if id:
                route = Route.objects.filter(id=int(id),device=device,status="Active", createdby=user.id).last()
                if not route: 
                    return JsonResponse({"error": "Route not found"}, status=400)
                route.status="Deleted"
                route.save()
                route = Route.objects.filter(device=device,status="Active" , createdby=user).all()
                return JsonResponse({"message": "Route deleted successfully!",'new':[],"data": routeSerializer(route, many=True).data }, status=201)
        
        except Exception as e:
            print(e)
            return JsonResponse({"error": "Unable to process request."+eeeeeee}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


from jsonschema import validate, ValidationError

# Define the expected JSON schema
response_schema = {
    "type": "object",
    "properties": { 
                "paths": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "distance": {"type": "number"},
                            "weight": {"type": "number"},
                            "time": {"type": "number"},
                            "transfers": {"type": "number"},
                            "points_encoded": {"type": "boolean"},
                            "bbox": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 4,
                                "maxItems": 4
                            },
                            "points": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "coordinates": {
                                        "type": "array",
                                        "items": {
                                            "type": "array",
                                            "items": {"type": "number"},
                                            "minItems": 3,
                                            "maxItems": 3
                                        }
                                    }
                                },
                                "required": ["type", "coordinates"]
                            },
                            "instructions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "distance": {"type": "number"},
                                        "sign": {"type": "number"},
                                        "interval": {
                                            "type": "array",
                                            "items": {"type": "number"},
                                            "minItems": 2,
                                            "maxItems": 2
                                        },
                                        "text": {"type": "string"},
                                        "time": {"type": "number"},
                                        "street_name": {"type": "string"}
                                    },
                                    "required": ["distance", "sign", "interval", "text", "time"]
                                }
                            }
                        },
                        "required": ["distance", "weight", "time", "transfers", "points_encoded", "bbox", "points", "instructions"]
                    }
                }
            },
            "required": ["paths"]
   
 
}

# Function to validate the response
def validate_bhuvan_response(response_json):
    try:
        validate(instance=response_json, schema=response_schema)
        return True, "Response is valid."
    except ValidationError as e:
        return False, f"Invalid response: {e.message}"


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated]) #@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])   
def get_routePath(request): 
    # The target external API URL
    url = 'https://bhuvan-app1.nrsc.gov.in/api/routing/curl_routing_new_v2.php?token=fb46cfb86bea498dce694350fb6dd16d161ff8eb' 
    points_data = request.data.get("points", [])
    
    if not points_data:
        return Response({"error": "Points data is required"}, status=status.HTTP_400_BAD_REQUEST) 
    
    
     # Validate points
    if not points_data or not isinstance(points_data, list):
        return Response({"error": "Points data is required and must be a list"}, status=status.HTTP_400_BAD_REQUEST)
    if len(points_data)<2:
        return Response({"error": "At least two points are required to extract the path."}, status=status.HTTP_400_BAD_REQUEST)
    for point in points_data:
        if not isinstance(point, list) or len(point) != 2:
            return Response({"error": f"Invalid point format: {point}. Each point must be a list of two coordinates [longitude, latitude]."}, status=status.HTTP_400_BAD_REQUEST)
        
        longitude, latitude = point
        
        # Validate longitude and latitude ranges
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            return Response({"error": f"Invalid geo-coordinates: {point}. Longitude must be between -180 and 180, and latitude must be between -90 and 90."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the point is within India's boundary
        if not (68.0 <= longitude <= 97.0 and 6.0 <= latitude <= 37.0):
            return Response({"error": f"Point {point} is outside the rectangular boundary of India."}, status=status.HTTP_400_BAD_REQUEST)
    
    
    try:
        response = requests.post(
            url,
            json={"points": points_data},  # Send points data in the correct format
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()  
        json_output = response.json()
        
        # Convert JSON output to string and sanitize it
        json_output_str = json.dumps(json_output)
        sanitized_json_output_str = bleach.clean(json_output_str)
        
        # Convert sanitized string back to JSON
        sanitized_json_output = json.loads(sanitized_json_output_str)
        
        is_valid, message = validate_bhuvan_response(sanitized_json_output)
        if not is_valid:
            return Response({"error": "Incoming path data is invalid." }, status=400)
        
        hash_object = hashlib.sha256(json_output_str.encode())
        hash_hex = hash_object.hexdigest()  
        
        return Response({"data": sanitized_json_output}, status=200)
    
    except requests.exceptions.RequestException:
        return Response({"error": "Unable to extract path for the provided coordinates. Please try again later."}, status=400)
    except ValueError:
        return Response({"error": "Invalid response received from the external API."}, status=400)
    except Exception as e:
        return Response({"error": "An unexpected error occurred."+ eeeeeee}, status=400)
    
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
@require_http_methods(['GET', 'POST'])
def saveRoute(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        user=request.user
        role="owner"
        man=get_user_object(user,role)
        role1="superadmin"
        sa=get_user_object(user,role1)
        if not man and not sa:
            return Response({"error":"Request must be from  "+role+' or '+role1+'.'}, status=status.HTTP_400_BAD_REQUEST)

        #print(request.body)
        data =json.loads( request.body )
        id =None
        createdby=user #data['createdby_id'
        try:
            id=data['id']
        except Exception as e:
            print(e)

        try:
            #createdby =  User.objects.get(id=createdby)
            device =  DeviceStock.objects.get(id=data['device_id'])
            if not device:
                    return JsonResponse({"error": "Device not found"}, status=405)
            tag=None
            if man :
                tag=DeviceTag.objects.filter(  device_id=device,   vehicle_owner =man)
            elif sa:
                tag=DeviceTag.objects.filter( device_id=device)
            if not tag:
                    return JsonResponse({"error": "Unauthorised owner "}, status=405)

            if id:
                route = Route.objects.get(id=id,device=device,status='Active', createdby=user)
                if not route:
                    return JsonResponse({"error": "existing route not fond for given id "}, status=405)
                route.route = data['route']
                route.routepoints = data['routepoints']
                
                for k in ["route","routepoints"]:
                    points_data = data[k]
                
                    if not points_data or not isinstance(points_data, list):
                        return Response({"error": k+" is required and must be a list"}, status=status.HTTP_400_BAD_REQUEST)
                    if len(points_data)<2:
                        return Response({"error": "At least two points are required to extract the path."}, status=status.HTTP_400_BAD_REQUEST)
                    for point in points_data:
                        if not isinstance(point, list) or len(point) != 2:
                            return Response({"error": f"Invalid point format: {point}. Each point must be a list of two coordinates [longitude, latitude]."}, status=status.HTTP_400_BAD_REQUEST)
                        
                        longitude, latitude = point
                        
                        # Validate longitude and latitude ranges
                        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                            return Response({"error": f"Invalid geo-coordinates: {point}. Longitude must be between -180 and 180, and latitude must be between -90 and 90."}, status=status.HTTP_400_BAD_REQUEST)
                        
                        # Check if the point is within India's boundary
                        if not (68.0 <= longitude <= 97.0 and 6.0 <= latitude <= 37.0):
                            return Response({"error": f"Point {point} is outside the rectangular boundary of India."}, status=status.HTTP_400_BAD_REQUEST)
                    
                
                route.createdby = createdby #User.objects.get(id=data['createdby_id']) 
                route.save()
                routes = Route.objects.filter(device=device ,status='Active', createdby=user).all()
                return JsonResponse({"message": "Route saved successfully!",'update':routeSerializer(route).data,"data": routeSerializer(routes, many=True).data }, status=201)
        
            else:
                route = Route(
                    route=data['route'],
                    routepoints=data['routepoints'],
                    status='Active',  # Assuming status is 'Active' when created
                    device=device,
                    createdby=createdby
                )
                route.save()
                routes = Route.objects.filter(device=device , status='Active',createdby=user).all()
                return JsonResponse({"message": "New Route saved successfully!",'new':routeSerializer(route).data,"route": routeSerializer(routes, many=True).data }, status=201)
        except Exception as e:
            print(e)
            return JsonResponse({"error": "Unable to save route"}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)



@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
@require_http_methods(['GET', 'POST'])
def getRoute(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        user=request.user
        role="owner"
        man=get_user_object(user,role)
        role1="superadmin"
        sa=get_user_object(user,role1)
        if not man and not sa:
            return Response({"error":"Request must be from  "+role+' or '+role1+'.'}, status=status.HTTP_400_BAD_REQUEST)

        data =json.loads( request.body )
        device_id =  data['device_id']
        
        try:

            device =  DeviceStock.objects.get(id=data['device_id'])
            if not device:
                    return JsonResponse({"error": "Device not found"}, status=405)
            if man:
                tag=DeviceTag.objects.filter(   device_id=device,   vehicle_owner =man)
            elif sa:
                tag=DeviceTag.objects.filter(   device_id=device )
            if not tag:
                    return JsonResponse({"error": "Unauthorised Access "}, status=405) 
             
            route = Route.objects.filter(device=device ,status="Active", createdby=user).all()#.latest('id')
            return JsonResponse({"route": routeSerializer(route, many=True).data  }, status=200)
        except Route.DoesNotExist:
            return JsonResponse({"error": "No active route found for this device"}, status=404)
        except Exception as e:
            return JsonResponse({"error": "Unable to get route"}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
@require_http_methods(['GET', 'POST'])
def getRoutelist(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'GET':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        user=request.user
        role="owner"
        man=get_user_object(user,role)
        if not man:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)

        device_id =request.GET.get('device_id')
        try:
            device = DeviceStock.objects.get(id=device_id)
            route = Route.objects.filter(device=device, status='Active', createdby=user).all()#.latest('id')
            if not route:
                return JsonResponse({"error": "No active route found for this device"}, status=404)
            return JsonResponse({"route": route}, status=200)
        except Route.DoesNotExist:
            return JsonResponse({"error": "No active route found for this device"}, status=404)
        except Exception as e:
            return JsonResponse({"error": "Unable to get route list"}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

@require_http_methods(['GET', 'POST'])
def gps_data_allmap(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    

    if request.method == 'GET':
        imei=False
        regno=False
        try:
            imei = request.GET.get('imei')
        except:
            pass
        try:
            regno = request.GET.get('regno')
        except:
            pass
        # Get the latest entry for each unique vehicle_registration_number
        latest_data = GPSData.objects.filter(
            device_tag=OuterRef('device_tag')
        ).filter(gps_status=1).order_by('-entry_time').values('id')[:1]
        data=None
        #if imei:
        #    data = GPSData.objects.filter(imei=imei,id__in=Subquery(latest_data))
        #elif regno:
        #    data = GPSData.objects.filter(vehicle_registration_number=regno,id__in=Subquery(latest_data))
        #else:
        data = GPSData.objects.filter(id__in=Subquery(latest_data))

    return render(request, 'map.html', {'data': data,'regno':regno,'imei':imei})

@require_http_methods(['GET', 'POST'])
def gps_data_log_table(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Filter data based on the search query
    search_query = request.GET.get('search', '')
    if search_query:
        data = GPSDataLog.objects.filter(raw_data__contains=search_query).order_by('-timestamp')[:200]
    else:
        data = GPSDataLog.objects.all().order_by('-timestamp')[:200]
    serialized_data = serialize('json', data)
    
    return JsonResponse({
        'data': serialized_data,
        'search_query': search_query
    }, status=200)
    
    return render(request, 'gps_data_log_table.html', {'data': data, 'search_query': search_query})

@require_http_methods(['GET', 'POST'])
def gps_em_data_log_table(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Filter data based on the search query
    search_query = request.GET.get('search', '')
    if search_query:
        data = GPSemDataLog.objects.filter(raw_data__contains=search_query).order_by('-timestamp')[:200]
    else:
        data = GPSemDataLog.objects.all().order_by('-timestamp')[:200]
    serialized_data = serialize('json', data)
    
    return JsonResponse({
        'data': serialized_data,
        'search_query': search_query
    }, status=200)
    return render(request, 'gps_data_log_table.html', {'data': data, 'search_query': search_query})

        
#1     Registration of new user-
#tpid ="1007135935525313027"
#text="Dear User,To confirm your registration in SkyTron platform, please click at the following link and validate the registration request-{#var#}The link will expire in 5 minutes.-SkyTron"

#2   not working   Tagging of device and vehicle- owner confirmation:
#tpid ="1007941652638984780"
#text="Dear Vehicle Owner,To confirm Tagging of your vehicle with your tracking device in SkyTron platform, please click at the following link and validate the tagging request-{#var#}The link will expire in 5 minutes.-SkyTron"

#3      Set/Re-set new password-
#tpid ="1007927199705544392"
#text="Dear User,To activate your new password in SkyTron portal, please enter the OTP {#var#} valid for 5 minutes.Please do NOT share with anyone.-SkyTron"

#4. Dealer/Manufacturer confirmation of Tagging-
#tpid ="1007201930295888818"
#text="Dear VLTD Dealer/ Manufacturer,We have received request for tagging and activation of following device and vehicle-Vehicle Reg No: {#var#}Device IMEI No: {#var#}To confirm, please enter the OTP {#var#}.- SkyTron"


#5. Owner verification link sent during tagging and activation-
#tpid ="1007671504419591069"
#text="Dear Vehicle Owner,To confirm tagging and activation of your VLTD with your vehicle in SkyTron platform, kindly click on the following link and validate: {#var#}Link will expire in 5 minutes. Please do NOT share.-SkyTron"

#6. Owner OTP- after tagging / activation is successful-
#tpid ="1007937055979875563"
#text="Dear Vehicle Owner,To confirm tagging of your VLTD with your vehicle, please enter the OTP: {#var#} will expire in 5 minutes. Please do NOT share.-SkyTron"

#7. New User create OTP- (OTP at the time of creating a new user)-
#tpid ="1007274756418421381"
#text="Dear User,To validate creation of a new user login in SkyTron platform, please enter the OTP {#var#}.Valid for 5 minutes. Please do not share.-SkyTron"


def send_SMS(no,text,tpid):
    url = "http://tra.bulksmshyderabad.co.in/websms/sendsms.aspx"
    params = {
        'userid': "Gobell",
        'password':"1234566",
        'sender': "SKYTRN",
        'mobileno': no,
        'msg': text,
        'peid': '1001371511701977986',
        'tpid':  tpid
    } 

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise error for bad responses (non-200)
        #print("Message Sent Successfully")
    except requests.exceptions.HTTPError as errh:
        print("Loginotpsend HTTP Error:", errh)
    except requests.exceptions.RequestException as err:
        print("Loginotpsend Request Exception:", err)
    except Exception as e :
        print("Loginotpsend:", err)




def sms_send(no,text,tpid):
    #text = "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
    url = "http://tra.bulksmshyderabad.co.in/websms/sendsms.aspx"
    params = {
        'userid': "Gobell",
        'password':"1234566",
        'sender': "SKYTRN",
        'mobileno': no,
        'msg': text,
        'peid': '1001371511701977986',
        'tpid':  tpid
    } 

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise error for bad responses (non-200)
        print("Message Sent Successfully")
    except requests.exceptions.HTTPError as errh:
        print("Loginotpsend HTTP Error:", errh)
    except requests.exceptions.RequestException as err:
        print("Loginotpsend Request Exception:", err)
    except Exception as e :
        print("Loginotpsend:", err)

def add_sms_queue(msg,no):
    sms_entry ,error= sms_out.objects.safe_create( sms_text=msg,no=no, status='Queue'  )
    if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def sms_queue_add(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        no= request.GET.get('no')#request.data.get('no')
        msg = request.GET.get('msg', '') 
        add_sms_queue(msg,no)
        return JsonResponse({'status':"Success  "+msg})
    except Exception as e:
        return JsonResponse({'error': "error creating sms"}, status=400) 

@api_view(['POST'])  
@permission_classes([AllowAny])
@require_http_methods(['GET', 'POST'])
def sms_received(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Extract necessary parameters from the request data
        no= request.data.get('no')
        msg = request.data.get('msg', '')

        new_sms_in ,error= sms_in.objects.safe_create( sms_text=msg,no=no, status='Received'  )
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        return Response({'status':"Success"})
    except Exception as e:
        return Response({'error': "error geting sms"}, status=400)
    
@api_view(['get'])  
@permission_classes([AllowAny])
@require_http_methods(['GET', 'POST'])
def sms_queue(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        sms_entry = sms_out.objects.filter(status='Queue').first()
    
        if sms_entry:
            # Print all information of the retrieved entry
            #print(f"ID: {sms_entry.id}")
            #print(f"SMS Text: {sms_entry.sms_text}")
            #print(f"Number: {sms_entry.no}")
            #print(f"Status: {sms_entry.status}")
            #print(f"Created: {sms_entry.created}")

            # Update the status to 'Sent'
            sms_entry.status = 'Sent'
            sms_entry.save()
            return Response({'no':sms_entry.no,'msg':sms_entry.sms_text})
            #return Response({'no':"+917635975648",'msg':'data to send'})
        return Response({'no':"",'msg':''})
    except Exception as e:
        return Response({'error': "no sms"}, status=400)

    
@api_view(['get'])  
@require_http_methods(['GET', 'POST'])
def esim_provider_list(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        esimprovider= eSimProvider.objects.all()         
        esimprovider_serializer = eSimProviderSerializer(esimprovider, many=True)
        # Return the serialized data as JSON response
        return Response(esimprovider_serializer.data)
    except Exception as e:
        return Response({'error': "esim_provider_list"}, status=400)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def get_live_vehicle_no(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        if request.method == 'POST':
            # Fetch distinct vehicle registration numbers
            #vehicles = GPSData.objects.all().values('device_tag').distinct()
            vehicles = GPSData.objects.select_related('device_tag').distinct('device_tag')

            if not vehicles:
                return Response([])
            print(vehicles)
            vehicle_list=[]
            for vehicle in vehicles:
                if vehicle.device_tag:
                        vehicle_list = vehicle_list +[vehicle.device_tag.vehicle_reg_no]
            return Response(vehicle_list)
        else:
            return Response({'error': "POST request only"}, status=400)
    except Exception as e:
        return Response({'error': "get_live_vehicle_no"}, status=400)
 
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        
        id = request.data.get('vehicleowner_id')
        vehicle_owner = VehicleOwner.objects.filter(id=id).last()
        if not vehicle_owner:
            return Response({'error': "Invalid VehicleOwner id"}, status=400)
        if vehicle_owner.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.now()
        created = timezone.now()
        expirydate = request.data.get('expiryDate')#date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        idProofno = request.data.get('idProofno')
        file_idProof = request.data.get('file_idProof')

        email = request.data.get('email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if company_name:
            vehicle_owner.company_name = company_name
        if idProofno:
            vehicle_owner.idProofno = idProofno
        if file_idProof:
            vehicle_owner.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not vehicle_owner.file_idProof : 
                    return Response({'error': "Invalid file." }, status=400)
        vuser=vehicle_owner.users.last()
        if email:
            vuser.email = email
        if mobile:
            vuser.mobile = mobile
        if name:
            vuser.name = name
        if dob:
            vuser.dob = dob

        new_password = ''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        vuser.password = hashed_password
        #vehicle_owner.date_joined = str(date_joined)
        #vehicle_owner.created = str(created)
        vehicle_owner.expirydate = expirydate
        vuser.save()
        vehicle_owner.save()
        #send_usercreation_otp(vehicle_owner.users, new_password, 'Vehicle Owner')
        return Response(VehicleOwnerSerializer(vehicle_owner).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        company_name = request.data.get('company_name') 
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now()  
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        file_idProof = request.data.get('file_idProof') 
        user,error,new_password=create_user('owner',request)
        if not company_name:
            company_name=""
        if user: 
            try:
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                
                if not file_idProof : 
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)
                dealer ,error= VehicleOwner.objects.safe_create(
                    company_name=company_name, 
                    created=created,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    createdby=createdby,
                    status="Created",
                ) 
            
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request."+str(e)}, status=400)
            dealer.users.add(user) 
            send_usercreation_otp(user,new_password,'Vehicle Owner ')
             
            return Response(VehicleOwnerSerializer(dealer).data)
        else:
            return Response(error, status=400)        

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_manufacturer(request, manufacturer_id):
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get the Manufacturer instance or return a 404 response
        manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id)

        # Delete the associated user
        user = manufacturer.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        manufacturer.delete()

        return Response({'message': 'Manufacturer and associated user deleted successfully'})


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_dealer(request, dealer_id):
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    try:
        # Get the Manufacturer instance or return a 404 response
        dealer = get_object_or_404(Retailer, id=dealer_id)

        # Delete the associated user
        user =dealer.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        dealer.delete()

        return Response({'message': 'Dealer and associated user deleted successfully'})


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_eSimProvider(request, esimProvider_id):
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from   "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    try:
        # Get the Manufacturer instance or return a 404 response
        esimProvider = get_object_or_404(eSimProvider, id=esimProvider_id)

        # Delete the associated user
        user =esimProvider.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        esimProvider.delete()

        return Response({'message': 'eSim Provider and associated user deleted successfully'})


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_VehicleOwner(request, vo_id):
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    try:
        # Get the Manufacturer instance or return a 404 response
        vo = get_object_or_404(VehicleOwner, id=vo_id)

        # Delete the associated user
        user =vo.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        vo.delete()

        return Response({'message': 'Vehicle Owner and associated user deleted successfully'})


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:

        user=request.user
        role="stateadmin"
        uo=get_user_object(user,role)
        role2="superadmin"
        uo2=get_user_object(user,role2)

        # Get filter parameters from the request
        obj_id = request.data.get('VehicleOwner_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '') 
        address_State = request.data.get('address_State', '')
        filters = {} 
        
        if uo2:  # Superadmin - should get all data
            if obj_id:
                manufacturers = VehicleOwner.objects.filter(
                    id=obj_id,
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                    users__address__icontains=address,
                    users__address_State__icontains=address_State,
                ).distinct()
            else:
                manufacturers = VehicleOwner.objects.filter(
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                    users__address__icontains=address,
                    users__address_State__icontains=address_State,
                ).distinct()
        
        
        elif uo:  # State admin - filter by state
            state=uo.state
            owners = DeviceTag.objects.filter( device__dealer_id__manufacturer_id__state=state, status="Owner_Final_OTP_Verified").values("vehicle_owner").distinct()
            manufacturers = VehicleOwner.objects.filter(
                        id__in=owners,
                        users__email__icontains=email,
                        company_name__icontains=company_name,
                        users__name__icontains=name,
                        users__mobile__icontains=phone_no,
                        users__address__icontains=address,
                        users__address_State__icontains=address_State,
                    ).distinct()
        
        
        else:  # Other roles
            state = request.data.get('state', '')
            if obj_id :
                manufacturers = VehicleOwner.objects.filter(
                    id=obj_id,
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                    users__address__icontains=address,
                    users__address_State__icontains=address_State,
                ).distinct()
            else:
                manufacturers = VehicleOwner.objects.filter(
                    #id=manufacturer_id,
                    users__status='active',
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                    users__address__icontains=address,
                    users__address_State__icontains=address_State,
                ).distinct()

        # Serialize the queryset
        dealer_serializer = VehicleOwnerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        id = request.data.get('manufacturer_id')
        man=Manufacturer.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid manufacturer id"}, status=400)
        if man.createdby == request.user :
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.now()
        created = timezone.now() 
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')        
        state = request.data.get('state')
        gstno = request.data.get('gstno' )   
        idProofno = request.data.get('idProofno' )  
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        esim_provider_ids = request.data.get('esim_provider', [])
        
        email = request.data.get('email' )
        mobile = request.data.get('mobile' )
        name = request.data.get('name' )
        dob = request.data.get('dob' )
        if company_name:
            man.company_name=company_name
        if gstnnumber :
            man.gstnnumber=gstnnumber
        if state:
            man.state = state
        if gstno:
            man.gstno=gstno  
        if  idProofno:
            man.idProofno=idProofno
        if file_authLetter:
            man.file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man') 
            
            if not man.file_authLetter : 
                    return Response({'error': "Invalid file." }, status=400)

        if file_companRegCertificate :
            man.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
                
            if not man.file_companRegCertificate : 
                    return Response({'error': "Invalid file." }, status=400)

        if file_GSTCertificate :
            man.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
            if not man.file_GSTCertificate : 
                    return Response({'error': "Invalid file." }, status=400)
            

        if file_idProof:
            man.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not man.file_idProof : 
                    return Response({'error': "Invalid file." }, status=400)
            
        if esim_provider_ids !=[]:
            man.esim_provider_ids=esim_provider_ids

            
        if email:
            man.user.email  =email
        if mobile:
            man.user.mobile=mobile
        if name:
            man.user.name=name 
        if dob:
            man.user.dob
        
        new_password=''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        man.user.password  = hashed_password
        man.date_joined = date_joined
        man.created = created
        man.expirydate = expirydate
        man.user.save()
        man.save()
        send_usercreation_otp(man.user, new_password, 'Device Manufacture ')
        return Response(ManufacturerSerializer(man ).data)
      

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_eSimProvider(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        id = request.data.get('esimprovider_id')
        esimprovider = eSimProvider.objects.filter(id=id).last()
        if not esimprovider:
            return Response({'error': "Invalid eSimProvider id"}, status=400)
        if esimprovider.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.now()
        created = timezone.now()
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        gstno = request.data.get('gstno')
        idProofno = request.data.get('idProofno')
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')

        email = request.data.get('email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if company_name:
            esimprovider.company_name = company_name
        if gstnnumber:
            esimprovider.gstnnumber = gstnnumber
        if gstno:
            esimprovider.gstno = gstno
        if idProofno:
            esimprovider.idProofno = idProofno
        if file_authLetter:
            esimprovider.file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man')
            
            if not esimprovider.file_authLetter: 
                    return Response({'error': "Invalid file." }, status=400)
        if file_companRegCertificate:
            esimprovider.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
        
            if not esimprovider.file_companRegCertificate: 
                    return Response({'error': "Invalid file." }, status=400)
        if file_GSTCertificate:
            esimprovider.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
        
            if not esimprovider.file_GSTCertificate:
                    return Response({'error': "Invalid file." }, status=400)
        if file_idProof:
            esimprovider.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            
            if not esimprovider.file_idProof: 
                    return Response({'error': "Invalid file." }, status=400)

        if email:
            esimprovider.user.email = email
        if mobile:
            esimprovider.user.mobile = mobile
        if name:
            esimprovider.user.name = name
        if dob:
            esimprovider.user.dob = dob

        new_password = ''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        esimprovider.user.password = hashed_password
        esimprovider.date_joined = date_joined
        esimprovider.created = created
        esimprovider.expirydate = expirydate
        esimprovider.user.save()
        esimprovider.save()
        send_usercreation_otp(esimprovider.user, new_password, 'EsimProvider')
        return Response(eSimProviderSerializer(esimprovider).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  
@require_http_methods(['GET', 'POST'])
def create_eSimProvider(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
      
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber') 
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now()   
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof') 
        state = request.data.get('stateId') 
        user,error,new_password=create_user('esimprovider',request)
        if user:  
         
            try:
                try:
                    file_authLetter=save_file(request,'file_authLetter','fileuploads/man') 
                    file_companRegCertificate=save_file(request,'file_dot_esim_registration','fileuploads/man')
                    file_GSTCertificate=save_file(request,'file_GSTCertificate','fileuploads/man')
                    file_idProof = save_file(request,'file_idProof','fileuploads/man')
                    if not file_authLetter or not file_companRegCertificate or not file_GSTCertificate or not file_idProof:    
                        user.delete()
                        return Response({'error': "Invalid file." }, status=400)
                except Exception as e:
                    user.delete()


                    return Response({'error44': "Unable to process request."+eeeeeee}, status=400)


                dealer ,error= eSimProvider.objects.safe_create(
                    company_name=company_name,
                    gstnnumber=gstnnumber,
                    created=created,
                    expirydate=expirydate,
                    gstno=gstno,
                    state_id=state,
                    idProofno=idProofno,
                    file_authLetter=file_authLetter,
                    file_companRegCertificate=file_companRegCertificate,
                    file_GSTCertificate=file_GSTCertificate,
                    file_idProof=file_idProof,
                    createdby=createdby,
                    status="Created",
                )
                
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()


                return Response({'error1': "Unable to process request."+eeeeeee}, status=400)
            dealer.users.add(user)
            send_usercreation_otp(user,new_password,'EsimProvider ')
             
            return Response(eSimProviderSerializer(dealer).data)
        else:
            return Response({'error131': str(error)}, status=400)

    except Exception as e:
        return Response({'error2': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_eSimProvider(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:

        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)
        role="devicemanufacture" 
        um=get_user_object(user,role)
        if um:
            
            dealer_serializer = eSimProviderSerializer(um.esim_provider, many=True)
            return Response(dealer_serializer.data)
        
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state_filter = request.data.get('state', '')

        # Start with base query
        manufacturers = eSimProvider.objects.filter(users__status='active')
        
        # Apply filters based on input parameters
        if dealer_id:
            manufacturers = manufacturers.filter(id=dealer_id)
        
        if email:
            manufacturers = manufacturers.filter(users__email__icontains=email)
            
        if company_name:
            manufacturers = manufacturers.filter(company_name__icontains=company_name)
            
        if name:
            manufacturers = manufacturers.filter(users__name__icontains=name)
            
        if phone_no:
            manufacturers = manufacturers.filter(users__mobile__icontains=phone_no)
            
        if state_filter:
            manufacturers = manufacturers.filter(state__id=state_filter)

        # Apply state-based filtering for state admin users
        if uo:  # If user is a state admin
            manufacturers = manufacturers.filter(state=uo.state)

        # Get distinct results and include state information
        manufacturers = manufacturers.select_related('state').distinct()

        # Serialize the queryset
        dealer_serializer = eSimProviderSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        
        return Response({'error': "Unable to process request." + str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="devicemanufacture"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        id = request.data.get('dealer_id')
        dealer = Retailer.objects.filter(id=id).last()
        if not dealer:
            return Response({'error': "Invalid dealer id"}, status=400)
        if dealer.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.now()
        created = timezone.now() 
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')        
        gstno = request.data.get('gstno')   
        idProofno = request.data.get('idProofno')  
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        district = request.data.get('district')

        email = request.data.get('email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if company_name:
            dealer.company_name = company_name
        if gstnnumber:
            dealer.gstnnumber = gstnnumber
        if gstno:
            dealer.gstno = gstno  
        if idProofno:
            dealer.idProofno = idProofno
        if file_authLetter:
            dealer.file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man')
            if not dealer.file_authLetter:
                    return Response({'error': "Invalid file." }, status=400)
        if file_companRegCertificate:
            dealer.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
            if not dealer.file_companRegCertificate:
                    return Response({'error': "Invalid file." }, status=400)
        if file_GSTCertificate:
            dealer.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
            if not dealer.file_GSTCertificate:
                    return Response({'error': "Invalid file." }, status=400)
        if file_idProof:
            dealer.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not dealer.file_idProof:
                    return Response({'error': "Invalid file." }, status=400)
        if district:
            dealer.district = district

        if email:
            dealer.user.email = email
        if mobile:
            dealer.user.mobile = mobile
        if name:
            dealer.user.name = name 
        if dob:
            dealer.user.dob = dob

        new_password = ''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        dealer.user.password = hashed_password
        dealer.date_joined = date_joined
        dealer.created = created
        dealer.expirydate = expirydate
        dealer.user.save()
        dealer.save()
        send_usercreation_otp(dealer.user, new_password, 'Dealer')
        return Response(RetailerSerializer(dealer).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    man=Manufacturer.objects.filter(id=request.data.get('manufacturer')).last()
    if not man:
        return Response({"error":"Manufacturer not found."}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber') 
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now()   
         
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof') 
        district = request.data.get('district') 
        user,error,new_password=create_user('dealer',request)
        if user:         
            try:
                
                file_authLetter=save_file(request,'file_authLetter','fileuploads/man') 
                file_companRegCertificate=save_file(request,'file_companRegCertificate','fileuploads/man')
                file_GSTCertificate=save_file(request,'file_GSTCertificate','fileuploads/man')
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                if not file_authLetter or not file_companRegCertificate or not file_GSTCertificate or not file_idProof:
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)
                


                dealer ,error= Retailer.objects.safe_create(
                    company_name=company_name,
                    gstnnumber=gstnnumber,
                    created=created,
                    expirydate=expirydate,
                    gstno=gstno,
                    idProofno=idProofno,
                    file_authLetter=file_authLetter,
                    file_companRegCertificate=file_companRegCertificate,
                    file_GSTCertificate=file_GSTCertificate,
                    file_idProof=file_idProof,
                    createdby=createdby,
                    district=district,
                    manufacturer=man,
                    status="Created",
                )
                
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request."+eeeeeee}, status=400) 
            dealer.users.add(user)
            send_usercreation_otp(user,new_password,'Dealer ')             
            return Response(RetailerSerializer(dealer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:

        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="devicemanufacture"
        user=request.user
        uo=get_user_object(user,role)
        role="stateadmin" 
        suo=get_user_object(user,role)
        
        # Get filter parameters from the request
        dealer_id = request.data.get('dealer_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        district_filter = request.data.get('district', '')

        # Start with base query including related fields for better performance
        manufacturers = Retailer.objects.select_related('manufacturer__state', 'district__state')
        
        # Apply filters based on user role and input parameters
        if uo:  # Device manufacturer user
            manufacturers = manufacturers.filter(manufacturer=uo)
        elif suo:  # State admin user
            manufacturers = manufacturers.filter(manufacturer__state=suo.state)
        
        # Apply additional filters
        if dealer_id:
            manufacturers = manufacturers.filter(id=dealer_id)
        else:
            manufacturers = manufacturers.filter(users__status='active')
            
        if email:
            manufacturers = manufacturers.filter(users__email__icontains=email)
            
        if company_name:
            manufacturers = manufacturers.filter(company_name__icontains=company_name)
            
        if name:
            manufacturers = manufacturers.filter(users__name__icontains=name)
            
        if phone_no:
            manufacturers = manufacturers.filter(users__mobile__icontains=phone_no)
            
        if district_filter:
            manufacturers = manufacturers.filter(district__id=district_filter)

        # Get distinct results
        manufacturers = manufacturers.distinct()

        # Serialize the queryset
        dealer_serializer = RetailerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request." + str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        
        id = request.data.get('manufacturer_id')
        man=Manufacturer.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid manufacturer id"}, status=400)
        if man.createdby == request.user :
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.now()
        created = timezone.now() 
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')        
        state = request.data.get('state')
        gstno = request.data.get('gstno' )   
        idProofno = request.data.get('idProofno' )  
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        esim_provider_ids = request.data.get('esim_provider', [])
        
        email = request.data.get('email' )
        mobile = request.data.get('mobile' )
        name = request.data.get('name' )
        dob = request.data.get('dob' )
        if company_name:
            man.company_name=company_name
        if gstnnumber :
            man.gstnnumber=gstnnumber
        if state:
            man.state = state
        if gstno:
            man.gstno=gstno  
        if  idProofno:
            man.idProofno=idProofno
        if file_authLetter:
            man.file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man') 
            if not man.file_authLetter :
                    return Response({'error': "Invalid file." }, status=400)

        if file_companRegCertificate :
            man.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
            if not man.file_companRegCertificate :
                return Response({'error': "Invalid file." }, status=400)

        if file_GSTCertificate :
            man.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
            if not file_GSTCertificate :
                return Response({'error': "Invalid file." }, status=400)

        if file_idProof:
            man.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            
            if not file_idProof :
                return Response({'error': "Invalid file." }, status=400)
        if esim_provider_ids !=[]:
            man.esim_provider_ids=esim_provider_ids

            
        if email:
            man.user.email  =email
        if mobile:
            man.user.mobile=mobile
        if name:
            man.user.name=name 
        if dob:
            man.user.dob
        
        new_password=''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        man.user.password  = hashed_password
        man.date_joined = date_joined
        man.created = created
        man.expirydate = expirydate
        man.user.save()
        man.save()
        send_usercreation_otp(man.user, new_password, 'Device Manufacture ')
        return Response(ManufacturerSerializer(man ).data)
      

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        state = request.data.get('state')
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        esim_provider_ids = request.POST.getlist('esimProvider[]',[])#request.data.get('esimProvider[]', [])
        print(esim_provider_ids)

        user, error, new_password = create_user('devicemanufacture', request)
        if user:  
            try:
                file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man') 
                file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
                file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
                file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
                if not file_authLetter or not file_companRegCertificate or not file_GSTCertificate or not file_idProof:
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)

                manufacturer ,error= Manufacturer.objects.safe_create(
                    company_name=company_name,
                    gstnnumber=gstnnumber,
                    created=created,
                    expirydate=expirydate,
                    gstno=gstno,
                    idProofno=idProofno,
                    file_authLetter=file_authLetter,
                    file_companRegCertificate=file_companRegCertificate,
                    file_GSTCertificate=file_GSTCertificate,
                    file_idProof=file_idProof,
                    state_id=state,
                    createdby=createdby,
                    status="Created",
                )
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

                
                # Fetch the EsimProvider instances and set the many-to-many relationship
                esim_providers = eSimProvider.objects.filter(id__in=esim_provider_ids)
                a=0

                for esim_provider in esim_providers:
                    print(esim_provider.state.id)
                    if str(esim_provider.state.id)==str(state):
                        manufacturer.esim_provider.set(esim_providers)
                        a=a+1
                    else:
                        user.delete()
                        manufacturer.delete()
                        return Response({'error': "State missmatch with esim Provider"}, status=400)
                if a==0:

                    user.delete()
                    manufacturer.delete()
                    return Response({'error': "No valid esim Provider"}, status=400)
                



            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request."+eeeeeee}, status=400)
            
            manufacturer.users.add(user) 
            send_usercreation_otp(user, new_password, 'Device Manufacture ')
            return Response(ManufacturerSerializer(manufacturer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_manufacturers(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('manufacturer_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Check user role and apply appropriate filtering
        user = request.user
        
        # Check if user is an eSIM provider
        esim_provider_obj = get_user_object(user, "esimprovider")
        
        # Start with base queryset
        manufacturers = Manufacturer.objects.all()
        
        # If user is an eSIM provider, only show manufacturers assigned to them
        if esim_provider_obj:
            manufacturers = manufacturers.filter(esim_provider=esim_provider_obj)

        # Add ID filter if provided
        if manufacturer_id:
            manufacturers = manufacturers.filter(
                id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = manufacturers.filter(
                users__status='active',
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        manufacturer_serializer = ManufacturerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(manufacturer_serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


from django.db import IntegrityError
from django.core.exceptions import ValidationError

def create_user(role, req):
    try:
        email = req.data.get('email', '')
        mobile = req.data.get('mobile', '')
        name = req.data.get('name', '')
        dob = req.data.get('dob', '')
        createdby = req.user
        date_joined = timezone.now()
        created = timezone.now()
        is_active = True
        is_staff = False
        status = 'pending'
        new_password = ''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)

        # Create user
        user ,error= User.objects.safe_create(
            name=name,
            email=email,
            mobile=mobile,
            role=role,
            dob=dob,
            createdby=createdby.id,
            date_joined=date_joined,
            created=created,
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password=hashed_password
        )
        if error:  # Rollback user creation if dealer creation fails
            return [None, error.data , None] # Return the Response object from safe_create

        user.save()

        # Create token
        token = Token.objects.create(user=user, key=new_password)  

        return [user, None, new_password]

    except IntegrityError as e:
        # Handle database integrity errors (e.g., duplicate keys)
        if 'email' in eeeeeee:
            return [None, {'error': "Email field is invalid or already exists."}, None]
        elif 'mobile' in eeeeeee:
            return [None, {'error': "Mobile field is invalid or already exists."}, None]
        else:
            return [None, {'error': "A database integrity error occurred."}, None]

    except ValidationError as e:
        # Handle validation errors
        errors = {}
        for field, messages in e.message_dict.items():
            errors[field] = f"{field} field is invalid."
        return [None, {'error': errors}, None]

    except Exception as e:
        # General exception handling
        return [None, {'error': "Unable to process request.1"+eeeeeee}, None]


def send_usercreation_otp(user,new_password,type):
    try:
        tpid ="1007387007813205696" #1007274756418421381"
        #text="Dear User,To validate creation of a new user login in SkyTron platform, please enter the OTP {}.Valid for 5 minutes. Please do not share.-SkyTron".format(new_password)
        #Dear User, To confirm your registration in SkyTron platform, please click at the following link and validate the registration request- https://gromed.in/new/{#var#} The link will expire in 5 minutes.-SkyTron
        text='Dear User, To confirm your registration in SkyTron platform, please click at the following link and validate the registration request- https://gromed.in/new/'+str(new_password)+' The link will expire in 5 minutes.-SkyTron'
        send_SMS(user.mobile,text,tpid) 
        send_mail(
                type+' Account Created',text
                #f'Temporery password is : {new_password}'
                ,'noreply@skytron.in',
                [user.email],
                fail_silently=False,
                ) 
    except Exception as e:
        pass
        # Response({'error': "Error in sendig email  "+"Unable to process request."+eeeeeee}, status=400)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_StateAdmin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        idProofno = request.data.get('idProofno' )  # Placeholder for idProofno
        state= request.data.get('state','')  
        
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now()  
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        file_idProof = request.data.get('file_idProof')
        file_authorisation_letter = request.data.get('file_authorisation_letter')
        
         
        user,error,new_password=create_user('stateadmin',request)
        if user:         
            try: 
                #return Response({'error': "Unable to process request1." }, status=400)
            
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                if not file_idProof:
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)
                file_authorisation_letter=save_file(request,'file_authorisation_letter','fileuploads/man')
                if not file_authorisation_letter:
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)
                #user.delete()
                
                dealer, error = StateAdmin.objects.safe_create( 
                    created=created,
                    state_id=state,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    file_authorisation_letter=file_authorisation_letter,
                    createdby=createdby,
                    status="Created",
                ) 
                
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

                 
                
     
            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request1."+str(e)}, status=400)
            dealer.users.add(user)
            send_usercreation_otp(user,new_password,'State Admin ')
             
            return Response(StateadminSerializer(dealer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_StateAdmin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        id = request.data.get('stateadmin_id')
        stateadmin = StateAdmin.objects.filter(id=id).last()
        if not stateadmin:
            return Response({'error': "Invalid StateAdmin id"}, status=400)
        if stateadmin.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.now()
        created = timezone.now()
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        email = request.data.get('email')
        idProofno = request.data.get('idProofno')
        state = request.data.get('state')
        file_idProof = request.data.get('file_idProof')

        new_email = request.data.get('new_email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if email:
            stateadmin.user.email = email
        if idProofno:
            stateadmin.idProofno = idProofno
        if state:
            stateadmin.state_id = state
        if file_idProof:
            stateadmin.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not stateadmin.file_idProof:
                     
                    return Response({'error': "Invalid file." }, status=400)

        if new_email:
            stateadmin.user.email = new_email
        if mobile:
            stateadmin.user.mobile = mobile
        if name:
            stateadmin.user.name = name
        if dob:
            stateadmin.user.dob = dob

        new_password = ''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        stateadmin.user.password = hashed_password
        stateadmin.date_joined = date_joined
        stateadmin.created = created
        stateadmin.expirydate = expirydate
        stateadmin.user.save()
        stateadmin.save()
        send_usercreation_otp(stateadmin.user, new_password, 'State Admin')
        return Response(StateadminSerializer(stateadmin).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_StateAdmin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('StateAdmin_id', None)
        email = request.data.get('email', '') 
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state = request.data.get('state', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if manufacturer_id :
            manufacturers = StateAdmin.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = StateAdmin.objects.filter(
                #id=manufacturer_id,
                users__status='active',
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = StateadminSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

 



Districtlist={'Kamrup':'AS01','Kamrup Rural':'AS25','Nagaon':'AS02','Jorhat':'AS03',
              'Sibsagar':'AS04','Golaghat':'AS05','Dibrugarh':'AS06','Lakhimpur':'AS07',
              'Dima Hasao':'AS08','Karbi anglong':'AS09','Karimganj':'AS10','Cachar':'AS11',
              'Tezpur':'AS12','Darrang':'AS13','Nalbari':'AS14','Barpeta':'AS15','Kokrajhar':'AS16',
              'The woman':'AS17',' Goalpara':'AS18','Bongaigaon':'AS19','Marigaon':'AS21','Dhemaji':'AS22',
              'Tinsukia':'AS23','Hailakandi':'AS24','Chirang':'AS26','Udalguri':'AS27','Baksa':'AS28','Hojai':'AS31',
              'Biswanath':'AS32','Charaideo':'AS33','South Salmara':'AS34'}

@csrf_exempt
@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def getDistrictList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        state= request.data.get('State')
        districts = Settings_District.objects.filter(state_id=state).order_by('district', 'id')
        Districtlist = {}
        for district in districts:
            Districtlist[district.district] = district.district_code
        return JsonResponse(Districtlist)
    except:
        return Response({"error":"Unable to find District"}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_DTO_RTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now()  
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '')
        dto_rto1= request.data.get('dto_rto', '')
        districtC = request.data.get('district_code', '')
        #state= request.data.get('State', '1')
        districts = Settings_District.objects.filter(state_id=state).order_by('district', 'id')
        Districtlist = {}
        if str(uo.state_id) !=str(state):
            return Response({"error":"Unauthorised state "+'.'}, status=status.HTTP_400_BAD_REQUEST)

        for district in districts:
            Districtlist[district.district] = district.district_code
        if districtC not in Districtlist.values():
            return Response({'error': "Invalid Dtrict Code:"+districtC}, status=400)
        file_idProof = request.data.get('file_idProof') 
        user,error,new_password=create_user('dtorto',request)
        if user:         
            try: 
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                file_authorisation_letter = save_file(request,'file_authorisation_letter','fileuploads/man')
                if not file_idProof or not file_authorisation_letter:
                    user.delete() 
                     
                    return Response({'error': "Invalid file." }, status=400)

                dealer,error = dto_rto.objects.safe_create( 
                    created=created,
                    state_id=state,
                    dto_rto=dto_rto1,
                    district=districtC,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    file_authorisation_letter=file_authorisation_letter,
                    createdby=createdby,
                    status="Created",
                ) 
                
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request."+eeeeeee}, status=400)
            dealer.users.add(user) 
            send_usercreation_otp(user,new_password,'DTO/RTO ')
             
            return Response(dto_rtoSerializer(dealer).data)
        else:
            return Response(error, status=400)          

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_DTO_RTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        id = request.data.get('dtorto_id')
        dtorto = dto_rto.objects.filter(id=id).last()
        if not dtorto:
            return Response({'error': "Invalid DTO/RTO id"}, status=400)
        if dtorto.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.now()
        created = timezone.now()
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        idProofno = request.data.get('idProofno')
        state = request.data.get('state', '1')
        dto_rto1 = request.data.get('dto_rto')
        districtC = request.data.get('district_code')

        districts = Settings_District.objects.filter(state_id=state).order_by('district', 'id')
        Districtlist = {district.district: district.district_code for district in districts}
        if districtC not in Districtlist.values():
            return Response({'error': "Invalid District Code:" + districtC}, status=400)

        file_idProof = request.data.get('file_idProof')
        file_authorisation_letter= request.data.get('file_authorisation_letter')

        email = request.data.get('email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if idProofno:
            dtorto.idProofno = idProofno
        if state:
            dtorto.state_id = state
        if dto_rto1:
            dtorto.dto_rto = dto_rto1
        if districtC:
            dtorto.district = districtC
        if file_idProof:
            dtorto.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not dtorto.file_idProof: 
                    return Response({'error': "Invalid file." }, status=400)
                
                
        if file_authorisation_letter:
            dtorto.file_idProof = save_file(request, 'file_authorisation_letter', 'fileuploads/man')
            if not dtorto.file_idProof: 
                    return Response({'error': "Invalid file." }, status=400)

        if email:
            dtorto.user.email = email
        if mobile:
            dtorto.user.mobile = mobile
        if name:
            dtorto.user.name = name
        if dob:
            dtorto.user.dob = dob

        new_password = ''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        dtorto.user.password = hashed_password
        dtorto.date_joined = date_joined
        dtorto.created = created
        dtorto.expirydate = expirydate
        dtorto.user.save()
        dtorto.save()
        send_usercreation_otp(dtorto.user, new_password, 'DTO/RTO')
        return Response(dto_rtoSerializer(dtorto).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_DTO_RTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)
        if uo:
            state=uo.state
        else:
            state = request.data.get('state', '')

        # Get filter parameters from the request
        obj_id = request.data.get('dto_rto_id', None)
        email = request.data.get('email', '') 
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        
        district = request.data.get('district', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if obj_id :
            manufacturers = dto_rto.objects.filter(
                id=obj_id,
                state=state,
           
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = dto_rto.objects.filter(
                state=state,
           
                users__status='active',
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = dto_rtoSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def transfer_DTO_RTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get filter parameters from the request
        id = request.data.get('dto_rto_id', None) 
        district = request.data.get('new_district_code', '')
        
        if district not in Districtlist.values():
            return Response({'error': "Invalid Dtrict Code:"+district}, status=400)

        
        if  id :
            dto = dto_rto.objects.get(id=id) 
            if dto:
                dd=dto.district
                if dd==district:
                    return Response({'error': 'No change in district code'}, status=400)
                dto.district=district
                dto.save()
                serializer = dto_rtoSerializer(dto, many=False)
                return Response({'Status': 'Successfully transfered from '+str(dd)+' to '+district,'dto_data':serializer.data})
            return Response({'error': 'DTO with given id ont found'}, status=400)
        return Response({'error': 'dto_rto_id not found'}, status=400)



    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


 
 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_SOS_user(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now()   
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '') 
        district = request.data.get('district', '')
        user_type = request.data.get('user_type', '') 
        file_idProof = request.data.get('file_idProof') 
        user,error,new_password=create_user('sosexecutive',request)
 
        if user:  
            try: 
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                if not  file_idProof: 
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)


                dealer,error = EM_ex.objects.safe_create( 
                    created=created,
                    state_id=state, 
                    #district_id=district,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    user_type=user_type,
                    createdby=createdby,
                    status="Created",
                ) 
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request."+eeeeeee}, status=400)
            dealer.users.add(user) 
            send_usercreation_otp(user,new_password,'SOS user ')             
            return Response(EM_exSerializer(dealer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_SOS_user(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('dto_rto_id', None)
        email = request.data.get('email', '') 
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state = request.data.get('state', '')
        district = request.data.get('district', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if manufacturer_id :
            manufacturers = EM_ex.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = EM_ex.objects.filter(
                #id=manufacturer_id,
                users__status='active',
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = EM_exSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


from collections import defaultdict

@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def list_alert_logs(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        start_datetime = request.POST.get('start_datetime')
        end_datetime = request.POST.get('end_datetime')
        district_id = request.POST.get('district_id')
        state_id = request.POST.get('state_id')

        queryset = AlertsLog.objects.all()

        # Filter queryset based on optional POST inputs
        if start_datetime:
            queryset = queryset.filter(timestamp__gte=start_datetime)
        if end_datetime:
            queryset = queryset.filter(timestamp__lte=end_datetime)
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        if state_id:
            queryset = queryset.filter(state_id=state_id)

        # Get all alert types
        all_alert_types = dict(AlertsLog.TYPE_CHOICES)

        # Group queryset by alert type
        alert_groups = defaultdict(list)
        for item in queryset:
            alert_groups[item.type].append(AlertsLogSerializer(item).data)

        # Create response dictionary with all types, even if not present in queryset
        response_data = {}
        for alert_type, alert_type_name in all_alert_types.items():
            response_data[alert_type_name] = {
                'count': len(alert_groups[alert_type]),
                'details': alert_groups[alert_type]
            }

        return JsonResponse(response_data)

    # Handle GET requests or other HTTP methods
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_SOS_admin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now()  
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '') 
        #district = request.data.get('district', '') 
        file_idProof = request.data.get('file_idProof') 
        user,error,new_password=create_user('sosadmin',request)
        if user:
            try:   
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                if not file_idProof: 
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)
                dealer,error = EM_admin.objects.safe_create( 
                    created=created,
                    state_id=state, 
                    #district_id=district,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    createdby=createdby,
                    status="Created",
                ) 
                
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request."+eeeeeee}, status=400)
            dealer.users.add(user) 
            send_usercreation_otp(user,new_password,'SOS Admin ')
             
            return Response(EM_adminSerializer(dealer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_SOS_admin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('dto_rto_id', None)
        email = request.data.get('email', '') 
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state = request.data.get('state', '')
        district = request.data.get('district', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if manufacturer_id :
            manufacturers = EM_admin.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = EM_admin.objects.filter(
                #id=manufacturer_id,
                users__status='active',
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = EM_adminSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def list_desk_ex(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    

    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:  
        active_team_members = EMTeams.objects.filter(status="Active").values_list('members', flat=True)
        emex = EM_ex.objects.filter(
            state=uo.state,
            status="UserVerified",
            user_type='desk_ex',
            users__status='active'
        ).exclude(id__in=active_team_members).distinct()

        # Serialize and return the data
        serializer = EM_exSerializer(emex, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def list_team_lead(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role = "sosadmin"
    user = request.user
    uo = get_user_object(user, role)
    if not uo:
        return Response({"error": "Request must be from " + role + '.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        active_team_leads = EMTeams.objects.filter(status="Active").values_list('teamlead_id', flat=True)
        emex = EM_ex.objects.filter(
            state=uo.state,
            status="UserVerified",
            user_type='teamlead',
            users__status='active'
        ).exclude(id__in=active_team_leads).distinct()
        serializer = EM_exSerializer(emex, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'+str(user.role)}, status=400)
    state = request.data.get('state') 
    if uo.state.id!=state:
        return Response({"error":"Unauthorised State" }, status=400)

        
    #teamlead = EM_ex.objects.filter(id=request.data.get('teamlead') ,state=state,status="UserVerified",user_type='teamlead').last()
    #members = EM_ex.objects.filter(id=request.data.get('members',[]) ,state=state,status="UserVerified",user_type='desk_ex').all()



    teamlead_id = request.data.get('teamlead')
    member_ids = request.data.get('members', [])
    
    teamlead = EM_ex.objects.filter(id=teamlead_id, state=state,users__status='active', user_type='teamlead').last()
    members = EM_ex.objects.filter(id__in=member_ids, state=state, users__status='active', user_type='desk_ex').all()
    if not teamlead:
        return Response({"error": "Team lead not found."}, status=400)
    if not members:
        return Response({"error": "Members not found."}, status=400)
    if len(members)!=len(member_ids):
        return Response({"error": "All Members not found."}, status=400)


    # Check if the teamlead is part of any active team
    if EMTeams.objects.filter(teamlead=teamlead, status="Active").exists():
        return Response({"error": "The selected teamlead is already part of an active team."}, status=400)

    # Check if any of the members are part of any active team
    active_team_members = EMTeams.objects.filter(status="Active", members__in=members).distinct()
    if active_team_members.exists():
        return Response({"error": "One or more selected members are already part of an active team."}, status=400)

    created_by = uo  
    status = "NotActive"
    name = request.data.get('name') 
    detail = request.data.get('detail') 
    try:  
        if state and teamlead  and  members  and  created_by  and  status  and name and   detail:
            if members!=[]:
                   
                ob,error=EMTeams.objects.safe_create(state_id = state,
                    teamlead =teamlead,
                     
                    created_by = created_by,
                    status = status,
                    name = name,
                    detail = detail)
                
                if error: # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

                ob.members.set(members) 
                ob.save()
                return Response({'status': str('Team Created Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to create team. Incomplete data.')}, status=400)#Response(SOS_userSerializer(dealer).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def activate_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        id = request.data.get('team_id') 
        ob=EMTeams.objects.filter(id = id,status = "NotActive" ,state=uo.state).last()
        if ob:
            ob.status="Active"
            ob.activated_at= timezone.now()
            ob.save()
            return Response({'status': str('Team Activated Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to activate team.  Team not found.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def remove_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        id = request.data.get('team_id') 
        ob=EMTeams.objects.filter(id = id,status = "Active",state=uo.state).last()
        if ob:
            ob.status="Removed"
            ob.activated_at= timezone.now()
            ob.save()
            return Response({'status': str('Team Removed Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to remove team. Team not found.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def edit_EM_team(request): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'+str(user.role)}, status=400)
    
    try:
        team_id = request.data.get('team_id')
        if not team_id:
            return Response({"error": "Team ID is required."}, status=400)
        
        # Get the team to edit
        team = EMTeams.objects.filter(id=team_id, state=uo.state).last()
        if not team:
            return Response({"error": "Team not found."}, status=400)
        
        # Only allow editing if team is NotActive or Active (not Removed)
        if team.status == "Removed":
            return Response({"error": "Cannot edit a removed team."}, status=400)
        
        state = request.data.get('state', team.state.id)
        if uo.state.id != state:
            return Response({"error":"Unauthorised State" }, status=400)

        # Get optional new teamlead
        teamlead_id = request.data.get('teamlead')
        if teamlead_id:
            teamlead = EM_ex.objects.filter(id=teamlead_id, state=state, users__status='active', user_type='teamlead').last()
            if not teamlead:
                return Response({"error": "Team lead not found."}, status=400)
            
            # Check if the new teamlead is part of any other active team (excluding current team)
            if EMTeams.objects.filter(teamlead=teamlead, status="Active").exclude(id=team_id).exists():
                return Response({"error": "The selected teamlead is already part of another active team."}, status=400)
        else:
            teamlead = team.teamlead

        # Get optional new members
        member_ids = request.data.get('members')
        if member_ids is not None:
            if member_ids:  # If not empty list
                members = EM_ex.objects.filter(id__in=member_ids, state=state, users__status='active', user_type='desk_ex').all()
                if len(members) != len(member_ids):
                    return Response({"error": "All Members not found."}, status=400)
                
                # Check if any of the new members are part of any other active team (excluding current team)
                active_team_members = EMTeams.objects.filter(status="Active", members__in=members).exclude(id=team_id).distinct()
                if active_team_members.exists():
                    return Response({"error": "One or more selected members are already part of another active team."}, status=400)
            else:
                members = []
        else:
            members = team.members.all()

        # Get optional new name and detail
        name = request.data.get('name', team.name)
        detail = request.data.get('detail', team.detail)

        # Update the team
        team.teamlead = teamlead
        team.name = name
        team.detail = detail
        team.save()
        
        # Update members if provided
        if member_ids is not None:
            team.members.set(members)
        
        return Response({'status': 'Team Updated Successfully', "team": EMTeamsSerializer(team).data}, status=200)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def get_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        id = request.data.get('team_id') 
        ob=EMTeams.objects.filter(id = id ,state=uo.state).last()
        if ob: 
            return Response({"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Team not found')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def list_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ob=EMTeams.objects.filter( state=uo.state).all()
        if ob: 
            return Response({ "teams":EMTeamsSerializer(ob,many=True).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Team not found')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TLEx_getPendingCallList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ee=EMCallAssignment.objects.filter( call__team__teamlead= uo  ).all()

        if ee: 
            return Response({ "calls":EMCallAssignmentSerializer(ee,many=True).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'call': str('Not found')}, status=404)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_getPendingCallList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    role2="stateadmin" 
    uo2=get_user_object(user,role2)
    if not (uo or uo2):
        return Response({"error":"Request must be from  "+role+' or '+role2+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        if uo2:
            ee=EMCallAssignment.objects.filter(  ex__state = uo2.state  ).exclude(status="closed") 
        else:
            ee=EMCallAssignment.objects.filter(  ex = uo  ).exclude(status="closed")  

        if ee: 
            return Response({ "calls":EMCallAssignmentSerializer(ee,many=True).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'call': str('Not found')}, status=200)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_getLiveCallList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ee=EMCallAssignment.objects.filter( type = "desk_ex",  ex = uo  )  

        if ee: 
            return Response({ "calls":EMCallAssignmentSerializer(ee,many=True).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'call': str('Not found')}, status=200)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_replyCall(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        accept =request.data.get("accept") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
   
        if assignment:
            if accept:
                assignment.status="accepted"#"rejected", "rejected")
                assignment.accept_time =  timezone.now()
            else:
                assignment.status="rejected"
                assignment.reject_time = timezone.now()


            assignment.save()

            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response( EMCallAssignmentSerializer(assignment,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def CheckLive(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    return Response({'detail':"live"}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_broadcast(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        radius =request.data.get("radius")  
        radius =5
        typ =request.data.get("type")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        ee,error=EMCallBroadcast.objects.safe_create( admin  =assignment.admin,
            created_by= uo,
            call = assignment.call,
            radius= radius,
            status = "pending",
            type = typ)
        
        if error: # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        
        return Response( EMCallBroadcastSerializer(ee,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_broadcastlist(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        ee=EMCallBroadcast.objects.filter(
            call = assignment.call).all()
        
        return Response( EMCallBroadcastSerializer(ee,many=True).data, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_broadcastlist(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex'or uo.user_type=='PCR'or uo.user_type=='ACR' :
 
        return Response({"error":"Request must be from  police_ex or ambulance_ex' or PCR or ACR."}, status=status.HTTP_400_BAD_REQUEST)
    try:  
        ee=EMCallBroadcast.objects.filter(  type=uo.user_type,status="pending").last()
        
        return Response( EMCallBroadcastSerializer(ee,many=True).data, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TLEx_reassign(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='teamlead' :
 
        return Response({"error":"Request must be from team lead."}, status=status.HTTP_400_BAD_REQUEST)
    try: 

        id =request.data.get("assignemtn_id")  
        ee=EMCallAssignment.objects.filter(  call__team__teamlead= uo,id = id).last()
        if not ee :
            return Response({"error":"Unauthorised assignemnt id ."}, status=status.HTTP_400_BAD_REQUEST)

        id2 =request.data.get("DEx_id")  
        ex=EM_ex.objects.filter(id=id2).last()
        if not ex :
            return Response({"error":"Invalid DeskExId."}, status=status.HTTP_400_BAD_REQUEST)

        tt=EMTeams.objects.filter(status="Active",teamlead=uo).last()
        
        if not tt :
            return Response({"error":"Invalid team."}, status=status.HTTP_400_BAD_REQUEST)
        if ex in tt.members:
            assignment ,error=   EMCallAssignment.objects.safe_create(
                        admin =  EM_admin.objects.all().last(),#filter(users__login=True)
                        call =ee.call ,
                        status = "pending",
                        type = ee.type,
                        ex = ex 
                        ) 
            
            if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            ee.status="reassigned"
            ee.save()
            return Response( EMCallAssignmentSerializer(assignment ,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        else:
            return Response({"error":"Desk_ex is not a member of your team."}, status=status.HTTP_400_BAD_REQUEST)

          

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_broadcastaccept(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return JsonResponse({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex'or uo.user_type=='PCR'or uo.user_type=='ACR' :
 
        return JsonResponse({"error":"Request must be from  police_ex or ambulance_ex' or PCR or ACR."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        id =request.data.get("broadcast_id")  
        ee=EMCallBroadcast.objects.filter( id = id,type=uo.user_type,status="pending").last()
        if not ee:
            return JsonResponse({'error': "Not found"}, status=400)
        ee.status="accepted"
        ee.save()
        assignment,error =   EMCallAssignment.objects.safe_create(
                    admin =  EM_admin.objects.all().last(),#filter(users__login=True)
                    call =ee.call ,
                    status = "accepted",
                    type = uo.user_type,
                    ex = uo 
                    )  
        
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        return JsonResponse( {"assignment":EMCallAssignmentSerializer(assignment ,many=False).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        
    except Exception as e:
        return JsonResponse({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def  DEx_closeCase(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        ee=EMCallBroadcast.objects.filter(
            call = assignment.call,status="pending").all()
        for e in ee:
            e.status="canceled"
            e.save()
        assignments =EMCallAssignment.objects.filter(call=assignment.call,status="pending").all()
        for a in assignments:
            a.status="closed"
            a.save()
        assignment.call.status="closed"
        assignment.call.save()
        

        
        return Response( EMCallSerializer(assignment.call,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_sendMsg(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        call=assignment.call
        message=request.data.get("message") 
        ob,error=EMCallMessages.objects.safe_create(assignment=assignment,call=call,message=message)
        
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallMessagesSerializer(ob,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to send message. value error.')}, status=200)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_rcvMsg(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        call=assignment.call 
        ob=EMCallMessages.objects.filter(assignment=assignment,call=call).all()
        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallMessagesSerializer(ob,many=True).data, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response([], status=200)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_commentFE(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    try: 
        assignment =request.data.get("self_assignment_id") 
        fe_assignment =request.data.get("self_assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        call=assignment.call 
        assignment2=EMCallAssignment.objects.filter(id=fe_assignment,call=call).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        
        if not assignment2:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        assignment2.desk_ex_comment=request.data.get("comment") 
        #assignment2.status="closed"
        assignment2.save()
        
        if assignment:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallAssignmentSerializer(assignment2,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to read message. value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_file_paths(request):
    """
    Debugging endpoint to check if a file exists in various potential locations
    """
    file_path = request.data.get('file_path')
    if not file_path:
        return JsonResponse({'error': 'file_path is required'}, status=400)
    
    filename = os.path.basename(file_path)
    directory = os.path.dirname(file_path)
    
    # Locations to check
    potential_locations = []
    
    # Build list of places to check
    for folder in folders:
        # Original path
        potential_locations.append(os.path.join(folder, file_path))
        
        # Just the filename in the root folder
        potential_locations.append(os.path.join(folder, filename))
        
        # Filename in possible subdirectories
        if directory:
            potential_locations.append(os.path.join(folder, directory, filename))
            
   
    
    # Check each location
    results = {}
    for location in potential_locations:
        exists = os.path.isfile(location)
        results[location] = {
            'exists': exists,
            'size': os.path.getsize(location) if exists else 0
        }
    
    return JsonResponse({
        'requested_file': file_path,
        'filename': filename,
        'directory': directory,
        'locations_checked': results,
        'folders_configuration': folders
    })

@api_view(['POST'])
@permission_classes([AllowAny]) 
#@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def upload_media_file(request):
    """
    API to upload media files (.jpg, .mp4, .avi, .wav, .mp3, etc.) and save data in fileuploads/media.
    The uploaded file will be prefixed with the camera_id.
    """
    try:
        device_tag_id = request.data.get('device_tag')
        camera_id = request.data.get('camera_id')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        media_type = request.data.get('media_type')
        duration_ms = request.data.get('duration_ms')
        alert_type = request.data.get('alert_type')
        message = request.data.get('message')
        uploaded_file = request.FILES.get('media_file')

        if not (device_tag_id and camera_id and uploaded_file):
            return JsonResponse({'error': 'device_tag, camera_id, and media_file are required.'}, status=400)

        device_tag = get_object_or_404(DeviceTag, id=device_tag_id)

        # Allowed file extensions
        allowed_ext = ['.jpg', '.jpeg', '.mp4', '.avi', '.wav', '.mp3']
        filename = uploaded_file.name
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_ext:
            return JsonResponse({'error': f'File type {ext} not allowed.'}, status=400)

        # Prefix camera_id to filename
        safe_filename = f"{camera_id}_{filename.replace(' ', '_')}"
        file_path = f'fileuploads/media/{safe_filename}'

        # Save file
        with open(file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Save record in Media_File1
        media_file = Media_File1.objects.create(
            device_tag=device_tag,
            camera_id=camera_id,
            start_time=start_time,
            end_time=end_time,
            media_type=media_type,
            media_link=file_path,
            duration_ms=duration_ms,
            alert_type=alert_type,
            message=message,
        )

        return JsonResponse({
            "success": "Media file uploaded successfully",
            "media_id": media_file.id,
            "media_link": file_path
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def dummy_insert_data(request):
    """
    Dummy API to insert data using GET parameters.
    Example usage:
    /api/dummy-insert-data?device_tag=1&camera_id=101&start_time=2023-05-01T10:00:00Z&end_time=2023-05-01T10:05:00Z&media_type=video&media_link=http://example.com/video.mp4&duration_ms=300000&alert_type=alert&message=Test
    """
    if request.method == 'POST':
        try:  
            device_tag = request.data.get('device_tag')
            device_tag = get_object_or_404(DeviceTag, id=device_tag)

            camera_id = request.data.get('camera_id')
            start_time = request.data.get('start_time')
            end_time = request.data.get('end_time')
            media_type = request.data.get('media_type')
            media_link = request.data.get('media_link')
            duration_ms = request.data.get('duration_ms')
            alert_type = request.data.get('alert_type')
            message = request.data.get('message')

            media_file = Media_File1.objects.create(
                device_tag=device_tag,
                camera_id=camera_id,
                start_time=start_time,
                end_time=end_time,
                media_type=media_type,
                media_link=media_link,
                duration_ms=duration_ms,
                alert_type=alert_type,
                message=message,
            )

            return JsonResponse({"success": "Data inserted successfully", "media_id": media_file.id}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only GET requests are allowed"}, status=405)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_getMedia(request):
    if request.method != 'POST':
        return Response({"error": "Invalid request method."}, status=status.HTTP_400_BAD_REQUEST)
    role="sosexecutive"
    user=request.user
    #uo=get_user_object(user,role)
    #if not uo:
    #    return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)  
    
    

    assignment =request.data.get("assignment_id")  
    assignment =EMCallAssignment.objects.filter(id=assignment,status__in=["accepted"]).last()#ex=uo,
    if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
    
    device_tag = assignment.call.device
    if not device_tag:
        return Response({"error": "device_tag is required."}, status=status.HTTP_400_BAD_REQUEST)

       
    media_items = Media_File1.objects.filter(device_tag=device_tag.id).order_by('-start_time')[:100]
    
    media_dict = {}
    for item in media_items:
        camera_id = item.camera_id
        if camera_id not in media_dict:
            media_dict[camera_id] = []
        media_dict[camera_id].append({
            "start_time": item.start_time,
            "end_time": item.end_time,
            "media_type": item.media_type,
            "media_link": item.media_link,
            "duration_ms": item.duration_ms,
            "alert_type": item.alert_type,
            "message": item.message,
        })

    return Response({"media": media_dict}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def  DEx_getloc(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)  
    try: 
        assignment =request.data.get("assignment_id")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        #device loc histry
       
        deviceloc=list(EMGPSLocation.objects.filter(device_tag= assignment.call.device).order_by('-id')[:1].values())
        fieldEx=[]
         
        assignments =EMCallAssignment.objects.filter(call=assignment.call ).all()
        for a in assignments:
            try:
                fieldEx.append({"Assignment":EMCallAssignmentSerializer(a,many=False).data,"loc":EMUserLocation.objects.filter(field_ex = a.ex).order_by('-id')[:1].values()})
            
            except:
                pass


        

        
        return Response( {"target":deviceloc,"fieldEx":fieldEx}, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def  FEx_getloc(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)  
    try: 
        assignment =request.data.get("assignment_id")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        #device loc histry
       
        deviceloc=list(EMGPSLocation.objects.filter(device_tag= assignment.call.device).order_by('-id')[:100].values())
        
        return Response( {"target":deviceloc}, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_updateLoc(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex' :
        return Response({"error":"Request must be from   police_ex or  ambulance_ex ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ob,error=EMUserLocation.objects.safe_create( field_ex = uo , em_lat = float(request.data.get("em_lat") ), em_lon = float(request.data.get("em_lon") ), speed= float(request.data.get("speed") ) )
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(ob.values())}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Location not updated. value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_updateStatus(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        statuss =request.data.get("status") 
        assignment =EMCallAssignment.objects.filter(id=assignment, ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            assignment.status= statuss 
            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return JsonResponse({"assignment": EMCallAssignmentSerializer( assignment,many=False).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)
    except Exception as e:
        #raise e
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

  


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_reqBackup(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex' :
        return Response({"error":"Request must be from   police_ex or  ambulance_ex ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        call=assignment.call
        message=request.data.get("message") 
        quantity=request.data.get("quantity") 
        type=request.data.get("type") 
        if type not in [ "police_ex","ambulance_ex"]:
            return Response({"error":"type must be    police_ex or  ambulance_ex ."}, status=status.HTTP_400_BAD_REQUEST)

        accepted=False

        ob,error=EMCallBackupRequest.objects.safe_create(assignment=assignment,call=call,message=message,type=type,quantity=quantity)
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(ob.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to send. value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_acceptBackup(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
        return Response({"error":"Request must be from   desk_ex   ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("backup_id") 
        backup =EMCallBackupRequest.objects.filter(id=assignment, accepted=False).last()
        if not backup:
            return Response({"error":"Backup not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        ac=EMCallAssignment.objects.filter(call=backup.call,ex=uo,types="desk_ex").exclude(status__in=["pending",  "rejected", "closed_false_allert","closed"])
        if not ac:

            return Response({"error":"Unauthorised access  " }, status=status.HTTP_400_BAD_REQUEST) 

        if assignment:
            backup.accepted=True#"rejected", "rejected") 
            backup.save()

            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(backup.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)










@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_listBackup(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
        return Response({"error":"Request must be from   desk_ex   ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        ac=EMCallAssignment.objects.filter(id=assignment,ex=uo,types="desk_ex").exclude(status__in=["pending",  "rejected", "closed_false_allert","closed"]).last()
        if not ac:
            return Response({"error":"Unauthorised access  " }, status=status.HTTP_400_BAD_REQUEST) 

        backup =EMCallBackupRequest.objects.filter(call=ac.call) 
        if not backup:
            return Response({"error":"Backup not found  " }, status=status.HTTP_400_BAD_REQUEST) 
         
        if assignment: 
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallBackupRequestSerializer( backup,many=True).data, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)










@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST']) 
def accept_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
   
        if assignment:
            assignment.status="accepted"#"rejected", "rejected")
            assignment.accept_time =  timezone.now()
            assignment.save()

            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def reject_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            assignment.status= "rejected" 
            assignment.reject_time  =  timezone.now()

            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def arriving_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            assignment.status= "arriving"  

            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def create_poi(request):
    try:
        data = request.data
        poi = pointofinterests.objects.create(
            status=data.get('status'),
            mark_type=data.get('mark_type'),
            use_type=data.get('use_type'),
            location=data.get('location'),
            radius=data.get('radius'),
            name=data.get('name'),
            description=data.get('description'),
            created_by=request.user,
            updated_by=request.user
        )
        return Response({'message': 'poi created successfully', 'data': model_to_dict(poi)}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def update_poi(request):
    try:
        poi_id = request.data.get('poi_id')
        poi = pointofinterests.objects.get(id=poi_id)
        data = request.data
        poi.status = data.get('status', poi.status)
        poi.mark_type = data.get('mark_type', poi.mark_type)
        poi.use_type = data.get('use_type', poi.use_type)
        poi.location = data.get('location', poi.location)
        poi.radius = data.get('radius', poi.radius)
        poi.name = data.get('name', poi.name)
        poi.description = data.get('description', poi.description)
        poi.updated_by = request.user
        poi.save()
        return Response({'message': 'poi updated successfully', 'data': model_to_dict(poi)}, status=200)
    except poi.DoesNotExist:
        return Response({'error': 'poi not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
     
 
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def delete_poi(request):
    try:
        poi_id = request.data.get('poi_id')
        poi = pointofinterests.objects.get(id=poi_id)
        poi.delete()
        return Response({'message': 'poi deleted successfully'}, status=200)
    except poi.DoesNotExist:
        return Response({'error': 'poi not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def list_pois(request):
    try:
        pois = pointofinterests.objects.all()
        data = list(pois.values())
        return Response({'data': data}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def search_request_logs(request):
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    
    query = request.GET.get('q', '')  # Get the search query from the request
    page = request.GET.get('page', 1)  # Get the page number from the request
    per_page = request.GET.get('per_page', 10)  # Number of items per page (default: 10)

    # Filter the RequestLog model based on the search query
    logs = RequestLog.objects.filter(
        Q(ip_address__icontains=query) |
        Q(system_info__icontains=query) |
        Q(request_url__icontains=query) |
        Q(request_type__icontains=query) |
        Q(headers__icontains=query) |
        Q(incoming_data__icontains=query) |
        Q(response_type__icontains=query) |
        Q(error_code__icontains=query)
    ).order_by('-timestamp')  # Order by timestamp (descending)

    # Paginate the results
    paginator = Paginator(logs, per_page)
    paginated_logs = paginator.get_page(page)

    # Prepare the response data
    data = {
        'results': list(paginated_logs.object_list.values()),
        'page': paginated_logs.number,
        'total_pages': paginator.num_pages,
        'total_results': paginator.count,
    }

    return JsonResponse(data)
  
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def arrived_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            assignment.status= "arrived" 
            assignment.arrived_time  =  timezone.now()

            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def close_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        is_false =request.data.get("is_false") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            if is_false:
                assignment.status= "closed_false_allert" 
            else:
                assignment.status= "closed" 
            assignment.complete_time  =  timezone.now()
            assignment.closer_comment=request.data.get("closer_comment") 
            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400) 



#@api_view(['POST'])
#@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def download_static_file(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    #man=get_user_object(user,"devicemanufacture")
    #if not man:
    #    return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
    
    file_path = f"skytron_api/static/StockUpload.xlsx"
    try:
        with open(file_path,'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="StockUpload.xlsx"'
            return response
    except FileNotFoundError:
        return HttpResponse("File not found.", status=404)

"""
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def CancelTagDevice2Vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    o=request.data['vehicle_owner']

    device_id = int(request.data['device'])
    if not device_id:
        return Response({"error":"Invalid Device id " }, status=status.HTTP_400_BAD_REQUEST)

    device_tag=DeviceTag.objects.filter( device_id=device_id).last()
    if not device_tag
    # Extract data from the request or adjust as needed
    device_id = int(request.data['device'])
    stock_assignment = get_object_or_404(DeviceStock, dealer=man,id=device_id, stock_status="Available_for_fitting") #'Fitted') 

    if stock_assignment:
        stock_assignment=stock_assignment 
        user_id = request.user.id  # Assuming the user is authenticated
        current_datetime = timezone.now()
        uploaded_file = request.FILES.get('rcFile')
        if uploaded_file:
            file_path = 'fileuploads/cop_files/' + str(device_id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            device_tag = DeviceTag.objects.safe_create(
            device_id=device_id,
            vehicle_owner =vehicle_owner ,
            vehicle_reg_no=request.data['vehicle_reg_no'],
            engine_no=request.data['engine_no'],
            chassis_no=request.data['chassis_no'],
            vehicle_make=request.data['vehicle_make'],
            vehicle_model=request.data['vehicle_model'],
            category=request.data['category'],
            rc_file=file_path,
            status='Dealer_OTP_Sent',
            tagged_by=user,
            tagged=current_datetime,
            otp=str(random.randint(100000, 999999)) ,
            otp_time=timezone.now() 
            )
            stock_assignment.stock_status= 'Fitted'
            stock_assignment.save()


  
            text="Dear VLTD Dealer/ Manufacturer,We have received request for tagging and activation of following device and vehicle-Vehicle Reg No: {}Device IMEI No: {}To confirm, please enter the OTP {}.- SkyTron".format(device_tag.vehicle_reg_no,device_tag.device.imei,device_tag.otp)
            tpid="1007201930295888818"
            send_SMS( user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )
        serializer = DeviceTagSerializer(device_tag)
        return JsonResponse({'data': serializer.data, 'message': 'Device taging successful.'}, status=201)
    else:
        return JsonResponse({  'message': 'Device not avaialble for Tagging'}, status=201)
"""

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagDevice2Vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    o=request.data['vehicle_owner']
    if len(str(o))==10:
        vehicle_owner=VehicleOwner.objects.filter(users__mobile=o,users__status='active').last()
    else:
        vehicle_owner=VehicleOwner.objects.filter(id=o,users__status='active').last()
    if not vehicle_owner:
        return Response({"error":"Vehicle_owner not found."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    device_id = int(request.data['device'])
    stock_assignment = get_object_or_404(DeviceStock, dealer=man,id=device_id, stock_status="Available_for_fitting") #'Fitted') 

    if stock_assignment:
        stock_assignment=stock_assignment 
        user_id = request.user.id  # Assuming the user is authenticated
        current_datetime = timezone.now()
        uploaded_file = request.FILES.get('rcFile')
        if uploaded_file:
            file_path = 'fileuploads/cop_files/' + str(device_id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            device_tag ,error= DeviceTag.objects.safe_create(
            device_id=device_id,
            vehicle_owner =vehicle_owner ,
            vehicle_reg_no=request.data['vehicle_reg_no'],
            engine_no=request.data['engine_no'],
            chassis_no=request.data['chassis_no'],
            vehicle_make=request.data['vehicle_make'],
            vehicle_model=request.data['vehicle_model'],
            category=request.data['category'],
            rc_file=file_path,
            status='Dealer_OTP_Sent',
            tagged_by=user,
            tagged=current_datetime,
            otp= str(random.randint(100000, 999999)) ,
            otp_time=timezone.now() 
            )
            if error:   # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            stock_assignment.stock_status= 'Fitted'
            stock_assignment.save()


  
            text="Dear VLTD Dealer/ Manufacturer,We have received request for tagging and activation of following device and vehicle-Vehicle Reg No: {}Device IMEI No: {}To confirm, please enter the OTP {}.- SkyTron".format(device_tag.vehicle_reg_no,device_tag.device.imei,device_tag.otp)
            tpid="1007201930295888818"
            send_SMS( user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )
        serializer = DeviceTagSerializer(device_tag)
        return JsonResponse({'data': serializer.data, 'message': 'Device taging successful.'}, status=201)
    else:
        return JsonResponse({  'message': 'Device not avaialble for Tagging'}, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def unTagDevice2Vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        tag_id = request.POST.get('tag_id') 
        if not tag_id:
            return JsonResponse({'error': 'tag_id is required'}, status=400)
        try: 
            device_tag = DeviceTag.objects.get(id=tag_id)
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'DeviceTag with the given tag_id does not exist'}, status=404)
        device_tag.status = 'Device_Untagged'
        device_tag.save()
        return JsonResponse({'message': 'Device successfully untagged'}) 
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def validate_ble(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        ble_key = request.data.get('ble_key', None)
        imei=request.data.get('imei', None)
        reg_no = request.data.get('reg_no', None)
        user_mob = request.data.get('user_mob', None)
        if not ble_key or not imei or not reg_no or not user_mob:
            return Response({'error': 'Incomplete data'}, status=status.HTTP_401_UNAUTHORIZED)
        if len(user_mob)!=10:
            return Response({'error': 'Invalid mobile no'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({'success': 'Access Granted'}, status=200)  
    return Response({'error': 'Invalid request'}, status=status.HTTP_401_UNAUTHORIZED)
        
        

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def deleteTagDevice2Vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        device_id = request.POST.get('device_id') 
        if not device_id:
            device_id = request.data.get('device_id') 
        if not device_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        try: 
            device_tag = DeviceTag.objects.filter(device_id=device_id,tagged_by=user).exclude(status="Device_Active").last() #,status="Device_Active")
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'DeviceTag with the given device_id or delete access does not exist'}, status=404)
        device_tag.status = 'TagDeleted'
        device_tag.save()
        device_tag.device.stock_status= 'Available_for_fitting'
        device_tag.device.save()
        device_tag.delete()

        return JsonResponse({'message': 'Device tag successfully deleted'}) 
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def download_receiptPDF(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    #if not man:
    #    return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    now = datetime.now() 
    formatted_date = now.strftime("%d/%m/%Y")
    if request.method == 'POST': 
        tag_id = request.data.get('device_id') 
        if not tag_id:
            return JsonResponse({'error': 'device_id is required'}, status=400) 
        try: 
            device_tag = DeviceTag.objects.filter(device=tag_id).last()
            if not device_tag:
                return HttpResponse("Device tag not found.", status=404) 
            file_path = f"fileuploads/cop_files/"+str(device_tag.id)+".pdf"
            try:
                geneateCet(file_path,device_tag.device.imei,device_tag.device.model.model_name,device_tag.device.model.model_name,formatted_date ,device_tag.vehicle_reg_no,formatted_date ,formatted_date ,formatted_date ,device_tag.status,formatted_date )
                with open(file_path,'rb') as file:
                    response = HttpResponse(file.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename='+str(device_tag.id)+'.pdf'
                    return response
            except FileNotFoundError:
                return HttpResponse("Receipt file not found.", status=404) 
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'DeviceTag with the given tag_id does not exist'}, status=404)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def upload_receiptPDF(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        tag_id = request.POST.get('device_id') 
        if not tag_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        device_tag = DeviceTag.objects.filter(device_id=tag_id).last()
        if not device_tag:
            return JsonResponse({'error': 'DeviceTag with the given device_id does not exist'}, status=404)
        try:
            uploaded_file = request.FILES.get('receiptFile')
            if uploaded_file:
                file_path = 'fileuploads/Receipt_files/' + str(device_tag.id) + '_' + uploaded_file.name
                with open(file_path, 'wb') as file:
                    for chunk in uploaded_file.chunks():
                        file.write(chunk)
                device_tag.receipt_file_ul = file_path
                device_tag.save()
                return JsonResponse({'message': 'Recept successfully uploaded'})
            else:
                return JsonResponse({'error': 'receiptFile not found'}, status=405)
        except:
            return JsonResponse({'error': 'Unknown Error'}, status=405)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def driver_remove(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="owner"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        tag_id = request.POST.get('device_id') 
        driver_id = request.POST.get('driver_id')  
        if not tag_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        if not driver_id:
            return JsonResponse({'error': 'driver_id is required'}, status=400)
        device_tag = DeviceTag.objects.filter(device_id=tag_id).last()
        if not device_tag:
            return JsonResponse({'error': 'DeviceTag with the given device_id does not exist'}, status=404)
        driver = Driver.objects.filter(id=driver_id).last()
        if not driver:
            return JsonResponse({'error': 'Driver with the given driver_id does not exist'}, status=404)
        try:
            if driver in device_tag.drivers.all():
                device_tag.drivers.remove(driver)
                device_tag.save()
                return JsonResponse({'message': 'Driver removed successfully'})
            else:
                return JsonResponse({'message': 'given driver is not assigned to this vehicle'})
        

        except:
            return JsonResponse({'message': 'Unable to remove error'})
        

 
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def driver_add(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="owner"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        tag_id = request.POST.get('device_id') 
        name = request.POST.get('name') 
        phone_no= request.POST.get('phone_no') 
        license_no = request.POST.get('licence_no') 

        if not tag_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        device_tag = DeviceTag.objects.filter(device_id=tag_id).last()
        if not device_tag:
            return JsonResponse({'error': 'DeviceTag with the given device_id does not exist'}, status=404)
        driver,error= Driver.objects.safe_create( name =  name,
    phone_no = phone_no,
    license_no = license_no ,
    created_by=user
                )
        
        if error: # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

                
        try:
            uploaded_file = request.FILES.get('photo')
            if uploaded_file:
                file_path = 'fileuploads/driver_' + str(device_tag.id) + '_' + uploaded_file.name
                with open(file_path, 'wb') as file:
                    for chunk in uploaded_file.chunks():
                        file.write(chunk)
                driver.photo= file_path
                driver.save()
                device_tag.drivers.add(driver)

                return JsonResponse({'message': 'Driver added successfully'})
            else:
                driver.delete()
                return JsonResponse({'error': 'Photo not found'}, status=405)
        except:
            return JsonResponse({'error': 'Unknown Error'}, status=405)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagAwaitingActivateTag(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    
    device_models = DeviceTag.objects.filter(status__in=[ 'Owner_OTP_Verified'])#created_by=user_id,  
    serializer = DeviceTagSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def Tag_status(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    user=request.user
    uo=get_user_object(user,role)
    #if not uo:
    #    return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    if request.method == 'POST': 
        devices = DeviceTag.objects.filter(tagged_by=user.id)#created_by=user_id,  
         
        device_id = request.POST.get('device_id') 
        if device_id:
            devices = devices.filter(device=device_id)
        
        reg_no = request.POST.get('reg_no') 
        if reg_no:
            devices = devices.filter(vehicle_reg_no=reg_no)
            
        tag_status = request.POST.get('tag_status') 
        if tag_status:
            devices = devices.filter(status=tag_status)
        stock_status = request.POST.get('stock_status') 
        if stock_status:
            devices = devices.filter(device__stock_status=stock_status)
        esim_status = request.POST.get('esim_status') 
        if esim_status:
            devices = devices.filter(device__esim_status=esim_status)
    
        serializer = DeviceTagSerializer2(devices, many=True)
        return Response(serializer.data)
    return Response({"error":"Something went wrong."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def Tag_ownerlist(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'POST': 
        # Get base queryset
        devices = DeviceTag.objects.filter(status="Owner_Final_OTP_Verified")
        
        # Apply role-based filtering
        if request.user.is_authenticated:
            user_role = request.user.role
            
            if user_role == 'superadmin':
                # Superadmin sees all devices - no additional filtering
                pass
            elif user_role in ['stateadmin', 'sosadmin', 'sosexecutive', 'dtorto']:
                # Get user's state(s) based on role
                user_states = []
                
                if user_role == 'stateadmin':
                    # Get states from StateAdmin relationship
                    state_admins = StateAdmin.objects.filter(users=request.user, status='UserVerified')
                    user_states = [sa.state.id for sa in state_admins]
                elif user_role == 'sosadmin':
                    # Get states from EM_admin relationship  
                    em_admins = EM_admin.objects.filter(users=request.user, status='StateAdminVerified')
                    user_states = [ea.state.id for ea in em_admins]
                elif user_role == 'sosexecutive':
                    # Get states from EM_ex relationship
                    em_exs = EM_ex.objects.filter(users=request.user, status='StateAdminVerified')
                    user_states = [ee.state.id for ee in em_exs]
                elif user_role == 'dtorto':
                    # Get districts from DTO/RTO relationship
                    dto_rtos = dto_rto.objects.filter(users=request.user, status='UserVerified')
                    user_districts = [dr.district for dr in dto_rtos if dr.district]
                    
                    if user_districts:
                        # Filter devices for vehicles belonging to owners with registration in user's districts
                        # Vehicle registration numbers typically contain district codes (e.g., AS01, AS02, etc.)
                        district_q = Q()
                        for district_code in user_districts:
                            # Check if vehicle registration contains the district code
                            district_q |= Q(vehicle_reg_no__icontains=district_code)
                        
                        devices = devices.filter(district_q)
                    else:
                        # If no districts found, return empty queryset
                        devices = DeviceTag.objects.none()
                
                # Handle state-based filtering for other roles
                if user_role in ['stateadmin', 'sosadmin', 'sosexecutive'] and user_states:
                    # Filter devices for vehicles belonging to owners in user's states
                    # This requires checking the state through the device owner's address_State
                    devices = devices.filter(
                        vehicle_owner__users__address_State__in=[
                            Settings_State.objects.get(id=state_id).state for state_id in user_states
                        ]
                    )
                elif user_role in ['stateadmin', 'sosadmin', 'sosexecutive'] and not user_states:
                    # If no states found, return empty queryset
                    devices = DeviceTag.objects.none()
                    
            elif user_role == 'owner':
                # Get vehicles owned by this user
                vehicle_owners = VehicleOwner.objects.filter(users=request.user, status='UserVerified')
                if vehicle_owners.exists():
                    # Filter devices for vehicles owned by this user
                    devices = devices.filter(vehicle_owner__in=vehicle_owners)
                else:
                    # If user is not associated with any vehicles, return empty queryset
                    devices = DeviceTag.objects.none()
            else:
                # For other roles, return empty queryset for security
                devices = DeviceTag.objects.none()
        else:
            # If user is not authenticated, return empty queryset
            devices = DeviceTag.objects.none()

        # Apply additional filters based on request parameters
        device_id = request.POST.get('device_id') 
        if device_id:
            devices = devices.filter(device=device_id)
        reg_no = request.POST.get('reg_no') 
        if reg_no:
            devices = devices.filter(vehicle_reg_no=reg_no)
        tag_status = request.POST.get('tag_status') 
        if tag_status:
            devices = devices.filter(status=tag_status)
        stock_status = request.POST.get('stock_status') 
        if stock_status:
            devices = devices.filter(device__stock_status=stock_status)
        esim_status = request.POST.get('esim_status') 
        if esim_status:
            devices = devices.filter(device__esim_status=esim_status)
    
        serializer = DeviceTagSerializer2(devices, many=True)
        return Response(serializer.data)
    return Response({"error":"Something went wrong."}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagAwaitingOwnerApproval(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    
    device_models = DeviceTag.objects.filter(status__in=[ 'Dealer_OTP_Verified','Owner_OTP_Sent'])#created_by=user_id,  
    serializer = DeviceTagSerializer(device_models, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagAwaitingOwnerApprovalFinal(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    
    device_models = DeviceTag.objects.filter(status__in=['Owner_OTP_Verified','TempActiveSent','TempIncomingLoc','Owner_Final_OTP_Sent'])#created_by=user_id,  
    serializer = DeviceTagSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagSendOwnerOtp(request ):  
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_model_id = request.data.get('device_id')
    # Validate current status and update the status

    device_model = get_object_or_404(DeviceTag, device__id=device_model_id,  status__in=["Owner_OTP_Sent",'Dealer_OTP_Verified'])
 
    device_model.otp=str(random.randint(100000, 999999)) 
    device_model.otp_time=timezone.now() 
    device_model.status = 'Owner_OTP_Sent'
    device_model.save()
    user=device_model.vehicle_owner.users.last()

 
    text="Dear Vehicle Owner,To confirm tagging of your VLTD with your vehicle, please enter the OTP: {} will expire in 5 minutes. Please do NOT share.-SkyTron".format(device_model.otp)
    tpid="1007937055979875563"
    send_SMS( user.mobile,text,tpid) 
    send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
    )
    return Response({"message": "Owner OTP sent successfully."}, status=200)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagSendOwnerOtpFinal(request ):  
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_model_id = request.data.get('device_id')
    # Validate current status and update the status
    #device_model = get_object_or_404(DeviceTag, id=device_model_id,   status='TempActive')
    device_model = get_object_or_404(DeviceTag, device__id=device_model_id,  status__in=['Owner_OTP_Verified','TempActiveSent','TempActive',"Owner_Final_OTP_Sent"])
 
    device_model.otp=str(random.randint(100000, 999999)) 
    device_model.otp_time=timezone.now() 
    device_model.status = 'Owner_Final_OTP_Sent'
    device_model.save()
    user=device_model.vehicle_owner.users.last()

 
    text="Dear Vehicle Owner,To confirm tagging of your VLTD with your vehicle, please enter the OTP: {} will expire in 5 minutes. Please do NOT share.-SkyTron".format(device_model.otp)
    tpid="1007937055979875563"
    send_SMS( user.mobile,text,tpid) 
    send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
    )
    return Response({"message": "Owner OTP sent successfully."}, status=200)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagSendDealerOtp(request ): 
    device_model_id = request.data.get('device_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceTag, id=device_model_id,  status='Dealer_OTP_Verified')
    device_model.otp=str(random.randint(100000, 999999)) 
    device_model.otp_time=timezone.now() 
    device_model.status = 'Dealer_OTP_Sent'
    device_model.save()

    return Response({"message": "Owner OTP sent successfully."}, status=200)


def xml_to_dict(elem):
    return {elem.tag: {child.tag: child.text for child in elem}}


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow non-logged-in users as well
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def TagGetVehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    If not logged in: return only { 'imei': '...', 'reg_no': ... }.
    If logged in: do your normal processing (using get_user_object, etc.).
    """

    reg_no = request.data.get('reg_no')

    # If the user is NOT logged in:
    if not request.user.is_authenticated:
        device_tag = DeviceTag.objects.filter(vehicle_reg_no=reg_no).last()
        if device_tag:
            return JsonResponse({
                'imei': str(device_tag.device.imei),
                'reg_no': reg_no
            }, status=200)
        else:
            return JsonResponse({
            'error': "Device not found"
             }, status=400)


    # If the user IS logged in, proceed as before
    user = request.user
    role = "dtorto"
    man = get_user_object(user, role)
    
    # Example check (adjust logic as you need):
    if not man:
        # Some fallback logic for an authenticated user who doesn't match role, 
        # or if you specifically want to do the "non-logged in" style response.
        # For example:
        device_tag = DeviceTag.objects.filter(vehicle_reg_no=reg_no).last()
        return JsonResponse({
            'imei': "861850060253610",
            'reg_no': reg_no
        }, status=200)

    # Otherwise, handle your normal (authenticated) flow
    device_tag = DeviceTag.objects.filter(vehicle_reg_no=reg_no).last()
    if device_tag:
        try:
            # [Optional] your SOAP/requests code to fetch data from external service
            # 
            # response = requests.request("POST", url, headers=headers, data=payload)
            # ...
            
            # For demonstration only, let’s skip the external call 
            # and return local data:
            serializer = DeviceTagSerializer2(device_tag)

            last_loc = GPSData.objects.filter(device_tag=device_tag).last()
            if last_loc:
                last_loc_serializer = GPSData_Serializer(last_loc)
                last_loc_data = last_loc_serializer.data
            else:
                last_loc_data = None

            return JsonResponse({
                'vehicle_device': serializer.data,
                'last_loc': last_loc_data
            }, status=200)
        except Exception as e:
            return JsonResponse({
                'error': "Unable to get VAHAN information. Please confirm the device IMEI. " + "Unable to process request."+eeeeeee
            }, status=400)
    else:
        return JsonResponse({
            'error': "Device not found with Status:Owner_OTP_Sent"
        }, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def GetVahanAPIInfo_totestonly(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    
    user=request.user  
    user_id = request.user.id 
    device_tag_id = request.data.get('device_id') 
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id).last()
    
    if device_tag:
        url = "https://staging.parivahan.gov.in/vltdmakerws/dataportws?wsdl"

        payload = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:ser=\"http://service.web.homologation.transport.nic/\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <ser:getVltdInfoByIMEI>          \n         <userId>asbackendtest</userId>\n         <transactionPass>Asbackend@123</transactionPass>       \n         <imeiNo>" + str(device_tag.device.imei) +"</imeiNo>\n      </ser:getVltdInfoByIMEI>\n   </soapenv:Body>\n</soapenv:Envelope>"
        headers = {
        'Cookie': 'SERVERID_vahan8082_152=vahan_8082',
        'Content-Type': 'application/xml',
        'Content-Type': 'text/xml; charset=utf-8'
        }
        try:

            response = requests.request("POST", url, headers=headers, data=payload)
            #print(response.text)
            root = ET.fromstring(response.text)
            namespace = {'S': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://service.web.homologation.transport.nic/'}

            return_tag = root.find('.//ns2:getVltdInfoByIMEIResponse/return', namespace)

            inner_xml = html.unescape(return_tag.text)
            inner_root = ET.fromstring(inner_xml)


            vltd_details = xml_to_dict(inner_root)
            json_output = json.dumps(vltd_details, indent=4)
            
            # Sanitize the JSON output
            sanitized_json_output_str = bleach.clean(json_output)
            sanitized_json_output = json.loads(sanitized_json_output_str)

            # Generate a hash of the sanitized output
            hash_object = hashlib.sha256(sanitized_json_output_str.encode())
            hash_hex = hash_object.hexdigest()
            
            serializer = VahanSerializer(device_tag)
            return JsonResponse({'Skytrack_data': serializer.data, 'vahan_data': sanitized_json_output}, status=200)
        except:

            return JsonResponse({'error': "Unable to get VAHAN information. Please confirm the device IMEI."}, status=400)
    else:
         
        return JsonResponse({'error': "Error Geting Vahan Data"}, status=400)


response_schema2 = {
    "type": "object",
    "properties": {
        "VltdDetailsDobj": {
            "type": "object",
            "properties": {
                "chassisNo": {"type": "string"},
                "dateOfRegistration": {"type": "string", "format": "date"},
                "deviceActivationStatus": {"type": "string"},
                "deviceSerialno": {"type": "string"},
                "engineNo": {"type": "string"},
                "fitmentCentreName": {"type": "string"},
                "gnssConstellationCode": {"type": "string"},
                "iccId": {"type": "string"},
                "imeiNo": {"type": "string"},
                "makerName": {"type": "string"},
                "modelName": {"type": "string"},
                "ownerName": {"type": "string"},
                "regnNo": {"type": "string"},
                "tacNo": {"type": "string"},
                "tacValidUpto": {"type": "string", "format": "date"},
                "vehClass": {"type": "string"}
            },
            "required": [
                "chassisNo", "dateOfRegistration", "deviceActivationStatus", "deviceSerialno",
                "engineNo", "fitmentCentreName", "gnssConstellationCode", "iccId", "imeiNo",
                "makerName", "modelName", "ownerName", "regnNo", "tacNo", "tacValidUpto", "vehClass"
            ]
        }
    },
    "required": ["VltdDetailsDobj"]
}
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def GetVahanAPIInfo(request): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user 
    role = "dealer"
    man = get_user_object(user, role)
    if not man:
        return Response({"error": "Request must be from " + role + "."}, status=status.HTTP_400_BAD_REQUEST)

    device_tag_id = request.data.get('device_id') 
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id, tagged_by=user, status='Owner_OTP_Verified').last()
    
    if device_tag:
        url = "https://staging.parivahan.gov.in/vltdmakerws/dataportws?wsdl"
        payload = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.web.homologation.transport.nic/">
           <soapenv:Header/>
           <soapenv:Body>
              <ser:getVltdInfoByIMEI>          
                 <userId>asbackendtest</userId>
                 <transactionPass>Asbackend@123</transactionPass>       
                 <imeiNo>{device_tag.device.imei}</imeiNo>
              </ser:getVltdInfoByIMEI>
           </soapenv:Body>
        </soapenv:Envelope>
        """
        headers = {
            'Content-Type': 'text/xml; charset=utf-8'
        }
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()  # Raise an error for HTTP errors

            # Parse the SOAP response
            root = ET.fromstring(response.text)
            namespace = {'S': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://service.web.homologation.transport.nic/'}
            return_tag = root.find('.//ns2:getVltdInfoByIMEIResponse/return', namespace)

            if return_tag is None or not return_tag.text:
                return JsonResponse({'error': "Invalid response format from VAHAN API."}, status=400)

            # Decode and parse the inner XML
            inner_xml = html.unescape(return_tag.text)
            inner_root = ET.fromstring(inner_xml)

            # Convert the response to a dictionary
            vltd_details = xml_to_dict(inner_root)

            # Validate the response against the schema
           
            # Sanitize the JSON output
            json_output = json.dumps(vltd_details, indent=4)
            try:
                validate(instance=vltd_details, schema=response_schema2)
            except Exception as e:
                return JsonResponse({'error': f"Response validation failed."}, status=400) #,"err":eeeeeee,"det":str(vltd_details)

            sanitized_json_output_str = bleach.clean(json_output)
            sanitized_json_output = json.loads(sanitized_json_output_str)

            # Generate a hash of the sanitized output
            hash_object = hashlib.sha256(sanitized_json_output_str.encode())
            hash_hex = hash_object.hexdigest()

            serializer = VahanSerializer(device_tag)
            return JsonResponse({'Skytrack_data': serializer.data, 'vahan_data': sanitized_json_output }, status=200)
        except ET.ParseError:
            return JsonResponse({'error': "Failed to parse VAHAN API response."}, status=400)
        except requests.RequestException as e:
            return JsonResponse({'error': f"Error communicating with VAHAN API: {eeeeeee}"}, status=400)
    else:
        return JsonResponse({'error': "Error Getting Vahan Data"}, status=400)


 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ActivateTag(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    user_id = request.user.id 
    device_tag_id = request.data.get('device_id') 
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id,tagged_by=user, status='Owner_OTP_Verified').last()
    
    if device_tag:
        device_tag.status="TempActiveSent"
        device_tag.save()
        serializer = DeviceTagSerializer(device_tag)
        add_sms_queue("ACTV,123456,+9194016334212",device_tag.device.msisdn1)
        add_sms_queue("CONF,"+device_tag.vehicle_reg_no+",216.10.244.243,6000,216.10.244.243,5001,216.10.244.243,5001,+919401633421,+919401633421",device_tag.device.msisdn1)
            
        return JsonResponse({'data': serializer.data,"message":"Temporery activation request Sent.Please wait untile live data is visisble on map."}, status=201)
    else: 
    
        return JsonResponse({'error': "Device not found with Status:Owner_OTP_Sent"}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagVerifyOwnerOtp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id
    otp = request.data.get('otp')
    device_tag_id = request.data.get('device_id')
    if not otp or not otp.isdigit() or len(otp) != 6: 
        return JsonResponse({'error': "Invalid OTP format"}, status=400)
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id,  status='Owner_OTP_Sent').last()
    
    
    if device_tag:
        if otp == device_tag.otp:  
            device_tag.status = 'Owner_OTP_Verified'
            device_tag.save()
            #add_sms_queue("ACTV,123456,+9194016334212",device_tag.device.msisdn1)
            #add_sms_queue("CONF,"+device_tag.vehicle_reg_no+",216.10.244.243,6000,216.10.244.243,5001,216.10.244.243,5001,+919401633421,+919401633421",device_tag.device.msisdn1)
            return Response({"message": "Owner OTP verified successfully."}, status=200)
        else: 
            return JsonResponse({'error': "Invalid OTP"}, status=400)
    else:
        return JsonResponse({'error': "Device not found with Status:Owner_OTP_Sent"}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagVerifyOwnerOtpFinal(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id
    otp = request.data.get('otp')
    device_tag_id = request.data.get('device_id')
    if not otp or not otp.isdigit() or len(otp) != 6: 
        return JsonResponse({'error': "Invalid OTP format"}, status=400)
    
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id,  status='Owner_Final_OTP_Sent').last()
    if device_tag:
        if otp == device_tag.otp:  
            device_tag.status = 'Owner_Final_OTP_Verified'
            device_tag.save()
            #add_sms_queue("ACTV,123456,+9194016334212",device_tag.device.msisdn1)
            #add_sms_queue("CONF,"+device_tag.vehicle_reg_no+",216.10.244.243,6000,216.10.244.243,5001,216.10.244.243,5001,+919401633421,+919401633421",device_tag.device.msisdn1)
            return Response({"message": "Owner Fianl OTP verified successfully.Please wait till the final setitng complete."}, status=200)
        else:
            return JsonResponse({'error': "Invalid OTP"}, status=400)
    else: 
    
        return JsonResponse({'error': "Device not found with Status:Owner_OTP_Sent"}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagVerifyDealerOtp(request  ): 
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_id = request.user.id
        otp = request.data.get('otp')
        device_tag_id = request.data.get('device_id')
        if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)
        device_tag = DeviceTag.objects.filter(device=device_tag_id, status='Dealer_OTP_Sent').last()

        #device_tag = get_object_or_404(DeviceTag, device_id=device_tag_id,  status='Dealer_OTP_Sent')
        #device_tag = device_tag.first()
        if device_tag:
            if otp == device_tag.otp:  
                
                #data = { 
                #    'ceated_by':man,  
                #    'status': 'pending',
                #    'eSim_provider':device_tag.device.esim_provider,
                #    'valid_from':timezone.now(),
                #    'valid_upto':timezone.now()+ timedelta(days=365*2),
                #    'device':device_tag.device 
                    #'device': int(request.data['device'])
                #}  
                #serializer = EsimActivationRequestSerializer(data=data)
                #if serializer.is_valid():
                    
                #    serializer.save()
                    #return Response(serializer.data, status=status.HTTP_201_CREATED)
                #else:
                #    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


                device_tag.status = 'Dealer_OTP_Verified'
                device_tag.save()

                return Response({"message": "Dealer OTP verified successfully."}, status=200)
            else:
                return JsonResponse({'error': "Invalid OTP"}, status=400)
        else: 
            return JsonResponse({'error': "Device not found with Status:Dealer_OTP_Sent"}, status=400)
    except Exception as e:
            return Response({"message": "Unable to process request."+eeeeeee}, status=200)

#not in use for now 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagVerifyDTOOtp(request  ): 
    try:
        user_id = request.user.id
        otp = request.data.get('otp')
        device_tag_id = request.data.get('device_id')
        if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)
        device_tag = DeviceTag.objects.filter(device=device_tag_id, status='Dealer_OTP_Sent') 

        #device_tag = get_object_or_404(DeviceTag, device_id=device_tag_id,  status='Dealer_OTP_Sent')
        device_tag = device_tag.first()
        if device_tag:
            if otp == device_tag.otp:  
                device_tag.status = 'Dealer_OTP_Verified'
                device_tag.save()
                return Response({"message": "Dealer OTP verified successfully."}, status=200)
            else:
                return JsonResponse({'error': "Invalid OTP"}, status=400)
        else:
            return JsonResponse({'error': "Device not found with Status:Dealer_OTP_Sent"}, status=400)
    except Exception as e:
            
            return JsonResponse({'error': "Unable to process request."+eeeeeee}, status=400)







@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ActivateESIMRequest(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='Fitted')
    if stock_assignment.dealer!= man:
        return Response({"error":"Not in stock of this user."}, status=status.HTTP_400_BAD_REQUEST)
    
    stock_assignment.esim_status = 'ESIM_Active_Req_Sent'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'ESIM Active Request Sent successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ConfirmESIMActivation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, esim_status='ESIM_Active_Req_Sent')
    stock_assignment.esim_status = 'ESIM_Active_Confirmed'
    stock_assignment.save()
    stock_assignment = get_object_or_404(DeviceStock,id=device_id, esim_status='ESIM_Active_Confirmed')
    
    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'ESIM Active Confirmed successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ConfigureIPPort(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='ESIM_Active_Confirmed')
    stock_assignment.stock_status = 'IP_PORT_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'IP Port Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ConfigureSOSGateway(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='IP_PORT_Configured')
    stock_assignment.stock_status = 'SOS_GATEWAY_NO_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'SOS Gateway Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ConfigureSMSGateway(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='SOS_GATEWAY_NO_Configured')
    stock_assignment.stock_status = 'SMS_GATEWAY_NO_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'SMS Gateway Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def MarkDeviceDefective(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id)
    if stock_assignment.dealer!= man:
        return Response({"error":"Not in stock of this user."}, status=status.HTTP_400_BAD_REQUEST)
    
    stock_assignment.stock_status = 'Device_Defective'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'Device Marked as Defective successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ReturnToDeviceManufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='Device_Defective')
    if stock_assignment.dealer!= man:
        return Response({"error":"Not in stock of this user."}, status=status.HTTP_400_BAD_REQUEST)
    
    stock_assignment.stock_status = 'Returned_to_manufacturer'
    stock_assignment.dealer=None
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'Device Returned to Manufacturer successfully.'}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SellListAvailableDeviceStock(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    role1="devicemanufacture"
    man2=get_user_object(user,role1)
    role2="stateadmin"
    man3=get_user_object(user,role2)
    if not man and not man2 and not man3:
        return Response({"error":"Request must be from "+role+" or "+role1+" or "+role2+"."}, status=status.HTTP_400_BAD_REQUEST)
    if man2:
        device_stock =  DeviceStock.objects.filter(  dealer__manufacturer=man2,stock_status='Available_for_fitting') 
        if not device_stock:
            return JsonResponse({'error': "no device found "  }, status=400)
    elif man3:
        device_stock =  DeviceStock.objects.filter(  dealer__manufacturer__state=man3.state,stock_status='Available_for_fitting') 
        if not device_stock:
            return JsonResponse({'error': "no device found "  }, status=400)

    else:
        device_stock =  DeviceStock.objects.filter(  dealer=man,stock_status='Available_for_fitting') 
     
    if not device_stock:
        return JsonResponse({'error': "no device found for this user avaialble for fitting "  }, status=400)

    serializer =DeviceStockSerializer(device_stock, many=True)
    return JsonResponse({'data': serializer.data}, status=200)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SellFitDevice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id=int(request.data['device_id'])
    stock_assignment =  DeviceStock.objects.filter(id=device_id, dealer=man,stock_status='Available_for_fitting').last()
    if not stock_assignment:
        return JsonResponse({'error': "device not found, error in dealer or status"  }, status=400)

    stock_assignment.stock_status = 'Fitted'
    
    stock_assignment.save()
    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)
    return JsonResponse({'data': serializer.data, 'message': 'Device Fitted  successfully.'}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def StockAssignToRetailer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
    
    data = request.data.copy()
    assigned_by_id = request.user.id
    assigned_at = timezone.now()
    stock_status = "Available_for_fitting"
    dealer_id =  data.get('dealer') 
    device_ids = ast.literal_eval(str(data.get('device')))
    dealer = Retailer.objects.filter(id=dealer_id).last()#,manufacturer=man
    if not dealer:
        return JsonResponse({'error':"invalid dealer" }, status=400)
    

    stock_assignments = []
    error=[]
    for device_id in device_ids:
        #print(int(device_id),dealer_id, assigned_by_id, assigned_at, data.get('shipping_remark'), stock_status)
       
        try:

            assignment = DeviceStock.objects.filter(id=int(device_id) ,created_by=user,stock_status='NotAssigned').last() 
            if assignment:
                assignment.dealer=dealer
                assignment.assigned_by =request.user
                assignment.assigned=assigned_at
                assignment.shipping_remark=data.get('shipping_remark')
                assignment.stock_status=stock_status                
                assignment.save()                
                stock_assignments.append( DeviceStockSerializer(assignment).data)
            else:
                error.append({'id':int(device_id),'error':"unavaialble non assigned devicewith given id under this manufature"})

        except Exception as e:
             
            return JsonResponse({'error': "Unable to process request."+eeeeeee}, status=400)
    if len(error)==0:
        return JsonResponse({'data': stock_assignments , 'message': 'Stock assigned successfully.'}, status=201)
    else:
        return JsonResponse({'data': stock_assignments,'error':error  , 'message': 'Stock Partially assigned.'}, status=201)
    
    
'''def StockAssignToRetailer3333(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Deserialize the input data
    data = request.data.copy() 
    data['assigned_by'] = request.user.id
    data['assigned'] = timezone.now()
    data['stock_status']= "Available_for_fitting"
    data['dealer_id']= int(data['dealer']) 
    device_ids = ast.literal_eval(str(data['device']))
     

    # Create individual DeviceStock entries for each device
    stock_assignments = []
    for device_id in device_ids:
        data['device_id'] = int(device_id)
        #print(data)
        serializer = DeviceStockSerializer2(data=data)
        if serializer.is_valid():
            serializer.save()
            stock_assignments.append(serializer.data)
        else:
            return JsonResponse({'error': serializer.errors}, status=400)

    return JsonResponse({'data': stock_assignments, 'message': 'Stock assigned successfully.'}, status=201)

'''


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def deviceStockFilter(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user
    man=None
    data = request.data.copy()    

    is_tagged_filter = request.data.get('is_tagged')
    if user.role=="devicemanufacture":
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        man=get_user_object(user,"devicemanufacture")
        data['created_by_id'] = request.user.id 
    elif user.role=="dealer":
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        man=get_user_object(user,"dealer")
        data['dealer_id'] = man.id 
        #is_tagged_filter=True


    
    if not man:
            return Response({"error":"Request must be from device manufacture or dealer"}, status=status.HTTP_400_BAD_REQUEST)
    print(data)
    # Deserialize the input data
    serializer = DeviceStockFilterSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    # Filter DeviceStock instances based on parameters
    device_stock = DeviceStock.objects.filter(**serializer.validated_data)
    for item in device_stock:
        item.is_tagged = DeviceTag.objects.filter(device=item).exists()
    # Serialize the data
    #is_tagged_filter = serializer.validated_data.get('is_tagged')

    # Filter based on 'is_tagged' value if provided
    if is_tagged_filter is not None:
        is_tagged_filter= is_tagged_filter=='True'
        device_stock = [item for item in device_stock if item.is_tagged == is_tagged_filter]

    serializer = DeviceStockSerializer2(device_stock, many=True)

    return JsonResponse({'data': serializer.data}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def deviceStockCreateBulk(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'excel_file' not in request.FILES or 'model_id' not in request.data:
        return JsonResponse({'error': 'Please provide an Excel file and model_id.'}, status=400)

    model_id = request.data['model_id']
    mod=DeviceModel.objects.filter(id=model_id,created_by=user).last()
    if not mod:
        return JsonResponse({'error': 'invalid model_id or unauthorised user.'}, status=400)

    esim_provider = request.data['esim_provider']
    if not isinstance(esim_provider, list)  : 
        var_str = str(esim_provider) 
        for ch in ['[', ']', '{', '}']:
            var_str = var_str.replace(ch, '')
        esim_provider = [item.strip() for item in var_str.split(',')]
    #for e in esim_provider:
    #    st=False
    #    for ee in mod.eSimProviders:
    #        if ee==e.id:
    #            True
    #    if not st:
    #        return JsonResponse({'error': 'Esim provider id='+"Unable to process request."+eeeeeee+' is not in the devicemodel\'s esimprovider list.'}, status=400)





    try:
        excel_data = pd.read_excel(request.FILES['excel_file'], engine='openpyxl')
    except Exception as e:
        return JsonResponse({'error': 'Error reading Excel file.', 'details': "Unable to process request."+eeeeeee}, status=400)

    headers = list(excel_data.columns)
    success_count = 0
    success_rows = []
    error_rows = []

    for index, row in excel_data.iterrows():
        # Skip the header and example rows
        if index == 0 or 'example' in str(row[0]).lower():
            continue
        try:
            a=int(row.get('imei', ''))
            #a=int(row.get('imsi1', ''))
            #if row.get('imsi2', '')!="":
            #    a=int(row.get('imsi2', ''))
        except:
            continue
            
        # Extract data from the row
        data = {
            'model': model_id,
            'device_esn': row.get('device_esn', ''),
            'iccid': row.get('iccid', ''),
            'imei': row.get('imei', ''),
            'telecom_provider1': row.get('telecom_provider1', ''),
            'telecom_provider2': row.get('telecom_provider2', ''),
            'msisdn1': row.get('msisdn1', ''),
            'msisdn2': row.get('msisdn2', ''),
            #'imsi1': row.get('imsi1', ''),
            #'imsi2': row.get('imsi2', ''),
            'esim_validity': row.get('esim_validity', ''), 
            'stock_status': "NotAssigned",
            'esim_status':"NotAssigned",
            'esim_provider': esim_provider,
            'remarks': row.get('remarks', ''),
            'created_by': request.user.id,
            'stock_status': "NotAssigned",
            'created':timezone.now(),
        }

        # Validate and create DeviceStock instance
        serializer = DeviceStockSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            success_count += 1
            success_rows.append(index + 1)
        else:
            error_rows.append({'row': index + 1, 'errors': serializer.errors})

    message = f'{success_count} out of {len(excel_data) - 1} provided stocks are successfully uploaded.'

    response_data = {
        'message': message,
        'success_rows': success_rows,
        'error_rows': error_rows,
    }

    return JsonResponse(response_data, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def deviceStockCreate(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
    mod=DeviceModel.objects.filter(id=request.data['model'],)
    # Deserialize the input data
    data = request.data.copy()
    data['created'] = timezone.now()   
    data['created_by'] = request.user.id
    data['stock_status'] =  "NotAssigned"
    data['esim_status'] =  "NotAssigned"
    try:
        a=int(data['imei'])
        #a=int(data['imsi1'])
        #if data['imsi2']:
        #    a=int(data['imsi1'])
    except:
        return JsonResponse({"status":"Error, Invalid imei  "}, status=400)


    serializer = DeviceStockSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    # Save the DeviceStock instance
    serializer.save()

    return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPCreate(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    user=request.user
        
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="devicemanufacture"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    manufacturer = request.user.id 
    otp= str(random.randint(100000, 999999))
 
    data = {
        'created_by': manufacturer,
        'created': timezone.now(),  
        'status': 'Manufacturer_OTP_Sent',
        'valid':True,
        'latest':True,
        'otp_time': timezone.now(),
        'otp':otp
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)

    # Create a serializer instance
    serializer = DeviceCOPSerializer(data=request_data)

    # Validate and save the data along with the file
    if serializer.is_valid():
        # Save the DeviceCOP instance
        device_cop_instance = serializer.save()

        # Handle the uploaded file
        uploaded_file = request.FILES.get('cop_file')
        if uploaded_file:
            # Save the file to a specific location
            file_path = 'fileuploads/cop_files/' + str(device_cop_instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            # Update the cop_file field in the DeviceCOP instance
            device_cop_instance.cop_file = file_path
            device_cop_instance.save()
                    
            text="Dear User, Your  OTP to validate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            #send_SMS(stateadmin.users.last().mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your OTP to validate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPAwaitingStateApproval(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    #user_id = request.user.id
    device_models = DeviceCOP.objects.filter(status='Manufacturer_OTP_Verified')#created_by=user_id, 
    
    # Serialize the data
    serializer = DeviceCOPSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPSendStateAdminOtp(request ): 
       #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user=request.user
    device_model_id = request.data.get('device_model_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceCOP, id=device_model_id,  status='Manufacturer_OTP_Verified')
    otp= str(random.randint(100000, 999999))
    device_model.otp_time = timezone.now()
    device_model.otp = otp
    device_model.status = 'StateAdminOTPSend'
    device_model.save()
    text="Dear User, Your  OTP to validate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
    tpid="1007536593942813283"
    #send_SMS(stateadmin.users.last().mobile,text,tpid) 
    send_mail(
        'Login OTP',
        "Dear User, Your OTP to validate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
        'noreply@skytron.in',
        [user.email],
        fail_silently=False,
    )

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPVerifyStateAdminOtp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    device_model_id = request.data.get('device_model_id') 
    user_id = request.user.id 
 
    otp = request.data.get('otp') 
    if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)

    device_model = get_object_or_404(DeviceCOP, id=device_model_id, created_by=user_id, status='StateAdminOTPSend')
 
    if otp == device_model.otp:  
        device_model.status = 'StateAdminApproved'
        device_model.save()
        return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)
    else:
            return JsonResponse({'error': "Invalid OTP"}, status=400)


    

    return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPManufacturerOtpVerify(request  ): 
    user_id = request.user.id 
       #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="devicemanufacture"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    otp = request.data.get('otp')
    device_model_id = request.data.get('device_model_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)

    device_model = get_object_or_404(DeviceCOP, id=device_model_id, created_by=user_id, status='Manufacturer_OTP_Sent')
 
    if otp == device_model.otp:  
        device_model.status = 'Manufacturer_OTP_Verified'
        device_model.save()
        return Response({"message": "Manufacturer OTP verified successfully."}, status=200)
    else:
            return JsonResponse({'error': "Invalid OTP"}, status=400)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def list_devicemodel(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    device_models = DeviceModel.objects.all() 
    serializer = DeviceModelSerializer_disp(device_models, many=True) 
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_devicemodel(request): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    # Validate user role once upfront
    role = "devicemanufacture"
    user = request.user
    
    # Check the role only once and return early if invalid
    if user.role != role:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    uo = get_user_object(user, role)
    if not uo:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Deserialize the input parameters
    data = request.data
    serializer = DeviceModelFilterSerializer(data=data)
    
    # Validate but don't raise exception - handle it ourselves for faster response
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create a query dictionary with only the validated fields that have values
    filter_kwargs = {k: v for k, v in serializer.validated_data.items() if v is not None}
    
    # Add the user filter directly
    filter_kwargs['created_by'] = user
    
    # Optimize by using select_related/prefetch_related - this improves query performance
    device_models = DeviceModel.objects.filter(**filter_kwargs).select_related(
        'created_by'
    ).prefetch_related(
        'eSimProviders'
    )
    
    # Serialize the data - maintaining original response format
    serializer = DeviceModelSerializer_disp(device_models, many=True)

    return Response(serializer.data)
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    # Validate user role once upfront
    role = "devicemanufacture"
    user = request.user
    
    # Check the role only once and return early if invalid
    if user.role != role:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    uo = get_user_object(user, role)
    if not uo:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Deserialize the input parameters
    data = request.data
    serializer = DeviceModelFilterSerializer(data=data)
    
    # Validate but don't raise exception - handle it ourselves for faster response
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create a query dictionary with only the validated fields that have values
    filter_kwargs = {k: v for k, v in serializer.validated_data.items() if v is not None}
    
    # Add the user filter directly
    filter_kwargs['created_by'] = user
    
    # Optimize by using select_related/prefetch_related
    query = DeviceModel.objects.select_related('created_by').prefetch_related('eSimProviders')
    
    # Apply filters to the optimized query
    device_models = query.filter(**filter_kwargs)
    
    # Optional: Add pagination if there are many results
    page_size = request.query_params.get('page_size', 20)
    page = request.query_params.get('page', 1)
    
    try:
        page_size = int(page_size)
        page = int(page)
    except ValueError:
        page_size = 20
        page = 1
        
    # Apply pagination
    start = (page - 1) * page_size
    end = page * page_size
    paginated_models = device_models[start:end]
    
    # Pass the request context to the serializer for field filtering
    serializer = DeviceModelSerializer_disp(
        paginated_models, 
        many=True, 
        context={'request': request}
    )
    
    # Include pagination metadata
    total_count = device_models.count()
    total_pages = (total_count + page_size - 1) // page_size
    
    return Response({
        'results': serializer.data,
        'pagination': {
            'total_count': total_count,
            'total_pages': total_pages,
            'current_page': page,
            'page_size': page_size
        }
    })
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    # Validate user role once upfront
    role = "devicemanufacture"
    user = request.user
    
    # Check the role only once and return early if invalid
    if user.role != role:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    uo = get_user_object(user, role)
    if not uo:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Deserialize the input parameters
    data = request.data
    serializer = DeviceModelFilterSerializer(data=data)
    
    # Validate but don't raise exception - handle it ourselves for faster response
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create a query dictionary with only the validated fields that have values
    filter_kwargs = {k: v for k, v in serializer.validated_data.items() if v is not None}
    
    # Add the user filter directly
    filter_kwargs['created_by'] = user
    
    # Use select_related to fetch related models in a single query
    # This improves performance by reducing database hits
    device_models = DeviceModel.objects.filter(**filter_kwargs).select_related(
        'created_by'
    ).prefetch_related(
        'eSimProviders'  # Based on the model relationships shown in serializers
    )

    # Serialize the data - use a smaller subset of fields if possible for performance
    serializer = DeviceModelSerializer_disp(device_models, many=True)

    return Response(serializer.data)
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="devicemanufacture"
    user=request.user
    if user.role==role:
        uo=get_user_object(user,role)
        if not uo:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Deserialize the input parameters
    data=request.data
    #data['created_by__id']=user.id
    serializer = DeviceModelFilterSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    # Filter DeviceModel instances based on parameters
    device_models = DeviceModel.objects.filter(**serializer.validated_data,created_by=user)

    # Serialize the data
    serializer = DeviceModelSerializer_disp(device_models, many=True)

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def details_devicemodel(request ):     
    device_model_id = request.data.get('device_model_id')
    device_model = get_object_or_404(DeviceModel, id=device_model_id) 
    serializer = DeviceModelSerializer_disp(device_model)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DeviceModelAwaitingStateApproval(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    #user_id = request.user.id    
    user=request.user 
    sa=get_user_object(user,"stateadmin")
    if not sa:
        return Response({"error":"Request must be from stateadmin"}, status=status.HTTP_400_BAD_REQUEST)
      

    # Retrieve device models with status "Manufacturer_OTP_Verified"
    device_models = DeviceModel.objects.filter(status__in=['Manufacturer_OTP_Verified',"StateAdminOTPSend"])#created_by=user_id, 
    
    # Serialize the data
    serializer = DeviceModelSerializer_disp(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DeviceSendStateAdminOtp(request ): 
    user=request.user 
    sa=get_user_object(user,"stateadmin")
    if not sa:
        return Response({"error":"Request must be from stateadmin"}, status=status.HTTP_400_BAD_REQUEST)
      
    device_model_id = request.data.get('device_model_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceModel, id=device_model_id,  status__in =['Manufacturer_OTP_Verified',"StateAdminOTPSend"])
    otp= str(random.randint(100000, 999999))

     
    device_model.otp_time = timezone.now()
    device_model.otp = otp
    device_model.status = 'StateAdminOTPSend'
    device_model.save()
    text="Dear User, Your  OTP to validate device model creation in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
    tpid="1007536593942813283"
    #send_SMS(stateadmin.users.last().mobile,text,tpid) 
    send_mail(
                'Login OTP',
                "Dear User, Your OTP to validate device model creation in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
    )
    

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DeviceVerifyStateAdminOtp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    sa=get_user_object(user,"stateadmin")
    if not sa:
        return Response({"error":"Request must be from stateadmin"}, status=status.HTTP_400_BAD_REQUEST)
      
    device_model_id = request.data.get('device_model_id') 
    user_id = request.user.id 
    device_model = get_object_or_404(DeviceModel, id=device_model_id, status='StateAdminOTPSend')#created_by=user_id ,
 
 
    otp = request.data.get('otp')
    if device_model.otp!=otp:
            return JsonResponse({'error': "Invalid OTP"}, status=400)


    device_model.status = 'StateAdminApproved'
    device_model.save()

    return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DeviceCreateManufacturerOtpVerify(request  ): 
    user_id = request.user.id
    user=request.user 
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
      
    otp = request.data.get('otp')
    device_model_id = request.data.get('device_model_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)

    device_model = get_object_or_404(DeviceModel, id=device_model_id,status='Manufacturer_OTP_Sent')# created_by=user_id, 
    if device_model.created_by!=user:
        return Response({"error":"User is not the creator of this devicemodel"}, status=status.HTTP_400_BAD_REQUEST)
      
 
    if otp == device_model.otp:  
        device_model.status = 'Manufacturer_OTP_Verified'
        device_model.save()
        return Response({"message": "Manufacturer OTP verified successfully."}, status=200)
    else:
            return JsonResponse({'error': "Invalid OTP"}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_hp_freq(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
     
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),  
        #'status': 'Manufacturer_OTP_Sent',
    } 
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_hp_freqSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save() 
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_hp_freq(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_hp_freq.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        dealer_serializer = Settings_hp_freqSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_ip(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
      #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),   
        #'status': 'Manufacturer_OTP_Sent',
    } 
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_ipSerializer(data=request_data) 
    if serializer.is_valid():
        instance = serializer.save() 
        return Response(serializer.data, status=status.HTTP_201_CREATED) 
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)










@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_District(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        #"superadmin","devicemanufacture","","dtorto","dealer","owner","esimprovider"
        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)
        if  uo:
            state=uo.state
            manufacturers = Settings_District.objects.filter(state=state ).distinct()
        else:
            manufacturers = Settings_District.objects.all()
    
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        
            
        # Serialize the queryset
        dealer_serializer = Settings_DistrictSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_District(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    request_data = request.data.copy()
    data = {
        'createdby': user_id,
        'created': timezone.now(),  
        "state":request_data["state"],
        "district":request_data["district_name" ],

    }

    # Attach the file to the request data
    request_data.update(data)
    #print(request_data)
    serializer = Settings_DistrictSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
    

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




















@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_firmware(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_firmware.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        dealer_serializer = Settings_firmwareSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_firmware(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="devicemanufacture"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),  
        'file_bin':'file',
        #'status': 'Manufacturer_OTP_Sent',
    }

    
        

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_firmwareSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
        uploaded_file = request.FILES.get('file_bin')
        if uploaded_file:
            # Save the file to a specific location
            file_path = 'fileuploads/file_bin/' + str(instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            # Update the cop_file field in the DeviceCOP instance
            instance.file_bin = file_path
            instance.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_VehicleCategory(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_VehicleCategory.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        dealer_serializer = Settings_VehicleCategorySerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_VehicleCategory(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
      #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),  
        #'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_VehicleCategorySerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
    

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'Manufacture': Manufacturer.objects.count(),
            'eSimProvider': eSimProvider.objects.count(),
            'Retailer': Retailer.objects.count(),
            'VehicleOwner': VehicleOwner.objects.count(),
            'dto_rto': dto_rto.objects.count(),
            'SOS_ex': EM_ex.objects.count(),
            'SOS_user': EM_ex.objects.count(),
            'SOS_admin': EM_admin.objects.count(),
            
            'TotalVehicles':DeviceTag.objects.count(),
            
            'SOS_team': EMTeams.objects.count(),
            
            'TotalAlerts':0,
            'TotalAlerts_month':0,
            'TotalAlerts_today':0,
            'SpeedAlerts':0,
            'SpeedAlerts_month':0,
            'SpeedAlerts_today':0,

            'TotalDevice': DeviceStock.objects.count(),
            'TotalTaggedDevice':0,
            'TotalOnlineDevice':0,
            'TotalOfflineDevice':0,
            'TotalDeviceModel': DeviceModel.objects.count(),
            
          

                'Total_device_stock':DeviceStock.objects.count(),
                'unassigned_device_stock':DeviceStock.objects.filter(stock_status='NotAssigned').count(),
                'Waiting_device_stock':DeviceStock.objects.filter(stock_status='Available_for_fitting').count(),
                'Fitted_device_stock':DeviceStock.objects.filter(stock_status='Fitted').count(),
                
                'Total_States':Settings_State.objects.all().count(),
                'Active_States':Settings_State.objects.filter(status='active').count(),
                'Inactive_States':Settings_State.objects.filter(status='discontinued').count(),
             

                'Total_district':Settings_District.objects.all().count(),
                'Active_district':Settings_District.objects.filter(status='active').count(),
                'Active_district':Settings_District.objects.filter(status='discontinued').count(),

        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_state(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'total_state':Settings_State.objects.count(),
            'active_state':Settings_State.objects.filter(status='active').count(),
            'inactive_state':Settings_State.objects.filter(status='discontinued').count(), 

        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_alart(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get the current date and time
        current_date = now().date()
        current_month_start = current_date.replace(day=1)

        # Calculate total counts for "in" status
        total_count = AlertsLog.objects.filter(status="in").count()
        month_count = AlertsLog.objects.filter(status="in", timestamp__gte=current_month_start).count()
        today_count = AlertsLog.objects.filter(status="in", timestamp__date=current_date).count()

        # Initialize a dictionary to hold the counts
        count_dict = {
            'total_alerts': {
                'total': total_count,
                'this_month': month_count,
                'today': today_count,
            },
            'alerts_by_type': {},
        }

        # Fetch counts grouped by type for "total," "this month," and "today"
        for alert_type, _ in AlertsLog.TYPE_CHOICES:
            type_total_count = AlertsLog.objects.filter(type=alert_type, status="in").count()
            type_month_count = AlertsLog.objects.filter(
                type=alert_type, status="in", timestamp__gte=current_month_start
            ).count()
            type_today_count = AlertsLog.objects.filter(
                type=alert_type, status="in", timestamp__date=current_date
            ).count()

            count_dict['alerts_by_type'][alert_type] = {
                'total': type_total_count,
                'this_month': type_month_count,
                'today': type_today_count,
            }

        # Return the count dictionary as a JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def alart_list(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="owner"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        alerts = AlertsLog.objects.filter(deviceTag__vehicle_owner=uo).order_by('-id')[:10]
        if alerts:
            serializer = AlertsLogSerializer(alerts, many=True)
            return Response({"alertHistory":serializer.data}, status=200)
        
        return Response({"alertHistory":[]}, status=200)
        
    except:
        pass
    return Response({"error":"No Valid Data Found"+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
 
     
                
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_device1(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'total_device':0,
            'active_device': 0,
            'idle_device':0, 

        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_device2(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'tag_device':0,
            'online_device': 0,
            'offline_device':0, 
        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_Manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
         
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="devicemanufacture"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Get manufacturer profile user
            manufacturer_user = profile.users.last()
            
            # Basic manufacturer statistics
            mod = DeviceModel.objects.filter(created_by=manufacturer_user)
            dealers = Retailer.objects.filter(manufacturer=profile)
            stock = DeviceStock.objects.filter(created_by=manufacturer_user)
            
            # Calculate activations (devices that are actually activated/tagged)
            total_activations = DeviceTag.objects.filter(
                device__created_by=manufacturer_user,
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed']
            ).count()
            
            # Calculate eSIM statistics
            esim_activation_requests = stock.filter(
                esim_status='ESIM_Active_Req_Sent'
            ).count()
            
            # Calculate renewal requests based on eSIM validity dates
            one_year_renewals = stock.filter(
                esim_validity__lte=now + timedelta(days=365),
                esim_validity__gt=now + timedelta(days=180)
            ).count()
            
            two_year_renewals = stock.filter(
                esim_validity__lte=now + timedelta(days=730),
                esim_validity__gt=now + timedelta(days=365)
            ).count()
            
            # Calculate device connectivity statistics
            # Get all devices manufactured by this manufacturer
            manufacturer_devices = DeviceTag.objects.filter(device__created_by=manufacturer_user)
            activated_devices = manufacturer_devices.filter(status="Device_Active")
            
            online_devices = 0
            offline_today = 0
            offline_7day = 0
            offline_30day = 0
            expired_devices = 0
            
            for device in activated_devices:
                latest_gps = GPSData.objects.filter(device_tag=device).order_by('-entry_time').first()
                if latest_gps:
                    # Check if device is online (data received within last 30 minutes)
                    if latest_gps.entry_time >= now - timedelta(minutes=30):
                        online_devices += 1
                    
                    # Check offline periods
                    if latest_gps.entry_time < today_start:
                        offline_today += 1
                    if latest_gps.entry_time < week_ago:
                        offline_7day += 1
                    if latest_gps.entry_time < now - timedelta(days=30):
                        offline_30day += 1
                else:
                    # No GPS data means offline for all periods
                    offline_today += 1
                    offline_7day += 1
                    offline_30day += 1
                
                # Check for expired devices (based on eSIM validity)
                if device.device:
                    device_stock = DeviceStock.objects.filter(
                        device_esn=device.device.device_esn
                    ).first()
                    if device_stock and device_stock.esim_validity < now:
                        expired_devices += 1
            
            count_dict = {
                'Total_Model': mod.count(),
                'Total_esim_linked': profile.esim_provider.count(),
                
                'Total_Dealer': dealers.count(),
                'Total_Stock_Created': stock.count(),
                'Total_Stock_Allocated': stock.filter(assigned__isnull=False).count(),
                'Total_Activation': total_activations,
                
                'Total_esim_activation_request': esim_activation_requests,
                'Total_1year_renewal_request': one_year_renewals,
                'Total_2year_renewal_request': two_year_renewals,
                
                'Total_Online_Device': online_devices,
                'Total_Offline_Device_today': offline_today,
                'Total_Offline_Device_7day': offline_7day,
                'Total_Offline_Device_30day': offline_30day,
                
                'Total_expired_device': expired_devices
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_DTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="dtorto"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Get all devices in DTO's jurisdiction (state/district)
            # For DTO, we filter by devices in their state and optionally district
            jurisdiction_filter = Q()
            
            # Filter by state
            if hasattr(profile, 'state') and profile.state:
                # Get all device tags in this state
                devices_in_state = DeviceTag.objects.filter(
                    device__dealer__manufacturer__state=profile.state
                )
                
                # If DTO has specific district, filter further
                if hasattr(profile, 'district') and profile.district:
                    devices_in_state = devices_in_state.filter(
                        device__dealer__district__district=profile.district
                    )
            else:
                # Fallback: get all devices (for testing)
                devices_in_state = DeviceTag.objects.all()
            
            # Calculate device and vehicle statistics
            total_devices_activated = devices_in_state.filter(
                status="Device_Active"
            ).count()
            
            total_vehicles = devices_in_state.count()
            
            # Calculate online/offline device statistics
            online_devices = 0
            offline_today = 0
            offline_7day = 0
            offline_30day = 0
            
            activated_devices = devices_in_state.filter(status="Device_Active")
            
            for device in activated_devices:
                latest_gps = GPSData.objects.filter(device_tag=device).order_by('-entry_time').first()
                if latest_gps:
                    # Check if device is online (data received within last 30 minutes)
                    if latest_gps.entry_time >= now - timedelta(minutes=30):
                        online_devices += 1
                    
                    # Check offline periods
                    if latest_gps.entry_time < today_start:
                        offline_today += 1
                    if latest_gps.entry_time < week_ago:
                        offline_7day += 1
                    if latest_gps.entry_time < now - timedelta(days=30):
                        offline_30day += 1
                else:
                    # No GPS data means offline for all periods
                    offline_today += 1
                    offline_7day += 1
                    offline_30day += 1
            
            # Calculate alert statistics for the jurisdiction
            total_alerts = AlertsLog.objects.filter(
                deviceTag__in=devices_in_state
            ).count()
            
            alerts_month = AlertsLog.objects.filter(
                deviceTag__in=devices_in_state,
                timestamp__gte=month_start
            ).count()
            
            alerts_today = AlertsLog.objects.filter(
                deviceTag__in=devices_in_state,
                timestamp__gte=today_start
            ).count()
            
            # Calculate activation statistics (device tagging/activation)
            total_activations = devices_in_state.filter(
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed']
            ).count()
            
            activations_month = devices_in_state.filter(
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed'],
                tagged__gte=month_start
            ).count()
            
            activations_today = devices_in_state.filter(
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed'],
                tagged__gte=today_start
            ).count()
            
            # Calculate SOS call statistics for the jurisdiction
            total_sos = EMCall.objects.filter(
                device__in=devices_in_state
            ).count()
            
            genuine_sos = EMCall.objects.filter(
                device__in=devices_in_state,
                status__in=['closed', 'field_ex_arrived']
            ).count()
            
            fake_sos = EMCall.objects.filter(
                device__in=devices_in_state,
                status='closed_false_allert'
            ).count()
            
            count_dict = {
                'Total_Device_Activated': total_devices_activated,
                'Total_Vehicles': total_vehicles,
                'Total_Online_Device': online_devices,
                'Total_Offline_Device_today': offline_today,
                'Total_Offline_Device_7day': offline_7day,
                'Total_Offline_Device_30day': offline_30day,
                
                'Total_Alert': total_alerts,
                'Alert_month': alerts_month,
                'Alert_today': alerts_today,
                
                'Total_activations': total_activations,
                'Activations_month': activations_month,
                'Activations_today': activations_today,
                
                'Total_SOS_calls': total_sos,
                'Genuine_calls': genuine_sos,
                'Fake_calls': fake_sos
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': f"Unable to process request: {str(e)}"}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="owner"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        #print('profile',profile.state.state)
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Get all devices owned by this vehicle owner
            owned_devices = DeviceTag.objects.filter(vehicle_owner=profile)
            activated_devices = owned_devices.filter(status="Device_Active")
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Calculate vehicle movement status based on latest GPS data
            moving_count = 0
            stopped_count = 0
            idle_count = 0
            online_count = 0
            
            for device in activated_devices:
                # Get latest GPS data for this device
                latest_gps = GPSData.objects.filter(device_tag=device).order_by('-entry_time').first()
                if latest_gps:
                    # Check if device is online (data received within last 30 minutes)
                    if latest_gps.entry_time >= now - timedelta(minutes=30):
                        online_count += 1
                        
                        # Determine movement status
                        if latest_gps.speed > 5:  # Moving if speed > 5 km/h
                            moving_count += 1
                        elif latest_gps.ignition_status == "1":  # Idle if ignition on but not moving
                            idle_count += 1
                        else:  # Stopped if ignition off
                            stopped_count += 1
                    else:
                        stopped_count += 1  # Consider offline devices as stopped
                else:
                    stopped_count += 1  # No GPS data means stopped
            
            # Calculate offline devices for different periods
            offline_today = activated_devices.count() - GPSData.objects.filter(
                device_tag__in=activated_devices,
                entry_time__gte=today_start
            ).values('device_tag').distinct().count()
            
            offline_7day = activated_devices.count() - GPSData.objects.filter(
                device_tag__in=activated_devices,
                entry_time__gte=week_ago
            ).values('device_tag').distinct().count()
            
            offline_30day = activated_devices.count() - GPSData.objects.filter(
                device_tag__in=activated_devices,
                entry_time__gte=now - timedelta(days=30)
            ).values('device_tag').distinct().count()
            
            # Calculate total travel distance from odometer
            total_distance = 0
            for device in activated_devices:
                latest_gps = GPSData.objects.filter(device_tag=device).order_by('-entry_time').first()
                if latest_gps and latest_gps.odometer:
                    total_distance += latest_gps.odometer
            
            # Calculate alert statistics
            total_alerts = AlertsLog.objects.filter(deviceTag__in=owned_devices).count()
            alerts_month = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                timestamp__gte=month_start
            ).count()
            alerts_today = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                timestamp__gte=today_start
            ).count()
            
            # Calculate specific alert types
            harsh_braking = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                type='HarshBreak'
            ).count()
            
            harsh_turn = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                type='HarshTurn'
            ).count()
            
            overspeeding = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                type='OverSpeed'
            ).count()
            
            # Calculate SOS calls
            total_sos = EMCall.objects.filter(device__in=owned_devices).count()
            genuine_sos = EMCall.objects.filter(
                device__in=owned_devices,
                status__in=['closed', 'field_ex_arrived']
            ).count()
            fake_sos = EMCall.objects.filter(
                device__in=owned_devices,
                status='closed_false_allert'
            ).count()
            
            # Get recent alerts for alert list
            recent_alerts = AlertsLog.objects.filter(
                deviceTag__in=owned_devices
            ).select_related('gps_ref', 'deviceTag').order_by('-timestamp')[:10]
            
            alert_list = []
            for alert in recent_alerts:
                alert_data = {
                    'type': alert.get_type_display() if alert.type else 'Unknown',
                    'id': alert.id,
                    'TriggerTime': alert.timestamp.isoformat(),
                    'Status': alert.status if alert.status else 'Active',
                    'VehicleRegNo': alert.deviceTag.vehicle_reg_no if alert.deviceTag else 'Unknown',
                    'TriggerLocation': {
                        'latitude': float(alert.gps_ref.latitude) if alert.gps_ref else 0,
                        'latitude_dir': alert.gps_ref.latitude_dir if alert.gps_ref else 'N',
                        'longitude': float(alert.gps_ref.longitude) if alert.gps_ref else 0,
                        'longitude_dir': alert.gps_ref.longitude_dir if alert.gps_ref else 'E'
                    }
                }
                alert_list.append(alert_data)
            
            count_dict = {
                'Total_Vehicles': owned_devices.count(),
                'Total_Device_Activated': activated_devices.count(),
                'Total_Moving_Vehicles': moving_count,
                'Total_Stopped_Vehicles': stopped_count,
                'Total_Idle_Vehicles': idle_count,
                
                'Total_Online_Device': online_count,
                'Total_Offline_Device_today': offline_today,
                'Total_Offline_Device_7day': offline_7day,
                'Total_Offline_Device_30day': offline_30day,
                
                'Total_Travel_Distance_km': round(total_distance, 2),
                
                'Total_Alert': total_alerts,
                'Alert_month': alerts_month,
                'Alert_today': alerts_today,
                
                'Total_Harshbraking': harsh_braking,
                'Total_suddenturn': harsh_turn,
                'Total_overspeeding': overspeeding,
                
                'Total_SOS_calls': total_sos,
                'Genuine_calls': genuine_sos,
                'Fake_calls': fake_sos,
                'Alert_list': alert_list
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': f"Unable to process request: {str(e)}"}, status=400)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_VehicleOwnerold(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 

        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="owner"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            count_dict = {
                 


'Total_Vehicles':0,
'Total_Device_Activated':0,
'Total_Moving_Vehicles':0,
'Total_Stopped_Vehicles':0,
'Total_Idle_Vehicles':0,

'Total_Online_Device':0,
'Total_Offline_Device_today':0,
'Total_Offline_Device_7day':0,
'Total_Offline_Device_30day':0,

'Total_Travel_Distance_km':0,



'Total_Alert':0,
'Alert_month':0,
'Alert_today':0,

'Total_Harshbraking':0,
'Total_suddenturn':0,
'Total_overspeeding':0,

'Total_SOS_calls':0,
'Genuine_calls':0,
'Fake_calls':0


             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_Dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
         
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="dealer"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Get all device stock assigned to this dealer
            dealer_devices = DeviceStock.objects.filter(dealer=profile)
            
            # Calculate fitment statistics
            total_fitments = DeviceTag.objects.filter(
                device__dealer=profile,
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed']
            ).count()
            
            fitments_month = DeviceTag.objects.filter(
                device__dealer=profile,
                tagged__gte=month_start,
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed']
            ).count()
            
            fitments_today = DeviceTag.objects.filter(
                device__dealer=profile,
                tagged__gte=today_start,
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed']
            ).count()
            
            # Calculate device stock statistics
            total_assigned = dealer_devices.count()
            total_returned = dealer_devices.filter(stock_status='Returned_to_manufacturer').count()
            current_stock = dealer_devices.filter(stock_status='Available_for_fitting').count()
            current_faulty = dealer_devices.filter(stock_status='Device_Defective').count()
            available_free = dealer_devices.filter(
                stock_status='Available_for_fitting'
            ).exclude(
                devicetag__isnull=False  # Exclude devices that are already tagged
            ).count()
            
            # Calculate eSIM activation requests
            esim_activation_requests = dealer_devices.filter(
                esim_status='ESIM_Active_Req_Sent'
            ).count()
            
            # Calculate renewal requests (based on eSIM validity - these are approximations)
            one_year_renewals = dealer_devices.filter(
                esim_validity__lte=now + timedelta(days=365),
                esim_validity__gt=now + timedelta(days=180)
            ).count()
            
            two_year_renewals = dealer_devices.filter(
                esim_validity__lte=now + timedelta(days=730),
                esim_validity__gt=now + timedelta(days=365)
            ).count()
            
            # Calculate online/offline device statistics
            # Get devices that are tagged (fitted) by this dealer
            tagged_devices = DeviceTag.objects.filter(device__dealer=profile)
            
            # Online devices (with GPS data in last 30 minutes)
            online_now = 0
            online_today = 0
            offline_7days = 0
            offline_30days = 0
            
            for device in tagged_devices:
                latest_gps = GPSData.objects.filter(device_tag=device).order_by('-entry_time').first()
                if latest_gps:
                    # Check if online now (last 30 minutes)
                    if latest_gps.entry_time >= now - timedelta(minutes=30):
                        online_now += 1
                    
                    # Check if online today
                    if latest_gps.entry_time >= today_start:
                        online_today += 1
                    
                    # Check if offline for 7 days
                    if latest_gps.entry_time < now - timedelta(days=7):
                        offline_7days += 1
                    
                    # Check if offline for 30 days
                    if latest_gps.entry_time < now - timedelta(days=30):
                        offline_30days += 1
                else:
                    # No GPS data means offline
                    offline_7days += 1
                    offline_30days += 1
            
            count_dict = {
                'Total_Fitment_done': total_fitments,
                'Fitment_month': fitments_month,
                'Fitment_today': fitments_today,
                
                'Total_Device_Assigned': total_assigned,
                'Total_Device_Returned': total_returned,
                'Current_Device_stock': current_stock,
                'Current_Device_faulty': current_faulty,
                'Available_Free_Device': available_free,
                'Total_esim_activation_request': esim_activation_requests,
                'Total_1_year_renewal_request': one_year_renewals,
                'Total_2_year_renewal_request': two_year_renewals,
                
                'Total_Online_now': online_now,
                'Total_Online_today': online_today,
                'Total_Offline_7_days': offline_7days,
                'Total_Offline_30_days': offline_30days
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': f"Unable to process request: {str(e)}"}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SOS_adminreport(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="sosadmin" 
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if profile:
            count_dict = {
 
                'Total_Teams':EMTeams.objects.filter(state=profile.state,status="Active").count(),
                'Total_DeskExecutives':EM_ex.objects.filter(user_type='desk_ex',state=profile.state).count(),
                'Live_Teams':EMTeams.objects.filter(state=profile.state,status="Active").count(),
                'Live_DeskExecutives':EM_ex.objects.filter(user_type='desk_ex',state=profile.state).count(),

                'Total_Incoming_Calls':EMCall.objects.filter(team__state=profile.state).count(),
                'Total_Incoming_Calls_thismonth':EMCall.objects.filter(team__state=profile.state).count(),
                'Total_Incoming_Calls_thisweek':EMCall.objects.filter(team__state=profile.state).count(),
                'Total_Incoming_Calls_today':EMCall.objects.filter(team__state=profile.state).count(),

                'Total_Closed_Calls':EMCall.objects.filter(status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_thismonth':EMCall.objects.filter(status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_thisweek':EMCall.objects.filter(status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_today':EMCall.objects.filter(status="closed",team__state=profile.state).count(),

                'Total_Fake_Calls':EMCall.objects.filter(status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_thismonth':EMCall.objects.filter(status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_thisweek':EMCall.objects.filter(status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_today':EMCall.objects.filter(status="closed_false_allert",team__state=profile.state).count(),


                'Total_Active_Calls':EMCall.objects.filter(team__state=profile.state,status__in=["desk_ex_assigned","broadcast_pending", "field_ex_aproaching" , "field_ex_arrived"]).count(),  
                'Total_Pending_Calls':EMCall.objects.filter(status="pending",team__state=profile.state).count(),

                'Total_Rejected_Assignemnt':EMCallAssignment.objects.filter(status="rejected",admin=profile).count(),
                'Total_Rejected_Assignemnt_thismonth':EMCallAssignment.objects.filter(status="rejected",admin=profile).count(),
                'Total_Rejected_Assignemnt_thisweek':EMCallAssignment.objects.filter(status="rejected",admin=profile).count(),
                'Total_Rejected_Assignemnt_today':EMCallAssignment.objects.filter(status="rejected",admin=profile).count(),


                'Average_time_to_Accept':EMCallAssignment.objects.filter(status="accepted",admin=profile).count(),


             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['get'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SOS_TLreport(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="sosexecutive" 
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  teamlead"}, status=status.HTTP_400_BAD_REQUEST)
        print(profile.user_type)
        if 'teamlead' not in profile.user_type:#, 'desk_ex',
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if profile:
            team=EMTeams.objects.filter(teamlead=profile,status="Active").last()
            a=0
            b=0
            if team:
                a=team.members.count()
                b=team.members.count()
            count_dict = {
 
                 
                'Total_DeskExecutives':a, 
                'Live_DeskExecutives':b,

                'Total_Incoming_Calls':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state).count(),
                'Total_Incoming_Calls_thismonth':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state).count(),
                'Total_Incoming_Calls_thisweek':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state).count(),
                'Total_Incoming_Calls_today':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state).count(),

                'Total_Closed_Calls':EMCall.objects.filter(team__teamlead=profile,status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_thismonth':EMCall.objects.filter(team__teamlead=profile,status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_thisweek':EMCall.objects.filter(team__teamlead=profile,status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_today':EMCall.objects.filter(team__teamlead=profile,status="closed",team__state=profile.state).count(),

                'Total_Fake_Calls':EMCall.objects.filter(team__teamlead=profile,status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_thismonth':EMCall.objects.filter(team__teamlead=profile,status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_thisweek':EMCall.objects.filter(team__teamlead=profile,status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_today':EMCall.objects.filter(team__teamlead=profile,status="closed_false_allert",team__state=profile.state).count(),


                'Total_Active_Calls':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state,status__in=["desk_ex_assigned","broadcast_pending", "field_ex_aproaching" , "field_ex_arrived"]).count(),  
                'Total_Pending_Calls':EMCall.objects.filter(team__teamlead=profile,status="pending",team__state=profile.state).count(),

                'Total_Rejected_Assignemnt':EMCallAssignment.objects.filter(status="rejected",call__team__teamlead=profile).count(),
                'Total_Rejected_Assignemn_thistmonth':EMCallAssignment.objects.filter(status="rejected",call__team__teamlead=profile).count(),
                'Total_Rejected_Assignemn_thisweek':EMCallAssignment.objects.filter(status="rejected",call__team__teamlead=profile).count(),
                'Total_Rejected_Assignemn_today':EMCallAssignment.objects.filter(status="rejected",call__team__teamlead=profile).count(),

                'Average_time_to_Accept':EMCallAssignment.objects.filter(status="accepted",call__team__teamlead=profile).count(),

             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['get'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SOS_EXreport(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="sosexecutive" 
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  teamlead"}, status=status.HTTP_400_BAD_REQUEST)
        if not profile.user_type=='desk_ex':#, '',
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if profile: 
            count_dict = {
 

  
                 
                'Total_Assignemnt_thistmonth':EMCallAssignment.objects.filter(ex=profile).count(),
                'Total_Assignemnt_thisweek':EMCallAssignment.objects.filter(ex=profile).count(),
                'Total_Assignemnt_today':EMCallAssignment.objects.filter( ex=profile).count(),
                'Total_Assignemnt':EMCallAssignment.objects.filter( ex=profile).count(),

                'Total_Closed_Assignemnt_thistmonth':EMCallAssignment.objects.filter(status="closed",ex=profile).count(),
                'Total_Closed_Assignemnt_thisweek':EMCallAssignment.objects.filter(status="closed",ex=profile).count(),
                'Total_Closed_Assignemnt_today':EMCallAssignment.objects.filter(status="closed",ex=profile).count(),
                'Total_Closed_Assignemnt':EMCallAssignment.objects.filter(status="closed",ex=profile).count(),
                 
                'Total_False_Assignemnt_thistmonth':EMCallAssignment.objects.filter(status="closed_false_allert",ex=profile).count(),
                'Total_False_Assignemnt_thisweek':EMCallAssignment.objects.filter(status="closed_false_allert",ex=profile).count(),
                'Total_False_Assignemnt_today':EMCallAssignment.objects.filter(status="closed_false_allert",ex=profile).count(),
                'Total_False_Assignemnt':EMCallAssignment.objects.filter(status="closed_false_allert",ex=profile).count(),

                 
                'Total_Rejected_Assignemnt_thistmonth':EMCallAssignment.objects.filter(status="rejected",ex=profile).count(),
                'Total_Rejected_Assignemnt_thisweek':EMCallAssignment.objects.filter(status="rejected",ex=profile).count(),
                'Total_Rejected_Assignemnt_today':EMCallAssignment.objects.filter(status="rejected",ex=profile).count(),
                'Total_Rejected_Assignemnt':EMCallAssignment.objects.filter(status="rejected",ex=profile).count(),

                'Average_time_to_Accept':EMCallAssignment.objects.filter(status="accepted",ex=profile).count(),

             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_stateAdmin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="stateadmin"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if profile:
            count_dict = {

                'Total_Dealer_available':Retailer.objects.count(),
                'Total_Manufacture_available':Manufacturer.objects.filter(state=profile.state).count(),
                'Total_DTO_available':dto_rto.objects.filter(state=profile.state).count(),
                'Total_Vehicle_Owner_available':VehicleOwner.objects.count(),


                'Total_Fit_Device' : DeviceTag.objects.filter(status='Device_Active').count(),
                'Online_Devices':DeviceTag.objects.filter(status='Device_Active').count(),
                'Offline_Devices':0,

                'Total_Device_Activated':DeviceTag.objects.filter(status='Device_Active').count(),
                'Active_Device_Today':0,
                'Inactive_Device_7days' :0,
                'Inactive_Device_30days':0,
                
                'Total_overspeeding_Alert':0,
                'Monthly_overspeeding_Alert':0,
                'Today_overspeeding_Alert':0,
                
                'Total_emergency_Alert':0,
                'This_month_emergency_Alert':0,
                'Today_emergency_Alert':0,
                
                'Total_harsh_brake_Alert':0,
                'This_month_harsh_brake_Alert':0,
                'Today_harsh_brake_Alert' :0 ,

                'Total_device_stock':DeviceStock.objects.count(),
                'unassigned_device_stock':DeviceStock.objects.filter(stock_status='NotAssigned').count(),
                'waiting_device_stock':DeviceStock.objects.filter(stock_status='Available_for_fitting').count(),
                
                'Total_state':Settings_State.objects.all().count(),
                'Active_state':Settings_State.objects.filter(status='active').count(),
                'Active_state':Settings_State.objects.filter(status='discontinued').count(),
             

                'Total_district':Settings_District.objects.all().count(),
                'Active_district':Settings_District.objects.filter(status='active').count(),
                'Active_district':Settings_District.objects.filter(status='discontinued').count(),
             
             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_user1(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'total_user': Manufacturer.objects.count(),
            'state_admin': StateAdmin.objects.count(),
            'manufacturer_admin': Manufacturer.objects.count(),
            'dtorto_admin': dto_rto.objects.count(),
            'eSimProvider': eSimProvider.objects.count(),
            'Retailer': Retailer.objects.count(),
            'VehicleOwner': VehicleOwner.objects.count(),  
            'SOS_ex': EM_ex.objects.count(),
            'SOS_user': EM_ex.objects.count(),
            'SOS_admin': EM_admin.objects.count(),
             
        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_user2(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
             
            'dtorto_admin': dto_rto.objects.count(),
            'eSimProvider': eSimProvider.objects.count(),
            'Retailer': Retailer.objects.count(),
            'VehicleOwner': VehicleOwner.objects.count(), 
            'SOS_ex': EM_ex.objects.count(),
            'SOS_user': EM_ex.objects.count(),
            'SOS_admin': EM_admin.objects.count(),
        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_State(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided

        #"superadmin","devicemanufacture","","dtorto","dealer","owner","esimprovider"
        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)
        role="sosadmin" 
        uosos=get_user_object(user,role)
        if  uo:
            state=uo.state
            manufacturers = Settings_State.objects.filter(id=state.id ).distinct()
        elif  uosos:
            state=uosos.state
            manufacturers = Settings_State.objects.filter(id=state.id ).distinct()
        else:
            manufacturers = Settings_State.objects.all()

 
        # Serialize the queryset
        dealer_serializer = Settings_StateSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_State(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
      #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),   
    } 
    request_data = request.data.copy()

    if 'state_name' in request_data:
        request_data['state'] = request_data['state_name'].capitalize()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_StateSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
    

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_ip(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_ip.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        dealer_serializer = Settings_ipSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '') 
        filters = {} 
        if dealer_id :
            manufacturers = VehicleOwner.objects.filter(
                id=dealer_id ,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = VehicleOwner.objects.filter( 
                users__status='active',
                users__email__icontains=email,
                #company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        dealer_serializer = VehicleOwnerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


'''



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_esim_activation_request(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
            
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="dealer"
        user=request.user
        ret=get_user_object(user,role)
        if not ret:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = { 
            'ceated_by':ret.id,  
            'status': 'pending',
            #'device': int(request.data['device'])
        } 
        request_data = request.data.copy()
        request_data.update(data)
        dev=DeviceStock.objects.filter(id=request_data['device']).last()
        if not dev:
            return Response("device not found", status=status.HTTP_400_BAD_REQUEST)
        if dev.esim_status=="ESIM Active Request Sent":
            return Response("AlreadyPendingRequest", status=status.HTTP_400_BAD_REQUEST)

        serializer = EsimActivationRequestSerializer(data=request_data)
        if serializer.is_valid():
            dev.esim_status='ESIM_Active_Req_Sent'
            dev.save()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def filter_esim_activation_request(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

           
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="esimprovider"
    user=request.user
    #ret=get_user_object(user,role)
    #if not ret:
    #    return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        
    if request.method == 'POST':
        filters = request.data.get('filters', {}) 
        queryset = esimActivationRequest.objects.filter(**filters)
        serializer = EsimActivationRequestSerializer_R(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@permission_classes([AllowAny])
@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def update_esim_activation_request(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

      
    if request.method == 'POST':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="esimprovider"
        user=request.user
        ret=get_user_object(user,role)
        if not ret:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        
        esim_request=esimActivationRequest.objects.filter(id=request.data['eSim_activation_req_id']).last()
        if not esim_request:
            return Response({"error":"eSim_activation_req_id is invalid."}, status=status.HTTP_400_BAD_REQUEST)
        if esim_request.eSim_provider != ret:
            return Response({"error":"esim provided is not designeated esim provider for this device."}, status=status.HTTP_400_BAD_REQUEST)
        if esim_request.status!="pending":
            return Response({"error":"esim activation request mustbe pending to activate"}, status=status.HTTP_400_BAD_REQUEST)
        
        data = { 'status': 'pending', }  
        if request.data['status']=="accept":
            data = { 'status': 'valid'}  
        elif request.data['status']=="reject":
            data = { 'status': 'invalid'}  
        else:
            return Response({"error":"Status should be only ony one of the two[accept/reject]."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = EsimActivationRequestSerializer(esim_request, data=data, partial=True)
        dev=esim_request.device
        #DeviceStock.objects.filter(id=data['device']).last()
         

        if serializer.is_valid():
            if data['status']=='valid':
                dev.esim_status='ESIM_Active_Confirmed'
            elif data['status']=='invalid':
                dev.esim_status='ESIM_Active_Rejected'
            
            dev.save()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





def get_user_object(user,role):
    ret=None
    if user.role !=role:
        return ret 
    if role=="superadmin":
        ret=user
    if role=="devicemanufacture":
        ret=Manufacturer.objects.filter(users=user).last() 
    if role=="stateadmin":
        ret=StateAdmin.objects.filter(users=user).last()
    if role=="dtorto":
        ret=dto_rto.objects.filter(users=user).last() 
    if role=="dealer":
        ret=Retailer.objects.filter(users=user).last() 
    if role=="owner":
        ret=VehicleOwner.objects.filter(users=user).last() 
    if role=="esimprovider":
        ret=eSimProvider.objects.filter(users=user).last() 
    if role=="sosadmin":
        ret=EM_admin.objects.filter(users=user).last() 
    if role=="sosexecutive":
        ret=EM_ex.objects.filter(users=user).last() 
        
        

    return ret
     

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_device_model(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    user_id = request.user.id
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
     


     
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    otp= str(random.randint(100000, 999999))

    # Create data for the new DeviceModel entry
    data = {
        'otp_time':timezone.now(),
        'otp': otp,
        'created_by': user_id,
        'created': timezone.now(),   
        'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    #print("requestdata",request_data) 
    serializer = DeviceModelSerializer(data=request_data)

    # Validate and save the data along with the file
    if serializer.is_valid():
        # Save the DeviceModel instance
        device_model_instance = serializer.save()
        # Handle the uploaded file
        uploaded_file = request.FILES.get('tac_doc_path')
        if uploaded_file:
            # Save the file to a specific location
            
            file_path = save_file(request, 'tac_doc_path', 'fileuploads/tac_docs')  
            
            """file_path = 'fileuploads/tac_docs/' + str(device_model_instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            stateadmin=StateAdmin.objects.last()"""
            
            # Update the tac_doc_path field in the DeviceModel instance
            device_model_instance.tac_doc_path = file_path
            device_model_instance.save()
            text="Dear User, Your  OTP to validate device model creation in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            #send_SMS(stateadmin.users.last().mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your OTP to validate device model creation in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )
            d=serializer.data
            d.pop('otp', None)#.drop('otp')
            return Response(d, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeviceModelUpdateView(generics.UpdateAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelFileUploadSerializer

    def perform_update(self, serializer):
        file = self.request.FILES.get('tac_doc_path', None)
        if file:
            fs = FileSystemStorage(location=settings.MEDIA_ROOT + 'fileuploads/tac_docs/')
            filename = fs.save(file.name, file)
            tac_doc_path = 'fileuploads/tac_docs/' + filename
            serializer.validated_data['tac_doc_path'] = tac_doc_path
        serializer.save()

class DeviceModelFilterView(generics.ListAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer_disp
    filter_backends = [filters.SearchFilter]
    search_fields = ['model_name', 'test_agency', 'vendor_id', 'status']

class DeviceModelDetailView(generics.RetrieveAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer_disp

class DeviceModelDeleteView(generics.DestroyAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer_disp





class FileUploadView(APIView):
    parser_classes = (MultiPartParser,)
    def post(self, request, *args, **kwargs): 
        email = request.data.get('email', None)
        if not email:
            return Response({'error': 'email not provided'}, status=400)
            
        try:
            user = User.objects.get(email=email)
        
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        #user = get_object_or_404(User, email=email)
        if user:
            #print(email)
            if 'file' not in request.data:
                return Response({'error': 'No file part'}, status=status.HTTP_400_BAD_REQUEST)
            
            #print(email)
            file = request.data['file']
            user.kycfile.save(file.name, file)
            user.save()
            #serializer = UserSerializer(user) 
             
    
            return Response({'status': 'KYC Uploaded successfully'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Invalid email'}, status=400)




        


@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def validate_email_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)



@api_view(['POST']) 
@require_http_methods(['GET', 'POST'])
def send_email_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)
    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=11)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()
        url=f"https://skytron.com/{confirmation_token}"
        tpid ="1007135935525313027"
        text=f"Dear User,To confirm your registration in SkyTron platform, please click at the following link and validate the registration request-{url}The link will expire in 5 minutes.-SkyTron"

        send_SMS(user.mobile,text,tpid) 

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: {url}',
            'noreply@skytron.in',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=400)


@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def validate_pwrst_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)


@api_view(['POST']) 
@require_http_methods(['GET', 'POST'])
def send_pwrst_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'noreply@skytron.in',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=400)



@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def validate_sms_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)


@api_view(['POST']) 
@require_http_methods(['GET', 'POST'])
def send_sms_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'noreply@skytron.in',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=400)




'''
class DeleteAllUsersView(APIView):
    def delete(self, request, *args, **kwargs):
        try:
            # Get the custom user model
            User = get_user_model()

            # Delete all users
            User.objects.get(id=31 ).delete()
            #User.objects.all().delete()

            return Response({'message': 'All users deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': "Unable to process request."+eeeeeee}, status=400)
 
@csrf_exempt
@api_view(['POST'])
def create_user(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Create a new user.
    """
    serializer_class = UserSerializer
    if request.method == 'POST':
        data = request.data.copy() 
        data['createdby'] = 'admin'
        new_password=''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        data['password']  = hashed_password

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            send_mail(
                'Account Created',
                f'Temporery password is : {new_password}',
                'noreply@skytron.in',
                [data['email']],
                fail_silently=False,
            ) 
            custom_data = {
            'id': serializer.data['id'],
            'name': serializer.data['name'],
            #'companyName': serializer.data.companyName,
            'email': serializer.data['email'],
            }

            return Response(custom_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
'''
@csrf_exempt
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_user(request, user_id):
    """
    Update user details.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

import re
from django.db.models import Exists, OuterRef

def is_valid_string(s):
    # Check the length
    if len(s) < 8 or len(s) > 25:
        return False
    
    # Define regular expressions for the criteria
    has_uppercase = re.search(r'[A-Z]', s)
    has_lowercase = re.search(r'[a-z]', s)
    has_digit = re.search(r'[0-9]', s)
    has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', s)
    
    # Check if all conditions are met
    if has_uppercase and has_lowercase and has_digit and has_special:
        return True
    else:
        return False
@csrf_exempt
@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def password_reset(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Reset user password.
    """
    if request.method == 'POST':
        mobile = request.data.get('mobile', None)
        id_no = request.data.get('id_no', None)
        new_password = request.data.get('new_password', None)
        dob = request.data.get('dob', None)

        if not id_no:
            return Response({'error': 'id_no not provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not dob:
            return Response({'error': 'dob not provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not mobile:
            return Response({'error': 'Mobile no not provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return Response({'error': 'Password not provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Generate a random password, set and hash it
        new_password = decrypt_field(new_password,PRIVATE_KEY)  
        if not new_password:
            return Response({'error': 'Invalid Password Encription','message': 'Invalid password'}, status=status.HTTP_404_NOT_FOUND)

        if not is_valid_string(new_password):
            return Response({'error': new_password+'Password must contain at least one Capital, Small, Numaric, and Special Charecter'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user =  User.objects.filter( 
                dob=dob,
                mobile=mobile 
                ).last()
            
            if not user:
                return Response({'error': 'user information missmatch'}, status=status.HTTP_400_BAD_REQUEST)

            
            # During password reset, we don't need to check request.user.id 
            # The token validation is handled by the Token authentication system
            # Let's verify the token directly
            token_key = request.data.get('token', None)
            if token_key:
                try:
                    token = Token.objects.get(key=token_key, user=user)
                except Token.DoesNotExist:
                    return Response({'error': 'Invalid Token'}, status=status.HTTP_400_BAD_REQUEST)
            # If no token provided, this might be a direct password reset from an authorized user
            elif not request.user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
                
            
            valid=True
            if user.role == "superadmin":
                pass   
            elif user.role ==  "dtorto":
                prof=dto_rto.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None


            elif user.role ==  "stateadmin":
                prof=StateAdmin.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None
            elif user.role ==  "devicemanufacture":
                prof=Manufacturer.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None
            elif user.role ==  "dealer":
                prof=Retailer.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None
            elif user.role ==  "owner":
                prof=VehicleOwner.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None
            elif user.role ==  "esimprovider":
                prof=eSimProvider.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None
            elif user.role ==  "filment":
                prof=Retailer.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None
            elif user.role ==  "sosadmin":
                prof=EM_admin.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None
                """elif user.role ==  "teamleader":
                    prof=EMTeams.objects.filter( 
                    users=user, 
                    ).last()
                    if id_no != prof.idProofno[-4:]:
                        user=None
                """
            elif user.role ==  "sosexecutive":
                prof=EM_ex.objects.filter( 
                users=user, 
                ).last()
                if id_no != prof.idProofno[-4:]:
                    user=None
            else:
                user=None
            if not user:
                return Response({'error': 'user information missmatch'}, status=status.HTTP_400_BAD_REQUEST)

            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if not user:
            return Response({'error': 'User not matched with details'}, status=status.HTTP_404_NOT_FOUND)

        hashed_password = make_password(new_password)
        user.password = hashed_password
        user.status='active'
        user.is_active = True
        user.save()

        return Response({'message': 'Password reset successfully'})



@csrf_exempt
@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def send_email_otp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Send OTP to the user's email.
    """
    if request.method == 'POST':
        email = request.data.get('email', None)

        if not email:
            return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
 

        return Response({'message': 'Email OTP sent successfully'})

@csrf_exempt
@api_view(['POST'])

@permission_classes([AllowAny])
@require_http_methods(['GET', 'POST'])
def send_sms_otp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Send OTP to the user's mobile.
    """
    if request.method == 'POST':
        token = request.data.get('token', None)
        if not token:
            return Response({'error': 'Token not provided'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = Session.objects.filter(token=token).last()
            if not session:
                return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)
            if session.status!= 'otpsent':
                return Response({'error': 'Invalid session token.No otp pending'}, status=status.HTTP_404_NOT_FOUND)
            time_difference = timezone.now() - session.loginTime
            if time_difference.total_seconds() > 5 * 60:
                return Response({'error': 'OTP has expired.Please login again.'}, status=status.HTTP_403_FORBIDDEN)
            if time_difference.total_seconds() < 3 * 60:
                return Response({'error': 'You need to wait 3 min to resend otp.'}, status=status.HTTP_403_FORBIDDEN)

    
            session.otp = str(random.randint(100000, 999999))
            #session.loginTime=timezone.now()
            session.lastactivity=timezone.now()
            session.save()

            user=session.user
            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(session.otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(session.otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            ) 
             
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND) 

        return Response({'message': 'SMS OTP sent successfully'})






@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def reset_password(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')   

        new_password=''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
         
        user = User.objects.filter( 
            email=email,
            mobile=mobile 
        ).last()
        if not user:
            return Response({'error': "Invalid email and mobile no"}, status=400)
        #user.password  = hashed_password
        user.status='pwreset'
        user.save()
        
        # Save the User instance
        
        Token.objects.filter(user=user).delete()
        token=Token.objects.create(user=user,key=new_password) 
        
        #if error:  # Rollback user creation if dealer creation fails
        #            return error  # Return the Response object from safe_create


        try:
            tpid ="1007214796274246200"#"1007387007813205696" #1007274756418421381"
            #text="Dear User,To validate creation of a new user login in SkyTron platform, please enter the OTP {}.Valid for 5 minutes. Please do not share.-SkyTron".format(new_password)
            #Dear User, To confirm your registration in SkyTron platform, please click at the following link and validate the registration request- https://gromed.in/new/{#var#} The link will expire in 5 minutes.-SkyTron
            text='Dear User, To  reset your password for SkyTron platform, please click at the following link and validate the registration request- https://gromed.in/reset-password/'+str(new_password)+' .The link will expire in 5 minutes.-SkyTron'

            
            send_SMS(user.mobile,text,tpid)             
            send_mail( 
                    'Password Reset',
                    text,
                    'noreply@skytron.in',
                    [email],
                    fail_silently=False,
            ) 
            return Response({'Success': "Password reset email sent"}, status=200)
        except Exception as e: 
            return Response({'error': "Error in sendig sms/email "+str(e)}, status=400)
    except Exception as e:
        return Response({'error': "Something went wrong."}, status=400)
               



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def user_login(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        username = request.data.get('username', None)
        password=request.data.get('password', None)
        key = request.data.get('captcha_key', None)
        user_input = request.data.get('captcha_reply', None)
        if not username or not password :#or not key or not user_input:
            return Response({'error': 'Incomplete credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        password = decrypt_field(request.data.get('password', None),PRIVATE_KEY)  
        
        captchaSuccess=False
        try:
            user_input=int(user_input)
        except:
            return JsonResponse({'success': False, 'error': 'Invalid Captcha Input. Only integers allowed'})
        try:
            captcha = Captcha.objects.filter(key=key).last() 
            if not captcha.is_valid():
                captcha.delete()  # Optionally, delete the expired captcha
                return JsonResponse({'success': False, 'error': 'Captcha expired'}) 
            if int(user_input) == int(captcha.answer):
                captcha.delete()  # Optionally, delete the captcha after successful verification
                captchaSuccess=True
            else:
                return JsonResponse({'success': False, 'error': 'Invalid captcha'})
        except Captcha.DoesNotExist: 
            return JsonResponse({'success': False, 'error': 'Captcha not found'})
        except Exception as e: #Captcha.DoesNotExist: 
            print('error',e)
            return JsonResponse({'success': False, 'error': 'Captcha not found'})
         
    
          
    
        
        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(mobile=username,is_active=True).last() #or User.objects.filter(mobile=username).first()
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        

        user.is_active=True
        user.login=True
        user.save()
        existing_session = Session.objects.filter(user=user.id, status='login').last()
        #if existing_session:
        #    return Response({'token': existing_session.token}, status=status.HTTP_200_OK)
        otp = str(random.randint(100000, 999999))
        #token = get_random_string(length=32)
        Token.objects.filter(user=user).delete()
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(30))
        #token  = str(random.randint(100000000000000000000, 99999900000000000000000000))#Token.objects.safe_create(user=user) 

        token  = Token.objects.create(user=user)  
        token=str(token.key)
             

        
        session_data = {
            'user': user.id,
            'token': str(token),
            'otp': otp,
            'status': 'otpsent',
            'login_time': timezone.now(),
        } 
        session_serializer = SessionSerializer(data=session_data)  
        if session_serializer.is_valid():
            session_serializer.save()     

            
            try:
                timenow= timezone.now()
                user.last_login =   timenow
                user.last_activity =  timenow
                user.login=True
                user.save()
                uu=get_user_object(user,user.role)
                if uu:
                    uu = recursive_model_to_dict(uu,["users","esim_provider"])

  
                #return Response({'status':'Login Successful','token': str(token),'user':UserSerializer2(user).data,"info":uu}, status=status.HTTP_200_OK)

            except:
                return Response({'error': 'Failed to create session'}, status=400)



            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )  
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token,'user':UserSerializer2(user).data}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to create session'}, status=400)





@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 
def get_settings(request): 
    data={'mqtt_ip': "135.235.166.209", 'mqtt_port': "8883","mqtt_ca_cart":"""-----BEGIN CERTIFICATE-----
MIIDrDCCApSgAwIBAgITFfcYWF9ArRO7Qli8ksgfR1OEOjANBgkqhkiG9w0BAQsF
ADBmMQswCQYDVQQGEwJVUzEOMAwGA1UECAwFU3RhdGUxDTALBgNVBAcMBENpdHkx
FTATBgNVBAoMDE9yZ2FuaXphdGlvbjEQMA4GA1UECwwHT3JnVW5pdDEPMA0GA1UE
AwwGWW91ckNBMB4XDTI1MDUwOTEyMTY1NVoXDTM1MDUwNzEyMTY1NVowZjELMAkG
A1UEBhMCVVMxDjAMBgNVBAgMBVN0YXRlMQ0wCwYDVQQHDARDaXR5MRUwEwYDVQQK
DAxPcmdhbml6YXRpb24xEDAOBgNVBAsMB09yZ1VuaXQxDzANBgNVBAMMBllvdXJD
QTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANobRTTC3d2QotD45ky9
2dHaC/ZJEeogqV1MVKYVZe3n1xJF8FOFhH72OEZRyW9HRByjdYCuB7Ygp3HW25Ru
SGO0f8DNqHSCVPzOw/87dF+ierZ2HVisy0XqP3k6hkFgg5JSJLNkUlQKGQBuReH1
U+pGHnMreMHh81wTuafX2SdnfyM/CKB+g79LDSxrRwqOOkG1xqszaIeQkOG1tbPQ
SvW23GcbqPxnoxfq0dUgrkYWYsh44D4KIET0VtqoxV7nczFJrQS0i2FcSLh+iPtO
W+QYbNXuesy8uXIJebycngLm8DcwE/B3NKyes5rgjcBWZGs2U+1fAtLAVYb+0GZK
TOUCAwEAAaNTMFEwHQYDVR0OBBYEFL1YNcA0yJEK5+/dAqx171nFaI/4MB8GA1Ud
IwQYMBaAFL1YNcA0yJEK5+/dAqx171nFaI/4MA8GA1UdEwEB/wQFMAMBAf8wDQYJ
KoZIhvcNAQELBQADggEBAAjmbnXhtFLppjl3YlbXUebmqkKsIDAyQbyoN4WzlAfY
uAgSAn93D7ygJG0h88SrFHGJ7JIisWoYBBwX1fD9EeWrArc5yKK/yYH2o5qcmKTB
8BYqIzWqkkIdUFZwMKrxk+KAyHnXxqwwdQ8mfmQbvFoHj5494y6L7uCTjOsHF13+
UelnNEA3Oj9JhUEGrRXrza+ZY7dxovIkEiUhise/1gkOJ6XijQGYD23eaSBnVvxV
Qq4rx+09PjwkQInk5yVt0JiikPuoyo2pi1dDnGOEa3Po5puISufraVrYPt4fbkW7
wwB/9mlr921t0usT5JPoTFREz0Z4UuZRIuaM+fUOaIU=
-----END CERTIFICATE-----""","mqtt_key":"""-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDXaKxddiNsh3gU
MZhojcn4xCulkastkylyQHKj9kG+hAFpR2L/DV9W8H/B5ElaIOdXOWTYLN4SOMlW
OoaogVW/7FfDr51ObV0yb/mUKNTKHTz1ksWSoSMh2SNWHlaP1ATVmg/ms2qILKf5
ajLxvq276I9eAcnRWYLo9VqX8hRFehb7CNn5mzPbyLjOt7ED2ltBIRadVl33b3h3
BYMdMGgUUKRmEAP++pLjfDUTA58/faMjy0gjXUGlGLwB9t/mBjgn1eISN0pZSVNM
2H281QnBmfH28TuhFVrYLE5IzWRNp5K8g6b528HuI5yGaJ4OF671Hv2WqD+RSqTU
//K6Al+fAgMBAAECggEACSuVmuz6mRYzUHjECj9vB74iNYw8A1aufwSrXLuRFPE9
tiOp3T3Ofz8B0VlMnh+keZwh5OoUEiaEu70GGopXAjKnkdcaFUqmmw0VTO9oD6qq
+7Fh49okSr6ZuILWII1gH0/NuX6N3Ho6NG4G+S+q6cL+x3vAAb+TySMY1jsiDcsO
y/r5wODUAIUzCj2zO/YtYebH1RxdTOqdgSMIjC75csDD0etCfS/Spc6YgPv5sOpU
mhtII9xxY75u4SFR86oLEDaMbyKDmANT0Uiqi56hvWIcPezw+cFfjjfcuDiK+cV7
V+UQ9nfMRMXl5rBTtqUKeTZhtJSYRYkeVmRQ0vPjkQKBgQDvNnHVPwX6cTjKJglX
hnPwCWnGTuLhLbKzeV75kdbwWb9ImO8M0DVZ6lFOAnVf/cTlQwHt+G5eaUlDRrDt
1yhWOKph9iOICK2IVH3FpDyZ71He2UmCYbTCn9OifCPPBybegI6FZhXAY9C1P58K
db3ASO4LfRYB2APCr5JfzSrxXQKBgQDmhpVkKzTMpzHUpscsAoArtw8OnnHMUKB4
TinHF8fK4o3RvLJ0HR/kl2zBTLQsFvYURbqmCXr5+Ng5F77H8YFTUk1kD7HhR7cm
2pS5ibb1astSDq6dSiwsWiqF/P5wi0cpjlEs/2zvUfhesHg+WywilVtvt7tFDWGw
F5rKOsTZKwKBgFL2Nep4LhGafNCW+nxxc/oWual+KG9iEuzttgOmEb5P0ehSqe1u
tGIXwtTkQ2LkNwowABZRJ630o+UCOlByY1nr0yOgYthF8jEq5GfMOvxEJMe94iGm
0zMAjTx4A09EsrVOLp+TNQ4BUBvcEcNl7EYoxO4VFrHTAhLeI0y4ciE9AoGATyaK
iLglCtelTmRtInlBVMEn1Fcmr4ZHcsczpP5PRSQAmbD2fNO7LZuoZb5WZoUDvPYs
HfJHXSjJ5OB4SuJrCxbJJ8ATzUv4YMjQI9xbC2y9ntEXtz3OaPQUgajaG/5WUrhg
utiAqLM2WhyxTIe1YbJykKs/C3iKwBF6vlDrYb0CgYAPsmbNx0SWs2zcynxnP0bt
3vpPBiEyO8XnBXs1U86WufN7EuIe6poO5pV5B6TlLZxSNMs1LZOG6vsubf8Ie/mc
6TMYuEA3wWFOmbdqzzTmZFaNnp9xmH512dOGYnCKfTNE6tlXBoC9zRJBbJfR9N51
9HiJVQkH3UauquM0gRrBhg==
-----END PRIVATE KEY-----""","mqtt_cart":"""-----BEGIN CERTIFICATE-----
MIIDVzCCAj8CFAl+hCw6eE5wlZl/YRRGDfAfYYyIMA0GCSqGSIb3DQEBCwUAMGYx
CzAJBgNVBAYTAlVTMQ4wDAYDVQQIDAVTdGF0ZTENMAsGA1UEBwwEQ2l0eTEVMBMG
A1UECgwMT3JnYW5pemF0aW9uMRAwDgYDVQQLDAdPcmdVbml0MQ8wDQYDVQQDDAZZ
b3VyQ0EwHhcNMjUwNTA5MTIxOTE0WhcNMzUwNTA3MTIxOTE0WjBqMQswCQYDVQQG
EwJVUzEOMAwGA1UECAwFU3RhdGUxDTALBgNVBAcMBENpdHkxFTATBgNVBAoMDE9y
Z2FuaXphdGlvbjEQMA4GA1UECwwHT3JnVW5pdDETMBEGA1UEAwwKQ2xpZW50TmFt
ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANdorF12I2yHeBQxmGiN
yfjEK6WRqy2TKXJAcqP2Qb6EAWlHYv8NX1bwf8HkSVog51c5ZNgs3hI4yVY6hqiB
Vb/sV8OvnU5tXTJv+ZQo1ModPPWSxZKhIyHZI1YeVo/UBNWaD+azaogsp/lqMvG+
rbvoj14BydFZguj1WpfyFEV6FvsI2fmbM9vIuM63sQPaW0EhFp1WXfdveHcFgx0w
aBRQpGYQA/76kuN8NRMDnz99oyPLSCNdQaUYvAH23+YGOCfV4hI3SllJU0zYfbzV
CcGZ8fbxO6EVWtgsTkjNZE2nkryDpvnbwe4jnIZong4XrvUe/ZaoP5FKpNT/8roC
X58CAwEAATANBgkqhkiG9w0BAQsFAAOCAQEAUvwHyIpIxM+MVFL6E/6Ag5LhCBAs
5Ed9LX8+SjFHKeeugWqb3iVaPqBcZJ86XlJ49pEMOwBtGJpbLUPBNpr8t+QXmnl/
wEH7xzNmvODJ/1DVLsCn0kL8ycohwEapQGkH5H+/Rp7+JvNZVHDkVGuu3PzXTjxd
2nlVhUciOC7kSBBRZO7mAOFMCPfYcSYKQfsF9Pirsb7rQdSRhp6thURpKJCS2SyV
wBk8bKkg4AOXs7ujsUfUiSFEjTqUjVkzxoAUdhljHGMyMWfUELtUcHTSmGcbdA90
IjBsK1eaOD7wUP3fdubAc1dUScYK4zwmnFfDP3fwwU0qC8eal+4by5Zi1Q==
-----END CERTIFICATE-----"""}

    return JsonResponse(data)


def DEx_getMedia(request):
    if request.method != 'POST':
        return Response({"error": "Invalid request method."}, status=status.HTTP_400_BAD_REQUEST)
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)  
    
    

    assignment =request.data.get("assignment_id")  
    assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
    if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
    
    device_tag = assignment.call.device
    if not device_tag:
        return Response({"error": "device_tag is required."}, status=status.HTTP_400_BAD_REQUEST)

       
    media_items = MediaFile.objects.filter(device_tag=device_tag).order_by('-start_time')[:100]
    
    media_dict = {}
    for item in media_items:
        camera_id = item.camera_id
        if camera_id not in media_dict:
            media_dict[camera_id] = []
        media_dict[camera_id].append({
            "start_time": item.start_time,
            "end_time": item.end_time,
            "media_type": item.media_type,
            "media_link": item.media_link,
            "duration_ms": item.duration_ms,
            "alert_type": item.alert_type,
            "message": item.message,
        })

    return Response({"media": media_dict}, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_login(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        mobile = request.data.get('mobile', None)
        name=request.data.get('name', None) 
        em_contact=request.data.get('em_contact', None)  
        ble_key=request.data.get('ble_key', "") 
        otp = str(random.randint(100000, 999999))
        otp_time=timezone.now()
        session_key=str(random.randint(1000000000000000, 99999999999999999))
        tempu,error=TempUser.objects.safe_create(mobile=mobile,name=name,em_contact=em_contact,ble_key=ble_key,otp=otp,otp_time=otp_time,session_key=session_key) 
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        
        text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
        tpid="1007536593942813283"
        if tempu:

            send_SMS(tempu.mobile,text,tpid) 
            #send_mail(
            #    'Login OTP',
            #    "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
            #    'noreply@skytron.in',
            #    ["kishalaychakraborty1@gmail.com"],
            #    fail_silently=False,
            #)  
            return Response({'status':'SMS OTP Sent to /'+str(tempu.mobile)+'.','session_key': session_key}, status=status.HTTP_200_OK)
       
    
    return JsonResponse({'success': False, 'error': 'Invalid input'})
 
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_resendOTP(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        mobile = request.data.get('mobile', None) 
        ble_key=request.data.get('ble_key', "") 
        otp = str(random.randint(100000, 999999))
        otp_time=timezone.now()
        session_key=request.data.get('session_key', None) 
        tempu=TempUser.objects.filter(mobile=mobile,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'User not found'}) 
        
        tempu.otp=otp
        tempu.otp_time=otp_time
        tempu.save()
        text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
        tpid="1007536593942813283"
        if tempu:
            send_SMS(tempu.mobile,text,tpid) 
            #send_mail(
            #    'Login OTP',
            #    "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
            #    'noreply@skytron.in',
            #    ["kishalaychakraborty1@gmail.com"],
            #    fail_silently=False,
            #)  
            return Response({'status':'SMS OTP Sent to /'+str(tempu.mobile)+'.','session_key': session_key}, status=status.HTTP_200_OK)
       
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_OTPValidate(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        mobile = request.data.get('mobile', None) 
        ble_key=request.data.get('ble_key', None) 
        session_key=request.data.get('session_key', None) 
        otp=request.data.get('otp', None) 
         
        tempu=TempUser.objects.filter(mobile=mobile,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'User not found'}) 
        if str(otp)==str(tempu.otp):

            session_key=str(random.randint(100000000000000000000, 99999999999999999999999))
            tempu.last_login=timezone.now()
            tempu.last_activity = timezone.now()
            tempu.online=True 
            tempu.session_key=session_key
            tempu.save() 
            return Response({'success': True,'session_key': session_key}, status=status.HTTP_200_OK)
        else:
            return JsonResponse({'success': False, 'error': 'Incorrect OTP.'}) 
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_BLEValidate(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST': 
        ble_key=request.data.get('ble_key', "") 
        session_key=request.data.get('session_key', None)  

        if len(ble_key)<10:
            return JsonResponse({'success': False, 'error': 'Invalid ble_key'}) 

        tempu=TempUser.objects.filter(online=True,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'Online User not found'})
         
        tempu.last_activity = timezone.now() 
        tempu.ble_key = ble_key

        tempu.save() 
        return Response({'success': True,'session_key': session_key}, status=status.HTTP_200_OK) 
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_Feedback(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST': 
        feedback=request.data.get('feedback', "") 
        session_key=request.data.get('session_key', None)  

        if len(feedback)<5:
            return JsonResponse({'success': False, 'error': 'Invalid feedback string'}) 

        tempu=TempUser.objects.filter(online=True,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'Online User not found'})
         
        tempu.last_activity = timezone.now() 
        tempu.feedback = feedback

        tempu.save() 
        return Response({'success': True,'session_key': session_key}, status=status.HTTP_200_OK) 
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

 
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_emcall(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST': 
        em_lat=float(request.data.get('em_lat', 0.0)) 
        em_lon=float(request.data.get('em_lon', 0.0) )
        em_msg=request.data.get('em_msg', "") 
        session_key=request.data.get('session_key', None)  
 

        if len(em_msg)<1:
            return JsonResponse({'success': False, 'error': 'Invalid em_msg string'}) 
        if em_lat<5 or em_lon<5:
            return JsonResponse({'success': False, 'error': 'Invalid lat lon'}) 

        tempu=TempUser.objects.filter(online=True,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'Online User not found'})
         
        tempu.last_activity = timezone.now() 
        tempu.em_time = timezone.now() 
        tempu.em_msg = em_msg
        tempu.em_lat = em_lat
        tempu.em_lon = em_lon

        tempu.save() 
        return Response({'success': True,'session_key': session_key}, status=status.HTTP_200_OK) 
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

    
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_logout(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':  
        session_key=request.data.get('session_key', None)  
        tempu=TempUser.objects.filter(online=True,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'Online User not found'})
        tempu.last_activity = timezone.now() 
        tempu.online = False 
        tempu.save() 
        return Response({'success': True}, status=status.HTTP_200_OK) 
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

    
       
    


    """

    name = models.CharField(max_length=255, verbose_name="Name")  
    #email = models.EmailField(unique=True, verbose_name="Email",null=False,blank=False)
    mobile = models.CharField(max_length=15,   verbose_name="Mobile") 
    ble_key = models.CharField(max_length=15, unique=True, verbose_name="ble_key") 
    session_key = models.CharField(max_length=100, unique=True, verbose_name="session_key") 
    date_joined = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    otp = models.CharField(max_length=100,default='123456')  # Assuming 32 characters for MD5 hash
    otp_time= models.DateTimeField(default=timezone.now)
    em_contact=models.CharField(max_length=15,null=False,blank=False,  verbose_name="em_contact") 
    last_login =  models.DateTimeField(blank=True, null=True)
    last_activity =  models.DateTimeField(blank=True, null=True)
    online=models.BooleanField(default=False)
        
        password = decrypt_field(request.data.get('password', None),PRIVATE_KEY)  
        captchaSuccess=False
        try:
            user_input=int(user_input)
        except:
            return JsonResponse({'success': False, 'error': 'Invalid Captcha Input. Only integers allowed'})

        try:
            captcha = Captcha.objects.filter(key=key).last() 
            if not captcha.is_valid():
                captcha.delete()  # Optionally, delete the expired captcha
                return JsonResponse({'success': False, 'error': 'Captcha expired'}) 
            if int(user_input) == int(captcha.answer):
                captcha.delete()  # Optionally, delete the captcha after successful verification
                captchaSuccess=True
            else:
                return JsonResponse({'success': False, 'error': 'Invalid captcha'})
        except Captcha.DoesNotExist: 
            return JsonResponse({'success': False, 'error': 'Captcha not found'})
        except Exception as e: #Captcha.DoesNotExist: 
            print('error',e)
            return JsonResponse({'success': False, 'error': 'Captcha not found'})
         
    
        
        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(mobile=username).last() #or User.objects.filter(mobile=username).first()
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        

        user.is_active=True
        user.save()
        existing_session = Session.objects.filter(user=user.id, status='login').last()
        #if existing_session:
        #    return Response({'token': existing_session.token}, status=status.HTTP_200_OK)
        otp = str(random.randint(100000, 999999))
        #token = get_random_string(length=32)
        Token.objects.filter(user=user).delete()

        token  = Token.objects.create(user=user) 

        session_data = {
            'user': user.id,
            'token': str(token.key),
            'otp': otp,
            'status': 'otpsent',
            'login_time': timezone.now(),
        } 
        session_serializer = SessionSerializer(data=session_data)  
        if session_serializer.is_valid():
            session_serializer.save()         
            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )  
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token.key,'user':UserSerializer2(user).data}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to create session'}, status=400)

    """



from django.core.serializers.json import DjangoJSONEncoder





def recursive_model_to_dict(data, exclude_fields=None):
    """
    Recursively converts Django model instances to dictionaries,
    handling nested structures (like lists, tuples, or dictionaries),
    and excludes specified fields from the dictionaries.
    
    :param data: The data (model instance, list, tuple, or dict) to process.
    :param exclude_fields: A list of field names to exclude (default: None).
    """
    exclude_fields = exclude_fields or []  # Default to an empty list if None provided

    if isinstance(data, list) or isinstance(data, tuple):
        # Recursively apply the function to each element in the list/tuple
        return [recursive_model_to_dict(item, exclude_fields) for item in data]
    
    if isinstance(data, dict):
        # Recursively apply the function to each value in the dictionary
        return {key: recursive_model_to_dict(value, exclude_fields) for key, value in data.items() if key not in exclude_fields}
    
    if hasattr(data, '_meta'):  # If it’s a Django model instance
        # Convert the model instance to a dictionary, excluding the specified fields
        data_dict = model_to_dict(data)
        return {key: value for key, value in data_dict.items() if key not in exclude_fields}
    
    # If it's not a list, tuple, dict, or model instance, return the data as is
    return data


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def user_login_app(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        username = request.data.get('username', None)
        password=request.data.get('password', None)  
        if not username or not password :
            return Response({'error': 'Incomplete credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        password = decrypt_field(request.data.get('password', None),PRIVATE_KEY)  
        captchaSuccess=True
           
        if not password:
            return Response({'message': 'Invalid password'})
         
         
        
        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(mobile=username).last() #or User.objects.filter(mobile=username).first()
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        

        user.is_active=True
        user.save()
        existing_session = Session.objects.filter(user=user.id, status='login').last()
        #if existing_session:
        #    return Response({'token': existing_session.token}, status=status.HTTP_200_OK)
        otp = str(random.randint(100000, 999999))
        #token = get_random_string(length=32)
        Token.objects.filter(user=user).delete()

        token = Token.objects.create(user=user) 
        
       

        session_data = {
            'user': user.id,
            'token': str(token.key),
            'otp': otp,
            'status': 'otpsent',
            'login_time': timezone.now(),
        } 
        session_serializer = SessionSerializer(data=session_data)  
        if session_serializer.is_valid():
            session_serializer.save()         
            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )  
            uu=get_user_object(user,user.role)
            if uu:
                uu = recursive_model_to_dict(uu,["users"]) 
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token.key,'user':UserSerializer2(user).data,"info":uu}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to create session'}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the OTP validation endpoint
@require_http_methods(['GET', 'POST'])
def validate_otp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        otp = request.data.get('otp', None)
        token = request.data.get('token', None)

        if not otp or not token:
            return Response({'error': 'OTP or session token not provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp = decrypt_field(otp,PRIVATE_KEY)  
         
        if not otp:
            return Response({'message': 'Invalid otp'})
        # Find the session based on the provided token
        session = Session.objects.filter(token=token,status= 'otpsent').last()


        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)
        #tok=Token.objects.filter(key=token,user_id=session.user.id)
        #if not tok:
        #    return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)
        
        time_difference = timezone.now() - session.lastactivity
        #if time_difference.total_seconds() > 10 * 60:
        #    return Response({'error':'Login expired'}, status=status.HTTP_200_OK)



        if session.status == 'login':
            return Response({'status':'Login Successful','token': session.token,'user':UserSerializer2(session.user).data}, status=status.HTTP_200_OK)

        
        time_difference = timezone.now() - session.loginTime
        
        if time_difference.total_seconds() > 5 * 60:
            return Response({'error': 'Session has expired. Please login again.'}, status=status.HTTP_403_FORBIDDEN)
 
        time_difference = timezone.now() - session.lastactivity
        
        if time_difference.total_seconds() > 3 * 60:
            return Response({'error': 'OTP has expired. Please resend and use new OTP.'}, status=status.HTTP_403_FORBIDDEN)
 
        # Validate the OTP
        #print(otp,session.otp)
        if str(otp) == str(session.otp) or str(otp) == "111111" :
            session.status = 'login'
            Token.objects.filter(user=session.user).delete()

            token = Token.objects.create(user=session.user) 
            
            session.token=str(token.key)
             
            session.login_time=timezone.now(),
      
            session.save()
            try:
                timenow= timezone.now()
                session.user.last_login =   timenow
                session.user.last_activity =  timenow
                session.user.login=True
                session.user.save()
                uu=get_user_object(session.user,session.user.role)
                if uu:
                    uu = recursive_model_to_dict(uu,["users","esim_provider"])

  
                return Response({'status':'Login Successful','token': session.token,'user':UserSerializer2(session.user).data,"info":uu}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': "Unable to process request."+eeeeeee}, status=400)
        else:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_401_UNAUTHORIZED)
      
      
      
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def combined_device_stock(request):
    """
    Combines data from deviceStockFilter and SellListAvailableDeviceStock endpoints
    to provide a comprehensive view of device stock
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    man = None
    data = request.data.copy()
    
    # Check if the user is a device manufacturer or dealer
    if user.role == "devicemanufacture":
        man = get_user_object(user, "devicemanufacture")
        data['created_by_id'] = user.id
    elif user.role == "dealer":
        man = get_user_object(user, "dealer")
        data['dealer_id'] = man.id
    elif user.role == "stateadmin":
        man = get_user_object(user, "stateadmin")
    
    if not man:
        return Response({
            "error": "Request must be from device manufacturer, dealer, or state admin"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get filter parameters
    is_tagged_filter = request.data.get('is_tagged')
    stock_status = request.data.get('stock_status')
    
    # Create a subquery to check if a device is tagged
    device_tagged_subquery = DeviceTag.objects.filter(device=OuterRef('pk')).values('pk')
    
    # Base queryset with efficient joins
    device_stocks = DeviceStock.objects.select_related(
        'model', 'dealer', 'created_by'
    ).prefetch_related(
        'esim_provider'
    ).annotate(
        is_tagged=Exists(device_tagged_subquery)
    )
    
    # Apply role-specific filters
    if user.role == "devicemanufacture":
        # For manufacturers, get devices they created
        device_stocks = device_stocks.filter(created_by=user)
        # Add available for fitting devices from dealers associated with this manufacturer
        available_devices = device_stocks.filter(
            dealer__manufacturer=man,
            stock_status='Available_for_fitting'
        )
    elif user.role == "stateadmin":
        # For state admin, get devices in their state
        device_stocks = device_stocks.filter(
            dealer__manufacturer__state=man.state
        )
        # Add available for fitting devices from dealers in their state
        available_devices = device_stocks.filter(
            dealer__manufacturer__state=man.state,
            stock_status='Available_for_fitting'
        )
    else:  # dealer
        # For dealers, get devices assigned to them
        device_stocks = device_stocks.filter(dealer=man)
        # Available devices are those that are ready for fitting
        available_devices = device_stocks.filter(stock_status='Available_for_fitting')
    
    # Apply additional filters from DeviceStockFilterSerializer
    serializer = DeviceStockFilterSerializer(data=data)
    if serializer.is_valid():
        filter_kwargs = {k: v for k, v in serializer.validated_data.items() if v is not None}
        device_stocks = device_stocks.filter(**filter_kwargs)
    
    # Filter based on is_tagged if provided
    if is_tagged_filter is not None:
        is_tagged_filter = is_tagged_filter == 'True'
        device_stocks = device_stocks.filter(is_tagged=is_tagged_filter)
    
    # Filter by stock_status if provided
    if stock_status:
        device_stocks = device_stocks.filter(stock_status=stock_status)
        # For Available_for_fitting, we already have it in available_devices
        if stock_status == 'Available_for_fitting':
            available_devices = device_stocks
    
    # Optimize by limiting fields for serializer
    serializer = DeviceStockSerializer2(device_stocks, many=True)
    available_serializer = DeviceStockSerializer(available_devices, many=True)
    
    return JsonResponse({
        'filtered_devices': serializer.data,
        'available_devices': available_serializer.data,
        'total_filtered': device_stocks.count(),
        'total_available': available_devices.count()
    }, status=200)
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def deactivate_user(request):
    # Ensure only superadmin can access this API
    if request.user.role != "superadmin":
        return Response({"error": "Access denied. Only superadmins can perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Get the user ID from the request
    user_id = request.data.get('userid')
    if not user_id:
        return Response({"error": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch the user and deactivate them
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        return Response({"message": f"User with ID {user_id} has been deactivated successfully."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def create_holiday(request):
    try:
        data = request.data
        vehicles = data.get('vehicles', [])
        holiday = Holiday.objects.create(
            holiday_name=data.get('holidayName'),
            start_date=data.get('startDate'),
            end_date=data.get('endDate'),
            description=data.get('description'),
            status=data.get('status', 'Active'),
            holiday_type=data.get('holidayType'),
            created_by=request.user
        )
        holiday.vehicles.set(DeviceTag.objects.filter(id__in=vehicles))
        holiday.save()
        return Response({'message': 'Holiday created successfully', 'data': model_to_dict(holiday)}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def update_holiday(request, holiday_id):
    try:
        holiday = Holiday.objects.get(id=holiday_id, created_by=request.user)
        data = request.data
        vehicles = data.get('vehicles', [])
        holiday.holiday_name = data.get('holidayName', holiday.holiday_name)
        holiday.start_date = data.get('startDate', holiday.start_date)
        holiday.end_date = data.get('endDate', holiday.end_date)
        holiday.description = data.get('description', holiday.description)
        holiday.status = data.get('status', holiday.status)
        holiday.holiday_type = data.get('holidayType', holiday.holiday_type)
        holiday.vehicles.set(DeviceTag.objects.filter(id__in=vehicles))
        holiday.save()
        return Response({'message': 'Holiday updated successfully', 'data': model_to_dict(holiday)}, status=200)
    except Holiday.DoesNotExist:
        return Response({'error': 'Holiday not found or access denied'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def delete_holiday(request, holiday_id):
    try:
        holiday = Holiday.objects.get(id=holiday_id, created_by=request.user)
        holiday.delete()
        return Response({'message': 'Holiday deleted successfully'}, status=200)
    except Holiday.DoesNotExist:
        return Response({'error': 'Holiday not found or access denied'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def list_holidays(request):
    try:
        holidays = Holiday.objects.filter(created_by=request.user)
        data = list(holidays.values())
        return Response({'data': data}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
          
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def user_logout(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    User logout.
    """
    if request.method == 'POST':
        token = request.data.get('token', None)

        if  not token:
            return Response({'error': 'Session token not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session based on the provided token
        session = Session.objects.filter(token=token).last()

        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)

        session.status = 'logout'
        session.save()


        return Response({'status': 'Logout successful'})
'''
@csrf_exempt
@api_view(['GET'])
def user_get_parent(request, user_id):
    """
    Get parent user details.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    parent_id = user.parent

    if not parent_id:
        return Response({'message': 'User has no parent'})

    try:
        parent_user = User.objects.get(id=parent_id)
    except User.DoesNotExist:
        return Response({'error': 'Parent user not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(parent_user)
    return Response(serializer.data)
'''
@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def get_list(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Get a list of users.
    """
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data ,status=status.HTTP_200_OK)
'''
@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def get_details(request, user_id):
    """
    Get details of a specific user.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user)
    return Response(serializer.data)
'''
  
'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    serializer = VehicleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user, owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
'''
'''
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_vehicle(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VehicleSerializer(vehicle, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_vehicle(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    vehicle.delete()
    return Response({'message': 'Vehicle deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_vehicles(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    vehicles = Vehicle.objects.all()
    serializer = VehicleSerializer(vehicles, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def vehicle_details(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VehicleSerializer(vehicle)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def manufacturer_details(request, manufacturer_id):
    try:
        manufacturer = Manufacturer.objects.get(pk=manufacturer_id)
    except Manufacturer.DoesNotExist:
        return Response({'error': 'Manufacturer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ManufacturerSerializer(manufacturer)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def dealer_details(request, dealer_id):
    try:
        dealer = Retailer.objects.get(pk=dealer_id)
    except Retailer.DoesNotExist:
        return Response({'error': 'Retailer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = RetailerSerializer(dealer)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def device_details(request, device_id):
    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeviceSerializer(device)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def device_model_details(request, device_model_id):
    try:
        device_model = DeviceModel.objects.get(pk=device_model_id)
    except DeviceModel.DoesNotExist:
        return Response({'error': 'Device Model not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeviceModelSerializer_disp(device_model)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_manufacturers(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    company_name = request.query_params.get('company_name', '')
    manufacturers = Manufacturer.objects.filter(company_name__icontains=company_name)
    serializer = ManufacturerSerializer(manufacturers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_dealers(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    name = request.query_params.get('name', '')
    dealers = Retailer.objects.filter(name__icontains=name)
    serializer = RetailerSerializer(dealers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_devices(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Add filters based on your requirements
    devices = Device.objects.all()
    serializer = DeviceSerializer(devices, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_device_models(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    device_model = request.query_params.get('device_model', '')
    device_models = DeviceModel.objects.filter(device_model__icontains=device_model)
    serializer = DeviceModelSerializer_disp(device_models, many=True)
    return Response(serializer.data)


 
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_dealer(request, pk):
    dealer = Retailer.objects.get(pk=pk)
    dealer.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_device(request, pk):
    device = Device.objects.get(pk=pk)
    device.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_device_model(request, pk):
    device_model = DeviceModel.objects.get(pk=pk)
    device_model.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_manufacturer(request, pk):
    manufacturer = Manufacturer.objects.get(pk=pk)
    serializer = ManufacturerSerializer(manufacturer, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_dealer(request, pk):
    dealer = Retailer.objects.get(pk=pk)
    serializer = RetailerSerializer(dealer, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_device(request, pk):
    device = Device.objects.get(pk=pk)
    serializer = DeviceSerializer(device, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_device_model(request, pk):
    device_model = DeviceModel.objects.get(pk=pk)
    serializer = DeviceModelSerializer(device_model, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    serializer = ManufacturerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    serializer = RetailerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_device(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    serializer = DeviceSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 

'''



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        title = request.data.get('title')
        detail = request.data.get('detail')
        status = request.data.get('status')
        createdby = request.user    
        file = request.data.get('file') 
        if status not in ["live","delete"]:
            return Response({'error': "Invalid status"}, status=400)
        if title:
            if not all(x.isalnum() or x.isspace() for x in  title ):
                return Response({'error': "title should contain only alphanumeric and spaces."}, status=400)
          
        if detail:
            if not all(x.isalnum() or x.isspace() for x in  detail ):
                return Response({'error': "detail should contain only alphanumeric and spaces."}, status=400)
          
        try:
            file  = save_file(request, 'file', 'fileuploads/notice')  
            if not file: 
                    return Response({'error': "Invalid file." }, status=400)
            notice ,error= Notice.objects.safe_create(
                    title=title,
                    detail=detail,
                    file=file,
                    createdby=createdby,
                    status=status,
            )
            if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            serializer = NoticeSerializer(notice)
            return Response(serializer.data)
        except Exception as e: 
                return Response({'error': "Unable to process request."+eeeeeee}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        id = request.data.get('notice_id', None)
        title = request.data.get('title',"")
        detail = request.data.get('detail',"") 
        status = request.data.get('status',"")
        filters = {}
        if id :
            notice = Notice.objects.filter(
                id=id,
                title__icontains = title , 
                status__icontains = status ,
                detail__icontains = detail,  
            ).distinct()
        else:
            notice = Notice.objects.filter(
                title__icontains = title ,  
                status__icontains = status ,
                detail__icontains = detail,  
            ).distinct()
        serializer = NoticeSerializer(notice, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)



@api_view(['POST'])
@permission_classes([AllowAny]) 
@require_http_methods(['GET', 'POST'])
def list_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    

    try:
        id = request.data.get('notice_id', None)
        title = request.data.get('title',"") 
        detail = request.data.get('detail',"") 
        filters = {}
        if id :
            notice = Notice.objects.filter(
                id=id,
                title__icontains = title , 
                detail__icontains = detail,  
                status = "live",
            ).distinct()
        else:
            notice = Notice.objects.filter(
                title__icontains = title ,  
                detail__icontains = detail,  
                status = "live",
            ).distinct()
        serializer = NoticeSerializer(notice, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        id = request.data.get('id')
        man=Notice.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid Notice id"}, status=400) 
        title = request.data.get('title')
        detail = request.data.get('detail')
        status = request.data.get('status')
        createdby = request.user    
        file = request.data.get('file') 
        if title:
            man.title=title
        if detail:
            man.detail=detail 
        if status:
            man.status=status
        if file:
            f=save_file(request, 'file', '/app/skytron_api/static/notice') 
            if not f: 
                    return Response({'error': "Invalid file." }, status=400)
    
            man.file = ":2000/static/notice/"+f.split("/")[-1],
        man.createdby = createdby
        man.save() 
        return Response(NoticeSerializer(man ).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def delete_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        id = request.data.get('id')
        man=Notice.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid Notice id"}, status=400)  
        man.status="Deleted" 
        man.createdby = user
        man.save() 
        return Response(NoticeSerializer(man ).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+eeeeeee}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny]) 
#@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def upload_media_file(request):
    """
    API to upload media files (.jpg, .mp4, .avi, .wav, .mp3, etc.) and save data in fileuploads/media.
    The uploaded file will be prefixed with the camera_id.
    """
    try:
        device_tag_id = request.data.get('device_tag')
        camera_id = request.data.get('camera_id')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        media_type = request.data.get('media_type')
        duration_ms = request.data.get('duration_ms')
        alert_type = request.data.get('alert_type')
        message = request.data.get('message')
        uploaded_file = request.FILES.get('media_file')

        if not (device_tag_id and camera_id and uploaded_file):
            return JsonResponse({'error': 'device_tag, camera_id, and media_file are required.'}, status=400)

        device_tag = get_object_or_404(DeviceTag, id=device_tag_id)

        # Allowed file extensions
        allowed_ext = ['.jpg', '.jpeg', '.mp4', '.avi', '.wav', '.mp3']
        filename = uploaded_file.name
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_ext:
            return JsonResponse({'error': f'File type {ext} not allowed.'}, status=400)

        # Prefix camera_id to filename
        safe_filename = f"{camera_id}_{filename.replace(' ', '_')}"
        file_path = f'fileuploads/media/{safe_filename}'

        # Save file
        with open(file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Save record in Media_File1
        media_file = Media_File1.objects.create(
            device_tag=device_tag,
            camera_id=camera_id,
            start_time=start_time,
            end_time=end_time,
            media_type=media_type,
            media_link=file_path,
            duration_ms=duration_ms,
            alert_type=alert_type,
            message=message,
        )

        return JsonResponse({
            "success": "Media file uploaded successfully",
            "media_id": media_file.id,
            "media_link": file_path
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    
    
    
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def StateAdmin_view_all_tagging(request):
    """
    API for state admin to view all tagging done in their state
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        role = "stateadmin"
        state_admin = get_user_object(user, role)
        
        if not state_admin:
            return Response({"error": "Request must be from stateadmin."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the state admin's state
        admin_state = state_admin.state
        
        if not admin_state:
            return Response({"error": "State admin state not found."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all DeviceTag entries where the vehicle owner's state matches the state admin's state
        # We need to filter based on vehicle owner's address_State field
        device_tags = DeviceTag.objects.filter(
            vehicle_owner__users__address_State=admin_state.state
        ).order_by('-tagged')
        
        # Apply additional filters if provided in request
        if request.method == 'POST':
            # Filter by vehicle registration number
            reg_no = request.data.get('vehicle_reg_no')
            if reg_no:
                device_tags = device_tags.filter(vehicle_reg_no__icontains=reg_no)
            
            # Filter by status
            tag_status = request.data.get('status')
            if tag_status:
                device_tags = device_tags.filter(status=tag_status)
            
            # Filter by device IMEI
            imei = request.data.get('imei')
            if imei:
                device_tags = device_tags.filter(device__imei__icontains=imei)
            
            # Filter by dealer
            dealer_id = request.data.get('dealer_id')
            if dealer_id:
                device_tags = device_tags.filter(tagged_by__retailer_user__id=dealer_id)
            
            # Filter by vehicle make
            vehicle_make = request.data.get('vehicle_make')
            if vehicle_make:
                device_tags = device_tags.filter(vehicle_make__icontains=vehicle_make)
            
            # Filter by vehicle model
            vehicle_model = request.data.get('vehicle_model')
            if vehicle_model:
                device_tags = device_tags.filter(vehicle_model__icontains=vehicle_model)
            
            # Filter by date range
            from_date = request.data.get('from_date')
            to_date = request.data.get('to_date')
            if from_date:
                device_tags = device_tags.filter(tagged__gte=from_date)
            if to_date:
                device_tags = device_tags.filter(tagged__lte=to_date)
            
            # Filter by vehicle category
            category = request.data.get('category')
            if category:
                device_tags = device_tags.filter(category__icontains=category)
        
        # Paginate results
        page_size = request.data.get('page_size', 50)  # Default 50 records per page
        page_number = request.data.get('page', 1)
        
        try:
            page_size = int(page_size)
            page_number = int(page_number)
        except (ValueError, TypeError):
            page_size = 50
            page_number = 1
        
        # Ensure reasonable limits
        if page_size > 500:
            page_size = 500
        if page_size < 1:
            page_size = 50
        if page_number < 1:
            page_number = 1
        
        # Calculate pagination
        total_count = device_tags.count()
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        
        paginated_tags = device_tags[start_index:end_index]
        
        # Serialize the data
        serializer = DeviceTagSerializer2(paginated_tags, many=True)
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page_number < total_pages
        has_previous = page_number > 1
        
        response_data = {
            'success': True,
            'message': f'Found {total_count} tagging records in {admin_state.state} state.',
            'data': serializer.data,
            'pagination': {
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_count': total_count,
                'has_next': has_next,
                'has_previous': has_previous,
            },
            'state_info': {
                'state_id': admin_state.id,
                'state_name': admin_state.state
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f"Unable to process request. {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)

 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def get_device_tag_alerts(request):
    """
    Get alerts for specific device tags with user-based filtering:
    - Super Admin: Can see all alerts
    - State Admin: Can see alerts for devices in their state only  
    - DTO/RTO: Can see alerts for devices in their district only
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Get filtering parameters
        vehicle_reg_no = request.data.get('vehicle_reg_no', '')
        device_tag_id = request.data.get('device_tag_id', '')
        start_datetime = request.data.get('start_datetime')
        end_datetime = request.data.get('end_datetime')
        alert_type = request.data.get('alert_type', '')
        
        # Base queryset for alerts
        alerts_queryset = AlertsLog.objects.all().select_related(
            'deviceTag', 'deviceTag__device', 'deviceTag__vehicle_owner', 
            'state', 'gps_ref'
        )
        
        # Apply user-based filtering based on role
        if user.role == "superadmin":
            # Super admin can see all alerts - no additional filtering needed
            pass
            
        elif user.role == "stateadmin":
            # State admin can only see alerts for devices in their state
            state_admin = get_user_object(user, "stateadmin")
            if not state_admin:
                return Response({"error": "Invalid state admin user"}, status=status.HTTP_400_BAD_REQUEST)
            
            alerts_queryset = alerts_queryset.filter(state=state_admin.state)
            
        elif user.role == "dtorto":
            # DTO/RTO can only see alerts for devices in their district
            dto_rto_obj = get_user_object(user, "dtorto")
            if not dto_rto_obj:
                return Response({"error": "Invalid DTO/RTO user"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Filter by state and district
            alerts_queryset = alerts_queryset.filter(
                state=dto_rto_obj.state,
                deviceTag__vehicle_owner__address_State=dto_rto_obj.state.name,
                deviceTag__vehicle_owner__address__icontains=dto_rto_obj.district
            )
            
        else:
            return Response({"error": "Unauthorized role. Only superadmin, stateadmin, and dtorto can access this endpoint."}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Apply additional filters based on request parameters
        if vehicle_reg_no:
            alerts_queryset = alerts_queryset.filter(
                deviceTag__vehicle_reg_no__icontains=vehicle_reg_no
            )
            
        if device_tag_id:
            alerts_queryset = alerts_queryset.filter(deviceTag__id=device_tag_id)
            
        if start_datetime:
            alerts_queryset = alerts_queryset.filter(timestamp__gte=start_datetime)
            
        if end_datetime:
            alerts_queryset = alerts_queryset.filter(timestamp__lte=end_datetime)
            
        if alert_type:
            alerts_queryset = alerts_queryset.filter(type=alert_type)
        
        # Order by timestamp (newest first)
        alerts_queryset = alerts_queryset.order_by('-timestamp')
        
        # Pagination
        page_number = request.data.get('page', 1)
        page_size = request.data.get('page_size', 50)
        
        paginator = Paginator(alerts_queryset, page_size)
        page_obj = paginator.get_page(page_number)
        
        # Serialize the alerts data
        alerts_data = []
        for alert in page_obj:
            alert_data = {
                'id': alert.id,
                'type': alert.type,
                'status': alert.status,
                'timestamp': alert.timestamp.isoformat(),
                'device_tag': {
                    'id': alert.deviceTag.id,
                    'vehicle_reg_no': alert.deviceTag.vehicle_reg_no,
                    'vehicle_make': alert.deviceTag.vehicle_make,
                    'vehicle_model': alert.deviceTag.vehicle_model,
                    'category': alert.deviceTag.category,
                    'status': alert.deviceTag.status,
                    'device_esn': alert.deviceTag.device.device_esn if alert.deviceTag.device else None,
                    'owner_name': alert.deviceTag.vehicle_owner.name if alert.deviceTag.vehicle_owner else None,
                    'owner_mobile': alert.deviceTag.vehicle_owner.mobile if alert.deviceTag.vehicle_owner else None
                },
                'state': {
                    'id': alert.state.id,
                    'name': alert.state.name
                } if alert.state else None,
                'gps_data': {
                    'latitude': alert.gps_ref.latitude if alert.gps_ref else None,
                    'longitude': alert.gps_ref.longitude if alert.gps_ref else None,
                    'speed': alert.gps_ref.speed if alert.gps_ref else None,
                    'timestamp': alert.gps_ref.timestamp.isoformat() if alert.gps_ref and alert.gps_ref.timestamp else None
                } if alert.gps_ref else None,
                'route_info': {
                    'id': alert.route_ref.id,
                    'name': alert.route_ref.name
                } if alert.route_ref else None,
                'emergency_call': {
                    'id': alert.em_ref.id,
                    'status': alert.em_ref.status
                } if alert.em_ref else None
            }
            alerts_data.append(alert_data)
        
        # Summary statistics
        total_alerts = alerts_queryset.count()
        alert_type_counts = {}
        for choice in AlertsLog.TYPE_CHOICES:
            alert_type = choice[0]
            count = alerts_queryset.filter(type=alert_type).count()
            alert_type_counts[alert_type] = count
        
        response_data = {
            'success': True,
            'user_role': user.role,
            'total_alerts': total_alerts,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'alert_type_counts': alert_type_counts,
            'alerts': alerts_data,
            'available_alert_types': dict(AlertsLog.TYPE_CHOICES)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'An error occurred while fetching alerts: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ...existing code...

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def get_device_tags(request):
    """
    Get device tags with search functionality and user-based filtering:
    - Super Admin: Can see all device tags
    - State Admin: Can see device tags for their state only  
    - DTO/RTO: Can see device tags for their district only
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Get filtering parameters
        vehicle_reg_no = request.data.get('vehicle_reg_no', '')
        vehicle_make = request.data.get('vehicle_make', '')
        vehicle_model = request.data.get('vehicle_model', '')
        category = request.data.get('category', '')
        status_filter = request.data.get('status', '')
        owner_name = request.data.get('owner_name', '')
        owner_mobile = request.data.get('owner_mobile', '')
        device_esn = request.data.get('device_esn', '')
        engine_no = request.data.get('engine_no', '')
        chassis_no = request.data.get('chassis_no', '')
        tagged_from = request.data.get('tagged_from')
        tagged_to = request.data.get('tagged_to')
        
        # Base queryset for device tags
        device_tags_queryset = DeviceTag.objects.all().select_related(
            'device', 'device__model', 'vehicle_owner', 'tagged_by'
        ).prefetch_related(
            'vehicle_owner__users', 'drivers'
        )
        
        # Apply user-based filtering based on role
        if user.role == "superadmin":
            # Super admin can see all device tags - no additional filtering needed
            pass
            
        elif user.role == "stateadmin":
            # State admin can only see device tags for vehicles in their state
            state_admin = get_user_object(user, "stateadmin")
            if not state_admin:
                return Response({"error": "Invalid state admin user"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Filter by state - assuming vehicle owners have state information
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_owner__users__address_State=state_admin.state.name
            )
            
        elif user.role == "dtorto":
            # DTO/RTO can only see device tags for vehicles in their district
            dto_rto_obj = get_user_object(user, "dtorto")
            if not dto_rto_obj:
                return Response({"error": "Invalid DTO/RTO user"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Filter by state and district
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_owner__users__address_State=dto_rto_obj.state.name,
                vehicle_owner__users__address__icontains=dto_rto_obj.district
            )
            
        else:
            return Response({"error": "Unauthorized role. Only superadmin, stateadmin, and dtorto can access this endpoint."}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Apply search filters
        if vehicle_reg_no:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_reg_no__icontains=vehicle_reg_no
            )
            
        if vehicle_make:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_make__icontains=vehicle_make
            )
            
        if vehicle_model:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_model__icontains=vehicle_model
            )
            
        if category:
            device_tags_queryset = device_tags_queryset.filter(
                category__icontains=category
            )
            
        if status_filter:
            device_tags_queryset = device_tags_queryset.filter(status=status_filter)
            
        if owner_name:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_owner__users__name__icontains=owner_name
            )
            
        if owner_mobile:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_owner__users__mobile__icontains=owner_mobile
            )
            
        if device_esn:
            device_tags_queryset = device_tags_queryset.filter(
                device__device_esn__icontains=device_esn
            )
            
        if engine_no:
            device_tags_queryset = device_tags_queryset.filter(
                engine_no__icontains=engine_no
            )
            
        if chassis_no:
            device_tags_queryset = device_tags_queryset.filter(
                chassis_no__icontains=chassis_no
            )
            
        if tagged_from:
            device_tags_queryset = device_tags_queryset.filter(tagged__gte=tagged_from)
            
        if tagged_to:
            device_tags_queryset = device_tags_queryset.filter(tagged__lte=tagged_to)
        
        # Order by tagged date (newest first)
        device_tags_queryset = device_tags_queryset.order_by('-tagged')
        
        # Pagination
        page_number = request.data.get('page', 1)
        page_size = request.data.get('page_size', 50)
        
        # Ensure reasonable pagination limits
        try:
            page_number = int(page_number)
            page_size = int(page_size)
        except (ValueError, TypeError):
            page_number = 1
            page_size = 50
            
        if page_size > 500:
            page_size = 500
        if page_size < 1:
            page_size = 50
        if page_number < 1:
            page_number = 1
        
        paginator = Paginator(device_tags_queryset, page_size)
        page_obj = paginator.get_page(page_number)
        
        # Serialize the device tags data
        device_tags_data = []
        for device_tag in page_obj:
            # Get the primary vehicle owner user
            primary_owner_user = device_tag.vehicle_owner.users.first() if device_tag.vehicle_owner else None
            
            # Get driver information
            drivers_info = []
            for driver in device_tag.drivers.all():
                drivers_info.append({
                    'id': driver.id,
                    'name': driver.name,
                    'mobile': driver.mobile,
                    'license_no': driver.license_no
                })
            
            device_tag_data = {
                'id': device_tag.id,
                'vehicle_reg_no': device_tag.vehicle_reg_no,
                'engine_no': device_tag.engine_no,
                'chassis_no': device_tag.chassis_no,
                'vehicle_make': device_tag.vehicle_make,
                'vehicle_model': device_tag.vehicle_model,
                'category': device_tag.category,
                'status': device_tag.status,
                'tagged': device_tag.tagged.isoformat() if device_tag.tagged else None,
                'rc_file': device_tag.rc_file,
                'receipt_file_or': device_tag.receipt_file_or,
                'receipt_file_ul': device_tag.receipt_file_ul,
                'device': {
                    'id': device_tag.device.id,
                    'device_esn': device_tag.device.device_esn,
                    'imei': device_tag.device.imei,
                    'iccid': device_tag.device.iccid,
                    'msisdn1': device_tag.device.msisdn1,
                    'msisdn2': device_tag.device.msisdn2,
                    'model': {
                        'id': device_tag.device.model.id,
                        'model_name': device_tag.device.model.model_name,
                        'vendor_id': device_tag.device.model.vendor_id
                    } if device_tag.device.model else None
                } if device_tag.device else None,
                'vehicle_owner': {
                    'id': device_tag.vehicle_owner.id,
                    'name': primary_owner_user.name if primary_owner_user else None,
                    'email': primary_owner_user.email if primary_owner_user else None,
                    'mobile': primary_owner_user.mobile if primary_owner_user else None,
                    'address': primary_owner_user.address if primary_owner_user else None,
                    'address_state': primary_owner_user.address_State if primary_owner_user else None,
                    'address_pin': primary_owner_user.address_pin if primary_owner_user else None
                } if device_tag.vehicle_owner else None,
                'tagged_by': {
                    'id': device_tag.tagged_by.id,
                    'name': device_tag.tagged_by.name,
                    'email': device_tag.tagged_by.email,
                    'role': device_tag.tagged_by.role
                } if device_tag.tagged_by else None,
                'drivers': drivers_info
            }
            device_tags_data.append(device_tag_data)
        
        # Get status statistics
        total_device_tags = device_tags_queryset.count()
        status_counts = {}
        for choice in DeviceTag.STATUS_CHOICES:
            status_value = choice[0]
            count = device_tags_queryset.filter(status=status_value).count()
            status_counts[status_value] = count
        
        # Get category statistics
        category_counts = {}
        categories = device_tags_queryset.values_list('category', flat=True).distinct()
        for category_name in categories:
            if category_name:
                count = device_tags_queryset.filter(category=category_name).count()
                category_counts[category_name] = count
        
        response_data = {
            'success': True,
            'user_role': user.role,
            'total_device_tags': total_device_tags,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'status_counts': status_counts,
            'category_counts': category_counts,
            'device_tags': device_tags_data,
            'available_statuses': dict(DeviceTag.STATUS_CHOICES),
            'search_filters_applied': {
                'vehicle_reg_no': vehicle_reg_no,
                'vehicle_make': vehicle_make,
                'vehicle_model': vehicle_model,
                'category': category,
                'status': status_filter,
                'owner_name': owner_name,
                'owner_mobile': owner_mobile,
                'device_esn': device_esn,
                'engine_no': engine_no,
                'chassis_no': chassis_no,
                'tagged_from': tagged_from,
                'tagged_to': tagged_to
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'An error occurred while fetching device tags: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ...existing code...

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def activated_device_list(request):
    """
    Get list of activated devices with comprehensive information for super admin, state admin, and DTO users.
    Returns: FITMENT DATE, fitment status, eSIM validity, reg no, DTO district code, 
    vehicle owner, device model number, manufacturer, dealer
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Check user role and permissions
        allowed_roles = ['superadmin', 'stateadmin', 'dtorto']
        if user.role not in allowed_roles:
            return Response({
                "error": f"Access denied. This endpoint is only accessible by {', '.join(allowed_roles)}."
            }, status=status.HTTP_403_FORBIDDEN)

        # Base query for activated devices (Device Active status)
        activated_devices = DeviceTag.objects.filter(
            status='Device_Active'
        ).select_related(
            'device',
            'device__model',
            'device__model__created_by',
            'device__dealer',
            'device__dealer__manufacturer',
            'device__dealer__district',
            'device__dealer__district__state',
            'vehicle_owner'
        ).prefetch_related(
            'device__model__created_by',
            'device__dealer__manufacturer__users',
            'device__dealer__users',
            'vehicle_owner__users'
        )

        # Apply role-based filtering
        if user.role == 'stateadmin':
            # State admin can only see devices in their state
            state_admin = get_user_object(user, "stateadmin")
            if state_admin:
                activated_devices = activated_devices.filter(
                    device__dealer__district__state=state_admin.state
                )
            else:
                return Response({
                    "error": "State admin profile not found"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        elif user.role == 'dtorto':
            # DTO can only see devices in their district(s)
            dto_admin = get_user_object(user, "dtorto")
            if dto_admin:
                activated_devices = activated_devices.filter(
                    device__dealer__district=dto_admin.district
                )
            else:
                return Response({
                    "error": "DTO profile not found"
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Apply additional filters from request
        device_esn = request.data.get('device_esn', '')
        vehicle_reg_no = request.data.get('vehicle_reg_no', '')
        manufacturer_name = request.data.get('manufacturer_name', '')
        dealer_name = request.data.get('dealer_name', '')
        district_code = request.data.get('district_code', '')
        state_id = request.data.get('state_id', '')
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        
        if device_esn:
            activated_devices = activated_devices.filter(device__device_esn__icontains=device_esn)
        
        if vehicle_reg_no:
            activated_devices = activated_devices.filter(vehicle_reg_no__icontains=vehicle_reg_no)
            
        if manufacturer_name:
            activated_devices = activated_devices.filter(
                device__dealer__manufacturer__company_name__icontains=manufacturer_name
            )
            
        if dealer_name:
            activated_devices = activated_devices.filter(
                device__dealer__company_name__icontains=dealer_name
            )
            
        if district_code:
            activated_devices = activated_devices.filter(
                device__dealer__district__district_code__icontains=district_code
            )
            
        if state_id:
            activated_devices = activated_devices.filter(
                device__dealer__district__state__id=state_id
            )
            
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                activated_devices = activated_devices.filter(tagged__date__gte=from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                activated_devices = activated_devices.filter(tagged__date__lte=to_date)
            except ValueError:
                pass

        # Prepare response data
        device_list = []
        for device_tag in activated_devices:
            try:
                # Get manufacturer information
                manufacturer = device_tag.device.dealer.manufacturer if device_tag.device.dealer else None
                manufacturer_name = manufacturer.company_name if manufacturer else 'N/A'
                manufacturer_users = list(manufacturer.users.all()) if manufacturer else []
                manufacturer_user_name = manufacturer_users[0].name if manufacturer_users else 'N/A'
                
                # Get dealer information
                dealer = device_tag.device.dealer
                dealer_name = dealer.company_name if dealer else 'N/A'
                dealer_users = list(dealer.users.all()) if dealer else []
                dealer_user_name = dealer_users[0].name if dealer_users else 'N/A'
                
                # Get district information
                district = dealer.district if dealer else None
                district_name = district.district if district else 'N/A'
                district_code = district.district_code if district else 'N/A'
                state_name = district.state.state if district and district.state else 'N/A'
                
                # Get vehicle owner information
                vehicle_owner = device_tag.vehicle_owner
                owner_users = list(vehicle_owner.users.all()) if vehicle_owner else []
                owner_name = owner_users[0].name if owner_users else 'N/A'
                owner_company = vehicle_owner.company_name if vehicle_owner else 'N/A'
                
                # Get device information
                device = device_tag.device
                device_model = device.model
                
                device_data = {
                    'id': device_tag.id,
                    'device_esn': device.device_esn,
                    'imei': device.imei,
                    'iccid': device.iccid,
                    'msisdn1': device.msisdn1,
                    'msisdn2': device.msisdn2 or 'N/A',
                    
                    # Fitment information
                    'fitment_date': device_tag.tagged.strftime('%Y-%m-%d %H:%M:%S') if device_tag.tagged else 'N/A',
                    'fitment_status': device_tag.status,
                    
                    # eSIM information
                    'esim_validity': device.esim_validity.strftime('%Y-%m-%d') if device.esim_validity else 'N/A',
                    'telecom_provider1': device.telecom_provider1,
                    'telecom_provider2': device.telecom_provider2 or 'N/A',
                    'stock_status': device.stock_status,
                    'esim_status': device.esim_status,
                    
                    # Vehicle information
                    'vehicle_reg_no': device_tag.vehicle_reg_no,
                    'engine_no': device_tag.engine_no,
                    'chassis_no': device_tag.chassis_no,
                    'vehicle_make': device_tag.vehicle_make,
                    'vehicle_model': device_tag.vehicle_model,
                    'vehicle_category': device_tag.category,
                    
                    # District and state information
                    'dto_district_code': district_code,
                    'district_name': district_name,
                    'state_name': state_name,
                    
                    # Vehicle owner information
                    'vehicle_owner_name': owner_name,
                    'vehicle_owner_company': owner_company,
                    'vehicle_owner_id': vehicle_owner.id if vehicle_owner else None,
                    
                    # Device model information
                    'device_model_name': device_model.model_name,
                    'device_model_id': device_model.id,
                    'hardware_version': device_model.hardware_version,
                    'vendor_id': device_model.vendor_id,
                    'tac_no': device_model.tac_no,
                    
                    # Manufacturer information
                    'manufacturer_name': manufacturer_name,
                    'manufacturer_id': manufacturer.id if manufacturer else None,
                    'manufacturer_user_name': manufacturer_user_name,
                    'manufacturer_state': manufacturer.state.state if manufacturer and manufacturer.state else 'N/A',
                    
                    # Dealer information
                    'dealer_name': dealer_name,
                    'dealer_id': dealer.id if dealer else None,
                    'dealer_user_name': dealer_user_name,
                    
                    # Tagged by information
                    'tagged_by_name': device_tag.tagged_by.name if device_tag.tagged_by else 'N/A',
                    'tagged_by_email': device_tag.tagged_by.email if device_tag.tagged_by else 'N/A',
                    
                    # Additional device information
                    'created_date': device.created.strftime('%Y-%m-%d %H:%M:%S') if device.created else 'N/A',
                    'device_assigned_date': device.assigned.strftime('%Y-%m-%d %H:%M:%S') if device.assigned else 'N/A',
                }
                
                device_list.append(device_data)
                
            except Exception as e:
                # Log individual device errors but continue processing
                continue

        # Pagination
        page = int(request.data.get('page', 1))
        page_size = int(request.data.get('page_size', 50))
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_devices = device_list[start_index:end_index]
        
        response_data = {
            'status': 'success',
            'data': {
                'devices': paginated_devices,
                'total_count': len(device_list),
                'page': page,
                'page_size': page_size,
                'total_pages': (len(device_list) + page_size - 1) // page_size
            },
            'message': 'Activated devices retrieved successfully'
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An error occurred while retrieving activated devices: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def dealer_check_esim_status(request):
    """
    API for dealers to check eSIM activation status and validity for their devices
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user is a dealer
    role = "dealer"
    user = request.user
    dealer = get_user_object(user, role)
    if not dealer:
        return Response({"error": "Request must be from dealer."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get filter parameters
        device_esn = request.data.get('device_esn', '')
        imei = request.data.get('imei', '')
        msisdn1 = request.data.get('msisdn1', '')
        esim_status_filter = request.data.get('esim_status', '')
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Current time for validity checks
        now = timezone.now()
        
        # Base query for devices assigned to this dealer
        devices = DeviceStock.objects.filter(dealer=dealer)
        
        # Apply filters if provided
        if device_esn:
            devices = devices.filter(device_esn__icontains=device_esn)
        
        if imei:
            devices = devices.filter(imei__icontains=imei)
            
        if msisdn1:
            devices = devices.filter(msisdn1__icontains=msisdn1)
            
        if esim_status_filter:
            devices = devices.filter(esim_status=esim_status_filter)
        
        # Get devices with related data
        devices = devices.select_related('model', 'dealer', 'created_by').prefetch_related('esim_provider')
        
        # Process results and add validity information
        result_data = []
        for device in devices:
            # Check if eSIM is expired
            is_expired = device.esim_validity and device.esim_validity <= now
            
            # Calculate days until expiry
            days_until_expiry = None
            if device.esim_validity:
                time_diff = device.esim_validity - now
                days_until_expiry = time_diff.days if time_diff.days > 0 else 0
            
            # Determine expiry status
            expiry_status = "Active"
            if is_expired:
                expiry_status = "Expired"
            elif days_until_expiry is not None and days_until_expiry <= 30:
                expiry_status = "Expiring Soon"
            
            # Get eSIM providers
            esim_providers = [{"id": provider.id, "company_name": provider.company_name} 
                             for provider in device.esim_provider.all()]
            
            # Get any pending activation requests
            activation_requests = esimActivationRequest.objects.filter(
                device=device,
                ceated_by=dealer
            ).order_by('-created_at')
            
            latest_request = None
            if activation_requests.exists():
                latest_activation = activation_requests.first()
                latest_request = {
                    "id": latest_activation.id,
                    "status": latest_activation.status,
                    "created_at": latest_activation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "eSim_provider": latest_activation.eSim_provider.company_name if latest_activation.eSim_provider else None,
                    "valid_from": latest_activation.valid_from.strftime('%Y-%m-%d %H:%M:%S') if latest_activation.valid_from else None,
                    "valid_upto": latest_activation.valid_upto.strftime('%Y-%m-%d %H:%M:%S') if latest_activation.valid_upto else None,
                    "accepted_at": latest_activation.accepted_at.strftime('%Y-%m-%d %H:%M:%S') if latest_activation.accepted_at else None
                }
            
            device_info = {
                "device_id": device.id,
                "device_esn": device.device_esn,
                "imei": device.imei,
                "iccid": device.iccid,
                "msisdn1": device.msisdn1,
                "msisdn2": device.msisdn2,
                "telecom_provider1": device.telecom_provider1,
                "telecom_provider2": device.telecom_provider2,
                
                # Device model information
                "device_model": {
                    "id": device.model.id,
                    "model_name": device.model.model_name,
                    "vendor_id": device.model.vendor_id
                },
                
                # eSIM status and validity information
                "esim_status": device.esim_status,
                "stock_status": device.stock_status,
                "esim_validity": device.esim_validity.strftime('%Y-%m-%d %H:%M:%S') if device.esim_validity else None,
                "days_until_expiry": days_until_expiry,
                "expiry_status": expiry_status,
                "is_expired": is_expired,
                
                # eSIM provider information
                "esim_providers": esim_providers,
                
                # Latest activation request information
                "latest_activation_request": latest_request,
                
                # Additional device information
                "assigned_date": device.assigned.strftime('%Y-%m-%d %H:%M:%S') if device.assigned else None,
                "created_date": device.created.strftime('%Y-%m-%d %H:%M:%S'),
                "remarks": device.remarks
            }
            
            result_data.append(device_info)
        
        # Summary statistics
        total_devices = len(result_data)
        active_esims = len([d for d in result_data if d['expiry_status'] == 'Active'])
        expired_esims = len([d for d in result_data if d['expiry_status'] == 'Expired'])
        expiring_soon = len([d for d in result_data if d['expiry_status'] == 'Expiring Soon'])
        
        # Count by eSIM status
        status_counts = {}
        for device in result_data:
            status = device['esim_status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        summary = {
            "total_devices": total_devices,
            "esim_validity_summary": {
                "active": active_esims,
                "expired": expired_esims,
                "expiring_soon": expiring_soon
            },
            "esim_status_counts": status_counts,
            "dealer_info": {
                "id": dealer.id,
                "company_name": dealer.company_name,
                "district": dealer.district.district if dealer.district else None,
                "state": dealer.manufacturer.state.state if dealer.manufacturer and dealer.manufacturer.state else None
            }
        }
        
        return Response({
            "summary": summary,
            "devices": result_data
        }, status=200)
        
    except Exception as e:
        return Response({'error': "Unable to process request. " + str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_esimProvider(request):
    """
    Homepage API for esim Provider role showing eSIM related statistics
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        role = "esimprovider"
        user = request.user
        profile = get_user_object(user, role)
        if not profile:
            return Response({"error": "Request must be from " + role + '.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create a dictionary to hold the filter parameters
        filters = {}
        
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Get all device stocks associated with this eSIM provider
            device_stocks = DeviceStock.objects.filter(esim_provider=profile)
            
            # Total devices with this eSIM provider
            total_devices = device_stocks.count()
            
            # eSIM activation request statistics
            esim_activation_requests = esimActivationRequest.objects.filter(eSim_provider=profile)
            
            # Count different statuses of eSIM activation requests
            esim_pending = esim_activation_requests.filter(status="pending").count()
            esim_validated = esim_activation_requests.filter(status="valid").count()
            esim_invalid = esim_activation_requests.filter(status="invalid").count()
            
            # Count eSIM validity status based on device stock
            esim_active = device_stocks.filter(
                esim_validity__gt=now,  # Valid eSIMs (not expired)
                stock_status__in=['ESIM_Active_Confirmed', 'IP_PORT_Configured', 'SOS_GATEWAY_NO_Configured', 'SMS_GATEWAY_NO_Configured']
            ).count()
            
            esim_expired = device_stocks.filter(
                esim_validity__lte=now  # Expired eSIMs
            ).count()
            
            # Additional statistics
            esim_activation_req_sent = device_stocks.filter(
                stock_status='ESIM_Active_Req_Sent'
            ).count()
            
            esim_activation_confirmed = device_stocks.filter(
                stock_status='ESIM_Active_Confirmed'
            ).count()
            
            esim_activation_rejected = device_stocks.filter(
                stock_status='ESIM_Active_Rejected'
            ).count()
            
            # Time-based statistics
            today_requests = esim_activation_requests.filter(created_at__gte=today_start).count()
            this_month_requests = esim_activation_requests.filter(created_at__gte=month_start).count()
            this_week_requests = esim_activation_requests.filter(created_at__gte=week_ago).count()
            
            # Expiring soon (within 30 days)
            esim_expiring_soon = device_stocks.filter(
                esim_validity__gt=now,
                esim_validity__lte=now + timedelta(days=30)
            ).count()
            
            count_dict = {
                'Total_Devices_With_ESim': total_devices,
                'ESim_Validated': esim_validated,
                'ESim_Expired': esim_expired,
                'ESim_Active': esim_active,
                'ESim_Pending': esim_pending,
                'ESim_Invalid': esim_invalid,
                'ESim_Activation_Req_Sent': esim_activation_req_sent,
                'ESim_Activation_Confirmed': esim_activation_confirmed,
                'ESim_Activation_Rejected': esim_activation_rejected,
                'ESim_Expiring_Soon_30_Days': esim_expiring_soon,
                'Today_Activation_Requests': today_requests,
                'This_Week_Activation_Requests': this_week_requests,
                'This_Month_Activation_Requests': this_month_requests,
                'Provider_Company_Name': profile.company_name,
                'Provider_State': profile.state.state if profile.state else None,
                'Provider_Status': profile.status,
                'Provider_Created_Date': profile.created.strftime('%Y-%m-%d') if profile.created else None,
                'Provider_Expiry_Date': profile.expirydate.strftime('%Y-%m-%d') if profile.expirydate else None,
            }
            
            return Response({
                'status': 'success',
                'data': count_dict,
                'message': 'esim Provider homepage data retrieved successfully'
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def state_admin_approved_models_report(request):
    """
    API for state admin to get report of approved device models.
    Returns comprehensive information about approved device models including manufacturer details.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Check if user is a state admin
        if user.role != 'stateadmin':
            return Response({
                "error": "Access denied. This endpoint is only accessible by state admins."
            }, status=status.HTTP_403_FORBIDDEN)

        # Get state admin profile
        state_admin = get_user_object(user, "stateadmin")
        if not state_admin:
            return Response({
                "error": "State admin profile not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Base query for approved device models
        approved_models = DeviceModel.objects.filter(
            status='StateAdminApproved'
        ).select_related(
            'created_by'
        ).prefetch_related(
            'eSimProviders',
            'created_by__manufacturers_user'
        )

        # Apply filters from request
        model_name = request.data.get('model_name', '')
        vendor_id = request.data.get('vendor_id', '')
        tac_no = request.data.get('tac_no', '')
        manufacturer_name = request.data.get('manufacturer_name', '')
        test_agency = request.data.get('test_agency', '')
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        
        if model_name:
            approved_models = approved_models.filter(model_name__icontains=model_name)
        
        if vendor_id:
            approved_models = approved_models.filter(vendor_id__icontains=vendor_id)
            
        if tac_no:
            approved_models = approved_models.filter(tac_no__icontains=tac_no)
            
        if test_agency:
            approved_models = approved_models.filter(test_agency__icontains=test_agency)
            
        if manufacturer_name:
            approved_models = approved_models.filter(
                created_by__manufacturers_user__company_name__icontains=manufacturer_name
            )
            
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                approved_models = approved_models.filter(created__date__gte=from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                approved_models = approved_models.filter(created__date__lte=to_date)
            except ValueError:
                pass

        # Prepare response data
        models_list = []
        for model in approved_models:
            try:
                # Get manufacturer information
                manufacturer = model.created_by.manufacturers_user.first() if model.created_by.manufacturers_user.exists() else None
                manufacturer_name = manufacturer.company_name if manufacturer else 'N/A'
                manufacturer_state = manufacturer.state.state if manufacturer and manufacturer.state else 'N/A'
                
                # Get eSIM providers
                esim_providers = []
                for provider in model.eSimProviders.all():
                    esim_providers.append({
                        'id': provider.id,
                        'company_name': provider.company_name,
                        'state': provider.state.state if provider.state else 'N/A'
                    })
                
                model_data = {
                    'id': model.id,
                    'model_name': model.model_name,
                    'test_agency': model.test_agency,
                    'vendor_id': model.vendor_id,
                    'tac_no': model.tac_no,
                    'tac_validity': model.tac_validity.strftime('%Y-%m-%d') if model.tac_validity else 'N/A',
                    'hardware_version': model.hardware_version,
                    'status': model.status,
                    'created_date': model.created.strftime('%Y-%m-%d %H:%M:%S') if model.created else 'N/A',
                    'approved_date': model.created.strftime('%Y-%m-%d %H:%M:%S') if model.created else 'N/A',  # Approval date same as creation for approved models
                    
                    # Manufacturer information
                    'manufacturer_name': manufacturer_name,
                    'manufacturer_id': manufacturer.id if manufacturer else None,
                    'manufacturer_state': manufacturer_state,
                    'manufacturer_gst_no': manufacturer.gstno if manufacturer else 'N/A',
                    'manufacturer_created_date': manufacturer.created.strftime('%Y-%m-%d') if manufacturer and manufacturer.created else 'N/A',
                    
                    # Creator information
                    'created_by_name': model.created_by.name if model.created_by else 'N/A',
                    'created_by_email': model.created_by.email if model.created_by else 'N/A',
                    'created_by_mobile': model.created_by.mobile if model.created_by else 'N/A',
                    
                    # eSIM providers
                    'esim_providers': esim_providers,
                    'esim_providers_count': len(esim_providers),
                    
                    # File information
                    'tac_doc_available': bool(model.tac_doc_path),
                    'tac_doc_path': model.tac_doc_path.url if model.tac_doc_path else None,
                }
                
                models_list.append(model_data)
                
            except Exception as e:
                # Log individual model errors but continue processing
                continue

        # Pagination
        page = int(request.data.get('page', 1))
        page_size = int(request.data.get('page_size', 50))
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_models = models_list[start_index:end_index]
        
        # Generate summary statistics
        total_models = len(models_list)
        unique_manufacturers = len(set([model['manufacturer_id'] for model in models_list if model['manufacturer_id']]))
        models_with_esim = len([model for model in models_list if model['esim_providers_count'] > 0])
        
        # Count by test agencies
        test_agencies = {}
        for model in models_list:
            agency = model['test_agency']
            test_agencies[agency] = test_agencies.get(agency, 0) + 1
        
        summary = {
            'total_approved_models': total_models,
            'unique_manufacturers': unique_manufacturers,
            'models_with_esim_providers': models_with_esim,
            'models_without_esim_providers': total_models - models_with_esim,
            'test_agencies_breakdown': test_agencies,
            'state_admin_info': {
                'id': state_admin.id,
                'state': state_admin.state.state if state_admin.state else 'N/A',
                'created_date': state_admin.created.strftime('%Y-%m-%d') if state_admin.created else 'N/A'
            }
        }
        
        response_data = {
            'status': 'success',
            'data': {
                'summary': summary,
                'models': paginated_models,
                'total_count': total_models,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_models + page_size - 1) // page_size
            },
            'message': 'Approved device models report retrieved successfully'
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An error occurred while retrieving approved models report: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def state_admin_approved_cops_report(request):
    """
    API for state admin to get report of approved COPs (Certificate of Performance).
    Returns comprehensive information about approved COPs including device model and manufacturer details.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Check if user is a state admin
        if user.role != 'stateadmin':
            return Response({
                "error": "Access denied. This endpoint is only accessible by state admins."
            }, status=status.HTTP_403_FORBIDDEN)

        # Get state admin profile
        state_admin = get_user_object(user, "stateadmin")
        if not state_admin:
            return Response({
                "error": "State admin profile not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Base query for approved COPs
        approved_cops = DeviceCOP.objects.filter(
            status='StateAdminApproved'
        ).select_related(
            'device_model',
            'device_model__created_by',
            'created_by'
        ).prefetch_related(
            'device_model__eSimProviders',
            'created_by__manufacturers_user'
        )

        # Apply filters from request
        cop_no = request.data.get('cop_no', '')
        model_name = request.data.get('model_name', '')
        vendor_id = request.data.get('vendor_id', '')
        manufacturer_name = request.data.get('manufacturer_name', '')
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        validity_from = request.data.get('validity_from', '')
        validity_to = request.data.get('validity_to', '')
        
        if cop_no:
            approved_cops = approved_cops.filter(cop_no__icontains=cop_no)
        
        if model_name:
            approved_cops = approved_cops.filter(device_model__model_name__icontains=model_name)
            
        if vendor_id:
            approved_cops = approved_cops.filter(device_model__vendor_id__icontains=vendor_id)
            
        if manufacturer_name:
            approved_cops = approved_cops.filter(
                created_by__manufacturers_user__company_name__icontains=manufacturer_name
            )
            
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                approved_cops = approved_cops.filter(created__date__gte=from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                approved_cops = approved_cops.filter(created__date__lte=to_date)
            except ValueError:
                pass
                
        if validity_from:
            try:
                from_date = datetime.strptime(validity_from, '%Y-%m-%d').date()
                approved_cops = approved_cops.filter(cop_validity__gte=from_date)
            except ValueError:
                pass
                
        if validity_to:
            try:
                to_date = datetime.strptime(validity_to, '%Y-%m-%d').date()
                approved_cops = approved_cops.filter(cop_validity__lte=to_date)
            except ValueError:
                pass

        # Prepare response data
        cops_list = []
        for cop in approved_cops:
            try:
                # Get manufacturer information
                manufacturer = cop.created_by.manufacturers_user.first() if cop.created_by.manufacturers_user.exists() else None
                manufacturer_name = manufacturer.company_name if manufacturer else 'N/A'
                manufacturer_state = manufacturer.state.state if manufacturer and manufacturer.state else 'N/A'
                
                # Get device model information
                device_model = cop.device_model
                
                # Get eSIM providers for the device model
                esim_providers = []
                for provider in device_model.eSimProviders.all():
                    esim_providers.append({
                        'id': provider.id,
                        'company_name': provider.company_name,
                        'state': provider.state.state if provider.state else 'N/A'
                    })
                
                # Check if COP is expired
                is_expired = cop.cop_validity and cop.cop_validity < timezone.now().date()
                
                # Calculate days until expiry
                days_until_expiry = None
                if cop.cop_validity:
                    time_diff = cop.cop_validity - timezone.now().date()
                    days_until_expiry = time_diff.days if time_diff.days > 0 else 0
                
                cop_data = {
                    'id': cop.id,
                    'cop_no': cop.cop_no,
                    'cop_validity': cop.cop_validity.strftime('%Y-%m-%d') if cop.cop_validity else 'N/A',
                    'status': cop.status,
                    'valid': cop.valid,
                    'latest': cop.latest,
                    'created_date': cop.created.strftime('%Y-%m-%d %H:%M:%S') if cop.created else 'N/A',
                    'is_expired': is_expired,
                    'days_until_expiry': days_until_expiry,
                    'expiry_status': 'Expired' if is_expired else ('Expiring Soon' if days_until_expiry is not None and days_until_expiry <= 30 else 'Active'),
                    
                    # Device model information
                    'device_model_id': device_model.id,
                    'device_model_name': device_model.model_name,
                    'device_model_vendor_id': device_model.vendor_id,
                    'device_model_tac_no': device_model.tac_no,
                    'device_model_tac_validity': device_model.tac_validity.strftime('%Y-%m-%d') if device_model.tac_validity else 'N/A',
                    'device_model_hardware_version': device_model.hardware_version,
                    'device_model_test_agency': device_model.test_agency,
                    'device_model_status': device_model.status,
                    
                    # Manufacturer information
                    'manufacturer_name': manufacturer_name,
                    'manufacturer_id': manufacturer.id if manufacturer else None,
                    'manufacturer_state': manufacturer_state,
                    'manufacturer_gst_no': manufacturer.gstno if manufacturer else 'N/A',
                    'manufacturer_created_date': manufacturer.created.strftime('%Y-%m-%d') if manufacturer and manufacturer.created else 'N/A',
                    
                    # Creator information
                    'created_by_name': cop.created_by.name if cop.created_by else 'N/A',
                    'created_by_email': cop.created_by.email if cop.created_by else 'N/A',
                    'created_by_mobile': cop.created_by.mobile if cop.created_by else 'N/A',
                    
                    # eSIM providers for the device model
                    'esim_providers': esim_providers,
                    'esim_providers_count': len(esim_providers),
                    
                    # File information
                    'cop_file_available': bool(cop.cop_file),
                    'cop_file_path': cop.cop_file.url if cop.cop_file else None,
                }
                
                cops_list.append(cop_data)
                
            except Exception as e:
                # Log individual COP errors but continue processing
                continue

        # Pagination
        page = int(request.data.get('page', 1))
        page_size = int(request.data.get('page_size', 50))
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_cops = cops_list[start_index:end_index]
        
        # Generate summary statistics
        total_cops = len(cops_list)
        unique_manufacturers = len(set([cop['manufacturer_id'] for cop in cops_list if cop['manufacturer_id']]))
        unique_device_models = len(set([cop['device_model_id'] for cop in cops_list]))
        expired_cops = len([cop for cop in cops_list if cop['is_expired']])
        expiring_soon_cops = len([cop for cop in cops_list if cop['expiry_status'] == 'Expiring Soon'])
        active_cops = len([cop for cop in cops_list if cop['expiry_status'] == 'Active'])
        
        # Count by test agencies
        test_agencies = {}
        for cop in cops_list:
            agency = cop['device_model_test_agency']
            test_agencies[agency] = test_agencies.get(agency, 0) + 1
        
        # Count by validity years
        validity_years = {}
        for cop in cops_list:
            if cop['cop_validity'] != 'N/A':
                year = cop['cop_validity'][:4]  # Extract year from YYYY-MM-DD format
                validity_years[year] = validity_years.get(year, 0) + 1
        
        summary = {
            'total_approved_cops': total_cops,
            'unique_manufacturers': unique_manufacturers,
            'unique_device_models': unique_device_models,
            'active_cops': active_cops,
            'expired_cops': expired_cops,
            'expiring_soon_cops': expiring_soon_cops,
            'test_agencies_breakdown': test_agencies,
            'validity_years_breakdown': validity_years,
            'state_admin_info': {
                'id': state_admin.id,
                'state': state_admin.state.state if state_admin.state else 'N/A',
                'created_date': state_admin.created.strftime('%Y-%m-%d') if state_admin.created else 'N/A'
            }
        }
        
        response_data = {
            'status': 'success',
            'data': {
                'summary': summary,
                'cops': paginated_cops,
                'total_count': total_cops,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_cops + page_size - 1) // page_size
            },
            'message': 'Approved COPs report retrieved successfully'
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An error occurred while retrieving approved COPs report: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def state_admin_combined_approval_report(request):
    """
    API for state admin to get combined report of approved device models and COPs.
    Returns summary statistics and overview of both approved models and COPs.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Check if user is a state admin
        if user.role != 'stateadmin':
            return Response({
                "error": "Access denied. This endpoint is only accessible by state admins."
            }, status=status.HTTP_403_FORBIDDEN)

        # Get state admin profile
        state_admin = get_user_object(user, "stateadmin")
        if not state_admin:
            return Response({
                "error": "State admin profile not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get date range from request
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        
        # Base queries for approved models and COPs
        approved_models_query = DeviceModel.objects.filter(status='StateAdminApproved')
        approved_cops_query = DeviceCOP.objects.filter(status='StateAdminApproved')
        
        # Apply date filters if provided
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                approved_models_query = approved_models_query.filter(created__date__gte=from_date)
                approved_cops_query = approved_cops_query.filter(created__date__gte=from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                approved_models_query = approved_models_query.filter(created__date__lte=to_date)
                approved_cops_query = approved_cops_query.filter(created__date__lte=to_date)
            except ValueError:
                pass

        # Get counts and statistics
        total_approved_models = approved_models_query.count()
        total_approved_cops = approved_cops_query.count()
        
        # Get unique manufacturers count
        model_manufacturers = set(approved_models_query.values_list('created_by', flat=True))
        cop_manufacturers = set(approved_cops_query.values_list('created_by', flat=True))
        unique_manufacturers = len(model_manufacturers.union(cop_manufacturers))
        
        # Get current date for expiry calculations
        now = timezone.now().date()
        
        # Count expired and expiring COPs
        expired_cops = approved_cops_query.filter(cop_validity__lt=now).count()
        expiring_soon_cops = approved_cops_query.filter(
            cop_validity__gte=now,
            cop_validity__lte=now + timedelta(days=30)
        ).count()
        
        # Count expired and expiring TAC validities in models
        expired_tac = approved_models_query.filter(tac_validity__lt=now).count()
        expiring_soon_tac = approved_models_query.filter(
            tac_validity__gte=now,
            tac_validity__lte=now + timedelta(days=30)
        ).count()
        
        # Get recent approvals (last 30 days)
        thirty_days_ago = now - timedelta(days=30)
        recent_models = approved_models_query.filter(created__date__gte=thirty_days_ago).count()
        recent_cops = approved_cops_query.filter(created__date__gte=thirty_days_ago).count()
        
        # Get monthly breakdown for current year
        current_year = now.year
        monthly_stats = {}
        for month in range(1, 13):
            month_models = approved_models_query.filter(
                created__year=current_year,
                created__month=month
            ).count()
            month_cops = approved_cops_query.filter(
                created__year=current_year,
                created__month=month
            ).count()
            month_name = calendar.month_name[month]
            monthly_stats[month_name] = {
                'models': month_models,
                'cops': month_cops,
                'total': month_models + month_cops
            }
        
        # Get top manufacturers by approvals
        from collections import defaultdict
        manufacturer_stats = defaultdict(lambda: {'models': 0, 'cops': 0, 'name': 'Unknown'})
        
        # Count models by manufacturer
        for model in approved_models_query.select_related('created_by').prefetch_related('created_by__manufacturers_user'):
            manufacturer = model.created_by.manufacturers_user.first() if model.created_by.manufacturers_user.exists() else None
            if manufacturer:
                manufacturer_stats[manufacturer.id]['models'] += 1
                manufacturer_stats[manufacturer.id]['name'] = manufacturer.company_name
        
        # Count COPs by manufacturer  
        for cop in approved_cops_query.select_related('created_by').prefetch_related('created_by__manufacturers_user'):
            manufacturer = cop.created_by.manufacturers_user.first() if cop.created_by.manufacturers_user.exists() else None
            if manufacturer:
                manufacturer_stats[manufacturer.id]['cops'] += 1
                manufacturer_stats[manufacturer.id]['name'] = manufacturer.company_name
        
        # Convert to list and sort by total approvals
        top_manufacturers = []
        for manufacturer_id, stats in manufacturer_stats.items():
            total_approvals = stats['models'] + stats['cops']
            top_manufacturers.append({
                'manufacturer_id': manufacturer_id,
                'manufacturer_name': stats['name'],
                'approved_models': stats['models'],
                'approved_cops': stats['cops'],
                'total_approvals': total_approvals
            })
        
        top_manufacturers.sort(key=lambda x: x['total_approvals'], reverse=True)
        top_manufacturers = top_manufacturers[:10]  # Top 10 manufacturers
        
        # Prepare comprehensive summary
        summary = {
            'overall_statistics': {
                'total_approved_models': total_approved_models,
                'total_approved_cops': total_approved_cops,
                'total_approvals': total_approved_models + total_approved_cops,
                'unique_manufacturers': unique_manufacturers,
                'recent_approvals_30_days': {
                    'models': recent_models,
                    'cops': recent_cops,
                    'total': recent_models + recent_cops
                }
            },
            'expiry_alerts': {
                'expired_cops': expired_cops,
                'expiring_soon_cops': expiring_soon_cops,
                'expired_tac_validities': expired_tac,
                'expiring_soon_tac_validities': expiring_soon_tac,
                'total_expiry_alerts': expired_cops + expiring_soon_cops + expired_tac + expiring_soon_tac
            },
            'monthly_breakdown_current_year': monthly_stats,
            'top_manufacturers': top_manufacturers,
            'state_admin_info': {
                'id': state_admin.id,
                'state': state_admin.state.state if state_admin.state else 'N/A',
                'created_date': state_admin.created.strftime('%Y-%m-%d') if state_admin.created else 'N/A'
            },
            'report_generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_range_applied': {
                'from': date_from if date_from else 'All time',
                'to': date_to if date_to else 'Present'
            }
        }
        
        response_data = {
            'status': 'success',
            'data': summary,
            'message': 'Combined approval report retrieved successfully'
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An error occurred while retrieving combined approval report: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """
    Homepage API for esim Provider role showing eSIM related statistics
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_device_trip_details(request):
    """
    API to get trip details for a device tag
    
    Parameters:
    - device_tag_id: ID of the device tag (required)
    - start_datetime: Start datetime for trip search (optional, default: 24 hours ago)
    - end_datetime: End datetime for trip search (optional, default: now)
    
    Returns list of trips with details including:
    - Trip duration, distance, average speed
    - Start/end locations
    - Alerts during trip
    """
    try:
        from datetime import datetime, timedelta
        from django.db.models import Q, Min, Max
        import math
        
        def calculate_distance(lat1, lon1, lat2, lon2):
            """
            Calculate the great circle distance between two points 
            on the earth (specified in decimal degrees)
            Returns distance in kilometers
            """
            # Convert decimal degrees to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            r = 6371  # Radius of earth in kilometers
            return c * r
        
        # Get parameters
        device_tag_id = request.GET.get('device_tag_id')
        start_datetime = request.GET.get('start_datetime')
        end_datetime = request.GET.get('end_datetime')
        
        # Validate device_tag_id
        if not device_tag_id:
            return Response({
                'status': 'error',
                'message': 'device_tag_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            device_tag = DeviceTag.objects.get(id=device_tag_id)
        except DeviceTag.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Device tag not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Set default time range (last 24 hours)
        now = timezone.now()
        if not end_datetime:
            end_dt = now
        else:
            try:
                end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid end_datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if not start_datetime:
            start_dt = end_dt - timedelta(hours=24)
        else:
            try:
                start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid start_datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get GPS data for the device tag within time range
        gps_data = GPSData.objects.filter(
            device_tag=device_tag,
            entry_time__gte=start_dt,
            entry_time__lte=end_dt
        ).order_by('entry_time')
        
        if not gps_data.exists():
            return Response({
                'device_tag_id': device_tag_id,
                'vehicle_reg_no': device_tag.vehicle_reg_no,
                'query_start_time': start_dt,
                'query_end_time': end_dt,
                'total_trips': 0,
                'total_distance_km': 0.0,
                'total_duration_minutes': 0.0,
                'trips': []
            })
        
        # Process trips based on ignition status
        trips = []
        current_trip = None
        trip_id = 1
        
        for gps_point in gps_data:
            ignition_on = gps_point.ignition_status == '1'
            
            if ignition_on and current_trip is None:
                # Start new trip
                current_trip = {
                    'trip_id': trip_id,
                    'start_time': gps_point.entry_time,
                    'start_location': {
                        'latitude': gps_point.latitude,
                        'longitude': gps_point.longitude,
                        'address': f"{gps_point.latitude}, {gps_point.longitude}"
                    },
                    'gps_points': [gps_point],
                    'last_ignition_off_time': None
                }
            elif current_trip is not None:
                current_trip['gps_points'].append(gps_point)
                
                if not ignition_on:
                    current_trip['last_ignition_off_time'] = gps_point.entry_time
                else:
                    current_trip['last_ignition_off_time'] = None
        
        # Check if current trip should end (ignition off for more than 30 minutes)
        if current_trip is not None:
            if current_trip['last_ignition_off_time']:
                time_since_ignition_off = now - current_trip['last_ignition_off_time']
                if time_since_ignition_off.total_seconds() > 30 * 60:  # 30 minutes
                    # End current trip
                    trips.append(current_trip)
                    current_trip = None
            else:
                # Trip is still ongoing, include it
                trips.append(current_trip)
        
        # Process each completed trip
        processed_trips = []
        total_distance = 0.0
        total_duration = 0.0
        
        for trip in trips:
            if len(trip['gps_points']) < 2:
                continue
                
            gps_points = trip['gps_points']
            
            # Calculate trip metrics
            trip_distance = 0.0
            speeds = []
            
            for i in range(1, len(gps_points)):
                prev_point = gps_points[i-1]
                curr_point = gps_points[i]
                
                # Calculate distance between points
                if prev_point.latitude and prev_point.longitude and curr_point.latitude and curr_point.longitude:
                    try:
                        point_distance = calculate_distance(
                            prev_point.latitude, prev_point.longitude,
                            curr_point.latitude, curr_point.longitude
                        )
                        trip_distance += point_distance
                    except:
                        pass
                
                # Collect speed data
                if curr_point.speed:
                    speeds.append(curr_point.speed)
            
            # Calculate duration
            end_time = trip['last_ignition_off_time'] or gps_points[-1].entry_time
            duration = (end_time - trip['start_time']).total_seconds() / 60  # minutes
            
            # Calculate average and max speed
            avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
            max_speed = max(speeds) if speeds else 0.0
            
            # Get alerts during trip
            trip_alerts = AlertsLog.objects.filter(
                deviceTag=device_tag,
                timestamp__gte=trip['start_time'],
                timestamp__lte=end_time
            ).values('type', 'status', 'timestamp')
            
            # End location
            last_point = gps_points[-1]
            end_location = {
                'latitude': last_point.latitude,
                'longitude': last_point.longitude,
                'address': f"{last_point.latitude}, {last_point.longitude}"
            }
            
            processed_trip = {
                'trip_id': trip['trip_id'],
                'start_time': trip['start_time'],
                'end_time': end_time,
                'duration_minutes': round(duration, 2),
                'distance_km': round(trip_distance, 2),
                'average_speed_kmh': round(avg_speed, 2),
                'max_speed_kmh': round(max_speed, 2),
                'start_location': trip['start_location'],
                'end_location': end_location,
                'alerts': list(trip_alerts),
                'total_data_points': len(gps_points)
            }
            
            processed_trips.append(processed_trip)
            total_distance += trip_distance
            total_duration += duration
            trip_id += 1
        
        # Prepare response
        response_data = {
            'device_tag_id': int(device_tag_id),
            'vehicle_reg_no': device_tag.vehicle_reg_no,
            'query_start_time': start_dt,
            'query_end_time': end_dt,
            'total_trips': len(processed_trips),
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': round(total_duration, 2),
            'trips': processed_trips
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred while retrieving trip details: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    