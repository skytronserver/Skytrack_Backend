# skytronapp/models.py
from django.db import models
from django.db.models import CheckConstraint, UniqueConstraint, Q
from django.db.models.functions import Coalesce
import hashlib
from django.utils import timezone  # Add this line
from django.core.validators import MinValueValidator, MaxValueValidator

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

 
from django.db.models import Count, Q



# SkytronServer/gps_api/models.py
from django.db import models

from datetime import datetime , timedelta


# SkytronServer/gps_api/models.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone



import random

import uuid
from django.utils import timezone
from datetime import timedelta


from django.utils import timezone 

from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.db import models, IntegrityError
from rest_framework.response import Response
from rest_framework import status
import os
import time
from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections

# Background thread pool for reverse geocoding.
# Geocoding blocks on an external HTTP call (~50-70 ms) — we run it after
# the GPS record is already saved so the tracking worker thread is not stalled.
_geocode_bg_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="geocode-bg")


def generate_uuid_hex():
    return uuid.uuid4().hex



class SafeCreateManager(models.Manager):
    def safe_create(self, **kwargs):
        """
        A utility function to safely create a model instance and handle IntegrityError.
        Returns the created object or a Response with a standardized error message.
        """
        try:
            # Check if all foreign key fields reference valid objects
            for field in self.model._meta.fields:
                if isinstance(field, models.ForeignKey):
                    related_field_name = field.name
                    related_model = field.related_model
                    related_id = kwargs.get(related_field_name + "_id")
                    if related_id and not related_model.objects.filter(id=related_id).exists():
                        return None, Response(
                            {'error': f"Invalid {related_field_name}_id: {related_id} does not exist."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            # Attempt to create the object
            return self.create(**kwargs), None
        except IntegrityError as e:
            # Extract the field name causing the IntegrityError
            error_message = str(e)
            for field in kwargs.keys():
                if field in error_message:
                    return None, Response({'error': f"{field} is invalid or already exists."}, status=status.HTTP_400_BAD_REQUEST)
            # Generic error for unknown fields
            return None, Response({'error': "A database integrity error occurred."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Handle other exceptions
            return None, Response({'error': f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class Captcha(models.Model):
    objects = SafeCreateManager()
    key = models.CharField(max_length=32, unique=True, default=generate_uuid_hex)
    answer = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
     

    def is_valid(self):
        return timezone.now() < self.created_at + timedelta(minutes=3)
    
"""
class Help(models.Model):
    TYPE_CHOICES = [
        ('Emergency', 'Emergency'),
        ('Assistance', 'Assistance'),
        # Add other types as needed
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    field_ex = models.ForeignKey('User', null=True,on_delete=models.CASCADE,related_name='help_field_executive_id')# models.CharField(max_length=50, unique=True)
    loc_lat = models.CharField(max_length=20, blank=True, null=True)
    loc_lon = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.field_ex.name

"""
class RequestLog(models.Model):
    
    objects = SafeCreateManager()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.CharField(max_length=70)  # Supports IPv6
    system_info = models.TextField()
    request_url = models.URLField()
    request_type = models.CharField(max_length=100)
    headers = models.TextField()
    incoming_data = models.TextField()
    response_type = models.CharField(max_length=100)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    error_code = models.IntegerField(null=True, blank=True)
    def __str__(self):
        return self.ip_address
    
    
    
class Media_File1(models.Model):
    device_tag = models.ForeignKey('DeviceTag', on_delete=models.CASCADE)
    camera_id = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    media_type = models.CharField(max_length=50, choices=[('audio', 'Audio'), ('video', 'Video'), ('image', 'Image')])
    media_link = models.URLField()
    duration_ms = models.IntegerField()
    alert_type = models.CharField(max_length=255)
    message = models.TextField()

    def __str__(self):
        return f"{self.media_type} from {self.camera_id} at {self.start_time}"
    
    
class RequestLogaaaaa(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=70)  # Supports IPv6
    system_info = models.TextField()
    request_url = models.URLField()
    request_type = models.CharField(max_length=100)
    headers = models.TextField()
    incoming_data = models.TextField()
    response_type = models.CharField(max_length=100)
    error_code = models.IntegerField(null=True, blank=True)
    def __str__(self):
        return self.ip_address


class RegNoLookupLog(models.Model):
    """
    Logs successful non-auth registration-number lookups to TagGetVehicle.
    Stores the resolved device tag, vehicle registration number, device IMEI,
    and the provided request header values for authorization and sessionid.

    This is meant for auditing/traceability of anonymous queries coming via
    external systems.
    """
    objects = SafeCreateManager()

    device_tag = models.ForeignKey('DeviceTag', on_delete=models.CASCADE, related_name='regno_lookup_logs')
    vehicle_reg_no = models.CharField(max_length=64)
    imei = models.CharField(max_length=32)
    authorization = models.TextField(blank=True, null=True)
    sessionid = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['vehicle_reg_no']),
            models.Index(fields=['imei']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Reg No Lookup Log'
        verbose_name_plural = 'Reg No Lookup Logs'

    def __str__(self):
        return f"{self.vehicle_reg_no} -> {self.imei} @ {self.created_at}"

class pointofinterests(models.Model): 
    status_choices = [
            ('Active', 'Active'),
            ('NotActive', 'NotActive'),
            ('Deleted', 'Deleted'),  
            ('Deleted2', 'Deleted2'),  
        ]
    
    status2 = models.CharField(max_length=20, choices=status_choices)
    status = models.CharField(max_length=20, choices=status_choices)
    mark_type_choices = [
            ('Point', 'Point'),
            ('Road', 'Road'),
            ('Circle', 'Circle'), 
            ('Polygon', 'Polygon'), 
        ]
    mark_type = models.CharField(max_length=40, choices=mark_type_choices)
    use_type_choices = [
            ('StateBoundary', 'StateBoundary'),
            ( 'DistrictBoundary', 'DistrictBoundary'),
            ( 'CityBoundary',  'CityBoundary'), 
            ( 'VillageBoundary',  'VillageBoundary'), 
            ( 'PermitRoute',  'PermitRoute'), 
            ( 'Police',  'Police'), 
            ( 'School',  'School'), 
            ( 'Hospital',  'Hospital'), 
            ( 'PoliceStation',  'PoliceStation'), 
            ( 'BusStop',  'BusStop'),  
            ( 'NoParking',  'NoParking'),  
            ( 'Prohibited_Area',  'Prohibited_Area'),  
            ( 'RailwayStation',  'RailwayStation'), 
            ( 'Airport',  'Airport'), 
            ( 'FuelStation',  'FuelStation'), 
            ( 'TollGate',  'TollGate'), 
            ( 'Other',  'Other'),
            ( 'Personal',  'Personal'),
            
        ]
    use_type = models.CharField(max_length=40, choices=use_type_choices)
    location = models.TextField()
    lat = models.FloatField(blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)
    radius = models.FloatField(blank=True, null=True)
    name = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    pluscode = models.CharField(max_length=50, blank=True, null=True)
    area= models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    
    description = models.TextField()
    # New fields
    ALERT_TYPE_CHOICES = [
        ('in', 'In'),
        ('out', 'Out'),
        ('both', 'Both'),
        ('none', 'None'),
    ]
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPE_CHOICES, default='none')
    speed_limit = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,related_name='POI_created_by')
    updated_by = models.ForeignKey('User', on_delete=models.CASCADE,related_name='POI_updated_by')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name
    
     

    
def get_logged_in_users_with_min_assignments(): 
    eight_hours_ago = timezone.now() - timezone.timedelta(hours=8) 
    return 0


# Trip model for trip management
class Trip(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("ended", "Ended"),
        ("canceled", "Canceled"),
    ]

    created_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='trips_created', null=True, blank=True)
    mobile_no = models.CharField(max_length=25, null=True, blank=True, help_text="Mobile number for temp user")
    created_at = models.DateTimeField(auto_now_add=True)
    trip_name = models.CharField(max_length=255)
    trip_route = models.TextField(help_text="List of lat,long as text")
    tripvehical_tag = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)
    expected_time_of_travel = models.DurationField()
    distance_travel = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="created")

    def __str__(self):
        user_info = self.created_by if self.created_by else self.mobile_no
        return f"Trip {self.id} - {self.trip_name} ({self.status}) [{user_info}]"
"""
    #
    #role='sosadmin',
    logged_in_users =  User.objects.filter(login=True, last_activity__gte=timezone.now() - timezone.timedelta(seconds=30) ).all()
    user_assignments = (
        logged_in_users
        .annotate(assignment_count=Count(
            'emergencycall_assignment', 
            filter=Q(emergencycall_assignment__assign_time__gte=eight_hours_ago)
        ))
        .order_by('assignment_count')  # Order by assignment count in increasing order
    ).first()
    
    
    # Print the results (or process as needed)
    #for user in user_assignments:
    #    print(f"User: {user.username}, Assignments in last 8 hours: {user.assignment_count}")
    # return user_assignments
    """
   
 







"""


class EmergencyCall(models.Model):
    call_id = models.AutoField(primary_key=True)
    device_imei = models.CharField(max_length=15)
    vehicle_no = models.CharField(max_length=20)
    start_time = models.DateTimeField()
    status = models.CharField(max_length=20)
    desk_executive_id = models.ForeignKey('User', null=True,on_delete=models.CASCADE,related_name='desk_executive_id')
    field_executive_id = models.ForeignKey('User',null=True, on_delete=models.CASCADE,related_name='field_executive_id')
    final_comment = models.TextField()

    def __str__(self):
        return f"EmergencyCall {self.call_id}"
"""
"""

class EmergencyCall_assignment(models.Model):
    emergencyCall_id = models.ForeignKey(EmergencyCall, on_delete=models.CASCADE)    
    user = models.ForeignKey('User', on_delete=models.CASCADE) 
    assign_time = models.DateTimeField()
    accept_time = models.DateTimeField(blank=True, null=True)
    complete_time = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20)#Assigned,Acccepted, Rejected,Timeout,Closed
    def __str__(self):
        return f"EmergencyCall_assignment {self.id}"
    """






class CustomUserManager(BaseUserManager):
     
    objects = SafeCreateManager()
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)




class User(AbstractBaseUser, PermissionsMixin):
    objects = SafeCreateManager()
    name = models.CharField(max_length=255, verbose_name="Name",null=False,blank=False) 
    #companyName=models.CharField(max_length=255, default='',verbose_name="companyName") 
    #username = models.EmailField(unique=True, verbose_name="Username")
    email = models.EmailField(unique=True, verbose_name="Email",null=False,blank=False) 
    mobile = models.CharField(max_length=25, unique=True, verbose_name="Mobile",null=False,blank=False)
    role = models.CharField(max_length=20,null=False,blank=False, choices=[("superadmin", "Super Admin"), ("stateadmin", "State Admin"), ("devicemanufacture", "Device Manufacture"), ("dealer", "Dealer"), ("owner", "Owner"), ("esimprovider", "eSimProvider"), ("filment", "Filment"), ("sosadmin", "SOS Admin"), ("teamleader", "Team Leader"), ("sosexecutive", "SOS Executive"),("schooladmin", "School Admin"),("parentuser", "Parent User"),("helpdesk", "Help Desk")], verbose_name="Role")
    usertype = models.CharField(max_length=10, default='main', verbose_name="User Type")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    date_joined = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    Access = models.JSONField(default=list,blank=True, null=True, verbose_name="Access")  
    password = models.CharField(max_length=100,default='12345678')  # Assuming 32 characters for MD5 hash
    lat = models.FloatField(blank=True, null=True, verbose_name="User_lat") 
    lon = models.FloatField(blank=True, null=True, verbose_name="User_lon") 
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address")
    address_pin = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address Pin")
    address_State = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address State")
    dob = models.CharField(max_length=255,  verbose_name="Date of Birth",null=False,blank=False)
    status = models.CharField(max_length=10, choices=[("active", "Active"), ("deactive", "Deactive")], verbose_name="Status")
    last_login =  models.DateTimeField(blank=True, null=True)
    last_activity =  models.DateTimeField(blank=True, null=True)
    login=models.BooleanField(default=False)
    nf_popup = models.BooleanField(default=True, verbose_name="Notification Popup")
    nf_sms = models.BooleanField(default=True, verbose_name="Notification SMS")
    nf_email = models.BooleanField(default=True, verbose_name="Notification Email")
    # Notification frequency per day (integer): how many times notifications can be sent daily
    # 0 means disabled/suppressed by frequency (still governed by nf_* flags)
    nf_frequency = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        verbose_name="Notification Frequency Per Day",
        help_text="Number of times per day notifications can be sent (0-1440)",
    )
    id_card_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="ID Card Name")
    id_card = models.CharField(max_length=500, blank=True, null=True, verbose_name="ID Card File Path")
    authorisation_letter = models.CharField(max_length=500, blank=True, null=True, verbose_name="Authorisation Letter File Path")
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name' ]

    objects = SafeCreateManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Hash the password using MD5 before saving
        #if self.password:
        #    self.password = make_password( self.password )
        super(User, self).save(*args, **kwargs)
    '''
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="Groups",
        blank=True,
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="User Permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
   
    '''





class TempUser(models.Model):
    objects = SafeCreateManager()
    name = models.CharField(max_length=255, verbose_name="Name")  
    #email = models.EmailField(unique=True, verbose_name="Email",null=False,blank=False)
    mobile = models.CharField(max_length=25,   verbose_name="Mobile") 
    ble_key = models.CharField(max_length=15, null=True,blank=True,unique=False, verbose_name="ble_key") 
    session_key = models.CharField(max_length=100, unique=True, verbose_name="session_key") 
    date_joined = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    otp = models.CharField(max_length=100,default='123456')  # Assuming 32 characters for MD5 hash
    otp_time= models.DateTimeField(default=timezone.now)
    em_contact=models.CharField(max_length=25,null=False,blank=False,  verbose_name="em_contact") 
    last_login =  models.DateTimeField(blank=True, null=True)
    last_activity =  models.DateTimeField(blank=True, null=True)
    online=models.BooleanField(default=False)
    feedback = models.TextField(blank=True, null=True, verbose_name="feedback") 
    em_lat = models.FloatField(blank=True, null=True, verbose_name="em_lat") 
    em_lon = models.FloatField(blank=True, null=True, verbose_name="em_lon") 
    em_msg=models.TextField(blank=True, null=True, verbose_name="em_msg") 
    em_time= models.DateTimeField(blank=True, null=True)
    
      
class Confirmation(models.Model):
    objects = SafeCreateManager()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=1500, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    type=    models.CharField(max_length=20, choices=[("email", "Email"), ("sms", "SMS"), ("pw_rst", "Password Resset")], verbose_name="Type")

    def is_valid(self):
        return timezone.now() < self.created_at + timedelta(hours=24)
        

class Manufacturer(models.Model):
    objects = SafeCreateManager()
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    company_address = models.CharField(max_length=255, blank=True, null=True)
    company_pin = models.CharField(max_length=20, blank=True, null=True)
    company_email = models.EmailField(max_length=255, blank=True, null=True)
    company_phoneno = models.CharField(max_length=20, blank=True, null=True)
    company_registration_no = models.CharField(max_length=255, blank=True, null=True)
    panno = models.CharField(max_length=50, blank=True, null=True)
    gstnnumber = models.CharField(max_length=20, blank=True, null=True)
    users = models.ManyToManyField('User', related_name='manufacturers_user')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_authLetter = models.CharField(max_length=255, blank=True, null=True)
    file_companRegCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_company_registration_certificate = models.CharField(max_length=255, blank=True, null=True)
    file_GSTCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    file_affidavitNda = models.CharField(max_length=255, blank=True, null=True)
    file_officialTechnicalOnboardingRequestLetter = models.CharField(max_length=255, blank=True, null=True)
    file_vehicleTypeApprovalTacAnnexureCopy = models.CharField(max_length=255, blank=True, null=True)
    file_ais140DeviceTacCopy = models.CharField(max_length=255, blank=True, null=True)
    file_factoryFitmentDeclaration = models.CharField(max_length=255, blank=True, null=True)
    cop_file = models.CharField(max_length=255, blank=True, null=True)
    tac = models.TextField(blank=True, null=True)
    tac_validity = models.DateField(blank=True, null=True)
    cop_no = models.CharField(max_length=255, blank=True, null=True)
    cop_validity = models.DateField(blank=True, null=True)
    manufacturer_type = models.CharField(max_length=255, blank=True, null=True)
    device_model_details = models.TextField(blank=True, null=True)
    assam_office_address = models.CharField(max_length=500, blank=True, null=True)
    assam_office_pin = models.CharField(max_length=20, blank=True, null=True)
    assam_office_phone = models.CharField(max_length=20, blank=True, null=True)
    assam_office_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    assam_office_lon = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    esim_provider = models.ManyToManyField("eSimProvider", related_name='eSimProvider_Manufacturer',  blank=True)
    
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
            ('Reject', 'Reject'),
            ('Allow to login', 'Allow to login'),
            ('Allow to add dealer', 'Allow to add dealer'),
            ('Accept', 'Accept'),
            ('TechnicalOnboardingApproved', 'Technical Onboarding Approved'),
            ('TechnicalOnboardingRejected', 'Technical Onboarding Rejected'),
        ] 
    
    status = models.CharField(max_length=30, choices=status_choices)

class eSimProvider(models.Model):
    objects = SafeCreateManager()
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    company_address = models.CharField(max_length=255, blank=True, null=True)
    company_pin = models.CharField(max_length=20, blank=True, null=True)
    company_email = models.EmailField(max_length=255, blank=True, null=True)
    company_phoneno = models.CharField(max_length=20, blank=True, null=True)
    company_registration_no = models.CharField(max_length=255, blank=True, null=True)
    panno = models.CharField(max_length=50, blank=True, null=True)
    gstnnumber = models.CharField(max_length=20, blank=True, null=True)
    m2m_reg_certificate_no = models.CharField(max_length=255, blank=True, null=True)
    telecomProviders = models.JSONField(default=list, blank=True)
    users = models.ManyToManyField('User', related_name='eSimProvider_User')
    
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_authLetter = models.CharField(max_length=255, blank=True, null=True)
    file_companRegCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_company_registration_certificate = models.CharField(max_length=255, blank=True, null=True)
    file_GSTCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    file_officialTechnicalOnboardingRequestLetter = models.CharField(max_length=255, blank=True, null=True)
    file_selfCertifiedDotM2mRegistrationCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_affidavitNda = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
            ('Reject', 'Reject'),
            ('Allow to login', 'Allow to login'),
            ('Allow to add dealer', 'Allow to add dealer'),
            ('Accept', 'Accept'),
        ]
    status = models.CharField(max_length=20, choices=status_choices)
         
class Dealer(models.Model):
    objects = SafeCreateManager()
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    gstnnumber = models.CharField(max_length=20, blank=True, null=True)
    users = models.ManyToManyField('User', related_name='Dealer_user')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_authLetter = models.CharField(max_length=255, blank=True, null=True)
    file_companRegCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_GSTCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    districts = models.ManyToManyField('Settings_District', related_name='dealer_districts', blank=True)
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
        ]
    status = models.CharField(max_length=20, choices=status_choices)
    
    class Meta:
        db_table = 'skytron_api_retailer'  # Keep the old table name for now
        # Explicitly set the many-to-many table name to match the expected name
        # This ensures the districts relationship uses the correct table name
    
