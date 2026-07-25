# Serializer for GSM cell info input (cell location API)

# skytron_api/serializers.py
from rest_framework import serializers
from .models import User, Manufacturer, Dealer, Device, DeviceModel, FOTA,  Session, OTPRequest, EditRequest, Settings

from .models import Manufacturer, Dealer, Device, DeviceModel
from .models import Confirmation
#from .models import Vehicle
from .models import DeviceStock,DeviceTag
from .models import *

import bleach
from .models import VehicleOwner


class GSMCellInfoInputSerializer(serializers.Serializer):
    gsm_signal_strength = serializers.CharField(max_length=5, required=False)
    mcc = serializers.CharField(max_length=6)
    mnc = serializers.CharField(max_length=6)
    lac = serializers.CharField(max_length=6)
    cell_id = serializers.CharField(max_length=6, required=False)
    nbr1_cell_id = serializers.CharField(max_length=6, required=False)
    nbr1_lac = serializers.CharField(max_length=6, required=False)
    nbr1_signal_strength = serializers.CharField(max_length=6, required=False)
    nbr2_cell_id = serializers.CharField(max_length=6, required=False)
    nbr2_lac = serializers.CharField(max_length=6, required=False)
    nbr2_signal_strength = serializers.CharField(max_length=4, required=False)
    nbr3_cell_id = serializers.CharField(max_length=6, required=False)
    nbr3_lac = serializers.CharField(max_length=6, required=False)
    nbr3_signal_strength = serializers.CharField(max_length=6, required=False)
    nbr4_cell_id = serializers.CharField(max_length=6, required=False)
    nbr4_lac = serializers.CharField(max_length=6, required=False)
    nbr4_signal_strength = serializers.CharField(max_length=6, required=False)


class SanitizingModelSerializer(serializers.ModelSerializer ):
    def validate(self, data):
        # Sanitize all fields
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = bleach.clean(value)
        return data

        
class Settings_StateSerializer(SanitizingModelSerializer):
    #state_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_State
        fields = '__all__'

class DriverSerializer(SanitizingModelSerializer):
    #state_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Driver
        fields = '__all__'


class DeviceStockSerializer(SanitizingModelSerializer):
    class Meta:
        model = DeviceStock
        fields = '__all__'   


class DeviceTagSerializer(SanitizingModelSerializer):
    category_info = serializers.SerializerMethodField()
    category_code_info = serializers.SerializerMethodField()

    def get_category_info(self, obj):
        try:
            cat_obj = obj.category
            if cat_obj:
                return Settings_VehicleCategorySerializer(cat_obj).data
        except Exception:
            pass
        return None

    def get_category_code_info(self, obj):
        try:
            cc_obj = obj.category_code
            if cc_obj:
                return Settings_VehicleCategoryCodeSerializer(cc_obj).data
        except Exception:
            pass
        return None

    class Meta:
        model = DeviceTag
        exclude = ['otp', 'otp_time']

class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = ['device_tag', 'camera_id', 'start_time', 'end_time', 'media_type', 'media_link', 'duration_ms', 'alert_type', 'message']
        

