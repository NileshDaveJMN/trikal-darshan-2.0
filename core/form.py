# core/forms.py
from django import forms

class KundaliForm(forms.Form):
    """Form to capture birth details for Single Janma Kundali"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    name = forms.CharField(
        max_length=100, 
        label="Name", 
        widget=forms.TextInput(attrs={'placeholder': 'Enter Full Name'})
    )
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES, 
        label="Gender", 
        initial='M',
        widget=forms.Select(attrs={'class': 'pydroid-select'})
    )
    birth_date = forms.DateField(
        label="Birth Date", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'pydroid-date'})
    )
    birth_time = forms.TimeField(
        label="Birth Time", 
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'pydroid-time'})
    )
    place_name = forms.CharField(
        max_length=255, 
        label="Birth Place", 
        widget=forms.TextInput(attrs={'id': 'place_search_kundali', 'placeholder': 'Search City/Village'})
    )

    # Hidden fields to store accurate data from Nominatim JS search API
    lat = forms.FloatField(widget=forms.HiddenInput(), required=False)
    lon = forms.FloatField(widget=forms.HiddenInput(), required=False)
    # Timezone hidden field, usually handled in view or set by JS
    timezone = forms.FloatField(widget=forms.HiddenInput(), required=False, initial=5.5) # Default IST


class MilanForm(forms.Form):
    """Form to capture birth details for partnership Matching"""
    
    # --- Var (Boy) Details ---
    boy_name = forms.CharField(
        max_length=100, 
        label="Var (Boy) Name", 
        widget=forms.TextInput(attrs={'placeholder': "Boy's Name"})
    )
    boy_birth_date = forms.DateField(
        label="Boy Birth Date", 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    boy_birth_time = forms.TimeField(
        label="Boy Birth Time", 
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    boy_place = forms.CharField(
        max_length=255, 
        label="Boy Birth Place",
        widget=forms.TextInput(attrs={'id': 'place_search_boy', 'placeholder': 'Search City'})
    )
    # Hidden fields for Boy
    boy_lat = forms.FloatField(widget=forms.HiddenInput(), required=False)
    boy_lon = forms.FloatField(widget=forms.HiddenInput(), required=False)
    boy_timezone = forms.FloatField(widget=forms.HiddenInput(), required=False, initial=5.5)

    # --- Kanya (Girl) Details ---
    girl_name = forms.CharField(
        max_length=100, 
        label="Kanya (Girl) Name", 
        widget=forms.TextInput(attrs={'placeholder': "Girl's Name"})
    )
    girl_birth_date = forms.DateField(
        label="Girl Birth Date", 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    girl_birth_time = forms.TimeField(
        label="Girl Birth Time", 
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    girl_place = forms.CharField(
        max_length=255, 
        label="Girl Birth Place",
        widget=forms.TextInput(attrs={'id': 'place_search_girl', 'placeholder': 'Search City'})
    )
    # Hidden fields for Girl
    girl_lat = forms.FloatField(widget=forms.HiddenInput(), required=False)
    girl_lon = forms.FloatField(widget=forms.HiddenInput(), required=False)
    girl_timezone = forms.FloatField(widget=forms.HiddenInput(), required=False, initial=5.5)
