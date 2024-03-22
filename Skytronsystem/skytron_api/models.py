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
    #companyName=models.CharField(max_length=255, default='',verbose_name="companyName") 
    #username = models.EmailField(unique=True, verbose_name="Username")
    email = models.EmailField(unique=True, verbose_name="Email")
    mobile = models.CharField(max_length=15, unique=True, verbose_name="Mobile")
    role = models.CharField(max_length=20, choices=[("superadmin", "Super Admin"), ("stateadmin", "State Admin"), ("devicemanufacture", "Device Manufacture"), ("dealer", "Dealer"), ("owner", "Owner"), ("esimprovider", "eSimProvider"), ("filment", "Filment"), ("sosadmin", "SOS Admin"), ("teamleader", "Team Leader"), ("sosexecutive", "SOS Executive")], verbose_name="Role")
    usertype = models.CharField(max_length=10, default='main', verbose_name="User Type")
    createdby = models.CharField(max_length=255, verbose_name="Created By")
    date_joined = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    Access = models.JSONField(default=list, verbose_name="Access")
    password = models.CharField(max_length=100,default='12345678')  # Assuming 32 characters for MD5 hash
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address")
    address_pin = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address Pin")
    address_State = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address State")
    dob = models.CharField(max_length=255, blank=True, null=True, verbose_name="Date of Birth")
    status = models.CharField(max_length=10, choices=[("active", "Active"), ("deactive", "Deactive")], verbose_name="Status")

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
    users = models.ManyToManyField('User', related_name='manufacturers')
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
    hardware_version = models.CharField(max_length=255)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE)
    created = models.DateTimeField()
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    tac_doc_path = models.FileField(upload_to='tac_docs/', null=True, blank=True)


class DeviceStock(models.Model):
    model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE)
    device_esn = models.CharField(max_length=255)
    iccid = models.CharField(max_length=255)
    imei = models.CharField(max_length=255)
    telecom_provider1 = models.CharField(max_length=255)
    telecom_provider2 = models.CharField(max_length=255, blank=True, null=True)
    msisdn1 = models.CharField(max_length=255)
    msisdn2 = models.CharField(max_length=255, blank=True, null=True)
    imsi1 = models.CharField(max_length=255)
    imsi2 = models.CharField(max_length=255, blank=True, null=True)
    esim_validity = models.DateTimeField()
    esim_provider = models.CharField(max_length=255)
    remarks = models.TextField(blank=True, null=True)
    created = models.DateTimeField()
    created_by = models.ForeignKey('User', on_delete=models.CASCADE)

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

    def __str__(self):
        return f"{self.device_model} - COP: {self.cop_no}"
 
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

class DeviceTag(models.Model):
    STATUS_CHOICES = [
        ('Dealer_OTP_Sent', 'Dealer OTP Sent'),
        ('Dealer_OTP_Verified', 'Dealer OTP Verified'),
        ('Owner_OTP_Sent', 'Owner OTP Sent'),
        ('Owner_OTP_Verified', 'Owner OTP Verified'),
        ('RegNo_Configuration_SentToDevice', 'Reg No Configuration Sent to Device'),
        ('RegNo_Configuration_Confirmed', 'Reg No Configuration Confirmed'),
        ('Live_Location_Confirmed', 'Live Location Confirmed'),
        ('SOS_Confirmed', 'SOS Confirmed'),
        ('Device_Active', 'Device Active'),
        ('Device_Not_Active', 'Device Not Active'),
        ('Device_Untagged', 'Device Untagged'),
    ]

    device = models.ForeignKey(DeviceStock, on_delete=models.CASCADE)
    vehicle_owner = models.ForeignKey(User, on_delete=models.CASCADE)
   
    vehicle_reg_no = models.CharField(max_length=255)
    engine_no = models.CharField(max_length=255)
    chassis_no = models.CharField(max_length=255)
    vehicle_make = models.CharField(max_length=255)
    vehicle_model = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    rc_file = models.CharField(max_length=255)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    tagged_by = models.IntegerField()
    tagged = models.DateTimeField()
    def __str__(self):
        return self.vehicle_reg_no

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


class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deactive', 'Deactive'),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    access = models.ManyToManyField(User, related_name='accessible_vehicles', blank=True)
    vregno = models.CharField(max_length=255)
    engineno = models.CharField(max_length=255)
    chessisno = models.CharField(max_length=255)
    vehiclemake = models.CharField(max_length=255)
    vehiclemodel = models.CharField(max_length=255)
    vehiclecategory = models.CharField(max_length=255)
    rcfilepath = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    createdby = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_vehicles')
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.vregno

 
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
  