class VehicleOwner(models.Model):
    objects = SafeCreateManager()
    company_name = models.CharField(max_length=255, blank=True, null=True,verbose_name="Company Name")
    users = models.ManyToManyField(User, related_name='manufacturers')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    file_GSTCertificate = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    status_choices = [
        ('Created', 'Created'),
        ('UserVerified', 'UserVerified'),
        ('UserExpired', 'UserExpired'), 
        ('Discontinued', 'Discontinued'),
    ]
    status = models.CharField(max_length=20, choices=status_choices)
    

class MediaFile(models.Model):
    device_tag = models.ForeignKey('Device', on_delete=models.CASCADE)
    camera_id = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    media_type = models.CharField(max_length=50, choices=[('audio', 'Audio'), ('video', 'Video'), ('image', 'Image')])
    media_link = models.URLField()
    duration_ms = models.IntegerField()
    alert_type = models.CharField(max_length=255)
    message = models.TextField()

    def __str__(self):
        return f"{self.media_type} from {self.camera_id} at {self.start_time}"
    

class StateAdmin(models.Model):
    objects = SafeCreateManager()
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='stateadmin_User')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    file_authorisation_letter = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            #('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
        ]
    status = models.CharField(max_length=20, choices=status_choices)
     



class sms_in(models.Model):     
    objects = SafeCreateManager()
    sms_text = models.CharField(max_length=500)
    no = models.CharField(max_length=20 )
    status = models.CharField(max_length=20, choices=[('Received','Received'),("Processed","Processed"),("Error","Error")])
    created = models.DateField(auto_now_add=True)
    
class sms_out(models.Model):   
    objects = SafeCreateManager()  
    sms_text = models.CharField(max_length=500)
    no = models.CharField(max_length=20 )
    status = models.CharField(max_length=20, choices=[('Queue','Queue'),("Sent","Sent"),("Error","Error")])
    created = models.DateField(auto_now_add=True)
    
    
class dto_rto(models.Model):
    objects = SafeCreateManager()
    dto_rto=   models.CharField(max_length=20, choices=[('DTO','DTO'),("RTO","RTO")])
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    district =models.CharField(max_length=255, blank=True, null=True)#models.ForeignKey('Settings_District', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='dto_rto_User')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    file_authorisation_letter = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
        ]
    status = models.CharField(max_length=20, choices=status_choices)
          
class EM_ex(models.Model): 
    objects = SafeCreateManager()
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    district =models.CharField(max_length=255, blank=True, null=True)#models.ForeignKey('Settings_District', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='SOS_ex_user')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    user_type=models.CharField(max_length=20, choices=[
            ('teamlead', 'teamlead'),
            ('desk_ex', 'desk_ex'),
            ('police_ex', 'police_ex'),
            ('ambulance_ex', 'ambulance_ex'),  
            ('PCR', 'PCR'),  #police control room
            ('ACR', 'ACR'),  #ambulance control room 
        ])
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
        ]
    status = models.CharField(max_length=20, choices=status_choices)

"""
class SOS_user(models.Model): 
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    district =models.CharField(max_length=255, blank=True, null=True)#models.ForeignKey('Settings_District', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='SOS_user')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(auto_now_add=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
        ]
    status = models.CharField(max_length=20, choices=status_choices)
"""

class EM_admin(models.Model): 
    objects = SafeCreateManager()
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    
    #district = models.ForeignKey('Settings_District', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='EM_admin')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
        ]
    status = models.CharField(max_length=20, choices=status_choices)

 


class Settings_State(models.Model): 
    objects = SafeCreateManager()
    state=models.CharField(max_length=50,unique=True)
    status = models.CharField(max_length=20, choices=[('active','active'),('discontinued','discontinued')])


class Settings_VehicleCategory(models.Model): 
    objects = SafeCreateManager()
    category=models.CharField(max_length=50,unique=True)
    maxSpeed=models.CharField(max_length=5)
    warnSpeed=models.CharField(max_length=5)
    working_hour_start_time=models.TimeField(null=True, blank=True)
    working_hour_end_time=models.TimeField(null=True, blank=True)
     

class Settings_VehicleCategoryCode(models.Model):
    objects = SafeCreateManager()
    category_code = models.CharField(max_length=50, unique=True)
    details = models.TextField(blank=True, null=True)
    speed_limit = models.CharField(max_length=5, null=True, blank=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='vcc_created')
    updated_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='vcc_updated')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.category_code


class Settings_PermitMaster(models.Model):
    objects = SafeCreateManager()
    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='permit_master_created')
    updated_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='permit_master_updated')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Settings_District(models.Model):
    objects = SafeCreateManager()
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    district =models.CharField(max_length=50,unique=True)  
    district_code =models.CharField(max_length=8,unique=True)    
    status = models.CharField(max_length=20, choices=[('active','active'),('discontinued','discontinued')])

"""
class SOS_team(models.Model):  
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    district =models.ForeignKey('Settings_District', on_delete=models.CASCADE)
    admin =models.ForeignKey('EM_admin', on_delete=models.CASCADE)
    teamlead =models.ForeignKey('EM_ex', on_delete=models.CASCADE)
    desk_team = models.ManyToManyField('EM_ex', related_name='SOS_Executive_desk_team')
    field_team = models.ManyToManyField('EM_ex', related_name='SOS_Executive_field_team')   
    status = models.CharField(max_length=20, choices=[('active','active'),('discontinued','discontinued')])
    queue_length = models.CharField(max_length=20)
    created = models.DateField(auto_now_add=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE,related_name='userc')
    updated = models.DateField(auto_now_add=True)
    updatedby = models.ForeignKey('User', on_delete=models.CASCADE,related_name='useru')
   """
 


class Device(models.Model):
    objects = SafeCreateManager()
    deviceModel = models.ForeignKey('DeviceModel', on_delete=models.CASCADE)
    status_choices = [
        ('Created', 'Created'),
        ('FactoryTestOK', 'FactoryTestOK'),
        ('ShipedtoDealer', 'ShipedtoDealer'),
        ('Sold', 'Sold'),
        ('Installed', 'Installed'),
        ('Active', 'Active'),
        ('DeviceError', 'Device Error'),
        ('Discontinued', 'Discontinued'),
    ]
    status = models.CharField(max_length=20, choices=status_choices)
    softwareLatestVersion = models.CharField(max_length=20, blank=True, null=True)
    vehicle = models.IntegerField()
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)




class Route(models.Model): 
    objects = SafeCreateManager()
    status_choices = [
        ('Active', 'Active'),
        ('Deleted', 'Deleted'), 
    ]
    status = models.CharField(max_length=20, choices=status_choices)
    route = models.TextField() 
    routepoints = models.TextField() 
    device = models.ForeignKey('DeviceStock', on_delete=models.CASCADE)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)






class DeviceModel(models.Model):
    objects = SafeCreateManager()
    STATUS_CHOICES = [
        ('Manufacturer_OTP_Sent', 'Manufacturer OTP Sent'),
        ('Manufacturer_OTP_Verified', 'Manufacturer OTP Verified'),
        ('StateAdminOTPSend', 'State Admin OTP Sent'),
        ('StateAdminApproved', 'State Admin Approved'),
    ]

    model_name = models.CharField(max_length=255, db_index=True)
    test_agency = models.CharField(max_length=255, db_index=True)
    vendor_id = models.CharField(max_length=255, db_index=True)
    tac_no = models.CharField(max_length=255, db_index=True)
    tac_validity = models.DateField(db_index=True)
    eSimProviders = models.ManyToManyField(eSimProvider, related_name='eSimProvider_devicemodle',  blank=True)
    otp_time=models.DateTimeField()
    hardware_version = models.CharField(max_length=255, db_index=True)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE, db_index=True)
    created = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, db_index=True)
    tac_doc_path = models.FileField(upload_to='tac_docs/', null=True, blank=True)
    otp = models.CharField(max_length=6 )
    mqtt_pw = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        # Composite index for common filtering combinations
        indexes = [
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['model_name', 'vendor_id']),
            models.Index(fields=['tac_no', 'tac_validity']),
        ]


class DeviceModelTechnicalOnboardingRequest(models.Model):
    objects = SafeCreateManager()

    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('ongoing_evaluation', 'Ongoing Evaluation'),
        ('technically_compatible', 'Technically Compatible'),
        ('technically_not_compatible', 'Technically Not Compatible'),
        ('StateAdminApproved', 'State Admin Approved'),
        ('StateAdminRejected', 'State Admin Rejected'),
    ]

    manufacturer = models.ForeignKey('Manufacturer', on_delete=models.CASCADE, related_name='technical_onboarding_requests')
    device_model = models.ForeignKey('DeviceModel', on_delete=models.CASCADE, related_name='technical_onboarding_requests')
    request_datetime = models.DateTimeField(auto_now_add=True)

    user_manual_pdf = models.CharField(max_length=255)
    ot_command_list_pdf = models.CharField(max_length=255)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted', db_index=True)
    compatibility_report_pdf = models.CharField(max_length=255, blank=True, null=True)
    final_comment = models.TextField(blank=True, null=True)

    evaluation_datetime = models.DateTimeField(blank=True, null=True)
    decision_datetime = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['manufacturer', 'status']),
            models.Index(fields=['device_model', 'status']),
            models.Index(fields=['request_datetime']),
        ]


class DeviceModelTechnicalOnboardingDemoDevice(models.Model):
    objects = SafeCreateManager()

    onboarding_request = models.ForeignKey(
        'DeviceModelTechnicalOnboardingRequest',
        on_delete=models.CASCADE,
        related_name='demo_devices'
    )
    device_serial_no = models.CharField(max_length=100)
    imei = models.CharField(max_length=50)
    ccid1 = models.CharField(max_length=50)
    ccid2 = models.CharField(max_length=50)
    msisdn1 = models.CharField(max_length=30)
    msisdn2 = models.CharField(max_length=30)

    class Meta:
        indexes = [
            models.Index(fields=['onboarding_request']),
            models.Index(fields=['imei']),
            models.Index(fields=['device_serial_no']),
        ]


class Settings_firmware(models.Model):
    objects = SafeCreateManager()
    devicemodel = models.ForeignKey('DeviceModel', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    firmware_vertion = models.CharField(max_length=255, blank=True, null=True)
    file_bin = models.CharField(max_length=512, blank=True, null=True)  # relative path
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True)            # bytes
    file_hash_md5 = models.CharField(max_length=32, blank=True, null=True)
    file_hash_sha256 = models.CharField(max_length=64, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)


class DeviceFirmwareLog(models.Model):
    objects = SafeCreateManager()

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed',  'Failed'),
    ]

    device_tag       = models.ForeignKey('DeviceTag', on_delete=models.CASCADE, related_name='firmware_logs')
    firmware         = models.CharField(max_length=255, blank=True, null=True)
    firmware_version = models.CharField(max_length=255, blank=True, null=True)
    file_size        = models.BigIntegerField(blank=True, null=True)
    file_hash_md5    = models.CharField(max_length=32, blank=True, null=True)
    file_hash_sha256 = models.CharField(max_length=64, blank=True, null=True)
    updated_at       = models.DateTimeField(blank=True, null=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    updated_by       = models.CharField(max_length=255, blank=True, null=True)
    created          = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['device_tag', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.device_tag} | v{self.firmware_version} | {self.updated_at}"


class Settings_hp_freq(models.Model):
    objects = SafeCreateManager()
    devicemodel = models.ForeignKey('DeviceModel', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    freq = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
     
  
class Settings_ip3(models.Model): 
    objects = SafeCreateManager()
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE, null=True)
    devicemodel = models.ForeignKey('DeviceModel', on_delete=models.CASCADE, null=True)
    created = models.DateField(auto_now_add=True)
    ip_tracking = models.CharField(max_length=255, blank=True, null=True)
    ip_tracking2 = models.CharField(max_length=255, blank=True, null=True)
    ip_sos = models.CharField(max_length=255, blank=True, null=True)
    port_tracking = models.CharField(max_length=255, blank=True, null=True)
    port_tracking2 = models.CharField(max_length=255, blank=True, null=True)
    port_sos = models.CharField(max_length=255, blank=True, null=True)
    sms_tracking = models.CharField(max_length=255, blank=True, null=True)
    sms_tracking2 = models.CharField(max_length=255, blank=True, null=True)
    sms_sos = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
     

class Settings_ip(models.Model): 
    objects = SafeCreateManager()
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE, null=True)
    devicemodel = models.ForeignKey('DeviceModel', on_delete=models.CASCADE, null=True)
    created = models.DateField(auto_now_add=True)
    ip_tracking = models.CharField(max_length=255, blank=True, null=True)
    ip_tracking2 = models.CharField(max_length=255, blank=True, null=True)
    ip_sos = models.CharField(max_length=255, blank=True, null=True)
    port_tracking = models.CharField(max_length=255, blank=True, null=True)
    port_tracking2 = models.CharField(max_length=255, blank=True, null=True)
    port_sos = models.CharField(max_length=255, blank=True, null=True)
    sms_tracking = models.CharField(max_length=255, blank=True, null=True)
    sms_tracking2 = models.CharField(max_length=255, blank=True, null=True)
    sms_sos = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
     


class DeviceStock(models.Model):
    objects = SafeCreateManager()
    model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE)
    device_esn = models.CharField(max_length=55,unique=True)
    iccid = models.CharField(max_length=55,unique=True)
    imei = models.CharField(max_length=55,unique=True)
    iccid2 = models.CharField(max_length=55,unique=True, blank=True, null=True)
    telecom_provider1 = models.CharField(max_length=25)
    telecom_provider2 = models.CharField(max_length=25, blank=True, null=True)
    msisdn1 = models.CharField(max_length=255,unique=True)
    msisdn2 = models.CharField(max_length=255, unique=True,blank=True, null=True)
    imsi1 = models.CharField(max_length=255,blank=True, null=True)
    imsi2 = models.CharField(max_length=255, blank=True, null=True)
    esim_validity = models.DateTimeField(null=True, blank=True)
    esim_provider = models.ManyToManyField(eSimProvider, related_name='eSimProvider_devicestock')
    
    #esim_provider = models.CharField(max_length=255)
    remarks = models.TextField(blank=True, null=True)
    created = models.DateTimeField()
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,related_name="createby_USERdevicestock")

    STATUS_CHOICES = [
        ('NotAssigned', 'NotAssigned'),
        ('In_transit_to_dealer', 'In Transit to Dealer'),
        ('Available_for_fitting', 'Available for Fitting'),
        ('Fitted', 'Fitted'),
        ('ESIM_Active_Req_Sent', 'ESIM Active Request Sent'),
        ('ESIM_Active_Confirmed', 'ESIM Active Confirmed'),
        ('ESIM_Active_Rejected', 'ESIM_Active_Rejected'),
        
        ('IP_PORT_Configured', 'IP Port Configured'),
        ('SOS_GATEWAY_NO_Configured', 'SOS Gateway No Configured'),
        ('SMS_GATEWAY_NO_Configured', 'SMS Gateway No Configured'),
        ('Device_Defective', 'Device Defective'),
        ('Returned_to_manufacturer', 'Returned to Manufacturer'),
        ('Device_Untagged', 'Device Untagged'),
        
    ]
 
    dealer =  models.ForeignKey(Dealer, on_delete=models.CASCADE,null=True,blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True)   
    assigned = models.DateTimeField(null=True,blank=True)
    shipping_remark = models.TextField(null=True,blank=True)
    stock_status = models.CharField(max_length=55, choices=STATUS_CHOICES)
    esim_status = models.CharField(max_length=55, choices=STATUS_CHOICES)

    # KYC fields — updated directly by the eSimProvider
    KYC_STATUS_CHOICES = [
        ('active',   'Active'),
        ('inactive', 'Inactive'),
    ]
    kyc_status     = models.CharField(max_length=10, choices=KYC_STATUS_CHOICES, null=True, blank=True)
    last_kyc_date  = models.DateTimeField(null=True, blank=True)
    kyc_updated_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='kyc_updates_made')
    kyc_updated_at = models.DateTimeField(null=True, blank=True)
    kyc_remarks    = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.model} - ESN: {self.device_esn}"
    
class DeviceCOP(models.Model):
    objects = SafeCreateManager()
    STATUS_CHOICES = [
        ('Manufacturer_OTP_Sent', 'Manufacturer OTP Sent'),
        ('Manufacturer_OTP_Verified', 'Manufacturer OTP Verified'),
        ('StateAdminOTPSend', 'State Admin OTP Sent'),
        ('StateAdminApproved', 'State Admin Approved'),
    ]

    device_model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE)
    cop_no = models.CharField(max_length=255)
    cop_validity = models.DateField()
    cop_file = models.FileField(upload_to='cop_files/', null=True, blank=True)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE)  # Assuming this is the Manufacturer ID
    created = models.DateTimeField()
    valid = models.BooleanField(default=True)
    latest = models.BooleanField(default=True)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
      
    otp = models.CharField(max_length= 6,null=True,blank=True)
    otp_time = models.DateTimeField( null=True,blank=True)


    def __str__(self):
        return f"{self.device_model} - COP: {self.cop_no}"
"""
class StockAssignment(models.Model):
    STATUS_CHOICES = [
        ('In_transit_to_dealer', 'In Transit to Dealer'),
        ('Available_for_fitting', 'Available for Fitting'),
        ('Fitted', 'Fitted'),
        ('ESIM_Active_Req_Sent', 'ESIM Active Request Sent'),
        ('ESIM_Active_Confirmed', 'ESIM Active Confirmed'),
        ('IP_PORT_Configured', 'IP Port Configured'),
        ('SOS_GATEWAY_NO_Configured', 'SOS Gateway No Configured'),
        ('SMS_GATEWAY_NO_Configured', 'SMS Gateway No Configured'),
        ('Device_Defective', 'Device Defective'),
        ('Returned_to_manufacturer', 'Returned to Manufacturer'),
    ]

    device = models.ForeignKey(DeviceStock, on_delete=models.CASCADE)
    dealer =  models.ForeignKey(Dealer, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE)   
    assigned = models.DateTimeField()
    shipping_remark = models.TextField()
    stock_status = models.CharField(max_length=255, choices=STATUS_CHOICES)
"""


class Driver(models.Model): 
    objects = SafeCreateManager()

    created = models.DateTimeField(auto_now_add=True,)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,related_name="createby_USERdriver")
   
    name = models.CharField(max_length= 55 )
    phone_no = models.CharField(max_length=55)
    license_no = models.CharField(max_length=55)
    photo = models.CharField(max_length= 555,null=True)

    def __str__(self):
        return self.name
    
