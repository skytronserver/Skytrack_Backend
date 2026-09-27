import re
# Serializer for GSM cell info input (cell location API)

# skytron_api/serializers.py
from datetime import timedelta

from django.utils import timezone
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
        if not obj.createdby:
            return ''
        # `createdby` is a plain CharField (not a real FK), so it can't be
        # select_related/prefetch_related away. Cache lookups per serialization
        # pass (e.g. one API response) since the same creator is commonly
        # referenced by many users in a list (a dealer's users, a
        # manufacturer's users, etc.) and would otherwise be re-queried once
        # per occurrence.
        cache = self.context.setdefault('_created_by_name_cache', {})
        if obj.createdby in cache:
            return cache[obj.createdby]
        try:
            name = User.objects.get(id=obj.createdby).name
        except (User.DoesNotExist, ValueError):
            name = ''
        cache[obj.createdby] = name
        return name

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
    shipping_remark = serializers.SerializerMethodField()
    #is_tagged=serializers.CharField( )

    def get_shipping_remark(self, obj):
        return obj.shipping_remark if obj.shipping_remark is not None else "ok"

    class Meta:
        model = DeviceStock
        fields = '__all__'

    #def get_created_by_name(self, obj):
    #    return obj.created_by.name if obj.created_by else ''
    #def get_device_model_name(self, obj):
    #    return obj.model.model_name if obj.created_by else ''


class DeviceRenewalEligibleDeviceSerializer(serializers.ModelSerializer):
    """List-API row: device eligible for renewal (eSIM expiring within the window)."""
    model_name = serializers.CharField(source='model.model_name', read_only=True)
    manufacturer_name = serializers.SerializerMethodField()
    dealer_name = serializers.CharField(source='dealer.company_name', read_only=True)
    days_since_activation = serializers.SerializerMethodField()
    vehicle_reg_no = serializers.SerializerMethodField()
    days_to_expiry = serializers.SerializerMethodField()

    class Meta:
        model = DeviceStock
        fields = [
            'id', 'imei', 'iccid', 'model_name', 'manufacturer_name', 'dealer_name',
            'esim_validity', 'days_to_expiry', 'vehicle_reg_no', 'days_since_activation',
            'stock_status',
        ]

    def get_manufacturer_name(self, obj):
        return obj.model.created_by.name if obj.model and obj.model.created_by else None

    def get_vehicle_reg_no(self, obj):
        tag = getattr(obj, '_latest_tag', None)
        return tag.vehicle_reg_no if tag else None

    def get_days_since_activation(self, obj):
        tag = getattr(obj, '_latest_tag', None)
        if not tag or not tag.tagged:
            return None
        return (timezone.now() - tag.tagged).days

    def get_days_to_expiry(self, obj):
        if not obj.esim_validity:
            return None
        return (obj.esim_validity - timezone.now()).days


class DeviceRenewalSubmitSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    requested_duration_years = serializers.ChoiceField(choices=[1, 2])


class DeviceRenewalRequestListSerializer(serializers.ModelSerializer):
    device_imei = serializers.CharField(source='device.imei', read_only=True)
    device_iccid = serializers.CharField(source='device.iccid', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.name', read_only=True)

    class Meta:
        model = DeviceRenewalRequest
        fields = [
            'id', 'device', 'device_imei', 'device_iccid', 'requested_by', 'requested_by_name',
            'requester_role', 'requested_duration_years', 'old_esim_validity', 'new_esim_validity',
            'status', 'rejection_reason', 'packets_all_received', 'vahan_push_status',
            'certificate_file_path', 'created_at',
        ]


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
        read_only_fields = ['reject_reason', 'rejected_by', 'rejected_at']
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
        read_only_fields = ['reject_reason', 'rejected_by', 'rejected_at']



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
    checkpoint_status = serializers.SerializerMethodField()

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
            'receipt_confirmed',
            'receipt_confirmed_at',
            'receipt_confirmed_by',
            'receipt_rejected',
            'receipt_rejected_at',
            'receipt_rejected_by',
            'receipt_reject_reason',
            'checkpoint_status',
        ]
        read_only_fields = [
            'receipt_confirmed', 'receipt_confirmed_at', 'receipt_confirmed_by',
            'receipt_rejected', 'receipt_rejected_at', 'receipt_rejected_by', 'receipt_reject_reason',
        ]

    def get_checkpoint_status(self, obj):
        executions = list(
            TechnicalOnboardingTestExecution.objects.filter(
                demo_device=obj, test_case__active=True
            ).select_related('test_case').order_by('test_case__serial_no')
        )

        last_completed = None
        next_test = None
        for execution in executions:
            if execution.status == 'complete':
                last_completed = execution
            elif next_test is None:
                next_test = execution

        return {
            'last_completed_test_no': last_completed.test_case.serial_no if last_completed else None,
            'last_completed_test_name': last_completed.test_case.name if last_completed else None,
            'next_test_no': next_test.test_case.serial_no if next_test else None,
            'next_test_name': next_test.test_case.name if next_test else None,
            'next_test_status': next_test.status if next_test else None,
        }


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
        if not value or len(value) != 5:
            raise serializers.ValidationError('Exactly 5 demo devices are required.')
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


class TechnicalOnboardingCourierTrackingSerializer(serializers.Serializer):
    onboarding_request_id = serializers.IntegerField()
    courier_name = serializers.CharField(required=False, allow_blank=True)
    courier_tracking_number = serializers.CharField(required=False, allow_blank=True)
    courier_shipped_date = serializers.DateField(required=False)


class TechnicalOnboardingConfirmReceiptSerializer(serializers.Serializer):
    onboarding_request_id = serializers.IntegerField()
    demo_device_id = serializers.IntegerField()
    # 'confirmed' is the default so existing clients keep working.
    status = serializers.ChoiceField(choices=['confirmed', 'rejected'], required=False, default='confirmed')
    remarks = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['status'] == 'rejected' and not attrs.get('remarks', '').strip():
            raise serializers.ValidationError({'remarks': 'A reject reason is required when rejecting receipt.'})
        return attrs


class TechnicalOnboardingTestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicalOnboardingTestCase
        fields = '__all__'


class TechnicalOnboardingTestBoardRequestSerializer(serializers.Serializer):
    onboarding_request_id = serializers.IntegerField()


class TechnicalOnboardingStartTestSerializer(serializers.Serializer):
    onboarding_request_id = serializers.IntegerField()
    demo_device_id = serializers.IntegerField()
    test_case_id = serializers.IntegerField()


class TechnicalOnboardingExecutionActionSerializer(serializers.Serializer):
    execution_id = serializers.IntegerField()


class TechnicalOnboardingCompleteTestSerializer(serializers.Serializer):
    execution_id = serializers.IntegerField()
    manual_result = serializers.ChoiceField(choices=['pass', 'fail'], required=False)
    manual_notes = serializers.CharField(required=False, allow_blank=True)


class TechnicalOnboardingDemoDeviceHistorySerializer(serializers.Serializer):
    """
    Either `timestamp` (the 1 hour ending there, defaults to now) or a
    `start_datetime`/`end_datetime` pair at most 24 hours apart. Validated
    data always carries the resolved start_datetime/end_datetime.
    """
    onboarding_request_id = serializers.IntegerField()
    timestamp = serializers.DateTimeField(required=False)
    start_datetime = serializers.DateTimeField(required=False)
    end_datetime = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        start = attrs.get('start_datetime')
        end = attrs.get('end_datetime')

        if start or end:
            if 'timestamp' in attrs:
                raise serializers.ValidationError('Send either timestamp or start_datetime/end_datetime, not both.')
            if not (start and end):
                raise serializers.ValidationError('start_datetime and end_datetime must be sent together.')
            if end <= start:
                raise serializers.ValidationError({'end_datetime': 'Must be after start_datetime.'})
            if end - start > timedelta(hours=24):
                raise serializers.ValidationError({'end_datetime': 'The range can be at most 24 hours.'})
        else:
            end = attrs.get('timestamp') or timezone.now()
            start = end - timedelta(hours=1)

        attrs['start_datetime'] = start
        attrs['end_datetime'] = end
        return attrs


class TechnicalOnboardingTestExecutionSerializer(serializers.ModelSerializer):
    test_case = TechnicalOnboardingTestCaseSerializer(read_only=True)
    demo_device = DeviceModelTechnicalOnboardingDemoDeviceSerializer(read_only=True)

    class Meta:
        model = TechnicalOnboardingTestExecution
        fields = '__all__'


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























# =====================================================
# School Bus Module — Added by Harshit
# =====================================================





import os
from rest_framework.exceptions import ValidationError





# =====================================================
# Student
# =====================================================

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "name",
            "roll_number",
            "class_name",
            "section",          # NEW
            "school",
        ]

class StudentCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "name",
            "roll_number",
            "class_name",
            "section",          # NEW
        ]

    def validate(self, attrs):
        request = self.context["request"]
        school = request.user.schooladmin_user.first()

        class_name = attrs.get("class_name")
        roll_number = attrs.get("roll_number")

        queryset = Student.objects.filter(
            school=school,
            class_name=class_name,
            roll_number=roll_number,
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError({
                "roll_number": "Roll number already exists in this class."
            })

        return attrs

class StudentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "name",
            "roll_number",
            "class_name",
            "section",          # NEW
            "school",
        ]
        read_only_fields = ["school"]

# =====================================================
# Parent
# =====================================================

class ParentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField(required=False)
    address = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    dob = serializers.DateField()

    def validate_mobile(self, value):
        if len(value) != 10:
            raise serializers.ValidationError(
                "Mobile number must be exactly 10 digits"
            )
        if not value.isdigit():
            raise serializers.ValidationError(
                "Mobile number must contain only digits"
            )
        return value

class ParentDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    mobile = serializers.CharField(source="user.mobile", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    student_count = serializers.IntegerField(source="students.count", read_only=True)
    students = serializers.SerializerMethodField()

    class Meta:
        model = ParentProfile
        fields = [
            "id",
            "name",
            "mobile",
            "email",
            "address",
            "latitude",
            "longitude",
            "is_active",
            "student_count",
            "students",
        ]

    def get_students(self, obj):
        return [
            {
                "id": s.id,
                "name": s.name,
                "class_name": s.class_name,
                "section": s.section,       # NEW
                "roll_number": s.roll_number,
            }
            for s in obj.students.all()
        ]

class ParentWithStudentsSerializer(serializers.ModelSerializer):
    students = StudentSerializer(many=True, read_only=True)

    class Meta:
        model = ParentProfile
        fields = [
            "id",
            "user",
            "school",
            "students",
        ]

class ParentStudentLinkSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

# =====================================================
# School Route
# =====================================================

class RouteSerializer(serializers.ModelSerializer):
    stops = serializers.SerializerMethodField()
    stop_count = serializers.SerializerMethodField()     # NEW — "No. of Stops" column in list
    
    stops_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        default=list,
    )

    class Meta:
        model = SchoolRoute
        fields = [
            "id",
            "name",
            "description",      # NEW
            "status",
            "route_points",
            "stops",
            "stop_count", 
            "stops_data", # NEW
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_stops(self, obj):
        return [
            {
                "id": rs.stop.id,
                "name": rs.stop.name,
                "latitude": rs.stop.latitude,
                "longitude": rs.stop.longitude,
                "timing": rs.stop.timing,       # NEW
                "order": rs.order,
            }
            for rs in obj.route_stops.select_related("stop").order_by("order")
        ]

    def get_stop_count(self, obj):
        return obj.route_stops.count()

    def validate_name(self, value):
        request = self.context.get("request")
        school = request.user.schooladmin_user.first()

        queryset = SchoolRoute.objects.filter(
            school=school,
            name__iexact=value,
            # Remove: status=SchoolRoute.STATUS_ACTIVE
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Route with this name already exists in your school."
            )

        return value

    def validate_route_points(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("route_points must be a list.")

        for i, point in enumerate(value):
            if not isinstance(point, dict):
                raise serializers.ValidationError(
                    f"Each point must be an object. Invalid at index {i}."
                )
            if "lat" not in point or "lng" not in point:
                raise serializers.ValidationError(
                    f"Each point must have 'lat' and 'lng'. Invalid at index {i}."
                )
            try:
                lat = float(point["lat"])
                lng = float(point["lng"])
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    f"'lat' and 'lng' must be numbers. Invalid at index {i}."
                )
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError(
                    f"Invalid latitude {lat} at index {i}."
                )
            if not (-180 <= lng <= 180):
                raise serializers.ValidationError(
                    f"Invalid longitude {lng} at index {i}."
                )

        return value
    
    def validate_stops_data(self, value):
        for i, item in enumerate(value):
            if "stop_id" not in item or "order" not in item:
                raise serializers.ValidationError(
                    f"Each stop must have 'stop_id' and 'order'. Invalid at index {i}."
                )
            try:
                int(item["stop_id"])
                int(item["order"])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"'stop_id' and 'order' must be integers. Invalid at index {i}."
                )
        # Check for duplicate orders
        orders = [int(item["order"]) for item in value]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError("Duplicate order values are not allowed.")
        return value

# =====================================================
# School Bus Stop
# =====================================================

class BusStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolBusStop
        fields = [
            "id",
            "name",
            "latitude",
            "longitude",
            "timing",           # NEW — visible in stops table and Add Bus Stop modal
            "is_active",
            "created_at",
        ]
        read_only_fields = ["is_active", "created_at"]

    def validate_name(self, value):
        request = self.context.get("request")
        school = request.user.schooladmin_user.first()

        queryset = SchoolBusStop.objects.filter(
            school=school,
            name__iexact=value,
            # Remove: is_active=True
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Bus stop with this name already exists in your school."
            )

        return value

# =====================================================
# Student Bus Allocation
# =====================================================

class StudentBusAllocationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentBusAllocation
        fields = [
            "bus",
            "route",
            "pickup_stop",
            "drop_stop",
            "start_date",
        ]

    def validate(self, attrs):
        if attrs["pickup_stop"] == attrs["drop_stop"]:
            raise serializers.ValidationError(
                {"detail": "Pickup and drop stop cannot be the same."}
            )
        return attrs

class StudentBusAllocationDetailSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    bus = serializers.SerializerMethodField()
    route = serializers.SerializerMethodField()
    pickup_stop = serializers.SerializerMethodField()
    drop_stop = serializers.SerializerMethodField()

    class Meta:
        model = StudentBusAllocation
        fields = [
            "id",
            "student_id",
            "bus",
            "route",
            "pickup_stop",
            "drop_stop",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
        ]

    def get_bus(self, obj):
        return {
            "id": obj.bus.id,
            "vehicle_reg_no": obj.bus.vehicle_reg_no,
        }

    def get_route(self, obj):
        return {
            "id": obj.route.id,
            "name": obj.route.name,
        }

    def get_pickup_stop(self, obj):
        return {
            "id": obj.pickup_stop.id,
            "name": obj.pickup_stop.name,
        }

    def get_drop_stop(self, obj):
        return {
            "id": obj.drop_stop.id,
            "name": obj.drop_stop.name,
        }

# =====================================================
# School Holiday
# =====================================================

class SchoolHolidaySerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    school_id = serializers.IntegerField(source="school.id", read_only=True)

    class Meta:
        model = SchoolHoliday
        fields = [
            "id",
            "school_id",
            "date",
            "title",
            "type",
            "type_display",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["is_active", "created_at", "updated_at"]

    def get_created_by(self, obj):
        if obj.created_by:
            return {
                "id": obj.created_by.id,
                "email": obj.created_by.email,
            }
        return None

    def validate(self, attrs):
        request = self.context.get("request")
        school = request.user.schooladmin_user.first()
        date = attrs.get("date")

        if not date:
            return attrs

        qs = SchoolHoliday.objects.filter(
            school=school,
            date=date,
            is_active=True
        )

        # Exclude current instance on PATCH/PUT to allow updating without false conflict
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                {"date": "Holiday already exists for this date"}
            )

        return attrs

# =====================================================
# School Application
# =====================================================

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Submit application
# Single multipart/form-data request containing school info + user info + files
# ─────────────────────────────────────────────────────────────────────────────

