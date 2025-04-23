# skytronapp/models.py
from django.db import models
import hashlib
from django.utils import timezone  # Add this line

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

 
from django.db.models import Count, Q



# SkytronServer/gps_api/models.py
from django.db import models

from datetime import datetime , timedelta


# SkytronServer/gps_api/models.py
from django.db.models.signals import post_save
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

class Captcha(models.Model):
    key = models.CharField(max_length=32, unique=True, default=uuid.uuid4().hex)
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
    mark_type = models.CharField(max_length=20, choices=mark_type_choices)
    use_type_choices = [
            ('StateBoundary', 'StateBoundary'),
            ( 'DistrictBoundary', 'DistrictBoundary'),
            ( 'CityBoundary',  'CityBoundary'), 
            ( 'VillageBoundary',  'VillageBoundary'), 
            ( 'PermitRoute',  'PermitRoute'), 
            ( 'School',  'School'), 
            ( 'Hospital',  'Hospital'), 
            ( 'PoliceStation',  'PoliceStation'), 
            ( 'BusStop',  'BusStop'),  
            ( 'RailwayStation',  'RailwayStation'), 
            ( 'Airport',  'Airport'), 
            ( 'FuelStation',  'FuelStation'), 
            ( 'TollGate',  'TollGate'), 
            ( 'Other',  'Other'),
            ( 'Personal',  'Personal'),
            
        ]
    use_type = models.CharField(max_length=20, choices=use_type_choices)
    location = models.TextField()
    radius = models.FloatField(blank=True, null=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,related_name='POI_created_by')
    updated_by = models.ForeignKey('User', on_delete=models.CASCADE,related_name='POI_updated_by')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name
    
     

    
def get_logged_in_users_with_min_assignments(): 
    eight_hours_ago = timezone.now() - timezone.timedelta(hours=8) 
    return 0
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
    name = models.CharField(max_length=255, verbose_name="Name",null=False,blank=False) 
    #companyName=models.CharField(max_length=255, default='',verbose_name="companyName") 
    #username = models.EmailField(unique=True, verbose_name="Username")
    email = models.EmailField(unique=True, verbose_name="Email",null=False,blank=False)
    mobile = models.CharField(max_length=15, unique=True, verbose_name="Mobile",null=False,blank=False)
    role = models.CharField(max_length=20,null=False,blank=False, choices=[("superadmin", "Super Admin"), ("stateadmin", "State Admin"), ("devicemanufacture", "Device Manufacture"), ("dealer", "Dealer"), ("owner", "Owner"), ("esimprovider", "eSimProvider"), ("filment", "Filment"), ("sosadmin", "SOS Admin"), ("teamleader", "Team Leader"), ("sosexecutive", "SOS Executive")], verbose_name="Role")
    usertype = models.CharField(max_length=10, default='main', verbose_name="User Type")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    date_joined = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    Access = models.JSONField(default=list,blank=True, null=True, verbose_name="Access")  
    password = models.CharField(max_length=100,default='12345678')  # Assuming 32 characters for MD5 hash
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
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name' ]

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
    name = models.CharField(max_length=255, verbose_name="Name")  
    #email = models.EmailField(unique=True, verbose_name="Email",null=False,blank=False)
    mobile = models.CharField(max_length=15,   verbose_name="Mobile") 
    ble_key = models.CharField(max_length=15, null=True,blank=True,unique=False, verbose_name="ble_key") 
    session_key = models.CharField(max_length=100, unique=True, verbose_name="session_key") 
    date_joined = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    otp = models.CharField(max_length=100,default='123456')  # Assuming 32 characters for MD5 hash
    otp_time= models.DateTimeField(default=timezone.now)
    em_contact=models.CharField(max_length=15,null=False,blank=False,  verbose_name="em_contact") 
    last_login =  models.DateTimeField(blank=True, null=True)
    last_activity =  models.DateTimeField(blank=True, null=True)
    online=models.BooleanField(default=False)
    feedback = models.TextField(blank=True, null=True, verbose_name="feedback") 
    em_lat = models.FloatField(blank=True, null=True, verbose_name="em_lat") 
    em_lon = models.FloatField(blank=True, null=True, verbose_name="em_lon") 
    em_msg=models.TextField(blank=True, null=True, verbose_name="em_msg") 
    em_time= models.DateTimeField(blank=True, null=True)
      