class DeviceTag(models.Model):
    objects = SafeCreateManager()
    STATUS_CHOICES = [
        ('Dealer_OTP_Sent', 'Dealer OTP Sent'),
        ('Dealer_OTP_Verified', 'Dealer_OTP_Verified'),
        ('TempActive', 'TempActive'),
        ('Owner_OTP_Sent', 'Owner OTP Sent'),
        ('Owner_OTP_Verified', 'Owner OTP Verified'),
        ('RegNo_Configuration_SentToDevice', 'Reg No Configuration Sent to Device'),
        ('RegNo_Configuration_Confirmed', 'Reg No Configuration Confirmed'),
        ('Live_Location_Confirmed', 'Live Location Confirmed'),
        ('SOS_Confirmed', 'SOS Confirmed'),
        ('Device_Active', 'Device Active'),
        ('Device_Not_Active', 'Device Not Active'),
        ('Device_Untagged', 'Device Untagged'),
        ('Device_Untagged', 'Device Untagged'),
        ('Owner_Final_OTP_Verified', 'Owner Final OTP Verified'),
        ('TagDeleted', 'TagDeleted'),
        ('untaged_after_failed_taging', 'Untagged After Failed Tagging'),
    ]

    device = models.ForeignKey(DeviceStock, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle_owner = models.ForeignKey(VehicleOwner, on_delete=models.CASCADE)
   
    vehicle_reg_no = models.CharField(max_length= 55,unique=True)
    engine_no = models.CharField(max_length=55,unique=True)
    chassis_no = models.CharField(max_length= 55,unique=True)
    vehicle_make = models.CharField(max_length= 55)
    vehicle_model = models.CharField(max_length= 55)
    device_sell_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sale_type = models.CharField(
        max_length=20,
        choices=[('withinstate', 'Within State'), ('interstate', 'Inter State')],
        default='withinstate'
    )
    category = models.ForeignKey(Settings_VehicleCategory, on_delete=models.CASCADE)
    category_code = models.ForeignKey('Settings_VehicleCategoryCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='device_tags')
    rc_file = models.CharField(max_length=255)
    receipt_file_or = models.CharField(max_length=255)
    receipt_file_ul = models.CharField(max_length=255)
    district = models.ForeignKey(Settings_District, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    tagged_by = models.ForeignKey(User, on_delete=models.CASCADE)
    tagged = models.DateTimeField()    
    otp = models.CharField(max_length= 6,null=True,blank=True)
    otp_time = models.DateTimeField( null=True,blank=True)
    drivers= models.ManyToManyField(Driver, related_name='driver_vehicles', blank=True)
    with_trailer = models.BooleanField(default=False)
    trailer_id = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return self.vehicle_reg_no







class Holiday(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    HOLIDAY_TYPE_CHOICES = [
        ('Public', 'Public'),
        ('Private', 'Private'),
    ]

    holiday_name = models.CharField(max_length=255, verbose_name="Holiday Name")
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active', verbose_name="Status")
    holiday_type = models.CharField(max_length=20, choices=HOLIDAY_TYPE_CHOICES, verbose_name="Holiday Type")
    vehicles = models.ManyToManyField(DeviceTag, related_name="holiday_vehicles", verbose_name="Vehicle List")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="holiday_created_by", verbose_name="Created By")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    def __str__(self):
        return self.holiday_name
    
    
    
##unused



       
class EMGPSLocation(models.Model): #imergency tracking data
    objects = SafeCreateManager()
    message_type = models.CharField(max_length=3)  # EMR or SEM
    device_imei = models.CharField(max_length=15)
    packet_status = models.CharField(max_length=2)  # NM or SP
    date = models.DateField()
    time = models.TimeField()
    gps_validity = models.CharField(max_length=5)  # A or V
    latitude = models.FloatField()
    latitude_direction = models.CharField(max_length=5)  # N or S
    longitude = models.FloatField()
    longitude_direction = models.CharField(max_length=5)  # E or W
    altitude = models.FloatField()
    speed = models.FloatField()
    distance = models.FloatField()
    provider = models.CharField(max_length=50)
    vehicle_reg_no = models.CharField(max_length=20)
    reply_mob_no = models.CharField(max_length=15)    
    extention = models.TextField(blank=True, null=True)
    device_tag=models.ForeignKey(DeviceTag, on_delete=models.CASCADE,null=True, blank=True)
    class Meta:
        app_label = 'skytron_api'
    def __str__(self):
        return f"{self.device_imei} - {self.date} {self.time}"

    @classmethod
    def create_from_string(cls, data_list): 
        # Handle default values for missing data
        if data_list[3]=='x':
            data_list[3]='01012020'
        if data_list[4]=='x':
            data_list[4]='000000'
            
        # For new EPB format, the date and time are already separated correctly
        # data_list[3] should be date in DDMMYYYY format like "24102025"
        # data_list[4] should be time in HHMMSS format like "063355"
        
        # Parse the date - expect DDMMYYYY format
        try:
            date_part = data_list[3]
            if len(date_part) == 8:  # DDMMYYYY format
                data_list[3] = datetime.strptime(date_part, "%d%m%Y").strftime("%Y-%m-%d")
            else:
                # Fallback to default date if format is unexpected
                data_list[3] = datetime.strptime("23062025", "%d%m%Y").strftime("%Y-%m-%d")
        except ValueError as e:
            print(f"Date parsing error: {e}, using default date")
            data_list[3] = datetime.strptime("23062025", "%d%m%Y").strftime("%Y-%m-%d")
        
        # Parse the time - expect HHMMSS format  
        try:
            time_part = data_list[4]
            if len(time_part) == 6:  # HHMMSS format
                data_list[4] = datetime.strptime(time_part, "%H%M%S").strftime("%H:%M:%S")
            else:
                # Fallback to default time if format is unexpected
                data_list[4] = datetime.strptime("000000", "%H%M%S").strftime("%H:%M:%S")
        except ValueError as e:
            print(f"Time parsing error: {e}, using default time")
            data_list[4] = datetime.strptime("000000", "%H%M%S").strftime("%H:%M:%S")

        # Combine date and time, then adjust timezone (GMT to IST: +5:30)
        datetime_str = f"{data_list[3]} {data_list[4]}"
        dt_object = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S") 
        adjusted_datetime = dt_object + timedelta(hours=5, minutes=30, seconds=0)

        data_list[3]=adjusted_datetime.strftime("%Y-%m-%d") 
        data_list[4]=adjusted_datetime.strftime("%H:%M:%S") 
        # First, let's check what device tags exist for this IMEI
        all_device_tags = DeviceTag.objects.filter(device__imei=str(data_list[1]))
        print(f"All device tags for IMEI {data_list[1]}:")
        for tag in all_device_tags:
            print(f"  - Status: {tag.status}, Vehicle: {tag.vehicle_reg_no}")
        
        # Try to find an active device tag
        device_tag = DeviceTag.objects.filter(device__imei=str(data_list[1])).last()
        if not device_tag:
            # If no active device found, try other valid statuses
            device_tag = DeviceTag.objects.filter(
                device__imei=str(data_list[1]), 
                status__in=['Owner_OTP_Verified', 'SOS_Confirmed', 'Live_Location_Confirmed']
            ).last()
        
        print("datalist",data_list[1])
        print(data_list)
        print(device_tag)
        

        #live_executiveList = User.objects.filter(login=True ,role='sosadmin', last_activity__gte=timezone.now() - timezone.timedelta(seconds=30) ).all()
        #existing_emergency_call = EmergencyCall.objects.filter(status = 'Closed').order_by('-start_time').all()
        #user_to_assign=get_logged_in_users_with_min_assignments()
        #EmergencyCall_assignment.objects.filter( EmergencyCall_id=existing_emergency_call    ).last()

        #print("received new call ")


        if device_tag:
            return cls(
                message_type=data_list[0],
                device_imei=data_list[1],
                packet_status=data_list[2],
                date=data_list[3],
                time=data_list[4],
                gps_validity=data_list[12],
                latitude=float(data_list[5]),
                latitude_direction=data_list[6],
                longitude=float(data_list[7]),
                longitude_direction=data_list[8],
                altitude=float(data_list[9]),
                speed=float(data_list[10]),
                distance=float(data_list[11]),
                provider=data_list[13],
                vehicle_reg_no=data_list[13],
                reply_mob_no=data_list[14],
                device_tag=device_tag,
            )



 


@receiver(post_save, sender=EMGPSLocation)
def create_emergency_call(sender, instance, created, **kwargs):

    if not created:
        return

    try:
        # Guard: device_tag must be set
        if not instance.device_tag_id:
            print(f"[EMCall] Skipping call creation — no device_tag on EMGPSLocation {instance.id}", flush=True)
            return

        # Cooldown guard: if this device call was just closed, ignore fresh SOS packets
        # for a short window so delayed device-side SOS state updates don't reopen a call.
        em_reopen_cooldown_seconds = 20
        latest_closed_call = (
            EMCall.objects
            .filter(device=instance.device_tag, status__in=["closed", "closed_false_alert"])
            .annotate(effective_closed_time=Coalesce('end_time', 'start_time'))
            .order_by('-effective_closed_time', '-id')
            .first()
        )
        if latest_closed_call:
            last_closed_time = latest_closed_call.end_time or latest_closed_call.start_time
            cooldown_cutoff = timezone.now() - timedelta(seconds=em_reopen_cooldown_seconds)
            if last_closed_time and last_closed_time >= cooldown_cutoff:
                print(
                    f"[EMCall] Cooldown active for device_tag {instance.device_tag_id} "
                    f"(last closed call #{latest_closed_call.id} at {last_closed_time}) "
                    f"— skipping new call",
                    flush=True,
                )
                return

        # Check if an EMCall already exists for this device that is still open
        existing_emergency_call = EMCall.objects.filter(
            device=instance.device_tag
        ).exclude(status__in=["closed_false_alert", "closed"]).last()

        if existing_emergency_call:
            # If the existing call is still pending and has at least one active (non-closed,
            # non-rejected) assignment, nothing new is needed.
            active_assignment = EMCallAssignment.objects.filter(
                call=existing_emergency_call,
            ).exclude(status__in=["closed", "rejected", "closed_false_alert"]).exists()

            if active_assignment:
                print(
                    f"[EMCall] Existing open EMCall #{existing_emergency_call.id} "
                    f"(status={existing_emergency_call.status}) already has active assignments "
                    f"— skipping new call for device_tag {instance.device_tag_id}",
                    flush=True,
                )
                return

            # All assignments are closed/rejected but the call itself is still open.
            # Re-open the call as pending and re-assign below instead of creating a duplicate.
            print(
                f"[EMCall] Existing EMCall #{existing_emergency_call.id} has no active assignments "
                f"— resetting to pending and re-assigning for device_tag {instance.device_tag_id}",
                flush=True,
            )
            existing_emergency_call.status = "pending"
            existing_emergency_call.save(update_fields=["status"])

        # Resolve state from the device_tag chain
        try:
            st = instance.device_tag.device.dealer.manufacturer.state
        except AttributeError as e:
            print(f"[EMCall] Cannot resolve state for device_tag {instance.device_tag_id}: {e}", flush=True)
            return

        extention_value = (instance.extention or '').strip()
        normalized_extention = extention_value[1:-1].strip() if extention_value.startswith('{') and extention_value.endswith('}') else extention_value
        em_type = 'device'
        if normalized_extention.startswith('SOS_PUB_'):
            em_type = 'BLE_Public'
        elif normalized_extention.startswith('SOS_USER_'):
            em_type = 'BLE_Login'
        elif normalized_extention.startswith('SOS_TM_IP_'):
            em_type = 'BLE_TM_PW_Fail'
        elif normalized_extention.startswith('SOS_TM_RV_'):
            em_type = 'BLE_TM_Route'

        if existing_emergency_call:
            # Re-use the existing call (now reset to pending), just create fresh assignments
            em = existing_emergency_call
        else:
            # Create a brand-new EMCall
            team = EMTeams.objects.filter(status="Active", state=st).order_by('?').last()
            em = EMCall.objects.create(
                device=instance.device_tag,
                team=team,
                status='pending',
                em_type=em_type,
                extention=extention_value or None,
            )
            print(f"[EMCall] Created new EMCall #{em.id} for device_tag {instance.device_tag_id}", flush=True)

        # Resolve team for assignments (may differ if just re-using an old call)
        team = EMTeams.objects.filter(status="Active", state=st).order_by('?').last()
        if not team:
            print(f"[EMCall] No active team found in state {st} — EMCall #{em.id} created with no assignments", flush=True)
            return

        admin = EM_admin.objects.filter(state=st).last() or EM_admin.objects.last()
        if not admin:
            print(f"[EMCall] No EM_admin found — cannot create assignments for EMCall #{em.id}", flush=True)
            return

        teamlead = team.teamlead

        if teamlead:
            EMCallAssignment.objects.create(
                admin=admin,
                call=em,
                status="pending",
                type="teamlead",
                ex=teamlead,
            )
        else:
            print(f"[EMCall] Team #{team.id} has no teamlead — skipping teamlead assignment", flush=True)

        # --- Smart desk_ex assignment with round-robin load balancing ---
        # Team membership is not used for desk_ex assignment. Any desk_ex in
        # the same state can receive calls.
        desk_ex_members = list(EM_ex.objects.filter(state=st, user_type='desk_ex').distinct())

        # Determine which of them are currently online/active in the last minute.
        online_threshold = timezone.now() - timedelta(minutes=1)
        from django.db.models import Count, Q
        online_desk_exs = [
            ex for ex in desk_ex_members
            if ex.users.filter(login=True, last_activity__gte=online_threshold).exists()
        ]

        if online_desk_exs:
            # Pick the executive with the fewest active (non-closed/non-rejected) desk_ex assignments.
            active_statuses = ["pending", "accepted", "arriving", "arrived"]
            load = {
                ex.id: EMCallAssignment.objects.filter(
                    ex=ex,
                    type="desk_ex",
                    status__in=active_statuses,
                ).count()
                for ex in online_desk_exs
            }
            desk_ex = min(online_desk_exs, key=lambda ex: load[ex.id])
            print(
                f"[EMCall] Assigned EMCall #{em.id} to desk_ex #{desk_ex.id} "
                f"(load={load[desk_ex.id]}; {len(online_desk_exs)} executives online)",
                flush=True,
            )
        else:
            # No online executive — leave unassigned; will be picked up when one logs in.
            desk_ex = None
            print(
                f"[EMCall] No desk_ex online for EMCall #{em.id} — assignment left unassigned",
                flush=True,
            )

        EMCallAssignment.objects.create(
            admin=admin,
            call=em,
            status="pending",
            type="desk_ex",
            ex=desk_ex,  # may be None if nobody is online
        )
        # --- End smart assignment ---

    except Exception as e:
        print(f"[EMCall] Unexpected error in create_emergency_call signal: {e}", flush=True)












class IPList(models.Model):
    objects = SafeCreateManager()
    STATUS_CHOICES = [
        ('Valid', 'Valid'),
        # Add other status options
    ]

    ip1 = models.GenericIPAddressField()
    port1 = models.CharField(max_length=4)
    ip2 = models.GenericIPAddressField()
    port2 = models.CharField(max_length=4)
    ip_im = models.GenericIPAddressField()
    port_im = models.CharField(max_length=4)
    rule = models.TextField()
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)


    

class FOTA(models.Model):
    objects = SafeCreateManager()
    deviceMode = models.IntegerField(verbose_name="Device Mode")
    status = models.CharField(max_length=10, choices=[("active", "Active"), ("notactive", "Not Active")], verbose_name="Status")
    softwareVersion = models.CharField(max_length=255, verbose_name="Software Version")
    firmwarePath = models.CharField(max_length=255, verbose_name="Firmware Path")
    firmwareHex = models.CharField(max_length=255, verbose_name="Firmware Hex")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    def __str__(self):
        return f"FOTA {self.id}"


'''class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deactive', 'Deactive'),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    access = models.ManyToManyField(User, related_name='accessible_vehicles', blank=True)
    vregno = models.CharField(max_length=55,unique=True)
    engineno = models.CharField(max_length=55,unique=True)
    chessisno = models.CharField(max_length=55,unique=True)
    vehiclemake = models.CharField(max_length=55)
    vehiclemodel = models.CharField(max_length=55)
    vehiclecategory = models.CharField(max_length=55)
    rcfilepath = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    createdby = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_vehicles')
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.vregno'''
'''

class CustomToken(Token):
    is_active = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.last_activity = timezone.now()
        super().save(*args, **kwargs)

'''
class Session(models.Model):
    objects = SafeCreateManager()
    loginTime = models.DateTimeField(default=timezone.now, verbose_name="Login Time")
    user = models.ForeignKey(User, on_delete=models.CASCADE)# models.IntegerField(verbose_name="User")
    token = models.CharField(max_length=1500, blank=True, null=True, verbose_name="Token")  # Increased for JWT tokens
    token_tmp = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token_tmp")
    otp = models.IntegerField(blank=True, null=True, verbose_name="OTP")
    status = models.CharField(max_length=10, choices=[("otpsent", "OTP Sent"), ("login", "Login"), ("logout", "Logout"), ("timeout", "Timeout")], verbose_name="Status")
    lastactivity=models.DateTimeField(default=timezone.now, verbose_name="lastactivity")
   
    def __str__(self):
        return f"Session {self.id}"

class OTPRequest(models.Model):
    objects = SafeCreateManager()
    otpTime = models.DateTimeField(auto_now_add=True, verbose_name="OTP Time")
    type = models.CharField(max_length=5, choices=[("email", "Email"), ("sms", "SMS")], verbose_name="Type")
    user = models.IntegerField(verbose_name="User")
    otp = models.CharField(max_length=255, verbose_name="OTP")
    status = models.CharField(max_length=20, choices=[("otpsent", "OTP Sent"), ("errorsending", "Error Sending"), ("verified", "Verified"), ("donotmatch", "Do Not Match"), ("timeout", "Timeout")], verbose_name="Status")

    def __str__(self):
        return f"OTPRequest {self.id}"

class esimActivationRequest(models.Model):
    objects = SafeCreateManager()
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="creates_at")
    ceated_by=models.ForeignKey(Dealer, on_delete=models.CASCADE)
    eSim_provider=models.ForeignKey(eSimProvider, on_delete=models.CASCADE)
    valid_from = models.DateTimeField(null=True)
    valid_upto = models.DateTimeField(null=True)
    accepted_at = models.DateTimeField(null=True)
    device=models.ForeignKey(DeviceStock, on_delete=models.CASCADE)    
    status = models.CharField(max_length=20, choices=[("pending", "pending"), ("valid", "valid"), ("invalid", "invalid")], verbose_name="Status")

    def __str__(self):
        return f"esimActivationRequest {self.id}"

class EditRequest(models.Model):
    objects = SafeCreateManager()
    time = models.DateTimeField(auto_now_add=True, verbose_name="Time")
    type = models.CharField(max_length=20, choices=[("owner", "Owner"), ("device", "Device"), ("vehicle", "Vehicle"), ("devicemodel", "Device Model"), ("dealer", "Dealer"), ("manufacturer", "Manufacturer")], verbose_name="Type")
    from_user = models.IntegerField(verbose_name="From User")
    to_user = models.IntegerField(verbose_name="To User")
    otp = models.IntegerField(verbose_name="OTP")
    newdataid = models.IntegerField(verbose_name="New Data ID")
    olddataid = models.IntegerField(verbose_name="Old Data ID")
    status = models.CharField(max_length=20, choices=[("requestsent", "Request Sent"), ("accepted", "Accepted"), ("rejected", "Rejected")], verbose_name="Status")

    def __str__(self):
        return f"EditRequest {self.id}"
 

class Settings(models.Model):
    objects = SafeCreateManager()
    velid_time = models.DateTimeField(auto_now_add=True, verbose_name="Valid Time")
    type = models.CharField(max_length=255, verbose_name="Type")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    settingsstring = models.CharField(max_length=255, verbose_name="Settings String")
    settingsmethod = models.CharField(max_length=255, verbose_name="Settings Method")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    def __str__(self):
        return f"Settings {self.id}"


class LoginSettings(models.Model):
    """
    Model to store login restrictions and settings per user type/role.
    These settings control login behavior including limits, expiry, and time boundaries.
    """
    objects = SafeCreateManager()
    
    # User role this setting applies to
    user_role = models.CharField(
        max_length=20,
        unique=True,
        choices=[
            ("superadmin", "Super Admin"),
            ("stateadmin", "State Admin"),
            ("devicemanufacture", "Device Manufacture"),
            ("dealer", "Dealer"),
            ("owner", "Owner"),
            ("esimprovider", "eSimProvider"),
            ("filment", "Filment"),
            ("sosadmin", "SOS Admin"),
            ("teamleader", "Team Leader"),
            ("sosexecutive", "SOS Executive"),
            ("default", "Default"),  # Fallback for any role not explicitly configured
        ],
        verbose_name="User Role"
    )
    
    # 1. Per day login limit (how many times a user can login per day)
    daily_login_limit = models.IntegerField(
        default=0,
        verbose_name="Daily Login Limit",
        help_text="Maximum number of logins allowed per day per user. 0 = unlimited"
    )
    
    # 2. Session expiry time in minutes (how long a session stays active)
    session_expiry_minutes = models.IntegerField(
        default=2880,  # 2 days (48 hours) default
        verbose_name="Session Expiry (Minutes)",
        help_text="Session expiry time in minutes. After this time, user must login again"
    )
    
    # 3. Maximum simultaneous active sessions
    max_simultaneous_sessions = models.IntegerField(
        default=0,
        verbose_name="Max Simultaneous Sessions",
        help_text="Maximum number of simultaneous active sessions allowed. 0 = unlimited"
    )
    
    # 4. Login time boundaries (allowed login hours)
    login_start_time = models.TimeField(
        default="00:00:00",
        verbose_name="Login Start Time",
        help_text="Start time for allowed login period (24-hour format, e.g., 08:00:00)"
    )
    
    login_end_time = models.TimeField(
        default="23:59:59",
        verbose_name="Login End Time",
        help_text="End time for allowed login period (24-hour format, e.g., 18:00:00)"
    )
    
    # Enable/disable time boundary check
    enforce_time_boundary = models.BooleanField(
        default=False,
        verbose_name="Enforce Time Boundary",
        help_text="If True, users can only login between start and end times"
    )
    
    # Metadata
    created_by = models.CharField(max_length=255, blank=True, null=True, verbose_name="Created By")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    class Meta:
        verbose_name = "Login Setting"
        verbose_name_plural = "Login Settings"
        ordering = ['user_role']
    
    def __str__(self):
        return f"LoginSettings for {self.user_role}"


class GPSData(models.Model):
    objects = SafeCreateManager()
    entry_time = models.DateTimeField(auto_now_add=True)
    packet_datetime = models.DateTimeField(null=True, blank=True)
    #start_character = models.CharField(max_length=1)
    #header = models.CharField(max_length=1)
    #vendor_id = models.CharField(max_length=4)
    #firmware_version = models.CharField(max_length=5)
    packet_type = models.CharField(max_length=2)
    alert_id = models.CharField(max_length=4)
    packet_status = models.CharField(max_length=4)
    #imei = models.CharField(max_length=15)
    #vehicle_registration_number = models.CharField(max_length=16)
    gps_status = models.CharField(max_length=4)
    date = models.CharField(max_length=8)
    time = models.CharField(max_length=6)
    latitude = models.FloatField()
    latitude_dir = models.CharField(max_length=5)
    longitude = models.FloatField()
    longitude_dir = models.CharField(max_length=5)
    speed = models.FloatField()
    heading = models.FloatField()
    satellites = models.IntegerField()
    altitude = models.IntegerField()
    pdop = models.FloatField()
    hdop = models.FloatField()
    network_operator = models.CharField(max_length=8)
    ignition_status = models.CharField(max_length=4)
    main_power_status = models.CharField(max_length=4)
    main_input_voltage = models.FloatField()
    internal_battery_voltage = models.FloatField()
    emergency_status = models.CharField(max_length=4)
    box_tamper_alert = models.CharField(max_length=4)
    gsm_signal_strength = models.CharField(max_length=5)
    mcc = models.CharField(max_length=6)
    mnc = models.CharField(max_length=6)
    lac = models.CharField(max_length=6)
    cell_id = models.CharField(max_length=6)
    nbr1_cell_id = models.CharField(max_length=6)
    nbr1_lac = models.CharField(max_length=6)
    nbr1_signal_strength = models.CharField(max_length=6)
    nbr2_cell_id = models.CharField(max_length=6)
    nbr2_lac = models.CharField(max_length=6)
    nbr2_signal_strength = models.CharField(max_length=4)
    nbr3_cell_id = models.CharField(max_length=6)
    nbr3_lac = models.CharField(max_length=6)
    nbr3_signal_strength = models.CharField(max_length=6)
    nbr4_cell_id = models.CharField(max_length=6)
    nbr4_lac = models.CharField(max_length=6)
    nbr4_signal_strength = models.CharField(max_length=6)
    digital_input_status = models.CharField(max_length=6)
    digital_output_status = models.CharField(max_length=4)
    frame_number = models.IntegerField()
    odometer = models.FloatField()
    #checksum = models.CharField(max_length=8)
    #end_char = models.CharField(max_length=1) 
    device_tag=models.ForeignKey(DeviceTag, on_delete=models.CASCADE,null=True, blank=True)

    # Location / administrative area information (nullable)
    state = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    district = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    city = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    road = models.CharField(max_length=255, null=True, blank=True)
    road_type = models.CharField(max_length=32, null=True, blank=True)

    # Consecutive time spent in the same administrative area (nullable)
    time_in_same_state = models.DurationField(null=True, blank=True)
    time_in_same_district = models.DurationField(null=True, blank=True)
    time_in_same_city = models.DurationField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['device_tag', '-entry_time', '-id'], name='gpsdata_tag_time_id_idx'),
            models.Index(fields=['device_tag', '-packet_datetime', '-id'], name='gpsdata_tag_packet_dt_idx'),
            # Supports fast GROUP BY device_tag_id + MAX(id) for latest-per-device queries
            models.Index(fields=['device_tag', 'id'], name='gpsdata_tag_id_asc_idx'),
        ]


