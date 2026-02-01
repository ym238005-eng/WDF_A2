from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

# Create your models here.
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    cover_pic = models.ImageField(upload_to='cover_pics/', blank=True)
    isbn = models.CharField(max_length=13, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=50)
    published_date = models.DateField()
    available_copies = models.PositiveIntegerField(default=1)

    # Add genre for search functionality
    GENRE_CHOICES = [
        ('FICTION', 'Fiction'),
        ('NON_FICTION', 'Non-Fiction'),
        ('SCI_FI', 'Science Fiction'),
        ('MYSTERY', 'Mystery'),
        ('ROMANCE', 'Romance'),
        ('BIOGRAPHY', 'Biography'),
        ('HISTORY', 'History'),
    ]
    
    genre = models.CharField(max_length=20, choices=GENRE_CHOICES, default='FICTION')

    def __str__(self):
        return self.title
    
    # Add these methods for borrowing functionality
    def can_borrow(self):
        return self.available_copies > 0
    
    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            total = sum([review.rating for review in reviews])
            return round(total / len(reviews), 1)
        return 0
    
    @property
    def rating_count(self):
        return self.reviews.count()
    
    def get_user_review(self, user):
        """Get user's review for this book if it exists"""
        try:
            return self.reviews.get(user=user)
        except Review.DoesNotExist:
            return None
    
    def has_user_reviewed(self, user):
        """Check if user has reviewed this book"""
        return self.reviews.filter(user=user).exists()
    
    @property
    def total_borrowed(self):
        """Get total number of times this book has been borrowed"""
        return self.borrowings.count()
    
    def get_genre_display(self):
        """Get human-readable genre display"""
        return dict(self.GENRE_CHOICES).get(self.genre, self.genre)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Add Borrowing and Review models
class Borrowing(models.Model):
    STATUS_CHOICES = [
        ('BORROWED', 'Borrowed'),
        ('RETURNED', 'Returned'),
        ('OVERDUE', 'Overdue'),
        ('RESERVED', 'Reserved'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    borrowed_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    returned_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BORROWED')
    late_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.status})"
    
    def is_overdue(self):
        if self.status == 'BORROWED' and timezone.now() > self.due_date:
            return True
        return False
    
    def calculate_late_fee(self):
        if self.is_overdue():
            days_overdue = (timezone.now() - self.due_date).days
            return Decimal(days_overdue) * Decimal('0.50')  # $0.50 per day
        return Decimal('0.00')
    
    # Property methods for templates
    @property
    def overdue_days(self):
        """Calculate number of overdue days"""
        if self.is_overdue():
            days_overdue = (timezone.now() - self.due_date).days
            return max(0, days_overdue)
        return 0
    
    @property
    def days_left(self):
        """Calculate days left until due date"""
        if self.status == 'BORROWED' and not self.is_overdue():
            days_left = (self.due_date - timezone.now()).days
            return max(0, days_left)
        return 0
    
    @property
    def total_late_fee(self):
        """Total late fee for display in templates"""
        return self.calculate_late_fee()
    
    def save(self, *args, **kwargs):
        """Update status to OVERDUE if book is overdue"""
        if self.status == 'BORROWED' and self.is_overdue():
            self.status = 'OVERDUE'
        super().save(*args, **kwargs)

class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['book', 'user']  # One review per user per book
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.rating} stars)"
    
    def get_rating_display(self):
        """Get human-readable rating display"""
        return dict(self.RATING_CHOICES).get(self.rating, f"{self.rating} Stars")
    
    def get_stars(self):
        """Get star representation of rating"""
        return '★' * self.rating + '☆' * (5 - self.rating)