class Confirmation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    type=    models.CharField(max_length=20, choices=[("email", "Email"), ("sms", "SMS"), ("pw_rst", "Password Resset")], verbose_name="Type")
   
    is_valid = models.BooleanField(default=True)
    def is_valid(self):
        # Define your logic to check if the confirmation link is still valid (e.g., within a certain time limit)
        # You might want to add an expiry time field to the model for this purpose
        return self.is_valid
        

class Manufacturer(models.Model):
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    gstnnumber = models.CharField(max_length=20, blank=True, null=True)
    users = models.ManyToManyField('User', related_name='manufacturers_user')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(auto_now_add=True)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_authLetter = models.CharField(max_length=255, blank=True, null=True)
    file_companRegCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_GSTCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    esim_provider = models.ManyToManyField("eSimProvider", related_name='eSimProvider_Manufacturer',  blank=True)
    
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
        ]
    
    status = models.CharField(max_length=20, choices=status_choices)

class eSimProvider(models.Model):
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    gstnnumber = models.CharField(max_length=20, blank=True, null=True)
    users = models.ManyToManyField('User', related_name='eSimProvider_User')
    
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(auto_now_add=True)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_authLetter = models.CharField(max_length=255, blank=True, null=True)
    file_companRegCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_GSTCertificate = models.CharField(max_length=255, blank=True, null=True)
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
         
class Retailer(models.Model):
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    gstnnumber = models.CharField(max_length=20, blank=True, null=True)
    users = models.ManyToManyField('User', related_name='Retailer_user')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(auto_now_add=True)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    idProofno = models.CharField(max_length=255, blank=True, null=True)
    file_authLetter = models.CharField(max_length=255, blank=True, null=True)
    file_companRegCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_GSTCertificate = models.CharField(max_length=255, blank=True, null=True)
    file_idProof = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    district = models.ForeignKey('Settings_District', on_delete=models.CASCADE,blank=True, null=True)
    status_choices = [
            ('Created', 'Created'),
            ('UserVerified', 'UserVerified'),
            ('StateAdminVerified', 'StateAdminVerified'),
            ('UserExpired', 'UserExpired'), 
            ('Discontinued', 'Discontinued'),
        ]
    status = models.CharField(max_length=20, choices=status_choices)
    
class VehicleOwner(models.Model):
    company_name = models.CharField(max_length=255, blank=True, null=True,verbose_name="Company Name")
    users = models.ManyToManyField(User, related_name='manufacturers')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(auto_now_add=True)
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
    

class StateAdmin(models.Model):
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='stateadmin_User')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(auto_now_add=True)
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
    sms_text = models.CharField(max_length=500)
    no = models.CharField(max_length=20 )
    status = models.CharField(max_length=20, choices=[('Received','Received'),("Processed","Processed"),("Error","Error")])
    created = models.DateField(auto_now_add=True)
    
class sms_out(models.Model):     
    sms_text = models.CharField(max_length=500)
    no = models.CharField(max_length=20 )
    status = models.CharField(max_length=20, choices=[('Queue','Queue'),("Sent","Sent"),("Error","Error")])
    created = models.DateField(auto_now_add=True)
    
    
class dto_rto(models.Model):
    dto_rto=   models.CharField(max_length=20, choices=[('DTO','DTO'),("RTO","RTO")])
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    district =models.CharField(max_length=255, blank=True, null=True)#models.ForeignKey('Settings_District', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='dto_rto_User')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(auto_now_add=True)
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
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    district =models.CharField(max_length=255, blank=True, null=True)#models.ForeignKey('Settings_District', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='SOS_ex_user')
    created = models.DateField(auto_now_add=True)
    expirydate = models.DateField(auto_now_add=True)
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
    state = models.ForeignKey('Settings_State', on_delete=models.CASCADE)
    
    #district =models.ForeignKey('Settings_District', on_delete=models.CASCADE)
    users = models.ManyToManyField('User', related_name='EM_admin')
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

 


class Settings_State(models.Model): 
    state=models.CharField(max_length=50,unique=True)
    status = models.CharField(max_length=20, choices=[('active','active'),('discontinued','discontinued')])


class Settings_VehicleCategory(models.Model): 
    category=models.CharField(max_length=50,unique=True)
    maxSpeed=models.CharField(max_length=5)
    warnSpeed=models.CharField(max_length=5)
     

