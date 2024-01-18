# skytron_api/serializers.py
from rest_framework import serializers
from .models import User, Manufacturer, Retailer, Device, DeviceModel, FOTA, Vehicle, Tracking, TrackingLog, Session, OTPRequest, EditRequest, Settings

from .models import Manufacturer, Retailer, Device, DeviceModel
from .models import Confirmation

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'    #, deleting, list view of all , detail view.

class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = '__all__'

class RetailerSerializer(serializers.ModelSerializer):
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

class FOTASerializer(serializers.ModelSerializer):
    class Meta:
        model = FOTA
        fields = '__all__'

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class TrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tracking
        fields = '__all__'

class TrackingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingLog
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



class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = '__all__'

class RetailerSerializer(serializers.ModelSerializer):
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