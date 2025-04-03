from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
      required=True,
      label="Email Address",
      error_messages={'required': 'Email is required'},
      widget=forms.EmailInput(attrs={'class': 'form-control ', 'placeholder': ''})
    )
    username = forms.CharField(
      label="Username",
      error_messages={'required': 'Username is required'},
      widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': ''})
    )
    password1 = forms.CharField(
      label="Password",
      error_messages={'required': 'Password is required'},
      widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': ''})
    )

    password2 = forms.CharField(
      label="Confirm Password",
      error_messages={'required': 'Confirm password is required'},
      widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': ''})
    )

    class Meta:
      model = User
      fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
      email = self.cleaned_data.get('email')
      if User.objects.filter(email=email).exists():
        raise forms.ValidationError("Email already exists.")
      return email

    def clean_username(self):
      username = self.cleaned_data.get('username')
      if User.objects.filter(username=username).exists():
        raise forms.ValidationError("Username already exists.")
      return username
    