class SchoolApplicationSubmitSerializer(serializers.Serializer):

    # ── School fields ──────────────────────────────────────────────────────────
    school_name    = serializers.CharField(max_length=255)
    school_address = serializers.CharField(max_length=255)
    school_pin     = serializers.CharField(max_length=20)
    school_email   = serializers.EmailField()
    school_phone   = serializers.CharField(max_length=20)
    school_lat     = serializers.FloatField(required=False, allow_null=True)
    school_lon     = serializers.FloatField(required=False, allow_null=True)
    state          = serializers.IntegerField()
    district_code  = serializers.CharField(max_length=8)

    # ── Applicant (User) fields ────────────────────────────────────────────────
    name    = serializers.CharField(max_length=255)
    email   = serializers.EmailField()
    mobile  = serializers.CharField(max_length=15)
    dob     = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    pin     = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # ── Documents ──────────────────────────────────────────────────────────────
    file_idProof              = serializers.FileField()
    file_authorisation_letter = serializers.FileField()

    # ── FIELD VALIDATION ──────────────────────────────────────────────────────
    def validate_mobile(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile must be exactly 10 digits.")
        return value

    def validate_file_idProof(self, file):
        return self._validate_file(file)

    def validate_file_authorisation_letter(self, file):
        return self._validate_file(file)

    def _validate_file(self, file):
        if file.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size must be ≤ 5 MB.")
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
            raise serializers.ValidationError("Allowed types: PDF, JPG, JPEG, PNG.")
        return file

    # ── MAIN VALIDATION ───────────────────────────────────────────────────────
    def validate(self, attrs):
        mobile = attrs["mobile"]
        email  = attrs["email"].lower()
        attrs["email"] = email

        ACTIVE_STATUSES = [
            School.STATUS_SUBMITTED,
            School.STATUS_UNDER_REVIEW,
            School.STATUS_APPROVED,
            School.STATUS_SETUP_SENT,
            School.STATUS_SETUP_LINK_APPROVED,
        ]

        existing_user = None  # Will be set if this is a resubmission

        # ── Check mobile ──────────────────────────────────────────────────────
        user_by_mobile = User.objects.filter(mobile=mobile).first()
        if user_by_mobile:
            has_active_application = School.objects.filter(
                users=user_by_mobile,
                status__in=ACTIVE_STATUSES
            ).exists()
            if has_active_application:
                raise serializers.ValidationError({
                    "mobile": "An active application already exists for this mobile number."
                })
            # User exists but all schools were rejected — allow resubmission
            existing_user = user_by_mobile

        # ── Check email ───────────────────────────────────────────────────────
        user_by_email = User.objects.filter(email=email).first()
        if user_by_email:
            # Different user already owns this email — hard block
            if existing_user and user_by_email.id != existing_user.id:
                raise serializers.ValidationError({
                    "email": "This email is already registered to a different account."
                })
            # Same user (found by both mobile and email) — check active school
            has_active_application = School.objects.filter(
                users=user_by_email,
                status__in=ACTIVE_STATUSES
            ).exists()
            if has_active_application:
                raise serializers.ValidationError({
                    "email": "An active application already exists for this email."
                })
            existing_user = user_by_email

        # ── If email changed on resubmission, ensure new email is free ────────
        if existing_user and user_by_email is None:
            # Mobile matched an existing user but they're submitting with a new email
            # user_by_email is None means no one owns the new email yet — safe to proceed
            pass

        # Store for the view to consume
        attrs["existing_user"] = existing_user  # None = brand new user

        # ── Duplicate School check ────────────────────────────────────────────
        school_email = attrs.get("school_email", "").lower()
        school_phone = attrs.get("school_phone", "")

        if School.objects.filter(
            school_email__iexact=school_email,
            status__in=ACTIVE_STATUSES
        ).exists():
            raise serializers.ValidationError({
                "school_email": "An active application already exists for this school email."
            })

        if School.objects.filter(
            school_phone=school_phone,
            status__in=ACTIVE_STATUSES
        ).exists():
            raise serializers.ValidationError({
                "school_phone": "An active application already exists for this school phone number."
            })

        # ── State validation ──────────────────────────────────────────────────
        try:
            attrs["state_obj"] = Settings_State.objects.get(pk=attrs["state"])
        except Settings_State.DoesNotExist:
            raise serializers.ValidationError({"state": "Invalid state ID."})

        # ── District validation ───────────────────────────────────────────────
        try:
            attrs["district_obj"] = Settings_District.objects.get(
                district_code=attrs["district_code"]
            )
        except Settings_District.DoesNotExist:
            raise serializers.ValidationError({
                "district_code": f"No district found with code '{attrs['district_code']}'"
            })

        return attrs

# ─────────────────────────────────────────────────────────────────────────────
# State admin — list serializer
# ─────────────────────────────────────────────────────────────────────────────

class SchoolApplicationListSerializer(serializers.ModelSerializer):

    # ── Derived fields ────────────────────────────────────────────────────────
    state_name    = serializers.CharField(source="state.state", read_only=True)
    district_name = serializers.CharField(source="district.district", read_only=True)

    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.SerializerMethodField()
    applicant_mobile = serializers.SerializerMethodField()

    has_id_proof   = serializers.SerializerMethodField()
    has_auth_letter = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            "id",

            # school
            "school_name",
            "school_address",
            "school_pin",
            "school_email",
            "school_phone",
            "school_lat",
            "school_lon",

            # location
            "state",
            "state_name",
            "district",
            "district_name",

            # applicant (from User)
            "applicant_name",
            "applicant_email",
            "applicant_mobile",

            # documents
            "has_id_proof",
            "has_auth_letter",
            "extra_documents",

            # meta
            "status",
            "remarks",
            "created_at",
            "updated_at",
        ]

    def get_has_id_proof(self, obj):
        return bool(obj.file_id_proof)

    def get_has_auth_letter(self, obj):
        return bool(obj.file_authorization_letter)
    
    def get_primary_user(self, obj):
        return obj.users.first() if obj.users.exists() else None

    def get_applicant_name(self, obj):
        user = self.get_primary_user(obj)
        return user.name if user else None

    def get_applicant_email(self, obj):
        user = self.get_primary_user(obj)
        return user.email if user else None

    def get_applicant_mobile(self, obj):
        user = self.get_primary_user(obj)
        return user.mobile if user else None

# ─────────────────────────────────────────────────────────────────────────────
# State admin — approve / reject
# ─────────────────────────────────────────────────────────────────────────────

class SchoolApplicationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    remarks  = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["decision"] == "REJECT" and not attrs.get("remarks", "").strip():
            raise serializers.ValidationError(
                {"remarks": "Remarks are required when rejecting."}
            )
        return attrs

# ─────────────────────────────────────────────────────────────────────────────
# School detail (used in responses after approval)
# ─────────────────────────────────────────────────────────────────────────────

class SchoolDetailSerializer(serializers.ModelSerializer):

    state_name    = serializers.CharField(source="state.state", read_only=True)
    district_name = serializers.CharField(source="district.district", read_only=True)

    applicant = serializers.SerializerMethodField()
    admin_users = serializers.SerializerMethodField()

    has_id_proof    = serializers.SerializerMethodField()
    has_auth_letter = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            "id",
            "school_name",
            "school_address",
            "school_pin",
            "school_email",
            "school_phone",
            "school_lat",
            "school_lon",

            "state",
            "state_name",
            "district",
            "district_name",

            "applicant",
            "admin_users",

            "has_id_proof",
            "has_auth_letter",
            "extra_documents",

            "status",
            "remarks",
            "is_active",

            "created_at",
            "updated_at",
        ]

    # ── Primary user (treated as applicant) ───────────────────────────────────
    def get_primary_user(self, obj):
        return obj.users.first() if obj.users.exists() else None

    # ── Applicant (derived) ───────────────────────────────────────────────────
    def get_applicant(self, obj):
        user = self.get_primary_user(obj)
        if not user:
            return None
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "mobile": user.mobile,
        }

    # ── Admin users ───────────────────────────────────────────────────────────
    def get_admin_users(self, obj):
        return [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "mobile": u.mobile
            }
            for u in obj.users.all()
        ]

    # ── Documents ─────────────────────────────────────────────────────────────
    def get_has_id_proof(self, obj):
        return bool(obj.file_id_proof)

    def get_has_auth_letter(self, obj):
        return bool(obj.file_authorization_letter)

# =====================================================
# School Bus Document
# =====================================================

class SchoolBusDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = SchoolBusDocument
        fields = [
            "id",
            "document_type",
            "file",
            "file_path",
            "uploaded_at",
        ]
        read_only_fields = ["file_path", "uploaded_at"]

    def validate_file(self, file):
        max_size = 5 * 1024 * 1024

        if file.size > max_size:
            raise serializers.ValidationError(
                "File size must be less than or equal to 5 MB."
            )

        allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]
        ext = os.path.splitext(file.name)[1].lower()

        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                "Invalid file type. Allowed types: PDF, JPG, JPEG, PNG."
            )

        return file

# =====================================================
# School Bus Trip
# =====================================================

class SchoolBusTripSerializer(serializers.ModelSerializer):

    class Meta:
        model = SchoolBusTrip
        fields = [
            "id",
            "bus",
            "route",
            "trip_date",
            "start_time",
            "end_time",
            "status",
            "created_at",
        ]
        read_only_fields = ["status", "created_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        if not request:
            raise ValidationError("Request context is missing.")

        school = request.user.schooladmin_user.first()
        if not school:
            raise ValidationError("Admin has no school.")

        start = attrs.get("start_time")
        end = attrs.get("end_time")
        bus = attrs.get("bus")
        route = attrs.get("route")
        trip_date = attrs.get("trip_date")

        # Validate time range
        if start and end and start >= end:
            raise ValidationError({
                "end_time": "End time must be after start time."
            })

        # Validate route belongs to school
        if route and route.school != school:
            raise ValidationError({
                "route": "Invalid route for this school."
            })

        # Only approved + active tagged buses can be used
        if bus and not SchoolBusTag.objects.filter(
            school=school,
            bus=bus,
            is_active=True,
            status="approved"
        ).exists():
            raise ValidationError({
                "bus": "Bus is not tagged and approved for this school."
            })

        # Validate bus is assigned to selected route
        if bus and route and not RouteBusAssignment.objects.filter(
            school=school,
            bus=bus,
            route=route,
            is_active=True,
            status="active"
        ).exists():
            raise ValidationError({
                "bus": "Bus is not assigned to this route."
            })

        # Prevent overlapping trips for same bus
        if start and end and bus and trip_date:
            conflict_qs = SchoolBusTrip.objects.filter(
                school=school,
                bus=bus,
                trip_date=trip_date,
                start_time__lt=end,
                end_time__gt=start
            )

            # Exclude self during update
            if self.instance:
                conflict_qs = conflict_qs.exclude(pk=self.instance.pk)

            if conflict_qs.exists():
                raise ValidationError({
                    "start_time": "Bus already has a trip in this time range."
                })

        return attrs

# =====================================================
# Student Attendance
# =====================================================

class StudentBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["id", "name", "roll_number", "class_name", "section"]  # section NEW

class StudentAttendanceSerializer(serializers.ModelSerializer):
    student = StudentBasicSerializer(read_only=True)
    attendance_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = StudentAttendance
        fields = [
            "attendance_id",
            "student",
            "pickup_status",
            "drop_status",
            "pickup_time",
            "drop_time",
            "pickup_stop",
            "drop_stop",
            "created_at",
        ]

class ParentStudentAttendanceItemSerializer(serializers.ModelSerializer):
    trip_date = serializers.DateField(source="trip.trip_date")

    class Meta:
        model = StudentAttendance
        fields = [
            "trip_date",
            "pickup_status",
            "drop_status",
            "is_present",
        ]

class ParentStudentAttendanceSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    attendance = ParentStudentAttendanceItemSerializer(many=True)

# =====================================================
# School Bus Tag — UPDATED + NEW serializers
# =====================================================

class SchoolBusTagSerializer(serializers.ModelSerializer):
    bus_number = serializers.CharField(source="bus.vehicle_reg_no", read_only=True)
    # NEW fields surfaced from updated SchoolBusTag model
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SchoolBusTag
        fields = [
            "id",
            "bus",
            "bus_number",
            "is_active",
            "tagged_at",
            "status",               # NEW
            "status_display",       # NEW
            "remarks",              # NEW
            "requested_by",         # NEW
            "requested_by_name",    # NEW
            "requested_at",         # NEW
            "reviewed_by",          # NEW
            "reviewed_by_name",     # NEW
            "reviewed_at",          # NEW
        ]
        read_only_fields = [
            "is_active", "tagged_at", "status_display",
            "requested_by_name", "reviewed_by_name",
        ]

    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return obj.requested_by.name
        return None

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.name
        return None

# Step 1 — Initiate tagging request
class BusTagInitiateSerializer(serializers.Serializer):
    """
    Step 1: School admin selects a bus by vehicle_reg_no.
    UI shows a dropdown of available (untagged) buses.
    """
    vehicle_reg_no = serializers.CharField(max_length=55)

    def validate_vehicle_reg_no(self, value):
        try:
            bus = DeviceTag.objects.get(
                vehicle_reg_no=value,
                status="Owner_Final_OTP_Verified"
            )
        except DeviceTag.DoesNotExist:
            raise serializers.ValidationError(
                "Vehicle not found or not active in Skytron."
            )
        self._bus = bus
        return value

    def get_bus(self):
        return self._bus

# Step 2 — Verify OTP sent to vehicle owner
class BusTagOTPVerifySerializer(serializers.Serializer):
    """
    Step 2: School admin enters OTP received by the vehicle owner.
    """
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be 6 digits.")
        return value

# Step 3 — Upload documents
class BusTagDocumentUploadSerializer(serializers.Serializer):
    """
    Step 3: Upload each of the 5 mandatory documents.
    Called once per document — UI uploads them individually.
    document_type choices match SchoolBusDocument.DOC_CHOICES
    including the new REQUEST_LETTER type.
    """
    DOCUMENT_CHOICES = [
        ("PERMIT", "School Bus Permit"),
        ("REQUEST_LETTER", "Request Letter From School Principal"),
        ("RC", "Vehicle Registration Certificate"),
        ("AUTH_LETTER", "Authorization Letter From Vehicle Owner"),
        ("VLTD_RECEIPT", "Skytron VLTD Fitment Receipt"),
    ]
    document_type = serializers.ChoiceField(choices=DOCUMENT_CHOICES)
    file = serializers.FileField()

    def validate_file(self, file):
        max_size = 5 * 1024 * 1024
        if file.size > max_size:
            raise serializers.ValidationError(
                "File size must be less than or equal to 5 MB."
            )
        allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                "Invalid file type. Allowed: PDF, JPG, JPEG, PNG."
            )
        return file

