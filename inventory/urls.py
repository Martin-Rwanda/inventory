from django.urls import path
from . import views


urlpatterns = [
    path('register/', views.register_uer, name='register'),
    path('', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('product/<int:pk>/delete/', views.delete_product, name='delete_product'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add', views.add_category, name='add_category'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),
    path('stock/add/<int:product_id>', views.add_stock, name='add_stock'),
    path('stock/remove/<int:product_id>', views.remove_stock, name='remove_stock'),
    path('movements/',views.all_movements, name='all_movements'),
    path('manager', views.admin_page, name='admin_page'),
    path('manager/update/<int:staff_id>/', views.update_staff_status, name='update_staff_status'),
    
    #export
    path('export/products/', views.export_products_csv, name='export_products_csv'),
    path('export/options', views.export_options, name='export_options'),
    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
    path('export/movements/',views.export_movements_csv, name='export_movements_csv'),
    
    
    #apis
    path('api/category-stats/', views.category_stats, name='category_stats'),
    path('api/stock-status-stats/', views.stock_status_stats, name='stock_status_stats'),
    path('api/stock-timeline-stats/', views.stock_timeline_stats, name='stock_timeline_stats'), 
]
