# skytron_api/serializers.py
from rest_framework import serializers
from .models import User, Manufacturer, Retailer, Device, DeviceModel, FOTA,  Session, OTPRequest, EditRequest, Settings

from .models import Manufacturer, Retailer, Device, DeviceModel
from .models import Confirmation
#from .models import Vehicle
from .models import DeviceStock,DeviceTag
from .models import *

from .models import VehicleOwner

        
class Settings_StateSerializer(serializers.ModelSerializer):
    #state_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_State
        fields = '__all__'

class DriverSerializer(serializers.ModelSerializer):
    #state_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Driver
        fields = '__all__'


class DeviceStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceStock
        fields = '__all__'   

class RetailerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Retailer
        fields = '__all__'  

class DeviceTagSerializer(serializers.ModelSerializer):
    class Meta:
        model =DeviceTag        
        exclude = ['otp','otp_time'] 



class UserSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        exclude = ['password'] 
        #fields = '__all__'    
    def get_created_by_name(self, obj):
        if obj.createdby:
            try: 
                created_by_user = User.objects.get(id=obj.createdby)
                return created_by_user.name
            except User.DoesNotExist:
                return ''
            except ValueError:
                return ''  
        return ''

class VehicleOwnerSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    class Meta:
        model = VehicleOwner 
        fields = '__all__'
class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver 
        fields = '__all__'



class VahanSerializer(serializers.ModelSerializer):
    device = DeviceStockSerializer(many=False, read_only=True) 
    vehicle_owner =VehicleOwnerSerializer(many=False, read_only=True)
   
    class Meta:
        model =DeviceTag
        fields = '__all__'

        

'''
class StockAssignmentSerializer(serializers.ModelSerializer):
    device = DeviceStockSerializer()  # Nested serializer for 'device' field
    dealer = RetailerSerializer()  
    class Meta:
        model = StockAssignment
        fields = ['device', 'dealer', 'assigned_by', 'assigned', 'shipping_remark', 'stock_status']

class StockAssignmentSerializer2(serializers.ModelSerializer):
    device = DeviceStockSerializer()  # Nested serializer for 'device' field
    dealer = RetailerSerializer()  
    class Meta:
        model = StockAssignment
        fields = ['device_id', 'dealer_id', 'assigned_by', 'assigned', 'shipping_remark', 'stock_status']
'''
class AlertsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertsLog
        fields = '__all__'
class DeviceStockFilterSerializer(serializers.Serializer):
    model_id = serializers.IntegerField(required=False)
    device_esn = serializers.CharField(required=False)
    iccid = serializers.CharField(required=False)
    imei = serializers.CharField(required=False)
    telecom_provider1 = serializers.CharField(required=False)
    telecom_provider2 = serializers.CharField(required=False)
    msisdn1 = serializers.CharField(required=False)
    msisdn2 = serializers.CharField(required=False)
    imsi1 = serializers.CharField(required=False)
    imsi2 = serializers.CharField(required=False)
    esim_validity = serializers.DateField(required=False)
    esim_provider = serializers.CharField(required=False)
    remarks = serializers.CharField(required=False)
    created_by_id = serializers.IntegerField(required=False)
    dealer_id= serializers.IntegerField(required=False)
    stock_status = serializers.CharField(required=False)
    esim_status = serializers.CharField(required=False)
    #is_tagged=serializers.CharField(required=False)
class DeviceModelFilterSerializer(serializers.Serializer):
    model_name = serializers.CharField(required=False)
    test_agency = serializers.CharField(required=False)
    vendor_id = serializers.CharField(required=False)
    tac_no = serializers.CharField(required=False)
    tac_validity = serializers.DateField(required=False)
    hardware_version = serializers.CharField(required=False)
    created_by_id = serializers.IntegerField(required=False)
    created = serializers.DateField(required=False)
    status = serializers.CharField(required=False)
class DeviceCOPSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceCOP
        #exclude = ['otp','otp_time'] 
        fields = '__all__' 
        

 

