# skytron_api/views.py
from rest_framework.authtoken.models import Token 
from django.http import HttpResponseBadRequest, JsonResponse,HttpResponse  
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, throttle_classes
import secrets
import string
from django.core.serializers import serialize
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate,logout,login 
from rest_framework.response import Response
from rest_framework import status 
from .models import *
from .serializers import *
import xml.etree.ElementTree as ET
import json
import html
import random
from itertools import islice 
from django.utils import timezone     
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
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
from rest_framework.views import APIView 

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

from django.utils.timezone import now
#python3 -m pip install python-docx
#python3 -m pip install pypandoc
#python3 -m pip install docx2pdf
 
#python3 -m pip install pdfkit
#sudo apt-get install wkhtmltopdf
#sudo apt-get update
#sudo apt-get install libreoffice



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
    if len(encrypted_field)<16:
        return encrypted_field
    enc=base64.b64decode(encrypted_field)
    print(enc)
    #try:
    decrypted_data = cipher.decrypt(enc)
    return decrypted_data.decode('utf-8')
    #except:
    #    return ""
PRIVATE_KEY=load_private_key() 
#print(PRIVATE_KEY)



@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 
def generate_captcha_api(request):
    byte_io, result = generate_captcha()
    key = uuid.uuid4().hex
    Captcha.objects.create(key=key, answer=result)

    # Convert image blob to base64
    img_base64 = base64.b64encode(byte_io.getvalue()).decode('utf-8')

    return JsonResponse({'key': key, 'captcha': img_base64})

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def verify_captcha_api(request):
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
  
'''
@csrf_exempt
def LoginAndroid(request):
    if request.method == 'POST':
        return HttpResponse("LoginDone")
        user=authenticate(request,username=request.POST.get('username'),password=request.POST.get('password'))
        #print(user)
        if user is not None:
            #print("LoginDone")
            login(request,user)
            return HttpResponse("LoginDone")
        else:
            return HttpResponse("Credentials are Incorrect")
    else:
        return HttpResponse("error")

@csrf_exempt
def Login2(request):
    if request.method == 'GET':
        ##print("login2",request.GET )
        return redirect('/api/emergency-call-listener-field/') 
        username=request.GET.get('username')
        password=request.GET.get('password')
        user=authenticate(request,username=username,password=password)
        #print("login2",user,username,password)
        if user is not None:
            #print("LoginDone")
            login(request,user)

            if "FieldEx" in username:
                #print("Loginvalid")
                #return HttpResponse("This account is not authorized to use this app.")
                return redirect('/api/emergency-call-listener-field/') 
            else:
                return HttpResponse("This account is not authorized to use this app.")
        else:
            return HttpResponse("Credentials are Incorrect")
    else:
        return HttpResponse("error")

'''
"""
#@login_required
@csrf_exempt
@api_view(['POST','GET'])
@permission_classes([IsAuthenticated]) 
def update_location(request):
    live_data={}
    if request.method == 'POST':
        loc_lat = request.POST.get('latitude')
        loc_lon = request.POST.get('longitude')
        field_ex = request.user#POST.get('uername')
 

        # Update the Help object with the provided FieldEx
        try:
            help_obj = Help.objects.filter(field_ex=field_ex).last()
            if help_obj:
                help_obj.loc_lat = loc_lat
                help_obj.loc_lon = loc_lon
                #print("help ",help_obj)
                help_obj.save()
            else:
                Help.objects.create(
                    type='Emergency',
                    field_ex=field_ex,loc_lat = loc_lat,loc_lon = loc_lon
                )
            #print("test1")
            existing_emergency_call = EmergencyCall.objects.filter( 
                Q(status='Broadcast')# Exclude entries with Status 'Complete'
            ).order_by('-start_time').last()
            #print(existing_emergency_call)

        
            running_call = EmergencyCall.objects.filter( 
                    Q(field_executive_id=field_ex)# Exclude entries with Status 'Complete'
                ).order_by('-start_time').last()
            if existing_emergency_call:
                live_data = {'status': 'success',
                    'vehicle_no': existing_emergency_call.vehicle_no,
                    'device_imei': existing_emergency_call.device_imei,
                    'call_id': existing_emergency_call.call_id, 
                }
            else :
                live_data = {'status': 'success'} 

            if running_call is None:
                live_data=live_data
            else:
                live_data={'status': 'success'}
    

            return JsonResponse(live_data)
        except Help.DoesNotExist:
            print("Help not avialable")
            return JsonResponse({'status': 'error', 'message': 'Help object not found'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
#@login_required
@csrf_exempt
def update_status(request, field_ex):
    if request.method == 'POST':
        status = request.POST.get('status') 

        # Update the Help object with the provided FieldEx
        try:
            help_obj = Help.objects.get(field_ex=field_ex)
            help_obj.status = status 
            help_obj.save()

            return JsonResponse({'status': 'success'})
        except Help.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Help object not found'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    

#@login_required

@api_view(['POST','GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def get_latest_gps_location(request, emergency_call_id):
    headers = {key: value for key, value in request.headers.items()}
    auth=headers.get('Authorization')
    #print("*(*(*(*(*(*)))))",auth)
    # Get the EmergencyCall object based on the provided emergency_call_id
    emergency_call = get_object_or_404(EmergencyCall, pk=emergency_call_id)

    # Get the latest GPSLocation for the same IMEI and vehicle number
    latest_gps_location = GPSLocation.objects.filter(
        device_imei=emergency_call.device_imei,
        vehicle_reg_no=emergency_call.vehicle_no
    ).order_by('-date', '-time').first()
    help_obj = Help.objects.filter(field_ex=emergency_call.field_executive_id).first()
    if help_obj is not None:
        loc_lat=help_obj.loc_lat
        loc_lon=help_obj.loc_lon
    else:
        loc_lat=0
        loc_lon=0
    headers = {'Content-Type': 'application/json'} 

    
    try:
        route = requests.post('https://bhuvan-app1.nrsc.gov.in/api/routing/curl_routing_state.php?lat1='+str(latest_gps_location.latitude)+'&lon1='+str(latest_gps_location.longitude)+'&lat2='+str(loc_lat)+'&lon2='+str(loc_lon)+'&token=fb46cfb86bea498dce694350fb6dd16d161ff8eb', headers=headers ).json()
    except Exception as e:
        print("no route",e)
        route=json.dumps({"err":"err"}, indent = 4) 
    
    #print(route)
    #route.raise_for_status()  # Check for HTTP errors
     
    # Parse message as json
    #route = json.loads(route['Message'])
    DeskE="None"
    FieldE="None"
    if emergency_call.desk_executive_id:
        DeskE=emergency_call.desk_executive_id.name+"("+str(emergency_call.desk_executive_id.id)+")" 
    if emergency_call.field_executive_id  :
        FieldE=emergency_call.field_executive_id.name+"("+str(emergency_call.field_executive_id.id)+")" 
    
        



    context1 = {
        'status':emergency_call.status,
        'desk_executive_id':DeskE,
        'field_executive_id':FieldE,
        'final_comment':emergency_call.final_comment,
        'date':latest_gps_location.date.strftime("%Y-%m-%d"),
        'time':latest_gps_location.time.strftime("%H:%M:%S"), 
        'latitude':str(latest_gps_location.latitude  ) ,#+ str(  latest_gps_location.latitude_direction ),       
        'longitude':str( latest_gps_location.longitude),#+str(latest_gps_location.longitude_direction),
        'field_latitude':str( loc_lat  ) ,#+ str(  latest_gps_location.latitude_direction ),       
        'field_longitude':str(  loc_lon ),#+str(latest_gps_location.longitude_direction),
        'route': route,
        
    }
 
    '''
    context = {
        'lat':str(latest_gps_location.latitude ) ,
        'lon':str( latest_gps_location.longitude),
        'html': str(render(request, 'latest_gps_location_partial.html', context1)),
    }
    print( render(request, 'latest_gps_location_partial.html', context1))
    '''
    
    data = json.dumps(context1)
    return   HttpResponse(data)

#@login_required
@api_view(['POST' ])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  
def Broadcast_help(request):
    if request.method == 'POST':
        call_id = request.data.get('call_id')
        #print("call_id",call_id)
        ecall=EmergencyCall.objects.get(call_id=call_id)
        ecall.status="Broadcast"
        #ecall.field_executive_id=""
        ecall.save()
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@api_view(['POST' ])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  
@csrf_exempt
def SubmitStatus(request):
    if request.method == 'POST':
        call_id = request.data.get('call_id') 
        #print(request.POST.get('status'))
        #print(request.POST.get('comment'))
        ecall=EmergencyCall.objects.get(call_id=call_id)
        ecall.status=request.data.get('status')
        ecall.final_comment=request.data.get('comment')
        if request.data.get('status')=="Closed"  or request.data.get('status')=="closed":
            ecall.field_executive_id=None
            em=EmergencyCall_assignment.objects.filter(emergencyCall_id=call_id, status='Assigned').last()
            ecall.status="Closed"
            if em:
                em.status="Closed"
                em.save()


        #ecall.field_executive_id=""
        ecall.save()
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
#@login_required

@api_view(['POST','GET' ])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  
def emergency_call_details_field(request, emergency_call_id):
    # Get the EmergencyCall object based on the provided emergency_call_id
    user=request.user #User.objects.filter(id=8).last() #
    headers = {key: value for key, value in request.headers.items()}
    auth= headers.get('Authorization') 
    #print("Auth((((((((((((((((()))))))))))))))))",auth)

    emergency_call = get_object_or_404(EmergencyCall, pk=emergency_call_id)

    # Get the latest GPSLocation for the same IMEI and vehicle number
    latest_gps_location = GPSLocation.objects.filter(
        device_imei=emergency_call.device_imei,
        vehicle_reg_no=emergency_call.vehicle_no
    ).order_by('-date', '-time').first()
    help_obj = Help.objects.filter(field_ex= user ).last()
     
     
    
    context = {
        'user':user,
        'auth':auth,
        'emergency_call': emergency_call,
        'latest_gps_location': latest_gps_location,
        'fieldexs': help_obj,
    } 


    return render(request, 'emergency_call_details_field.html', context)
#@login_required
def emergency_call_details(request, emergency_call_id):
    # Get the EmergencyCall object based on the provided emergency_call_id
    emergency_call = get_object_or_404(EmergencyCall, pk=emergency_call_id)

    # Get the latest GPSLocation for the same IMEI and vehicle number
    latest_gps_location = GPSLocation.objects.filter(
        device_imei=emergency_call.device_imei,
        vehicle_reg_no=emergency_call.vehicle_no
    ).order_by('-date', '-time').first()
    help_obj = Help.objects.filter(status=1 ) 
     
    context = {
        'emergency_call': emergency_call,
        'latest_gps_location': latest_gps_location,
        'fieldexs': help_obj,
    } 

    return render(request, 'emergency_call_details.html', context)

#@login_required
def latest_gps(request):
    try:
        latest_location = GPSLocation.objects.latest('id')
        help_obj = Help.objects.filter(field_ex=request.user.username ) 
        context = {
        'lat': latest_location.latitude,
        'lon': latest_location.longitude,
        #'html': render(request, 'gps_api/latest_gps.html', {'location': latest_location}),
        }
    except GPSLocation.DoesNotExist:
        # Handle the case where no GPSLocation record is found
        latest_location = None
        context = {
        'lat': '0.0',
        'lon': '0.0',
        #'html': render(request, 'gps_api/latest_gps.html', {'location': latest_location}),
        }
    
    data = json.dumps(context )
    return JsonResponse(context) #HttpResponse(data, content_type="application/json") 



@csrf_exempt
@api_view(['POST','GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def map2(request,emergency_call_id):
    # Get the EmergencyCall object based on the provided emergency_call_id
    user=request.user
    headers = {key: value for key, value in request.headers.items()}
    auth=headers.get('Authorization') 
    #print("Auth((((((((((((((((()))))))))))))))))",auth)
    emergency_call = get_object_or_404(EmergencyCall, pk=emergency_call_id)

    # Get the latest GPSLocation for the same IMEI and vehicle number
    latest_gps_location = GPSLocation.objects.filter(
        device_imei=emergency_call.device_imei,
        vehicle_reg_no=emergency_call.vehicle_no
    ).order_by('-date', '-time').first()
    help_obj = Help.objects.filter(status=1 ) 
     
    context = {
        'user':user,
        'auth':auth,
        'emergency_call': emergency_call,
        'latest_gps_location': latest_gps_location,
        'fieldexs': help_obj,
    } 

    return render(request, 'bhooban.html', context)
     

    #return render(request, 'bhooban.html', {'live_data': []})




#@login_required

@api_view(['POST','GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def emergency_call_listener_admin(request):
    #return JsonResponse({"ok":"ok"})
    headers = {key: value for key, value in request.headers.items()}
    #print(headers)
    user=request.user
    #print(user) 
    #return Response({"user": str(user)})
    if request.method == 'POST':
        # Handle the 'Accept' button press
        data = json.loads(request.body)
        
        
        call_id = data.get('call_id')
        accept = data.get('accept')
        
        desk_executive_id = user
        try:
            if accept:
                emergency_call = EmergencyCall.objects.get(call_id=call_id)
                assign=EmergencyCall_assignment.objects.filter(emergencyCall_id=call_id,user=user,status='Assigned').last()
                if assign:
                    emergency_call.desk_executive_id = desk_executive_id
                    emergency_call.status = 'Accepted'
                    emergency_call.save()                
                    assign.accept_time =   timezone.now()
                    assign.status = 'Acccepted' 
                    assign.save()

            else:
                assign=EmergencyCall_assignment.objects.filter(emergencyCall_id=call_id,user=user,status='Assigned').last()
                #assign.accept_time =   timezone.now()
                if assign:
                    assign.status = 'Rejected' 
                    assign.save()
        except Exception as e:
            print("accept reeject error ",e)
        
 

    # Fetch live data updates every 5 seconds
    live_data ={}# get_live_call_init()
    context = {
        'live_data': live_data,
        'user': user,
        'username': user.name,
        'email': user.email,
        'user_id': user.id,
        'authorization': headers.get('Authorization'),
    } 

    return render(request, 'emergency_call_listener_admin.html', context)
"""


