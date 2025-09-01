from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Book(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class BookMember(models.Model):
    ROLE_CHOICES = (
        ('partner', 'Partner'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    # invited_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_book_members', help_text="User who added this member to the book")

    class Meta:
        unique_together = ('book', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.role} in {self.book.name}"


class Category(models.Model):
    name = models.CharField(max_length=100)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='categories')  # Tie categories to a book
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CashEntry(models.Model):
    TRANSACTION_TYPES = (
        ('IN', 'Cash In'),
        ('OUT', 'Cash Out'),
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    time = models.TimeField(default=timezone.now)
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField(blank=True)
    image = models.ImageField(upload_to='cashbook_images/', blank=True, null=True)
    optional_field = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} in {self.book.name}"