def _gps_norm_text(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.casefold()


def _gps_classify_road_type(geo_payload, road_value, city_value):
    """Return one of: National highway, city area, others."""
    payload = geo_payload or {}
    extratags = payload.get('extratags') or {}
    namedetails = payload.get('namedetails') or {}

    road_candidates = [
        road_value,
        payload.get('name'),
        extratags.get('ref'),
        namedetails.get('ref'),
    ]
    road_text = " ".join([str(x) for x in road_candidates if x]).upper()

    highway_class = str(payload.get('class') or payload.get('category') or '').lower()
    highway_type = str(payload.get('type') or '').lower()

    if "NATIONAL HIGHWAY" in road_text or "NH" in road_text:
        return "National highway"

    if highway_class == 'highway' and highway_type in {
        'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link'
    }:
        return "National highway"

    if city_value or highway_type in {
        'residential', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link',
        'unclassified', 'service', 'living_street', 'road'
    }:
        return "city area"

    return "others"


def _gps_reverse_geocode_from_api(lat, lon):
    """Resolve state/district/city/road from map-geocoding.gromed.in reverse API."""
    geocode_enabled = os.getenv('GPS_REVERSE_GEOCODE_ENABLED', '1').strip().lower()
    if geocode_enabled in {'0', 'false', 'no', 'off'}:
        return {}

    fail_until = getattr(_gps_reverse_geocode_from_api, '_fail_until', 0.0)
    now = time.monotonic()
    if fail_until and now < fail_until:
        return {}

    timeout_raw = os.getenv('GPS_REVERSE_GEOCODE_TIMEOUT', '1.0').strip()
    cooldown_raw = os.getenv('GPS_REVERSE_GEOCODE_COOLDOWN', '15').strip()

    try:
        timeout_sec = max(0.2, float(timeout_raw))
    except Exception:
        timeout_sec = 1.0

    try:
        cooldown_sec = max(1.0, float(cooldown_raw))
    except Exception:
        cooldown_sec = 15.0

    try:
        import json
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen
    except Exception:
        return {}

    base_url = (os.getenv('GPS_REVERSE_GEOCODE_ROOT', 'https://map-geocoding.gromed.in').strip() or 'https://map-geocoding.gromed.in')
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"

    params = {
        'format': 'jsonv2',
        'lat': str(lat),
        'lon': str(lon),
        'zoom': '18',
        'addressdetails': '1',
        'extratags': '1',
        'namedetails': '1',
    }
    api_url = f"{base_url.rstrip('/')}/reverse?{urlencode(params)}"

    try:
        req = Request(api_url, headers={'User-Agent': 'SkytrackBackend/1.0'})
        with urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode('utf-8', errors='ignore'))
    except Exception:
        _gps_reverse_geocode_from_api._fail_until = time.monotonic() + cooldown_sec
        return {}

    _gps_reverse_geocode_from_api._fail_until = 0.0

    address = payload.get('address') or {}

    state_value = address.get('state')
    district_value = address.get('state_district') or address.get('county')
    city_value = (
        address.get('city')
        or address.get('town')
        or address.get('village')
        or address.get('suburb')
    )
    road_value = address.get('road') or payload.get('name')

    road_type_value = _gps_classify_road_type(payload, road_value, city_value)

    return {
        'state': state_value,
        'district': district_value,
        'city': city_value,
        'road': road_value,
        'road_type': road_type_value,
    }


def _geocode_and_patch(pk, lat, lon):
    """Background: resolve address from geocoding API and patch the GPS record."""
    try:
        close_old_connections()
        geo = _gps_reverse_geocode_from_api(lat, lon)
        if not geo:
            return
        patch = {}
        if geo.get('state'):     patch['state']     = geo['state']
        if geo.get('district'):  patch['district']  = geo['district']
        if geo.get('city'):      patch['city']      = geo['city']
        if geo.get('road'):      patch['road']      = geo['road']
        if geo.get('road_type'): patch['road_type'] = geo['road_type']
        if patch:
            GPSData.objects.filter(pk=pk).update(**patch)
    except Exception:
        pass


@receiver(post_save, sender=GPSData, dispatch_uid="gpsdata_populate_location_and_consecutive_time")
def gpsdata_populate_location_and_consecutive_time(sender, instance, created, **kwargs):
    """Populate state/district/city/road and consecutive time counters on insert.

    Rules:
    - Location fields are nullable.
    - If current value matches the previous entry for the same device_tag,
      the corresponding time_in_same_* is incremented by the delta between entry_time values.
    - Otherwise the counter resets to 0 (or remains null if current value is null).
    """
    if not created:
        return

    if not getattr(instance, 'device_tag_id', None):
        return

    update_data = {}

    # Geocoding is done asynchronously in the background (_geocode_and_patch).
    # Here we only carry forward location from the previous GPS point so the
    # record has useful data immediately, without blocking on an HTTP call.

    # Fallback from device-tag registration hierarchy where possible.
    try:
        dt = instance.device_tag
        if dt is not None:
            if not update_data.get('state') and not instance.state:
                st_obj = getattr(getattr(getattr(dt, 'district', None), 'state', None), 'state', None)
                if st_obj:
                    update_data['state'] = st_obj
            if not update_data.get('district') and not instance.district:
                dist_obj = getattr(getattr(dt, 'district', None), 'district', None)
                if dist_obj:
                    update_data['district'] = dist_obj
    except Exception:
        pass

    # Fetch previous point for this device_tag.
    prev = (
        GPSData.objects.filter(device_tag_id=instance.device_tag_id)
        .exclude(pk=instance.pk)
        .order_by('-entry_time', '-id')
        .first()
    )

    delta = timedelta(0)
    if prev is not None:
        try:
            delta = instance.entry_time - prev.entry_time
            if delta.total_seconds() < 0:
                delta = timedelta(0)
        except Exception:
            delta = timedelta(0)

    current_state = update_data.get('state', instance.state)
    current_district = update_data.get('district', instance.district)
    current_city = update_data.get('city', instance.city)

    # If API lookup misses for this point, carry forward previous resolved location.
    if prev is not None:
        if not current_state and prev.state:
            update_data['state'] = prev.state
            current_state = prev.state
        if not current_district and prev.district:
            update_data['district'] = prev.district
            current_district = prev.district
        if not current_city and prev.city:
            update_data['city'] = prev.city
            current_city = prev.city
        if not update_data.get('road', instance.road) and prev.road:
            update_data['road'] = prev.road
        if not update_data.get('road_type', instance.road_type) and prev.road_type:
            update_data['road_type'] = prev.road_type

    if current_state is None:
        update_data['time_in_same_state'] = None
    else:
        if prev is not None and _gps_norm_text(prev.state) == _gps_norm_text(current_state):
            update_data['time_in_same_state'] = (prev.time_in_same_state or timedelta(0)) + delta
        else:
            update_data['time_in_same_state'] = timedelta(0)

    if current_district is None:
        update_data['time_in_same_district'] = None
    else:
        if prev is not None and _gps_norm_text(prev.district) == _gps_norm_text(current_district):
            update_data['time_in_same_district'] = (prev.time_in_same_district or timedelta(0)) + delta
        else:
            update_data['time_in_same_district'] = timedelta(0)

    if current_city is None:
        update_data['time_in_same_city'] = None
    else:
        if prev is not None and _gps_norm_text(prev.city) == _gps_norm_text(current_city):
            update_data['time_in_same_city'] = (prev.time_in_same_city or timedelta(0)) + delta
        else:
            update_data['time_in_same_city'] = timedelta(0)

    # Avoid recursion: update via queryset.
    if update_data:
        GPSData.objects.filter(pk=instance.pk).update(**update_data)

    # Submit reverse geocoding in background; will patch state/city/road when done.
    try:
        _lat = float(instance.latitude)
        _lon = float(instance.longitude)
        _geocode_bg_executor.submit(_geocode_and_patch, instance.pk, _lat, _lon)
    except Exception:
        pass

class GPSDataLog(models.Model):
    objects = SafeCreateManager()
    timestamp = models.DateTimeField(auto_now_add=True)
    raw_data = models.TextField()

class GPSemDataLog(models.Model):
    objects = SafeCreateManager()
    timestamp = models.DateTimeField(auto_now_add=True)
    raw_data = models.TextField()

  
class AlertsLog(models.Model):
    objects = SafeCreateManager()
    TYPE_CHOICES = [
        ('Route', 'Route Deviation'),
        ('Geofence', 'Geofence'),
        ('Idling', 'Idling'),
        ('OfflineDevice', 'OfflineDevice'),
        ('Overtime', 'Overtime'),
        ('UnauthorizedStop', 'Unauthorized Stop'),
        ('UnauthorizedSkip', 'Unauthorized Skip'),
        ('NetworkLoss', 'Network Loss'),
        ('GPSLoss', 'GPS Loss'),
        ('Permit', 'Permit'),
        ('Permit_3day', 'Permit Expiring Soon'),
        ('Route_overspeed', 'Route Overspeed'),
        ('state_border_cross', 'State Border Cross'),
        ('district_border_cross', 'District Border Cross'),
        ('city_border_cross', 'City Border Cross'),
        ('Incident', 'Incident'),
        ('Em', 'Emergency SOS'),
        ('EmPublicApp', 'EmPublicApp'),
        ('EmRegisteredApp', 'EmRegisteredApp'),
        ('EmMonitorTripSOS', 'EmMonitorTripSOS'),
        ('EmMonitorTripInvalidPw', 'EmMonitorTripInvalidPw'),
        ('EmMonitorTripBLEDisconnect', 'EmMonitorTripBLEDisconnect'),
        ('EmMonitorTripDeviated', 'EmMonitorTripDeviated'),
        ('Eng', 'Engine Status'),
        ('OverSpeed', 'Over Speed'),
        ('LowIntBat', 'Low Internal Battery'),
        ('LowExtBat', 'Low External Battery'),
        ('ExtBatDiscnt', 'External Battery Disconnected'),
        ('BoxTemp', 'Box Temperature'),
        ('EmTemp', 'Emergency Temperature'),
        ('Tilt', 'Tilt'),
        ('HarshBreak', 'Harsh Braking'),
        ('HarshTurn', 'Harsh Turn'),
        ('HarshAcceleration', 'Harsh Acceleration'),
        ('UnauthorizedParking', 'Unauthorized Parking'),
        ('Prohibited_Area', 'Prohibited Area'),
    ]
    status_CHOICES = [
        ('in', 'in'), 
        ('out', 'out'),  
        ('', ''),  
    ]

    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=50, choices=status_CHOICES,null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    gps_ref=models.ForeignKey(GPSData, on_delete=models.CASCADE)
    route_ref=models.ForeignKey(Route, on_delete=models.CASCADE,null=True, blank=True)
    poi_ref=models.ForeignKey(pointofinterests, on_delete=models.CASCADE,null=True, blank=True)
    em_ref=models.ForeignKey("EMCall", on_delete=models.CASCADE,null=True, blank=True)
    alert_details = models.TextField()
    #dummnyuser=models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True) 
    deviceTag=models.ForeignKey(DeviceTag, on_delete=models.CASCADE) 
    #district=models.ForeignKey(dto_rto, on_delete=models.CASCADE,null=True, blank=True) 
    state=models.ForeignKey(Settings_State, on_delete=models.CASCADE) 
    

class Notice(models.Model): 
    objects = SafeCreateManager()
    created = models.DateField(auto_now_add=True)  
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    file = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    detail = models.CharField(max_length=255, blank=True, null=True)     
    status = models.CharField(max_length=25, blank=True, null=True)      




class EMTeams(models.Model): 
    objects = SafeCreateManager()
    choices=[("NotActive", "NotActive"), ("Active", "Active"), ("Removed", "Removed")] 
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    teamlead =models.ForeignKey(EM_ex, on_delete=models.CASCADE)
    members = models.ManyToManyField(EM_ex,   related_name='SOS_Executive_member_team') 
    created_by = models.ForeignKey(EM_admin, on_delete=models.CASCADE, related_name='SOS_admin_createdby_team') 
    created_at =   models.DateTimeField(auto_now_add=True, verbose_name="created_at")
    activated_at =   models.DateTimeField(blank=True, null=True)
    removed_at =   models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20,choices=choices)
    name = models.TextField()
    detail = models.TextField()
    def __str__(self):
        return f"EMCall {self.id}"


class EMCall(models.Model): 
    objects = SafeCreateManager()
    choices=[("pending", "pending"), ("desk_ex_assigned", "desk_ex_assigned"), ("broadcast_pending", "broadcast_pending"), ("field_ex_aproaching", "field_ex_aproaching"), ("field_ex_arrived", "field_ex_arrived"), ("closed_false_alert", "closed_false_alert"), ("closed", "closed")]
    team  = models.ForeignKey(EMTeams, null=True,  on_delete=models.CASCADE,related_name='EMTeams_id')
    device = models.ForeignKey(DeviceTag,  on_delete=models.CASCADE,related_name='DeviceTag_id')
    start_time =   models.DateTimeField(auto_now_add=True, verbose_name="start_time")
    end_time =   models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=30,choices=choices)
    closer_comment = models.TextField(blank=True, null=True)
    em_type=models.CharField(max_length=50,null=True, blank=True)
    extention = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"EMCall {self.id}"
 