class BusTagDocumentsBulkUploadSerializer(serializers.Serializer):
    PERMIT = serializers.FileField(required=False)
    REQUEST_LETTER = serializers.FileField(required=False)
    RC = serializers.FileField(required=False)
    AUTH_LETTER = serializers.FileField(required=False)
    VLTD_RECEIPT = serializers.FileField(required=True)  # always mandatory

    def _validate_file(self, file):
        if file.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size must be ≤ 5 MB.")
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
            raise serializers.ValidationError("Allowed: PDF, JPG, JPEG, PNG.")
        return file

    def validate_PERMIT(self, f):        return self._validate_file(f)
    def validate_REQUEST_LETTER(self, f): return self._validate_file(f)
    def validate_RC(self, f):            return self._validate_file(f)
    def validate_AUTH_LETTER(self, f):   return self._validate_file(f)
    def validate_VLTD_RECEIPT(self, f):  return self._validate_file(f)

# Step 4 — State admin approve/reject
class BusTagDecisionSerializer(serializers.Serializer):
    """
    Step 4: State admin approves or rejects the tagging request.
    On APPROVE — SchoolBusTag.is_active becomes True.
    On REJECT  — remarks are mandatory.
    """
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    remarks = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["decision"] == "REJECT" and not attrs.get("remarks", "").strip():
            raise serializers.ValidationError(
                {"remarks": "Remarks are required when rejecting."}
            )
        return attrs