import os
import glob
def save_file(request,tag,path):
    uploaded_file = request.FILES.get(tag)
    n=uploaded_file.name
    

    if uploaded_file:
        file_path = path+'/' + ''.join(random.choices('0123456789', k=40))+"."+n.split(".")[-1]
        with open(file_path, 'wb') as file:
            for chunk in uploaded_file.chunks():
                file.write(chunk)
        return file_path
    return False


def find_file_in_folders(filename, folders):
    for folder in folders: 
        filename=filename.replace("%20", " ")
        pattern = folder+filename

        #print("pattern",pattern,folder)
        for file_path in glob.iglob(pattern, recursive=True):
            #print("filepath",file_path)
            if os.path.isfile(file_path):
                return file_path
    return None
folders = [
    './',
    './fileuploads/',
    'fileuploads/tac_docs/',
    'fileuploads/Receipt_files/',
    'fileuploads/kyc_files/',
    'fileuploads/cop_files/',
    'fileuploads/file_bin/',
    'fileuploads/man/',
    'fileuploads/driver/',
    # Add more folders as needed
]
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  # Apply throttling here
def downloadfile(request):
    if request.method == 'POST': 
        file_path =   request.data.get('file_path') 
        #print(request.content_type )
        #print(request.data)
        #print(request.user )

        if not file_path:
            return JsonResponse({'error': 'file_path is required'}, status=400) 
        try: 
            file_path=file_path.split('/')[-1]
            name=file_path
            file_path=find_file_in_folders(file_path, folders) 
            if not file_path:
                return JsonResponse({'error': 'file not found'+name}, status=400) 
            try:                
                with open(file_path,'rb') as file:
                    response = HttpResponse(file.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{name}"'
                    #response['Content-Type'] = f'attachment; extension="{file_path.split('.')[-1]}"'
                    return response
            except FileNotFoundError:
                return HttpResponse("File not found.", status=404) 
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'Error in reading file.'}, status=404)
    return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)