class EMCallAssignment(models.Model):
    objects = SafeCreateManager() 
    status=[("pending", "pending"), ("accepted", "accepted"), ("rejected", "rejected"), ("arriving", "arriving"), ("arrived", "arrived"), ("closed_false_alert", "closed_false_alert"), ("closed", "closed")]
    types=[("teamlead", "teamlead"), ("desk_ex", "desk_ex"), ("police_ex", "police_ex"), ("ambulance_ex", "ambulance_ex") , ("pcr", "pcr") , ("acr", "acr") ]
    admin = models.ForeignKey(EM_admin,  on_delete=models.CASCADE,related_name='emcalladmin')
    ex = models.ForeignKey(EM_ex, null=True, blank=True, on_delete=models.SET_NULL, related_name='exec_id')
    call = models.ForeignKey(EMCall,  on_delete=models.CASCADE,related_name='EMCall_id')
    start_time =   models.DateTimeField(auto_now_add=True, verbose_name="start_time")
    accept_time = models.DateTimeField(blank=True, null=True)
    arrived_time = models.DateTimeField(blank=True, null=True)
    complete_time = models.DateTimeField(blank=True, null=True)
    reject_time =   models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=30,choices=status)
    type = models.CharField(max_length=30,choices=types)
    closer_comment = models.TextField(blank=True,null=True)
    desk_ex_comment = models.TextField(blank=True,null=True)
    def __str__(self):
        return f"EMCall {self.id}"

class EMCallBroadcast(models.Model): 
    objects = SafeCreateManager()
    status=[("pending", "pending"), ("accepted", "accepted"), ("timeout", "timeout"), ("canceled", "canceled")]
    types=[("police_ex", "police_ex"), ("ambulance_ex", "ambulance_ex") , ("pcr", "pcr") , ("acr", "acr") ]
    admin = models.ForeignKey(EM_admin,  on_delete=models.CASCADE,related_name='emcalladminb')
    acceted_by= models.ForeignKey(EM_ex, blank=True, null=True, on_delete=models.CASCADE,related_name='accptedbyexec_id')
    created_by= models.ForeignKey(EM_ex, blank=True, null=True, on_delete=models.CASCADE,related_name='createdbyexec_id')
    call = models.ForeignKey(EMCall,  on_delete=models.CASCADE,related_name='EMCallb_id')
    created_at =   models.DateTimeField(auto_now_add=True, verbose_name="start_time")
    accept_at = models.DateTimeField(blank=True, null=True)
    canceled_time = models.DateTimeField(blank=True, null=True) 
    radius= models.FloatField(blank=True, null=True)
    status = models.CharField(max_length=30,choices=status)
    type = models.CharField(max_length=30,choices=types) 
    def __str__(self):
        return f"EMCall {self.id}"
    


class EMCallMessages(models.Model): 
    objects = SafeCreateManager()
    call = models.ForeignKey(EMCall,  on_delete=models.CASCADE,related_name='EMCa111ll_id111')
    assignment = models.ForeignKey(EMCallAssignment,  on_delete=models.CASCADE,related_name='EMCallAssignm11ent111_id')
    time =   models.DateTimeField(auto_now_add=True, verbose_name="time")  
    message = models.TextField()
    def __str__(self):
        return f"EMCall {self.id}"


class EMCallBackupRequest(models.Model): 
    objects = SafeCreateManager()
    types=[ ("police_ex", "police_ex"), ("ambulance_ex", "ambulance_ex") ]
    call = models.ForeignKey(EMCall,  on_delete=models.CASCADE,related_name='EMCall_id111')
    assignment = models.ForeignKey(EMCallAssignment,  on_delete=models.CASCADE,related_name='EMCallAssignment111_id')
    time =   models.DateTimeField(auto_now_add=True, verbose_name="time")  
    type = models.CharField(max_length=30,choices=types)
    quantity = models.IntegerField( )
    accepted = models.BooleanField( )
    message = models.TextField()
    def __str__(self):
        return f"EMCall {self.id}"

class EMUserLocation(models.Model): 
    objects = SafeCreateManager()
    field_ex = models.ForeignKey(EM_ex,  null=True,on_delete=models.CASCADE,related_name='field_executive1_id_location')# models.CharField(max_length=50, unique=True)
    em_lat = models.FloatField(blank=True, null=True, verbose_name="em_lat") 
    em_lon = models.FloatField(blank=True, null=True, verbose_name="em_lon") 
    speed = models.FloatField(blank=True, null=True, verbose_name="speed") 
    time =   models.DateTimeField(auto_now_add=True, verbose_name="time")   
    def __str__(self):
        return f"EMCall {self.id}"


class BleKey(models.Model):
    objects = SafeCreateManager()
    # Increased length to support 128-character hexadecimal keys
    key = models.CharField(max_length=128, unique=True, verbose_name="BLE Key")
    imei = models.CharField(max_length=15, verbose_name="Device IMEI")
    active = models.BooleanField(default=True, verbose_name="Active Status")
    entry_time = models.DateTimeField(auto_now_add=True, verbose_name="Entry Time")
    
    def __str__(self):
        return f"BleKey {self.key} - {self.imei}"

    class Meta:
        app_label = 'skytron_api'
        indexes = [
            models.Index(fields=['imei', 'active'], name='blekey_imei_active_idx'),
        ]


class TokenBlacklist(models.Model):
    """
    Model to track blacklisted/invalidated JWT tokens
    Used to prevent token reuse after logout or security events
    """
    objects = SafeCreateManager()

    token = models.CharField(max_length=1500, unique=True, db_index=True, verbose_name="Token")
    jti = models.CharField(max_length=255, db_index=True, verbose_name="JWT ID")  # JWT ID from token payload
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")
    blacklisted_at = models.DateTimeField(default=timezone.now, verbose_name="Blacklisted At")
    reason = models.CharField(
        max_length=20, 
        choices=[
            ("logout", "User Logout"),
            ("expired", "Token Expired"),
            ("security", "Security Violation"),
            ("admin", "Admin Action")
        ],
        default="logout",
        verbose_name="Reason"
    )
    expires_at = models.DateTimeField(verbose_name="Token Expires At")  # Original token expiry time
    
    def __str__(self):
        return f"Blacklisted Token (User {self.user_id}) - {self.reason}"
    
    class Meta:
        db_table = 'token_blacklist'
        verbose_name = 'Token Blacklist'
        verbose_name_plural = 'Token Blacklists'
        indexes = [
            models.Index(fields=['token'], name='token_idx'),
            models.Index(fields=['jti'], name='jti_idx'),
            models.Index(fields=['user_id'], name='user_id_idx'),
        ]
    
    @classmethod
    def is_blacklisted(cls, token):
        """Check if a token is blacklisted"""
        return cls.objects.filter(token=token).exists()
    
    @classmethod
    def blacklist_token(cls, token, user_id, jti, expires_at, reason="logout"):
        """Add a token to the blacklist"""
        try:
            cls.objects.get_or_create(
                token=token,
                defaults={
                    'jti': jti,
                    'user_id': user_id,
                    'expires_at': expires_at,
                    'reason': reason
                }
            )
            return True
        except Exception as e:
            print(f"Error blacklisting token: {e}")
            return False
    
    @classmethod
    def cleanup_expired(cls):
        """Remove blacklisted tokens that have already expired (cleanup job)"""
        from django.utils import timezone
        deleted_count = cls.objects.filter(expires_at__lt=timezone.now()).delete()[0]
        print(f"Cleaned up {deleted_count} expired blacklisted tokens")
        return deleted_count


"""


class EMCall(models.Model): 
    device 
    start_time  
    end_time  
    status = [("pending", "pending"), ("desk_ex_assigned", "desk_ex_assigned"), ("broadcast_pending", "broadcast_pending"), ("field_ex_aproaching", "field_ex_aproaching"), ("field_ex_arrived", "field_ex_arrived"), ("closed_false_alert", "closed_false_alert"), ("closed", "closed")]
    closer_comment  

class EMCallAssignment(models.Model): 
    status=[("pending", "pending"), ("accepted", "accepted"), ("rejected", "rejected"), ("arriving", "arriving"), ("arrived", "arrived"), ("closed_false_alert", "closed_false_alert"), ("closed", "closed")]
    types=[("teamlead", "teamlead"), ("desk_ex", "desk_ex"), ("police_ex", "police_ex"), ("ambulance_ex", "ambulance_ex") ]
    call 
    start_time   
    end_time  
    closer_comment  

class EMCallMessages(models.Model): 
    call 
    assignment  
    time  
    message  


class EMUserLocation(models.Model): 
    field_ex
    em_lat  
    em_lon  
    speed  
    time  
    
"""


class BusStand(models.Model):
    objects = SafeCreateManager()
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    name = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bus_stands')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bus_stand'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.latitude}, {self.longitude}"


class OTASettings(models.Model):
    objects = SafeCreateManager()
    command = models.TextField()
    triggered_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ota_settings')
    triggered_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ota_settings'
        ordering = ['-triggered_at']

    def __str__(self):
        return f"OTA Command by {self.triggered_by} at {self.triggered_at}"



class IncidentRegister(models.Model):
    objects = SafeCreateManager()
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    image_file = models.CharField(max_length=500, blank=True, null=True)
    vehicle_reg_no = models.CharField(max_length=50)
    details = models.TextField(blank=True, null=True)
    registered_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incidents', null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    police_station = models.CharField(max_length=100, blank=True, null=True)
    latest_status = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='incident_updates', null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'incident_register'
        ordering = ['-registered_at']

    def __str__(self):
        return f"Incident - {self.vehicle_reg_no} at {self.registered_at}"
    
    
    
    
    
    
    
class TestAgency(models.Model):
    objects = SafeCreateManager()
    agency_name = models.CharField(max_length=255, verbose_name="Test Agency Name")
    company_address = models.CharField(max_length=255, blank=True, null=True)
    company_pin = models.CharField(max_length=20, blank=True, null=True)
    file_authLetter = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    users = models.ManyToManyField('User', related_name='testagency_user')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(default=timezone.localdate)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE, related_name='testagency_createdby')
    status_choices = [
        ('Created', 'Created'),
        ('UserVerified', 'UserVerified'),
        ('UserExpired', 'UserExpired'),
        ('Discontinued', 'Discontinued'),
        ('Accept', 'Accept'),
        ('Reject', 'Reject'),
    ]
    status = models.CharField(max_length=20, choices=status_choices)

    def __str__(self):
        return self.agency_name


class TestAgencyDetails(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
####################################################################################
####################################################################################
####################################################################################
########################School module models########################################
####################################################################################
####################################################################################
####################################################################################


from django.core.exceptions import ValidationError  

# =====================================================
# School Route
# =====================================================
# Table: skytron_api_schoolroute
# M2M (via through model RouteStop): skytron_api_routestop
class SchoolRoute(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_DELETED = "deleted"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        ("inactive", "Inactive"),  
    ]

    name = models.CharField(max_length=255)
    school = models.ForeignKey("School",on_delete=models.CASCADE,related_name="routes")
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_ACTIVE)

    # Example: [{"lat": 28.61, "lng": 77.20}, {"lat": 28.62, "lng": 77.21}]
    route_points = models.JSONField(default=list,blank=True,help_text="List of lat/lng coordinates defining the route path")

    # Ordered stops via RouteStop through model
    stops = models.ManyToManyField("SchoolBusStop",through="RouteStop",related_name="routes",blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="created_routes")
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    class Meta:
        # Table: skytron_api_schoolroute
        unique_together = ("school", "name")
        indexes = [
            models.Index(fields=["school", "status"]),
        ]

    def __str__(self):
        return self.name

# =====================================================
# School Bus Stop (owned by school bus module)
# =====================================================
# Table: skytron_api_schoolbusstop
class SchoolBusStop(models.Model):
    name = models.CharField(max_length=255)
    school = models.ForeignKey("School",on_delete=models.CASCADE,related_name="bus_stops")
    latitude = models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True)
    longitude = models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="created_bus_stops")
    created_at = models.DateTimeField(auto_now_add=True)
    timing = models.TimeField(null=True, blank=True)

    class Meta:
        # Table: skytron_api_schoolbusstop
        unique_together = ("school", "name")
        indexes = [
            models.Index(fields=["school", "is_active"]),
        ]

    def __str__(self):
        return self.name

# Table: skytron_api_routestop
class RouteStop(models.Model):
    route = models.ForeignKey(SchoolRoute,on_delete=models.CASCADE,related_name="route_stops")
    stop = models.ForeignKey("SchoolBusStop",on_delete=models.PROTECT,related_name="route_stops")
    order = models.PositiveIntegerField(help_text="Order of this stop in the route")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Table: skytron_api_routestop
        unique_together = ("route", "stop")
        ordering = ["order"]
        indexes = [
            models.Index(fields=["route", "order"]),
        ]

    def __str__(self):
        return f"{self.route.name} → Stop {self.order}: {self.stop.name}"

# =====================================================
# School
# =====================================================
# Table: skytron_api_school
class School(models.Model):

    # ── STATUS ────────────────────────────────────────────────────────────────
    STATUS_SUBMITTED            = "SUBMITTED"
    STATUS_UNDER_REVIEW         = "UNDER_REVIEW"
    STATUS_APPROVED             = "APPROVED"
    STATUS_REJECTED             = "REJECTED"
    STATUS_SETUP_SENT           = "SETUP_SENT"
    STATUS_SETUP_LINK_APPROVED  = "SETUP_LINK_APPROVED"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SETUP_SENT, "Setup Sent"),
        (STATUS_SETUP_LINK_APPROVED, "Setup Link Approved"),
    ]

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
        db_index=True
    )

    # ── SCHOOL DETAILS ────────────────────────────────────────────────────────
    school_name          = models.CharField(max_length=255)
    school_address       = models.TextField()
    school_pin    = models.CharField(max_length=20, db_index=True)
    school_phone = models.CharField(max_length=20)
    school_email = models.EmailField()

    school_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    school_lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    state = models.ForeignKey(
        'skytron_api.Settings_State',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    district = models.ForeignKey(
        'skytron_api.Settings_District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # ── USER RELATIONS ────────────────────────────────────────────────────────


    # School admins (after setup completion)
    users = models.ManyToManyField(User,
        related_name="schooladmin_user",
        )

    # ── DOCUMENTS (FTP PATHS) ─────────────────────────────────────────────────
    file_id_proof = models.CharField(max_length=1000, blank=True, null=True)
    file_authorization_letter = models.CharField(max_length=1000, blank=True, null=True)
    extra_documents = models.JSONField(default=list, blank=True)

    # ── META ──────────────────────────────────────────────────────────────────
    remarks    = models.TextField(blank=True)
    is_active  = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"


# =====================================================
# School Application (Onboarding)
# =====================================================
# Table: skytron_api_schoolapplication
class SchoolApplication(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    school_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_PENDING)
    remarks = models.TextField(blank=True)
    otp = models.CharField(max_length=128, blank=True)
    otp_verified = models.BooleanField(default=False)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="school_applications")

    class Meta:
        # Table: skytron_api_schoolapplication
        indexes = [models.Index(fields=["status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["latitude", "longitude"],
                name="unique_school_location"
            ),
        ]

    def __str__(self):
        return f"{self.school_name} ({self.status})"


# =====================================================
# School Bus Document
# =====================================================
# Table: skytron_api_schoolbusdocument

def bus_document_upload_path(instance, filename):
    return (
        f"school_bus_documents/"
        f"school_{instance.school.id}/"
        f"bus_{instance.bus.id}/"
        f"{filename}"
    )


class SchoolBusDocument(models.Model):
    DOC_RC = "RC"
    DOC_PERMIT = "PERMIT"
    DOC_AUTH = "AUTH_LETTER"
    DOC_VLTD = "VLTD_RECEIPT"
    DOC_REQUEST_LETTER = "REQUEST_LETTER"

    DOC_CHOICES = [
        (DOC_RC, "Vehicle RC"),
        (DOC_PERMIT, "School Bus Permit"),
        (DOC_AUTH, "Authorization Letter"),
        (DOC_VLTD, "VLTD Fitment Receipt"),
        (DOC_REQUEST_LETTER, "Request Letter From School Principal"), 
    ]

    school = models.ForeignKey(School,on_delete=models.CASCADE,related_name="bus_documents")
    # Bus still comes from Skytron's DeviceTag
    bus = models.ForeignKey('DeviceTag',on_delete=models.CASCADE,related_name="documents")
    document_type = models.CharField(max_length=30, choices=DOC_CHOICES)
    file_path = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Table: skytron_api_schoolbusdocument
        unique_together = ("bus", "document_type")
        indexes = [models.Index(fields=["school", "bus"])]

    def __str__(self):
        return f"{self.bus} - {self.document_type}"


# =====================================================
# Student
# =====================================================
# Table: skytron_api_student
class Student(models.Model):
    name = models.CharField(max_length=255)
    roll_number = models.CharField(max_length=50)
    class_name = models.CharField(max_length=50)
    school = models.ForeignKey(School,on_delete=models.CASCADE,related_name="students")
    created_at = models.DateTimeField(auto_now_add=True)
    section = models.CharField(max_length=50, blank=True)

    class Meta:
        # Table: skytron_api_student
        constraints = [
            models.UniqueConstraint(
                fields=["school", "class_name", "roll_number"],
                name="unique_roll_per_class_per_school"
            )
        ]
        indexes = [models.Index(fields=["school", "class_name"])]

    def __str__(self):
        return f"{self.name} ({self.class_name})"


# =====================================================
# Parent Profile
# =====================================================
# Table: skytron_api_parentprofile
# M2M (students): skytron_api_parentprofile_students
class ParentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="parent_profile")
    school = models.ForeignKey(School,on_delete=models.CASCADE,related_name="parents")
    students = models.ManyToManyField(Student,related_name="parents",blank=True)  # M2M table: skytron_api_parentprofile_students
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6,null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6,null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Table: skytron_api_parentprofile
        indexes = [
            models.Index(fields=["school"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"Parent: {self.user}"


# =====================================================
# Student Bus Allocation
# =====================================================
# Table: skytron_api_studentbusallocation
class StudentBusAllocation(models.Model):
    student = models.ForeignKey(Student,on_delete=models.CASCADE,related_name="bus_allocations")
    # Bus from Skytron
    bus = models.ForeignKey('DeviceTag',on_delete=models.PROTECT,related_name="student_allocations")
    # Route from our own module
    route = models.ForeignKey(SchoolRoute,on_delete=models.PROTECT,related_name="student_allocations")
    # Stops from our own module
    pickup_stop = models.ForeignKey(SchoolBusStop,on_delete=models.PROTECT,related_name="pickup_students")
    drop_stop = models.ForeignKey(SchoolBusStop,on_delete=models.PROTECT,related_name="drop_students")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Table: skytron_api_studentbusallocation
        indexes = [models.Index(fields=["student", "is_active"])]

    def clean(self):
        if self.is_active:
            qs = StudentBusAllocation.objects.filter(
                student=self.student,
                is_active=True
            ).exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError(
                    "This student already has an active bus allocation."
                )

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Allocation for {self.student}"


# =====================================================
# School Holiday
# =====================================================
# Table: skytron_api_schoolholiday
class SchoolHoliday(models.Model):
    HOLIDAY_TYPE_CHOICES = [
        ("national", "National"),
        ("festival", "Festival"),
        ("local", "Local"),
        ("emergency", "Emergency"),
    ]

    school = models.ForeignKey(School,on_delete=models.CASCADE,related_name="holidays")
    date = models.DateField()
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20,choices=HOLIDAY_TYPE_CHOICES,default="festival")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="created_holidays")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="updated_holidays")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Table: skytron_api_schoolholiday
        constraints = [
            models.UniqueConstraint(
                fields=["school", "date"],
                condition=models.Q(is_active=True),
                name="unique_active_holiday_per_school_date"
            )
        ]
        ordering = ["-date"]
        indexes = [models.Index(fields=["school", "date"])]

    def __str__(self):
        return f"{self.school.name} - {self.date} - {self.title}"


# =====================================================
# School Bus Trip
# =====================================================
# Table: skytron_api_schoolbustrip
class SchoolBusTrip(models.Model):
    STATUS_PLANNED = "PLANNED"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_UNSCHEDULED = "UNSCHEDULED"

    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planned"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_UNSCHEDULED, "Unscheduled"),
    ]

    school = models.ForeignKey(School,on_delete=models.CASCADE,related_name="trips")
    # Bus from Skytron
    bus = models.ForeignKey('DeviceTag',on_delete=models.PROTECT)
    # Route from our own module
    route = models.ForeignKey(SchoolRoute,on_delete=models.PROTECT)
    trip_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_PLANNED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Table: skytron_api_schoolbustrip
        indexes = [models.Index(fields=["school", "trip_date"])]

    def __str__(self):
        return f"{self.school.name} - {self.trip_date}"


