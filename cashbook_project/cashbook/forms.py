from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Book, Category, CashEntry, BookMember

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

class CreateUserForBookForm(forms.Form):
    select_user = forms.ModelChoiceField(
        queryset=User.objects.none(),  # Will be set in __init__
        required=False,
        label="Select Existing User",
        empty_label="Create New User",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="New Username"
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Password"
    )
    system_role = forms.ChoiceField(
        choices=[
            ('manager', 'Manager'),
            ('partner', 'Partner'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="System Role"
    )
    book_role = forms.ChoiceField(
        choices=BookMember.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Book Role"
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.request:
            # Filter users to those associated with books created by the current user
            self.fields['select_user'].queryset = User.objects.filter(
                book_memberships__book__created_by=self.request.user
            ).distinct()

    def clean(self):
        cleaned_data = super().clean()
        select_user = cleaned_data.get('select_user')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if not select_user and not (username and password):
            raise ValidationError("Please either select an existing user or provide a new username and password.")
        if select_user and (username or password):
            raise ValidationError("Do not provide username or password when selecting an existing user.")
        if username and User.objects.filter(username=username).exists():
            raise ValidationError("A user with that username already exists.")

        return cleaned_data

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CashEntryForm(forms.ModelForm):
    class Meta:
        model = CashEntry
        fields = ['transaction_type', 'amount', 'date', 'time', 'remarks', 'category', 'image', 'optional_field']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'optional_field': forms.TextInput(attrs={'class': 'form-control'}),
        }










# from django import forms
# from django.contrib.auth.models import User
# from django.contrib.auth.forms import UserCreationForm
# from .models import Book, Category, CashEntry, BookMember

# class UserRegistrationForm(UserCreationForm):
#     # email = forms.EmailField(required=True)
#     class Meta:
#         model = User
#         fields = ['username', 'password1', 'password2']

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['username'].widget.attrs.update({'class': 'form-control'})
#         self.fields['password1'].widget.attrs.update({'class': 'form-control'})
#         self.fields['password2'].widget.attrs.update({'class': 'form-control'})

#     # def clean_email(self):
#     #     email = self.cleaned_data.get('email')
#     #     if User.objects.filter(email=email).exists():
#     #         raise forms.ValidationError("A user with that email address already exists.")
#     #     return 
    
#     def clean_username(self):
#       username = self.cleaned_data.get('username')
#       if User.objects.filter(username=username).exists():
#         raise forms.ValidationError("A user with that username already exists.")
#       return username

# class CreateUserForBookForm(forms.Form):
#     username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
#     password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
#     system_role = forms.ChoiceField(choices=[
#         ('manager', 'Manager'),
#         ('partner', 'Partner'),
#     ], widget=forms.Select(attrs={'class': 'form-control'}))
#     book_role = forms.ChoiceField(choices=BookMember.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))

#     def clean_username(self):
#         username = self.cleaned_data.get('username')
#         if User.objects.filter(username=username).exists():
#             raise forms.ValidationError("A user with that username already exists.")
#         return username
    

# class BookForm(forms.ModelForm):
#     class Meta:
#         model = Book
#         fields = ['name']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#         }

# class CategoryForm(forms.ModelForm):
#     class Meta:
#         model = Category
#         fields = ['name']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#         }

# class CashEntryForm(forms.ModelForm):
#     class Meta:
#         model = CashEntry
#         fields = ['transaction_type', 'amount', 'date', 'time', 'remarks', 'category', 'image', 'optional_field']
#         widgets = {
#             'transaction_type': forms.Select(attrs={'class': 'form-control'}),
#             'amount': forms.NumberInput(attrs={'class': 'form-control'}),
#             'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
#             'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
#             'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
#             'category': forms.Select(attrs={'class': 'form-control'}),
#             'image': forms.FileInput(attrs={'class': 'form-control'}),
#             'optional_field': forms.TextInput(attrs={'class': 'form-control'}),
#         }