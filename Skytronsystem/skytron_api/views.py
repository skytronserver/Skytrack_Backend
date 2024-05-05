# skytron_api/views.py
from rest_framework.authtoken.models import Token 
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, login
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel
from .models import *
from .serializers import *
import random
from itertools import islice
from django.contrib.auth.hashers import make_password 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel
from .serializers import UserSerializer
import random
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel, Session,Confirmation
from .serializers import StateadminSerializer, UserSerializer, SessionSerializer
from django.contrib.auth.hashers import make_password, check_password
import sys

from django.db import transaction

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404


from .serializers import ConfirmationSerializer
from rest_framework.parsers import MultiPartParser
import time

from .models import DeviceStock
from .serializers import DeviceStockSerializer,DeviceStockSerializer2


import pandas as pd
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView 

from rest_framework import generics
from rest_framework import filters
#from .models import DeviceModel,User
from .serializers import DeviceModelSerializer

from django.core.files.storage import FileSystemStorage
from rest_framework import generics, status
from rest_framework.response import Response
#from .models import DeviceModel
from .serializers import DeviceModelSerializer, DeviceModelFileUploadSerializer
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
#from .models import DeviceModel,DeviceTag
from .serializers import DeviceModelSerializer
from .models import *

from io import BytesIO

from .models import StateAdmin,VehicleOwner,DeviceCOP,StockAssignment,eSimProvider
from .serializers import DeviceCOPSerializer,DeviceModelFilterSerializer

from .serializers import VehicleOwnerSerializer,eSimProviderSerializer, DeviceStockSerializer,DeviceStockFilterSerializer
from .serializers import StockAssignmentSerializer, DeviceTagSerializer
from django.utils import timezone
import ast
 
from django.views.static import serve
from django.conf import settings
from django.http import HttpResponse





from django.shortcuts import render
from .models import GPSData,GPSDataLog
from django.db.models import Subquery, OuterRef 
from django.http import JsonResponse 
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models import Max
from django.db.models import F
from django.forms.models import model_to_dict
from django.db.models import Subquery, OuterRef
from scipy.signal import butter, lfilter,lfilter
from .forms import GPSDataFilterForm
import numpy as np

from django.shortcuts import render
from django.views import View
# SkytronServer/gps_api/views.py 
from .models import GPSLocation
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404 
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import EmergencyCall, GPSLocation,Help
import json
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
import requests


from .models import Help

from django.contrib.auth import logout,login,authenticate


@csrf_exempt
def LoginAndroid(request):
    if request.method == 'POST':
        return HttpResponse("LoginDone")
        user=authenticate(request,username=request.POST.get('username'),password=request.POST.get('password'))
        print(user)
        if user is not None:
            print("LoginDone")
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
        print("login2",user,username,password)
        if user is not None:
            print("LoginDone")
            login(request,user)

            if "FieldEx" in username:
                print("Loginvalid")
                #return HttpResponse("This account is not authorized to use this app.")
                return redirect('/api/emergency-call-listener-field/') 
            else:
                return HttpResponse("This account is not authorized to use this app.")
        else:
            return HttpResponse("Credentials are Incorrect")
    else:
        return HttpResponse("error")

 
