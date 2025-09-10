from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.contrib.auth.models import User, Group
from .models import CashEntry, Category, Book, BookMember, UserProfile
from .forms import CashEntryForm, CategoryForm, BookForm, UserRegistrationForm, CreateUserForBookForm
import json
from django.http import JsonResponse, HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import openpyxl
from django.db import models
import secrets
import string
import logging
from django.db import transaction
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # Add this import for month calculations
from django.utils import timezone

logger = logging.getLogger(__name__)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            admin_group, _ = Group.objects.get_or_create(name='Admin')
            user.groups.add(admin_group)
            # UserProfile.objects.create(user=user, created_by=request.user)  # Track creator
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Error during registration. Please check the form.')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in successfully.')
            return redirect('homepage')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')

def user_logout(request):
    try:
        logout(request)
        messages.success(request, 'Logged out successfully.')
        return redirect('login')
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        messages.error(request, 'An error occurred during logout. Please try again.')
        return redirect('homepage')
    
@login_required
def homepage(request):
    # Get books the user owns or is a member of, sorted by created_at descending
    books = Book.objects.filter(
        Q(created_by=request.user) | Q(members__user=request.user)
    ).distinct().order_by('-created_at')
    
    # Calculate net balance for each book
    books_with_balance = []
    for book in books:
        cash_in = CashEntry.objects.filter(book=book, transaction_type='IN').aggregate(total_in=Sum('amount'))['total_in'] or 0
        cash_out = CashEntry.objects.filter(book=book, transaction_type='OUT').aggregate(total_out=Sum('amount'))['total_out'] or 0
        net_balance = cash_in - cash_out
        books_with_balance.append({
            'book': book,
            'net_balance': net_balance
        })
    
    # Log the sorted books for debugging
    logger.info(f"Homepage books for user {request.user.username}: {[{'name': item['book'].name, 'created_at': item['book'].created_at} for item in books_with_balance]}")
    
    return render(request, 'homepage.html', {
        'books_with_balance': books_with_balance,
        'user': request.user
    })

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # For month calculations