class UserSerializer2(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id","last_login","is_superuser","name","email", "mobile","role", "usertype","date_joined", "created","Access","is_active",  "address",   "address_pin",  "address_State",  "dob",  "status", "groups",  "user_permissions"]#'__all__'    #, deleting, list view of all , detail view.



class eSimProviderSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    class Meta:
        model = eSimProvider
        fields = '__all__'
class ManufacturerSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    state = Settings_StateSerializer(many=False, read_only=True)
    esim_provider = eSimProviderSerializer( many=True, read_only=True)
    #eSimProviders = serializers.PrimaryKeyRelatedField(many=True, queryset=eSimProvider.objects.all())
    class Meta:
        model = Manufacturer
        fields = '__all__'
class NoticeSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Notice
        fields = '__all__'

class RetailerSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    manufacturer=ManufacturerSerializer(many=False, read_only=True)
    class Meta:
        model = Retailer
        fields = '__all__'



class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'


class DeviceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModel
        fields = '__all__'
class DeviceStockSerializer2(serializers.ModelSerializer):
    #created_by_name = serializers.SerializerMethodField()
    model = DeviceModelSerializer(many=False, read_only=True)
    dealer  = RetailerSerializer(many=False, read_only=True)
    created_by = UserSerializer(many=False, read_only=True)
    esim_provider = eSimProviderSerializer(many=True, read_only=True)
    #is_tagged=serializers.CharField( )
    class Meta:
        model = DeviceStock
        fields = '__all__'

    #def get_created_by_name(self, obj):
    #    return obj.created_by.name if obj.created_by else ''
    #def get_device_model_name(self, obj):
    #    return obj.model.model_name if obj.created_by else ''


class FOTASerializer(serializers.ModelSerializer):
    class Meta:
        model = FOTA
        fields = '__all__'


class EsimActivationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = esimActivationRequest
        fields = '__all__'
 
 
class EsimActivationRequestSerializer_R(serializers.ModelSerializer):
    ceated_by = RetailerSerializer(read_only=True)
    eSim_provider=eSimProviderSerializer(read_only=True)
    device=DeviceStockSerializer(read_only=True)
    class Meta:
        model = esimActivationRequest
        fields = '__all__'
 
    

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'

class OTPRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPRequest
        fields = '__all__'

class EditRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditRequest
        fields = '__all__'

class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = '__all__'
class ConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Confirmation
        fields = '__all__'


  

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'


class DeviceModelSerializer(serializers.ModelSerializer):
    eSimProviders = serializers.PrimaryKeyRelatedField(many=True, queryset=eSimProvider.objects.all())
    #eSimProviders = eSimProviderSerializer( many=True, read_only=True)

    class Meta:
        model = DeviceModel
        fields = '__all__'
class DeviceModelSerializer_disp(serializers.ModelSerializer):
    #eSimProviders = serializers.PrimaryKeyRelatedField(many=True, queryset=eSimProvider.objects.all())
    eSimProviders = eSimProviderSerializer( many=True, read_only=True)
    created_by=UserSerializer( read_only=True)

    class Meta:
        model = DeviceModel
        fields = '__all__'

class Settings_hp_freqSerializer(serializers.ModelSerializer):
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_hp_freq
        fields = '__all__'

        
       
class Settings_firmwareSerializer(serializers.ModelSerializer):
    #state_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_firmware
        fields = '__all__'


class Settings_DistrictSerializer(serializers.ModelSerializer):
    state_info = Settings_StateSerializer(source='state', read_only=True)
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_District
        fields = '__all__'

class Settings_VehicleCategorySerializer(serializers.ModelSerializer):
    #state_info = Settings_StateSerializer(source='state', read_only=True)
    #devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_VehicleCategory
        fields = '__all__'


    
class Settings_ipSerializer(serializers.ModelSerializer):
    state_info = Settings_StateSerializer(source='state', read_only=True)
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_ip
        fields = '__all__'


class DeviceModelFileUploadSerializer(serializers.ModelSerializer):
    tac_doc_path = serializers.FileField(write_only=True)

    class Meta:
        model = DeviceModel
        fields = '__all__'



class GPSData_Serializer(serializers.ModelSerializer):
    entry_time = serializers.DateTimeField()
    packet_status = serializers.CharField( )
    #imei = serializers.CharField()
    #rn = serializers.CharField(source='vehicle_registration_number')
    latitude = serializers.CharField()
    #latitudeDir = serializers.CharField(source='latitude_dir')
    longitude  = serializers.CharField()
    #longitudeDir = serializers.CharField(source='longitude_dir')  
    speed = serializers.CharField()
    heading  = serializers.CharField()
    satellites  = serializers.CharField()
    gps_status  = serializers.CharField()
    altitude  = serializers.CharField()
    #pdop = serializers.CharField()
    #hdop = serializers.CharField()
    network_operator = serializers.CharField()
    ignition_status = serializers.CharField()
    main_power_status = serializers.CharField()
    main_input_voltage = serializers.CharField()
    internal_battery_voltage = serializers.CharField()
    emergency_status = serializers.CharField()
    box_tamper_alert = serializers.CharField()
    gsm_signal_strength = serializers.CharField()
    #mcc = serializers.CharField()
    #mnc = serializers.CharField()
    #lac = serializers.CharField()
    #cellId = serializers.CharField(source='cell_id')
    #nbr1CellId = serializers.CharField(source='nbr1_cell_id')
    #nbr1Lac = serializers.CharField(source='nbr1_lac')
    #nbr1SignalStrength = serializers.CharField(source='nbr1_signal_strength')
    #nbr2CellId = serializers.CharField(source='nbr2_cell_id')
    #nbr2Lac = serializers.CharField(source='nbr2_lac')
    #nbr2SignalStrength = serializers.CharField(source='nbr2_signal_strength')
    #nbr3CellId = serializers.CharField(source='nbr3_cell_id')
    #nbr3Lac = serializers.CharField(source='nbr3_lac')
    #nbr3SignalStrength = serializers.CharField(source='nbr3_signal_strength')
    #nbr4CellId = serializers.CharField(source='nbr4_cell_id')
    #nbr4Lac = serializers.CharField(source='nbr4_lac')
    #nbr4SignalStrength = serializers.CharField(source='nbr4_signal_strength')
    digital_input_status = serializers.CharField()
    digital_output_status = serializers.CharField() 
    odometer = serializers.CharField()
    packet_type= serializers.CharField()
    











    
    class Meta:
        model = GPSData
        fields = ["entry_time","packet_status","latitude","longitude","speed","heading","satellites","gps_status","altitude","network_operator","ignition_status","main_power_status","main_input_voltage","internal_battery_voltage","emergency_status","box_tamper_alert","gsm_signal_strength","digital_input_status","digital_output_status","frame_number","odometer","packet_type"]
        ''' entryTime', 'packetStatus', 'imei', 'vehicleRegistrationNumber',
                  'latitude',  'longitude',#'latitudeDir', 'longitudeDir',
                  'speed', 'heading', 'satellites', 'gpsStatus', 'altitude',
                  'pdop', 'hdop', 'networkOperator', 'ignitionStatus',
                  'mainPowerStatus', 'mainInputVoltage', 'internalBatteryVoltage',
                  'emergencyStatus', 'boxTamperAlert', 'gsmSignalStrength',
                  'mcc', 'mnc', 'lac', 'cellId',# 'nbr1CellId', 'nbr1Lac',
                  #'nbr1SignalStrength', 'nbr2CellId', 'nbr2Lac', 'nbr2SignalStrength',
                  #'nbr3CellId', 'nbr3Lac', 'nbr3SignalStrength', 'nbr4CellId',
                  #'nbr4Lac', 'nbr4SignalStrength', 
                  'digitalInputStatus',
                  'digitalOutputStatus', 'frameNumber', 'odometer']'''

class GPSData_modSerializer(serializers.ModelSerializer):
    et = serializers.DateTimeField(source='entry_time')
    ps = serializers.CharField(source='packet_status')
    #imei = serializers.CharField()
    #rn = serializers.CharField(source='vehicle_registration_number')
    lat = serializers.CharField(source='latitude')
    #latitudeDir = serializers.CharField(source='latitude_dir')
    lon  = serializers.CharField(source='longitude')
    #longitudeDir = serializers.CharField(source='longitude_dir')  
    s = serializers.CharField(source='speed')
    h  = serializers.CharField(source='heading')
    sat  = serializers.CharField(source='satellites')
    gpsS  = serializers.CharField(source='gps_status')
    alt  = serializers.CharField(source='altitude')
    #pdop = serializers.CharField()
    #hdop = serializers.CharField()
    no = serializers.CharField(source='network_operator')
    igs = serializers.CharField(source='ignition_status')
    mps = serializers.CharField(source='main_power_status')
    miv = serializers.CharField(source='main_input_voltage')
    ibv = serializers.CharField(source='internal_battery_voltage')
    ems = serializers.CharField(source='emergency_status')
    bta = serializers.CharField(source='box_tamper_alert')
    gss = serializers.CharField(source='gsm_signal_strength')
    #mcc = serializers.CharField()
    #mnc = serializers.CharField()
    #lac = serializers.CharField()
    #cellId = serializers.CharField(source='cell_id')
    #nbr1CellId = serializers.CharField(source='nbr1_cell_id')
    #nbr1Lac = serializers.CharField(source='nbr1_lac')
    #nbr1SignalStrength = serializers.CharField(source='nbr1_signal_strength')
    #nbr2CellId = serializers.CharField(source='nbr2_cell_id')
    #nbr2Lac = serializers.CharField(source='nbr2_lac')
    #nbr2SignalStrength = serializers.CharField(source='nbr2_signal_strength')
    #nbr3CellId = serializers.CharField(source='nbr3_cell_id')
    #nbr3Lac = serializers.CharField(source='nbr3_lac')
    #nbr3SignalStrength = serializers.CharField(source='nbr3_signal_strength')
    #nbr4CellId = serializers.CharField(source='nbr4_cell_id')
    #nbr4Lac = serializers.CharField(source='nbr4_lac')
    #nbr4SignalStrength = serializers.CharField(source='nbr4_signal_strength')
    dis = serializers.CharField(source='digital_input_status')
    dos = serializers.CharField(source='digital_output_status')
    fn = serializers.CharField(source='frame_number')
    om = serializers.CharField(source='odometer')
    ps= serializers.CharField(source='packet_type')
    

    class Meta:
        model = GPSData
        fields = [ 'et','ps',#'imei',  'rn',
                  'lat','lon','s','h','sat','gpsS','alt','no','igs',
                  'mps','miv','ibv','ems','bta','gss','dis','dos','fn','om','ps']
        ''' entryTime', 'packetStatus', 'imei', 'vehicleRegistrationNumber',
                  'latitude',  'longitude',#'latitudeDir', 'longitudeDir',
                  'speed', 'heading', 'satellites', 'gpsStatus', 'altitude',
                  'pdop', 'hdop', 'networkOperator', 'ignitionStatus',
                  'mainPowerStatus', 'mainInputVoltage', 'internalBatteryVoltage',
                  'emergencyStatus', 'boxTamperAlert', 'gsmSignalStrength',
                  'mcc', 'mnc', 'lac', 'cellId',# 'nbr1CellId', 'nbr1Lac',
                  #'nbr1SignalStrength', 'nbr2CellId', 'nbr2Lac', 'nbr2SignalStrength',
                  #'nbr3CellId', 'nbr3Lac', 'nbr3SignalStrength', 'nbr4CellId',
                  #'nbr4Lac', 'nbr4SignalStrength', 
                  'digitalInputStatus',
                  'digitalOutputStatus', 'frameNumber', 'odometer']'''

class GPSdata_vehIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = GPSData
        fields = ('vehicle_registration_number', 'imei') 
class StateadminSerializer(serializers.ModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)

    class Meta:
        model = StateAdmin
        fields = '__all__'
class routeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id" ,"device_id","createdby_id","route","routepoints")

class dto_rtoSerializer(serializers.ModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    #district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = dto_rto
        fields = '__all__'


class EM_exSerializer(serializers.ModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = EM_ex
        fields = '__all__'


 
class EMTeamSerializer(serializers.ModelSerializer):
    
    #admin = SOS_AdminSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='created_by', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)
    teamlead_info =EM_exSerializer(source='teamlead', read_only=True)
    members_info =EM_exSerializer(source='members', read_only=True,many=True)  
    class Meta:
        model = EMTeams
        fields = '__all__' 
 

        
class EM_adminSerializer(serializers.ModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = EM_admin
        fields = '__all__' 


class EMGPSLocationSerializer11(serializers.ModelSerializer):
    class Meta:
        model = EMGPSLocation
        fields ='__all__'    # Specify relevant fields

class DeviceTagSerializer2(serializers.ModelSerializer):
    device = DeviceStockSerializer2(many=False, read_only=True)
    vehicle_owner = VehicleOwnerSerializer(many=False, read_only=True)
    drivers = DriverSerializer(many=True, read_only=True)
    deviceloc = serializers.SerializerMethodField()

    class Meta:
        model = DeviceTag
        #fields = '__all__' #
        exclude = ['otp', 'otp_time']

    def get_deviceloc(self, obj):
        locations = EMGPSLocation.objects.filter(device_tag=obj.id).order_by('-id')[:10]
        return EMGPSLocationSerializer11(locations, many=True).data




class EMTeamsSerializer(serializers.ModelSerializer):  
    state = Settings_StateSerializer( read_only=True)
    teamlead =EM_exSerializer(  read_only=True)
    members=EM_exSerializer(  many=True,read_only=True)
    created_by = EM_adminSerializer( read_only=True)
 
    class Meta:
        model = EMTeams 
        fields = '__all__'  
 


class EMCallSerializer(serializers.ModelSerializer):  
    team  = EMTeamsSerializer(  read_only=True)
    device = DeviceTagSerializer2( read_only=True) 

    class Meta:
        model = EMCall 
        fields = '__all__'  



class EMCallAssignmentSerializer(serializers.ModelSerializer):  
    admin = EM_adminSerializer(  read_only=True)
    ex =EM_exSerializer(  read_only=True)
    call=EMCallSerializer(  read_only=True) 
    class Meta:
        model = EMCallAssignment 
        fields = '__all__'  



class EMCallMessagesSerializer(serializers.ModelSerializer):  
    assignment =EMCallAssignmentSerializer( read_only=True)
    call=EMCallSerializer(  read_only=True) 
    class Meta:
        model = EMCallMessages
        fields = '__all__'  


 
class EMCallBackupRequestSerializer(serializers.ModelSerializer):  
    assignment =EMCallAssignmentSerializer(source='ex', read_only=True)
    call=EMCallSerializer( read_only=True) 
    class Meta:
        model = EMCallBackupRequest
        fields = '__all__'  

class EMCallBroadcastSerializer(serializers.ModelSerializer):   
    call=EMCallSerializer(  read_only=True) 
    class Meta:
        model = EMCallBroadcast
        fields = '__all__'  


 
class EMUserLocationSerializer(serializers.ModelSerializer):  
    field_ex =EM_exSerializer( read_only=True)
    call=EMCallSerializer( read_only=True) 
    class Meta:
        model = EMUserLocation
        fields = '__all__'  


 

class AlertsLogSerializer(serializers.ModelSerializer):

    gps_ref=GPSData_Serializer(read_only=True)
    route_ref=routeSerializer(read_only=True)
    #em_ref=models.ForeignKey("EMCall", on_delete=models.CASCADE,null=True, blank=True) 
    deviceTag=DeviceTagSerializer2(read_only=True) 
    state=Settings_StateSerializer( read_only=True)
    class Meta:
        model = AlertsLog
        fields = '__all__'

