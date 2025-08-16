from django.contrib import admin
from .models import Book, Category, CashEntry, BookMember
# Register your models here.

admin.site.register(Book)
admin.site.register(Category)
admin.site.register(BookMember)
admin.site.register(CashEntry)