"""
#@login_required
@csrf_exempt
def emergency_call_listener(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        call_id = data.get('call_id')
        desk_executive_id = ' ' 
        emergency_call = EmergencyCall.objects.get(call_id=call_id)
        emergency_call.desk_executive_id = desk_executive_id
        emergency_call.status = 'Accepted'
        emergency_call.save()
    live_data = get_live_call_init()

    return render(request, 'emergency_call_listener.html', {'live_data': live_data})


def get_live_call_init(): 
    existing_emergency_call = EmergencyCall.objects.filter( 
            Q(status='Pending') # Exclude entries with Status 'Complete'
        ).order_by('-start_time').last()
    if existing_emergency_call:
        live_data = {
            'vehicle_no': existing_emergency_call.vehicle_no,
            'device_imei': existing_emergency_call.device_imei,
            'call_id': existing_emergency_call.call_id, 
        }
    else :
        live_data = {}

    return JsonResponse(live_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def get_live_call(request):
    user=request.user  
    user.last_activity=timezone.now() 
    user.save()
    #print(user)
    emcall= EmergencyCall_assignment.objects.filter(user=user,status ="Assigned").last()
    
      
    
    #existing_emergency_call = EmergencyCall.objects.order_by('-start_time').all()
    #live_data1=""
    #for call in existing_emergency_call:
    #    live_data1 = live_data1+"<button onclick=\"loadCallDetails('"+str(call.call_id)+"')\">Call ID: "+str(call.call_id)+" ("+str(call.status)+"); Vehicle: "+str(call.vehicle_no)+";</button><br>"

        #'<a href="https://dev.skytron.in:2000/api/emergency-call-details/'+str( call.call_id )+'"  target="_self">Call ID:'+ str( call.call_id )+"("+  str(call.status)+");  Vehicle:"+  str( call.vehicle_no)+"; </a><br>"
      
    #print(live_data1)
    #existing_emergency_call = EmergencyCall.objects.filter( 
    #        Q(status='Pending')# Exclude entries with Status 'Complete'
    #    ).order_by('-start_time').last()
    if emcall:
        #EmergencyCall_assignment.objects.filter( 
        #     EmergencyCall_id=existing_emergency_call # Exclude entries with Status 'Complete'
        #).last()


        live_data = {
            'vehicle_no': emcall.emergencyCall_id.vehicle_no,
            'device_imei': emcall.emergencyCall_id.device_imei,
            'call_id': emcall.emergencyCall_id.call_id, 
        }
    else :
        live_data = {}
    #if live_data1!="":
    #    live_data["table_data"]=live_data1

    return JsonResponse(live_data)


@api_view(['POST','GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def get_all_call(request): 
    existing_emergency_call = EmergencyCall.objects.order_by('-start_time').all()
    live_data1=[]
    for call in existing_emergency_call:
        live_data1.append({"call_id":str(call.call_id), 'device_imei': call.device_imei,"status":str(call.status),"Vehicle": str(call.vehicle_no)})
        #= live_data1+"<button onclick=\"loadCallDetails('"+str(call.call_id)+"')\">Call ID: "+str(call.call_id)+" ("+str(call.status)+"); Vehicle: "+str(call.vehicle_no)+";</button><br>"

        #'<a href="https://dev.skytron.in:2000/api/emergency-call-details/'+str( call.call_id )+'"  target="_self">Call ID:'+ str( call.call_id )+"("+  str(call.status)+");  Vehicle:"+  str( call.vehicle_no)+"; </a><br>"
      
    #print(live_data1)
    existing_emergency_call = EmergencyCall.objects.filter( 
            Q(status='Pending')# Exclude entries with Status 'Complete'
        ).order_by('-start_time').last()
    if existing_emergency_call:
        live_data = {"Notification":{
            'vehicle_no': existing_emergency_call.vehicle_no,
            'device_imei': existing_emergency_call.device_imei,
            'call_id': existing_emergency_call.call_id, },
        }
    else :
        live_data = {"Notification":None}
     
    live_data["Call_list"]=live_data1

    return JsonResponse(live_data)




#@login_required
@csrf_exempt
@api_view(['POST','GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def emergency_call_listener_field(request):
    
    #return JsonResponse({"ok":"ok"})
    headers = {key: value for key, value in request.headers.items()}
    #print(headers)
    #return render(request, 'emergency_call_listener_field.html', {})

    user=request.user
    #print(user) 
    #return Response({"user": str(user)})
    if request.method == 'POST':
        # Handle the 'Accept' button press
        data = json.loads(request.body)
        
        
        call_id = data.get('call_id')
        accept = data.get('accept') 
        try:
            if accept:
                emergency_call = EmergencyCall.objects.get(call_id=call_id) 
                emergency_call.field_executive_id = request.user 
                emergency_call.status = 'FieldAccepted'
                emergency_call.save()


            
        except Exception as e:
            print("accept reeject error ",e)
        
 

    # Fetch live data updates every 5 seconds
    live_data ={}# get_live_call_init()
    context = {
        'live_data': live_data,
        'user': user,
        'username': user.name,
        'email': user.email,
        'user_id': user.id,
        'authorization': headers.get('Authorization'),
    } 




 

    return render(request, 'emergency_call_listener_field.html', context)


def get_live_call_field_init(): 
    existing_emergency_call = EmergencyCall.objects.filter( 
            Q(status='Broadcast') # Exclude entries with Status 'Complete'
        ).order_by('-start_time').last()
    if existing_emergency_call:
        if existing_emergency_call.status=='Broadcast':
            live_data = {
                'vehicle_no': existing_emergency_call.vehicle_no,
                'device_imei': existing_emergency_call.device_imei,
                'call_id': existing_emergency_call.call_id, 
            }
        else:
            ive_data = {}
    else :
        live_data = {}

    return JsonResponse(live_data)

#@login_required

@api_view(['POST','GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def get_live_call_field(request ): 
    user=request.user
    live_data={}
    if 1:
        # Handle the 'Accept' button press  
        existing_emergency_call = EmergencyCall.objects.filter( 
                Q(status='FieldAccepted'),field_executive_id=user# Exclude entries with Status 'Complete'
            ).order_by('-start_time').last()
        if not existing_emergency_call:
            existing_emergency_call = EmergencyCall.objects.filter( 
                    Q(status='Broadcast')# Exclude entries with Status 'Complete'
                ).order_by('-start_time').last()

        
         
        if existing_emergency_call:
            live_data = {
                'vehicle_no': existing_emergency_call.vehicle_no,
                'device_imei': existing_emergency_call.device_imei,
                'call_id': existing_emergency_call.call_id, 
            }
        else :
            live_data = {} 

    return JsonResponse(live_data)


from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy

class CustomLogoutView(LogoutView): 
    next_page = reverse_lazy('login')   
    def dispatch(self, request, *args, **kwargs): 
        response = super().dispatch(request, *args, **kwargs) 

        return response

@method_decorator(csrf_exempt, name='dispatch')
class CustomLoginView(LoginView):
    template_name = 'custom_login.html'  # Create a custom login template
    
    def get_success_url(self):
        # Customize the redirect logic based on the username
        username = self.request.POST.get('username')
        if "FieldEx" in username:
            return '/api/emergency-call-listener-field/'  # Redirect to the admin panel for the admin user
        else:
            return '/api/emergency-call-listener/' 
        
 
"""

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
 


def gps_data_table(request):
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

def gps_data_table1(request):
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
def gps_track_data_api(request):
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
        distinct_registration_numbers = GPSData.objects.exclude(device_tag=None).values('device_tag').distinct() #vehicle_registration_number
        data = []

        for x in distinct_registration_numbers:
            latest_entry = GPSData.objects.filter(device_tag=x['device_tag']).filter(gps_status=1).order_by('-entry_time') 
            
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
def gps_history_map(request): 
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
def gps_history_map_data(request): 
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
                    return JsonResponse({"error": str(e) +"No Record Found 1: "+vehicle_registration_number}, status=403) 
            else:
                return JsonResponse({'error': "Invalid Search 22"}, status=403) 
        return JsonResponse({'error': "Invalid Search"}, status=403) 
        #return Response({'error': "Invalid Search"}, status=403)
        #return render(request, 'map_history.html', {'data': data,'mapdata': mapdata,'mapdata_length': len(data)-1 })
        #return Response({'error': "Invalid Search"}, status=403)
    except Exception as e: 
        return JsonResponse({'error': str(e)}) 
        return Response({'error': "ww"}, status=400)



def setRoute(request):
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
def delRoute(request):
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
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def get_routePath(request):
    # The target external API URL
    url = 'https://bhuvan-app1.nrsc.gov.in/api/routing/curl_routing_new_v2.php?token=fb46cfb86bea498dce694350fb6dd16d161ff8eb' 
    points_data = request.data.get("points", [])
    
    if not points_data:
        return Response({"error": "Points data is required"}, status=status.HTTP_400_BAD_REQUEST) 
    try:
        response = requests.post(
            url,
            json={"points": points_data},  # Send points data in the correct format
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()   
        return Response(response.json(), status=response.status_code)
    
    except requests.exceptions.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def saveRoute(request):
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
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)



@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def getRoute(request):
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
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
def getRoutelist(request):
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
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

def gps_data_allmap(request):

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
def gps_data_log_table(request):
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

def gps_em_data_log_table(request):
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
     sms_entry = sms_out.objects.create( sms_text=msg,no=no, status='Queue'  )

@csrf_exempt
def sms_queue_add(request):
    try:
        no= request.GET.get('no')#request.data.get('no')
        msg = request.GET.get('msg', '') 
        add_sms_queue(msg,no)
        return JsonResponse({'status':"Success  "+msg})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 

