# skytron_api/views.py
from rest_framework.authtoken.models import Token 
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, login
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel
from .serializers import UserSerializer
import random
from django.contrib.auth.hashers import make_password 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel
from .serializers import UserSerializer
import random
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel, Session,Confirmation
from .serializers import UserSerializer, SessionSerializer
from django.contrib.auth.hashers import make_password, check_password


from django.db import transaction

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404


from .serializers import ConfirmationSerializer
from rest_framework.parsers import MultiPartParser


from .models import DeviceStock
from .serializers import DeviceStockSerializer,DeviceStockSerializer2


import pandas as pd
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView 

from rest_framework import generics
from rest_framework import filters
from .models import DeviceModel,User
from .serializers import DeviceModelSerializer

from django.core.files.storage import FileSystemStorage
from rest_framework import generics, status
from rest_framework.response import Response
from .models import DeviceModel
from .serializers import DeviceModelSerializer, DeviceModelFileUploadSerializer
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import DeviceModel,DeviceTag
from .serializers import DeviceModelSerializer


from io import BytesIO

from .models import VehicleOwner,DeviceCOP,StockAssignment,eSimProvider
from .serializers import DeviceCOPSerializer,DeviceModelFilterSerializer

from .serializers import VehicleOwnerSerializer,eSimProviderSerializer, DeviceStockSerializer,DeviceStockFilterSerializer
from .serializers import StockAssignmentSerializer, DeviceTagSerializer
from django.utils import timezone
import ast
 
from django.views.static import serve
from django.conf import settings
from django.http import HttpResponse




@api_view(['POST'])  
def sms_received(request):
    try:
        # Extract necessary parameters from the request data
        no= request.data.get('no')
        msg = request.data.get('msg', '')
        print('SMS Received; NO:'+no+"; MSG:"+msg)
        return Response({'status':"Success"})
    except Exception as e:
        return Response({'error': str(e)}, status=500)
