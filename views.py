from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from .form import Bookform, ReviewForm
from .models import Book, UserProfile, Borrowing, Review
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# Create your views here.
# List all books
def book_list(request):
    books = Book.objects.all()
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        books = books.filter(
            Q(title__icontains=search) | 
            Q(author__icontains=search) |
            Q(genre__icontains=search)
        )
    
    return render(request, 'book_list.html', {'books': books})

def home(request):
    message = "Welcome to the Library Management System"
    return render(request, 'home.html', {'message': message})

#Delete Book View
def delete_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if request.method == 'POST':
        book.delete()
        return redirect('book_list')
    
    return render(request, 'confirm_delete.html', {'book': book})

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def user_dashboard(request):
    users = User.objects.all().order_by('-date_joined')
    stats = {
        'total': users.count(),
        'staff': users.filter(is_staff=True).count(),
        'recent': users.filter(is_active=True).count(),
    }
    return render(request, 'user_dashboard.html', {'users': users, 'stats': stats})

@user_passes_test(is_admin)
def user_create(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New user created successfully!")
            return redirect('user_dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'user_form.html', {'form': form, 'title': 'Add New User'})

@user_passes_test(is_admin)
def user_edit(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # Using a simplified form for admin updates
        target_user.email = request.POST.get('email')
        target_user.first_name = request.POST.get('first_name')
        target_user.last_name = request.POST.get('last_name')
        target_user.is_staff = 'is_staff' in request.POST
        target_user.save()
        messages.success(request, f"User {target_user.username} updated!")
        return redirect('user_dashboard')
    return render(request, 'user_edit_form.html', {'target_user': target_user})

#create view to add
def book_create(request):

    if request.method == 'POST':
        form = Bookform(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect('book_list')
    else:
        form = Bookform()
    return render(request, 'book_form.html', {'form': form})

#update view to edit existing book details
@user_passes_test(is_admin)
def book_update(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if request.method == 'POST':
        form = Bookform(request.POST, request.FILES, instance=book)

        if form.is_valid():
            form.save()
            messages.success(request, f"'{book.title}' updated successfully!")
            return redirect('book_list')
    else:
        form = Bookform(instance=book)
    return render(request, 'book_update.html', {'form': form, 'is_update': True})

# Thank You page view
def thank_you(request):
    return render(request, 'thank_you.html')

#User Functionalities
#Register user
def register(request):
    # Registration logic here
    if request.method == 'POST':
        # user table fields
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        # profile table fields
        bio = request.POST.get('bio', '').strip()
        profile_pic = request.FILES.get('profile_picture')

# Get terms checkbox
        terms = request.POST.get('terms')
        error_messages = []
        
        # Validate username
        if not username:
            error_messages.append("Username is required.")
        elif len(username) < 3:
            error_messages.append("Username must be at least 3 characters long.")
        elif User.objects.filter(username=username).exists():
            error_messages.append("Username already exists. Please choose a different username.")
        
        # Validate email
        if not email:
            error_messages.append("Email is required.")
        elif '@' not in email or '.' not in email:
            error_messages.append("Please enter a valid email address.")
        elif User.objects.filter(email=email).exists():
            error_messages.append("Email is already registered. Please use a different email.")
        
        # Validate first and last name
        if not first_name:
            error_messages.append("First name is required.")
        if not last_name:
            error_messages.append("Last name is required.")
        
        # Validate password
        if not password:
            error_messages.append("Password is required.")
        elif len(password) < 6:
            error_messages.append("Password must be at least 6 characters long.")
        elif password != password_confirm:
            error_messages.append("Passwords do not match.")
        
        # Validate terms and conditions
        if not terms:
            error_messages.append("You must agree to the Terms and Conditions.")
        
        # If there are errors, display them
        if error_messages:
            for error in error_messages:
                messages.error(request, error)
            
            # Preserve form data on error
            context = {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'bio': bio,
            }
            return render(request, 'register.html', context)
        
        # Create the user
        try:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password
            )
            
            # Create user profile
            profile = UserProfile.objects.create(user=user, bio=bio)
            
            # Handle profile picture if provided
            if profile_pic:
                # Check file size (5MB max)
                if profile_pic.size > 5 * 1024 * 1024:
                    messages.error(request, "Profile picture is too large. Maximum size is 5MB.")
                    user.delete()  # Rollback user creation
                    context = {
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'bio': bio,
                    }
                    return render(request, 'register.html', context)
                
                profile.profile_pic = profile_pic
            
            profile.save()
            
            # Send confirmation email
            try:
                subject = 'Welcome to Silent Library - Registration Confirmation'
                message = f'''
Dear {first_name} {last_name},

Thank you for registering with Silent Library!

Your account has been successfully created with the following details:
Username: {username}
Email: {email}
Name: {first_name} {last_name}

You can now login to access our library services, borrow books, and manage your reading lists.

Click here to login: {request.build_absolute_uri('/login')}

Happy Reading!

Best regards,
The Silent Library Team
                '''
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [email]
                
                send_mail(
                    subject,
                    message,
                    from_email,
                    recipient_list,
                    fail_silently=True,
                )
                # Don't show email error to user if it fails
            except Exception as e:
                # Just log the error but continue
                print(f"Email sending failed: {e}")
            
            # Redirect to thank you page
            return redirect('thank_you')
            
        except Exception as e:
            messages.error(request, f"An error occurred during registration: {str(e)}")
            print(f"Registration error: {e}")
            return render(request, 'register.html')
    
    # GET request - show empty form
    return render(request, 'register.html')

#Login user
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)  # Use auth_login instead of login
            return redirect('profile')   
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, 'login.html')
        
    return render(request, 'login.html')

#Logout user
def logout(request):
    auth_logout(request)
    return redirect('home')

@login_required(login_url='login')
def profile(request):
    # Get or create user profile using UserProfile model
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Create a profile if it doesn't exist
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Get form data
        bio = request.POST.get('bio', '').strip()
        profile_pic = request.FILES.get('profile_pic')
        
        # Also update user's first and last name if provided
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        if first_name:
            request.user.first_name = first_name
        if last_name:
            request.user.last_name = last_name
        
        request.user.save()

        # Update profile fields
        profile.bio = bio
        
        if profile_pic:
            profile.profile_pic = profile_pic
        elif request.POST.get('remove_picture'):
            # Remove profile picture if checkbox is checked
            profile.profile_pic = None

        profile.save()

        messages.success(request, "Your profile has been updated successfully.")
        return redirect('profile')

    # GET request → show the current profile data
    # Update statistics with actual data
    total_borrowed = Borrowing.objects.filter(user=request.user).count()
    reviews_count = Review.objects.filter(user=request.user).count()
    currently_reading = Borrowing.objects.filter(user=request.user, status='BORROWED').count()
    
    context = {
        'profile': profile,
        'total_borrowed': total_borrowed,
        'reviews_count': reviews_count,
        'currently_reading': currently_reading,
        'wishlist_count': 8,  # You can implement wishlist later
    }
    return render(request, 'profile.html', context)

@user_passes_test(lambda u: u.is_superuser)
def user_delete(request, user_id):
    if request.method == 'POST':
        user_to_delete = get_object_or_404(User, id=user_id)
        if user_to_delete == request.user:
            messages.error(request, "You cannot delete your own admin account.")
        else:
            user_to_delete.delete()
            messages.success(request, "User deleted successfully.")
    return redirect('user_dashboard')


# BORROWING AND RATING FUNCTIONALITY

@login_required
def borrow_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    if not book.can_borrow():
        messages.error(request, "Sorry, this book is currently unavailable.")
        return redirect('book_list')
    
    # Check if user already has this book borrowed
    existing_borrowing = Borrowing.objects.filter(
        book=book, 
        user=request.user, 
        status='BORROWED'
    ).exists()
    
    if existing_borrowing:
        messages.warning(request, "You have already borrowed this book.")
        return redirect('book_list')
    
    # Check user's borrowing limit (max 5 books)
    active_borrowings = Borrowing.objects.filter(
        user=request.user, 
        status='BORROWED'
    ).count()
    
    if active_borrowings >= 5:
        messages.error(request, "You have reached the borrowing limit (5 books). Please return some books first.")
        return redirect('my_borrowings')
    
    if request.method == 'POST':
        borrowing = Borrowing.objects.create(
            book=book,
            user=request.user,
            due_date=timezone.now() + timedelta(days=14),
            status='BORROWED'
        )
        
        # Update book available copies
        book.available_copies -= 1
        book.save()
        
        # Send email notification
        try:
            subject = f'Book Borrowed: {book.title}'
            message = f'''
Hello {request.user.first_name},

You have successfully borrowed "{book.title}" by {book.author}.

Borrowing Details:
- Borrowed Date: {borrowing.borrowed_date.strftime("%B %d, %Y")}
- Due Date: {borrowing.due_date.strftime("%B %d, %Y")}
- Book ISBN: {book.isbn}

Please return the book by the due date to avoid late fees.

Thank you for using Silent Library!
            '''
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Email sending failed: {e}")
        
        messages.success(request, f"You have successfully borrowed '{book.title}'!")
        return redirect('my_borrowings')
    
    return render(request, 'confirm_borrow.html', {'book': book})

@login_required
def return_book(request, borrowing_id):
    borrowing = get_object_or_404(Borrowing, id=borrowing_id, user=request.user)
    
    if borrowing.status != 'BORROWED':
        messages.error(request, "This book has already been returned.")
        return redirect('my_borrowings')
    
    if request.method == 'POST':
        borrowing.status = 'RETURNED'
        borrowing.returned_date = timezone.now()
        
        # Calculate late fee if overdue
        if borrowing.is_overdue():
            borrowing.late_fee = borrowing.calculate_late_fee()
            messages.warning(request, f"Book returned late. Late fee: ${borrowing.late_fee}")
        
        borrowing.save()
        
        # Update book available copies
        book = borrowing.book
        book.available_copies += 1
        book.save()
        
        messages.success(request, f"You have returned '{book.title}' successfully!")
        return redirect('my_borrowings')
    
    return render(request, 'confirm_return.html', {'borrowing': borrowing})

@login_required
def my_borrowings(request):
    borrowings = Borrowing.objects.filter(user=request.user).order_by('-borrowed_date')
    
    # Update overdue status
    for borrowing in borrowings.filter(status='BORROWED'):
        if borrowing.is_overdue():
            borrowing.status = 'OVERDUE'
            borrowing.save()
    
    # Calculate statistics
    total_late_fees = Decimal('0.00')
    for b in borrowings:
        total_late_fees += b.late_fee
    
    context = {
        'active_borrowings': borrowings.filter(status='BORROWED'),
        'overdue_borrowings': borrowings.filter(status='OVERDUE'),
        'returned_borrowings': borrowings.filter(status='RETURNED'),
        'total_late_fees': total_late_fees,
    }
    return render(request, 'my_borrowings.html', context)

@login_required
def submit_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Check if user has borrowed this book before
    has_borrowed = Borrowing.objects.filter(
        book=book, 
        user=request.user, 
        status='RETURNED'
    ).exists()
    
    if not has_borrowed:
        messages.error(request, "You can only review books you have borrowed and returned.")
        return redirect('book_list')
    
    # Check for existing review
    existing_review = Review.objects.filter(book=book, user=request.user).first()
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.book = book
            review.user = request.user
            review.save()
            messages.success(request, "Thank you for your review!")
            return redirect('book_list')
    else:
        form = ReviewForm(instance=existing_review)
    
    return render(request, 'submit_review.html', {
        'form': form, 
        'book': book,
        'existing_review': existing_review
    })

@login_required
def book_reviews(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    reviews = Review.objects.filter(book=book).order_by('-created_at')
    
    # Check if current user has reviewed this book
    user_has_reviewed = False
    user_review = None
    if request.user.is_authenticated:
        user_review = book.get_user_review(request.user)
        user_has_reviewed = book.has_user_reviewed(request.user)
    
    return render(request, 'book_reviews.html', {
        'book': book,
        'reviews': reviews,
        'average_rating': book.average_rating,
        'user_has_reviewed': user_has_reviewed,
        'user_review': user_review,
    })

# Staff view to manage all borrowings
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def manage_all_borrowings(request):
    borrowings = Borrowing.objects.all().order_by('-borrowed_date')
    
    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    if status_filter:
        borrowings = borrowings.filter(status=status_filter)
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        borrowings = borrowings.filter(
            Q(book__title__icontains=search) | 
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Calculate statistics
    total_borrowings = borrowings.count()
    overdue_count = borrowings.filter(status='OVERDUE').count()
    active_count = borrowings.filter(status='BORROWED').count()
    total_late_fees = sum(b.late_fee for b in borrowings)
    
    context = {
        'borrowings': borrowings,
        'total_borrowings': total_borrowings,
        'overdue_count': overdue_count,
        'active_count': active_count,
        'total_late_fees': total_late_fees,
        'status_filter': status_filter,
        'search_query': search,
    }
    return render(request, 'manage_borrowings.html', context)

# Staff can manually update borrowing status
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def update_borrowing_status(request, borrowing_id):
    borrowing = get_object_or_404(Borrowing, id=borrowing_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        borrowing.status = new_status
        
        if new_status == 'RETURNED' and not borrowing.returned_date:
            borrowing.returned_date = timezone.now()
            # Update book available copies
            borrowing.book.available_copies += 1
            borrowing.book.save()
        
        borrowing.save()
        messages.success(request, f"Borrowing status updated to {new_status}")
        return redirect('manage_all_borrowings')
    
    return render(request, 'update_borrowing_status.html', {'borrowing': borrowing})