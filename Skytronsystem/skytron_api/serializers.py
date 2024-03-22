# skytron_api/serializers.py
from rest_framework import serializers
from .models import User, Manufacturer, Retailer, Device, DeviceModel, FOTA, Vehicle, Session, OTPRequest, EditRequest, Settings

from .models import Manufacturer, Retailer, Device, DeviceModel
from .models import Confirmation
from .models import Vehicle
from .models import DeviceStock,DeviceTag
from .models import DeviceCOP,eSimProvider

from .models import StockAssignment,VehicleOwner

class DeviceTagSerializer(serializers.ModelSerializer):
    class Meta:
        model =DeviceTag
        fields = '__all__'
class StockAssignmentSerializer(serializers.ModelSerializer):
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

        
class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'    #, deleting, list view of all , detail view.

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


class DeviceStockSerializer2(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    device_model_name = serializers.SerializerMethodField()

    class Meta:
        model = DeviceStock
        fields = '__all__'

    def get_created_by_name(self, obj):
        return obj.created_by.name if obj.created_by else ''
    def get_device_model_name(self, obj):
        return obj.model.model_name if obj.created_by else ''

class DeviceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceModel
        fields = '__all__'

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

class DeviceModelFileUploadSerializer(serializers.ModelSerializer):
    tac_doc_path = serializers.FileField(write_only=True)

    class Meta:
        model = DeviceModel
        fields = '__all__'