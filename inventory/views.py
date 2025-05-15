from django.shortcuts import get_object_or_404, render, redirect

# Create your views here.
from django.contrib.auth.models import User, Group
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Sum, F, Q
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import datetime, timedelta
import csv
import re
from .models import UserProfile, Product, Category, StockMovement
from pickle import FALSE

@never_cache
@csrf_protect
def register_uer(request):
    error_message = None
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1').strip()
        password2 = request.POST.get('password2').strip()
        email = request.POST.get('email')
        role = request.POST.get('role')
        
        #validation
        if not all([username, email, password1, password2, role]):
            error_message = "all fields are required"
        elif password1 != password2:
            error_message = "Password don't match"
        elif User.objects.filter(username=username).exists():
            error_message = "Username already exists"
        elif User.objects.filter(email=email).exists():
            error_message = "Email already exists"
        else:
            # email format validation
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                error_message = "please enter a valid address"
            else:
                #password validation
                try:
                    if len(password1)<5:
                        error_message = "Password must be at least 5 character long"
                    elif not any(c.isdigit() for c in password1):
                        error_message = "Password must contain at least one number"
                    elif not any(c.isalpha() for c in password1):
                        error_message = "Password must contain at least one letter"
                    else:
                        try:
                            user = User.objects.create_user(
                                username=username,
                                email=email,
                                password=password1
                            )
                            
                            #user profile
                            UserProfile.objects.create(user=user, role=role)
                            
                            #log the user
                            login(request, user)
                            
                            #redirect to dashboard
                            return redirect('dashboard')
                        except Exception as e:
                            error_message = f"Error creating account: {str(e)}"
                            
                except ValidationError as e:
                    error_message = ", ".join(e.messages)
                    
    role_choices = UserProfile.ROLE_CHOICES
    context = {
        'role_choices': role_choices,
        'error_message': error_message
    }
    
    return render(request, 'registration/register.html', context)


@never_cache
@csrf_protect
def login_user(request):
    error_message = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            error_message = "Please enter both username and password."
        else:
            #check username
            if not User.objects.filter(username=username).exists():
                error_message = "Username does not exist. Please check yur username or register"
            else:
                #authenticate
                user = authenticate(request, username=username, password=password)
                
                if user is not None:
                    login(request, user)
                    return redirect('dashboard')
                
                else:
                    # password fails
                    error_message = "Incorrect password. Please try again."
    
    #for Get request
    return render(request, 'registration/login.html', {'error_message': error_message})

@login_required
def logout_user(request):
    request.session.flush()
    logout(request)
    return redirect('login')

@never_cache
@login_required
def dashboard(request):
    if request.user.is_authenticated:
        low_stock_products = Product.objects.filter(quantity__lte=F('minimum_stock'))
        total_products = Product.objects.count()
        total_categories = Category.objects.count()
        recent_movements = StockMovement.objects.select_related('product', 'created_by').order_by('-created_at')[:10]
        total_movements = StockMovement.objects.count()
        
        # Get top products by movement count
        top_products = Product.objects.annotate(
            movement_count=Count('movements')
        ).select_related('category').order_by('-movement_count')[:5]
        
        context = {
            'low_stock_count': low_stock_products.count(),
            'total_products': total_products,
            'total_categories': total_categories,
            'recent_movements': recent_movements,
            'total_movements': total_movements,
            'top_products': top_products
        }
        return render(request, 'inventory/dashboard.html', context)
    return render(request, 'registration/login.html')



# def has_any_role(user, roles):
#     if not user.is_authenticated:
#         return False
#     try:
#         return user.userprofile.role in roles
#     except UserProfile.DoesNotExist:
#         return False

def has_any_role(user, roles):
    if not user.is_authenticated:
        return False

    # Try to get the profile safely
    profile = UserProfile.objects.filter(user=user).first()
    if not profile:
        return False

    return profile.role in roles


@never_cache
@login_required
def product_list(request):
    products = Product.objects.all().order_by('-id')
    return render(request, 'inventory/product_list.html', {'products': products})


