from django.db import models

# Create your models here.
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin/owner'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('viewer', 'Viewer'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "categories"

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock
    

class StockMovement(models.Model):
    MOVEMENT_TYPES = (
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # update product quantity based on movement type
        if self.movement_type == 'in': # in
            self.product.quantity += self.quantity
            
        else: # out
            self.product.quantity -= self.quantity
            
        self.product.save()
        super().save(*args, **kwargs)
        
        def __str__(self):
            return f"{self.get_movement_type_display()} - {self.quantity} units of {self.product.name} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        
        class Meta:
            ordering = ['-created_at'] # New movement first