# Tagging History list — bottom table in UI
class BusTagHistorySerializer(serializers.ModelSerializer):
    """
    Powers the 'Tagging History & Status' table.
    Columns: Vehicle Reg No | School Name | Status | Requested Date
    """
    vehicle_reg_no = serializers.CharField(source="bus.vehicle_reg_no", read_only=True)
    school_name = serializers.CharField(source="school.school_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SchoolBusTag
        fields = [
            "id",
            "vehicle_reg_no",   # "Vehicle Reg No" column
            "school_name",      # "School Name" column
            "status",           # raw value for filtering
            "status_display",   # "Status" column display
            "requested_at",     # "Requested Date" column
        ]

# =====================================================
# Route Bus Assignment — UPDATED
# =====================================================

class RouteBusAssignmentSerializer(serializers.ModelSerializer):
    route_name = serializers.CharField(source="route.name", read_only=True)
    bus_number = serializers.CharField(source="bus.vehicle_reg_no", read_only=True)
    # Driver info — shown in Bus-to-Route Assignment list table
    driver = serializers.SerializerMethodField()
    assigned_date = serializers.DateTimeField(
        source="assigned_at", read_only=True
    )

    class Meta:
        model = RouteBusAssignment
        fields = [
            "id",
            "school",
            "route",
            "route_name",
            "bus",
            "bus_number",
            "driver",           # NEW — shown in assignment list
            "status",           # NEW — Active badge in UI
            "is_active",
            "assigned_date",    # "Assigned Date" column
        ]
        read_only_fields = ["school", "is_active", "assigned_at"]

    def get_driver(self, obj):
        # Driver comes from DeviceTag.drivers M2M (Skytron model)
        driver = obj.bus.drivers.first()
        if driver:
            return {
                "id": driver.id,
                "name": driver.name,
                "phone_no": driver.phone_no,
            }
        return None

# =====================================================
# Bus Alerts
# =====================================================

class BusAlertSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = BusAlert
        fields = [
            "id",
            "description",
            "latitude",
            "longitude",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_created_by(self, obj):
        if obj.created_by:
            return obj.created_by.id
        return None

class AdminBusAlertSerializer(serializers.ModelSerializer):
    alert_type = serializers.CharField(read_only=True)
    alert_type_display = serializers.CharField(
        source="get_alert_type_display", read_only=True
    )
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = BusAlert
        fields = [
            "id",
            "alert_type",
            "alert_type_display",
            "description",
            "latitude",
            "longitude",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_created_by(self, obj):
        if obj.created_by:
            return {
                "id": obj.created_by.id,
                "email": obj.created_by.email,
            }
        return None

class ParentAlertSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(
        source="get_alert_type_display", read_only=True
    )
    school_id = serializers.IntegerField(source="school.id", read_only=True)
    school_name = serializers.CharField(source="school.school_name", read_only=True)
    bus_id = serializers.IntegerField(source="bus.id", read_only=True)

    class Meta:
        model = BusAlert
        fields = [
            "id",
            "school_id",
            "school_name",
            "bus_id",
            "alert_type",
            "alert_type_display",
            "description",
            "latitude",
            "longitude",
            "created_at",
        ]

# =====================================================
# Parent Tracking & Active Trip
# =====================================================

class DropLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolBusStop
        fields = ["id", "name", "timing"]   # timing NEW

class ActiveTripSerializer(serializers.Serializer):
    trip_id = serializers.IntegerField()
    bus = serializers.IntegerField()
    route = serializers.IntegerField()
    trip_date = serializers.DateField()

# =====================================================
# Misc
# =====================================================

class TripAttendanceInitSerializer(serializers.Serializer):
    trip_id = serializers.IntegerField()

class StudentPickupDropSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    timestamp = serializers.DateTimeField(required=False)
    
class StudentListUISerializer(serializers.ModelSerializer):
    linked_parent = serializers.SerializerMethodField()
    assigned_route = serializers.SerializerMethodField()
    pickup_stop = serializers.SerializerMethodField()
    drop_stop = serializers.SerializerMethodField()
    class_display = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "name",
            "class_display",
            "section",
            "roll_number",
            "linked_parent",
            "assigned_route",
            "pickup_stop",
            "drop_stop",
        ]

    def get_class_display(self, obj):
        return f"{obj.class_name}th"

    def get_linked_parent(self, obj):
        parent = obj.parents.first()
        return str(parent.user.name) if parent else None

    def get_allocation(self, obj):
        return obj.bus_allocations.filter(is_active=True).first()


    def get_assigned_route(self, obj):
        allocation = self.get_allocation(obj)
        return allocation.route.name if allocation and allocation.route else None


    def get_pickup_stop(self, obj):
        allocation = self.get_allocation(obj)
        return allocation.pickup_stop.name if allocation and allocation.pickup_stop else None


    def get_drop_stop(self, obj):
        allocation = self.get_allocation(obj)
        return allocation.drop_stop.name if allocation and allocation.drop_stop else None
    
class ParentTripHistorySerializer(serializers.ModelSerializer):
    trip_type = serializers.SerializerMethodField()
    start_time = serializers.TimeField(format="%I:%M %p")
    end_time = serializers.TimeField(format="%I:%M %p")

    class Meta:
        model = SchoolBusTrip
        fields = [
            "trip_date",
            "trip_type",
            "start_time",
            "end_time",
            "status"
        ]

    def get_trip_type(self, obj):
        if not obj.start_time:
            return None

        if obj.start_time.hour < 12:
            return "Morning Pickup"
        return "Evening Drop"
    
    
# =====================================================
# Permit Enforcement Serializers
# =====================================================


class PermitConditionCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = PermitCondition
        fields = [
            'id',
            'permit_name',
            'vehicle_category',
            'violation_type',
            'rule_details',
            'penalty',
            'penalty_amount',
            'challan_code',
            'activation_datetime',
            'deactivation_datetime',
        ]

    def validate(self, attrs):
        activation   = attrs.get('activation_datetime')
        deactivation = attrs.get('deactivation_datetime')

        if activation and deactivation:
            if deactivation <= activation:
                raise serializers.ValidationError({
                    'deactivation_datetime': 'Deactivation must be after activation datetime.'
                })

        return attrs


class PermitConditionUpdateSerializer(serializers.ModelSerializer):
    """
    Only allowed transitions:
    created → active → deactive
    Once active  → cannot edit any field except status
    Once deactive → nothing can change, create new instead
    """

    class Meta:
        model  = PermitCondition
        fields = [
            'id',
            'status',
            'penalty_amount',
            'activation_datetime',
            'deactivation_datetime',
        ]

    def validate(self, attrs):
        instance = self.instance
        new_status = attrs.get('status', instance.status)
        activation = attrs.get('activation_datetime', instance.activation_datetime)
        deactivation = attrs.get('deactivation_datetime', instance.deactivation_datetime)

        # Once deactive — nothing can change
        if instance.status == PermitCondition.STATUS_DEACTIVE:
            raise serializers.ValidationError(
                'A deactivated condition cannot be modified. Please create a new one.'
            )

        # Validate transition
        valid_transitions = {
            PermitCondition.STATUS_CREATED: [PermitCondition.STATUS_ACTIVE],
            PermitCondition.STATUS_ACTIVE:  [PermitCondition.STATUS_DEACTIVE],
        }
        
        allowed = valid_transitions.get(instance.status, [])
        if new_status != instance.status and new_status not in allowed:
            raise serializers.ValidationError({
                'status': f"Cannot transition from '{instance.status}' to '{new_status}'."
            })

        # Once active — cannot edit dates
        if instance.status == PermitCondition.STATUS_ACTIVE:
            if (
                activation   != instance.activation_datetime or
                deactivation != instance.deactivation_datetime
            ):
                raise serializers.ValidationError(
                    'Cannot edit dates after activation.'
                )

        if activation and deactivation and deactivation <= activation:
            raise serializers.ValidationError({
                'deactivation_datetime': 'Deactivation must be after activation datetime.'
            })

        return attrs


class PermitConditionListSerializer(serializers.ModelSerializer):
    vehicle_category_name = serializers.CharField(source='vehicle_category.category', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    violation_type_display = serializers.SerializerMethodField()

    class Meta:
        model  = PermitCondition
        fields = [
            'id',
            'permit_name',
            'vehicle_category',
            'vehicle_category_name',
            'violation_type',
            'violation_type_display',
            'rule_details',
            'penalty',
            'status',
            'activation_datetime',
            'deactivation_datetime',
            'created_datetime',
            'created_by',
            'created_by_name',
        ]

    def get_violation_type_display(self, obj):
        return dict(PermitCondition.PERMIT_VIOLATION_CHOICES).get(obj.violation_type, obj.violation_type)


class ViolationReportSerializer(serializers.ModelSerializer):
    permit_condition_name = serializers.CharField(source='permit_condition.permit_name', read_only=True)
    violation_type = serializers.CharField(source='permit_condition.violation_type', read_only=True)
    vehicle_category_name = serializers.CharField(source='permit_condition.vehicle_category.category', read_only=True)
    challan_code = serializers.CharField(source='permit_condition.challan_code', read_only=True)
    state_name = serializers.CharField(source='state.state', read_only=True)
    district_name = serializers.CharField(source='district.district', read_only=True)

    # From device_tag directly
    vehicle_reg_no = serializers.CharField(source='device_tag.vehicle_reg_no', read_only=True)

    # From device_tag.device (DeviceStock)
    imei = serializers.SerializerMethodField()

    class Meta:
        model  = ViolationReport
        fields = [
            'id',
            'permit_condition',
            'permit_condition_name',
            'violation_type',
            'vehicle_category_name',
            'challan_code',
            'device_tag',
            'vehicle_reg_no',
            'imei',
            'penalty_amount',
            'violation_datetime',
            'state',
            'state_name',
            'district',
            'district_name',
            'created_at',
        ]

    def get_imei(self, obj):
        try:
            return obj.device_tag.device.imei
        except Exception:
            return None
        
        
        
# =====================================================
# Passenger Information System Serializers
# =====================================================


class PublicBusStopSerializer(serializers.ModelSerializer):
    state_name    = serializers.CharField(source='state.state',       read_only=True)
    district_name = serializers.CharField(source='district.district', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)

    class Meta:
        model  = PublicBusStop
        fields = [
            'id',
            'name',
            'address',
            'latitude',
            'longitude',
            'state',
            'state_name',
            'district',
            'district_name',
            'status',
            'last_activation_date',
            'last_deactivation_date',
            'deactivation_date',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'created_by', 'created_at', 'updated_at',
            'last_activation_date', 'last_deactivation_date',
            # status only changes through the /toggle/ endpoint, which also
            # records activation/deactivation dates
            'status',
        ]

    # VAPT (improper input validation): strict server-side allow-list for
    # every client-supplied field of this endpoint.
    WRITABLE_FIELDS = {'name', 'address', 'latitude', 'longitude', 'state', 'district', 'deactivation_date'}
    # letters/digits (\w) plus Indic scripts incl. their vowel signs (U+0900-U+0DFF:
    # Devanagari, Bengali/Assamese, ...), space and basic punctuation
    NAME_RE    = re.compile(r"^[\w\u0900-\u0DFF .,()/&'-]+$")
    ADDRESS_RE = re.compile(r"^[^<>{}`\\\x00-\x08\x0b-\x1f\x7f]*$")  # no markup/control characters
    # India bounding box (with margin)
    LAT_RANGE = (6, 38)
    LON_RANGE = (68, 98)

    def to_internal_value(self, data):
        if hasattr(data, 'keys'):
            unexpected = set(data.keys()) - self.WRITABLE_FIELDS
            if unexpected:
                raise serializers.ValidationError(
                    {field: 'This field is not allowed.' for field in sorted(unexpected)}
                )
        return super().to_internal_value(data)

    def validate_address(self, value):
        if value is None:
            return value
        value = value.strip()
        if len(value) > 500:
            raise serializers.ValidationError('Address must be at most 500 characters.')
        if not self.ADDRESS_RE.match(value):
            raise serializers.ValidationError('Address contains characters that are not allowed.')
        return value

    def validate_latitude(self, value):
        if value is not None and not (self.LAT_RANGE[0] <= value <= self.LAT_RANGE[1]):
            raise serializers.ValidationError(f'Latitude must be between {self.LAT_RANGE[0]} and {self.LAT_RANGE[1]}.')
        return value

    def validate_longitude(self, value):
        if value is not None and not (self.LON_RANGE[0] <= value <= self.LON_RANGE[1]):
            raise serializers.ValidationError(f'Longitude must be between {self.LON_RANGE[0]} and {self.LON_RANGE[1]}.')
        return value

    def validate(self, attrs):
        # District must belong to the chosen state (use stored values on partial update)
        state    = attrs.get('state',    getattr(self.instance, 'state', None))
        district = attrs.get('district', getattr(self.instance, 'district', None))
        if state and district and district.state_id != state.id:
            raise serializers.ValidationError({'district': 'District does not belong to the selected state.'})
        if not self.instance:
            for field in ('latitude', 'longitude'):
                if attrs.get(field) is None:
                    raise serializers.ValidationError({field: 'This field is required.'})
        return attrs

    def validate_name(self, value):
        value = value.strip()
        if not 2 <= len(value) <= 100:
            raise serializers.ValidationError('Name must be 2 to 100 characters.')
        if not self.NAME_RE.match(value):
            raise serializers.ValidationError(
                "Name may contain only letters, digits, spaces and . , ( ) / & ' -"
            )
        # No duplicate stop name in same state+district
        request = self.context.get('request')
        state_id    = request.data.get('state')    or getattr(self.instance, 'state_id', None)
        district_id = request.data.get('district') or getattr(self.instance, 'district_id', None)
        # Raw ids come straight from the request; if they are not integers the
        # state/district fields report their own error - don't query with them.
        if not (str(state_id).isdigit() and str(district_id).isdigit()):
            return value

        qs = PublicBusStop.objects.filter(
            name__iexact=value,
            state_id=state_id,
            district_id=district_id,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'A bus stop with this name already exists in this district.'
            )
        return value


class PublicRouteStopSerializer(serializers.ModelSerializer):
    stop_name  = serializers.CharField(source='stop.name',      read_only=True)
    latitude   = serializers.DecimalField(source='stop.latitude',  max_digits=9, decimal_places=6, read_only=True)
    longitude  = serializers.DecimalField(source='stop.longitude', max_digits=9, decimal_places=6, read_only=True)

    class Meta:
        model  = PublicRouteStop
        fields = [
            'id',
            'stop',
            'stop_name',
            'latitude',
            'longitude',
            'order',
            'arrival_time_min',
            'halt_time_min',
        ]


class PublicBusRouteSerializer(serializers.ModelSerializer):
    state_name        = serializers.CharField(source='state.state',              read_only=True)
    district_name     = serializers.CharField(source='district.district',        read_only=True)
    source_stop_name  = serializers.CharField(source='source_stop.name',         read_only=True)
    destination_stop_name = serializers.CharField(source='destination_stop.name', read_only=True)
    created_by_name   = serializers.CharField(source='created_by.name',          read_only=True)
    route_stops       = PublicRouteStopSerializer(many=True, read_only=True)

    # Write only — for creating/updating stops along with route
    stops_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        default=list,
    )

    class Meta:
        model  = PublicBusRoute
        fields = [
            'id',
            'name',
            'route_number',
            'route_path',
            'source_stop',
            'source_stop_name',
            'destination_stop',
            'destination_stop_name',
            'state',
            'state_name',
            'district',
            'district_name',
            'status',
            'last_activation_date',
            'last_deactivation_date',
            'deactivation_date',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'route_stops',
            'stops_data',
        ]
        read_only_fields = [
            'created_by', 'created_at', 'updated_at',
            'last_activation_date', 'last_deactivation_date',
        ]

    def validate_stops_data(self, value):
        for i, item in enumerate(value):
            if 'stop_id' not in item or 'order' not in item or 'arrival_time_min' not in item:
                raise serializers.ValidationError(
                    f"Each stop must have 'stop_id', 'order', 'arrival_time_min'. Invalid at index {i}."
                )
            try:
                int(item['stop_id'])
                int(item['order'])
                int(item['arrival_time_min'])
                int(item.get('halt_time_min', 0))
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"'stop_id', 'order', 'arrival_time_min' must be integers. Invalid at index {i}."
                )
        # Check for duplicate orders
        orders = [int(item['order']) for item in value]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError("Duplicate order values are not allowed.")
        return value

    def validate(self, attrs):
        state = attrs.get('state')
        district = attrs.get('district')

        source_stop = attrs.get('source_stop')
        destination_stop = attrs.get('destination_stop')

        # Source stop validation
        if source_stop:
            if source_stop.state != state:
                raise serializers.ValidationError({
                    'source_stop': 'Source stop must belong to selected state.'
                })

            if district and source_stop.district != district:
                raise serializers.ValidationError({
                    'source_stop': 'Source stop must belong to selected district.'
                })

        # Destination stop validation
        if destination_stop:
            if destination_stop.state != state:
                raise serializers.ValidationError({
                    'destination_stop': 'Destination stop must belong to selected state.'
                })

            if district and destination_stop.district != district:
                raise serializers.ValidationError({
                    'destination_stop': 'Destination stop must belong to selected district.'
                })

        return attrs

class BusScheduleStopETASerializer(serializers.ModelSerializer):
    stop_name  = serializers.CharField(source='route_stop.stop.name',     read_only=True)
    latitude   = serializers.DecimalField(source='route_stop.stop.latitude',  max_digits=9, decimal_places=6, read_only=True)
    longitude  = serializers.DecimalField(source='route_stop.stop.longitude', max_digits=9, decimal_places=6, read_only=True)

    class Meta:
        model  = BusScheduleStopETA
        fields = [
            'id',
            'order',
            'stop_name',
            'latitude',
            'longitude',
            'scheduled_arrival',
            'scheduled_departure',
            'actual_arrival',
            'actual_departure',
        ]


class BusScheduleSerializer(serializers.ModelSerializer):
    route_number    = serializers.CharField(source='route.route_number', read_only=True)
    route_name      = serializers.CharField(source='route.name',         read_only=True)
    vehicle_reg_no  = serializers.CharField(source='bus.vehicle_reg_no', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name',    read_only=True)
    stop_etas       = BusScheduleStopETASerializer(many=True, read_only=True)

    class Meta:
        model  = BusSchedule
        fields = [
            'id',
            'service_type',
            'route',
            'route_number',
            'route_name',
            'bus',
            'vehicle_reg_no',
            'start_datetime',
            'status',
            'actual_start_time',
            'actual_end_time',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'stop_etas',
        ]
        read_only_fields = [
            'created_by', 'created_at', 'updated_at',
            'actual_start_time', 'actual_end_time', 'status',
        ]

    def validate(self, attrs):
        route = attrs.get('route', getattr(self.instance, 'route', None))
        bus   = attrs.get('bus',   getattr(self.instance, 'bus',   None))
        start = attrs.get('start_datetime', getattr(self.instance, 'start_datetime', None))

        # Bus must have active route stops defined
        if route and not PublicRouteStop.objects.filter(route=route).exists():
            raise serializers.ValidationError({
                'route': 'This route has no stops defined. Add stops before scheduling.'
            })

        return attrs


# Public (no auth) serializers — minimal fields only

class PublicBusStopListSerializer(serializers.ModelSerializer):
    state_name    = serializers.CharField(source='state.state',       read_only=True)
    district_name = serializers.CharField(source='district.district', read_only=True)

    class Meta:
        model  = PublicBusStop
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'state_name', 'district_name']


class PublicBusRouteListSerializer(serializers.ModelSerializer):
    source_stop_name      = serializers.CharField(source='source_stop.name',      read_only=True)
    destination_stop_name = serializers.CharField(source='destination_stop.name', read_only=True)
    state_name            = serializers.CharField(source='state.state',            read_only=True)
    stops                 = PublicRouteStopSerializer(source='route_stops', many=True, read_only=True)

    class Meta:
        model  = PublicBusRoute
        fields = [
            'id', 'name', 'route_number',
            'source_stop_name', 'destination_stop_name',
            'state_name', 'stops',
        ]


class PublicScheduleStatusSerializer(serializers.ModelSerializer):
    route_number   = serializers.CharField(source='route.route_number', read_only=True)
    route_name     = serializers.CharField(source='route.name',         read_only=True)
    vehicle_reg_no = serializers.CharField(source='bus.vehicle_reg_no', read_only=True)
    stop_etas      = BusScheduleStopETASerializer(many=True, read_only=True)

    # Live GPS location — only when status=started
    live_location = serializers.SerializerMethodField()

    class Meta:
        model  = BusSchedule
        fields = [
            'id',
            'service_type',
            'route_number',
            'route_name',
            'vehicle_reg_no',
            'start_datetime',
            'status',
            'actual_start_time',
            'stop_etas',
            'live_location',
        ]

    def get_live_location(self, obj):
        if obj.status != BusSchedule.STATUS_STARTED:
            return None
        from skytron_api.models import GPSData
        gps = (
            GPSData.objects
            .filter(device_tag=obj.bus)
            .order_by('-entry_time')
            .first()
        )
        if not gps:
            return None
        return {
            'latitude':     gps.latitude,
            'longitude':    gps.longitude,
            'speed':        gps.speed,
            'heading':      gps.heading,
            'last_updated': gps.entry_time,
        }
        
        
# =====================================================
# Map / Public-Facing APIs — Serializers
# =====================================================


# ------------------------------------------------------------------
# API 1 — School Bus Module: All routes across all schools
# ------------------------------------------------------------------

class MapSchoolBusStopSerializer(serializers.ModelSerializer):
    """Minimal stop info for map display."""
    latitude  = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        model  = SchoolBusStop
        fields = ['id', 'name', 'latitude', 'longitude', 'timing', 'is_active']


class MapSchoolRouteSerializer(serializers.ModelSerializer):
    """One route entry — includes school details and ordered active stops."""
    school_id      = serializers.IntegerField(source='school.id',           read_only=True)
    school_name    = serializers.CharField(source='school.school_name',     read_only=True)
    school_address = serializers.CharField(source='school.school_address',  read_only=True)
    state_name     = serializers.CharField(source='school.state.state',     read_only=True)
    district_name  = serializers.CharField(source='school.district.district', read_only=True)
    school_lat     = serializers.DecimalField(
        source='school.school_lat', max_digits=9, decimal_places=6, read_only=True
    )
    school_lon     = serializers.DecimalField(
        source='school.school_lon', max_digits=9, decimal_places=6, read_only=True
    )
    stops = serializers.SerializerMethodField()

    class Meta:
        model  = SchoolRoute
        fields = [
            'id', 'name', 'status', 'description', 'route_points',
            'school_id', 'school_name', 'school_address',
            'state_name', 'district_name', 'school_lat', 'school_lon',
            'stops',
        ]

    def get_stops(self, obj):
        # route_stops pre-fetched by the view; only active stops
        return [
            {
                'id':        rs.stop.id,
                'name':      rs.stop.name,
                'order':     rs.order,
                'latitude':  float(rs.stop.latitude)  if rs.stop.latitude  else None,
                'longitude': float(rs.stop.longitude) if rs.stop.longitude else None,
                'timing':    rs.stop.timing,
            }
            for rs in obj.route_stops.all()
            if rs.stop.is_active
        ]



class MapPISRouteSerializer(serializers.ModelSerializer):
    """Lightweight PIS route for map display."""
    source_stop_name      = serializers.CharField(source='source_stop.name',       read_only=True)
    destination_stop_name = serializers.CharField(source='destination_stop.name',  read_only=True)
    state_name            = serializers.CharField(source='state.state',            read_only=True)
    district_name         = serializers.CharField(source='district.district',      read_only=True)
    stops = serializers.SerializerMethodField()

    class Meta:
        model  = PublicBusRoute
        fields = [
            'id', 'name', 'route_number', 'route_path',
            'source_stop_name', 'destination_stop_name',
            'state_name', 'district_name', 'status',
            'stops',
        ]

    def get_stops(self, obj):
        return [
            {
                'id':               rs.stop.id,
                'name':             rs.stop.name,
                'order':            rs.order,
                'arrival_time_min': rs.arrival_time_min,
                'halt_time_min':    rs.halt_time_min,
                'latitude':  float(rs.stop.latitude)  if rs.stop.latitude  else None,
                'longitude': float(rs.stop.longitude) if rs.stop.longitude else None,
            }
            for rs in obj.route_stops.all()
        ]


# ------------------------------------------------------------------
# API 3 — School Bus live locations
# ------------------------------------------------------------------

class MapSchoolBusLocationSerializer(serializers.Serializer):
    """One bus entry with latest GPS location."""
    bus_id          = serializers.IntegerField()
    vehicle_reg_no  = serializers.CharField()
    vehicle_make    = serializers.CharField()
    vehicle_model   = serializers.CharField()
    school_id       = serializers.IntegerField()
    school_name     = serializers.CharField()
    # driver — may be None
    driver          = serializers.DictField(allow_null=True)
    # latest GPS
    latitude        = serializers.FloatField(allow_null=True)
    longitude       = serializers.FloatField(allow_null=True)
    speed           = serializers.FloatField(allow_null=True)
    heading         = serializers.FloatField(allow_null=True)
    ignition_status = serializers.CharField(allow_null=True)
    last_updated    = serializers.DateTimeField(allow_null=True)


# ------------------------------------------------------------------
# API 4 — Public (PIS) Bus live locations
# ------------------------------------------------------------------

class MapPISBusLocationSerializer(serializers.Serializer):
    """One PIS bus entry with latest GPS location."""
    bus_id          = serializers.IntegerField()
    vehicle_reg_no  = serializers.CharField()
    schedule_id     = serializers.IntegerField(allow_null=True)
    schedule_status = serializers.CharField(allow_null=True)
    service_type    = serializers.CharField(allow_null=True)
    route_number    = serializers.CharField(allow_null=True)
    route_name      = serializers.CharField(allow_null=True)
    latitude        = serializers.FloatField(allow_null=True)
    longitude       = serializers.FloatField(allow_null=True)
    speed           = serializers.FloatField(allow_null=True)
    heading         = serializers.FloatField(allow_null=True)
    ignition_status = serializers.CharField(allow_null=True)
    last_updated    = serializers.DateTimeField(allow_null=True)


# ----------------------------------------------------------------
#  4.1 State Transport Analytics Platform 
# ----------------------------------------------------------------


class TripAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for Trip analytics list.
    vehicle_category is resolved from a pre-built tag_map passed
    via serializer context — avoids N+1 DB queries.
    """
    vehicle_category = serializers.SerializerMethodField()
    created_by_name  = serializers.SerializerMethodField()
 
    class Meta:
        model  = Trip
        fields = [
            'id',
            'trip_name',
            'tripvehical_tag',
            'vehicle_category',
            'status',
            'distance_travel',
            'expected_time_of_travel',
            'created_at',
            'updated_at',
            'mobile_no',
            'created_by_name',
        ]
 
    def get_vehicle_category(self, obj):
        # tag_map is pre-built in the view: { vehicle_reg_no: category_name }
        return self.context.get('tag_map', {}).get(obj.tripvehical_tag)
 
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.name
        return obj.mobile_no
    
    
    
class DrivingPatternAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for a single driving-pattern alert.
    GPS location resolved from gps_ref FK (already select_related'd by view).
    Vehicle info resolved from deviceTag FK (already select_related'd by view).
    """
    vehicle_reg_no   = serializers.CharField(source='deviceTag.vehicle_reg_no', read_only=True)
    vehicle_category = serializers.SerializerMethodField()
    state_name       = serializers.CharField(source='state.state', read_only=True)
    district_name    = serializers.SerializerMethodField()
    latitude         = serializers.SerializerMethodField()
    longitude        = serializers.SerializerMethodField()
    alert_type_display = serializers.SerializerMethodField()
 
    class Meta:
        model  = AlertsLog
        fields = [
            'id',
            'type',
            'alert_type_display',
            'alert_details',
            'timestamp',
            'vehicle_reg_no',
            'vehicle_category',
            'state_name',
            'district_name',
            'latitude',
            'longitude',
        ]
 
    def get_vehicle_category(self, obj):
        # category_map pre-built by view: { device_tag_id: category_name }
        return self.context.get('category_map', {}).get(obj.deviceTag_id)
 
    def get_latitude(self, obj):
        return obj.gps_ref.latitude if obj.gps_ref else None
 
    def get_longitude(self, obj):
        return obj.gps_ref.longitude if obj.gps_ref else None
 
    def get_district_name(self, obj):
        # District lives on DeviceTag, not AlertsLog directly
        try:
            return obj.deviceTag.district.district if obj.deviceTag.district else None
        except Exception:
            return None
 
    def get_alert_type_display(self, obj):
        DISPLAY_MAP = {
            'HarshBreak':         'Harsh Braking',
            'HarshTurn':          'Harsh Turn',
            'HarshAcceleration':  'Harsh Acceleration',
            'OverSpeed':          'Overspeed',
            'Route_overspeed':    'Route Overspeed',
            'Idling':             'Idling',
            'UnauthorizedStop':   'Unauthorized Stop',
            'UnauthorizedSkip':   'Unauthorized Skip',
            'Tilt':               'Tilt',
        }
        return DISPLAY_MAP.get(obj.type, obj.type)


class VehicleAlertSummarySerializer(serializers.Serializer):
    device_tag_id    = serializers.IntegerField()
    vehicle_reg_no   = serializers.CharField(allow_null=True)
    vehicle_make     = serializers.CharField(allow_null=True)
    vehicle_model    = serializers.CharField(allow_null=True)
    vehicle_category = serializers.CharField(allow_null=True)
    state_name       = serializers.CharField(allow_null=True)
    district_name    = serializers.CharField(allow_null=True)

    # Driving pattern
    harsh_braking_count      = serializers.IntegerField()
    harsh_turn_count         = serializers.IntegerField()
    harsh_acceleration_count = serializers.IntegerField()
    overspeed_count          = serializers.IntegerField()
    route_overspeed_count    = serializers.IntegerField()
    idling_count             = serializers.IntegerField()
    unauthorized_stop_count  = serializers.IntegerField()
    unauthorized_skip_count  = serializers.IntegerField()
    tilt_count               = serializers.IntegerField()

    # Boundary / compliance
    overtime_count              = serializers.IntegerField()
    state_border_cross_count    = serializers.IntegerField()
    district_border_cross_count = serializers.IntegerField()
    city_border_cross_count     = serializers.IntegerField()
    permit_count                = serializers.IntegerField()
    unauthorized_parking_count  = serializers.IntegerField()
    prohibited_area_count       = serializers.IntegerField()

    # Device health
    offline_device_count = serializers.IntegerField()
    network_loss_count   = serializers.IntegerField()
    gps_loss_count       = serializers.IntegerField()
    low_int_bat_count    = serializers.IntegerField()
    low_ext_bat_count    = serializers.IntegerField()
    ext_bat_discnt_count = serializers.IntegerField()
    box_temp_count       = serializers.IntegerField()
    em_temp_count        = serializers.IntegerField()
    engine_count         = serializers.IntegerField()

    # Geofence / route
    geofence_count        = serializers.IntegerField()
    route_deviation_count = serializers.IntegerField()
    incident_count        = serializers.IntegerField()

    # Emergency
    emergency_count = serializers.IntegerField()

    total_alerts = serializers.IntegerField()
    
    
class PISAnalyticsSummarySerializer(serializers.Serializer):
    # Scope identifiers (echo back what was filtered)
    state_id            = serializers.IntegerField(allow_null=True)
    state_name          = serializers.CharField(allow_null=True)
    district_id         = serializers.IntegerField(allow_null=True)
    district_name       = serializers.CharField(allow_null=True)
    vehicle_category_id = serializers.IntegerField(allow_null=True)
    vehicle_category    = serializers.CharField(allow_null=True)
    date_from           = serializers.DateTimeField(allow_null=True)
    date_to             = serializers.DateTimeField(allow_null=True)

    # Infrastructure counts (scope-filtered, not date-filtered)
    total_buses           = serializers.IntegerField()
    total_active_stops    = serializers.IntegerField()
    total_deactivated_stops = serializers.IntegerField()
    total_active_routes   = serializers.IntegerField()
    total_deactivated_routes = serializers.IntegerField()

    # Schedule counts (date-range filtered + scope filtered)
    schedules_total     = serializers.IntegerField()
    schedules_created   = serializers.IntegerField()
    schedules_started   = serializers.IntegerField()
    schedules_completed = serializers.IntegerField()
    schedules_canceled  = serializers.IntegerField()

    # Schedule breakdown by service type (date-range filtered)
    service_type_breakdown = serializers.ListField(child=serializers.DictField())
    
    
class AlertHeatmapSerializer(serializers.ModelSerializer):
    alert_type = serializers.CharField(source='type')
    latitude = serializers.FloatField(source='gps_ref.latitude')
    longitude = serializers.FloatField(source='gps_ref.longitude')

    vehicle_reg_no = serializers.SerializerMethodField()
    vehicle_category = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    district_name = serializers.SerializerMethodField()
    manufacturer_name = serializers.SerializerMethodField()
    model_name = serializers.SerializerMethodField()

    class Meta:
        model = AlertsLog
        fields = [
            "id",
            "alert_type",
            "latitude",
            "longitude",
            "timestamp",
            "vehicle_reg_no",
            "vehicle_category",
            "state_name",
            "district_name",
            "manufacturer_name",
            "model_name",
        ]

    def get_vehicle_reg_no(self, obj):
        return obj.deviceTag.vehicle_reg_no if obj.deviceTag else None

    def get_vehicle_category(self, obj):
        if obj.deviceTag and obj.deviceTag.category:
            return obj.deviceTag.category.category
        return None

    def get_state_name(self, obj):
        return obj.state.state if obj.state else None

    def get_district_name(self, obj):
        if obj.deviceTag and obj.deviceTag.district:
            return obj.deviceTag.district.district
        return None

    def get_manufacturer_name(self, obj):
        try:
            return obj.deviceTag.device.dealer.manufacturer.company_name
        except Exception:
            return None

    def get_model_name(self, obj):
        try:
            return obj.deviceTag.device.model.model_name
        except Exception:
            return None
        
        
        
class FavoriteCreateSerializer(serializers.Serializer):

    bus = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    route = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    bus_stop = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    label = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default=""
    )

    def validate(self, attrs):

        bus = attrs.get("bus")
        route = attrs.get("route")
        bus_stop = attrs.get("bus_stop")

        if not any([bus, route, bus_stop]):
            raise serializers.ValidationError(
                "At least one of bus, route or bus_stop is required."
            )

        if bus and not DeviceTag.objects.filter(id=bus).exists():
            raise serializers.ValidationError({
                "bus": f"Bus with id {bus} does not exist."
            })

        if route and not PublicBusRoute.objects.filter(id=route).exists():
            raise serializers.ValidationError({
                "route": f"Route with id {route} does not exist."
            })

        if bus_stop and not PublicBusStop.objects.filter(id=bus_stop).exists():
            raise serializers.ValidationError({
                "bus_stop": f"Bus stop with id {bus_stop} does not exist."
            })

        return attrs
    
    