@never_cache
@csrf_protect
def add_product(request):
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        quantity = int(request.POST.get('quantity'))
        minimum_stock = request.POST.get('minimum_stock')
        
        category = get_object_or_404(Category, pk=category_id)
        
        product = Product.objects.create(
            name=name,
            description=description,
            category=category,
            price=price,
            quantity=0,
            minimum_stock=minimum_stock
        )
        
        # initial stock movement
        if int(quantity)>0:
            StockMovement.objects.create(
                product=product,
                quantity=quantity,
                movement_type='in',
                note='initial stock',
                created_by=request.user
            )
        messages.success(request, f'Product "{product.name}" has been created successfully.')
        return redirect('product_detail', pk=product.pk)
    categories = Category.objects.all()
    return render(request, 'inventory/product_form.html', {'categories': categories})

@never_cache
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    movements = product.movements.all().order_by('-created_at')[:20]
    context = {
        'product': product,
        'movements': movements,
    }
    return render(request, 'inventory/product_detail.html', context)

@never_cache
@csrf_protect
@login_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.category = get_object_or_404(Category, pk=request.POST.get('category'))
        product.price = request.POST.get('price')
        product.minimum_stock = request.POST.get('minimum_stock')
        product.save()
        
        return redirect('product_detail', pk=product.pk)
    categories = Category.objects.all()
    return render(request, 'inventory/product_form.html', {'product': product, 'categories': categories})

@never_cache
@csrf_protect
@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})

@never_cache
@login_required
def category_list(request):
    categories = Category.objects.all().order_by('-id')
    return render(request, 'inventory/category_list.html', {'categories': categories})

@never_cache
@csrf_protect
@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        Category.objects.create(
            name=name,
            description=description
        )
        return redirect('category_list')
    return render(request, 'inventory/category_form.html')

@login_required
def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    products = category.products.all()
    
    context = {
        'category': category,
        'products': products,
        'product_count': products.count()
    }
    return render(request, 'inventory/category_detail.html', context)

@never_cache
@csrf_protect
@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    #check if  category has products
    if category.products.exists():
        messages.error(request, f"Cannot delete category '{category.name}' because it contains products. please move or delete thes products first.")
        return redirect('category_list')
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f"Category '{category_name}' was deleted successfully")
        
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})

@login_required
def all_movements(request):
    """View to display all stock movements with filtering options"""
    movements = StockMovement.objects.select_related('product', 'created_by', 'product__category').order_by('-created_at')
    
    #filter options
    product_filter = request.GET.get('product')
    category_filter = request.GET.get('category')
    type_filter = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    #apply filters
    if product_filter:
        movements = movements.filter(product_id=product_filter)
    if category_filter:
        movements = movements.filter(product__category_id=category_filter)
    if type_filter in ['in', 'out']:
        movements = movements.filter(movement_type=type_filter)
    if date_from:
        try:
            date_from = datetime.striptime(date_from, '%Y-%m-%d').date()
            movements = movements.filter(created_at__date__gte=date_from)
        except ValueError:
            pass
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            movements = movements.filter(created_at__date__lte=date_to)
        except ValueError:
            pass
    
    #all products and categories 
    products = Product.objects.all().order_by('name')
    categories = Category.objects.all().order_by('name')
    
    paginator = Paginator(movements, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'movements': page_obj,
        'products': products,
        'categories': categories,
        'product_filter': product_filter,
        'category_filter': category_filter,
        'type_filter': type_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'inventory/all_movements.html', context)