@login_required
def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    # Check if user has permission to view the book
    if not (
        request.user.groups.filter(name='Admin').exists() or
        book.created_by == request.user or
        BookMember.objects.filter(book=book, user=request.user).exists()
    ):
        messages.error(request, 'You do not have permission to view this book.')
        logger.error(f"Permission denied for User: {request.user.username}, Book ID: {book.id}")
        return redirect('homepage')
    
    # Define categories early to avoid undefined variable error
    try:
        categories = Category.objects.filter(book=book)
        logger.info(f"Categories for Book ID {book.id}: {list(categories.values('id', 'name'))}")
    except Exception as e:
        logger.error(f"Error fetching categories for Book ID {book.id}: {str(e)}")
        categories = Category.objects.none()  # Fallback to empty queryset to avoid errors

    # Get all entries for the book
    entries = CashEntry.objects.filter(book=book).order_by('-time')
    
    # Apply filters from query parameters
    date_filter = request.GET.get('date_filter')
    category_filter = request.GET.get('category')
    type_filter = request.GET.get('type')
    search_query = request.GET.get('search', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Date filter logic for Today, This Month, Last Month
    # Date filter logic
    if date_filter:
        today = datetime.now().date()
        if date_filter == 'today':
            entries = entries.filter(date=today)
        elif date_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            entries = entries.filter(date=yesterday)
        elif date_filter == 'this_month':
            start_of_month = today.replace(day=1)
            entries = entries.filter(date__gte=start_of_month, date__lte=today)
        elif date_filter == 'last_month':
            last_month = today - relativedelta(months=1)
            start_of_last_month = last_month.replace(day=1)
            end_of_last_month = start_of_last_month + relativedelta(months=1, days=-1)
            entries = entries.filter(date__gte=start_of_last_month, date__lte=end_of_last_month)
        elif date_filter == 'custom' and start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                if start_date > end_date:
                    messages.error(request, 'Start date cannot be after end date.')
                    logger.error(f"Invalid date range: Start date {start_date} is after end date {end_date}")
                else:
                    entries = entries.filter(date__gte=start_date, date__lte=end_date)
            except ValueError:
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
                logger.error(f"Invalid date format for start_date: {start_date}, end_date: {end_date}")

    # Category filter
    if category_filter:
        entries = entries.filter(category__id=category_filter)
    
    # Transaction type filter
    if type_filter:
        entries = entries.filter(transaction_type=type_filter)
    
    # Search query filter
    if search_query:
        entries = entries.filter(Q(remarks__icontains=search_query) | Q(amount__icontains=search_query))

    # Calculate cash in, cash out, and net balance
    cash_in = entries.filter(transaction_type='IN').aggregate(Sum('amount'))['amount__sum'] or 0
    cash_out = entries.filter(transaction_type='OUT').aggregate(Sum('amount'))['amount__sum'] or 0
    net_balance = cash_in - cash_out

    # Paginate entries for all users
    paginator = Paginator(entries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    entry_data = []
    running_balance = 0
    for entry in page_obj:
        if entry.transaction_type == 'IN':
            running_balance += entry.amount
        else:
            running_balance -= entry.amount
        serialized_entry = {
            'id': entry.id,
            'transaction_type': entry.get_transaction_type_display(),
            'amount': str(entry.amount),
            'date': entry.date.isoformat() if entry.date else '',
            'time': entry.time.strftime('%H:%M:%S') if entry.time else '',
            'remarks': entry.remarks or '',
            'category': entry.category.name if entry.category else '',
            'image': entry.image.url if entry.image else '',
            'optional_field': entry.optional_field or '',
            'user': entry.user.username if entry.user else '',
            'created_at': entry.created_at.isoformat() if entry.created_at else '',
            'book_id': entry.book.id,
            'running_balance': str(running_balance),
        }
        entry_data.append((entry, json.dumps(serialized_entry, ensure_ascii=False), running_balance))

    context = {
        'book': book,
        'entry_data': entry_data,
        'categories': categories,  # Use the defined categories variable
        'cash_in': cash_in,
        'cash_out': cash_out,
        'net_balance': net_balance,
        'search_query': search_query,
        'page_obj': page_obj,
        'current_user': request.user,
        'is_book_admin': (
            request.user.groups.filter(name='Admin').exists() or
            book.created_by == request.user or
            BookMember.objects.filter(book=book, user=request.user, role='admin').exists()
        ),
        'can_add_entry': (
            request.user.groups.filter(name='Admin').exists() or
            request.user.groups.filter(name='Manager').exists() or
            book.created_by == request.user or
            BookMember.objects.filter(book=book, user=request.user, role__in=['admin', 'manager']).exists()
        ),
        'can_generate_report': (
            request.user.groups.filter(name='Admin').exists() or
            request.user.groups.filter(name='Manager').exists() or
            book.created_by == request.user or
            BookMember.objects.filter(book=book, user=request.user, role='admin').exists()
        ),
        'date_filter': date_filter,  # Pass date_filter to template
    }
    
    logger.info(f"Book Detail - User: {request.user.username}, Book ID: {book.id}, "
                f"Entries Count: {entries.count()}, Cash In: {cash_in}, Cash Out: {cash_out}, Net Balance: {net_balance}, "
                f"Categories Count: {categories.count()}, "
                f"Date Filter: {date_filter}, Start Date: {start_date or 'N/A'}, End Date: {end_date or 'N/A'}, "
                f"Is Book Admin: {context['is_book_admin']}, Can Add Entry: {context['can_add_entry']}, "
                f"BookMember Role: {BookMember.objects.filter(book=book, user=request.user).values('role').first() or 'None'}")
    
    return render(request, 'book_detail.html', context)


# @login_required
# def book_detail(request, book_id):
#     book = get_object_or_404(Book, id=book_id)
#     # Check if user has permission to view the book
#     if not (
#         request.user.groups.filter(name='Admin').exists() or
#         book.created_by == request.user or
#         BookMember.objects.filter(book=book, user=request.user).exists()
#     ):
#         messages.error(request, 'You do not have permission to view this book.')
#         logger.error(f"Permission denied for User: {request.user.username}, Book ID: {book.id}")
#         return redirect('homepage')
    
#     # Get all entries for the book
#     entries = CashEntry.objects.filter(book=book).order_by('-time')
    
#     # Apply filters from query parameters
#     date_filter = request.GET.get('date_filter')
#     category_filter = request.GET.get('category')
#     type_filter = request.GET.get('type')
#     search_query = request.GET.get('search', '')

#     if date_filter:
#         today = datetime.now().date()
#         if date_filter == 'today':
#             entries = entries.filter(date=today)
#         elif date_filter == 'this_month':
#             start_of_month = today.replace(day=1)
#             entries = entries.filter(date__gte=start_of_month, date__lte=today)
#         elif date_filter == 'last_month':
#             last_month = today - relativedelta(months=1)
#             start_of_last_month = last_month.replace(day=1)
#             end_of_last_month = start_of_last_month + relativedelta(months=1, days=-1)
#             entries = entries.filter(date__gte=start_of_last_month, date__lte=end_of_last_month)
#     if category_filter:
#         entries = entries.filter(category__id=category_filter)
#     if type_filter:
#         entries = entries.filter(transaction_type=type_filter)
#     if search_query:
#         entries = entries.filter(Q(remarks__icontains=search_query) | Q(amount__icontains=search_query))

#     # Calculate cash in, cash out, and net balance
#     cash_in = entries.filter(transaction_type='IN').aggregate(Sum('amount'))['amount__sum'] or 0
#     cash_out = entries.filter(transaction_type='OUT').aggregate(Sum('amount'))['amount__sum'] or 0
#     net_balance = cash_in - cash_out

#     # Paginate entries for all users
#     paginator = Paginator(entries, 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     entry_data = []
#     running_balance = 0
#     for entry in page_obj:
#         if entry.transaction_type == 'IN':
#             running_balance += entry.amount
#         else:
#             running_balance -= entry.amount
#         serialized_entry = {
#             'id': entry.id,
#             'transaction_type': entry.get_transaction_type_display(),
#             'amount': str(entry.amount),
#             'date': entry.date.isoformat() if entry.date else '',
#             'time': entry.time.strftime('%H:%M:%S') if entry.time else '',
#             'remarks': entry.remarks or '',
#             'category': entry.category.name if entry.category else '',
#             'image': entry.image.url if entry.image else '',
#             'optional_field': entry.optional_field or '',
#             'user': entry.user.username if entry.user else '',
#             'created_at': entry.created_at.isoformat() if entry.created_at else '',
#             'book_id': entry.book.id,
#             'running_balance': str(running_balance),
#         }
#         entry_data.append((entry, json.dumps(serialized_entry, ensure_ascii=False), running_balance))

#         categories = Category.objects.filter(book=book)
    
#     context = {
#         'book': book,
#         'entry_data': entry_data,
#         'categories' : categories,
#         # 'categories': Category.objects.filter(created_by=request.user) if not request.user.groups.filter(name='Admin').exists() else Category.objects.all(),
#         'cash_in': cash_in,
#         'cash_out': cash_out,
#         'net_balance': net_balance,
#         'search_query': search_query,
#         'page_obj': page_obj,
#         'current_user': request.user,  # Add current user to context for modal permission check
#         'is_book_admin': (
#             request.user.groups.filter(name='Admin').exists() or
#             book.created_by == request.user or
#             BookMember.objects.filter(book=book, user=request.user, role='admin').exists()
#         ),
#         'can_add_entry': (
#             request.user.groups.filter(name='Admin').exists() or
#             request.user.groups.filter(name='Manager').exists() or
#             book.created_by == request.user or
#             BookMember.objects.filter(book=book, user=request.user, role__in=['admin', 'manager']).exists()
#         ),
#         'can_generate_report': (
#             request.user.groups.filter(name='Admin').exists() or
#             request.user.groups.filter(name='Manager').exists() or
#             book.created_by == request.user or
#             BookMember.objects.filter(book=book, user=request.user, role='admin').exists()
#         ),
#         'date_filter': date_filter,  # Pass date_filter to template for display
#     }
    
#     logger.info(f"Book Detail - User: {request.user.username}, Book ID: {book.id}, "
#                 f"Entries Count: {entries.count()}, Cash In: {cash_in}, Cash Out: {cash_out}, Net Balance: {net_balance}, "
#                 f"Is Book Admin: {context['is_book_admin']}, Can Add Entry: {context['can_add_entry']}, "
#                 f"BookMember Role: {BookMember.objects.filter(book=book, user=request.user).values('role').first() or 'None'}")
    
#     return render(request, 'book_detail.html', context)


@login_required
def create_user_for_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    # Only Admins, book creators, or book admins can add users
    if not (request.user.groups.filter(name='Admin').exists() or 
            book.created_by == request.user or 
            BookMember.objects.filter(book=book, user=request.user, role='admin').exists()):
        messages.error(request, 'You do not have permission to create users for this book.')
        return redirect('book_detail', book_id=book.id)
    if request.method == 'POST':
        form = CreateUserForBookForm(request.POST, request=request, book=book)
        if form.is_valid():
            select_user = form.cleaned_data['select_user']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            system_role = form.cleaned_data['system_role']
            book_role = form.cleaned_data['book_role']
            try:
                if select_user:
                    user = select_user
                    if BookMember.objects.filter(book=book, user=user).exists():
                        messages.error(request, f'User {user.username} is already a member of this book.')
                        return render(request, 'create_user_for_book.html', {'form': form, 'book': book})
                else:
                    user = User.objects.create_user(
                        username=username,
                        password=password
                    )
                    UserProfile.objects.create(user=user, created_by=request.user)  # Track creator
                    group, _ = Group.objects.get_or_create(name=system_role.capitalize())
                    user.groups.add(group)
                
                BookMember.objects.create(
                    book=book,
                    user=user,
                    role=book_role,
                    created_by=request.user  # Set the Admin who added the user
                )
                logger.info(f"Created BookMember - User: {user.username}, Book ID: {book.id}, Book Role: {book_role}, System Role: {system_role}, Created By: {request.user.username}")
                
                return render(request, 'user_created_success.html', {
                    'book': book,
                    'username': user.username,
                    'password': password if not select_user else 'N/A (Existing User)',
                    'system_role': system_role,
                    'book_role': book_role,
                })
            except Exception as e:
                messages.error(request, f'Error creating or adding user: {str(e)}')
                logger.error(f"Error creating BookMember - User: {username}, Book ID: {book_id}, Error: {str(e)}")
        else:
            messages.error(request, 'Error in the form. Please check your input.')
    else:
        form = CreateUserForBookForm(request=request, book=book)
    
    return render(request, 'create_user_for_book.html', {
        'form': form,
        'book': book,
    })


@login_required
def add_book(request):
    if request.user.groups.filter(name='Partner').exists():
        messages.error(request, 'Partners cannot create books.')
        return redirect('homepage')
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.created_by = request.user
            book.save()
            BookMember.objects.create(book=book, user=request.user, role='admin')
            messages.success(request, 'Book created successfully.')
            return redirect('homepage')
        else:
            messages.error(request, 'Error creating book. Please check the form.')
    else:
        form = BookForm()
    return render(request, 'add_book.html', {'form': form})


@login_required
def add_entry(request, book_id, transaction_type):
    book = get_object_or_404(Book, id=book_id)
    # Check if user is an Admin, book creator, or has admin/manager role in BookMember
    is_authorized = (
        request.user.groups.filter(name='Admin').exists() or
        book.created_by == request.user or
        BookMember.objects.filter(book=book, user=request.user, role__in=['admin', 'manager']).exists()
    )
    logger.info(f"User: {request.user.username}, Book: {book.id}, "
                f"Is Admin: {request.user.groups.filter(name='Admin').exists()}, "
                f"Is Book Creator: {book.created_by == request.user}, "
                f"BookMember Role: {BookMember.objects.filter(book=book, user=request.user).values('role').first()}")
    if not is_authorized:
        messages.error(request, 'You do not have permission to add entries to this book.')
        return redirect('book_detail', book_id=book.id)
    
    if request.method == 'POST':
        if 'add_category' in request.POST:
            if request.user.groups.filter(name='Partner').exists():
                messages.error(request, 'Partners cannot create categories.')
                return redirect('add_entry', book_id=book_id, transaction_type=transaction_type)
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                category = category_form.save(commit=False)
                category.created_by = request.user
                category.book = book
                category.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'category_id': category.id,
                        'category_name': category.name
                    })
                else:
                    messages.success(request, 'Category added successfully.')
                    return redirect('add_entry', book_id=book_id, transaction_type=transaction_type)
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'errors': category_form.errors
                    }, status=400)
                messages.error(request, 'Error adding category. Please check the form.')
        else:
            form = CashEntryForm(request.POST, request.FILES, book=book)
            if form.is_valid():
                entry = form.save(commit=False)
                entry.book = book
                entry.user = request.user
                entry.transaction_type = transaction_type
                entry.date = datetime.now().date()
                entry.time = datetime.now().time()
                entry.save()
                messages.success(request, f'{"Cash In" if transaction_type == "IN" else "Cash Out"} added successfully.')
                if 'save_and_add' in request.POST:
                    return redirect('add_entry', book_id=book.id, transaction_type=transaction_type)
                return redirect('book_detail', book_id=book.id)
            else:
                messages.error(request, 'Error adding entry. Please check the form.')
    else:
        form = CashEntryForm(initial={'transaction_type': transaction_type}, book=book)
    
    category_form = CategoryForm()
    return render(request, 'add_entry.html', {
        'form': form,
        'category_form': category_form,
        'book': book,
        'transaction_type': transaction_type,
        'current_date': timezone.now().date(),  # Add for display
        'current_time': timezone.now().time(),  # Add for display
    })