class FavoriteUpdateSerializer(serializers.Serializer):

    label = serializers.CharField(
        max_length=100,
        allow_blank=True
    )
    
    
    
class FavoriteDetailSerializer(serializers.ModelSerializer):

    bus = serializers.SerializerMethodField()
    route = serializers.SerializerMethodField()
    bus_stop = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = [
            "id",
            "label",
            "bus",
            "route",
            "bus_stop",
            "created_at",
            "updated_at",
        ]

    def get_bus(self, obj):

        if not obj.bus:
            return None

        return {
            "id": obj.bus.id,
            "vehicle_reg_no": obj.bus.vehicle_reg_no,
        }

    def get_route(self, obj):

        if not obj.route:
            return None

        return {
            "id": obj.route.id,
            "route_number": getattr(obj.route, "route_number", None),
            "route_name": getattr(obj.route, "route_name", None),
        }

    def get_bus_stop(self, obj):

        if not obj.bus_stop:
            return None

        return {
            "id": obj.bus_stop.id,
            "name": obj.bus_stop.name,
            "latitude": obj.bus_stop.latitude,
            "longitude": obj.bus_stop.longitude,
        }
        
# =====================================================
# User Login Report
# =====================================================

class UserLoginReportSerializer(serializers.Serializer):
    user_id           = serializers.IntegerField()
    name              = serializers.CharField()
    email             = serializers.EmailField()
    mobile            = serializers.CharField()
    role              = serializers.CharField()
    status            = serializers.CharField()
    is_online         = serializers.BooleanField()
    last_login        = serializers.DateTimeField(allow_null=True)
    login_count_today = serializers.IntegerField()
    login_count_week  = serializers.IntegerField()
    login_count_month = serializers.IntegerField()
    total_login_count = serializers.IntegerField()
    
    
    

 
 
class CustomAlertSubruleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CustomAlertSubrule
        fields = [
            'id',
            'order',
            'parameter',
            'operator',
            'value',
            'value_start',
            'value_end',
            'time_from',
            'time_to',
        ]
 
    def validate(self, attrs):
        op        = attrs.get('operator')
        parameter = attrs.get('parameter')
        value     = attrs.get('value', '')
        v_start   = attrs.get('value_start', '')
        v_end     = attrs.get('value_end', '')
 
        is_text = parameter in CustomAlertSubrule.TEXT_PARAMETERS
 
        # Operator / parameter type compatibility
        text_only_ops    = {CustomAlertSubrule.OPERATOR_CONTAINS, CustomAlertSubrule.OPERATOR_NOT_CONTAINS}
        numeric_only_ops = {
            CustomAlertSubrule.OPERATOR_GT, CustomAlertSubrule.OPERATOR_GTE,
            CustomAlertSubrule.OPERATOR_LT, CustomAlertSubrule.OPERATOR_LTE,
            CustomAlertSubrule.OPERATOR_IN_RANGE,
        }
 
        if is_text and op in numeric_only_ops:
            raise serializers.ValidationError({
                'operator': f"Operator '{op}' is not valid for text parameter '{parameter}'."
            })
 
        if not is_text and op in text_only_ops:
            raise serializers.ValidationError({
                'operator': f"Operator '{op}' is only valid for text parameters."
            })
 
        # Value requirements
        if op == CustomAlertSubrule.OPERATOR_IN_RANGE:
            if not v_start or not v_end:
                raise serializers.ValidationError({
                    'value_start': 'Both value_start and value_end are required for in_range.',
                    'value_end':   'Both value_start and value_end are required for in_range.',
                })
            try:
                s, e = float(v_start), float(v_end)
                if s >= e:
                    raise serializers.ValidationError({'value_start': 'value_start must be less than value_end.'})
            except ValueError:
                raise serializers.ValidationError({'value_start': 'value_start and value_end must be numeric.'})
        else:
            if not value:
                raise serializers.ValidationError({'value': 'value is required for this operator.'})
 
        # Time window consistency
        t_from = attrs.get('time_from')
        t_to   = attrs.get('time_to')
        if bool(t_from) != bool(t_to):
            raise serializers.ValidationError({
                'time_from': 'Both time_from and time_to must be provided together.'
            })
 
        return attrs
 
 