# =====================================================
# Student Attendance
# =====================================================
# Table: skytron_api_studentattendance
class StudentAttendance(models.Model):
    trip = models.ForeignKey(SchoolBusTrip,on_delete=models.CASCADE,related_name="attendances")
    student = models.ForeignKey(Student,on_delete=models.CASCADE,related_name="attendances")
    # Stops from our own module
    pickup_stop = models.ForeignKey(SchoolBusStop,null=True, blank=True,on_delete=models.SET_NULL,related_name="pickup_attendances")
    drop_stop = models.ForeignKey(SchoolBusStop,null=True, blank=True,on_delete=models.SET_NULL,related_name="drop_attendances")
    pickup_status = models.BooleanField(default=False)
    drop_status = models.BooleanField(default=False)
    pickup_time = models.DateTimeField(null=True, blank=True)
    drop_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_present = models.BooleanField(default=False)

    class Meta:
        # Table: skytron_api_studentattendance
        unique_together = ("trip", "student")
        indexes = [
            models.Index(fields=["trip"]),
            models.Index(fields=["student"]),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.trip.trip_date}"


# =====================================================
# School Bus Tag
# =====================================================
# Table: skytron_api_schoolbustag
class SchoolBusTag(models.Model):
    school = models.ForeignKey(School,on_delete=models.CASCADE,related_name="bus_tags")
    # Bus from Skytron
    bus = models.ForeignKey('DeviceTag',on_delete=models.PROTECT,related_name="school_tags")
    is_active = models.BooleanField(default=True)
    tagged_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending"
    )
    otp = models.CharField(max_length=128, blank=True)
    otp_verified = models.BooleanField(default=False)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)
    remarks = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="requested_bus_tags"
    )
    requested_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_bus_tags"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        # Table: skytron_api_schoolbustag
        constraints = [
        models.UniqueConstraint(
                fields=["school", "bus"],
                condition=models.Q(status__in=["pending", "approved"]),
                name="unique_active_tag_per_school_bus"
            )
        ]
        indexes = [models.Index(fields=["school", "is_active"])]

    def __str__(self):
        return f"{self.school.name} → {self.bus}"


# =====================================================
# Route Bus Assignment
# =====================================================
# Table: skytron_api_routebusassignment
class RouteBusAssignment(models.Model):
    
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        default="active"
    )


    
    school = models.ForeignKey(School,on_delete=models.CASCADE,related_name="route_bus_assignments")
    # Route from our own module
    route = models.ForeignKey(SchoolRoute,on_delete=models.PROTECT,related_name="bus_assignments")
    # Bus from Skytron
    bus = models.ForeignKey('DeviceTag',on_delete=models.PROTECT,related_name="route_assignments")
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Table: skytron_api_routebusassignment
        unique_together = ("school", "bus")
        indexes = [models.Index(fields=["school", "route", "is_active"])]

    def __str__(self):
        return f"{self.bus} → {self.route}"


# =====================================================
# Bus Alert
# =====================================================
# Table: skytron_api_busalert
class BusAlert(models.Model):
    ALERT_OVERSPEED = "overspeed"
    ALERT_HARSH_BRAKE = "harsh_braking"
    ALERT_HARSH_ACCEL = "harsh_acceleration"
    ALERT_ROUTE_DEVIATION = "route_deviation"
    ALERT_SOS = "sos"

    ALERT_CHOICES = [
        (ALERT_OVERSPEED, "Overspeed"),
        (ALERT_HARSH_BRAKE, "Harsh Braking"),
        (ALERT_HARSH_ACCEL, "Harsh Acceleration"),
        (ALERT_ROUTE_DEVIATION, "Route Deviation"),
        (ALERT_SOS, "SOS"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE)
    # Bus from Skytron
    bus = models.ForeignKey('DeviceTag', on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="created_alerts")
    alert_type = models.CharField(max_length=50, choices=ALERT_CHOICES)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6,null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Table: skytron_api_busalert
        indexes = [models.Index(fields=["school", "alert_type"])]













####################################################################################
######################## Permit Enforcement ########################################
####################################################################################

class PermitCondition(models.Model):

    STATUS_CREATED    = 'created'
    STATUS_ACTIVE     = 'active'
    STATUS_DEACTIVE   = 'deactive'

    STATUS_CHOICES = [
        (STATUS_CREATED,  'Created'),
        (STATUS_ACTIVE,   'Active'),
        (STATUS_DEACTIVE, 'Deactive'),
    ]

    # All alert types from AlertsLog
    PERMIT_VIOLATION_CHOICES = [
        ('Route', 'Route'),
        ('Geofence', 'Geofence'),
        ('Idling', 'Idling'),
        ('OfflineDevice', 'OfflineDevice'),
        ('Overtime', 'Overtime'), 
        ('UnauthorizedStop', 'UnauthorizedStop'), 
        ('UnauthorizedSkip', 'UnauthorizedSkip'), 
        ('NetworkLoss', 'NetworkLoss'), 
        ('GPSLoss', 'GPSLoss'), 
        ('Permit', 'Permit'), 
        ('Permit_3day', 'Permit_3day'), 
        ('Route_overspeed', 'Route_overspeed'),
        ('state_border_cross', 'state_border_cross'),
        ('district_border_cross', 'district_border_cross'),
        ('city_border_cross', 'city_border_cross'),
        ('Incident', 'Incident'), 
        ('Em', 'Em'), 
        ('EmPublicApp', 'EmPublicApp'), 
        ('EmRegisteredApp', 'EmRegisteredApp'), 
        ('EmMonitorTripSOS', 'EmMonitorTripSOS'), 
        ('EmMonitorTripInvalidPw', 'EmMonitorTripInvalidPw'), 
        ('EmMonitorTripBLEDisconnect', 'EmMonitorTripBLEDisconnect'), 
        ('EmMonitorTripDeviated', 'EmMonitorTripDeviated'), 
        ('Eng', 'Eng'), 
        ('OverSpeed', 'OverSpeed'), 
        ('LowIntBat', 'LowIntBat'), 
        ('LowExtBat', 'LowExtBat'), 
        ('ExtBatDiscnt', 'ExtBatDiscnt'), 
        ('BoxTemp', 'BoxTemp'), 
        ('EmTemp', 'EmTemp'), 
        ('Tilt', 'Tilt'), 
        ('HarshBreak', 'HarshBreak'),
        ('HarshTurn', 'HarshTurn'),
        ('HarshAcceleration', 'HarshAcceleration'), 
        ('UnauthorizedParking', 'UnauthorizedParking'),
        ('Prohibited_Area', 'Prohibited_Area'),
    ]
    
    permit_name = models.CharField(max_length=255)
    vehicle_category = models.ForeignKey('Settings_VehicleCategory',on_delete=models.PROTECT, related_name='permit_conditions')
    violation_type = models.CharField(max_length=250,choices=PERMIT_VIOLATION_CHOICES)
    rule_details = models.TextField(help_text="Rule details as per Motor Vehicle Act")
    penalty = models.CharField(max_length=250, help_text="Penalty details as per Motor Vehicle Act")
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    challan_code= models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_CREATED)

    activation_datetime = models.DateTimeField(null=True, blank=True)
    deactivation_datetime = models.DateTimeField(null=True, blank=True)
    created_datetime = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User',on_delete=models.PROTECT,related_name='permit_conditions_created')

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['violation_type']),
            models.Index(fields=['vehicle_category']),
            models.Index(fields=['activation_datetime', 'deactivation_datetime']),
        ]

    def __str__(self):
        return f"{self.permit_name} ({self.status})"


class ViolationReport(models.Model):
    """
    generated when AlertsLog matches an active PermitCondition.
    """
    permit_condition  = models.ForeignKey(PermitCondition,on_delete=models.PROTECT,related_name='violations')
    alert_log = models.ForeignKey('AlertsLog',on_delete=models.PROTECT, related_name='violations')
    device_tag = models.ForeignKey('DeviceTag',on_delete=models.PROTECT,related_name='violations')
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2)
    violation_datetime = models.DateTimeField()

    state = models.ForeignKey('Settings_State',on_delete=models.SET_NULL,null=True, blank=True)
    district  = models.ForeignKey('Settings_District',on_delete=models.SET_NULL,null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['device_tag']),
            models.Index(fields=['violation_datetime']),
            models.Index(fields=['permit_condition']),
            models.Index(fields=['state']),
            models.Index(fields=['district']),
        ]

    def __str__(self):
        return f"{self.device_tag.vehicle_reg_no} - {self.permit_condition.permit_name}"


@receiver(post_save, sender=AlertsLog)
def auto_generate_violation(sender, instance, created, **kwargs):
    if not created:
        return

    now = instance.timestamp

    try:
        conditions = PermitCondition.objects.filter(
            status=PermitCondition.STATUS_ACTIVE,
            violation_type=instance.type,
            vehicle_category=instance.deviceTag.category,
            activation_datetime__lte=now,
            deactivation_datetime__gte=now,
        )
    except Exception as e:
        print(f"[ViolationSignal] Error fetching conditions: {e}", flush=True)
        return

    if not conditions.exists():
        return

    for condition in conditions:

        # Avoid duplicate
        if ViolationReport.objects.filter(
            permit_condition=condition,
            alert_log=instance
        ).exists():
            continue

        # imei from DeviceTag → DeviceStock
        imei = ''
        try:
            imei = instance.deviceTag.device.imei
        except Exception:
            pass

        district = getattr(instance.deviceTag, 'district', None)

        ViolationReport.objects.create(
            permit_condition=condition,
            alert_log=instance,
            device_tag=instance.deviceTag,
            penalty_amount=condition.penalty_amount,
            violation_datetime=instance.timestamp,
            state=instance.state,
            district=district,
        )
        print(
            f"[ViolationSignal] Violation created for "
            f"{instance.deviceTag.vehicle_reg_no} "
            f"under condition '{condition.permit_name}'",
            flush=True
        )
        
        
        
        
####################################################################################
######################## Passenger Information System ##############################
####################################################################################


class PublicBusStop(models.Model):
    """
    Bus stops for public bus routes.
    """
    STATUS_ACTIVE      = 'active'
    STATUS_DEACTIVATED = 'deactivated'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,      'Active'),
        (STATUS_DEACTIVATED, 'Deactivated'),
    ]

    name  = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    latitude  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    state = models.ForeignKey('Settings_State',on_delete=models.PROTECT,related_name='public_bus_stops')
    district = models.ForeignKey('Settings_District',on_delete=models.PROTECT,related_name='public_bus_stops')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    # Activation / deactivation tracking
    last_activation_date   = models.DateTimeField(null=True, blank=True)
    last_deactivation_date = models.DateTimeField(null=True, blank=True)
    deactivation_date      = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey('User',on_delete=models.PROTECT,related_name='public_bus_stops_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['state', 'status']),
            models.Index(fields=['district', 'status']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return self.name


class PublicBusRoute(models.Model):
    """
    A bus route with source, destination and intermediate stops.
    
    """
    STATUS_ACTIVE      = 'active'
    STATUS_DEACTIVATED = 'deactivated'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,      'Active'),
        (STATUS_DEACTIVATED, 'Deactivated'),
    ]

    name = models.CharField(max_length=255)
    route_number = models.CharField(max_length=50, unique=True)
    route_path = models.JSONField(default=list, blank=True, help_text="List of lat/lng coordinates defining the route path")

    source_stop  = models.ForeignKey(PublicBusStop,on_delete=models.PROTECT,related_name='routes_as_source')
    destination_stop = models.ForeignKey(PublicBusStop,on_delete=models.PROTECT,related_name='routes_as_destination')

    # Intermediate stops via through model PublicRouteStop
    stops = models.ManyToManyField(PublicBusStop,through='PublicRouteStop',related_name='routes',blank=True)

    state    = models.ForeignKey('Settings_State',on_delete=models.PROTECT,related_name='public_bus_routes')
    district = models.ForeignKey('Settings_District',on_delete=models.SET_NULL,null=True, blank=True,related_name='public_bus_routes')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    last_activation_date   = models.DateTimeField(null=True, blank=True)
    last_deactivation_date = models.DateTimeField(null=True, blank=True)
    deactivation_date      = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey('User',on_delete=models.PROTECT,related_name='public_bus_routes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['state', 'status']),
            models.Index(fields=['route_number']),
        ]

    def __str__(self):
        return f"{self.route_number} - {self.name}"


class PublicRouteStop(models.Model):
    """
    Through model for PublicBusRoute ↔ PublicBusStop.
    Each stop on a route has:
    - order           : position in route (1, 2, 3 ...)
    - arrival_time_min  : minutes from route start to arrive at this stop
    - halt_time_min     : how many minutes bus halts at this stop
    travel_time to next stop is derived:
    arrival_time_min(next) - arrival_time_min(current) - halt_time_min(current)
    """
    route = models.ForeignKey( PublicBusRoute, on_delete=models.CASCADE, related_name='route_stops')
    stop  = models.ForeignKey(PublicBusStop,on_delete=models.PROTECT,related_name='route_stops')

    order = models.PositiveIntegerField()
    arrival_time_min = models.PositiveIntegerField(default=0,help_text="Minutes from route start time to arrive at this stop")
    halt_time_min = models.PositiveIntegerField(default=0,help_text="Minutes bus halts at this stop")
  

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['route', 'order', 'stop']),
        ]

    def __str__(self):
        return f"{self.route.route_number} → Stop {self.order}: {self.stop.name}"


class BusSchedule(models.Model):
    """
    A bus (DeviceTag) assigned to a route on a specific date/time.

    Once started → actual_start_time is filled
    Once completed → actual_end_time is filled

    Status flow:
    created | → started → completed
            | → canceled
    """
    STATUS_CREATED   = 'created'
    STATUS_CANCELED  = 'canceled'
    STATUS_STARTED   = 'started'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_CREATED,   'Created'),
        (STATUS_CANCELED,  'Canceled'),
        (STATUS_STARTED,   'Started'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    SERVICE_TYPE_CHOICES = [
        ('Express',  'Express'),
        ('Ordinary', 'Ordinary'),
        ('AC',       'AC'),
        ('City_Bus',   'City Bus'),
        ('Sleeper',  'Sleeper'),
        ('Deluxe',   'Deluxe'),
    ]

    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES)
    route = models.ForeignKey(PublicBusRoute,on_delete=models.PROTECT,related_name='schedules')
    bus = models.ForeignKey('DeviceTag',on_delete=models.PROTECT,related_name='bus_schedules')

    # Scheduled start datetime (entered by admin)
    start_datetime = models.DateTimeField()

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_CREATED)

    # Actual times — filled when owner updates trip start/end
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time   = models.DateTimeField(null=True, blank=True)

    created_by  = models.ForeignKey('User',on_delete=models.PROTECT,related_name='bus_schedules_created')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['route', 'start_datetime']),
            models.Index(fields=['bus',   'start_datetime']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.bus.vehicle_reg_no} on {self.route.route_number} at {self.start_datetime}"


class BusScheduleStopETA(models.Model):
    """
    Auto-calculated ETA for each stop on a BusSchedule.
    Generated when schedule is created, based on:
      scheduled_arrival  = start_datetime + arrival_time_min (from PublicRouteStop)
      scheduled_departure = scheduled_arrival + halt_time_min

    actual_arrival and actual_departure are filled in real time
    as bus reaches each stop.
    """
    schedule   = models.ForeignKey(BusSchedule,on_delete=models.CASCADE,related_name='stop_etas')
    route_stop = models.ForeignKey(PublicRouteStop,on_delete=models.PROTECT,related_name='stop_etas')

    order = models.PositiveIntegerField()

    # Calculated at schedule creation time
    scheduled_arrival   = models.DateTimeField()
    scheduled_departure = models.DateTimeField()

    # Filled in real time
    actual_arrival   = models.DateTimeField(null=True, blank=True)
    actual_departure = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('schedule', 'route_stop')
        ordering        = ['order']
        indexes = [
            models.Index(fields=['schedule', 'order']),
        ]

    def __str__(self):
        return f"Schedule {self.schedule_id} → Stop {self.order}"


# ─── Dynamic RBAC ────────────────────────────────────────────────────────────


class UserRoleType(models.Model):
    """
    Registry of all user role types — both the built-in primary roles and any
    custom roles a super-admin creates.  The `code` value must match the string
    stored in User.role so the two systems stay in sync during the incremental
    migration.
    """
    objects = SafeCreateManager()

    BUILTIN_CODES = [
        'superadmin', 'stateadmin', 'devicemanufacture', 'dealer', 'owner',
        'esimprovider', 'filment', 'sosadmin', 'teamleader', 'sosexecutive',
        'schooladmin', 'parentuser', 'dtorto',
    ]

    code         = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description  = models.TextField(blank=True, null=True)
    is_builtin   = models.BooleanField(default=False)
    is_active    = models.BooleanField(default=True)
    created_by   = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_role_types',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Role Type'
        verbose_name_plural = 'User Role Types'
        ordering = ['display_name']

    def __str__(self):
        return f"{self.display_name} ({self.code})"


