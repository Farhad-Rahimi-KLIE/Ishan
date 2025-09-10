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
        queryset=User.objects.none(),
        required=False,
        label="Select Existing User",
        empty_label="Create New User",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Username"
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Password"
    )
    system_role = forms.ChoiceField(
        choices=[
            ('admin', 'Admin'),
            ('manager', 'Manager'),
            ('partner', 'Partner'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="System Role"
    )
    book_role = forms.ChoiceField(
        choices=BookMember.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Book Role",
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.book = kwargs.pop('book', None)
        self.instance = kwargs.pop('instance', None)  # BookMember or User instance
        super().__init__(*args, **kwargs)
        if self.request and self.book:
            if not (self.request.user.groups.filter(name='Admin').exists() or 
                    self.book.created_by == self.request.user or 
                    BookMember.objects.filter(book=self.book, user=self.request.user, role='admin').exists()):
                raise ValidationError("Only Admins, book creators, or book admins can add/edit users.")
            self.fields['select_user'].queryset = User.objects.filter(
                Q(book_memberships__book__created_by=self.book.created_by) |
                Q(id=self.book.created_by.id)
            ).distinct().exclude(book_memberships__book=self.book)
        if self.instance:
            self.fields['select_user'].disabled = True
            self.fields['select_user'].required = False
            self.fields['password'].required = False
            self.fields['password'].widget = forms.HiddenInput()
            if isinstance(self.instance, User):
                self.fields['username'].initial = self.instance.username
                self.fields['system_role'].initial = self.instance.groups.first().name.lower() if self.instance.groups.exists() else 'partner'
                self.fields['book_role'].widget = forms.HiddenInput()
                self.fields['book_role'].required = False
            else:  # BookMember
                self.fields['username'].initial = self.instance.user.username
                self.fields['system_role'].initial = self.instance.user.groups.first().name.lower() if self.instance.user.groups.exists() else 'partner'
                self.fields['book_role'].initial = self.instance.role
        if not self.book:
            self.fields['book_role'].widget = forms.HiddenInput()
            self.fields['book_role'].required = False

    def clean(self):
        cleaned_data = super().clean()
        select_user = cleaned_data.get('select_user')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        book_role = cleaned_data.get('book_role')

        if self.instance:  # Edit mode (User or BookMember)
            if select_user or password:
                print("Validation Error: select_user or password provided in edit mode")  # Debug
                raise ValidationError("Do not provide select_user or password when editing a user.")
            if not username:
                print("Validation Error: Username is missing")  # Debug
                raise ValidationError("Username is required.")
            if isinstance(self.instance, User):
                if User.objects.filter(username=username).exclude(id=self.instance.id).exists():
                    print(f"Validation Error: Username {username} already exists")  # Debug
                    raise ValidationError("A user with that username already exists.")
            else:  # BookMember
                if User.objects.filter(username=username).exclude(id=self.instance.user.id).exists():
                    print(f"Validation Error: Username {username} already exists")  # Debug
                    raise ValidationError("A user with that username already exists.")
                if self.book and not book_role:
                    print("Validation Error: Book role is missing")  # Debug
                    raise ValidationError("Book role is required when editing a user for a book.")
        else:  # Create mode
            if not select_user and not (username and password):
                print("Validation Error: No select_user or username/password provided in create mode")  # Debug
                raise ValidationError("Please either select an existing user or provide a username and password.")
            if select_user and (username or password):
                print("Validation Error: Username or password provided with select_user in create mode")  # Debug
                raise ValidationError("Do not provide username or password when selecting an existing user.")
            if username and User.objects.filter(username=username).exists():
                print(f"Validation Error: Username {username} already exists in create mode")  # Debug
                raise ValidationError("A user with that username already exists.")
            if self.book and not book_role:
                print("Validation Error: Book role is missing in create mode")  # Debug
                raise ValidationError("Book role is required when adding a user to a book.")

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
        fields = ['transaction_type', 'amount', 'remarks', 'category', 'image', 'optional_field']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            # 'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            # 'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'optional_field': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book', None)  # Extract the book parameter
        super().__init__(*args, **kwargs)
        if book:
            # Filter categories to only those associated with the given book
            self.fields['category'].queryset = Category.objects.filter(book=book)














# from django import forms
# from django.contrib.auth.models import User
# from django.contrib.auth.forms import UserCreationForm
# from django.core.exceptions import ValidationError
# from django.db.models import Q
# from .models import Book, Category, CashEntry, BookMember

# class UserRegistrationForm(UserCreationForm):
#     class Meta:
#         model = User
#         fields = ['username', 'password1', 'password2']

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['username'].widget.attrs.update({'class': 'form-control'})
#         self.fields['password1'].widget.attrs.update({'class': 'form-control'})
#         self.fields['password2'].widget.attrs.update({'class': 'form-control'})

#     def clean_username(self):
#         username = self.cleaned_data.get('username')
#         if User.objects.filter(username=username).exists():
#             raise forms.ValidationError("A user with that username already exists.")
#         return username

# class CreateUserForBookForm(forms.Form):
#     select_user = forms.ModelChoiceField(
#         queryset=User.objects.none(),  # Will be set in __init__
#         required=False,
#         label="Select Existing User",
#         empty_label="Create New User",
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )
#     username = forms.CharField(
#         max_length=150,
#         required=False,
#         widget=forms.TextInput(attrs={'class': 'form-control'}),
#         label="New Username"
#     )
#     password = forms.CharField(
#         required=False,
#         widget=forms.PasswordInput(attrs={'class': 'form-control'}),
#         label="Password"
#     )
#     system_role = forms.ChoiceField(
#         choices=[
#             ('manager', 'Manager'),
#             ('partner', 'Partner'),
#         ],
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         label="System Role"
#     )
#     book_role = forms.ChoiceField(
#         choices=BookMember.ROLE_CHOICES,
#         widget=forms.Select(attrs={'class': 'form-control'}),
#         label="Book Role"
#     )

#     def __init__(self, *args, **kwargs):
#         self.request = kwargs.pop('request', None)
#         self.book = kwargs.pop('book', None)
#         self.instance = kwargs.pop('instance', None)
#         super().__init__(*args, **kwargs)
#         if self.request and self.book:
#             # Only Admins or book creators/book admins can add users
#             if not (self.request.user.groups.filter(name='Admin').exists() or 
#                     self.book.created_by == self.request.user or 
#                     BookMember.objects.filter(book=self.book, user=self.request.user, role='admin').exists()):
#                 raise ValidationError("Only Admins can add users to a book.")
#             self.fields['select_user'].queryset = User.objects.filter(
#                 book_memberships__book__created_by=self.request.user
#             ).distinct().exclude(book_memberships__book=self.book)
#             if self.instance:
#                 # Disable select_user for editing
#                 self.fields['select_user'].disabled = True

#     def clean(self):
#         cleaned_data = super().clean()
#         select_user = cleaned_data.get('select_user')
#         username = cleaned_data.get('username')
#         password = cleaned_data.get('password')

        
#         if not self.instance:  # Create mode
#             if not select_user and not (username and password):
#                 raise ValidationError("Please either select an existing user or provide a new username and password.")
#             if select_user and (username or password):
#                 raise ValidationError("Do not provide username or password when selecting an existing user.")
#             if username and User.objects.filter(username=username).exists():
#                 raise ValidationError("A user with that username already exists.")
#         else:  # Edit mode
#             if select_user:
#                 raise ValidationError("Cannot change to another existing user during edit.")
#             if username and User.objects.filter(username=username).exclude(id=self.instance.user.id).exists():
#                 raise ValidationError("A user with that username already exists.")

#         return cleaned_data

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

#     def __init__(self, *args, **kwargs):
#         book = kwargs.pop('book', None)  # Extract the book parameter
#         super().__init__(*args, **kwargs)
#         if book:
#             # Filter categories to only those associated with the given book
#             self.fields['category'].queryset = Category.objects.filter(book=book)