class CustomAlertRuleCreateSerializer(serializers.ModelSerializer):
    subrules = CustomAlertSubruleSerializer(many=True)
 
    class Meta:
        model  = CustomAlertRule
        fields = [
            'id',
            'name',
            'description',
            'status',
            'subrule_logic',
            'time_from',
            'time_to',
            'state',
            'subrules',
        ]
        read_only_fields = ['id', 'state']   # state is set by the view based on user role
 
    def validate_subrules(self, value):
        if not value:
            raise serializers.ValidationError('At least one subrule is required.')
        if len(value) > 4:
            raise serializers.ValidationError('A rule can have a maximum of 4 subrules.')
        orders = [item.get('order', 0) for item in value]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError('Subrule order values must be unique.')
        return value
 
    def validate(self, attrs):
        t_from = attrs.get('time_from')
        t_to   = attrs.get('time_to')
        if bool(t_from) != bool(t_to):
            raise serializers.ValidationError({
                'time_from': 'Both time_from and time_to must be provided together.'
            })
        return attrs
 
    def create(self, validated_data):
        subrules_data = validated_data.pop('subrules')
        rule = CustomAlertRule.objects.create(**validated_data)
        for sr_data in subrules_data:
            CustomAlertSubrule.objects.create(rule=rule, **sr_data)
        return rule
 
 
class CustomAlertRuleUpdateSerializer(serializers.ModelSerializer):
    """
    Partial update: top-level fields + full subrule replacement.
    If 'subrules' is provided, ALL existing subrules are replaced.
    """
    subrules = CustomAlertSubruleSerializer(many=True, required=False)
 
    class Meta:
        model  = CustomAlertRule
        fields = [
            'name',
            'description',
            'status',
            'subrule_logic',
            'time_from',
            'time_to',
            'subrules',
        ]
 
    def validate_subrules(self, value):
        if value is not None:
            if len(value) > 4:
                raise serializers.ValidationError('A rule can have a maximum of 4 subrules.')
            orders = [item.get('order', 0) for item in value]
            if len(orders) != len(set(orders)):
                raise serializers.ValidationError('Subrule order values must be unique.')
        return value
 
    def update(self, instance, validated_data):
        subrules_data = validated_data.pop('subrules', None)
 
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
 
        if subrules_data is not None:
            # Full replacement
            instance.subrules.all().delete()
            for sr_data in subrules_data:
                CustomAlertSubrule.objects.create(rule=instance, **sr_data)
 
        return instance
 
 
class CustomAlertRuleDetailSerializer(serializers.ModelSerializer):
    subrules    = CustomAlertSubruleSerializer(many=True, read_only=True)
    state_name  = serializers.CharField(source='state.state', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    log_count   = serializers.SerializerMethodField()
 
    class Meta:
        model  = CustomAlertRule
        fields = [
            'id',
            'name',
            'description',
            'status',
            'subrule_logic',
            'time_from',
            'time_to',
            'state',
            'state_name',
            'subrules',
            'log_count',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
 
    def get_log_count(self, obj):
        return obj.logs.count()
 
 
class CustomAlertLogSerializer(serializers.ModelSerializer):
    rule_name      = serializers.CharField(source='rule.name', read_only=True)
    vehicle_reg_no = serializers.CharField(source='device_tag.vehicle_reg_no', read_only=True)
    state_name     = serializers.CharField(source='state.state', read_only=True)
    latitude       = serializers.FloatField(source='gps_ref.latitude', read_only=True)
    longitude      = serializers.FloatField(source='gps_ref.longitude', read_only=True)
    speed          = serializers.FloatField(source='gps_ref.speed', read_only=True)
 
    class Meta:
        model  = CustomAlertLog
        fields = [
            'id',
            'rule',
            'rule_name',
            'device_tag',
            'vehicle_reg_no',
            'state_name',
            'latitude',
            'longitude',
            'speed',
            'details',
            'fired_at',
        ]