class Settings_District(models.Model):  
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
    deviceModel = models.ForeignKey('DeviceModel', on_delete=models.CASCADE)
    status_choices = [
        ('Created', 'Created'),
        ('FactoryTestOK', 'FactoryTestOK'),
        ('ShipedtoRetailer', 'ShipedtoRetailer'),
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
    STATUS_CHOICES = [
        ('Manufacturer_OTP_Sent', 'Manufacturer OTP Sent'),
        ('Manufacturer_OTP_Verified', 'Manufacturer OTP Verified'),
        ('StateAdminOTPSend', 'State Admin OTP Sent'),
        ('StateAdminApproved', 'State Admin Approved'),
    ]

    model_name = models.CharField(max_length=255)
    test_agency = models.CharField(max_length=255)
    vendor_id = models.CharField(max_length=255)
    tac_no = models.CharField(max_length=255)
    tac_validity = models.DateField()
    eSimProviders = models.ManyToManyField(eSimProvider, related_name='eSimProvider_devicemodle',  blank=True)
    otp_time=models.DateTimeField()
    hardware_version = models.CharField(max_length=255)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE)
    created = models.DateTimeField()
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    tac_doc_path = models.FileField(upload_to='tac_docs/', null=True, blank=True)
    otp = models.CharField(max_length=6 )


class Settings_firmware(models.Model): 
    devicemodel = models.ForeignKey('DeviceModel', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    firmware_vertion = models.CharField(max_length=255, blank=True, null=True)
    file_bin = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
     

class Settings_hp_freq(models.Model): 
    devicemodel = models.ForeignKey('DeviceModel', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    freq = models.CharField(max_length=255, blank=True, null=True)
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
     
  
class Settings_ip3(models.Model): 
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
    model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE)
    device_esn = models.CharField(max_length=55,unique=True)
    iccid = models.CharField(max_length=55,unique=True)
    imei = models.CharField(max_length=55,unique=True)
    telecom_provider1 = models.CharField(max_length=25)
    telecom_provider2 = models.CharField(max_length=25, blank=True, null=True)
    msisdn1 = models.CharField(max_length=255,unique=True)
    msisdn2 = models.CharField(max_length=255, unique=True,blank=True, null=True)
    imsi1 = models.CharField(max_length=255,blank=True, null=True)
    imsi2 = models.CharField(max_length=255, blank=True, null=True)
    esim_validity = models.DateTimeField()
    esim_provider = models.ManyToManyField(eSimProvider, related_name='eSimProvider_devicestock',  blank=True)
    
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
    ]
 
    dealer =  models.ForeignKey(Retailer, on_delete=models.CASCADE,null=True,blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True)   
    assigned = models.DateTimeField(null=True,blank=True)
    shipping_remark = models.TextField(null=True,blank=True)
    stock_status = models.CharField(max_length=55, choices=STATUS_CHOICES)
    esim_status = models.CharField(max_length=55, choices=STATUS_CHOICES)
    def __str__(self):
        return f"{self.model} - ESN: {self.device_esn}"
    
class DeviceCOP(models.Model):
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
    dealer =  models.ForeignKey(Retailer, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE)   
    assigned = models.DateTimeField()
    shipping_remark = models.TextField()
    stock_status = models.CharField(max_length=255, choices=STATUS_CHOICES)
