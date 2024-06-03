 


import glob
import numpy as np
import cv2
import matplotlib.pyplot as plt
import pickle 
import os  
from google.cloud import vision
import io
import sys 
import math
from threading import Thread

import face_recognition  
import re
import json
from django.http import HttpResponse
import time 
from asgiref.sync import sync_to_async
import asyncio
import urllib
import numpy as np
from datetime import datetime
from uuid import uuid4
from django.shortcuts import render



TOL=.37 

  
NMS_THRESHOLD=.71
MIN_CONFIDENCE=0.3

labelsPath = "/home/azureuser/ImageProject/yolo/coco.names"
LABELS = open(labelsPath).read().strip().split("\n")
weights_path = "/home/azureuser/ImageProject/yolo/yolov4-tiny.weights"
config_path = "/home/azureuser/ImageProject/yolo/yolov4-tiny.cfg"

model = cv2.dnn.readNetFromDarknet(config_path, weights_path) 
layer_name = model.getLayerNames()  
layer_name = [layer_name[i - 1] for i in model.getUnconnectedOutLayers()]


 

client = vision.ImageAnnotatorClient()

  
 

 
cascPath = "/home/azureuser/ImageProject/haarcascade_frontalface_default.xml"
haar_cascade_face = cv2.CascadeClassifier(cascPath)

 
 
     
def get_enc(img): 
    face = face_recognition.face_locations(img,number_of_times_to_upsample= 1  )
     
    encode = face_recognition.face_encodings(img,known_face_locations = face, num_jitters  = 3,  model = "large")
    fc= face #[f.tolist() for f in face]
    en=[f.tolist() for f in encode]
    return  [en ,fc]

def area_from_loc(loc):
    if len(loc):
        a=(loc[2]-loc[0])*(loc[1]-loc[3])
        return a
    else:
        return 0
    


 


def face_reg(media_url):   
    r =urllib.request.urlopen( media_url)  
    arr = np.asarray(bytearray(r.read()), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR) 
    d=get_enc(img)
    ma=0
    dd=0
    if len(d[0])>0:
        for x in range(0,len(d[0])):
            if area_from_loc(d[0][x])>ma:
                ma=area_from_loc(d[0][x])
                dd=d

        face_enc=json.dumps(d[0][0])
        face_loc=json.dumps(d[1][0])   
        print("Face Detected-ok")
        print(face_enc)
        print(face_loc)
        
    else:
        print("No face detected!")
    
    
 

def face_matc(testFace,database_Face):
   r=face_recognition.compare_faces(testFace,database_Face,tolerance=TOL) 
   if True in r:
        print("face found")