class UserSerializer(SanitizingModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        exclude = ['password','dob'] 
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

class VehicleOwnerSerializer(SanitizingModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    class Meta:
        model = VehicleOwner 
        fields = '__all__'
class DriverSerializer(SanitizingModelSerializer):
    class Meta:
        model = Driver 
        fields = '__all__'



class VahanSerializer(SanitizingModelSerializer):
    device = DeviceStockSerializer(many=False, read_only=True) 
    vehicle_owner =VehicleOwnerSerializer(many=False, read_only=True)
   
    class Meta:
        model =DeviceTag
        fields = '__all__'

        

'''
class StockAssignmentSerializer(SanitizingModelSerializer):
    device = DeviceStockSerializer()  # Nested serializer for 'device' field
    dealer = DealerSerializer()  
    class Meta:
        model = StockAssignment
        fields = ['device', 'dealer', 'assigned_by', 'assigned', 'shipping_remark', 'stock_status']

class StockAssignmentSerializer2(SanitizingModelSerializer):
    device = DeviceStockSerializer()  # Nested serializer for 'device' field
    dealer = DealerSerializer()  
    class Meta:
        model = StockAssignment
        fields = ['device_id', 'dealer_id', 'assigned_by', 'assigned', 'shipping_remark', 'stock_status']
'''
class AlertsLogSerializer(SanitizingModelSerializer):
    device_info = DeviceTagSerializer(source='deviceTag', read_only=True)
    gps_info = serializers.SerializerMethodField()
    route_info = serializers.SerializerMethodField()
    state_info = Settings_StateSerializer(source='state', read_only=True)
    
    class Meta:
        model = AlertsLog
        fields = '__all__'
    
    def get_gps_info(self, obj):
        if obj.gps_ref:
            return {
                'latitude': obj.gps_ref.latitude,
                'longitude': obj.gps_ref.longitude,
                'date': obj.gps_ref.date,
                'time': obj.gps_ref.time
            }
        return None
    
    def get_route_info(self, obj):
        if obj.route_ref:
            return {
                'id': obj.route_ref.id,
                'status': obj.route_ref.status
            }
        return None

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


class DeviceStockUploadBatchSerializer(SanitizingModelSerializer):
    class Meta:
        model = DeviceStockUploadBatch
        fields = '__all__'


class DeviceStockUntaggedFilterSerializer(serializers.Serializer):
    # Partial (icontains) match fields
    imei = serializers.CharField(required=False)
    iccid = serializers.CharField(required=False)
    iccid2 = serializers.CharField(required=False)
    msisdn1 = serializers.CharField(required=False)
    msisdn2 = serializers.CharField(required=False)
    imsi1 = serializers.CharField(required=False)
    imsi2 = serializers.CharField(required=False)
    device_esn = serializers.CharField(required=False)
    telecom_provider1 = serializers.CharField(required=False)
    telecom_provider2 = serializers.CharField(required=False)
    remarks = serializers.CharField(required=False)
    upload_file_name = serializers.CharField(required=False)

    # Exact match fields
    model_id = serializers.IntegerField(required=False)
    stock_status = serializers.CharField(required=False)
    esim_status = serializers.CharField(required=False)
    dealer_id = serializers.IntegerField(required=False)
    unassigned_only = serializers.BooleanField(required=False)
    upload_batch_id = serializers.IntegerField(required=False)

    # Pagination
    page = serializers.IntegerField(required=False)
    page_size = serializers.IntegerField(required=False)


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
class DeviceCOPSerializer(SanitizingModelSerializer):
    class Meta:
        model = DeviceCOP
        #exclude = ['otp','otp_time'] 
        fields = '__all__' 
        

 

class UserSerializer2(SanitizingModelSerializer):
    class Meta:
        model = User
        fields = ["id","last_login","is_superuser","name","email", "mobile","role", "usertype","date_joined", "created","Access","is_active",  "address",   "address_pin",  "address_State",  "dob",  "status", "groups",  "user_permissions"]#'__all__'    #, deleting, list view of all , detail view.



class eSimProviderSerializer(SanitizingModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    state = Settings_StateSerializer(many=False, read_only=True)
    class Meta:
        model = eSimProvider
        fields = '__all__'


class TestAgencySerializer(SanitizingModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    class Meta:
        model = TestAgency
        fields = '__all__'


class TestAgencyDetailsSerializer(SanitizingModelSerializer):
    class Meta:
        model = TestAgencyDetails
        fields = '__all__'


class ManufacturerSerializer(SanitizingModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    state = Settings_StateSerializer(many=False, read_only=True)
    esim_provider = eSimProviderSerializer( many=True, read_only=True)
    #eSimProviders = serializers.PrimaryKeyRelatedField(many=True, queryset=eSimProvider.objects.all())
    class Meta:
        model = Manufacturer
        fields = '__all__'
        
class NoticeSerializer(SanitizingModelSerializer): 
    class Meta:
        model = Notice
        fields = '__all__'

class DealerSerializer2(SanitizingModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    manufacturer=ManufacturerSerializer(many=False, read_only=True)
    districts = serializers.SerializerMethodField()
    
    def get_districts(self, obj):
        districts_data = []
        for district in obj.districts.all():
            districts_data.append({
                'id': district.id,
                'district': district.district,
                'district_code': district.district_code,
                'status': district.status,
                'state': {
                    'id': district.state.id,
                    'state': district.state.state,
                    'status': district.state.status,
                } if district.state else None
            })
        return districts_data
    
    class Meta:
        model = Dealer
        fields = '__all__'



class DeviceSerializer(SanitizingModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'


class DeviceModelSerializer(SanitizingModelSerializer):
    class Meta:
        model = DeviceModel
        fields = '__all__'
class DeviceStockSerializer2(SanitizingModelSerializer):
    #created_by_name = serializers.SerializerMethodField()
    model = DeviceModelSerializer(many=False, read_only=True)
    dealer  = DealerSerializer2(many=False, read_only=True)
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


class FOTASerializer(SanitizingModelSerializer):
    class Meta:
        model = FOTA
        fields = '__all__'


class EsimActivationRequestSerializer(SanitizingModelSerializer):
    class Meta:
        model = esimActivationRequest
        fields = '__all__'
 
 
class EsimActivationRequestSerializer_R(SanitizingModelSerializer):
    ceated_by = DealerSerializer2(read_only=True)
    eSim_provider=eSimProviderSerializer(read_only=True)
    device=DeviceStockSerializer(read_only=True)
    class Meta:
        model = esimActivationRequest
        fields = '__all__'
 
    

class SessionSerializer(SanitizingModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'

class OTPRequestSerializer(SanitizingModelSerializer):
    class Meta:
        model = OTPRequest
        fields = '__all__'

class EditRequestSerializer(SanitizingModelSerializer):
    class Meta:
        model = EditRequest
        fields = '__all__'

class SettingsSerializer(SanitizingModelSerializer):
    class Meta:
        model = Settings
        fields = '__all__'
class ConfirmationSerializer(SanitizingModelSerializer):
    class Meta:
        model = Confirmation
        fields = '__all__'


  

class DeviceSerializer(SanitizingModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'


class DeviceModelSerializer(SanitizingModelSerializer):
    eSimProviders = serializers.PrimaryKeyRelatedField(many=True, queryset=eSimProvider.objects.all())
    #eSimProviders = eSimProviderSerializer( many=True, read_only=True)

    class Meta:
        model = DeviceModel
        fields = '__all__'
class DeviceModelSerializer_disp(SanitizingModelSerializer):
    #eSimProviders = serializers.PrimaryKeyRelatedField(many=True, queryset=eSimProvider.objects.all())
    eSimProviders = eSimProviderSerializer( many=True, read_only=True)
    created_by=UserSerializer( read_only=True)

    class Meta:
        model = DeviceModel
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        # Only include necessary fields based on context
        super(DeviceModelSerializer_disp, self).__init__(*args, **kwargs)

        # Optional optimization: If a fields parameter is passed, only serialize those fields
        request = self.context.get('request')
        if request and request.query_params.get('fields'):
            fields = request.query_params.get('fields').split(',')
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.context.get('show_mqtt_pw'):
            data.pop('mqtt_pw', None)
        return data


class Settings_hp_freqSerializer(SanitizingModelSerializer):
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_hp_freq
        fields = '__all__'

        
       
class Settings_firmwareSerializer(SanitizingModelSerializer):
    #state_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_firmware
        fields = '__all__'


class Settings_DistrictSerializer(SanitizingModelSerializer):
    state_info = Settings_StateSerializer(source='state', read_only=True)
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_District
        fields = '__all__'

class Settings_VehicleCategorySerializer(SanitizingModelSerializer):
    #state_info = Settings_StateSerializer(source='state', read_only=True)
    #devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    #createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_VehicleCategory
        fields = '__all__'


    
class Settings_VehicleCategoryCodeSerializer(SanitizingModelSerializer):
    class Meta:
        model = Settings_VehicleCategoryCode
        fields = '__all__'


class Settings_PermitMasterSerializer(SanitizingModelSerializer):
    class Meta:
        model = Settings_PermitMaster
        fields = '__all__'


class Settings_ipSerializer(SanitizingModelSerializer):
    state_info = Settings_StateSerializer(source='state', read_only=True)
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_ip
        fields = '__all__'


class DeviceModelFileUploadSerializer(SanitizingModelSerializer):
    tac_doc_path = serializers.FileField(write_only=True)

    class Meta:
        model = DeviceModel
        fields = '__all__'



class GPSData_Serializer(SanitizingModelSerializer):
    entry_time = serializers.DateTimeField()
    packet_type = serializers.CharField()
    alert_id = serializers.CharField()
    packet_status = serializers.CharField()
    gps_status = serializers.CharField()
    date = serializers.CharField()
    time = serializers.CharField()
    latitude = serializers.CharField()
    latitude_dir = serializers.CharField()
    longitude = serializers.CharField()
    longitude_dir = serializers.CharField()
    speed = serializers.CharField()
    heading = serializers.CharField()
    satellites = serializers.CharField()
    altitude = serializers.CharField()
    pdop = serializers.CharField()
    hdop = serializers.CharField()
    network_operator = serializers.CharField()
    ignition_status = serializers.CharField()
    main_power_status = serializers.CharField()
    main_input_voltage = serializers.CharField()
    internal_battery_voltage = serializers.CharField()
    emergency_status = serializers.CharField()
    box_tamper_alert = serializers.CharField()
    gsm_signal_strength = serializers.CharField()
    mcc = serializers.CharField()
    mnc = serializers.CharField()
    lac = serializers.CharField()
    cell_id = serializers.CharField()
    nbr1_cell_id = serializers.CharField()
    nbr1_lac = serializers.CharField()
    nbr1_signal_strength = serializers.CharField()
    nbr2_cell_id = serializers.CharField()
    nbr2_lac = serializers.CharField()
    nbr2_signal_strength = serializers.CharField()
    nbr3_cell_id = serializers.CharField()
    nbr3_lac = serializers.CharField()
    nbr3_signal_strength = serializers.CharField()
    nbr4_cell_id = serializers.CharField()
    nbr4_lac = serializers.CharField()
    nbr4_signal_strength = serializers.CharField()
    digital_input_status = serializers.CharField()
    digital_output_status = serializers.CharField()
    frame_number = serializers.IntegerField()
    odometer = serializers.CharField()
    
    class Meta:
        model = GPSData
        fields = [
            "entry_time", "packet_type", "alert_id", "packet_status", "gps_status",
            "date", "time", "latitude", "latitude_dir", "longitude", "longitude_dir",
            "speed", "heading", "satellites", "altitude", "pdop", "hdop",
            "network_operator", "ignition_status", "main_power_status",
            "main_input_voltage", "internal_battery_voltage", "emergency_status",
            "box_tamper_alert", "gsm_signal_strength", "mcc", "mnc", "lac", "cell_id",
            "nbr1_cell_id", "nbr1_lac", "nbr1_signal_strength",
            "nbr2_cell_id", "nbr2_lac", "nbr2_signal_strength",
            "nbr3_cell_id", "nbr3_lac", "nbr3_signal_strength",
            "nbr4_cell_id", "nbr4_lac", "nbr4_signal_strength",
            "digital_input_status", "digital_output_status", "frame_number", "odometer"
        ]
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

class GPSData_modSerializer(SanitizingModelSerializer):
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

class GPSdata_vehIdentitySerializer(SanitizingModelSerializer):
    class Meta:
        model = GPSData
        fields = ('vehicle_registration_number', 'imei') 
class StateadminSerializer(SanitizingModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)

    class Meta:
        model = StateAdmin
        fields = '__all__'
class routeSerializer(SanitizingModelSerializer):
    class Meta:
        model = Route
        fields = ("id" ,"device_id","createdby_id","route","routepoints")

class dto_rtoSerializer(SanitizingModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    #district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = dto_rto
        fields = '__all__'


class EM_exSerializer(SanitizingModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = EM_ex
        fields = '__all__'


 
class EMTeamSerializer(SanitizingModelSerializer):
    
    #admin = SOS_AdminSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='created_by', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)
    teamlead_info =EM_exSerializer(source='teamlead', read_only=True)
    members_info =EM_exSerializer(source='members', read_only=True,many=True)  
    class Meta:
        model = EMTeams
        fields = '__all__' 
 

        
class EM_adminSerializer(SanitizingModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = EM_admin
        fields = '__all__' 


class EMGPSLocationSerializer11(SanitizingModelSerializer):
    class Meta:
        model = EMGPSLocation
        fields ='__all__'    # Specify relevant fields

class DeviceTagSerializer2(SanitizingModelSerializer):
    device = DeviceStockSerializer2(many=False, read_only=True)
    vehicle_owner = VehicleOwnerSerializer(many=False, read_only=True)
    drivers = DriverSerializer(many=True, read_only=True)
    category = Settings_VehicleCategorySerializer(many=False, read_only=True)
    category_code = Settings_VehicleCategoryCodeSerializer(many=False, read_only=True)
    deviceloc = serializers.SerializerMethodField()

    class Meta:
        model = DeviceTag
        #fields = '__all__' #
        exclude = ['otp', 'otp_time']

    def get_deviceloc(self, obj):
        def _format_date(date_value):
            """Convert GPSData.date into EMGPSLocationSerializer11-like 'YYYY-MM-DD' string when possible."""
            if not date_value:
                return None
            s = str(date_value).strip()
            if len(s) != 8 or not s.isdigit():
                return s
            # Heuristic: YYYYMMDD if starts with plausible year, else DDMMYYYY
            try:
                year = int(s[:4])
                if 2000 <= year <= 2100:
                    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
                return f"{s[4:8]}-{s[2:4]}-{s[0:2]}"
            except Exception:
                return s

        def _format_time(time_value):
            """Convert GPSData.time into EMGPSLocationSerializer11-like 'HH:MM:SS' string when possible."""
            if not time_value:
                return None
            s = str(time_value).strip()
            if len(s) != 6 or not s.isdigit():
                return s
            return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"

        # Fast path: use prefetched GPSData model instances if provided by the view.
        prefetched_models = getattr(obj, '_prefetched_gps', None)
        if prefetched_models is not None:
            gps_vals = [
                {
                    'id': g.id,
                    'date': g.date,
                    'time': g.time,
                    'latitude': g.latitude,
                    'latitude_dir': g.latitude_dir,
                    'longitude': g.longitude,
                    'longitude_dir': g.longitude_dir,
                    'altitude': g.altitude,
                    'speed': g.speed,
                    'network_operator': g.network_operator,
                    'device_tag_id': g.device_tag_id,
                }
                for g in prefetched_models[:10]
            ]
        else:
            # Secondary fast path: allow views to attach precomputed `.values()` dicts.
            prefetched_vals = getattr(obj, '_prefetched_gps_vals', None)
            if prefetched_vals is not None:
                gps_vals = prefetched_vals[:10]
            else:
                gps_vals = list(
                    GPSData.objects
                    .filter(device_tag=obj.id, gps_status='1')
                    .order_by('-id')[:10]
                    .values(
                        'id',
                        'date',
                        'time',
                        'latitude',
                        'latitude_dir',
                        'longitude',
                        'longitude_dir',
                        'altitude',
                        'speed',
                        'network_operator',
                        'device_tag_id',
                    )
                )

        device_imei = None
        try:
            device_imei = obj.device.imei if getattr(obj, 'device', None) else None
        except Exception:
            device_imei = None

        return [
            {
                'id': g.get('id'),
                'message_type': 'EMR',
                'device_imei': device_imei,
                'packet_status': 'NM',
                'date': _format_date(g.get('date')),
                'time': _format_time(g.get('time')),
                'gps_validity': 'A',
                'latitude': g.get('latitude'),
                'latitude_direction': g.get('latitude_dir'),
                'longitude': g.get('longitude'),
                'longitude_direction': g.get('longitude_dir'),
                'altitude': g.get('altitude'),
                'speed': g.get('speed'),
                'distance': 0,
                'provider': g.get('network_operator'),
                'vehicle_reg_no': getattr(obj, 'vehicle_reg_no', None),
                'reply_mob_no': '9401633421',
                'device_tag': g.get('device_tag_id') or obj.id,
            }
            for g in gps_vals
        ]




class EMTeamsSerializer(SanitizingModelSerializer):  
    state = Settings_StateSerializer( read_only=True)
    teamlead =EM_exSerializer(  read_only=True)
    members=EM_exSerializer(  many=True,read_only=True)
    created_by = EM_adminSerializer( read_only=True)
 
    class Meta:
        model = EMTeams 
        fields = '__all__'  
 


class EMCallSerializer(SanitizingModelSerializer):  
    team  = EMTeamsSerializer(  read_only=True)
    device = DeviceTagSerializer2( read_only=True) 

    class Meta:
        model = EMCall 
        fields = '__all__'  



class EMCallAssignmentSerializer(SanitizingModelSerializer):  
    admin = EM_adminSerializer(  read_only=True)
    ex =EM_exSerializer(  read_only=True)
    call=EMCallSerializer(  read_only=True) 
    class Meta:
        model = EMCallAssignment 
        fields = '__all__'  



class EMCallMessagesSerializer(SanitizingModelSerializer):  
    assignment =EMCallAssignmentSerializer( read_only=True)
    call=EMCallSerializer(  read_only=True) 
    class Meta:
        model = EMCallMessages
        fields = '__all__'  


 
class EMCallBackupRequestSerializer(SanitizingModelSerializer):  
    assignment =EMCallAssignmentSerializer(source='ex', read_only=True)
    call=EMCallSerializer( read_only=True) 
    class Meta:
        model = EMCallBackupRequest
        fields = '__all__'  

class EMCallBroadcastSerializer(SanitizingModelSerializer):   
    call=EMCallSerializer(  read_only=True) 
    class Meta:
        model = EMCallBroadcast
        fields = '__all__'  


 
class EMUserLocationSerializer(SanitizingModelSerializer):  
    field_ex =EM_exSerializer( read_only=True)
    call=EMCallSerializer( read_only=True) 
    class Meta:
        model = EMUserLocation
        fields = '__all__'  


 

class AlertsLogSerializer(SanitizingModelSerializer):

    gps_ref=GPSData_Serializer(read_only=True)
    route_ref=routeSerializer(read_only=True)
    #em_ref=models.ForeignKey("EMCall", on_delete=models.CASCADE,null=True, blank=True) 
    deviceTag=DeviceTagSerializer2(read_only=True) 
    state=Settings_StateSerializer( read_only=True)
    class Meta:
        model = AlertsLog
        fields = '__all__'

class TripDetailSerializer(serializers.Serializer):
    trip_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    duration_minutes = serializers.FloatField()
    distance_km = serializers.FloatField()
    average_speed_kmh = serializers.FloatField()
    max_speed_kmh = serializers.FloatField()
    start_location = serializers.DictField()
    end_location = serializers.DictField()
    alerts = serializers.ListField()
    total_data_points = serializers.IntegerField()

class TripListResponseSerializer(serializers.Serializer):
    device_tag_id = serializers.IntegerField()
    vehicle_reg_no = serializers.CharField()
    query_start_time = serializers.DateTimeField()
    query_end_time = serializers.DateTimeField()
    total_trips = serializers.IntegerField()
    total_distance_km = serializers.FloatField()
    total_duration_minutes = serializers.FloatField()
    trips = TripDetailSerializer(many=True)


class DealerSerializer(SanitizingModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    manufacturer = ManufacturerSerializer(many=False, read_only=True)
    districts = Settings_DistrictSerializer(many=True, read_only=True)
    
    class Meta:
        model = Dealer
        fields = '__all__'  


class BusStandSerializer(SanitizingModelSerializer):
    created_by_info = UserSerializer(source='created_by', read_only=True)
    
    class Meta:
        model = BusStand
        fields = '__all__'


class OTASettingsSerializer(SanitizingModelSerializer):
    triggered_by_info = UserSerializer(source='triggered_by', read_only=True)

    class Meta:
        model = OTASettings
        fields = '__all__'


class OTACommandDefinitionSerializer(SanitizingModelSerializer):
    created_by_info = UserSerializer(source='created_by', read_only=True)
    updated_by_info = UserSerializer(source='updated_by', read_only=True)

    class Meta:
        model = OTACommandDefinition
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']


class OTACommandHistorySerializer(SanitizingModelSerializer):
    ota_command_info = OTACommandDefinitionSerializer(source='ota_command', read_only=True)
    device_tag_info = DeviceTagSerializer(source='device_tag', read_only=True)
    sent_by_info = UserSerializer(source='sent_by', read_only=True)

    class Meta:
        model = OTACommandHistory
        fields = '__all__'
        read_only_fields = ['sent_by', 'created_at']


class OTACommandValueSuggestionSerializer(SanitizingModelSerializer):
    class Meta:
        model = OTACommandValueSuggestion
        fields = '__all__'
        read_only_fields = ['use_count', 'last_used_at', 'created_at']


class ActivationCommandReplySerializer(SanitizingModelSerializer):
    class Meta:
        model = ActivationCommandReply
        fields = '__all__'


class ActivationCommandDispatchSerializer(SanitizingModelSerializer):
    device_tag_info = DeviceTagSerializer(source='device_tag', read_only=True)
    sent_by_info = UserSerializer(source='sent_by', read_only=True)
    reply_info = ActivationCommandReplySerializer(source='reply', read_only=True)

    class Meta:
        model = ActivationCommandDispatch
        fields = '__all__'
        read_only_fields = ['sent_by', 'sent_at', 'send_status', 'reply', 'replied_at']


class IncidentRegisterSerializer(SanitizingModelSerializer):
    registered_by_info = UserSerializer(source='registered_by', read_only=True)
    updated_by_info = UserSerializer(source='updated_by', read_only=True)
    
    class Meta:
        model = IncidentRegister
        fields = '__all__'


class NotificationPreferencesSerializer(serializers.Serializer):

    """
    Serializer for updating user notification preferences.
    All fields are optional.
    """
    nf_popup = serializers.BooleanField(required=False, help_text="Enable/disable popup notifications")
    nf_sms = serializers.BooleanField(required=False, help_text="Enable/disable SMS notifications")
    nf_email = serializers.BooleanField(required=False, help_text="Enable/disable email notifications")
    nf_frequency = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=1440,
        help_text="Notification frequency per day (0-1440). 0 disables by frequency.",
    )
    
    def validate(self, data):
        # Ensure at least one field is provided
        if not data:
            raise serializers.ValidationError("At least one notification preference must be provided.")
        return data



# Trip Serializer
from .models import Trip

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'
        
class PointOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = pointofinterests
        fields = '__all__'


class DeviceModelTechnicalOnboardingDemoDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModelTechnicalOnboardingDemoDevice
        fields = [
            'id',
            'device_serial_no',
            'imei',
            'ccid1',
            'ccid2',
            'msisdn1',
            'msisdn2',
        ]


class DeviceModelTechnicalOnboardingRequestCreateSerializer(serializers.ModelSerializer):
    device_model_id = serializers.IntegerField(write_only=True)
    demo_devices = DeviceModelTechnicalOnboardingDemoDeviceSerializer(many=True, write_only=True)

    class Meta:
        model = DeviceModelTechnicalOnboardingRequest
        fields = [
            'id',
            'device_model_id',
            'user_manual_pdf',
            'ot_command_list_pdf',
            'demo_devices',
        ]
        read_only_fields = ['id']

    def validate_demo_devices(self, value):
        if not value:
            raise serializers.ValidationError('At least one demo device is required.')
        return value


class DeviceModelTechnicalOnboardingRequestDetailSerializer(serializers.ModelSerializer):
    manufacturer = ManufacturerSerializer(read_only=True)
    device_model = DeviceModelSerializer_disp(read_only=True)
    demo_devices = DeviceModelTechnicalOnboardingDemoDeviceSerializer(many=True, read_only=True)

    class Meta:
        model = DeviceModelTechnicalOnboardingRequest
        fields = '__all__'


class DeviceModelTechnicalOnboardingMarkEvaluationSerializer(serializers.Serializer):
    onboarding_request_id = serializers.IntegerField()
    evaluation_datetime = serializers.DateTimeField(required=False)


class DeviceModelTechnicalOnboardingFinalizeSerializer(serializers.Serializer):
    onboarding_request_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['technically_compatible', 'technically_not_compatible'])
    final_comment = serializers.CharField(required=True)


class DeviceModelForTestAgencySerializer(SanitizingModelSerializer):
    eSimProviders = eSimProviderSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    cop_info = serializers.SerializerMethodField()
    manufacturer_info = serializers.SerializerMethodField()

    class Meta:
        model = DeviceModel
        fields = '__all__'

    def get_cop_info(self, obj):
        cop = DeviceCOP.objects.filter(device_model=obj, latest=True).first()
        if cop:
            return DeviceCOPSerializer(cop).data
        return None

    def get_manufacturer_info(self, obj):
        manufacturers = Manufacturer.objects.filter(
            technical_onboarding_requests__device_model=obj,
            technical_onboarding_requests__status='accepted'
        ).distinct()
        return ManufacturerSerializer(manufacturers, many=True).data
