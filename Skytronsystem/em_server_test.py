# gps_socket_server.py
import os
import socket
import django
#python3 manage.py tcp_server --traceback >logtcp.log &
#sudo python3 gps_socket_server.py > tcplog.log &
# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Skytronsystem.settings")
django.setup()

from skytron_api.models import User,EMGPSLocation,GPSemDataLog
from django.core.management import call_command
import socket
import threading
from django.db.models import Q
 
def processEM(str_data):
        try:
            GPSemDataLog.objects.create(raw_data=str_data)
        except Exception as e:
            print("Data processing error log:", e, flush=True)
        data_l = str_data.split('$')
        for dat in data_l:
            dat='$'+dat
            if len(dat)>4:
                try:
                    data_list = dat.split(',')
                    if len(data_list)==20:
                        data_list=data_list[2:]
                        location = EMGPSLocation.create_from_string(data_list)
                        location.save()
                        RegNo=data_list[14]
                except Exception as e :
                    print("error1 ",e)
                    raise e
inp="$,EPB,EMR,868960065504918,NM,29092024,142315,A,26.134428,N,91.803711,E,61.1,0.0,143.8,G,GEM1205-04-00,0000000000,49,*"
processEM(inp)
#$,EPB,EMR,868960065504918,NM,29092024,142315,A,26.134428,N,91.803711,E,61.1,0.0,143.8,G,GEM1205-04-00,0000000000,49,*

#$EPB,EMR,861850060252398,NM,30092024133003,A,28.456395,N,77.032699,E,229,0,G,00,ABC00000015,9655543732,4C,*