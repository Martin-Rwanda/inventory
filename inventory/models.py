from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('staff', 'Staff'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    manager = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        limit_choices_to={'role': 'manager'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role} ({self.status})"
    
    @property
    def is_manager(self):
        return self.role == 'manager'
    @property
    def is_staff(self):
        return self.role == 'staff'
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    def approve(self, manager_profile):
        """Approve staff member"""
        if manager_profile.is_manager:
            self.status = 'approved'
            self.manager = manager_profile
            self.approved_at = timezone.now()
            self.save()
            return True
        return False

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "categories"
        ordering = ['name']

class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    quantity = models.IntegerField(default=0, db_index=True)
    minimum_stock = models.IntegerField(default=10)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock
    @property
    def is_zero(self):
        return self.quantity == 0
    

class StockMovement(models.Model):
    MOVEMENT_TYPES = (
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES, db_index=True)
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    def save(self, *args, **kwargs):
        # update product quantity based on movement type
        
        is_new = self.pk is None
        
        if is_new:
            
            if self.movement_type == 'in': # in
                self.product.quantity += self.quantity
            elif self.movement_type == 'out':
                
                if self.product.quantity >= self.quantity:
                    self.product.quantity -= self.quantity
                else:
                    raise ValueError(f"Insuffcient stock. Available: {self.product.quantity}")
            
            self.product.save()
            
        super().save(*args, **kwargs)
            
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.quantity} units of {self.product.name} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        
    class Meta:
        ordering = ['-created_at'] # New movement first