class RolePermissionConfig(models.Model):
    """
    Maps a UserRoleType to a system module with fine-grained permission flags
    and a data-hierarchy scope tier.

    One row = one role's complete access policy for one module.
    Super-admin can edit any row at runtime; the RBAC engine caches results in
    Redis and invalidates on save/delete via the post_save signal below.
    """
    objects = SafeCreateManager()

    DATA_SCOPE_CHOICES = [
        ('national',     'National — all data'),
        ('state',        'State — assigned state(s) only'),
        ('manufacturer', 'Manufacturer — own company\'s devices only'),
        ('district',     'District — assigned district(s) only'),
        ('dealer',       'Dealer — own handled devices only'),
        ('owner',        'Owner — own vehicles only'),
        ('self',         'Self — own records only'),
        ('none',         'None — no data access'),
    ]

    MODULE_CHOICES = [
        # ── Legacy / API-enforcement modules (kept for @require_permission) ───
        ('dashboard',               'Dashboard'),
        ('gps_tracking',            'GPS Live Tracking'),
        ('gps_history',             'GPS History'),
        ('gps_clustering',          'GPS Cluster / Grid'),
        ('device_management',       'Device Model Management'),
        ('device_stock',            'Device Stock & Inventory'),
        ('vehicle_tagging',         'Vehicle Tagging'),
        ('driver_management',       'Driver Management'),
        ('owner_management',        'Vehicle Owner Management'),
        ('manufacturer_management', 'Manufacturer Management'),
        ('dealer_management',       'Dealer Management'),
        ('stateadmin_management',   'State Admin Management'),
        ('esim_management',         'eSIM Provider Management'),
        ('emergency_management',    'Emergency (SOS) Management'),
        ('emergency_teams',         'Emergency Teams'),
        ('poi_management',          'Points of Interest'),
        ('route_management',        'Route Management'),
        ('alerts',                  'Alerts & Notifications'),
        ('reports',                 'Reports'),
        ('user_management',         'User Management'),
        ('notice_management',       'Notices'),
        ('trip_management',         'Trip Management'),
        ('settings_management',     'System Settings'),
        ('complaint',               'Complaint Management'),

        # ── UI Navigation modules ─────────────────────────────────────────────

        # Dashboard variants
        ('dashboard_north',             'North Dashboard'),
        ('dashboard_central',           'Central Dashboard'),

        # School Bus System
        ('sbs_dashboard',               'School Bus System — Dashboard'),
        ('sbs_bus_tagging',             'School Bus System — Bus Tagging'),
        ('sbs_route_mgmt',              'School Bus System — Route Management'),
        ('sbs_bus_assignment',          'School Bus System — Bus Assignment'),
        ('sbs_profile_mgmt',            'School Bus System — Profile Management'),
        ('sbs_school_reports',          'School Bus System — School Reports'),
        ('sbs_create_school',           'School Bus System — Create School'),
        ('sbs_approve_school',          'School Bus System — Approve School'),
        ('sbs_bus_tracking',            'School Bus System — School Bus Tracking'),
        ('sbs_create_trip',             'School Bus System — Create Trip'),
        ('sbs_parent_tracking',         'School Bus System — Parent Tracking'),

        # Test Agency
        ('ta_create_agency',            'Test Agency — Create Agency Details'),
        ('ta_agency_list',              'Test Agency — Agency Details List'),
        ('ta_create_user',              'Test Agency — Create Agency User'),
        ('ta_user_list',                'Test Agency — Agency User List'),
        ('ta_view_models',              'Test Agency — View Assigned Models'),

        # Create New (user provisioning)
        ('cn_state_admin',              'Create New — State Admin'),
        ('cn_m2m_provider',             'Create New — M2M Service Provider'),
        ('cn_manufacturer',             'Create New — Manufacturer'),
        ('cn_sos_admin',                'Create New — SOS Admin'),
        ('cn_system_admin',             'Create New — System Admin'),
        ('cn_dto',                      'Create New — DTO'),
        ('cn_dealer',                   'Create New — Dealer Account'),
        ('cn_sos_user',                 'Create New — SOS User'),
        ('cn_vehicle_owner',            'Create New — Vehicle Owner'),

        # M2M
        ('m2m_registration',            'M2M Registration Requests'),
        ('m2m_pending',                 'M2M — Pending Activation Requests'),
        ('m2m_rejected',                'M2M — Rejected Requests'),
        ('m2m_accepted',                'M2M — Accepted Requests'),

        # Manufacturer / AIS-140 Requests
        ('mfr_vlt_requests',            'Vehicle Manufacturer Requests'),
        ('mfr_ais140_requests',         'AIS-140 Manufacturer Requests'),

        # Technical Onboarding
        ('tech_onboarding',             'Technical Onboarding Requests'),
        ('tech_onboarding_final',       'Technical Onboarding — Final Approval'),
        ('mfr_onboarding_new',          'Manufacturer Onboarding — New Request'),
        ('mfr_onboarding_list',         'Manufacturer Onboarding — My Requests'),

        # Tracking / Playback / Viewer
        ('route_fixing',                'Route Fixing'),
        ('live_tracking',               'Live Tracking'),
        ('history_playback',            'History Playback'),
        ('trip_viewer',                 'Trip Viewer'),
        ('trip_monitor',                'Trip Monitor'),

        # VLTD Approval
        ('vltd_pending_model',          'VLTD — Pending Model Approval'),
        ('vltd_pending_cop',            'VLTD — Pending COP'),
        ('vltd_approved_models',        'VLTD — Approved Models'),
        ('vltd_approved_cops',          'VLTD — Approved COPs'),

        # Whitelist & KYC
        ('wkyc_requests',               'Whitelist & KYC — Whitelist Requests'),
        ('wkyc_device_dashboard',       'Whitelist & KYC — Device Dashboard'),

        # POI Viewer
        ('poi_viewer',                  'POI Viewer'),

        # Report sub-modules
        ('report_sos',                  'Report — SOS'),
        ('report_notices',              'Report — Notices'),
        ('report_users',                'Report — Users'),
        ('report_state_admin',          'Report — State Admin'),
        ('report_manufacturer',         'Report — Manufacturer'),
        ('report_sos_admin',            'Report — SOS Admin'),
        ('report_m2m_provider',         'Report — M2M Provider'),
        ('report_dealers',              'Report — Dealers'),
        ('report_vehicle_owner',        'Report — Vehicle Owner'),
        ('report_dto',                  'Report — DTO User List'),
        ('report_gps_log',              'Report — GPS Data Log'),
        ('report_activation_log',       'Report — Activation Log'),
        ('report_emergency_data',       'Report — Emergency Data Logs'),
        ('report_health_packet',        'Report — Health Packet Log'),
        ('report_event_data',           'Report — Event Data Log'),
        ('report_activated_device',     'Report — Activated Device'),
        ('report_alert',                'Report — Alert'),
        ('report_poi',                  'Report — POI'),
        ('report_incident',             'Report — Incident'),
        ('report_device_health',        'Report — Device Health'),
        ('report_user_stats',           'Report — User Statistics'),
        ('report_violation',            'Report — Violation'),
        ('report_sos_users',            'Report — SOS Users'),
        ('report_sos_call_list',        'Report — SOS Call List'),
        ('report_stock',                'Report — Stock'),
        ('report_fitment',              'Report — Fitment'),
        ('report_device',               'Report — Device'),

        # Settings sub-modules
        ('settings_notice',             'Settings — Notice'),
        ('settings_send_command',       'Settings — Send Command'),
        ('settings_vehicle_type',       'Settings — Vehicle Type'),
        ('settings_vehicle_category',   'Settings — Vehicle Category Code'),
        ('settings_alert_notif',        'Settings — Alert Notification Delivery Mode'),
        ('settings_state_district',     'Settings — State & District'),
        ('settings_ota_firmware',       'Settings — OTA & Firmware'),
        ('settings_archive_restore',    'Settings — Archive & Restore'),
        ('settings_ip',                 'Settings — IP Settings'),
        ('settings_login',              'Settings — Login Settings'),
        ('settings_permit_cond',        'Settings — Permit Conditions'),
        ('settings_custom_alerts',      'Settings — Custom Alerts'),

        # Passenger Info System
        ('pis_bus_stops',               'PIS — Bus Stops'),
        ('pis_bus_routes',              'PIS — Bus Routes'),
        ('pis_bus_schedules',           'PIS — Bus Schedules'),

        # State Transport Analytics
        ('sta_trip_analysis',           'Analytics — Trip Analysis'),
        ('sta_driving_patterns',        'Analytics — Driving Pattern Alerts'),
        ('sta_vehicle_alerts',          'Analytics — Vehicle Alerts Count'),
        ('sta_pis_summary',             'Analytics — PIS Summary'),
        ('sta_operational',             'Analytics — Operational Analytics'),
        ('sta_comparative',             'Analytics — Comparative Analysis'),
        ('sta_resource_perf',           'Analytics — Resource Performance'),

        # Custom User Module
        ('cum_custom_roles',            'Custom User — Role Management'),
        ('cum_feature_perms',           'Custom User — Feature Permissions'),
        ('cum_user_mgmt',               'Custom User — User Management'),

        # Complaint Tickets (UI sub-menu)
        ('ct_my_dashboard',             'Complaints — My Ticket Dashboard'),
        ('ct_create',                   'Complaints — Create Ticket'),
        ('ct_all_tickets',              'Complaints — All Tickets'),
        ('ct_escalated',                'Complaints — Escalated Tickets'),

        # Device Model (manufacturer)
        ('dm_create_model',             'Device — Create Model'),
        ('dm_tac_cop',                  'Device — TAC/COP Extension'),

        # Device Stock (manufacturer)
        ('ds_individual',               'Stock — Individual'),
        ('ds_bulk',                     'Stock — Bulk'),
        ('ds_assign',                   'Stock — Assign'),

        # Dealer-specific
        ('dealer_m2m_status',           'Dealer — Check M2M Status'),
        ('dealer_request_m2m',          'Dealer — Request M2M Activation'),
        ('dealer_tag_device',           'Dealer — Tag Device to Vehicle'),
        ('dealer_untagged',             'Dealer — UnTagged Devices'),
        ('dealer_download_cert',        'Dealer — Download Certificate'),

        # EM Team (SOS Admin)
        ('em_team_create',              'EM Team — Create'),
        ('em_team_list',                'EM Team — List'),

        # SOS
        ('sos_call_list',               'SOS Call List'),

        # OTA Command Management
        ('ota_command_definition',      'OTA — Command Definitions'),
        ('ota_command_history',         'OTA — Command History & Send Command'),
        ('ota_value_suggestion',        'OTA — Value Suggestions'),
    ]

    role   = models.ForeignKey(
        UserRoleType, on_delete=models.CASCADE,
        related_name='module_permissions',
    )
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)

    can_view   = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_filter = models.BooleanField(default=False)
    show_in_menu = models.BooleanField(default=False)

    data_scope = models.CharField(
        max_length=20, choices=DATA_SCOPE_CHOICES, default='none',
    )

    updated_by = models.ForeignKey(
        'User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='rbac_configs_updated',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('role', 'module')]
        verbose_name = 'Role Permission Config'
        verbose_name_plural = 'Role Permission Configs'
        ordering = ['role', 'module']

    def __str__(self):
        return f"{self.role.code} → {self.module}"


@receiver([post_save, post_delete], sender=RolePermissionConfig,
          dispatch_uid='rbac_cache_invalidate')
def _invalidate_rbac_cache(sender, instance, **kwargs):
    """Clear the Redis permission cache whenever a config row changes."""
    try:
        from django.core.cache import cache
        cache.delete(f"rbac:role:{instance.role.code}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Complaint Management
# ---------------------------------------------------------------------------

class ComplaintTicket(models.Model):
    objects = SafeCreateManager()

    STATUS_CREATED   = 'created'
    STATUS_IN_REVIEW = 'in_review'
    STATUS_PENDING   = 'pending'
    STATUS_CLOSED    = 'closed'
    STATUS_CANCELED  = 'canceled'

    STATUS_CHOICES = [
        (STATUS_CREATED,   'Created'),
        (STATUS_IN_REVIEW, 'In Review'),
        (STATUS_PENDING,   'Pending'),
        (STATUS_CLOSED,    'Closed'),
        (STATUS_CANCELED,  'Canceled'),
    ]

    SOURCE_CHOICES = [
        ('helpdesk_call',  'HelpDesk Call'),
        ('helpdesk_email', 'HelpDesk Email'),
        ('public_app',     'Public App'),
    ]

    ESCALATION_CHOICES = [
        ('teamlead',     'Team Lead'),
        ('sosadmin',     'SOS Admin'),
        ('manufacturer', 'Manufacturer'),
    ]

    ticket_ref       = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    applicant_name   = models.CharField(max_length=255)
    applicant_phone  = models.CharField(max_length=25)
    applicant_email  = models.EmailField(blank=True, null=True)
    title            = models.CharField(max_length=500)
    details          = models.TextField()
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED, db_index=True)
    source           = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='public_app')
    escalated_to     = models.CharField(
        max_length=20, choices=ESCALATION_CHOICES, null=True, blank=True, db_index=True,
    )
    escalated_to_manufacturer = models.ForeignKey(
        'Manufacturer', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='escalated_complaint_tickets',
    )
    device_stock     = models.ForeignKey(
        'DeviceStock', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='complaint_tickets',
    )
    solution         = models.TextField(blank=True, null=True)
    final_report_file = models.CharField(max_length=500, blank=True, null=True)
    created_by       = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_complaint_tickets',
    )
    entry_date  = models.DateField(auto_now_add=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Complaint Ticket'
        verbose_name_plural = 'Complaint Tickets'

    def __str__(self):
        return f"{self.ticket_ref} – {self.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_ref:
            self.ticket_ref = self._generate_ref()
        super().save(*args, **kwargs)

    def _generate_ref(self):
        from django.utils import timezone as tz
        year = tz.now().year
        count = ComplaintTicket.objects.filter(created_at__year=year).count()
        return f"TKT-{year}-{str(count + 1).zfill(5)}"


class TicketAttachment(models.Model):
    objects = SafeCreateManager()

    ticket      = models.ForeignKey(ComplaintTicket, on_delete=models.CASCADE, related_name='attachments')
    file_path   = models.CharField(max_length=500)
    file_name   = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_attachments',
    )

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.ticket.ticket_ref} – {self.file_name}"


class TicketActivity(models.Model):
    objects = SafeCreateManager()

    ACTION_CREATED       = 'created'
    ACTION_STATUS_CHANGE = 'status_change'
    ACTION_COMMENT       = 'comment'
    ACTION_FINAL_REPORT  = 'final_report'
    ACTION_ATTACHMENT    = 'attachment'
    ACTION_ESCALATION    = 'escalation'

    ACTION_CHOICES = [
        (ACTION_CREATED,       'Ticket Created'),
        (ACTION_STATUS_CHANGE, 'Status Changed'),
        (ACTION_COMMENT,       'Comment Added'),
        (ACTION_FINAL_REPORT,  'Final Report Submitted'),
        (ACTION_ATTACHMENT,    'Attachment Added'),
        (ACTION_ESCALATION,    'Ticket Escalated'),
    ]

    ticket     = models.ForeignKey(ComplaintTicket, on_delete=models.CASCADE, related_name='activities')
    actor      = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_activities',
    )
    actor_name  = models.CharField(max_length=255, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    old_value   = models.CharField(max_length=255, blank=True, null=True)
    new_value   = models.CharField(max_length=255, blank=True, null=True)
    comment     = models.TextField(blank=True, null=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.ticket.ticket_ref} – {self.action_type} at {self.timestamp}"


# ---------------------------------------------------------------------------
# Whitelist Request Management
# ---------------------------------------------------------------------------

class WhitelistRequest(models.Model):
    REQUEST_TYPE_CHOICES = [
        ('add', 'Add Whitelist'),
        ('remove', 'Remove Whitelist'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    REQUESTER_TYPE_CHOICES = [
        ('manufacturer', 'Manufacturer'),
        ('dealer', 'Dealer'),
    ]

    request_type   = models.CharField(max_length=10, choices=REQUEST_TYPE_CHOICES)
    device_stocks  = models.ManyToManyField(DeviceStock, related_name='whitelist_requests')
    esim_provider  = models.ForeignKey(eSimProvider, on_delete=models.CASCADE, related_name='whitelist_requests_received')
    requested_by   = models.ForeignKey('User', on_delete=models.CASCADE, related_name='whitelist_requests_sent')
    requester_type = models.CharField(max_length=15, choices=REQUESTER_TYPE_CHOICES)
    manufacturer   = models.ForeignKey(Manufacturer, on_delete=models.SET_NULL, null=True, blank=True, related_name='whitelist_requests')
    dealer         = models.ForeignKey(Dealer, on_delete=models.SET_NULL, null=True, blank=True, related_name='whitelist_requests')
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requester_remarks = models.TextField(blank=True, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"WhitelistRequest #{self.pk} ({self.request_type}) – {self.status}"


class WhitelistEntry(models.Model):
    WHITELIST_TYPE_CHOICES = [
        ('ip',    'IP Address'),
        ('url',   'URL'),
        ('phone', 'Phone Number'),
        ('apn',   'APN'),
    ]

    request        = models.ForeignKey(WhitelistRequest, on_delete=models.CASCADE, related_name='entries')
    whitelist_type = models.CharField(max_length=10, choices=WHITELIST_TYPE_CHOICES)
    value          = models.CharField(max_length=500)

    def __str__(self):
        return f"{self.whitelist_type}: {self.value}"


class WhitelistRequestReview(models.Model):
    ACTION_CHOICES = [
        ('approved', 'Approved'),
        ('denied',   'Denied'),
    ]

    request     = models.OneToOneField(WhitelistRequest, on_delete=models.CASCADE, related_name='review')
    reviewed_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='whitelist_reviews_given')
    esim_provider = models.ForeignKey(eSimProvider, on_delete=models.CASCADE, related_name='whitelist_reviews')
    action      = models.CharField(max_length=10, choices=ACTION_CHOICES)
    reason      = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for Request #{self.request_id}: {self.action}"


class ActiveWhitelist(models.Model):
    WHITELIST_TYPE_CHOICES = [
        ('ip',    'IP Address'),
        ('url',   'URL'),
        ('phone', 'Phone Number'),
        ('apn',   'APN'),
    ]

    device_stock    = models.ForeignKey(DeviceStock, on_delete=models.CASCADE, related_name='active_whitelists')
    esim_provider   = models.ForeignKey(eSimProvider, on_delete=models.CASCADE, related_name='active_whitelists')
    whitelist_type  = models.CharField(max_length=10, choices=WHITELIST_TYPE_CHOICES)
    value           = models.CharField(max_length=500)
    source_request  = models.ForeignKey(WhitelistRequest, on_delete=models.SET_NULL, null=True, related_name='activated_entries')
    is_active       = models.BooleanField(default=True)
    activated_at    = models.DateTimeField(auto_now_add=True)
    deactivated_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-activated_at']

    def __str__(self):
        state = 'active' if self.is_active else 'inactive'
        return f"ActiveWhitelist [{state}]: {self.whitelist_type}={self.value} on device {self.device_stock_id}"


class DeviceActivationLog(models.Model):
    """
    Immutable audit trail of every esim_status / stock_status change on a device.
    DeviceStock stores only the current state; this model stores the full history
    so users can see activation dates, deactivation dates, etc.
    """
    device_stock  = models.ForeignKey(DeviceStock, on_delete=models.CASCADE, related_name='activation_logs')
    esim_provider = models.ForeignKey(eSimProvider, on_delete=models.SET_NULL, null=True, blank=True, related_name='activation_logs')
    status        = models.CharField(max_length=55)
    changed_by    = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='activation_log_entries')
    changed_at    = models.DateTimeField(auto_now_add=True)
    remarks       = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"ActivationLog #{self.pk}: device {self.device_stock_id} → {self.status}"



    
class Favorite(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
        db_index=True,
    )

    bus = models.ForeignKey(
        "skytron_api.DeviceTag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="favorited_by",
    )

    route = models.ForeignKey(
        "skytron_api.PublicBusRoute",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="favorited_by",
    )

    bus_stop = models.ForeignKey(
        "skytron_api.PublicBusStop",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="favorited_by",
    )

    label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional nickname for this favorite",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "favorites_favorite"

        ordering = ["-created_at"]

        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"

        constraints = [
            CheckConstraint(
                check=(
                    Q(bus__isnull=False) |
                    Q(route__isnull=False) |
                    Q(bus_stop__isnull=False)
                ),
                name="favorite_at_least_one_reference"
            ),

            UniqueConstraint(
                fields=["user", "bus"],
                condition=Q(bus__isnull=False),
                name="unique_user_bus_favorite"
            ),

            UniqueConstraint(
                fields=["user", "route"],
                condition=Q(route__isnull=False),
                name="unique_user_route_favorite"
            ),

            UniqueConstraint(
                fields=["user", "bus_stop"],
                condition=Q(bus_stop__isnull=False),
                name="unique_user_busstop_favorite"
            ),
        ]

        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["bus"]),
            models.Index(fields=["route"]),
            models.Index(fields=["bus_stop"]),
        ]

    def __str__(self):
        return (
            f"Favorite("
            f"user={self.user_id}, "
            f"bus={self.bus_id}, "
            f"route={self.route_id}, "
            f"bus_stop={self.bus_stop_id}"
            f")"
        )

    @property
    def is_orphaned(self):
        return (
            self.bus is None and
            self.route is None and
            self.bus_stop is None
        )





 

