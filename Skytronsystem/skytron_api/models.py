# skytronapp/models.py
from django.db import models
import hashlib
from django.utils import timezone  # Add this line

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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
    name = models.CharField(max_length=255, verbose_name="Name")    
    #username = models.EmailField(unique=True, verbose_name="Username")
    email = models.EmailField(unique=True, verbose_name="Email")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address")
    address_pin = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address Pin")
    mobile = models.CharField(max_length=15, unique=True, verbose_name="Mobile")
    role = models.CharField(max_length=20, choices=[("superadmin", "Super Admin"), ("stateadmin", "State Admin"), ("devicemanufacture", "Device Manufacture"), ("dealer", "Dealer"), ("owner", "Owner"), ("filment", "Filment"), ("sosadmin", "SOS Admin"), ("teamleader", "Team Leader"), ("sosexecutive", "SOS Executive")], verbose_name="Role")
    usertype = models.CharField(max_length=10, default='main', verbose_name="User Type")
    roleassign = models.JSONField(default=list, verbose_name="Role Assign")
    parent = models.CharField(max_length=255, blank=True, null=True, verbose_name="Parent")
    stateid = models.CharField(max_length=255, blank=True, null=True, verbose_name="State ID")
    status = models.CharField(max_length=10, choices=[("active", "Active"), ("deactive", "Deactive")], verbose_name="Status")
    dob = models.CharField(max_length=255, blank=True, null=True, verbose_name="Date of Birth")
    panfile = models.CharField(max_length=255, blank=True, null=True, verbose_name="PAN File")
    kyctype = models.CharField(max_length=255, blank=True, null=True, verbose_name="KYC Type")
    kycdocnumber = models.CharField(max_length=255, blank=True, null=True, verbose_name="KYC Doc Number")
    kycfile = models.CharField(max_length=255, blank=True, null=True, verbose_name="KYC File")
    mobileotp = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mobile OTP")
    mobileotpsend = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mobile OTP Send")
    token = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token")
    gstnnumber = models.CharField(max_length=255, blank=True, null=True, verbose_name="GSTN Number")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    Access = models.JSONField(default=list, verbose_name="Access")
    password = models.CharField(max_length=100)  # Assuming 32 characters for MD5 hash
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

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
    

class Manufacturer(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address")
    address_pin = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address Pin")
    gstnnumber = models.CharField(max_length=255, blank=True, null=True, verbose_name="GSTN Number")
    users = models.JSONField(default=list, verbose_name="Users")
    deviceModel = models.JSONField(default=list, verbose_name="Device Model")
    retailer = models.JSONField(default=list, verbose_name="Retailer")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    Access = models.JSONField(default=list, verbose_name="Access")

    def __str__(self):
        return self.name

class Retailer(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address")
    address_pin = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address Pin")
    gstnnumber = models.CharField(max_length=255, blank=True, null=True, verbose_name="GSTN Number")
    users = models.JSONField(default=list, verbose_name="Users")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    Access = models.JSONField(default=list, verbose_name="Access")

    def __str__(self):
        return self.name

class Device(models.Model):
    deviceModel = models.IntegerField(verbose_name="Device Model")
    status = models.CharField(max_length=255, verbose_name="Status")
    softwareLatestVersion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Software Latest Version")
    vehicle = models.IntegerField(verbose_name="Vehicle")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    def __str__(self):
        return f"Device {self.id}"

class DeviceModel(models.Model):
    deviceModel = models.CharField(max_length=255, verbose_name="Device Model")
    status = models.CharField(max_length=20, choices=[("active", "Active"), ("discontinued", "Discontinued")], verbose_name="Status")
    hardwareVersion = models.CharField(max_length=255, verbose_name="Hardware Version")
    softwareLatestVersion = models.CharField(max_length=255, verbose_name="Software Latest Version")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    def __str__(self):
        return self.deviceModel

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

class Vehicle(models.Model):
    status = models.CharField(max_length=10, choices=[("active", "Active"), ("deactive", "Deactive")], verbose_name="Status")
    access = models.JSONField(default=list, verbose_name="Access")
    vregno = models.CharField(max_length=255, blank=True, null=True, verbose_name="Vehicle Registration Number")
    engineno = models.CharField(max_length=255, blank=True, null=True, verbose_name="Engine Number")
    chessisno = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chassis Number")
    vehiclemake = models.CharField(max_length=255, blank=True, null=True, verbose_name="Vehicle Make")
    vehiclemodel = models.CharField(max_length=255, blank=True, null=True, verbose_name="Vehicle Model")
    vehiclecategory = models.CharField(max_length=255, blank=True, null=True, verbose_name="Vehicle Category")
    rcfilepath = models.CharField(max_length=255, blank=True, null=True, verbose_name="RC File Path")
    owner = models.IntegerField(verbose_name="Owner")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    def __str__(self):
        return f"Vehicle {self.id}"

class Tracking(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    def __str__(self):
        return f"Tracking {self.id}"

class TrackingLog(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")

    def __str__(self):
        return f"TrackingLog {self.id}"

class Session(models.Model):
    loginTime = models.DateTimeField(default=timezone.now, verbose_name="Login Time")
    user = models.IntegerField(verbose_name="User")
    token = models.CharField(max_length=255, verbose_name="Token")
    otp = models.IntegerField(blank=True, null=True, verbose_name="OTP")
    status = models.CharField(max_length=10, choices=[("otpsent", "OTP Sent"), ("login", "Login"), ("logout", "Logout"), ("timeout", "Timeout")], verbose_name="Status")

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
