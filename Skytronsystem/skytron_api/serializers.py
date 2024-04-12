# skytron_api/serializers.py
from rest_framework import serializers
from .models import User, Manufacturer, Retailer, Device, DeviceModel, FOTA, Vehicle, Session, OTPRequest, EditRequest, Settings

from .models import Manufacturer, Retailer, Device, DeviceModel
from .models import Confirmation
from .models import Vehicle
from .models import DeviceStock,DeviceTag
from .models import *

from .models import StockAssignment,VehicleOwner



class DeviceStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceStock
        fields = '__all__'  # Include all fields of DeviceStock model

class RetailerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Retailer
        fields = '__all__'  # Include all fields of Retailer model

class DeviceTagSerializer(serializers.ModelSerializer):
    class Meta:
        model =DeviceTag
        fields = '__all__'


class StockAssignmentSerializer(serializers.ModelSerializer):
    device = DeviceStockSerializer()  # Nested serializer for 'device' field
    dealer = RetailerSerializer()  
    class Meta:
        model = StockAssignment
        fields = ['device', 'dealer', 'assigned_by', 'assigned', 'shipping_remark', 'stock_status']

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
        fields = '__all__'
class DeviceStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceStock
        fields = '__all__'

 


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'    #, deleting, list view of all , detail view.



class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class ManufacturerSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    class Meta:
        model = Manufacturer
        fields = '__all__'

class RetailerSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    class Meta:
        model = Retailer
        fields = '__all__'

class eSimProviderSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    class Meta:
        model = eSimProvider
        fields = '__all__'
class VehicleOwnerSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)
    class Meta:
        model = VehicleOwner 
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
    created_by = UserSerializer(many=False, read_only=True)
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

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
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

        
class Settings_StateSerializer(serializers.ModelSerializer):
    #state_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    devicemodel_info = DeviceModelSerializer(source='devicemodel', read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)

    class Meta:
        model = Settings_State
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


class StateadminSerializer(serializers.ModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)

    class Meta:
        model = StateAdmin
        fields = '__all__'


class dto_rtoSerializer(serializers.ModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = dto_rto
        fields = '__all__'

 
class SOS_teamSerializer(serializers.ModelSerializer):
    
    #admin = SOS_AdminSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = SOS_team
        fields = '__all__'
class SOS_userSerializer(serializers.ModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = SOS_ex
        fields = '__all__'
        
class SOS_adminSerializer(serializers.ModelSerializer):
    
    users = UserSerializer(many=True, read_only=True)
    createdby_info = UserSerializer(source='createdby', read_only=True)
    state_info = Settings_StateSerializer(source='state', read_only=True)
    district_info = Settings_DistrictSerializer(source='district', read_only=True)

    class Meta:
        model = SOS_admin
        fields = '__all__'
 