#@login_required
@csrf_exempt
def update_location(request):
    live_data={}
    if request.method == 'POST':
        loc_lat = request.POST.get('latitude')
        loc_lon = request.POST.get('longitude')
        field_ex = request.POST.get('uername')
 

        # Update the Help object with the provided FieldEx
        try:
            help_obj = Help.objects.get(field_ex=field_ex)
            help_obj.loc_lat = loc_lat
            help_obj.loc_lon = loc_lon
            print(help_obj)
            help_obj.save()

            existing_emergency_call = EmergencyCall.objects.filter( 
                Q(status='Broadcast')# Exclude entries with Status 'Complete'
            ).order_by('-start_time').last()

        
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
def get_latest_gps_location(request, emergency_call_id):
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
        print("no rout",e)
        route=json.dumps({"err":"err"}, indent = 4) 
    
    #print(route)
    #route.raise_for_status()  # Check for HTTP errors
     
    # Parse message as json
    #route = json.loads(route['Message'])

    context1 = {
        'status':emergency_call.status,
        'desk_executive_id':emergency_call.desk_executive_id,
        'field_executive_id':emergency_call.field_executive_id,
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
@csrf_exempt
def Broadcast_help(request):
    if request.method == 'POST':
        call_id = request.POST.get('call_id')
        ecall=EmergencyCall.objects.get(call_id=call_id)
        ecall.status="Broadcast"
        ecall.field_executive_id=""
        ecall.save()
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
#@login_required
@csrf_exempt
def SubmitStatus(request):
    if request.method == 'POST':
        call_id = request.POST.get('call_id') 
        print(request.POST.get('status'))
        print(request.POST.get('comment'))
        ecall=EmergencyCall.objects.get(call_id=call_id)
        ecall.status=request.POST.get('status')
        ecall.final_comment=request.POST.get('comment')
        if request.POST.get('status')=="Closed":
            ecall.field_executive_id=""
        #ecall.field_executive_id=""
        ecall.save()
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
#@login_required
def emergency_call_details_field(request, emergency_call_id):
    # Get the EmergencyCall object based on the provided emergency_call_id
    emergency_call = get_object_or_404(EmergencyCall, pk=emergency_call_id)

    # Get the latest GPSLocation for the same IMEI and vehicle number
    latest_gps_location = GPSLocation.objects.filter(
        device_imei=emergency_call.device_imei,
        vehicle_reg_no=emergency_call.vehicle_no
    ).order_by('-date', '-time').first()
    help_obj = Help.objects.filter(field_ex=request.user.username ).first()
     
    context = {
        'emergency_call': emergency_call,
        'latest_gps_location': latest_gps_location,
        'fieldex': help_obj,
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
def map2(request,emergency_call_id):
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

    return render(request, 'bhooban.html', context)
     

    #return render(request, 'bhooban.html', {'live_data': []})


#@login_required
@csrf_exempt
def emergency_call_listener_admin(request):
    #return JsonResponse({"ok":"ok"})
    if request.method == 'POST':
        # Handle the 'Accept' button press
        data = json.loads(request.body)
        call_id = data.get('call_id')
        desk_executive_id = 'DeskEx1'  # Set the desk_executive_id

        # Update the EmergencyCall entry with the desk_executive_id
        emergency_call = EmergencyCall.objects.get(call_id=call_id)
        emergency_call.desk_executive_id = desk_executive_id
        emergency_call.status = 'Accepted'
        emergency_call.save()

    # Fetch live data updates every 5 seconds
    live_data = get_live_call_init()

    return render(request, 'emergency_call_listener_admin.html', {'live_data': live_data})


#@login_required
@csrf_exempt
def emergency_call_listener(request):
    if request.method == 'POST':
        # Handle the 'Accept' button press
        data = json.loads(request.body)
        call_id = data.get('call_id')
        desk_executive_id = 'DeskEx1'  # Set the desk_executive_id

        # Update the EmergencyCall entry with the desk_executive_id
        emergency_call = EmergencyCall.objects.get(call_id=call_id)
        emergency_call.desk_executive_id = desk_executive_id
        emergency_call.status = 'Accepted'
        emergency_call.save()

    # Fetch live data updates every 5 seconds
    live_data = get_live_call_init()

    return render(request, 'emergency_call_listener.html', {'live_data': live_data})


def get_live_call_init():
    # Implement the logic to fetch live data updates (replace with your actual implementation)
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

#@login_required
def get_live_call(request):
    # Implement the logic to fetch live data updates (replace with your actual implementation)
    existing_emergency_call = EmergencyCall.objects.order_by('-start_time').all()
    live_data1=""
    for call in existing_emergency_call:
        live_data1 = live_data1+"<button onclick=\"loadCallDetails('"+str(call.call_id)+"')\">Call ID: "+str(call.call_id)+" ("+str(call.status)+"); Vehicle: "+str(call.vehicle_no)+";</button><br>"

        #'<a href="https://skytrack.tech:2000/api/emergency-call-details/'+str( call.call_id )+'"  target="_self">Call ID:'+ str( call.call_id )+"("+  str(call.status)+");  Vehicle:"+  str( call.vehicle_no)+"; </a><br>"
      
    #print(live_data1)
    existing_emergency_call = EmergencyCall.objects.filter( 
            Q(status='Pending')# Exclude entries with Status 'Complete'
        ).order_by('-start_time').last()
    if existing_emergency_call:
        live_data = {
            'vehicle_no': existing_emergency_call.vehicle_no,
            'device_imei': existing_emergency_call.device_imei,
            'call_id': existing_emergency_call.call_id, 
        }
    else :
        live_data = {}
    if live_data1!="":
        live_data["table_data"]=live_data1

    return JsonResponse(live_data)


def get_all_call(request):
    # Implement the logic to fetch live data updates (replace with your actual implementation)
    existing_emergency_call = EmergencyCall.objects.order_by('-start_time').all()
    live_data1=[]
    for call in existing_emergency_call:
        live_data1.append({"call_id":str(call.call_id), 'device_imei': call.device_imei,"status":str(call.status),"Vehicle": str(call.vehicle_no)})
        #= live_data1+"<button onclick=\"loadCallDetails('"+str(call.call_id)+"')\">Call ID: "+str(call.call_id)+" ("+str(call.status)+"); Vehicle: "+str(call.vehicle_no)+";</button><br>"

        #'<a href="https://skytrack.tech:2000/api/emergency-call-details/'+str( call.call_id )+'"  target="_self">Call ID:'+ str( call.call_id )+"("+  str(call.status)+");  Vehicle:"+  str( call.vehicle_no)+"; </a><br>"
      
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
def emergency_call_listener_field(request):
    if request.method == 'POST':
        # Handle the 'Accept' button press
        data = json.loads(request.body)
        call_id = data.get('call_id')  # Set the desk_executive_id

        # Update the EmergencyCall entry with the desk_executive_id
        emergency_call = EmergencyCall.objects.get(call_id=call_id)
        emergency_call.field_executive_id = request.user.username
        emergency_call.status = 'FieldAccepted'
        emergency_call.save()

    # Fetch live data updates every 5 seconds
    live_data = get_live_call_field_init()

    return render(request, 'emergency_call_listener_field.html', {'live_data': live_data})


def get_live_call_field_init():
    # Implement the logic to fetch live data updates (replace with your actual implementation)
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
def get_live_call_field(request ):
    # Implement the logic to fetch live data updates (replace with your actual implementation)
    live_data={}
    if 1:
        # Handle the 'Accept' button press  
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
    # Customize the behavior after logging out
    next_page = reverse_lazy('login')  # Replace with the URL where you want to redirect after logout

    def dispatch(self, request, *args, **kwargs):
        # You can add custom logic here before logging out
        # For example, logging the user out of other systems or services

        # Call the parent class method to perform the logout
        response = super().dispatch(request, *args, **kwargs)

        # You can add custom logic here after logging out
        # For example, setting a custom message or performing additional actions

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
            data = data.filter(vehicle_registration_number__icontains=vehicle_registration_number)

        if start_datetime and end_datetime:
            data = data.filter(entry_time__range=(start_datetime, end_datetime))
    data=data.order_by('-entry_time')[:200]
    return render(request, 'gps_data_table.html', {'data': data, 'form': form})

def gps_data_table1(request):
    data = GPSData.objects.all().order_by('-entry_time')[:200]
    print("data", flush=True)
    print(data, flush=True)
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




@csrf_exempt  # Disable CSRF protection for simplicity. Make sure to secure your API in production.
def gps_track_data_api(request):
    distinct_registration_numbers = GPSData.objects.values('vehicle_registration_number').distinct()
    data = []

    for x in distinct_registration_numbers:
        latest_entry = GPSData.objects.filter(vehicle_registration_number=x['vehicle_registration_number']).filter(gps_status=1).order_by('-entry_time').first()
        excluded_fields = []  # Add any fields you want to exclude
        if latest_entry:
            #data.append(latest_entry.values())
            data.append(model_to_dict(latest_entry, exclude=excluded_fields))

    data_list = list(data)
    return JsonResponse({'data': data_list})



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
#@csrf_exempt  # Disable CSRF protection for simplicity. Make sure to secure your API in production.
#@csrf_exempt
def gps_history_map(request): 
    t = time.time()
    print("Timer init",time.time() - t )   

    mapdata=[]
    data=[]     
    mapdata=[]
    data=[]
    try:
        vehicle_registration_number ="L89_003-0000"
        start_datetime = "2024-04-11"
        end_datetime = "2024-04-12" 
        
        
        try:
            vehicle_registration_number = request.GET.get('vehicle_registration_number', None)
            start_datetime = request.GET.get('start_datetime', None)
            end_datetime = request.GET.get('end_datetime', None)
        except:
            vehicle_registration_number ="L89_003-0000"
            start_datetime = "2024-04-11"
            end_datetime = "2024-04-12"

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
               
                print("Timer input",time.time() - t ) 
                data = GPSData.objects.all().filter(gps_status=1).filter(longitude__range =[80,100]).filter(latitude__range =[20,30]).filter(vehicle_registration_number__icontains=vehicle_registration_number)
                 
                print("Data select done")
                print("filter1 ",time.time() - t ) 
                if start_datetime and end_datetime:
                        data = data.filter(entry_time__range=(start_datetime, end_datetime))   
                         
                        print("Date fileter done")  
                        print("filter2 ",time.time() - t )                    
                        data=data.filter(gps_status=1).order_by('entry_time')#[:17280]  
                        print("sorting done")  
                        print("sort ",time.time() - t ) 
                        mapdata=apply_low_pass_filter(data, ['longitude', 'latitude'])#[3:]  
                        print("lpf done done")  
                        print("lpf ",time.time() - t ) 
                        print("total dataSize ",get_size(data))
                try:    #return JsonResponse({"eg":vehicle_registration_number})     
                    return render(request, 'map_history.html', {'data': data,'mapdata': mapdata,'mapdata_length': len(data)-1 })
                except:
                    return JsonResponse({"error": "No Record Found: "+vehicle_registration_number}, status=403) 
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
    print("Timer init",time.time() - t )   

    mapdata=[]
    data=[]     
    mapdata=[]
    data=[]
    try:
        vehicle_registration_number ="L89_003-0000"
        start_datetime = "2024-04-11"
        end_datetime = "2024-04-12" 
        
        
        try:
            vehicle_registration_number = request.GET.get('vehicle_registration_number', None)
            start_datetime = request.GET.get('start_datetime', None)
            end_datetime = request.GET.get('end_datetime', None)
        except:
            vehicle_registration_number ="L89_003-0000"
            start_datetime = "2024-04-11"
            end_datetime = "2024-04-12"

        #return JsonResponse({"eg":vehicle_registration_number})
        if vehicle_registration_number:
            pass
        else:
            vehicle_registration_number ="L89_003-0000"
            start_datetime = "2024-04-11"
            end_datetime = "2024-04-12"
        
        
        if vehicle_registration_number!="":
            if vehicle_registration_number:
                print("Timer input",time.time() - t ) 
                data = GPSData.objects.all().filter(gps_status=1).filter(longitude__range =[80,100]).filter(latitude__range =[20,30]).filter(vehicle_registration_number__icontains=vehicle_registration_number)
                 
                print("Data select done")
                print("filter1 ",time.time() - t ) 
                if start_datetime and end_datetime:
                        data = data.filter(entry_time__range=(start_datetime, end_datetime))   
                         
                        print("Date fileter done")  
                        print("filter2 ",time.time() - t )                    
                        data=data.filter(gps_status=1).order_by('entry_time')#[:17280]  
                        datalen=len(data)-1
                        print("sorting done")  
                        print("sort ",time.time() - t ) 
                        #mapdata=apply_low_pass_filter(data, ['longitude', 'latitude'])#[3:]  
                        print("lpf done done")  
                        print("lpf ",time.time() - t ) 
                        print("total dataSize ",get_size(data))
                        data=GPSData_modSerializer(data, many=True).data
                        #mapdata=GPSData_modSerializer(mapdata, many=True).data
                try:    #return JsonResponse({"eg":vehicle_registration_number})     
                    return JsonResponse( {'data': data,'mapdata': mapdata,'mapdata_length': datalen })
                except Exception as e:
                    return JsonResponse({"error": str(e) +"No Record Found 1: "+vehicle_registration_number}, status=403) 
            else:
                return JsonResponse({'error': "Invalid Search 22"}, status=403) 
        return JsonResponse({'error': "Invalid Search"}, status=403) 
        return Response({'error': "Invalid Search"}, status=403)
        return render(request, 'map_history.html', {'data': data,'mapdata': mapdata,'mapdata_length': len(data)-1 })
        return Response({'error': "Invalid Search"}, status=403)
    except Exception as e: 
        return JsonResponse({'error': e}) 
        return Response({'error': "ww"}, status=400)



def setRout(request):
    # Get the latest entry for each unique vehicle_registration_number
    #latest_data = GPSData.objects.filter(
    #    vehicle_registration_number=OuterRef('vehicle_registration_number')
    #).filter(gps_status=1).order_by('-entry_time').values('id')#[:1]


    # Retrieve the complete GPSData objects using the latest entry IDs
    #data = GPSData.objects.filter(id__in=Subquery(latest_data))
    if request.method == 'GET':
        device_id = 1 #request.GET.get('device_id')
        device = DeviceStock.objects.get(id=device_id)   
        rout = Rout.objects.filter(device=device ) 
        return render(request, 'map_rout.html',{"routs": rout } )
    
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


 
@csrf_exempt
def delRout(request):
    if request.method == 'POST':
        data =json.loads( request.body )
        try:
            id=data['id']  
            device =  DeviceStock.objects.get(id=data['device_id'])

            if id:
                route = Rout.objects.get(id=id)
                route.delete()
                rout = Rout.objects.filter(device=device ).all()
                return JsonResponse({"message": "Route deleted successfully!",'new':[],"data": routSerializer(rout, many=True).data }, status=201)
        
        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)



@csrf_exempt
def saveRout(request):
    if request.method == 'POST':
        print(request.body)
        data =json.loads( request.body )
        id =None
        try:
            id=data['id']
        except Exception as e:
            print(e)
        try:
            createdby =  User.objects.get(id=data['createdby_id'])
            device =  DeviceStock.objects.get(id=data['device_id'])

            if id:
                route = Rout.objects.get(id=id)
                route.rout = data['rout']
                route.createdby = User.objects.get(id=data['createdby_id']) 
                route.save()
                rout = Rout.objects.filter(device=device ).all()
                return JsonResponse({"message": "Route saved successfully!",'new':routSerializer(route).data,"data": routSerializer(rout, many=True).data }, status=201)
        
            else:
                route = Rout(
                    rout=data['rout'],
                    status='Active',  # Assuming status is 'Active' when created
                    device=device,
                    createdby=createdby
                )
                route.save()
                rout = Rout.objects.filter(device=device ).all()
                return JsonResponse({"message": "New Route saved successfully!",'new':routSerializer(route).data,"data": routSerializer(rout, many=True).data }, status=201)
        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


def getRout(request):
    if request.method == 'GET':
        device_id = 1 #request.GET.get('device_id')
        try:
            device = DeviceStock.objects.get(id=device_id)
            rout = Rout.objects.filter(device=device ) 
            return JsonResponse({"rout": rout }, status=200)
        except Rout.DoesNotExist:
            return JsonResponse({"error": "No active route found for this device"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
def getRoutlist(request):
    if request.method == 'GET':
        device_id = 1 #request.GET.get('device_id')
        try:
            device = DeviceStock.objects.get(id=device_id)
            rout = Rout.objects.filter(device=device, status='Active').latest('id')
            return JsonResponse({"rout": rout.rout}, status=200)
        except Rout.DoesNotExist:
            return JsonResponse({"error": "No active route found for this device"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

def gps_data_allmap(request):
    # Get the latest entry for each unique vehicle_registration_number
    latest_data = GPSData.objects.filter(
        vehicle_registration_number=OuterRef('vehicle_registration_number')
    ).filter(gps_status=1).order_by('-entry_time').values('id')[:1]

    # Retrieve the complete GPSData objects using the latest entry IDs
    data = GPSData.objects.filter(id__in=Subquery(latest_data))

    return render(request, 'map.html', {'data': data})
def gps_data_log_table(request):
    # Filter data based on the search query
    search_query = request.GET.get('search', '')
    if search_query:
        data = GPSDataLog.objects.filter(raw_data__contains=search_query).order_by('-timestamp')[:200]
    else:
        data = GPSDataLog.objects.all().order_by('-timestamp')[:200]
    
    return render(request, 'gps_data_log_table.html', {'data': data, 'search_query': search_query})
     






@api_view(['POST'])  
def sms_received(request):
    try:
        # Extract necessary parameters from the request data
        no= request.data.get('no')
        msg = request.data.get('msg', '')
        print('SMS Received; NO:'+no+"; MSG:"+msg)
        return Response({'status':"Success"})
    except Exception as e:
        return Response({'error': str(e)}, status=500)
@api_view(['get'])  
def sms_queue(request):
    try: 
        return Response({'no':"6661234",'msg':'data to send'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def get_live_vehicle_no(request):
    try:
        if request.method == 'POST':
            # Fetch distinct vehicle registration numbers
            vehicles = GPSData.objects.all().values('vehicle_registration_number').distinct()
            vehicle_list = [vehicle['vehicle_registration_number'] for vehicle in vehicles]
            return Response(vehicle_list)
        else:
            return Response({'error': "POST request only"}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
 
    



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_VehicleOwner(request):
    try:
        # Extract necessary parameters from the request data
        company_name = request.data.get('company_name')

        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date

        # File uploads
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='owner',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'Vehicle Owner Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()
        if not company_name:
            company_name=""

        # Create Manufacturer instance
        retailer = VehicleOwner.objects.create(
            company_name=company_name, 
            created=created,
            expirydate=expirydate, 
            idProofno=idProofno, 
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        ) 
        retailer.users.add(user) 
        return Response(VehicleOwnerSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_manufacturer(request, manufacturer_id):
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
def delete_dealer(request, dealer_id):
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
def delete_eSimProvider(request, esimProvider_id):
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
def delete_VehicleOwner(request, vo_id):
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
def filter_VehicleOwner(request):
    try:
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if dealer_id :
            manufacturers = VehicleOwner.objects.filter(
                id=dealer_id ,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = VehicleOwner.objects.filter(
                #id=manufacturer_id,
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
@transaction.atomic
def create_eSimProvider(request):
    try:
        # Extract necessary parameters from the request data
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date

        # File uploads
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='esimprovider',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'E Sim Provider Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        retailer = eSimProvider.objects.create(
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
            status="Created",
        )

        # Add the user to the manufacturer's users
        retailer.users.add(user)
 
        return Response(eSimProviderSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_eSimProvider(request):
    try:
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

     
        if dealer_id :
            manufacturers = eSimProvider.objects.filter(
                id=dealer_id ,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = eSimProvider.objects.filter(
                #id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        retailer_serializer = eSimProviderSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_dealer(request):
    try:
        # Extract necessary parameters from the request data
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date

        # File uploads
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='dealer',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'Dealer Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
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
            status="Created",
        )

        # Add the user to the manufacturer's users
        retailer.users.add(user)
 
        return Response(RetailerSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_dealer(request):
    try:
        # Get filter parameters from the request
        dealer_id = request.data.get('dealer_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
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
@transaction.atomic
def create_manufacturer(request):
    try:
        # Extract necessary parameters from the request data
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date

        # File uploads
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='devicemanufacture',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'Device Manufacturere Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
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
            createdby=createdby,
            status="Created",
        )

        # Add the user to the manufacturer's users
        manufacturer.users.add(user)
 
        return Response(ManufacturerSerializer(manufacturer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_StateAdmin(request):
    try:
        # Extract necessary parameters from the request data
         
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '')
        # File uploads
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='stateadmin',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'State Admin Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        retailer = StateAdmin.objects.create( 
            created=created,
            state_id=state,
            expirydate=expirydate, 
            idProofno=idProofno, 
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        ) 
        retailer.users.add(user) 
        return Response(StateadminSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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









@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_DTO_RTO(request):
    try:
        # Extract necessary parameters from the request data
         
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '')
        dto_rto1= request.data.get('dto_rto', '')
        district = request.data.get('district', '')
        # File uploads
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='dtorto',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                     dto_rto1+' Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        retailer = dto_rto.objects.create( 
            created=created,
            state_id=state,
            dto_rto=dto_rto1,
            district_id=district,
            expirydate=expirydate, 
            idProofno=idProofno, 
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        ) 
        retailer.users.add(user) 
        return Response(dto_rtoSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_DTO_RTO(request):
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
            manufacturers = dto_rto.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = dto_rto.objects.filter(
                #id=manufacturer_id,
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
@transaction.atomic
def create_SOS_user(request):
    try:
        # Extract necessary parameters from the request data
         
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '') 
        district = request.data.get('district', '')
        # File uploads
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='sosuser',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail( 'SOS user Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        retailer = SOS_ex.objects.create( 
            created=created,
            state_id=state, 
            district_id=district,
            expirydate=expirydate, 
            idProofno=idProofno, 
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        ) 
        retailer.users.add(user) 
        return Response(SOS_userSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
            manufacturers = SOS_ex.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = SOS_ex.objects.filter(
                #id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = SOS_userSerializer(manufacturers, many=True)

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
@transaction.atomic
def create_SOS_admin(request):
    try:
        # Extract necessary parameters from the request data
         
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '') 
        district = request.data.get('district', '')
        # File uploads
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='sosadmin',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                      ' SOS Admin Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        retailer = SOS_admin.objects.create( 
            created=created,
            state_id=state, 
            district_id=district,
            expirydate=expirydate, 
            idProofno=idProofno, 
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        ) 
        retailer.users.add(user) 
        return Response(SOS_adminSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
            manufacturers = SOS_admin.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = SOS_admin.objects.filter(
                #id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = SOS_adminSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)




  

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_SOS_team(request):
    try:  
        createdby = request.user  
        created = timezone.now()  
        status = 'active'
        state= request.data.get('state', '') 
        district = request.data.get('district', '')
         
         
         
        return Response({'error': str('')}, status=500)#Response(SOS_userSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_SOS_team(request):
    try:
        
        state = request.data.get('state', '')
        district = request.data.get('district', '')

        # Create a dictionary to hold the filter parameters
        filters = {}
        manufacturers = SOS_team.objects.filter(
                 
            ).distinct()

        # Serialize the queryset
        serializer = SOS_teamSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)









def download_static_file(request):
    file_path = f"skytron_api/static/StockUpload.xlsx"
    try:
        with open(file_path,'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="StockUpload.xlsx"'
            return response
    except FileNotFoundError:
        return HttpResponse("File not found.", status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def TagDevice2Vehicle(request):
    # Extract data from the request or adjust as needed
    device_id = int(request.data['device'])
    user_id = request.user.id  # Assuming the user is authenticated
    current_datetime = timezone.now()
    uploaded_file = request.FILES.get('rcFile')
    if uploaded_file:
        file_path = 'cop_files/' + str(device_id) + '_' + uploaded_file.name
        with open(file_path, 'wb') as file:
            for chunk in uploaded_file.chunks():
                file.write(chunk)
             
        device_tag = DeviceTag.objects.create(
        device_id=device_id,
        vehicle_owner_id=request.data['vehicle_owner'],
        vehicle_reg_no=request.data['vehicle_reg_no'],
        engine_no=request.data['engine_no'],
        chassis_no=request.data['chassis_no'],
        vehicle_make=request.data['vehicle_make'],
        vehicle_model=request.data['vehicle_model'],
        category=request.data['category'],
        rc_file=file_path,
        status='Dealer_OTP_Sent',
        tagged_by=user_id,
        tagged=current_datetime,
    )

    # Serialize the created data
    serializer = DeviceTagSerializer(device_tag)

    return JsonResponse({'data': serializer.data, 'message': 'Device taging successful.'}, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unTagDevice2Vehicle(request):
    # Extract data from the request or adjust as needed
    if request.method == 'POST':
        # Get tag_id from POST data
        tag_id = request.POST.get('tag_id')

        # Check if tag_id is provided
        if not tag_id:
            return JsonResponse({'error': 'tag_id is required'}, status=400)

        try:
            # Retrieve DeviceTag instance by tag_id
            device_tag = DeviceTag.objects.get(id=tag_id)
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'DeviceTag with the given tag_id does not exist'}, status=404)

        # Update the status to Device_Untagged
        device_tag.status = 'Device_Untagged'
        device_tag.save()

        return JsonResponse({'message': 'Device successfully untagged'})

    # Handle GET requests or other HTTP methods
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def TagAwaitingOwnerApproval(request):
    # Assuming you have user authentication in place
    #user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    device_models = DeviceTag.objects.filter(status='Dealer_OTP_Verified')#created_by=user_id, 
    # Serialize the data
    serializer = DeviceTagSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def TagSendOwnerOtp(request ): 
    device_model_id = request.data.get('device_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceTag, id=device_model_id,  status='Dealer_OTP_Verified')

    device_model.status = 'Owner_OTP_Sent'
    device_model.save()

    return Response({"message": "Owner OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def TagVerifyOwnerOtp(request):
    # Assuming you have user authentication in place
    user_id = request.user.id
    otp = request.data.get('otp')
    device_tag_id = request.data.get('device_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
        return HttpResponseBadRequest("Invalid OTP format")
    device_tag = DeviceTag.objects.filter(device=device_tag_id, status='Owner_OTP_Sent') 

    #device_tag = get_object_or_404(DeviceTag, device_id=device_tag_id,  status='Dealer_OTP_Sent')
    device_tag = device_tag.first()
    if otp == '123456':  # Replace with your actual OTP verification logic
        device_tag.status = 'Owner_OTP_Verified'
        device_tag.save()
        return Response({"message": "Owner OTP verified successfully."}, status=200)
    else:
        return HttpResponseBadRequest("Invalid OTP")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def TagVerifyDealerOtp(request  ):
    # Assuming you have user authentication in place
    try:
        user_id = request.user.id
        otp = request.data.get('otp')
        device_tag_id = request.data.get('device_id')
        if not otp or not otp.isdigit() or len(otp) != 6:
            return HttpResponseBadRequest("Invalid OTP format")
        device_tag = DeviceTag.objects.filter(device=device_tag_id, status='Dealer_OTP_Sent') 

        #device_tag = get_object_or_404(DeviceTag, device_id=device_tag_id,  status='Dealer_OTP_Sent')
        device_tag = device_tag.first()
        if otp == '123456':  # Replace with your actual OTP verification logic
            device_tag.status = 'Dealer_OTP_Verified'
            device_tag.save()
            return Response({"message": "Dealer OTP verified successfully."}, status=200)
        else:
            return HttpResponseBadRequest("Invalid OTP")
    except Exception as e:
            return HttpResponseBadRequest(str(e))







@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ActivateESIMRequest(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='Fitted')
    stock_assignment.stock_status = 'ESIM_Active_Req_Sent'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'ESIM Active Request Sent successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ConfirmESIMActivation(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='ESIM_Active_Req_Sent')
    stock_assignment.stock_status = 'ESIM_Active_Confirmed'
    stock_assignment.save()
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='ESIM_Active_Confirmed')
    
    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'ESIM Active Confirmed successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ConfigureIPPort(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='ESIM_Active_Confirmed')
    stock_assignment.stock_status = 'IP_PORT_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'IP Port Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ConfigureSOSGateway(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='IP_PORT_Configured')
    stock_assignment.stock_status = 'SOS_GATEWAY_NO_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'SOS Gateway Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ConfigureSMSGateway(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='SOS_GATEWAY_NO_Configured')
    stock_assignment.stock_status = 'SMS_GATEWAY_NO_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'SMS Gateway Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def MarkDeviceDefective(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='SMS_GATEWAY_NO_Configured')
    stock_assignment.stock_status = 'Device_Defective'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'Device Marked as Defective successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ReturnToDeviceManufacturer(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='Device_Defective')
    stock_assignment.stock_status = 'Returned_to_manufacturer'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'Device Returned to Manufacturer successfully.'}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def SellListAvailableDeviceStock(request):
    # Get DeviceStock instances with StockAssignment having stock_status "Available_for_fitting"
    device_stock = StockAssignment.objects.filter(stock_status='Available_for_fitting')
    # Serialize the data
    serializer =StockAssignmentSerializer(device_stock, many=True)
    return JsonResponse({'data': serializer.data}, status=200)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def SellFitDevice(request):
    device_id=int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='Available_for_fitting')
    stock_assignment.stock_status = 'Fitted'
    stock_assignment.save()
    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)
    return JsonResponse({'data': serializer.data, 'message': 'Device Fitted  successfully.'}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def StockAssignToRetailer(request):
    data = request.data.copy()
    assigned_by_id = request.user.id
    assigned_at = timezone.now()
    stock_status = "Available_for_fitting"
    dealer_id = int(data.get('dealer'))
    device_ids = ast.literal_eval(str(data.get('device')))

    stock_assignments = []
    for device_id in device_ids:
        try:
            assignment = StockAssignment.objects.create(
                device_id=int(device_id),
                dealer_id=dealer_id,
                assigned_by_id=assigned_by_id,
                assigned=assigned_at,
                shipping_remark=data.get('shipping_remark'),
                stock_status=stock_status
            )
            stock_assignments.append(StockAssignmentSerializer(assignment).data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'data': stock_assignments , 'message': 'Stock assigned successfully.'}, status=201)
def StockAssignToRetailer3333(request):
    # Deserialize the input data
    data = request.data.copy() 
    data['assigned_by'] = request.user.id
    data['assigned'] = timezone.now()
    data['stock_status']= "Available_for_fitting"
    data['dealer_id']= int(data['dealer']) 
    device_ids = ast.literal_eval(str(data['device']))
     

    # Create individual StockAssignment entries for each device
    stock_assignments = []
    for device_id in device_ids:
        data['device_id'] = int(device_id)
        print(data)
        serializer = StockAssignmentSerializer2(data=data)
        if serializer.is_valid():
            serializer.save()
            stock_assignments.append(serializer.data)
        else:
            return JsonResponse({'error': serializer.errors}, status=400)

    return JsonResponse({'data': stock_assignments, 'message': 'Stock assigned successfully.'}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deviceStockFilter(request):
    # Deserialize the input data
    serializer = DeviceStockFilterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Filter DeviceStock instances based on parameters
    device_stock = DeviceStock.objects.filter(**serializer.validated_data)
    for item in device_stock:
        item.is_tagged = DeviceTag.objects.filter(device=item).exists()
    # Serialize the data
    #is_tagged_filter = serializer.validated_data.get('is_tagged')
    is_tagged_filter = request.data.get('is_tagged')

    # Filter based on 'is_tagged' value if provided
    if is_tagged_filter is not None:
        is_tagged_filter= is_tagged_filter=='True'
        device_stock = [item for item in device_stock if item.is_tagged == is_tagged_filter]

    serializer = DeviceStockSerializer2(device_stock, many=True)

    return JsonResponse({'data': serializer.data}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deviceStockCreateBulk(request):
    if 'excel_file' not in request.FILES or 'model_id' not in request.data:
        return JsonResponse({'error': 'Please provide an Excel file and model_id.'}, status=400)

    model_id = request.data['model_id']

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
            'imsi1': row.get('imsi1', ''),
            'imsi2': row.get('imsi2', ''),
            'esim_validity': row.get('esim_validity', ''),
            'esim_provider': row.get('esim_provider', ''),
            'remarks': row.get('remarks', ''),
            'created_by': request.user.id,
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
def deviceStockCreate(request):
    # Deserialize the input data
    data = request.data.copy()
    data['created'] = timezone.now()  # Ensure you import timezone from django.utils
    data['created_by'] = request.user.id

    serializer = DeviceStockSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    # Save the DeviceStock instance
    serializer.save()

    return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def COPCreate(request):
    # Assuming you have user authentication in place
    manufacturer = request.user.id

    # Create data for the new DeviceCOP entry
    data = {
        'created_by': manufacturer,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
        'status': 'Manufacturer_OTP_Sent',
        'valid':True,
        'latest':True,
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
            file_path = 'cop_files/' + str(device_cop_instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            # Update the cop_file field in the DeviceCOP instance
            device_cop_instance.cop_file = file_path
            device_cop_instance.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def COPAwaitingStateApproval(request):
    # Assuming you have user authentication in place
    #user_id = request.user.id

    # Retrieve device models with status "Manufacturer_OTP_Verified"
    device_models = DeviceCOP.objects.filter(status='Manufacturer_OTP_Verified')#created_by=user_id, 
    
    # Serialize the data
    serializer = DeviceCOPSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def COPSendStateAdminOtp(request ): 
    device_model_id = request.data.get('device_model_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceCOP, id=device_model_id,  status='Manufacturer_OTP_Verified')

    device_model.status = 'StateAdminOTPSend'
    device_model.save()

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def COPVerifyStateAdminOtp(request):
    device_model_id = request.data.get('device_model_id')
    # Assuming you have user authentication in place
    user_id = request.user.id
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceCOP, id=device_model_id, created_by=user_id, status='StateAdminOTPSend')

    # Additional logic for OTP verification can be added here if needed

    device_model.status = 'StateAdminApproved'
    device_model.save()

    return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def COPManufacturerOtpVerify(request  ):
    # Assuming you have user authentication in place
    user_id = request.user.id

    # Validate OTP and update the status
    otp = request.data.get('otp')
    device_model_id = request.data.get('device_model_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
        return HttpResponseBadRequest("Invalid OTP format")

    device_model = get_object_or_404(DeviceCOP, id=device_model_id, created_by=user_id, status='Manufacturer_OTP_Sent')

    # Verify OTP and update status
    if otp == '123456':  # Replace with your actual OTP verification logic
        device_model.status = 'Manufacturer_OTP_Verified'
        device_model.save()
        return Response({"message": "Manufacturer OTP verified successfully."}, status=200)
    else:
        return HttpResponseBadRequest("Invalid OTP")





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_devicemodel(request): 
    device_models = DeviceModel.objects.all() 
    serializer = DeviceModelSerializer(device_models, many=True) 
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_devicemodel(request):
    # Deserialize the input parameters
    serializer = DeviceModelFilterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Filter DeviceModel instances based on parameters
    device_models = DeviceModel.objects.filter(**serializer.validated_data)

    # Serialize the data
    serializer = DeviceModelSerializer(device_models, many=True)

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def details_devicemodel(request ): 
    
    device_model_id = request.data.get('device_model_id')
    device_model = get_object_or_404(DeviceModel, id=device_model_id)
 
    serializer = DeviceModelSerializer(device_model)

    return Response(serializer.data)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def DeviceModelAwaitingStateApproval(request):
    # Assuming you have user authentication in place
    #user_id = request.user.id

    # Retrieve device models with status "Manufacturer_OTP_Verified"
    device_models = DeviceModel.objects.filter(status='Manufacturer_OTP_Verified')#created_by=user_id, 
    
    # Serialize the data
    serializer = DeviceModelSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DeviceSendStateAdminOtp(request ): 
    device_model_id = request.data.get('device_model_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceModel, id=device_model_id,  status='Manufacturer_OTP_Verified')

    device_model.status = 'StateAdminOTPSend'
    device_model.save()

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DeviceVerifyStateAdminOtp(request):
    
    device_model_id = request.data.get('device_model_id')
    # Assuming you have user authentication in place
    user_id = request.user.id

    # Validate current status and update the status
    device_model = get_object_or_404(DeviceModel, id=device_model_id, created_by=user_id, status='StateAdminOTPSend')

    # Additional logic for OTP verification can be added here if needed

    device_model.status = 'StateAdminApproved'
    device_model.save()

    return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DeviceCreateManufacturerOtpVerify(request  ):
    # Assuming you have user authentication in place
    user_id = request.user.id

    # Validate OTP and update the status
    otp = request.data.get('otp')
    device_model_id = request.data.get('device_model_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
        return HttpResponseBadRequest("Invalid OTP format")

    device_model = get_object_or_404(DeviceModel, id=device_model_id, created_by=user_id, status='Manufacturer_OTP_Sent')

    # Verify OTP and update status
    if otp == '123456':  # Replace with your actual OTP verification logic
        device_model.status = 'Manufacturer_OTP_Verified'
        device_model.save()
        return Response({"message": "Manufacturer OTP verified successfully."}, status=200)
    else:
        return HttpResponseBadRequest("Invalid OTP")



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_Settings_hp_freq(request):
    # Assuming you have user authentication in place
    user_id = request.user.id 

    # Create data for the new DeviceModel entry
    data = {
        'createdby': user_id,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
        #'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
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
def create_Settings_ip(request):
    # Assuming you have user authentication in place
    user_id = request.user.id 

    # Create data for the new DeviceModel entry
    data = {
        'createdby': user_id,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
        #'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
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
def filter_Settings_District(request):
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_District.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        retailer_serializer = Settings_DistrictSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_Settings_District(request):
    # Assuming you have user authentication in place
    user_id = request.user.id 

    # Create data for the new DeviceModel entry
    data = {
        'createdby': user_id,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
        #'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_DistrictSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
    

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




















@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
def create_Settings_firmware(request):
    # Assuming you have user authentication in place
    user_id = request.user.id 

    # Create data for the new DeviceModel entry
    data = {
        'createdby': user_id,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
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
            file_path = 'file_bin/' + str(instance.id) + '_' + uploaded_file.name
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
def create_Settings_VehicleCategory(request):
    # Assuming you have user authentication in place
    user_id = request.user.id 

    # Create data for the new DeviceModel entry
    data = {
        'createdby': user_id,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
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
            'SOS_ex': SOS_ex.objects.count(),
            'SOS_user': SOS_user.objects.count(),
            'SOS_admin': SOS_admin.objects.count(),
            
            'TotalVehicles':0,
            
            'SOS_team': SOS_team.objects.count(),
            
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
            
            'Active_States':0,
            'Inactive_States':0,
            'Total_States':0,

        }
        # Return the serialized data as JSON response
        return Response(count_dict)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def homepage_state(request):
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'total_state':0,
            'active_state': 0,
            'inactive_state':0, 

        }
        # Return the serialized data as JSON response
        return Response(count_dict)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def homepage_alart(request):
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'total_alart':0,
            'alart_month': 0,
            'alart_today':0, 

        }
        # Return the serialized data as JSON response
        return Response(count_dict)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
            'SOS_ex': SOS_ex.objects.count(),
            'SOS_user': SOS_user.objects.count(),
            'SOS_admin': SOS_admin.objects.count(),
             
        }
        # Return the serialized data as JSON response
        return Response(count_dict)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
            'SOS_ex': SOS_ex.objects.count(),
            'SOS_user': SOS_user.objects.count(),
            'SOS_admin': SOS_admin.objects.count(),
             
        }
        # Return the serialized data as JSON response
        return Response(count_dict)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_Settings_State(request):
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_State.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        retailer_serializer = Settings_StateSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_Settings_State(request):
    # Assuming you have user authentication in place
    user_id = request.user.id 

    # Create data for the new DeviceModel entry
    data = {
        'createdby': user_id,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
        #'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_StateSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
    

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_VehicleOwner(request):
    try:
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if dealer_id :
            manufacturers = VehicleOwner.objects.filter(
                id=dealer_id ,
                users__email__icontains=email,
                #company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = VehicleOwner.objects.filter(
                #id=manufacturer_id,
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



















@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_device_model(request):
    # Assuming you have user authentication in place
    user_id = request.user.id

    # Create data for the new DeviceModel entry
    data = {
        'created_by': user_id,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
        'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    print("requestdata",request_data) 
    serializer = DeviceModelSerializer(data=request_data)

    # Validate and save the data along with the file
    if serializer.is_valid():
        # Save the DeviceModel instance
        device_model_instance = serializer.save()
        # Handle the uploaded file
        uploaded_file = request.FILES.get('tac_doc_path')
        if uploaded_file:
            # Save the file to a specific location
            file_path = '' + str(device_model_instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            # Update the tac_doc_path field in the DeviceModel instance
            device_model_instance.tac_doc_path = file_path
            device_model_instance.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeviceModelUpdateView(generics.UpdateAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelFileUploadSerializer

    def perform_update(self, serializer):
        file = self.request.FILES.get('tac_doc_path', None)
        if file:
            fs = FileSystemStorage(location=settings.MEDIA_ROOT + '/tac_docs/')
            filename = fs.save(file.name, file)
            tac_doc_path = 'tac_docs/' + filename
            serializer.validated_data['tac_doc_path'] = tac_doc_path
        serializer.save()

class DeviceModelFilterView(generics.ListAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['model_name', 'test_agency', 'vendor_id', 'status']

class DeviceModelDetailView(generics.RetrieveAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer

class DeviceModelDeleteView(generics.DestroyAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer





class FileUploadView(APIView):
    parser_classes = (MultiPartParser,)
    def post(self, request, *args, **kwargs): 
        email = request.data.get('email', None)
        if not email:
            return Response({'error': 'email not provided'}, status=400)
            
        try:
            user = UserModel.objects.get(email=email)
        
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        #user = get_object_or_404(UserModel, email=email)
        if user:
            print(email)
            if 'file' not in request.data:
                return Response({'error': 'No file part'}, status=status.HTTP_400_BAD_REQUEST)
            
            print(email)
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
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        data['password']  = hashed_password

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            send_mail(
                'Account Created',
                f'Temporery password is : {new_password}',
                'test@skytrack.tech',
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

@csrf_exempt
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    """
    Update user details.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
def password_reset(request):
    """
    Reset user password.
    """
    if request.method == 'POST':
        email = request.data.get('email', None)
        new_password = request.data.get('new_password', None)

        if not email:
            return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return Response({'error': 'Password not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate a random password, set and hash it
         
        hashed_password = make_password(new_password)
        user.password = hashed_password
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
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate and send OTP via email (Implementation depends on your email service)

        return Response({'message': 'Email OTP sent successfully'})

@csrf_exempt
@api_view(['POST'])
def send_sms_otp(request):
    """
    Send OTP to the user's mobile.
    """
    if request.method == 'POST':
        mobile = request.data.get('mobile', None)

        if not mobile:
            return Response({'error': 'Mobile not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(mobile=mobile)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate and send OTP via SMS (Implementation depends on your SMS service)

        return Response({'message': 'SMS OTP sent successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
def user_login(request):
    if request.method == 'POST':
        username = request.data.get('username', None)
        password = request.data.get('password', None)

        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)

        user = UserModel.objects.filter(email=username).first() or UserModel.objects.filter(mobile=username).first()
        #print(user,password, user.password)
        #print(check_password(password, user.password), )
        user.is_active=True
        user.save()
 
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check for an existing active session
        existing_session = Session.objects.filter(user=user.id, status='login').first()

        #if existing_session:
        #    return Response({'token': existing_session.token}, status=status.HTTP_200_OK)

        # Generate an OTP and a unique token
        otp = str(random.randint(100000, 999999))
        #token = get_random_string(length=32)
        token, created = Token.objects.get_or_create(user=user)

        # Create a new session entry
        session_data = {
            'user': user.id,
            'token': str(token.key),
            'otp': otp,
            'status': 'otpsent',
            'login_time': timezone.now(),
        }
        print(session_data)

        session_serializer = SessionSerializer(data=session_data)  # Replace with your actual SessionSerializer
        if session_serializer.is_valid():
            session_serializer.save()

            # Send OTP to the user's email
             
            send_mail(
                'Login OTP',
                f'Your login OTP is: {otp}',
                'test@skytrack.tech',
                [user.email],
                fail_silently=False,
            ) 
            
            return Response({'status':'Email OTP Sent to '+str(user.email),'token': token.key}, status=status.HTTP_200_OK)
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

        # Find the session based on the provided token
        session = Session.objects.filter(token=token).first()

        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'login':
            return Response({'status':'Login Successful','token': session.token}, status=status.HTTP_200_OK)

        # Validate the OTP
        print(otp,session.otp)
        if str(otp) == str(session.otp):
            # OTP is valid, change session status to 'login'
            session.status = 'login'
            session.save()

            return Response({'status':'Login Successful','token': session.token}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_401_UNAUTHORIZED)
            
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """
    User logout.
    """
    if request.method == 'POST':
        token = request.data.get('token', None)

        if  not token:
            return Response({'error': 'Session token not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session based on the provided token
        session = Session.objects.filter(token=token).first()

        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)

        session.status = 'logout'
        session.save()


        return Response({'status': 'Logout successful'})

@csrf_exempt
@api_view(['GET'])
def user_get_parent(request, user_id):
    """
    Get parent user details.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    parent_id = user.parent

    if not parent_id:
        return Response({'message': 'User has no parent'})

    try:
        parent_user = UserModel.objects.get(id=parent_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'Parent user not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(parent_user)
    return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_list(request):
    """
    Get a list of users.
    """
    users = UserModel.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data ,status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_details(request, user_id):
    """
    Get details of a specific user.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user)
    return Response(serializer.data)




from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Manufacturer, Retailer, Device, DeviceModel,Vehicle
from .serializers import ManufacturerSerializer, RetailerSerializer, DeviceSerializer, DeviceModelSerializer,VehicleSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_vehicle(request):
    serializer = VehicleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user, owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
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
def delete_vehicle(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    vehicle.delete()
    return Response({'message': 'Vehicle deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_vehicles(request):
    vehicles = Vehicle.objects.all()
    serializer = VehicleSerializer(vehicles, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vehicle_details(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VehicleSerializer(vehicle)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manufacturer_details(request, manufacturer_id):
    try:
        manufacturer = Manufacturer.objects.get(pk=manufacturer_id)
    except Manufacturer.DoesNotExist:
        return Response({'error': 'Manufacturer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ManufacturerSerializer(manufacturer)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def retailer_details(request, retailer_id):
    try:
        retailer = Retailer.objects.get(pk=retailer_id)
    except Retailer.DoesNotExist:
        return Response({'error': 'Retailer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = RetailerSerializer(retailer)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_details(request, device_id):
    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeviceSerializer(device)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_model_details(request, device_model_id):
    try:
        device_model = DeviceModel.objects.get(pk=device_model_id)
    except DeviceModel.DoesNotExist:
        return Response({'error': 'Device Model not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeviceModelSerializer(device_model)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_manufacturers(request):
    company_name = request.query_params.get('company_name', '')
    manufacturers = Manufacturer.objects.filter(company_name__icontains=company_name)
    serializer = ManufacturerSerializer(manufacturers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_retailers(request):
    name = request.query_params.get('name', '')
    retailers = Retailer.objects.filter(name__icontains=name)
    serializer = RetailerSerializer(retailers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_devices(request):
    # Add filters based on your requirements
    devices = Device.objects.all()
    serializer = DeviceSerializer(devices, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_device_models(request):
    device_model = request.query_params.get('device_model', '')
    device_models = DeviceModel.objects.filter(device_model__icontains=device_model)
    serializer = DeviceModelSerializer(device_models, many=True)
    return Response(serializer.data)


 
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_retailer(request, pk):
    retailer = Retailer.objects.get(pk=pk)
    retailer.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_device(request, pk):
    device = Device.objects.get(pk=pk)
    device.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_device_model(request, pk):
    device_model = DeviceModel.objects.get(pk=pk)
    device_model.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_manufacturer(request, pk):
    manufacturer = Manufacturer.objects.get(pk=pk)
    serializer = ManufacturerSerializer(manufacturer, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_retailer(request, pk):
    retailer = Retailer.objects.get(pk=pk)
    serializer = RetailerSerializer(retailer, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_device(request, pk):
    device = Device.objects.get(pk=pk)
    serializer = DeviceSerializer(device, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_device_model(request, pk):
    device_model = DeviceModel.objects.get(pk=pk)
    serializer = DeviceModelSerializer(device_model, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_manufacturer(request):
    serializer = ManufacturerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_retailer(request):
    serializer = RetailerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_device(request):
    serializer = DeviceSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 

'''