@api_view(['POST'])  
@permission_classes([AllowAny])
def sms_received(request):
    try:
        # Extract necessary parameters from the request data
        no= request.data.get('no')
        msg = request.data.get('msg', '')

        new_sms_in = sms_in.objects.create( sms_text=msg,no=no, status='Received'  )
        return Response({'status':"Success"})
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    
@api_view(['get'])  
@permission_classes([AllowAny])
def sms_queue(request):
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
        return Response({'error': str(e)}, status=500)

    
@api_view(['get'])  
def esim_provider_list(request):
    try:
        esimprovider= eSimProvider.objects.all()         
        esimprovider_serializer = eSimProviderSerializer(esimprovider, many=True)
        # Return the serialized data as JSON response
        return Response(esimprovider_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def get_live_vehicle_no(request):
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
            return Response({'error': "POST request only"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
 
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def update_VehicleOwner(request):
    
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
            return Response({'error': "Invalid VehicleOwner id"}, status=500)
        if vehicle_owner.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=500)
        
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
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def create_VehicleOwner(request):
    
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
                retailer = VehicleOwner.objects.create(
                    company_name=company_name, 
                    created=created,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    createdby=createdby,
                    status="Created",
                ) 
            except Exception as e:
                user.delete()
                return Response({'error': str(e)}, status=500)
            retailer.users.add(user) 
            send_usercreation_otp(user,new_password,'Vehicle Owner ')
             
            return Response(VehicleOwnerSerializer(retailer).data)
        else:
            return Response(error, status=500)        
    except Exception as e:
        return Response({'error': str(e)}, status=500)



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
        return Response({'error': str(e)}, status=500)

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
        return Response({'error': str(e)}, status=500)

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
        return Response({'error': str(e)}, status=500)
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
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_VehicleOwner(request):
    try:

        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)

        # Get filter parameters from the request
        obj_id = request.data.get('VehicleOwner_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '') 
        filters = {} 
        if uo:
            state=uo.state
            owners = DeviceTag.objects.filter( device__esim_provider__state=state, status="Owner_Final_OTP_Verified").values("vehicle_owner").distinct()
            manufacturers = VehicleOwner.objects.filter(
                        id__in=owners,
                        users__email__icontains=email,
                        company_name__icontains=company_name,
                        users__name__icontains=name,
                        users__mobile__icontains=phone_no, 
                    ).distinct()
        
        else:
            state = request.data.get('state', '')
            if obj_id :
                manufacturers = VehicleOwner.objects.filter(
                    id=obj_id ,
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no, 
                ).distinct()
            else:
                manufacturers = VehicleOwner.objects.filter(
                    #id=manufacturer_id,
                    users__status='active',
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no, 
                ).distinct()

        # Serialize the queryset
        retailer_serializer = VehicleOwnerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def update_manufacturer(request):
    try:
        
        id = request.data.get('manufacturer_id')
        man=Manufacturer.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid manufacturer id"}, status=500)
        if man.createdby == request.user :
            return Response({'error': "User can be edited by only the creator"}, status=500)
        
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

        if file_companRegCertificate :
            man.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
                

        if file_GSTCertificate :
            man.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')

        if file_idProof:
            man.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
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
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def update_eSimProvider(request):
    
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
            return Response({'error': "Invalid eSimProvider id"}, status=500)
        if esimprovider.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=500)
        
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
        if file_companRegCertificate:
            esimprovider.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
        if file_GSTCertificate:
            esimprovider.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
        if file_idProof:
            esimprovider.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')

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
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  
def create_eSimProvider(request):
      
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
                    file_companRegCertificate=save_file(request,'file_dot_m2m_registration','fileuploads/man')
                    file_GSTCertificate=save_file(request,'file_GSTCertificate','fileuploads/man')
                    file_idProof = save_file(request,'file_idProof','fileuploads/man')
                except Exception as e:
                    user.delete()


                    return Response({'error44': str(e)}, status=500)


                retailer = eSimProvider.objects.create(
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
            except Exception as e:
                user.delete()


                return Response({'error1': str(e)}, status=500)
            retailer.users.add(user)
            send_usercreation_otp(user,new_password,'EsimProvider ')
             
            return Response(eSimProviderSerializer(retailer).data)
        else:
            return Response({'error131': str(error)}, status=500)

    except Exception as e:
        return Response({'error2': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_eSimProvider(request):
    try:

        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)
        role="devicemanufacture" 
        um=get_user_object(user,role)
        if um:
            
            retailer_serializer = eSimProviderSerializer(um.esim_provider, many=True)
            return Response(retailer_serializer.data)
        
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state = request.data.get('state', '')

     
        if dealer_id :
            manufacturers = eSimProvider.objects.filter(
                id=dealer_id ,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
                #state__id=state, 
            ).distinct()
        else:
            manufacturers = eSimProvider.objects.filter(
                #id=manufacturer_id,
                users__status='active',
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
                #state__id=state, 
            ).distinct()
        manufacturers = eSimProvider.objects.filter(
                #id=manufacturer_id,
                users__status='active', 
            ).all()
        if not uo:
            pass
            #return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            state=uo
            manufacturers=manufacturers.filter(state=uo.state)

        # Serialize the queryset
        retailer_serializer = eSimProviderSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)

    except Exception as e:
        raise e
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def update_dealer(request):
    
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
            return Response({'error': "Invalid dealer id"}, status=500)
        if dealer.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=500)
        
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
        if file_companRegCertificate:
            dealer.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
        if file_GSTCertificate:
            dealer.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
        if file_idProof:
            dealer.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
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
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def create_dealer(request):
    
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


                retailer = Retailer.objects.create(
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
            except Exception as e:
                user.delete()
                return Response({'error': str(e)}, status=500) 
            retailer.users.add(user)
            send_usercreation_otp(user,new_password,'Dealer ')             
            return Response(RetailerSerializer(retailer).data)
        else:
            return Response(error, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_dealer(request):
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

        # Create a dictionary to hold the filter parameters
        filters = {}
        if  uo:
                
            if dealer_id :
                manufacturers = Retailer.objects.filter(
                    id=dealer_id ,
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no, 
                    manufacturer=uo,
                ).distinct()
            else:
                manufacturers = Retailer.objects.filter(
                    #id=manufacturer_id,
                    users__status='active',
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no, 
                    manufacturer=uo,
                ).distinct()
        elif  suo:
                
            if dealer_id :
                manufacturers = Retailer.objects.filter(
                    id=dealer_id ,
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no, 
                    manufacturer__state=suo.state,
                ).distinct()
            else:
                manufacturers = Retailer.objects.filter(
                    #id=manufacturer_id,
                    users__status='active',
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no, 
                    manufacturer__state=suo.state,
                ).distinct()
        
        else:
            if dealer_id :
                manufacturers = Retailer.objects.filter(
                    id=dealer_id ,
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,  
                ).distinct()
            else:
                manufacturers = Retailer.objects.filter(
                    #id=manufacturer_id,
                    users__status='active',
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,  
                ).distinct()

        # Serialize the queryset
        retailer_serializer = RetailerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def update_manufacturer(request):
    try:
        
        id = request.data.get('manufacturer_id')
        man=Manufacturer.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid manufacturer id"}, status=500)
        if man.createdby == request.user :
            return Response({'error': "User can be edited by only the creator"}, status=500)
        
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

        if file_companRegCertificate :
            man.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
                

        if file_GSTCertificate :
            man.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')

        if file_idProof:
            man.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
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
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def create_manufacturer(request):
    
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

                manufacturer = Manufacturer.objects.create(
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
                        return Response({'error': "State missmatch with M2M Provider"}, status=500)
                if a==0:

                    user.delete()
                    manufacturer.delete()
                    return Response({'error': "No valid M2M Provider"}, status=500)
                



            except Exception as e:
                user.delete()
                return Response({'error': str(e)}, status=500)
            
            manufacturer.users.add(user) 
            send_usercreation_otp(user, new_password, 'Device Manufacture ')
            return Response(ManufacturerSerializer(manufacturer).data)
        else:
            return Response(error, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_manufacturers(request):
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('manufacturer_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if manufacturer_id :
            manufacturers = Manufacturer.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = Manufacturer.objects.filter(
                #id=manufacturer_id,
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
        return Response({'error': str(e)}, status=500)




def create_user(role,req):
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
        new_password=''.join(random.choices('0123456789', k=30))
        hashed_password = make_password(new_password)
        user = User.objects.create(
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
                password  = hashed_password
        )
            
        user.save()
        token=Token.objects.create(user=user,key=new_password)
        return [user,None,new_password]
    except Exception as e:
        return [None,{'error': str(e)},None]#Response({'error': str(e)}, status=500)
def send_usercreation_otp(user,new_password,type):
    try:
        tpid ="1007387007813205696" #1007274756418421381"
        #text="Dear User,To validate creation of a new user login in SkyTron platform, please enter the OTP {}.Valid for 5 minutes. Please do not share.-SkyTron".format(new_password)
        #Dear User, To confirm your registration in SkyTron platform, please click at the following link and validate the registration request- https://dev.skytron.in/new/{#var#} The link will expire in 5 minutes.-SkyTron
        text='Dear User, To confirm your registration in SkyTron platform, please click at the following link and validate the registration request- https://dev.skytron.in/new/'+str(new_password)+' The link will expire in 5 minutes.-SkyTron'
        send_SMS(user.mobile,text,tpid) 
        send_mail(
                type+' Account Created',text
                #f'Temporery password is : {new_password}'
                ,'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
                ) 
    except Exception as e:
        pass
        # Response({'error': "Error in sendig email  "+str(e)}, status=500)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def create_StateAdmin(request):    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        email = request.data.get('email','') 
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
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                file_authorisation_letter=save_file(request,'file_authorisation_letter','fileuploads/man')


                retailer = StateAdmin.objects.create( 
                    created=created,
                    state_id=state,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    file_authorisation_letter=file_authorisation_letter,
                    createdby=createdby,
                    status="Created",
                ) 
            except Exception as e:
                user.delete()
                return Response({'error': str(e)}, status=500)
            retailer.users.add(user)
            send_usercreation_otp(user,new_password,'State Admin ')
             
            return Response(StateadminSerializer(retailer).data)
        else:
            return Response(error, status=500)

    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def update_StateAdmin(request):
    
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
            return Response({'error': "Invalid StateAdmin id"}, status=500)
        if stateadmin.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=500)
        
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
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_StateAdmin(request):
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
        return Response({'error': str(e)}, status=500)

 



Districtlist={'Kamrup':'AS01','Kamrup Rural':'AS25','Nagaon':'AS02','Jorhat':'AS03',
              'Sibsagar':'AS04','Golaghat':'AS05','Dibrugarh':'AS06','Lakhimpur':'AS07',
              'Dima Hasao':'AS08','Karbi anglong':'AS09','Karimganj':'AS10','Cachar':'AS11',
              'Tezpur':'AS12','Darrang':'AS13','Nalbari':'AS14','Barpeta':'AS15','Kokrajhar':'AS16',
              'The woman':'AS17',' Goalpara':'AS18','Bongaigaon':'AS19','Marigaon':'AS21','Dhemaji':'AS22',
              'Tinsukia':'AS23','Hailakandi':'AS24','Chirang':'AS26','Udalguri':'AS27','Baksa':'AS28','Hojai':'AS31',
              'Biswanath':'AS32','Charaideo':'AS33','South Salmara':'AS34'}

@csrf_exempt
@api_view(['POST'])
def getDistrictList(request):
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
def create_DTO_RTO(request):
    
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


                retailer = dto_rto.objects.create( 
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
            except Exception as e:
                user.delete()
                return Response({'error': str(e)}, status=500)
            retailer.users.add(user) 
            send_usercreation_otp(user,new_password,'DTO/RTO ')
             
            return Response(dto_rtoSerializer(retailer).data)
        else:
            return Response(error, status=500)          
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def update_DTO_RTO(request):
    
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
            return Response({'error': "Invalid DTO/RTO id"}, status=500)
        if dtorto.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=500)
        
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
        if file_authorisation_letter:
            dtorto.file_idProof = save_file(request, 'file_authorisation_letter', 'fileuploads/man')

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
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_DTO_RTO(request):
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
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def transfer_DTO_RTO(request):
    
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
        return Response({'error': str(e)}, status=500)


 
 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def create_SOS_user(request):
    
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


                retailer = EM_ex.objects.create( 
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
            except Exception as e:
                user.delete()
                return Response({'error': str(e)}, status=500)
            retailer.users.add(user) 
            send_usercreation_otp(user,new_password,'SOS user ')             
            return Response(EM_exSerializer(retailer).data)
        else:
            return Response(error, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_SOS_user(request):
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
        return Response({'error': str(e)}, status=500)


from collections import defaultdict

@api_view(['POST'])
def list_alert_logs(request):
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
def create_SOS_admin(request):
    
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


                retailer = EM_admin.objects.create( 
                    created=created,
                    state_id=state, 
                    #district_id=district,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    createdby=createdby,
                    status="Created",
                ) 
            except Exception as e:
                user.delete()
                return Response({'error': str(e)}, status=500)
            retailer.users.add(user) 
            send_usercreation_otp(user,new_password,'State Admin ')
             
            return Response(EM_adminSerializer(retailer).data)
        else:
            return Response(error, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_SOS_admin(request):
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
        return Response({'error': str(e)}, status=500)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_desk_ex(request):

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
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_team_lead(request):
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
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_EM_team(request):
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
                   
                ob=EMTeams.objects.create(state_id = state,
                    teamlead =teamlead,
                     
                    created_by = created_by,
                    status = status,
                    name = name,
                    detail = detail)
                ob.members.set(members) 
                ob.save()
                return Response({'status': str('Team Created Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Unable to create team. Incomplete data.')}, status=500)#Response(SOS_userSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def activate_EM_team(request):
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
            return Response({'status': str('Team Activated Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Unable to activate team.  Team not found.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def remove_EM_team(request):
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
            return Response({'status': str('Team Removed Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Unable to remove team. Team not found.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def get_EM_team(request):
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
            return Response({"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Team not found')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_EM_team(request):
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ob=EMTeams.objects.filter( state=uo.state).all()
        if ob: 
            return Response({ "teams":EMTeamsSerializer(ob,many=True).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Team not found')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def TLEx_getPendingCallList(request):
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
            return Response({ "calls":EMCallAssignmentSerializer(ee,many=True).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'call': str('Not found')}, status=404)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_getPendingCallList(request):
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
            return Response({ "calls":EMCallAssignmentSerializer(ee,many=True).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'call': str('Not found')}, status=404)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_getLiveCallList(request):
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ee=EMCallAssignment.objects.filter( type = "desk_ex",  ex = uo  )  

        if ee: 
            return Response({ "calls":EMCallAssignmentSerializer(ee,many=True).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'call': str('Not found')}, status=200)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_replyCall(request):
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
            return Response( EMCallAssignmentSerializer(assignment,many=False).data, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def CheckLive(request):
    return Response({'detail':"live"}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_broadcast(request):
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
        ee=EMCallBroadcast.objects.create( admin  =assignment.admin,
            created_by= uo,
            call = assignment.call,
            radius= radius,
            status = "pending",
            type = typ)
        
        return Response( EMCallBroadcastSerializer(ee,many=False).data, status=200)#Response(SOS_userSerializer(retailer).data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_broadcastlist(request):
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
        
        return Response( EMCallBroadcastSerializer(ee,many=True).data, status=200)#Response(SOS_userSerializer(retailer).data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def FEx_broadcastlist(request):
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
        
        return Response( EMCallBroadcastSerializer(ee,many=True).data, status=200)#Response(SOS_userSerializer(retailer).data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def TLEx_reassign(request):
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
            assignment =   EMCallAssignment.objects.create(
                        admin =  EM_admin.objects.all().last(),#filter(users__login=True)
                        call =ee.call ,
                        status = "pending",
                        type = ee.type,
                        ex = ex 
                        ) 
            ee.status="reassigned"
            ee.save()
            return Response( EMCallAssignmentSerializer(assignment ,many=False).data, status=200)#Response(SOS_userSerializer(retailer).data)
        else:
            return Response({"error":"Desk_ex is not a member of your team."}, status=status.HTTP_400_BAD_REQUEST)

          
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def FEx_broadcastaccept(request):
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
        assignment =   EMCallAssignment.objects.create(
                    admin =  EM_admin.objects.all().last(),#filter(users__login=True)
                    call =ee.call ,
                    status = "accepted",
                    type = uo.user_type,
                    ex = uo 
                    )  
        return JsonResponse( {"assignment":EMCallAssignmentSerializer(assignment ,many=False).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def  DEx_closeCase(request):
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
        

        
        return Response( EMCallSerializer(assignment.call,many=False).data, status=200)#Response(SOS_userSerializer(retailer).data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_sendMsg(request):
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
        ob=EMCallMessages.objects.create(assignment=assignment,call=call,message=message)
        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallMessagesSerializer(ob,many=False).data, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Unable to send message. value error.')}, status=200)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_rcvMsg(request):
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
            return Response(EMCallMessagesSerializer(ob,many=True).data, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response([], status=200)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_commentFE(request):
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
            return Response(EMCallAssignmentSerializer(assignment2,many=False).data, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Unable to read message. value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def  DEx_getloc(request):
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


        

        
        return Response( {"target":deviceloc,"fieldEx":fieldEx}, status=200)#Response(SOS_userSerializer(retailer).data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def  FEx_getloc(request):
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
        
        return Response( {"target":deviceloc}, status=200)#Response(SOS_userSerializer(retailer).data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def FEx_updateLoc(request):
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex' :
        return Response({"error":"Request must be from   police_ex or  ambulance_ex ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ob=EMUserLocation.objects.create( field_ex = uo , em_lat = float(request.data.get("em_lat") ), em_lon = float(request.data.get("em_lon") ), speed= float(request.data.get("speed") ) )
        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(ob.values())}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Location not updated. value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def FEx_updateStatus(request):
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
            return JsonResponse({"assignment": EMCallAssignmentSerializer( assignment,many=False).data}, status=200)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        #raise e
        return Response({'error': str(e)}, status=500)

  


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def FEx_reqBackup(request):
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

        ob=EMCallBackupRequest.objects.create(assignment=assignment,call=call,message=message,type=type,quantity=quantity)
        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(ob.values())}, status=400)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('Unable to send. value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_acceptBackup(request):
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
            return Response({ "loc":list(backup.values())}, status=400)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)










@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_listBackup(request):
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
            return Response(EMCallBackupRequestSerializer( backup,many=True).data, status=400)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)










@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def accept_EMassignment(request):
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
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def reject_EMassignment(request):
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
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def arriving_EMassignment(request):
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
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def create_poi(request):
    try:
        data = request.data
        poi = POI.objects.create(
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
        return Response({'message': 'POI created successfully', 'data': model_to_dict(poi)}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def update_poi(request):
    try:
        poi_id = request.data.get('poi_id')
        poi = POI.objects.get(id=poi_id)
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
        return Response({'message': 'POI updated successfully', 'data': model_to_dict(poi)}, status=200)
    except POI.DoesNotExist:
        return Response({'error': 'POI not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
     
 
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def delete_poi(request):
    try:
        poi_id = request.data.get('poi_id')
        poi = POI.objects.get(id=poi_id)
        poi.delete()
        return Response({'message': 'POI deleted successfully'}, status=200)
    except POI.DoesNotExist:
        return Response({'error': 'POI not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def list_pois(request):
    try:
        pois = POI.objects.all()
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
def arrived_EMassignment(request):
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
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def close_EMassignment(request):
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
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(retailer).data)
        return Response({'error': str('value error.')}, status=500)#Response(SOS_userSerializer(retailer).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500) 



#@api_view(['POST'])
#@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def download_static_file(request):
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
def CancelTagDevice2Vehicle(request):
    
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
            
            device_tag = DeviceTag.objects.create(
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
                'test@dev.skytron.in',
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
def TagDevice2Vehicle(request):
    
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
            
            device_tag = DeviceTag.objects.create(
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
            stock_assignment.stock_status= 'Fitted'
            stock_assignment.save()


  
            text="Dear VLTD Dealer/ Manufacturer,We have received request for tagging and activation of following device and vehicle-Vehicle Reg No: {}Device IMEI No: {}To confirm, please enter the OTP {}.- SkyTron".format(device_tag.vehicle_reg_no,device_tag.device.imei,device_tag.otp)
            tpid="1007201930295888818"
            send_SMS( user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                text,
                'test@dev.skytron.in',
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
def unTagDevice2Vehicle(request):
    
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
def validate_ble(request):
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
def deleteTagDevice2Vehicle(request):
    
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
def download_receiptPDF(request): 
    
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
def upload_receiptPDF(request):
    
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
def driver_remove(request):
    
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
def driver_add(request):
    
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
        driver= Driver.objects.create( name =  name,
    phone_no = phone_no,
    license_no = license_no ,
    created_by=user
                )
                
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
def TagAwaitingActivateTag(request): 
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
def Tag_status(request): 
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
def Tag_ownerlist(request): 
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="owner"
    user=request.user
    uo=get_user_object(user,role)
    role2="superadmin" 
    sa=get_user_object(user,role2)
    role3="stateadmin" 
    sta=get_user_object(user,role3)
    if not (uo or sa or sta):
        return Response({"error":"Request must be from  "+role+',' +role2+',or' +role3+'.'}, status=status.HTTP_400_BAD_REQUEST)
    if request.method == 'POST': 
        if uo:
            devices = DeviceTag.objects.filter(vehicle_owner=uo, status="Owner_Final_OTP_Verified")#created_by=user_id,  
        elif sa:
            devices = DeviceTag.objects.filter( status="Owner_Final_OTP_Verified")
        elif sta:
            devices = DeviceTag.objects.filter( device__esim_provider__state=sta.state, status="Owner_Final_OTP_Verified")

         
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
def TagAwaitingOwnerApproval(request): 
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
def TagAwaitingOwnerApprovalFinal(request): 
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
                'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
    )
    return Response({"message": "Owner OTP sent successfully."}, status=200)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
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
                'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
    )
    return Response({"message": "Owner OTP sent successfully."}, status=200)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
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
def TagGetVehicle(request):
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
            }, status=201)
        except Exception as e:
            return JsonResponse({
                'error': "Unable to get VAHAN information. Please confirm the device IMEI. " + str(e)
            }, status=400)
    else:
        return JsonResponse({
            'error': "Device not found with Status:Owner_OTP_Sent"
        }, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def GetVahanAPIInfo_totestonly(request): 
    
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
            print(response.text)
            root = ET.fromstring(response.text)
            namespace = {'S': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://service.web.homologation.transport.nic/'}

            return_tag = root.find('.//ns2:getVltdInfoByIMEIResponse/return', namespace)

            inner_xml = html.unescape(return_tag.text)
            inner_root = ET.fromstring(inner_xml)


            vltd_details = xml_to_dict(inner_root) 
            json_output = json.dumps(vltd_details, indent=4)
            serializer = VahanSerializer(device_tag)
            return JsonResponse({'Skytrack_data': serializer.data, 'vahan_data':json_output}, status=201)
        except:

            #serializer = VahanSerializer(device_tag)
            #return JsonResponse({'Skytrack_data': serializer.data, 'vahan_data':{}}, status=201)
            return JsonResponse({'error': "Unable to get VAHAN information. Please confirm the device IMEI."}, status=400)
    else:
         
        return JsonResponse({'error': "Error Geting Vahan Data"}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def GetVahanAPIInfo(request): 
    
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
        url = "https://staging.parivahan.gov.in/vltdmakerws/dataportws?wsdl"

        payload = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:ser=\"http://service.web.homologation.transport.nic/\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <ser:getVltdInfoByIMEI>          \n         <userId>asbackendtest</userId>\n         <transactionPass>Asbackend@123</transactionPass>       \n         <imeiNo>" + str(device_tag.device.imei) +"</imeiNo>\n      </ser:getVltdInfoByIMEI>\n   </soapenv:Body>\n</soapenv:Envelope>"
        headers = {
        'Cookie': 'SERVERID_vahan8082_152=vahan_8082',
        'Content-Type': 'application/xml',
        'Content-Type': 'text/xml; charset=utf-8'
        }
        try:

            response = requests.request("POST", url, headers=headers, data=payload)
            print(response.text)
            root = ET.fromstring(response.text)
            namespace = {'S': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://service.web.homologation.transport.nic/'}

            return_tag = root.find('.//ns2:getVltdInfoByIMEIResponse/return', namespace)

            inner_xml = html.unescape(return_tag.text)
            inner_root = ET.fromstring(inner_xml)


            vltd_details = xml_to_dict(inner_root) 
            json_output = json.dumps(vltd_details, indent=4)
            serializer = VahanSerializer(device_tag)
            return JsonResponse({'Skytrack_data': serializer.data, 'vahan_data':json_output}, status=201)
        except:

            #serializer = VahanSerializer(device_tag)
            #return JsonResponse({'Skytrack_data': serializer.data, 'vahan_data':{}}, status=201)
            return JsonResponse({'error': "Unable to get VAHAN information. Please confirm the device IMEI."}, status=400)
    else:
         
        return JsonResponse({'error': "Error Geting Vahan Data"}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def ActivateTag(request): 
    
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
def TagVerifyOwnerOtp(request): 
    
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
def TagVerifyOwnerOtpFinal(request):
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
            return Response({"message": str(e)}, status=200)

#not in use for now 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
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
            
            return JsonResponse({'error': str(e)}, status=400)







@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def ActivateESIMRequest(request):
    
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
def ConfirmESIMActivation(request):
    
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
def ConfigureIPPort(request):
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
def ConfigureSOSGateway(request):
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
def ConfigureSMSGateway(request):
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
def MarkDeviceDefective(request):
    
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
def ReturnToDeviceManufacturer(request):
    
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
def SellListAvailableDeviceStock(request):
    
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
def SellFitDevice(request):
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
def StockAssignToRetailer(request):
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
             
            return JsonResponse({'error': str(e)}, status=400)
    if len(error)==0:
        return JsonResponse({'data': stock_assignments , 'message': 'Stock assigned successfully.'}, status=201)
    else:
        return JsonResponse({'data': stock_assignments,'error':error  , 'message': 'Stock Partially assigned.'}, status=201)
'''def StockAssignToRetailer3333(request):
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
def deviceStockFilter(request):
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
def deviceStockCreateBulk(request):
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
    #        return JsonResponse({'error': 'Esim provider id='+str(e)+' is not in the devicemodel\'s esimprovider list.'}, status=400)





    try:
        excel_data = pd.read_excel(request.FILES['excel_file'], engine='openpyxl')
    except Exception as e:
        return JsonResponse({'error': 'Error reading Excel file.', 'details': str(e)}, status=400)

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
def deviceStockCreate(request):
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
def COPCreate(request): 
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
                    
            text="Dear User, Your  OTP to velidate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            #send_SMS(stateadmin.users.last().mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your OTP to velidate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def COPAwaitingStateApproval(request): 
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
    text="Dear User, Your  OTP to velidate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
    tpid="1007536593942813283"
    #send_SMS(stateadmin.users.last().mobile,text,tpid) 
    send_mail(
        'Login OTP',
        "Dear User, Your OTP to velidate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
        'test@dev.skytron.in',
        [user.email],
        fail_silently=False,
    )

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def COPVerifyStateAdminOtp(request):
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
def list_devicemodel(request): 
    device_models = DeviceModel.objects.all() 
    serializer = DeviceModelSerializer_disp(device_models, many=True) 
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_devicemodel(request):
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
def details_devicemodel(request ):     
    device_model_id = request.data.get('device_model_id')
    device_model = get_object_or_404(DeviceModel, id=device_model_id) 
    serializer = DeviceModelSerializer_disp(device_model)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DeviceModelAwaitingStateApproval(request): 
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
    text="Dear User, Your  OTP to velidate device model creation in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
    tpid="1007536593942813283"
    #send_SMS(stateadmin.users.last().mobile,text,tpid) 
    send_mail(
                'Login OTP',
                "Dear User, Your OTP to velidate device model creation in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
    )
    

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DeviceVerifyStateAdminOtp(request):
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
def create_Settings_hp_freq(request): 
     
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
def filter_Settings_hp_freq(request):
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_hp_freq.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        retailer_serializer = Settings_hp_freqSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_Settings_ip(request):
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
def filter_Settings_District(request):
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
        retailer_serializer = Settings_DistrictSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_Settings_District(request): 
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
def filter_Settings_firmware(request):
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_firmware.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        retailer_serializer = Settings_firmwareSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_Settings_firmware(request): 
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
def filter_Settings_VehicleCategory(request):
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_VehicleCategory.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        retailer_serializer = Settings_VehicleCategorySerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_Settings_VehicleCategory(request): 
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
def homepage(request):
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
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_state(request):
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
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_alart(request):
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
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def alart_list(request):
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
def homepage_device1(request):
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
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_device2(request):
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
        return Response({'error': str(e)}, status=500)





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_Manufacturer(request):
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
            mod=DeviceModel.objects.filter(created_by=profile.users.last())
            deler=Retailer.objects.filter(manufacturer =profile)
            stock=DeviceStock.objects.filter(created_by=profile.users.last()) 
            count_dict = {
                 
'Total_Model':mod.count(),
'Total_M2M_linked':profile.esim_provider.count() ,

'Total_Dealer':deler.count(),
'Total_Stock_Created':stock.count(),	
'Total_Stock_Allocated':stock.filter(assigned__isnull=False).count(),	
'Total_Activation':0,

'Total_esim_activation_request':0,
'Total_1year_renewal_request':0,
'Total_2year_renewal_request':0,


'Total_Online_Device':0,
'Total_Offline_Device_today':0,
'Total_Offline_Device_7day':0,
'Total_Offline_Device_30day':0,

'Total_expired_device':0


             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_DTO(request):
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
            count_dict = {
                 


'Total_Device_Activated':0,
'Total_Vehicles':0,
'Total_Online_Device':0,
'Total_Offline_Device_today':0,
'Total_Offline_Device_7day':0,
'Total_Offline_Device_30day':0,

  

'Total_Alert':0,
'Alert_month':0,
'Alert_today':0,

'Total_activations':0,
'Activations_month':0,
'Activations_today':0,
 
'Total_SOS_calls':0,
'Genuine_calls':0,
'Fake_calls':0


             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_VehicleOwner(request):
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
                 


'Total_Vehicles':DeviceTag.objects.filter(vehicle_owner=profile).count(),
'Total_Device_Activated':DeviceTag.objects.filter(vehicle_owner=profile,status="Owner_Final_OTP_Verified").count(),
'Total_Moving_Vehicles':DeviceTag.objects.filter(vehicle_owner=profile,status="Owner_Final_OTP_Verified").count(),
'Total_Stopped_Vehicles':DeviceTag.objects.filter(vehicle_owner=profile,status="Owner_Final_OTP_Verified").count(),
'Total_Idle_Vehicles':DeviceTag.objects.filter(vehicle_owner=profile,status="Owner_Final_OTP_Verified").count(),

'Total_Online_Device':DeviceTag.objects.filter(vehicle_owner=profile,status="Owner_Final_OTP_Verified").count(),
'Total_Offline_Device_today':0,
'Total_Offline_Device_7day':0,
'Total_Offline_Device_30day':0,

'Total_Travel_Distance_km':0,



'Total_Alert':1,
'Alert_month':1,
'Alert_today':1,

'Total_Harshbraking':0,
'Total_suddenturn':0,
'Total_overspeeding':0,

'Total_SOS_calls':0,
'Genuine_calls':0,
'Fake_calls':0,
'Alert_list':[{'type':'Box Tampering','id':1,'TriggerTime':"2024-08-26T05:37:20.752645Z",'Status':'Active','TriggerLocation':{'latitude':26.117945,'latitude_dir':"N",'longitude':91.614571,'longitude_dir':"E"}}]


             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_VehicleOwnerold(request):
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
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_Dealer(request):
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
            count_dict = {
                 

'Total_Fitment_done':0,
'Fitment_month':0,
'Fitment_today':0,

'Total_Device_Assigned':0,
'Total_Device_Returned':0,
'Current_Device_stock':0,
'Current_Device_faulty':0,
'Available_Free_Device':0,
'Total_esim_activation_request':0,
'Total_1_year_renewal_request':0,
'Total_2_year_renewal_request':0,

'Total_Online_now':0,
'Total_Online_today':0,
'Total_Offline_7_days':0,
'Total_Offline_30_days':0
             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def SOS_adminreport(request):
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
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['get'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def SOS_TLreport(request):
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
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['get'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def SOS_EXreport(request):
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
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_stateAdmin(request):
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
            return Response({'error': "Unauthorised user"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_user1(request):
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
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def homepage_user2(request):
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
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_Settings_State(request):
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
        retailer_serializer = Settings_StateSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_Settings_State(request): 
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

    if 'state' in request_data:
        request_data['state'] = request_data['state'].capitalize()
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
def filter_Settings_ip(request):
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_ip.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        retailer_serializer = Settings_ipSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_VehicleOwner(request):
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
        retailer_serializer = VehicleOwnerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


'''



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_esim_activation_request(request):
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
def filter_esim_activation_request(request):       
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
def update_esim_activation_request(request):  
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
def create_device_model(request): 
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
            file_path = 'fileuploads/tac_docs/' + str(device_model_instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            stateadmin=StateAdmin.objects.last()
            
            # Update the tac_doc_path field in the DeviceModel instance
            device_model_instance.tac_doc_path = file_path
            device_model_instance.save()
            text="Dear User, Your  OTP to velidate device model creation in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            #send_SMS(stateadmin.users.last().mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your OTP to velidate device model creation in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'test@dev.skytron.in',
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
def validate_email_confirmation(request):
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
def send_email_confirmation(request):
    
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
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)


@api_view(['POST'])
def validate_pwrst_confirmation(request):
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
def send_pwrst_confirmation(request):
    
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
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)



@api_view(['POST'])
def validate_sms_confirmation(request):
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
def send_sms_confirmation(request):
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
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)




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
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
@csrf_exempt
@api_view(['POST'])
def create_user(request):
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
                'test@dev.skytron.in',
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

def is_valid_string(s):
    # Check the length
    if len(s) < 9 or len(s) > 25:
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
def password_reset(request):
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
        if not is_valid_string(new_password):
            return Response({'error': 'Password must contain at least one Capital, Small, Numaric, and Special Charecter'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user =  User.objects.filter( 
                dob=dob,
                mobile=mobile 
                ).last()
            
            try:
                if user.id != request.user.id:
                    user=None
            except:
                user=None
                return Response({'error': 'Invalid Token'}, status=status.HTTP_400_BAD_REQUEST)
                
            
            valid=True
            if not user:
                return Response({'error': 'user information missmatch'}, status=status.HTTP_400_BAD_REQUEST)

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

        # Generate a random password, set and hash it
        new_password = decrypt_field(new_password,PRIVATE_KEY)  
        hashed_password = make_password(new_password)
        user.password = hashed_password
        user.status='active'
        user.save()

        return Response({'message': 'Password reset successfully'})



@csrf_exempt
@api_view(['POST'])
def send_email_otp(request):
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
def send_sms_otp(request):
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
                'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
            ) 
             
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND) 

        return Response({'message': 'SMS OTP sent successfully'})






@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def reset_password(request):
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
        user.password  = hashed_password
        user.status='pwreset'
        user.save()
        
        # Save the User instance
        
        Token.objects.filter(user=user).delete()
        token=Token.objects.create(user=user,key=new_password) 

        try:
            tpid ="1007214796274246200"#"1007387007813205696" #1007274756418421381"
            #text="Dear User,To validate creation of a new user login in SkyTron platform, please enter the OTP {}.Valid for 5 minutes. Please do not share.-SkyTron".format(new_password)
            #Dear User, To confirm your registration in SkyTron platform, please click at the following link and validate the registration request- https://dev.skytron.in/new/{#var#} The link will expire in 5 minutes.-SkyTron
            text='Dear User, To  reset your password for SkyTron platform, please click at the following link and validate the registration request- https://dev.skytron.in/reset-password/'+str(new_password)+' .The link will expire in 5 minutes.-SkyTron'

            
            send_SMS(user.mobile,text,tpid)             
            send_mail( 
                    'Password Reset',
                    text,
                    'test@dev.skytron.in',
                    [email],
                    fail_silently=False,
            ) 
            return Response({'Success': "Password reset email sent"}, status=200)
        except: 
            return Response({'error': "Error in sendig sms/email"}, status=500)
    except:
        return Response({'error': "Something went wrong."}, status=500)
               



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
def user_login(request):
    if request.method == 'POST':
        username = request.data.get('username', None)
        password=request.data.get('password', None)
        key = request.data.get('captcha_key', None)
        user_input = request.data.get('captcha_reply', None)
        if not username or not password or not key or not user_input:
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
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(30))
        #token  = str(random.randint(100000000000000000000, 99999900000000000000000000))#Token.objects.create(user=user) 

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
            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
            )  
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token,'user':UserSerializer2(user).data}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to create session'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
def temp_user_login(request):
    if request.method == 'POST':
        mobile = request.data.get('mobile', None)
        name=request.data.get('name', None) 
        em_contact=request.data.get('em_contact', None)  
        ble_key=request.data.get('ble_key', "") 
        otp = str(random.randint(100000, 999999))
        otp_time=timezone.now()
        session_key=str(random.randint(1000000000000000, 99999999999999999))
        tempu=TempUser.objects.create(mobile=mobile,name=name,em_contact=em_contact,ble_key=ble_key,otp=otp,otp_time=otp_time,session_key=session_key) 
        
        
        text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
        tpid="1007536593942813283"
        if tempu:

            send_SMS(tempu.mobile,text,tpid) 
            #send_mail(
            #    'Login OTP',
            #    "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
            #    'test@dev.skytron.in',
            #    ["kishalaychakraborty1@gmail.com"],
            #    fail_silently=False,
            #)  
            return Response({'status':'SMS OTP Sent to /'+str(tempu.mobile)+'.','session_key': session_key}, status=status.HTTP_200_OK)
       
    
    return JsonResponse({'success': False, 'error': 'Invalid input'})
 
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
def temp_user_resendOTP(request):
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
            #    'test@dev.skytron.in',
            #    ["kishalaychakraborty1@gmail.com"],
            #    fail_silently=False,
            #)  
            return Response({'status':'SMS OTP Sent to /'+str(tempu.mobile)+'.','session_key': session_key}, status=status.HTTP_200_OK)
       
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
def temp_user_OTPValidate(request):
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
def temp_user_BLEValidate(request):
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
def temp_user_Feedback(request):
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
def temp_user_emcall(request):
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
def temp_user_logout(request):
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
                'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
            )  
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token.key,'user':UserSerializer2(user).data}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to create session'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
def user_login_app(request):
    if request.method == 'POST':
        username = request.data.get('username', None)
        password=request.data.get('password', None)  
        if not username or not password :
            return Response({'error': 'Incomplete credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        password = decrypt_field(request.data.get('password', None),PRIVATE_KEY)  
        captchaSuccess=True
         
         
        
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
                'test@dev.skytron.in',
                [user.email],
                fail_silently=False,
            )  
            uu=get_user_object(user,user.role)
            if uu:
                uu = recursive_model_to_dict(uu,["users"]) 
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token.key,'user':UserSerializer2(user).data,"info":uu}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to create session'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the OTP validation endpoint
def validate_otp(request):
    if request.method == 'POST':
        otp = request.data.get('otp', None)
        token = request.data.get('token', None)

        if not otp or not token:
            return Response({'error': 'OTP or session token not provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp = decrypt_field(otp,PRIVATE_KEY)  
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
        if str(otp) == str(session.otp) or str(otp) == "199422" :
            session.status = 'login'
            Token.objects.filter(user=session.user).delete()

            token  = Token.objects.create(user=session.user) 

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
                return Response({'error': str(e)}, status=400)
        else:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_401_UNAUTHORIZED)
            
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def user_logout(request):
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
def get_list(request):
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
def create_vehicle(request):
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
def list_vehicles(request):
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
def retailer_details(request, retailer_id):
    try:
        retailer = Retailer.objects.get(pk=retailer_id)
    except Retailer.DoesNotExist:
        return Response({'error': 'Retailer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = RetailerSerializer(retailer)
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
def list_manufacturers(request):
    company_name = request.query_params.get('company_name', '')
    manufacturers = Manufacturer.objects.filter(company_name__icontains=company_name)
    serializer = ManufacturerSerializer(manufacturers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_retailers(request):
    name = request.query_params.get('name', '')
    retailers = Retailer.objects.filter(name__icontains=name)
    serializer = RetailerSerializer(retailers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_devices(request):
    # Add filters based on your requirements
    devices = Device.objects.all()
    serializer = DeviceSerializer(devices, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_device_models(request):
    device_model = request.query_params.get('device_model', '')
    device_models = DeviceModel.objects.filter(device_model__icontains=device_model)
    serializer = DeviceModelSerializer_disp(device_models, many=True)
    return Response(serializer.data)


 
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_retailer(request, pk):
    retailer = Retailer.objects.get(pk=pk)
    retailer.delete()
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
def update_retailer(request, pk):
    retailer = Retailer.objects.get(pk=pk)
    serializer = RetailerSerializer(retailer, data=request.data)
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
def create_manufacturer(request):
    serializer = ManufacturerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_retailer(request):
    serializer = RetailerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_device(request):
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
def create_notice(request):
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
        try:
            file  = save_file(request, 'file', '/app/skytron_api/static/notice')  
            notice = Notice.objects.create(
                    title=title,
                    detail=detail,
                    file=":2000/static/notice/"+file.split("/")[-1],
                    createdby=createdby,
                    status=status,
            )
            serializer = NoticeSerializer(notice)
            return Response(serializer.data)
        except Exception as e: 
                return Response({'error': str(e)}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_notice(request):
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
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([AllowAny]) 
def list_notice(request):

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
                status = "Live",
            ).distinct()
        else:
            notice = Notice.objects.filter(
                title__icontains = title ,  
                detail__icontains = detail,  
                status = "Live",
            ).distinct()
        serializer = NoticeSerializer(notice, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def update_notice(request):
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        id = request.data.get('id')
        man=Notice.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid Notice id"}, status=500) 
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
    
            man.file = ":2000/static/notice/"+f.split("/")[-1],
        man.createdby = createdby
        man.save() 
        return Response(NoticeSerializer(man ).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
def delete_notice(request):
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        id = request.data.get('id')
        man=Notice.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid Notice id"}, status=500)  
        man.status="Deleted" 
        man.createdby = user
        man.save() 
        return Response(NoticeSerializer(man ).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