####################################################################################
######################## Custom Alert Rules ########################################
####################################################################################
 
 
class CustomAlertRule(models.Model):
    """
    An alert rule defined by a superadmin or state admin.
    A rule can have up to 4 subrules combined with AND / OR logic.
 
    Evaluation:
    - Triggered by post_save on GPSData (see signal at bottom of this section).
    - Rule-level time window (time_from / time_to): if set, the rule only
      evaluates when the GPS packet's local time falls within the window.
    - Scope: superadmin rules apply globally; state admin rules are scoped
      to their state (matched via GPSData.device_tag.district.state).
    """
 
    SUBRULE_LOGIC_AND = 'AND'
    SUBRULE_LOGIC_OR  = 'OR'
    SUBRULE_LOGIC_CHOICES = [
        (SUBRULE_LOGIC_AND, 'AND — all subrules must match'),
        (SUBRULE_LOGIC_OR,  'OR  — any subrule must match'),
    ]
 
    STATUS_ACTIVE   = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE,   'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
 
    name           = models.CharField(max_length=255)
    description    = models.TextField(blank=True)
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    subrule_logic  = models.CharField(max_length=3, choices=SUBRULE_LOGIC_CHOICES, default=SUBRULE_LOGIC_AND)
 
    # Optional rule-level time window (IST, 24-hour)
    time_from = models.TimeField(null=True, blank=True, help_text="Rule only evaluates after this time (IST)")
    time_to   = models.TimeField(null=True, blank=True, help_text="Rule only evaluates before this time (IST)")
 
    # Scope — NULL means global (superadmin). Filled for state admin rules.
    state = models.ForeignKey(
        'Settings_State', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='custom_alert_rules',
        help_text="Leave blank for global scope (superadmin). State admins auto-set this."
    )
 
    created_by = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        related_name='created_custom_alert_rules',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['state', 'status']),
        ]
        ordering = ['-created_at']
 
    def __str__(self):
        return f"{self.name} ({self.status})"
 
 
class CustomAlertSubrule(models.Model):
    """
    One condition within a CustomAlertRule. Maximum 4 per rule (enforced by serializer).
 
    Supported GPSData parameters (all field names on the GPSData model):
        Numeric : speed, altitude, satellites, pdop, hdop, heading, odometer,
                  main_input_voltage, internal_battery_voltage, frame_number
        Text    : packet_type, alert_id, packet_status, gps_status,
                  ignition_status, main_power_status, emergency_status,
                  box_tamper_alert, network_operator, gsm_signal_strength
        Datetime: packet_datetime, entry_time
 
    Operator semantics by field type:
        Numeric / Datetime : ==  !=  >  >=  <  <=  in_range
        Text               : ==  !=  contains  not_contains
 
    For in_range, value_start and value_end must be supplied.
    For all other operators, value is used.
    """
 
    OPERATOR_EQ            = '=='
    OPERATOR_NEQ           = '!='
    OPERATOR_GT            = '>'
    OPERATOR_GTE           = '>='
    OPERATOR_LT            = '<'
    OPERATOR_LTE           = '<='
    OPERATOR_IN_RANGE      = 'in_range'
    OPERATOR_CONTAINS      = 'contains'
    OPERATOR_NOT_CONTAINS  = 'not_contains'
 
    OPERATOR_CHOICES = [
        (OPERATOR_EQ,           'Equal to (==)'),
        (OPERATOR_NEQ,          'Not equal to (!=)'),
        (OPERATOR_GT,           'Greater than (>)'),
        (OPERATOR_GTE,          'Greater than or equal to (>=)'),
        (OPERATOR_LT,           'Less than (<)'),
        (OPERATOR_LTE,          'Less than or equal to (<=)'),
        (OPERATOR_IN_RANGE,     'In range (start–end)'),
        (OPERATOR_CONTAINS,     'Contains (text)'),
        (OPERATOR_NOT_CONTAINS, 'Does not contain (text)'),
    ]
 
    # All GPSData fields available as alert parameters
    PARAMETER_CHOICES = [
        # Numeric
        ('speed',                    'Speed'),
        ('altitude',                 'Altitude'),
        ('satellites',               'Satellites'),
        ('pdop',                     'PDOP'),
        ('hdop',                     'HDOP'),
        ('heading',                  'Heading'),
        ('odometer',                 'Odometer'),
        ('main_input_voltage',       'Main Input Voltage'),
        ('internal_battery_voltage', 'Internal Battery Voltage'),
        ('frame_number',             'Frame Number'),
        # Text
        ('packet_type',              'Packet Type'),
        ('alert_id',                 'Alert ID'),
        ('packet_status',            'Packet Status'),
        ('gps_status',               'GPS Status'),
        ('ignition_status',          'Ignition Status'),
        ('main_power_status',        'Main Power Status'),
        ('emergency_status',         'Emergency Status'),
        ('box_tamper_alert',         'Box Tamper Alert'),
        ('network_operator',         'Network Operator'),
        ('gsm_signal_strength',      'GSM Signal Strength'),
        ('digital_input_status',     'Digital Input Status'),
        ('digital_output_status',    'Digital Output Status'),
    ]
 
    # Text parameters — used for operator validation
    TEXT_PARAMETERS = {
        'packet_type', 'alert_id', 'packet_status', 'gps_status',
        'ignition_status', 'main_power_status', 'emergency_status',
        'box_tamper_alert', 'network_operator', 'gsm_signal_strength',
        'digital_input_status', 'digital_output_status',
    }
 
    rule      = models.ForeignKey(CustomAlertRule, on_delete=models.CASCADE, related_name='subrules')
    order     = models.PositiveSmallIntegerField(default=1, help_text="Display order 1–4")
    parameter = models.CharField(max_length=50, choices=PARAMETER_CHOICES)
    operator  = models.CharField(max_length=15, choices=OPERATOR_CHOICES)
 
    # Value fields
    value       = models.CharField(max_length=255, blank=True, help_text="Single comparison value")
    value_start = models.CharField(max_length=255, blank=True, help_text="Range start (in_range only)")
    value_end   = models.CharField(max_length=255, blank=True, help_text="Range end (in_range only)")
 
    # Optional subrule-level time window (narrows when THIS condition is checked)
    time_from = models.TimeField(null=True, blank=True)
    time_to   = models.TimeField(null=True, blank=True)
 
    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(
                fields=['rule', 'order'],
                name='unique_subrule_order_per_rule'
            )
        ]
 
    def __str__(self):
        return f"Subrule {self.order}: {self.parameter} {self.operator} {self.value or f'{self.value_start}–{self.value_end}'}"
 
 
class CustomAlertLog(models.Model):
    """
    Fired when a CustomAlertRule evaluates True against a GPSData packet.
    Kept separate from AlertsLog to avoid polluting the hardcoded alert stream.
    """
    rule       = models.ForeignKey(CustomAlertRule, on_delete=models.CASCADE, related_name='logs')
    device_tag = models.ForeignKey('DeviceTag', on_delete=models.CASCADE, related_name='custom_alert_logs')
    gps_ref    = models.ForeignKey('GPSData', on_delete=models.CASCADE, related_name='custom_alert_logs')
    state      = models.ForeignKey('Settings_State', on_delete=models.SET_NULL, null=True, blank=True)
    fired_at   = models.DateTimeField(auto_now_add=True, db_index=True)
    details    = models.TextField(blank=True, help_text="Human-readable summary of which subrules matched")
 
    class Meta:
        indexes = [
            models.Index(fields=['rule', 'fired_at']),
            models.Index(fields=['device_tag', 'fired_at']),
            models.Index(fields=['state', 'fired_at']),
        ]
        ordering = ['-fired_at']
 
    def __str__(self):
        return f"CustomAlertLog rule={self.rule_id} device={self.device_tag_id} at {self.fired_at}"




# ──────────────────────────────────────────────────────────────────────────────
# Custom Alert Rule evaluation engine
# Triggered by GPSData post_save → writes into BOTH AlertsLog and CustomAlertLog
# ──────────────────────────────────────────────────────────────────────────────

CUSTOM_ALERT_COOLDOWN_MINUTES = 30


def _time_in_window(t, t_from, t_to):
    """True if time t is within [t_from, t_to]. Handles midnight wrap."""
    if t_from <= t_to:
        return t_from <= t <= t_to
    return t >= t_from or t <= t_to


def _evaluate_subrule(sr, gps, now_time):
    """
    Evaluate one CustomAlertSubrule against a GPSData record.
    Returns True if the condition is met, False otherwise.
    """
    if sr.time_from and sr.time_to:
        if not _time_in_window(now_time, sr.time_from, sr.time_to):
            return False

    raw_value = getattr(gps, sr.parameter, None)
    if raw_value is None:
        return False

    op      = sr.operator
    is_text = sr.parameter in CustomAlertSubrule.TEXT_PARAMETERS

    try:
        if op == CustomAlertSubrule.OPERATOR_CONTAINS:
            return str(sr.value).lower() in str(raw_value).lower()

        if op == CustomAlertSubrule.OPERATOR_NOT_CONTAINS:
            return str(sr.value).lower() not in str(raw_value).lower()

        if op == CustomAlertSubrule.OPERATOR_EQ:
            if is_text:
                return str(raw_value).strip().lower() == str(sr.value).strip().lower()
            return float(raw_value) == float(sr.value)

        if op == CustomAlertSubrule.OPERATOR_NEQ:
            if is_text:
                return str(raw_value).strip().lower() != str(sr.value).strip().lower()
            return float(raw_value) != float(sr.value)

        rv = float(raw_value)

        if op == CustomAlertSubrule.OPERATOR_GT:       return rv >  float(sr.value)
        if op == CustomAlertSubrule.OPERATOR_GTE:      return rv >= float(sr.value)
        if op == CustomAlertSubrule.OPERATOR_LT:       return rv <  float(sr.value)
        if op == CustomAlertSubrule.OPERATOR_LTE:      return rv <= float(sr.value)
        if op == CustomAlertSubrule.OPERATOR_IN_RANGE:
            return float(sr.value_start) <= rv <= float(sr.value_end)

    except (ValueError, TypeError):
        return False

    return False


def _is_in_cooldown(rule_id, device_tag_id):
    """
    Returns True if the same rule already fired for this device
    within the last CUSTOM_ALERT_COOLDOWN_MINUTES minutes.
    Queries CustomAlertLog which is written atomically with AlertsLog.
    """
    cutoff = timezone.now() - timedelta(minutes=CUSTOM_ALERT_COOLDOWN_MINUTES)
    return CustomAlertLog.objects.filter(
        rule_id=rule_id,
        device_tag_id=device_tag_id,
        fired_at__gte=cutoff,
    ).exists()


def _evaluate_custom_alert_rules(gps_instance):
    """
    Evaluate all active CustomAlertRules against a freshly saved GPSData record.
    Called inside transaction.on_commit so it never delays GPS ingestion.
    All exceptions are caught and printed — never raises.
    """
    device_tag = gps_instance.device_tag
    if not device_tag:
        return

    try:
        device_state = device_tag.district.state if device_tag.district else None
    except Exception:
        device_state = None

    if not device_state:
        print(
            f"[CustomAlert] Skipping gps_id={gps_instance.id} — "
            f"cannot resolve state for device_tag {device_tag.id}",
            flush=True,
        )
        return

    now_time = timezone.localtime(gps_instance.entry_time).time()

    rules_qs = (
        CustomAlertRule.objects
        .filter(status=CustomAlertRule.STATUS_ACTIVE)
        .filter(
            Q(state__isnull=True) | Q(state=device_state)
        )
        .prefetch_related('subrules')
    )

    for rule in rules_qs:
        try:
            _fire_rule_if_matches(rule, gps_instance, now_time, device_state)
        except Exception as e:
            print(
                f"[CustomAlert] Error evaluating rule {rule.id} "
                f"against gps {gps_instance.id}: {e}",
                flush=True,
            )


def _fire_rule_if_matches(rule, gps, now_time, device_state):
    """
    Check one rule. If it fires and is not in cooldown,
    write into AlertsLog AND CustomAlertLog.
    """
    if rule.time_from and rule.time_to:
        if not _time_in_window(now_time, rule.time_from, rule.time_to):
            return

    subrules = list(rule.subrules.all())
    if not subrules:
        return

    results      = []
    match_labels = []

    for sr in subrules:
        matched = _evaluate_subrule(sr, gps, now_time)
        results.append(matched)
        if matched:
            value_repr = (
                f"{sr.value_start}–{sr.value_end}"
                if sr.operator == CustomAlertSubrule.OPERATOR_IN_RANGE
                else sr.value
            )
            match_labels.append(
                f"[{sr.order}] {sr.parameter} {sr.operator} {value_repr}"
            )

    if rule.subrule_logic == CustomAlertRule.SUBRULE_LOGIC_AND:
        fired = all(results)
    else:
        fired = any(results)

    if not fired:
        return

    # ── Cooldown check ────────────────────────────────────────────────────────
    if _is_in_cooldown(rule.id, gps.device_tag_id):
        print(
            f"[CustomAlert] Rule '{rule.name}' (id={rule.id}) suppressed "
            f"for device {gps.device_tag.vehicle_reg_no} "
            f"— within {CUSTOM_ALERT_COOLDOWN_MINUTES}min cooldown",
            flush=True,
        )
        return

    details_text       = "; ".join(match_labels) if match_labels else "Rule matched"
    alert_details_text = f"Custom Rule: {rule.name} | {details_text}"

    # ── Write into AlertsLog ──────────────────────────────────────────────────
    AlertsLog.objects.create(
        type          = 'Custom',
        status        = '',
        gps_ref       = gps,
        route_ref     = None,
        poi_ref       = None,
        em_ref        = None,
        alert_details = alert_details_text,
        deviceTag     = gps.device_tag,
        state         = device_state,
    )

    # ── Write into CustomAlertLog ─────────────────────────────────────────────
    CustomAlertLog.objects.create(
        rule       = rule,
        device_tag = gps.device_tag,
        gps_ref    = gps,
        state      = device_state,
        details    = details_text,
    )

    print(
        f"[CustomAlert] Rule '{rule.name}' (id={rule.id}) fired "
        f"for device {gps.device_tag.vehicle_reg_no} "
        f"gps_id={gps.id}",
        flush=True,
    )


@receiver(post_save, sender=GPSData, dispatch_uid="gpsdata_evaluate_custom_alert_rules")
def gpsdata_evaluate_custom_alert_rules(sender, instance, created, **kwargs):
    if not created:
        return
    from django.db import transaction
    transaction.on_commit(lambda: _evaluate_custom_alert_rules(instance))


class ActivationCommandReply(models.Model):
    objects = SafeCreateManager()
    imei = models.CharField(max_length=55)
    device_tag = models.ForeignKey(DeviceTag, on_delete=models.SET_NULL, null=True, blank=True, related_name='activation_command_replies')
    raw_message = models.TextField()
    timestamp = models.DateTimeField()
    incoming_from_no = models.CharField(max_length=20)

    class Meta:
        indexes = [
            models.Index(fields=['imei']),
            models.Index(fields=['timestamp']),
        ]


# ===========================================================================
# OTA Command Management
# ===========================================================================

class OTACommandDefinition(models.Model):
    """
    A reusable OTA command definition (Page 1 — 'OT Commands' list).
    Defines the protocol-level get/set/clear templates for one device command.
    """
    objects = SafeCreateManager()

    SOURCE_CHOICES = [
        ('sms', 'SMS'),
        ('mqtt', 'MQTT'),
        ('both', 'Both'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    command_id = models.CharField(max_length=100, unique=True, verbose_name="Command ID")
    specification = models.TextField(blank=True, null=True)
    command_key = models.CharField(max_length=255, verbose_name="Command Key")

    # On-wire templates. {value} is substituted with the value supplied at
    # send-time (only meaningful for set_command_template).
    get_command_template = models.CharField(max_length=255, blank=True, null=True)
    set_command_template = models.CharField(max_length=255, blank=True, null=True)
    clear_command_template = models.CharField(max_length=255, blank=True, null=True)

    value_regex = models.CharField(max_length=500, blank=True, null=True)
    reply_regex = models.CharField(max_length=500, blank=True, null=True)

    allow_get = models.BooleanField(default=False)
    allow_set = models.BooleanField(default=False)
    allow_clear = models.BooleanField(default=False)

    allowed_source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='both')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ota_command_definitions_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ota_command_definitions_updated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ota_command_definition'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.command_id} ({self.command_key})"


class OTACommandHistory(models.Model):
    """
    A single get/set/clear command sent to a device and its reply (Page 2 —
    'OTA Command History').
    """
    objects = SafeCreateManager()

    COMMAND_TYPE_CHOICES = [
        ('get', 'Get'),
        ('set', 'Set'),
        ('clear', 'Clear'),
    ]
    SOURCE_CHOICES = [
        ('sms', 'SMS'),
        ('mqtt', 'MQTT'),
    ]
    SEND_STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('replied', 'Replied'),
        ('timeout', 'Timeout'),
    ]

    ota_command = models.ForeignKey(OTACommandDefinition, on_delete=models.CASCADE, related_name='history', verbose_name="OTA Command")
    command_type = models.CharField(max_length=10, choices=COMMAND_TYPE_CHOICES)
    command_sent = models.TextField(blank=True, null=True)
    reply_received = models.TextField(blank=True, null=True)
    imei = models.CharField(max_length=55)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    send_status = models.CharField(max_length=10, choices=SEND_STATUS_CHOICES, default='queued')

    device_tag = models.ForeignKey(DeviceTag, on_delete=models.SET_NULL, null=True, blank=True, related_name='ota_command_history')
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ota_commands_sent')

    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    reply_regex_output = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ota_command_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['imei']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"{self.ota_command_id} -> {self.imei} @ {self.created_at}"


class OTACommandValueSuggestion(models.Model):
    """
    Auto-populated list of previously-used values per OTA command (Model 3).
    Rows are created/updated automatically by the send-command API whenever a
    'set' command is sent with a value that isn't already in the list —
    there is no manual create endpoint for this model.
    """
    objects = SafeCreateManager()

    ota_command = models.ForeignKey(OTACommandDefinition, on_delete=models.CASCADE, related_name='value_suggestions', verbose_name="OTA Command")
    value = models.CharField(max_length=500)
    use_count = models.PositiveIntegerField(default=1)
    last_used_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ota_command_value_suggestion'
        ordering = ['-last_used_at']
        unique_together = ('ota_command', 'value')

    def __str__(self):
        return f"{self.ota_command_id}: {self.value}"

    def __str__(self):
        return f"{self.imei} @ {self.timestamp}"