@api_view(['get'])  
def sms_queue(request):
    try: 
        return Response({'no':"6661234",'msg':'data to send'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_VehicleOwner(request):
    try:
        # Extract necessary parameters from the request data
        company_name = request.data.get('company_name')

        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date

        # File uploads
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='owner',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'Vehicle Owner Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        retailer = VehicleOwner.objects.create(
            company_name=company_name, 
            created=created,
            expirydate=expirydate, 
            idProofno=idProofno, 
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        ) 
        retailer.users.add(user) 
        return Response(VehicleOwnerSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_manufacturer(request, manufacturer_id):
    try:
        # Get the Manufacturer instance or return a 404 response
        manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id)

        # Delete the associated user
        user = manufacturer.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        manufacturer.delete()

        return Response({'message': 'Manufacturer and associated user deleted successfully'})

    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_dealer(request, dealer_id):
    try:
        # Get the Manufacturer instance or return a 404 response
        dealer = get_object_or_404(Retailer, id=dealer_id)

        # Delete the associated user
        user =dealer.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        dealer.delete()

        return Response({'message': 'Dealer and associated user deleted successfully'})

    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_eSimProvider(request, esimProvider_id):
    try:
        # Get the Manufacturer instance or return a 404 response
        esimProvider = get_object_or_404(eSimProvider, id=esimProvider_id)

        # Delete the associated user
        user =esimProvider.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        esimProvider.delete()

        return Response({'message': 'eSim Provider and associated user deleted successfully'})

    except Exception as e:
        return Response({'error': str(e)}, status=500)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_VehicleOwner(request, vo_id):
    try:
        # Get the Manufacturer instance or return a 404 response
        vo = get_object_or_404(VehicleOwner, id=vo_id)

        # Delete the associated user
        user =vo.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        vo.delete()

        return Response({'message': 'Vehicle Owner and associated user deleted successfully'})

    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_VehicleOwner(request):
    try:
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if dealer_id :
            manufacturers = VehicleOwner.objects.filter(
                id=dealer_id ,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = VehicleOwner.objects.filter(
                #id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        retailer_serializer = VehicleOwnerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_eSimProvider(request):
    try:
        # Extract necessary parameters from the request data
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date

        # File uploads
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='esimprovider',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'E Sim Provider Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        retailer = eSimProvider.objects.create(
            company_name=company_name,
            gstnnumber=gstnnumber,
            created=created,
            expirydate=expirydate,
            gstno=gstno,
            idProofno=idProofno,
            file_authLetter=file_authLetter,
            file_companRegCertificate=file_companRegCertificate,
            file_GSTCertificate=file_GSTCertificate,
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        )

        # Add the user to the manufacturer's users
        retailer.users.add(user)
 
        return Response(eSimProviderSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_eSimProvider(request):
    try:
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

     
        if dealer_id :
            manufacturers = eSimProvider.objects.filter(
                id=dealer_id ,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = eSimProvider.objects.filter(
                #id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        retailer_serializer = eSimProviderSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_dealer(request):
    try:
        # Extract necessary parameters from the request data
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date

        # File uploads
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='dealer',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'Dealer Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        retailer = Retailer.objects.create(
            company_name=company_name,
            gstnnumber=gstnnumber,
            created=created,
            expirydate=expirydate,
            gstno=gstno,
            idProofno=idProofno,
            file_authLetter=file_authLetter,
            file_companRegCertificate=file_companRegCertificate,
            file_GSTCertificate=file_GSTCertificate,
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        )

        # Add the user to the manufacturer's users
        retailer.users.add(user)
 
        return Response(RetailerSerializer(retailer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_dealer(request):
    try:
        # Get filter parameters from the request
        dealer_id = request.data.get('dealer_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if dealer_id :
            manufacturers = Retailer.objects.filter(
                id=dealer_id ,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = Retailer.objects.filter(
                #id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        retailer_serializer = RetailerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(retailer_serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def create_manufacturer(request):
    try:
        # Extract necessary parameters from the request data
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')
        name = request.data.get('name', '')
        createdby = request.user 
        date_joined = timezone.now()
        created = timezone.now() 
        is_active = True
        is_staff = False
        status = 'active'
        # Additional parameters
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date

        # File uploads
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        
        # Create User instance
        user = User.objects.create(
            name=name,
            email=email,
            mobile=mobile,
            role='devicemanufacture',
            createdby=createdby.id,
            date_joined=date_joined,
            created=created, 
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password  = hashed_password
        )
        # Save the User instance
        try:
            
            send_mail(
                    'Device Manufacturere Account Created',
                    f'Temporery password is : {new_password}',
                    'test@skytrack.tech',
                    [email],
                    fail_silently=False,
            ) 
        except:
            pass
            #return Response({'error': "Error in sendig email"}, status=500)


        user.save()

        # Create Manufacturer instance
        manufacturer = Manufacturer.objects.create(
            company_name=company_name,
            gstnnumber=gstnnumber,
            created=created,
            expirydate=expirydate,
            gstno=gstno,
            idProofno=idProofno,
            file_authLetter=file_authLetter,
            file_companRegCertificate=file_companRegCertificate,
            file_GSTCertificate=file_GSTCertificate,
            file_idProof=file_idProof,
            createdby=createdby,
            status="Created",
        )

        # Add the user to the manufacturer's users
        manufacturer.users.add(user)
 
        return Response(ManufacturerSerializer(manufacturer).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_manufacturers(request):
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('manufacturer_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if manufacturer_id :
            manufacturers = Manufacturer.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = Manufacturer.objects.filter(
                #id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        manufacturer_serializer = ManufacturerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(manufacturer_serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


def download_static_file(request):
    file_path = f"skytron_api/static/StockUpload.xlsx"
    try:
        with open(file_path,'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="StockUpload.xlsx"'
            return response
    except FileNotFoundError:
        return HttpResponse("File not found.", status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def TagDevice2Vehicle(request):
    # Extract data from the request or adjust as needed
    device_id = int(request.data['device'])
    user_id = request.user.id  # Assuming the user is authenticated
    current_datetime = timezone.now()
    uploaded_file = request.FILES.get('rcFile')
    if uploaded_file:
        file_path = 'cop_files/' + str(device_id) + '_' + uploaded_file.name
        with open(file_path, 'wb') as file:
            for chunk in uploaded_file.chunks():
                file.write(chunk)
             
        device_tag = DeviceTag.objects.create(
        device_id=device_id,
        vehicle_owner_id=request.data['vehicle_owner'],
        vehicle_reg_no=request.data['vehicle_reg_no'],
        engine_no=request.data['engine_no'],
        chassis_no=request.data['chassis_no'],
        vehicle_make=request.data['vehicle_make'],
        vehicle_model=request.data['vehicle_model'],
        category=request.data['category'],
        rc_file=file_path,
        status='Dealer_OTP_Sent',
        tagged_by=user_id,
        tagged=current_datetime,
    )

    # Serialize the created data
    serializer = DeviceTagSerializer(device_tag)

    return JsonResponse({'data': serializer.data, 'message': 'Device taging successful.'}, status=201)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def TagAwaitingOwnerApproval(request):
    # Assuming you have user authentication in place
    #user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    device_models = DeviceTag.objects.filter(status='Dealer_OTP_Verified')#created_by=user_id, 
    # Serialize the data
    serializer = DeviceTagSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def TagSendOwnerOtp(request ): 
    device_model_id = request.data.get('device_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceTag, id=device_model_id,  status='Dealer_OTP_Verified')

    device_model.status = 'Owner_OTP_Sent'
    device_model.save()

    return Response({"message": "Owner OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def TagVerifyOwnerOtp(request):
    # Assuming you have user authentication in place
    user_id = request.user.id
    otp = request.data.get('otp')
    device_tag_id = request.data.get('device_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
        return HttpResponseBadRequest("Invalid OTP format")
    device_tag = DeviceTag.objects.filter(device=device_tag_id, status='Owner_OTP_Sent') 

    #device_tag = get_object_or_404(DeviceTag, device_id=device_tag_id,  status='Dealer_OTP_Sent')
    device_tag = device_tag.first()
    if otp == '123456':  # Replace with your actual OTP verification logic
        device_tag.status = 'Owner_OTP_Verified'
        device_tag.save()
        return Response({"message": "Owner OTP verified successfully."}, status=200)
    else:
        return HttpResponseBadRequest("Invalid OTP")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def TagVerifyDealerOtp(request  ):
    # Assuming you have user authentication in place
    user_id = request.user.id
    otp = request.data.get('otp')
    device_tag_id = request.data.get('device_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
        return HttpResponseBadRequest("Invalid OTP format")
    device_tag = DeviceTag.objects.filter(device=device_tag_id, status='Dealer_OTP_Sent') 

    #device_tag = get_object_or_404(DeviceTag, device_id=device_tag_id,  status='Dealer_OTP_Sent')
    device_tag = device_tag.first()
    if otp == '123456':  # Replace with your actual OTP verification logic
        device_tag.status = 'Dealer_OTP_Verified'
        device_tag.save()
        return Response({"message": "Dealer OTP verified successfully."}, status=200)
    else:
        return HttpResponseBadRequest("Invalid OTP")







@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ActivateESIMRequest(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='Fitted')
    stock_assignment.stock_status = 'ESIM_Active_Req_Sent'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'ESIM Active Request Sent successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ConfirmESIMActivation(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='ESIM_Active_Req_Sent')
    stock_assignment.stock_status = 'ESIM_Active_Confirmed'
    stock_assignment.save()
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='ESIM_Active_Confirmed')
    
    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'ESIM Active Confirmed successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ConfigureIPPort(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='ESIM_Active_Confirmed')
    stock_assignment.stock_status = 'IP_PORT_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'IP Port Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ConfigureSOSGateway(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='IP_PORT_Configured')
    stock_assignment.stock_status = 'SOS_GATEWAY_NO_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'SOS Gateway Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ConfigureSMSGateway(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='SOS_GATEWAY_NO_Configured')
    stock_assignment.stock_status = 'SMS_GATEWAY_NO_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'SMS Gateway Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def MarkDeviceDefective(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='SMS_GATEWAY_NO_Configured')
    stock_assignment.stock_status = 'Device_Defective'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'Device Marked as Defective successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def ReturnToDeviceManufacturer(request):
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='Device_Defective')
    stock_assignment.stock_status = 'Returned_to_manufacturer'
    stock_assignment.save()

    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'Device Returned to Manufacturer successfully.'}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def SellListAvailableDeviceStock(request):
    # Get DeviceStock instances with StockAssignment having stock_status "Available_for_fitting"
    device_stock = StockAssignment.objects.filter(stock_status='Available_for_fitting')
    # Serialize the data
    serializer =StockAssignmentSerializer(device_stock, many=True)
    return JsonResponse({'data': serializer.data}, status=200)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def SellFitDevice(request):
    device_id=int(request.data['device_id'])
    stock_assignment = get_object_or_404(StockAssignment, device=device_id, stock_status='Available_for_fitting')
    stock_assignment.stock_status = 'Fitted'
    stock_assignment.save()
    # Serialize the updated data
    serializer = StockAssignmentSerializer(stock_assignment)
    return JsonResponse({'data': serializer.data, 'message': 'Device Fitted  successfully.'}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def StockAssignToRetailer(request):
    # Deserialize the input data
    data = request.data.copy()
    data['assigned_by'] = request.user.id
    data['assigned'] = timezone.now()
    data['stock_status']= "Available_for_fitting"
    data['dealer']=int(data['dealer'])
    device_ids = ast.literal_eval(str(data['device']))
     

    # Create individual StockAssignment entries for each device
    stock_assignments = []
    for device_id in device_ids:
        data['device'] = int(device_id)
        serializer = StockAssignmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            stock_assignments.append(serializer.data)
        else:
            return JsonResponse({'error': serializer.errors}, status=400)

    return JsonResponse({'data': stock_assignments, 'message': 'Stock assigned successfully.'}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deviceStockFilter(request):
    # Deserialize the input data
    serializer = DeviceStockFilterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Filter DeviceStock instances based on parameters
    device_stock = DeviceStock.objects.filter(**serializer.validated_data)

    # Serialize the data
    serializer = DeviceStockSerializer2(device_stock, many=True)

    return JsonResponse({'data': serializer.data}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deviceStockCreateBulk(request):
    if 'excel_file' not in request.FILES or 'model_id' not in request.data:
        return JsonResponse({'error': 'Please provide an Excel file and model_id.'}, status=400)

    model_id = request.data['model_id']

    try:
        excel_data = pd.read_excel(request.FILES['excel_file'], engine='openpyxl')
    except Exception as e:
        return JsonResponse({'error': 'Error reading Excel file.', 'details': str(e)}, status=400)

    headers = list(excel_data.columns)
    success_count = 0
    success_rows = []
    error_rows = []

    for index, row in excel_data.iterrows():
        # Skip the header and example rows
        if index == 0 or 'example' in str(row[0]).lower():
            continue

        # Extract data from the row
        data = {
            'model': model_id,
            'device_esn': row.get('device_esn', ''),
            'iccid': row.get('iccid', ''),
            'imei': row.get('imei', ''),
            'telecom_provider1': row.get('telecom_provider1', ''),
            'telecom_provider2': row.get('telecom_provider2', ''),
            'msisdn1': row.get('msisdn1', ''),
            'msisdn2': row.get('msisdn2', ''),
            'imsi1': row.get('imsi1', ''),
            'imsi2': row.get('imsi2', ''),
            'esim_validity': row.get('esim_validity', ''),
            'esim_provider': row.get('esim_provider', ''),
            'remarks': row.get('remarks', ''),
            'created_by': request.user.id,
            'created':timezone.now(),
        }

        # Validate and create DeviceStock instance
        serializer = DeviceStockSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            success_count += 1
            success_rows.append(index + 1)
        else:
            error_rows.append({'row': index + 1, 'errors': serializer.errors})

    message = f'{success_count} out of {len(excel_data) - 1} provided stocks are successfully uploaded.'

    response_data = {
        'message': message,
        'success_rows': success_rows,
        'error_rows': error_rows,
    }

    return JsonResponse(response_data, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deviceStockCreate(request):
    # Deserialize the input data
    data = request.data.copy()
    data['created'] = timezone.now()  # Ensure you import timezone from django.utils
    data['created_by'] = request.user.id

    serializer = DeviceStockSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    # Save the DeviceStock instance
    serializer.save()

    return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def COPCreate(request):
    # Assuming you have user authentication in place
    manufacturer = request.user

    # Create data for the new DeviceCOP entry
    data = {
        'created_by': manufacturer,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
        'status': 'Manufacturer_OTP_Sent',
        'valid':True,
        'latest':True,
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)

    # Create a serializer instance
    serializer = DeviceCOPSerializer(data=request_data)

    # Validate and save the data along with the file
    if serializer.is_valid():
        # Save the DeviceCOP instance
        device_cop_instance = serializer.save()

        # Handle the uploaded file
        uploaded_file = request.FILES.get('cop_file')
        if uploaded_file:
            # Save the file to a specific location
            file_path = 'cop_files/' + str(device_cop_instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            # Update the cop_file field in the DeviceCOP instance
            device_cop_instance.cop_file = file_path
            device_cop_instance.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def COPAwaitingStateApproval(request):
    # Assuming you have user authentication in place
    #user_id = request.user.id

    # Retrieve device models with status "Manufacturer_OTP_Verified"
    device_models = DeviceCOP.objects.filter(status='Manufacturer_OTP_Verified')#created_by=user_id, 
    
    # Serialize the data
    serializer = DeviceCOPSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def COPSendStateAdminOtp(request ): 
    device_model_id = request.data.get('device_model_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceCOP, id=device_model_id,  status='Manufacturer_OTP_Verified')

    device_model.status = 'StateAdminOTPSend'
    device_model.save()

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def COPVerifyStateAdminOtp(request):
    device_model_id = request.data.get('device_model_id')
    # Assuming you have user authentication in place
    user_id = request.user.id
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceCOP, id=device_model_id, created_by=user_id, status='StateAdminOTPSend')

    # Additional logic for OTP verification can be added here if needed

    device_model.status = 'StateAdminApproved'
    device_model.save()

    return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def COPManufacturerOtpVerify(request  ):
    # Assuming you have user authentication in place
    user_id = request.user.id

    # Validate OTP and update the status
    otp = request.data.get('otp')
    device_model_id = request.data.get('device_model_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
        return HttpResponseBadRequest("Invalid OTP format")

    device_model = get_object_or_404(DeviceCOP, id=device_model_id, created_by=user_id, status='Manufacturer_OTP_Sent')

    # Verify OTP and update status
    if otp == '123456':  # Replace with your actual OTP verification logic
        device_model.status = 'Manufacturer_OTP_Verified'
        device_model.save()
        return Response({"message": "Manufacturer OTP verified successfully."}, status=200)
    else:
        return HttpResponseBadRequest("Invalid OTP")





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_devicemodel(request): 
    device_models = DeviceModel.objects.all() 
    serializer = DeviceModelSerializer(device_models, many=True) 
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_devicemodel(request):
    # Deserialize the input parameters
    serializer = DeviceModelFilterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Filter DeviceModel instances based on parameters
    device_models = DeviceModel.objects.filter(**serializer.validated_data)

    # Serialize the data
    serializer = DeviceModelSerializer(device_models, many=True)

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def details_devicemodel(request ): 
    
    device_model_id = request.data.get('device_model_id')
    device_model = get_object_or_404(DeviceModel, id=device_model_id)
 
    serializer = DeviceModelSerializer(device_model)

    return Response(serializer.data)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def DeviceModelAwaitingStateApproval(request):
    # Assuming you have user authentication in place
    #user_id = request.user.id

    # Retrieve device models with status "Manufacturer_OTP_Verified"
    device_models = DeviceModel.objects.filter(status='Manufacturer_OTP_Verified')#created_by=user_id, 
    
    # Serialize the data
    serializer = DeviceModelSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DeviceSendStateAdminOtp(request ): 
    device_model_id = request.data.get('device_model_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceModel, id=device_model_id,  status='Manufacturer_OTP_Verified')

    device_model.status = 'StateAdminOTPSend'
    device_model.save()

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DeviceVerifyStateAdminOtp(request):
    
    device_model_id = request.data.get('device_model_id')
    # Assuming you have user authentication in place
    user_id = request.user.id

    # Validate current status and update the status
    device_model = get_object_or_404(DeviceModel, id=device_model_id, created_by=user_id, status='StateAdminOTPSend')

    # Additional logic for OTP verification can be added here if needed

    device_model.status = 'StateAdminApproved'
    device_model.save()

    return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def DeviceCreateManufacturerOtpVerify(request  ):
    # Assuming you have user authentication in place
    user_id = request.user.id

    # Validate OTP and update the status
    otp = request.data.get('otp')
    device_model_id = request.data.get('device_model_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
        return HttpResponseBadRequest("Invalid OTP format")

    device_model = get_object_or_404(DeviceModel, id=device_model_id, created_by=user_id, status='Manufacturer_OTP_Sent')

    # Verify OTP and update status
    if otp == '123456':  # Replace with your actual OTP verification logic
        device_model.status = 'Manufacturer_OTP_Verified'
        device_model.save()
        return Response({"message": "Manufacturer OTP verified successfully."}, status=200)
    else:
        return HttpResponseBadRequest("Invalid OTP")

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_device_model(request):
    # Assuming you have user authentication in place
    user_id = request.user.id

    # Create data for the new DeviceModel entry
    data = {
        'created_by': user_id,
        'created': timezone.now(),  # Ensure you import timezone from django.utils
        'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    print("requestdata",request_data) 
    serializer = DeviceModelSerializer(data=request_data)

    # Validate and save the data along with the file
    if serializer.is_valid():
        # Save the DeviceModel instance
        device_model_instance = serializer.save()
        # Handle the uploaded file
        uploaded_file = request.FILES.get('tac_doc_path')
        if uploaded_file:
            # Save the file to a specific location
            file_path = '' + str(device_model_instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            # Update the tac_doc_path field in the DeviceModel instance
            device_model_instance.tac_doc_path = file_path
            device_model_instance.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeviceModelUpdateView(generics.UpdateAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelFileUploadSerializer

    def perform_update(self, serializer):
        file = self.request.FILES.get('tac_doc_path', None)
        if file:
            fs = FileSystemStorage(location=settings.MEDIA_ROOT + '/tac_docs/')
            filename = fs.save(file.name, file)
            tac_doc_path = 'tac_docs/' + filename
            serializer.validated_data['tac_doc_path'] = tac_doc_path
        serializer.save()

class DeviceModelFilterView(generics.ListAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['model_name', 'test_agency', 'vendor_id', 'status']

class DeviceModelDetailView(generics.RetrieveAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer

class DeviceModelDeleteView(generics.DestroyAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer





class FileUploadView(APIView):
    parser_classes = (MultiPartParser,)
    def post(self, request, *args, **kwargs): 
        email = request.data.get('email', None)
        if not email:
            return Response({'error': 'email not provided'}, status=400)
            
        try:
            user = UserModel.objects.get(email=email)
        
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        #user = get_object_or_404(UserModel, email=email)
        if user:
            print(email)
            if 'file' not in request.data:
                return Response({'error': 'No file part'}, status=status.HTTP_400_BAD_REQUEST)
            
            print(email)
            file = request.data['file']
            user.kycfile.save(file.name, file)
            user.save()
            #serializer = UserSerializer(user) 
             
    
            return Response({'status': 'KYC Uploaded successfully'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Invalid email'}, status=400)




        


@api_view(['POST'])
def validate_email_confirmation(request):
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)



@api_view(['POST']) 
def send_email_confirmation(request):
    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)
    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)


@api_view(['POST'])
def validate_pwrst_confirmation(request):
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)


@api_view(['POST']) 
def send_pwrst_confirmation(request):
    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)



@api_view(['POST'])
def validate_sms_confirmation(request):
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)


@api_view(['POST']) 
def send_sms_confirmation(request):
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)





class DeleteAllUsersView(APIView):
    def delete(self, request, *args, **kwargs):
        try:
            # Get the custom user model
            User = get_user_model()

            # Delete all users
            User.objects.get(id=31 ).delete()
            #User.objects.all().delete()

            return Response({'message': 'All users deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
def create_user(request):
    """
    Create a new user.
    """
    serializer_class = UserSerializer
    if request.method == 'POST':
        data = request.data.copy() 
        data['createdby'] = 'admin'
        new_password=''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
        hashed_password = make_password(new_password)
        data['password']  = hashed_password

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            send_mail(
                'Account Created',
                f'Temporery password is : {new_password}',
                'test@skytrack.tech',
                [data['email']],
                fail_silently=False,
            ) 
            custom_data = {
            'id': serializer.data['id'],
            'name': serializer.data['name'],
            #'companyName': serializer.data.companyName,
            'email': serializer.data['email'],
            }

            return Response(custom_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    """
    Update user details.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
def password_reset(request):
    """
    Reset user password.
    """
    if request.method == 'POST':
        email = request.data.get('email', None)
        new_password = request.data.get('new_password', None)

        if not email:
            return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return Response({'error': 'Password not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate a random password, set and hash it
         
        hashed_password = make_password(new_password)
        user.password = hashed_password
        user.save()

        return Response({'message': 'Password reset successfully'})



@csrf_exempt
@api_view(['POST'])
def send_email_otp(request):
    """
    Send OTP to the user's email.
    """
    if request.method == 'POST':
        email = request.data.get('email', None)

        if not email:
            return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate and send OTP via email (Implementation depends on your email service)

        return Response({'message': 'Email OTP sent successfully'})

@csrf_exempt
@api_view(['POST'])
def send_sms_otp(request):
    """
    Send OTP to the user's mobile.
    """
    if request.method == 'POST':
        mobile = request.data.get('mobile', None)

        if not mobile:
            return Response({'error': 'Mobile not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(mobile=mobile)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate and send OTP via SMS (Implementation depends on your SMS service)

        return Response({'message': 'SMS OTP sent successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
def user_login(request):
    if request.method == 'POST':
        username = request.data.get('username', None)
        password = request.data.get('password', None)

        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)

        user = UserModel.objects.filter(email=username).first() or UserModel.objects.filter(mobile=username).first()
        #print(user,password, user.password)
        #print(check_password(password, user.password), )
        user.is_active=True
        user.save()
 
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check for an existing active session
        existing_session = Session.objects.filter(user=user.id, status='login').first()

        #if existing_session:
        #    return Response({'token': existing_session.token}, status=status.HTTP_200_OK)

        # Generate an OTP and a unique token
        otp = str(random.randint(100000, 999999))
        #token = get_random_string(length=32)
        token, created = Token.objects.get_or_create(user=user)

        # Create a new session entry
        session_data = {
            'user': user.id,
            'token': str(token.key),
            'otp': otp,
            'status': 'otpsent',
            'login_time': timezone.now(),
        }
        print(session_data)

        session_serializer = SessionSerializer(data=session_data)  # Replace with your actual SessionSerializer
        if session_serializer.is_valid():
            session_serializer.save()

            # Send OTP to the user's email
             
            send_mail(
                'Login OTP',
                f'Your login OTP is: {otp}',
                'test@skytrack.tech',
                [user.email],
                fail_silently=False,
            ) 
            
            return Response({'status':'Email OTP Sent to '+str(user.email),'token': token.key}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to create session'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the OTP validation endpoint
def validate_otp(request):
    if request.method == 'POST':
        otp = request.data.get('otp', None)
        token = request.data.get('token', None)

        if not otp or not token:
            return Response({'error': 'OTP or session token not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session based on the provided token
        session = Session.objects.filter(token=token).first()

        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'login':
            return Response({'status':'Login Successful','token': session.token}, status=status.HTTP_200_OK)

        # Validate the OTP
        print(otp,session.otp)
        if str(otp) == str(session.otp):
            # OTP is valid, change session status to 'login'
            session.status = 'login'
            session.save()

            return Response({'status':'Login Successful','token': session.token}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_401_UNAUTHORIZED)
            
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """
    User logout.
    """
    if request.method == 'POST':
        token = request.data.get('token', None)

        if  not token:
            return Response({'error': 'Session token not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session based on the provided token
        session = Session.objects.filter(token=token).first()

        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)

        session.status = 'logout'
        session.save()


        return Response({'status': 'Logout successful'})

@csrf_exempt
@api_view(['GET'])
def user_get_parent(request, user_id):
    """
    Get parent user details.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    parent_id = user.parent

    if not parent_id:
        return Response({'message': 'User has no parent'})

    try:
        parent_user = UserModel.objects.get(id=parent_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'Parent user not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(parent_user)
    return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_list(request):
    """
    Get a list of users.
    """
    users = UserModel.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data ,status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_details(request, user_id):
    """
    Get details of a specific user.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user)
    return Response(serializer.data)




from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Manufacturer, Retailer, Device, DeviceModel,Vehicle
from .serializers import ManufacturerSerializer, RetailerSerializer, DeviceSerializer, DeviceModelSerializer,VehicleSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_vehicle(request):
    serializer = VehicleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user, owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_vehicle(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VehicleSerializer(vehicle, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_vehicle(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    vehicle.delete()
    return Response({'message': 'Vehicle deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_vehicles(request):
    vehicles = Vehicle.objects.all()
    serializer = VehicleSerializer(vehicles, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vehicle_details(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VehicleSerializer(vehicle)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manufacturer_details(request, manufacturer_id):
    try:
        manufacturer = Manufacturer.objects.get(pk=manufacturer_id)
    except Manufacturer.DoesNotExist:
        return Response({'error': 'Manufacturer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ManufacturerSerializer(manufacturer)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def retailer_details(request, retailer_id):
    try:
        retailer = Retailer.objects.get(pk=retailer_id)
    except Retailer.DoesNotExist:
        return Response({'error': 'Retailer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = RetailerSerializer(retailer)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_details(request, device_id):
    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeviceSerializer(device)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_model_details(request, device_model_id):
    try:
        device_model = DeviceModel.objects.get(pk=device_model_id)
    except DeviceModel.DoesNotExist:
        return Response({'error': 'Device Model not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeviceModelSerializer(device_model)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_manufacturers(request):
    company_name = request.query_params.get('company_name', '')
    manufacturers = Manufacturer.objects.filter(company_name__icontains=company_name)
    serializer = ManufacturerSerializer(manufacturers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_retailers(request):
    name = request.query_params.get('name', '')
    retailers = Retailer.objects.filter(name__icontains=name)
    serializer = RetailerSerializer(retailers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_devices(request):
    # Add filters based on your requirements
    devices = Device.objects.all()
    serializer = DeviceSerializer(devices, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_device_models(request):
    device_model = request.query_params.get('device_model', '')
    device_models = DeviceModel.objects.filter(device_model__icontains=device_model)
    serializer = DeviceModelSerializer(device_models, many=True)
    return Response(serializer.data)


 
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_retailer(request, pk):
    retailer = Retailer.objects.get(pk=pk)
    retailer.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_device(request, pk):
    device = Device.objects.get(pk=pk)
    device.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_device_model(request, pk):
    device_model = DeviceModel.objects.get(pk=pk)
    device_model.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_manufacturer(request, pk):
    manufacturer = Manufacturer.objects.get(pk=pk)
    serializer = ManufacturerSerializer(manufacturer, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_retailer(request, pk):
    retailer = Retailer.objects.get(pk=pk)
    serializer = RetailerSerializer(retailer, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_device(request, pk):
    device = Device.objects.get(pk=pk)
    serializer = DeviceSerializer(device, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_device_model(request, pk):
    device_model = DeviceModel.objects.get(pk=pk)
    serializer = DeviceModelSerializer(device_model, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_manufacturer(request):
    serializer = ManufacturerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_retailer(request):
    serializer = RetailerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_device(request):
    serializer = DeviceSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 

'''