@login_required
def edit_entry(request, book_id, pk):
    book = get_object_or_404(Book, id=book_id)
    entry = get_object_or_404(CashEntry, id=pk, book=book)
    # Check if user is an Admin, book creator, or has admin/manager role in BookMember
    is_authorized = (
        request.user.groups.filter(name='Admin').exists() or
        book.created_by == request.user or
        BookMember.objects.filter(book=book, user=request.user, role__in=['admin', 'manager']).exists()
    )
    logger.info(f"User: {request.user.username}, Book: {book.id}, "
                f"Is Admin: {request.user.groups.filter(name='Admin').exists()}, "
                f"Is Book Creator: {book.created_by == request.user}, "
                f"BookMember Role: {BookMember.objects.filter(book=book, user=request.user).values('role').first()}")
    if not is_authorized:
        messages.error(request, 'You do not have permission to edit this entry.')
        return redirect('book_detail', book_id=book.id)
    if request.method == 'POST':
        form = CashEntryForm(request.POST, request.FILES, instance=entry, book=book)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entry updated successfully.')
            return redirect('book_detail', book_id=book.id)
        else:
            messages.error(request, 'Error updating entry. Please check the form.')
    else:
        form = CashEntryForm(instance=entry, book=book)
    return render(request, 'edit_entry.html', {
        'form': form,
        'book': book,
        'entry': entry,
    })


