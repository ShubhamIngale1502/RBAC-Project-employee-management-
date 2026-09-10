from django import forms
from .models import User, User_Profile, Country, State, City,User
from django.contrib.auth.models import Group


class RoleChoiceMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            ('', 'Select a role'),
            *Group.objects.order_by('name').values_list('name', 'name'),
        ]


class StepOneForm(RoleChoiceMixin, forms.ModelForm):
    password = forms.CharField(
        label='Password',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password',
        })
    )
    role = forms.ChoiceField(
        label='Role',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'mobile', 'role']

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile number'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')

        if password and password2 and password != password2:
            raise forms.ValidationError('The passwords do not match.')

        if User.objects.filter(email__iexact=cleaned_data.get('email')).exists():
            raise forms.ValidationError('A user with this email already exists.')

        return cleaned_data


class StepTwoForm(forms.ModelForm):
    class Meta:
        model = User_Profile
        fields = ['country', 'state', 'city', 'address', 'pin_code']

        widgets = {
            'country': forms.Select(attrs={'class': 'form-select'}),
            'state': forms.Select(attrs={'class': 'form-select'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pin_code': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].required = False
        self.fields['state'].required = False
        self.fields['city'].required = False
        # self.fields['country'].queryset = Country.objects.all().order_by('country_name')
        # self.fields['state'].queryset = State.objects.all().order_by('state_name')
        # self.fields['city'].queryset = City.objects.all().order_by('city_name')


class UserForm(RoleChoiceMixin, forms.ModelForm):
    # username = forms.CharField(
    #     max_length=150,
    #     required=True,
    #     widget=forms.TextInput(attrs={
    #         'class': 'form-control',
    #         'placeholder': 'Username',
    #     })
    # )
    password = forms.CharField(
        label='Password',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password',
        })
    )
    profile_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        })
    )
    role = forms.ChoiceField(
        label='Role',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'mobile', 'role', 'profile_image']

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Please enter a valid email',
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mobile number',
            }),
            'role': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Role',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')

        if password and password2 and password != password2:
            raise forms.ValidationError('The passwords do not match.')

        if User.objects.filter(username__iexact=cleaned_data.get('username')).exists():
            raise forms.ValidationError('This username is already taken.')

        return cleaned_data


class UserUpdateForm(RoleChoiceMixin, forms.ModelForm):
    role = forms.ChoiceField(
        label='Role',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'mobile', 'role']

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address',
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mobile number',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('A user with this email already exists.')
        return email


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User_Profile
        fields = ['country', 'state', 'city', 'address', 'pin_code']

        widgets = {
            'country': forms.Select(attrs={'class': 'form-select'}),
            'state': forms.Select(attrs={'class': 'form-select'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pin_code': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].required = False
        self.fields['state'].required = False
        self.fields['city'].required = False

        self.fields['country'].queryset = Country.objects.all().order_by('country_name')
        self.fields['state'].queryset = State.objects.all().order_by('state_name')
        self.fields['city'].queryset = City.objects.all().order_by('city_name')

class SetNewPasswordForm(forms.Form):
    new_password1 = forms.CharField(label="New Password",required=True, widget=forms.PasswordInput(attrs={ "class":"form-control", "placeholder":"Enter Password"}))
    new_password2 = forms.CharField(label="Confirm Password",required=True, widget=forms.PasswordInput(attrs={"class":"form-control", "placeholder":"Confirm Password"}))

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 != password2:
            raise forms.ValidationError("Please Enter correct pasword they are not same")

        return cleaned_data


