# myapp/forms.py
from django import forms
from bootstrap_datepicker_plus.widgets import DateTimePickerInput

class GPSDataFilterForm(forms.Form):
    vehicle_registration_number = forms.CharField(required=True, label='Vehicle Registration Number')
    start_datetime = forms.DateTimeField(
        required=True,
        label='Start Datetime',
        widget=DateTimePickerInput(
            options={
                "format": "YYYY-MM-DD HH:mm",  # Set the format in the options
                "locale": "en",  # Adjust locale as needed
            }
        )
    )
    end_datetime = forms.DateTimeField(
        required=True,
        label='End Datetime',
        widget=DateTimePickerInput(
            options={
                "format": "YYYY-MM-DD HH:mm",  # Set the format in the options
                "locale": "en",  # Adjust locale as needed
            }
        )
    )