@login_required
def delete_entry(request, book_id, pk):
    book = get_object_or_404(Book, id=book_id)
    entry = get_object_or_404(CashEntry, id=pk, book=book)
    # Check if user is an Admin, book creator, or has admin/manager role in BookMember
    is_authorized = (
        request.user.groups.filter(name='Admin').exists() or
        book.created_by == request.user or
        BookMember.objects.filter(book=book, user=request.user, role__in=['admin', 'manager']).exists()
    )
    logger.info(f"User: {request.user.username}, Book: {book.id}, "
                f"Is Admin: {request.user.groups.filter(name='Admin').exists()}, "
                f"Is Book Creator: {book.created_by == request.user}, "
                f"BookMember Role: {BookMember.objects.filter(book=book, user=request.user).values('role').first()}")
    if not is_authorized:
        messages.error(request, 'You do not have permission to delete this entry.')
        return redirect('book_detail', book_id=book.id)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Entry deleted successfully.')
        return redirect('book_detail', book_id=book.id)
    return render(request, 'delete_entry.html', {
        'book': book,
        'entry': entry,
    })

@login_required
def manage_categories(request):
    if request.user.groups.filter(name='Partner').exists():
        messages.error(request, 'Partners cannot manage categories.')
        return redirect('homepage')
    # Only show categories for books the user has access to
    books = Book.objects.filter(
        Q(created_by=request.user) | Q(members__user=request.user)
    ).distinct()
    categories = Category.objects.filter(book__in=books)
    return render(request, 'manage_categories.html', {
        'categories': categories,
    })

