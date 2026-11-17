from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    """Login form using email instead of username."""
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'you@example.com',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '••••••••',
        })
    )


class UserRegistrationForm(UserCreationForm):
    """Admin-only form to register new users."""

    class Meta:
        model = User
        fields = ('email', 'name', 'role', 'phone', 'profile_photo')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


class UserProfileForm(forms.ModelForm):
    """User-editable profile form."""

    class Meta:
        model = User
        fields = ('name', 'phone', 'profile_photo')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserAdminEditForm(UserChangeForm):
    """Admin form to edit any user including role."""
    password = None  # hide password hash field

    class Meta:
        model = User
        fields = ('email', 'name', 'role', 'phone', 'profile_photo', 'is_active')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