@login_required
def export_movements_csv(request):
    """Generate CSV of filtered movements"""
    movements = StockMovement.objects.select_related('product', 'created_by', 'product__category').order_by('-created_at')
    
    # Apply the same filters as in the all_movements view
    product_filter = request.GET.get('product')
    category_filter = request.GET.get('category')
    type_filter = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if product_filter:
        movements = movements.filter(product_id=product_filter)
    
    if category_filter:
        movements = movements.filter(product__category_id=category_filter)
    
    if type_filter in ['in', 'out']:
        movements = movements.filter(movement_type=type_filter)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            movements = movements.filter(created_at__date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            movements = movements.filter(created_at__date__lte=date_to)
        except ValueError:
            pass
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"stock_movements_{timestamp}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(['Date & Time', 'Product', 'Category', 'Movement Type', 'Quantity', 'User', 'Note'])
    
    for movement in movements:
        writer.writerow([
            movement.created_at.strftime('%Y-%m-%d %H:%M'),
            movement.product.name,
            movement.product.category.name,
            'Stock In' if movement.movement_type == 'in' else 'Stock Out',
            movement.quantity,
            movement.created_by.username,
            movement.note or ""
        ])
    
    return response


@never_cache
@csrf_protect
@login_required
def add_stock(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        note = request.POST.get('note', '')
        
        if quantity > 0:
            StockMovement.objects.create(
                product=product,
                quantity=quantity,
                movement_type='in',
                note=note,
                created_by=request.user
            )
        messages.success(request, f"Added {quantity} units to {product.name}")
        return redirect('product_detail', pk=product_id)
    
    return render(request, 'inventory/stock_form.html', {'product': product, 'movement_type': 'in'})

@never_cache
@csrf_protect
@login_required
def remove_stock(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        note = request.POST.get('note', '')
        
        if quantity > 0:
            StockMovement.objects.create(
                product=product,
                quantity=quantity,
                movement_type='out',
                note=note,
                created_by=request.user
            )
        return redirect('product_detail', pk=product_id)
    
    return render(request, 'inventory/stock_form.html', {'product': product, 'movement_type': 'ut'})

@login_required
def export_products_csv(request):
    """Generate CSV based on selected options"""
    include_history = request.GET.get('include_history') == 'on'
    selected_products = request.GET.getlist('products')
    
    # If no products selected, use all
    if not selected_products:
        products = Product.objects.all()
    else:
        products = Product.objects.filter(id__in=selected_products)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"inventory_report_{timestamp}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    if include_history:
        # Export with full history
        writer.writerow(['Product', 'Category', 'Current Stock', 'Minimum Stock', 
                         'Movement Date', 'Movement Type', 'Quantity', 'User', 'Note'])
        
        for product in products:
            movements = StockMovement.objects.filter(product=product).order_by('created_at')
            
            if movements.exists():
                for movement in movements:
                    writer.writerow([
                        product.name,
                        product.category.name,
                        product.quantity,
                        product.minimum_stock,
                        movement.created_at.strftime('%Y-%m-%d %H:%M'),
                        'Stock In' if movement.movement_type == 'in' else 'Stock Out',
                        movement.quantity,
                        movement.created_by.username,
                        movement.note or ""
                    ])
            else:
                # Include product even if no movements
                writer.writerow([
                    product.name,
                    product.category.name,
                    product.quantity,
                    product.minimum_stock,
                    "", "", "", "", ""
                ])
    else:
        # Simple product list without history
        writer.writerow(['Product', 'Category', 'Current Stock', 'Minimum Stock', 'Low Stock'])
        
        for product in products:
            writer.writerow([
                product.name,
                product.category.name,
                product.quantity,
                product.minimum_stock,
                'Yes' if product.is_low_stock else 'No'
            ])
    
    return response

@login_required
def export_options(request):
    """View to display export options before generating the CSV"""
    products = Product.objects.all().order_by('name')
    
    context = {
        'products': products,
    }
    return render(request, 'inventory/export_options.html', context)
        
@never_cache
@login_required
def low_stock_report(request):
    all_products = Product.objects.all()
    
    show_all = request.GET.get('show_all', 'false') == 'true'
    
    product_name = request.GET.get('product_name', '')
    category_filter = request.GET.get('category', '')
    sort_order = request.GET.get('sort', 'name')
    stock_filter = request.GET.get('stock', 'all')
    
    if show_all:
        products_to_display = all_products
    else:
        products_to_display = all_products.filter(quantity__lte=F('minimum_stock'))
    
    if product_name:
        products_to_display = products_to_display.filter(name__icontains=product_name)
    
        products_to_display = products_to_display.filter(category_id=category_filter)
    
    if stock_filter == 'zero':
        products_to_display = products_to_display.filter(quantity=0)
    elif stock_filter == 'low':
        products_to_display = products_to_display.filter(quantity__gt=0, quantity__lte=F('minimum_stock'))
    elif stock_filter == 'normal':
        products_to_display = products_to_display.filter(quantity__gt=F('minimum_stock'))
    
    if sort_order == 'quantity':
        products_to_display = products_to_display.order_by('quantity')
    elif sort_order == 'percent':
        
        if hasattr(products_to_display, 'order_by'):
            products_list = list(products_to_display)
        else:
            products_list = products_to_display
            
        products_to_display = sorted(
            products_list,
            key=lambda p: (p.quantity / p.minimum_stock if p.minimum_stock > 0 else float('inf'))
        )
    else:  
        if hasattr(products_to_display, 'order_by'):
            products_to_display = products_to_display.order_by('name')
        else:
            products_to_display = sorted(products_to_display, key=lambda p: p.name)
    
    categories = Category.objects.all()
    
    product_movements = {}
    
    for product in products_to_display:
        movements = StockMovement.objects.filter(product=product).order_by('-created_at')[:10]
        product_movements[product.id] = movements
    
    context = {
        'products': products_to_display,
        'product_movements': product_movements,
        'categories': categories,
        'title': 'All Products' if show_all else 'Low Stock Report',
        'count': len(products_to_display),
        'show_all': show_all,
        'all_products_count': all_products.count(),
        'low_stock_count': all_products.filter(quantity__lte=F('minimum_stock')).count()
    }
    return render(request, 'inventory/low_stock_report.html', context)




#apis
@never_cache
@login_required
def category_stats(request):
    from django.db.models import Sum, Count
    from django.http import JsonResponse
    
    # Get total products by category
    categories = Category.objects.annotate(product_count=Count('products'))
    
    # Prepare data for chart
    labels = [category.name for category in categories]
    values = [category.product_count for category in categories]
    
    return JsonResponse({
        'labels': labels,
        'values': values
    })
    
@never_cache
@login_required
def stock_status_stats(request):
    """API view that returns stock status statistics for charts"""
    # Count products by stock status
    total_products = Product.objects.count()
    out_of_stock = Product.objects.filter(quantity=0).count()
    low_stock = Product.objects.filter(quantity__gt=0, quantity__lte=F('minimum_stock')).count()
    normal_stock = total_products - out_of_stock - low_stock
    
    return JsonResponse({
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'normal_stock': normal_stock,
        'total': total_products
    })
 
@never_cache   
@login_required
def stock_timeline_stats(request):
    """API view that returns stock movement timeline for charts"""
    # Get dates for the last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)
    
    # Get all dates in range
    dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    
    # Get top 5 products by movement count
    top_products = Product.objects.annotate(
        movement_count=Count('movements')
    ).order_by('-movement_count')[:5]
    
    # Prepare datasets for each product
    datasets = []
    colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b']
    
    for i, product in enumerate(top_products):
        # Get all movements for this product in date range
        movements = StockMovement.objects.filter(
            product=product,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).order_by('created_at')
        
        # Calculate running total of stock for each day
        stock_by_date = {}
        current_stock = product.quantity
        
        # Work backwards from current stock
        for movement in reversed(list(movements)):
            if movement.movement_type == 'in':
                current_stock -= movement.quantity
            else:  # out
                current_stock += movement.quantity
            
            movement_date = movement.created_at.date().strftime('%Y-%m-%d')
            stock_by_date[movement_date] = current_stock
        
        # Fill in all dates
        data = []
        for date in dates:
            # Find the most recent known stock level for this date
            if date in stock_by_date:
                data.append(stock_by_date[date])
            else:
                # Find closest previous date
                closest_date = None
                for d in reversed(dates[:dates.index(date)]):
                    if d in stock_by_date:
                        closest_date = d
                        break
                
                if closest_date:
                    data.append(stock_by_date[closest_date])
                else:
                    # No previous data, use earliest known value or 0
                    earliest_date = min(stock_by_date.keys()) if stock_by_date else None
                    data.append(stock_by_date.get(earliest_date, 0))
        
        datasets.append({
            'label': product.name,
            'data': data,
            'borderColor': colors[i],
            'backgroundColor': colors[i] + '20',  # Add transparency
            'fill': False,
            'tension': 0.1
        })
    
    return JsonResponse({
        'dates': dates,
        'datasets': datasets
    })
    
@never_cache
@login_required
def stock_projection_stats(request):
    """API view that returns projected stock changes for the next 14 days"""
    # Get all products with at least one movement
    products_with_movements = Product.objects.annotate(
        movement_count=Count('movements')
    ).filter(movement_count__gt=0).order_by('-movement_count')[:5]
    
    # Generate dates for the next 14 days
    start_date = timezone.now().date()
    dates = [(start_date + timedelta(days=i)).strftime('%b %d') for i in range(14)]
    
    # Prepare datasets for each product
    datasets = []
    colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b']
    
    for i, product in enumerate(products_with_movements):
        # Calculate average daily consumption rate
        out_movements = StockMovement.objects.filter(
            product=product,
            movement_type='out'
        )
        
        if out_movements.exists():
            # Get the total quantity removed and the date range
            total_out = out_movements.aggregate(Sum('quantity'))['quantity__sum'] or 0
            
            # If we have out movements, estimate daily consumption
            if total_out > 0:
                # Use 1 unit per day as minimum rate if we have at least one movement
                daily_consumption = max(1, total_out // 30)  # Assume last 30 days
            else:
                daily_consumption = 0
        else:
            # No out movements recorded, assume minimal usage
            daily_consumption = 0
        
        # Project stock levels for next 14 days
        current_stock = product.quantity
        projected_stocks = []
        
        for _ in range(14):
            # Decrease by daily consumption, but not below 0
            current_stock = max(0, current_stock - daily_consumption)
            projected_stocks.append(current_stock)
        
        datasets.append({
            'label': product.name,
            'data': projected_stocks,
            'borderColor': colors[i],
            'backgroundColor': 'transparent',
            'borderDash': [5, 5] if daily_consumption > 0 else [],  # Dashed line for projections
            'pointRadius': 3,
            'tension': 0.1
        })
        
        # Add a horizontal line for minimum stock level
        datasets.append({
            'label': f"{product.name} Min Level",
            'data': [product.minimum_stock] * 14,
            'borderColor': colors[i] + '80',  # Semi-transparent
            'borderDash': [2, 2],
            'pointRadius': 0,
            'fill': FALSE,
            'tension': 0
        })
    
    return JsonResponse({
        'dates': dates,
        'datasets': datasets
    })
    
@never_cache
@login_required
def product_activity_stats(request):
    """API view that returns product activity statistics for charts"""
    # Get top 10 products by movement count
    top_products = Product.objects.annotate(
        movement_count=Count('movements'),
        in_count=Count('movements', filter=Q(movements__movement_type='in')),
        out_count=Count('movements', filter=Q(movements__movement_type='out'))
    ).order_by('-movement_count')[:10]
    
    product_names = [product.name for product in top_products]
    in_counts = [product.in_count for product in top_products]
    out_counts = [product.out_count for product in top_products]
    
    return JsonResponse({
        'product_names': product_names,
        'in_counts': in_counts,
        'out_counts': out_counts
    })
    
@never_cache
@login_required
def all_movements(request):
    """View to display all stock movements with filtering options"""
    movements = StockMovement.objects.select_related('product', 'created_by', 'product__category').order_by('-created_at')
    
    # Filtering options
    product_filter = request.GET.get('product')
    category_filter = request.GET.get('category')
    type_filter = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Apply filters
    if product_filter:
        movements = movements.filter(product_id=product_filter)
    
    if category_filter:
        movements = movements.filter(product__category_id=category_filter)
    
    if type_filter in ['in', 'out']:
        movements = movements.filter(movement_type=type_filter)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            movements = movements.filter(created_at__date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            movements = movements.filter(created_at__date__lte=date_to)
        except ValueError:
            pass
    
    # Get all products and categories for filter dropdowns
    products = Product.objects.all().order_by('name')
    categories = Category.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(movements, 25)  # 25 movements per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'movements': page_obj,
        'products': products,
        'categories': categories,
        'product_filter': product_filter,
        'category_filter': category_filter,
        'type_filter': type_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'inventory/all_movements.html', context)