@login_required
def edit_category(request, pk):
    category = get_object_or_404(Category, id=pk)
    if not (request.user.groups.filter(name='Admin').exists() or 
            category.created_by == request.user or 
            BookMember.objects.filter(book=category.book, user=request.user, role='admin').exists()):
        messages.error(request, 'You do not have permission to edit this category.')
        return redirect('manage_categories')
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully.')
            return redirect('manage_categories')
        else:
            messages.error(request, 'Error updating category. Please check the form.')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'edit_category.html', {
        'form': form,
        'category': category,
    })

@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, id=pk)
    if not (request.user.groups.filter(name='Admin').exists() or 
            category.created_by == request.user or 
            BookMember.objects.filter(book=category.book, user=request.user, role='admin').exists()):
        messages.error(request, 'You do not have permission to delete this category.')
        return redirect('manage_categories')
    if request.method == 'POST':
        if CashEntry.objects.filter(category=category).exists():
            messages.error(request, 'Cannot delete category because it is associated with one or more entries.')
            return redirect('manage_categories')
        category.delete()
        messages.success(request, 'Category deleted successfully.')
        return redirect('manage_categories')
    return render(request, 'delete_category.html', {
        'category': category,
    })


@login_required
def edit_user(request, user_id, book_id=None):
    user = get_object_or_404(User, id=user_id)
    book = get_object_or_404(Book, id=book_id) if book_id else None
    book_member = BookMember.objects.filter(book=book, user=user).first() if book else None
    instance = book_member if book else user  # Use User for system-wide edits

    # Permission check
    is_authorized = (
        request.user.groups.filter(name='Admin').exists() or
        (book and (
            book.created_by == request.user or
            BookMember.objects.filter(book=book, user=request.user, role='admin').exists()
        ))
    )
    if not is_authorized:
        messages.error(request, 'You do not have permission to edit users.')
        logger.error(f"Permission denied for User: {request.user.username} to edit User: {user.username}, Book ID: {book_id or 'N/A'}")
        return redirect('manage_my_users')

    if request.method == 'POST':
        form = CreateUserForBookForm(
            request.POST,
            request=request,
            book=book,
            instance=instance
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    old_username = user.username
                    old_group = user.groups.first().name if user.groups.exists() else 'None'
                    old_book_role = book_member.role if book_member else 'None'
                    user.username = form.cleaned_data['username']
                    user.save()
                    system_role = form.cleaned_data['system_role']
                    group, _ = Group.objects.get_or_create(name=system_role.capitalize())
                    user.groups.clear()
                    user.groups.add(group)
                    if book and form.cleaned_data['book_role']:
                        if book_member:
                            book_member.role = form.cleaned_data['book_role']
                            book_member.save()
                        else:
                            book_member = BookMember.objects.create(
                                book=book,
                                user=user,
                                role=form.cleaned_data['book_role'],
                                created_by=request.user
                            )
                    logger.info(f"User updated: Old Username={old_username}, New Username={user.username}, Old System Role={old_group}, New System Role={system_role}, Old Book Role={old_book_role}, New Book Role={form.cleaned_data['book_role'] if book else 'N/A'}, Book ID={book_id or 'N/A'}")
                    messages.success(request, f'User {user.username} updated successfully.')
                    if request.user == user:  # Refresh session for current user
                        user = authenticate(request, username=user.username, password=user.password)
                        if user:
                            login(request, user)
                            logger.info(f"Session refreshed for User: {user.username}")
                    return redirect('manage_my_users')
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
                logger.error(f"Error updating User: {user.username}, Error: {str(e)}")
        else:
            messages.error(request, 'Error updating user. Please check the form.')
            logger.error(f"Form validation failed for User: {user.username}, Errors: {form.errors.as_json()}")
    else:
        initial = {
            'username': user.username,
            'system_role': user.groups.first().name.lower() if user.groups.exists() else 'partner'
        }
        if book_member:
            initial['book_role'] = book_member.role
        form = CreateUserForBookForm(
            request=request,
            book=book,
            instance=instance,
            initial=initial
        )

    return render(request, 'edit_user.html', {
        'form': form,
        'user': user,
        'book': book,
    })


@login_required
def delete_user(request, user_id, book_id=None):
    user = get_object_or_404(User, id=user_id)
    book = get_object_or_404(Book, id=book_id) if book_id else None

    # Permission check
    is_authorized = (
        request.user.groups.filter(name='Admin').exists() or
        (book and (
            book.created_by == request.user or
            BookMember.objects.filter(book=book, user=request.user, role='admin').exists()
        ))
    )
    if not is_authorized:
        messages.error(request, 'You do not have permission to delete users.')
        logger.error(f"Permission denied for User: {request.user.username} to delete User: {user.username}, Book ID: {book_id or 'N/A'}")
        return redirect('manage_my_users')

    if book_id:
        if book.created_by == user:
            messages.error(request, 'Cannot delete the book creator.')
            logger.warning(f"Attempt to delete book creator User: {user.username} for Book ID: {book_id}")
            return redirect('manage_my_users')
        if request.method == 'POST':
            BookMember.objects.filter(book=book, user=user).delete()
            messages.success(request, f'User {user.username} removed from book.')
            logger.info(f"User {user.username} removed from Book ID: {book_id}")
            return redirect('manage_my_users')
        return render(request, 'delete_user.html', {
            'user': user,
            'book': book,
        })
    else:
        if request.method == 'POST':
            if Book.objects.filter(created_by=user).exists():
                messages.error(request, 'Cannot delete user who created books.')
                logger.warning(f"Attempt to delete User: {user.username} who created books")
                return redirect('manage_my_users')
            user.delete()
            messages.success(request, 'User deleted successfully.')
            logger.info(f"User {user.username} deleted from system")
            return redirect('manage_my_users')
        return render(request, 'delete_user.html', {
            'user': user,
            'book': None,
        })


@login_required
def generate_report(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    # Only Admins, Managers, book creators, or book admins can generate reports
    if not (request.user.groups.filter(name='Admin').exists() or 
            request.user.groups.filter(name='Manager').exists() or 
            book.created_by == request.user or 
            BookMember.objects.filter(book=book, user=request.user, role='admin').exists()):
        messages.error(request, 'You do not have permission to generate reports for this book.')
        return redirect('book_detail', book_id=book.id)
    categories = Category.objects.filter(book=book)
    return render(request, 'generate_report.html', {
        'book': book,
        'categories': categories,
    })

@login_required
def download_report(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if not (request.user.groups.filter(name='Admin').exists() or 
            request.user.groups.filter(name='Manager').exists() or 
            book.created_by == request.user or 
            BookMember.objects.filter(book=book, user=request.user, role='admin').exists()):
        messages.error(request, 'You do not have permission to generate reports for this book.')
        return redirect('book_detail', book_id=book.id)
    
    report_type = request.GET.get('report_type')
    report_scope = request.GET.get('report_scope')
    category_id = request.GET.get('category')
    
    if not report_type or not report_scope:
        messages.error(request, 'Please select both report type and scope.')
        return redirect('generate_report', book_id=book_id)
    
    entries = CashEntry.objects.filter(book=book)
    if report_scope == 'category' and category_id:
        entries = entries.filter(category__id=category_id)
        category_name = Category.objects.get(id=category_id).name
    else:
        category_name = 'All Categories'
    
    if report_type == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        title = Paragraph(f"Cashbook Report - {book.name} ({category_name})", styles['Title'])
        elements.append(title)
        
        data = [['Date', 'Type', 'Amount', 'Category', 'Remarks', 'Running Balance']]
        running_balance = 0
        for entry in entries.order_by('date', 'time'):
            if entry.transaction_type == 'IN':
                running_balance += entry.amount
            else:
                running_balance -= entry.amount
            data.append([
                entry.date.strftime('%Y-%m-%d'),
                entry.get_transaction_type_display(),
                str(entry.amount),
                entry.category.name if entry.category else 'N/A',
                entry.remarks or 'N/A',
                str(running_balance),
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        
        cash_in = entries.filter(transaction_type='IN').aggregate(Sum('amount'))['amount__sum'] or 0
        cash_out = entries.filter(transaction_type='OUT').aggregate(Sum('amount'))['amount__sum'] or 0
        net_balance = cash_in - cash_out
        summary = Paragraph(
            f"<br/>Summary:<br/>Cash In: {cash_in}<br/>Cash Out: {cash_out}<br/>Net Balance: {net_balance}",
            styles['Normal']
        )
        elements.append(summary)
        
        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="cashbook_report_{book.name}_{report_scope}.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        return response
    
    elif report_type == 'excel':
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = f"{book.name} Report"
        
        worksheet.append([f"Cashbook Report - {book.name} ({category_name})"])
        worksheet.append(['Date', 'Type', 'Amount', 'Category', 'Remarks', 'Running Balance'])
        
        running_balance = 0
        for entry in entries.order_by('date', 'time'):
            if entry.transaction_type == 'IN':
                running_balance += entry.amount
            else:
                running_balance -= entry.amount
            worksheet.append([
                entry.date,
                entry.get_transaction_type_display(),
                entry.amount,
                entry.category.name if entry.category else 'N/A',
                entry.remarks or 'N/A',
                running_balance,
            ])
        
        cash_in = entries.filter(transaction_type='IN').aggregate(Sum('amount'))['amount__sum'] or 0
        cash_out = entries.filter(transaction_type='OUT').aggregate(Sum('amount'))['amount__sum'] or 0
        net_balance = cash_in - cash_out
        worksheet.append([])
        worksheet.append(['Summary'])
        worksheet.append(['Cash In', cash_in])
        worksheet.append(['Cash Out', cash_out])
        worksheet.append(['Net Balance', net_balance])
        
        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = max_length + 2
            worksheet.column_dimensions[column].width = adjusted_width
        
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="cashbook_report_{book.name}_{report_scope}.xlsx"'
        response.write(buffer.getvalue())
        buffer.close()
        return response
    
    else:
        messages.error(request, 'Invalid report type selected.')
        return redirect('generate_report', book_id=book_id)


@login_required
def manage_my_users(request):
    if not request.user.groups.filter(name='Admin').exists():
        messages.error(request, 'Only Admins can manage their users.')
        return redirect('homepage')
    
    # Get BookMember entries where you are the creator
    book_members = BookMember.objects.filter(created_by=request.user).select_related('user', 'book')
    # Get unique users you added to books
    users = User.objects.filter(book_memberships__created_by=request.user).distinct()
    user_data = []
    
    for user in users:
        system_role = user.groups.first().name if user.groups.exists() else 'No Role'
        # Get books this user is assigned to
        user_book_memberships = book_members.filter(user=user)
        books = [
            {
                'book': membership.book,
                'role': membership.get_role_display(),
            }
            for membership in user_book_memberships
        ]
        user_data.append({
            'user': user,
            'system_role': system_role,
            'books': books,
            'can_manage': user != request.user  # Prevent self-deletion
        })
    
    logger.info(f"Manage My Users - Admin: {request.user.username}, Total Users: {len(users)}")
    
    context = {
        'user_data': user_data,
        'is_admin': request.user.groups.filter(name='Admin').exists(),
    }
    return render(request, 'manage_my_users.html', context)