"""


class Driver(models.Model): 

    created = models.DateTimeField(auto_now_add=True,)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE,related_name="createby_USERdriver")
   
    name = models.CharField(max_length= 55 )
    phone_no = models.CharField(max_length=55)
    license_no = models.CharField(max_length=55)
    photo = models.CharField(max_length= 555,null=True)

    def __str__(self):
        return self.name
    
class DeviceTag(models.Model):
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
        ('TagDeleted', 'TagDeleted'),
    ]

    device = models.ForeignKey(DeviceStock, on_delete=models.CASCADE)
    vehicle_owner = models.ForeignKey(VehicleOwner, on_delete=models.CASCADE)
   
    vehicle_reg_no = models.CharField(max_length= 55,unique=True)
    engine_no = models.CharField(max_length=55,unique=True)
    chassis_no = models.CharField(max_length= 55,unique=True)
    vehicle_make = models.CharField(max_length= 55)
    vehicle_model = models.CharField(max_length= 55)
    category = models.CharField(max_length= 55)
    rc_file = models.CharField(max_length=255)
    receipt_file_or = models.CharField(max_length=255)
    receipt_file_ul = models.CharField(max_length=255)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    tagged_by = models.ForeignKey(User, on_delete=models.CASCADE)
    tagged = models.DateTimeField()    
    otp = models.CharField(max_length= 6,null=True,blank=True)
    otp_time = models.DateTimeField( null=True,blank=True)
    drivers= models.ManyToManyField(Driver, related_name='driver_vehicles', blank=True)

    def __str__(self):
        return self.vehicle_reg_no


##unused



       
class EMGPSLocation(models.Model): #imergency tracking data
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
    device_tag=models.ForeignKey(DeviceTag, on_delete=models.CASCADE,null=True, blank=True)
    class Meta:
        app_label = 'skytron_api'
    def __str__(self):
        return f"{self.device_imei} - {self.date} {self.time}"

    @classmethod
    def create_from_string(cls, data_list): 
        if data_list[3]=='x':
            data_list[3]='01012020'
        if data_list[4]=='x':
            data_list[4]='000000'
        data_list[3] = datetime.strptime(data_list[3], "%d%m%Y").strftime("%Y-%m-%d")
        data_list[4] = datetime.strptime(data_list[4], "%H%M%S").strftime("%H:%M:%S")

        datetime_str = f"{data_list[3]} {data_list[4]}"
        dt_object = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S") 
        adjusted_datetime = dt_object + timedelta(hours=5, minutes=30, seconds=0)

        data_list[3]=adjusted_datetime.strftime("%Y-%m-%d") 
        data_list[4]=adjusted_datetime.strftime("%H:%M:%S") 
        device_tag=DeviceTag.objects.filter(device__imei=str(data_list[1]),status='Owner_Final_OTP_Verified').last()
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
                gps_validity=data_list[5],
                latitude=float(data_list[6]),
                latitude_direction=data_list[7],
                longitude=float(data_list[8]),
                longitude_direction=data_list[9],
                altitude=float(data_list[10]),
                speed=float(data_list[11]),
                distance=float(data_list[12]),
                provider=data_list[13],
                vehicle_reg_no=data_list[14],
                reply_mob_no=data_list[15],
                device_tag=device_tag,
            )



 


@receiver(post_save, sender=EMGPSLocation)
def create_emergency_call(sender, instance, created, **kwargs):
    if created :#and instance.status == 'Complete':
     
        # Check if an EmergencyCall entry already exists for the given vehicle and IMEI
        existing_emergency_call =EMCall.objects.filter(
            device=instance.device_tag
        ).exclude(status__in=["closed_false_allert",  "closed"]).last()
        
        if existing_emergency_call:
            pass
            """
            timeouts=EmergencyCall_assignment.objects.filter(
                        emergencyCall_id=existing_emergency_call, 
                        assign_time__gte=timezone.now() - timezone.timedelta(seconds=20),
                        status = 'Assigned')
            for timeout in timeouts:
                timeout.status = 'Timeout'
                timeout.save()
                '''user_to_assign=get_logged_in_users_with_min_assignments()
                print(user_to_assign) 
                EmergencyCall_assignment.objects.create(
                            emergencyCall_id=existing_emergency_call,
                            user=user_to_assign,
                            assign_time = timezone.now(), 
                            status = 'Assigned',#Assigned,Acccepted, Rejected,Timeout,Closed
                        )
                ''' 

            
            assigned=EmergencyCall_assignment.objects.filter(
                        emergencyCall_id=existing_emergency_call,  
                        status__in=['Assigned','Acccepted','Closed']).last()
            if not assigned:
                user_to_assign=get_logged_in_users_with_min_assignments()  
                if  user_to_assign:              
                    EmergencyCall_assignment.objects.create(
                            emergencyCall_id=existing_emergency_call,
                            user=user_to_assign,
                            assign_time = timezone.now(), 
                            status = 'Assigned',#Assigned,Acccepted, Rejected,Timeout,Closed
                        ) 

        """
        st=instance.device_tag.device.dealer.manufacturer.state 
                                                                  
        if not existing_emergency_call:
            # Create a new EmergencyCall entry
            team  = EMTeams.objects.filter(status="Active",state=st
                                           ).order_by('?').last()
            em=EMCall.objects.create(
                device=instance.device_tag, 
                #start_time=timezone.now(),
                team=team,
                status='pending',  # Set the initial status as 'Pending'
                #desk_executive_id='',
                #field_executive_id='',
                #final_comment='',
            )
            #user_to_assign=get_logged_in_users_with_min_assignments()
            #if  user_to_assign:   
            EMCallAssignment.objects.create(
                        admin =   EM_admin.objects.filter().last(),#,filter(users__login=True)
                        call =em,
                        status = "pending",
                        type = "teamlead",
                        ex = team.teamlead    )  
            EMCallAssignment.objects.create(
                    admin = EM_admin.objects.all().last(),#
                    call =em ,
                    status = "pending",
                    type = "desk_ex",
                    ex = team.members.order_by('?').first(), #
                    )  












class IPList(models.Model):
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
    loginTime = models.DateTimeField(default=timezone.now, verbose_name="Login Time")
    user = models.ForeignKey(User, on_delete=models.CASCADE)# models.IntegerField(verbose_name="User")
    token = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token")
    token_tmp = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token_tmp")
    otp = models.IntegerField(blank=True, null=True, verbose_name="OTP")
    status = models.CharField(max_length=10, choices=[("otpsent", "OTP Sent"), ("login", "Login"), ("logout", "Logout"), ("timeout", "Timeout")], verbose_name="Status")
    lastactivity=models.DateTimeField(default=timezone.now, verbose_name="lastactivity")
   
    def __str__(self):
        return f"Session {self.id}"

class OTPRequest(models.Model):
    otpTime = models.DateTimeField(auto_now_add=True, verbose_name="OTP Time")
    type = models.CharField(max_length=5, choices=[("email", "Email"), ("sms", "SMS")], verbose_name="Type")
    user = models.IntegerField(verbose_name="User")
    otp = models.CharField(max_length=255, verbose_name="OTP")
    status = models.CharField(max_length=20, choices=[("otpsent", "OTP Sent"), ("errorsending", "Error Sending"), ("verified", "Verified"), ("donotmatch", "Do Not Match"), ("timeout", "Timeout")], verbose_name="Status")

    def __str__(self):
        return f"OTPRequest {self.id}"

class esimActivationRequest(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="creates_at")
    ceated_by=models.ForeignKey(Retailer, on_delete=models.CASCADE)
    eSim_provider=models.ForeignKey(eSimProvider, on_delete=models.CASCADE)
    valid_from = models.DateTimeField(null=True)
    valid_upto = models.DateTimeField(null=True)
    accepted_at = models.DateTimeField(null=True)
    device=models.ForeignKey(DeviceStock, on_delete=models.CASCADE)    
    status = models.CharField(max_length=20, choices=[("pending", "pending"), ("valid", "valid"), ("invalid", "invalid")], verbose_name="Status")

    def __str__(self):
        return f"esimActivationRequest {self.id}"

class EditRequest(models.Model):
    time = models.DateTimeField(auto_now_add=True, verbose_name="Time")
    type = models.CharField(max_length=20, choices=[("owner", "Owner"), ("device", "Device"), ("vehicle", "Vehicle"), ("devicemodel", "Device Model"), ("retailer", "Retailer"), ("manufacturer", "Manufacturer")], verbose_name="Type")
    from_user = models.IntegerField(verbose_name="From User")
    to_user = models.IntegerField(verbose_name="To User")
    otp = models.IntegerField(verbose_name="OTP")
    newdataid = models.IntegerField(verbose_name="New Data ID")
    olddataid = models.IntegerField(verbose_name="Old Data ID")
    status = models.CharField(max_length=20, choices=[("requestsent", "Request Sent"), ("accepted", "Accepted"), ("rejected", "Rejected")], verbose_name="Status")

    def __str__(self):
        return f"EditRequest {self.id}"
 

class Settings(models.Model):
    velid_time = models.DateTimeField(auto_now_add=True, verbose_name="Valid Time")
    type = models.CharField(max_length=255, verbose_name="Type")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    settingsstring = models.CharField(max_length=255, verbose_name="Settings String")
    settingsmethod = models.CharField(max_length=255, verbose_name="Settings Method")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    def __str__(self):
        return f"Settings {self.id}"

class GPSData(models.Model):
    entry_time = models.DateTimeField(auto_now_add=True)
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

class GPSDataLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    raw_data = models.TextField()

class GPSemDataLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    raw_data = models.TextField()

  
class AlertsLog(models.Model):
    TYPE_CHOICES = [
        ('Route', 'Route'), 
        ('Em', 'Em'), 
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
        ('HarshAccileration', 'HarshAccileration'), 
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
    em_ref=models.ForeignKey("EMCall", on_delete=models.CASCADE,null=True, blank=True)
    #dummnyuser=models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True) 
    deviceTag=models.ForeignKey(DeviceTag, on_delete=models.CASCADE) 
    #district=models.ForeignKey(dto_rto, on_delete=models.CASCADE,null=True, blank=True) 
    state=models.ForeignKey(Settings_State, on_delete=models.CASCADE) 
    

class Notice(models.Model): 
    created = models.DateField(auto_now_add=True)  
    createdby = models.ForeignKey('User', on_delete=models.CASCADE)
    file = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    detail = models.CharField(max_length=255, blank=True, null=True)     
    status = models.CharField(max_length=25, blank=True, null=True)      




class EMTeams(models.Model): 
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
    choices=[("pending", "pending"), ("desk_ex_assigned", "desk_ex_assigned"), ("broadcast_pending", "broadcast_pending"), ("field_ex_aproaching", "field_ex_aproaching"), ("field_ex_arrived", "field_ex_arrived"), ("closed_false_allert", "closed_false_allert"), ("closed", "closed")]
    team  = models.ForeignKey(EMTeams, null=True,  on_delete=models.CASCADE,related_name='EMTeams_id')
    device = models.ForeignKey(DeviceTag,  on_delete=models.CASCADE,related_name='DeviceTag_id')
    start_time =   models.DateTimeField(auto_now_add=True, verbose_name="start_time")
    end_time =   models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=30,choices=choices)
    closer_comment = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"EMCall {self.id}"
 




class EMCallAssignment(models.Model): 
    status=[("pending", "pending"), ("accepted", "accepted"), ("rejected", "rejected"), ("arriving", "arriving"), ("arrived", "arrived"), ("closed_false_allert", "closed_false_allert"), ("closed", "closed")]
    types=[("teamlead", "teamlead"), ("desk_ex", "desk_ex"), ("police_ex", "police_ex"), ("ambulance_ex", "ambulance_ex") , ("pcr", "pcr") , ("acr", "acr") ]
    admin = models.ForeignKey(EM_admin,  on_delete=models.CASCADE,related_name='emcalladmin')
    ex = models.ForeignKey(EM_ex,  on_delete=models.CASCADE,related_name='exec_id')
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
    call = models.ForeignKey(EMCall,  on_delete=models.CASCADE,related_name='EMCa111ll_id111')
    assignment = models.ForeignKey(EMCallAssignment,  on_delete=models.CASCADE,related_name='EMCallAssignm11ent111_id')
    time =   models.DateTimeField(auto_now_add=True, verbose_name="time")  
    message = models.TextField()
    def __str__(self):
        return f"EMCall {self.id}"


class EMCallBackupRequest(models.Model): 
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
    field_ex = models.ForeignKey(EM_ex,  null=True,on_delete=models.CASCADE,related_name='field_executive1_id_location')# models.CharField(max_length=50, unique=True)
    em_lat = models.FloatField(blank=True, null=True, verbose_name="em_lat") 
    em_lon = models.FloatField(blank=True, null=True, verbose_name="em_lon") 
    speed = models.FloatField(blank=True, null=True, verbose_name="speed") 
    time =   models.DateTimeField(auto_now_add=True, verbose_name="time")   
    def __str__(self):
        return f"EMCall {self.id}"




"""


class EMCall(models.Model): 
    device 
    start_time  
    end_time  
    status = [("pending", "pending"), ("desk_ex_assigned", "desk_ex_assigned"), ("broadcast_pending", "broadcast_pending"), ("field_ex_aproaching", "field_ex_aproaching"), ("field_ex_arrived", "field_ex_arrived"), ("closed_false_allert", "closed_false_allert"), ("closed", "closed")]
    closer_comment  

class EMCallAssignment(models.Model): 
    status=[("pending", "pending"), ("accepted", "accepted"), ("rejected", "rejected"), ("arriving", "arriving"), ("arrived", "arrived"), ("closed_false_allert", "closed_false_allert"), ("closed", "closed")]
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