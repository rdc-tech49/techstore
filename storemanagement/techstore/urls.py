from django.urls import path

from . import views
from django.contrib.auth import views as auth_views
from .views import CustomPasswordChangeView, update_user


urlpatterns = [
    path("", views.home, name="home"),
    path('store-admin/', views.store_admin_dashboard, name='store_admin'),
    path('store-user/', views.store_user_dashboard, name='store_user'),



    path('signup/', views.signup, name='signup'),
    path('store_admin/', views.store_admin, name='store_admin'),

    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='techstore/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='techstore/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='techstore/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='techstore/password_reset_complete.html'), name='password_reset_complete'),
    path('password/change/', CustomPasswordChangeView.as_view(), name='password_change'),
    
    path('profile/update/', update_user, name='update_user'),
    path('logout/', views.logout_view, name='logout'),


    path('store-admin/loan-register/', views.store_admin_loanregister, name='store_admin_loanregister'),
    path('loan-product-to-user/', views.loan_product_to_user, name='loan_product_to_user'),
    path('get-models-by-category/<int:category_id>/', views.get_models_by_category, name='get_models_by_category'),
    path('get-available-loan-quantity/<int:model_id>/', views.get_available_loan_quantity, name='get_available_loan_quantity'),



    path('store-admin/dashboard/', views.dashboard_view, name='store_admin_dashboard'),
    path('store-admin/products/', views.products_view, name='store_admin_products'),
    path('store-admin/users/', views.customers_view, name='store_admin_customers'),
    path('store-admin/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),

    
    # add/edit product 
    path('store-admin/products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('store-admin/products/delete/<int:product_id>/', views.delete_product, name='delete_product'),

    path('store-admin/orders/', views.orders_view, name='store_admin_orders'),
    path('get-models-by-category/<int:category_id>/', views.get_models_by_category, name='get_models_by_category'),

    path('get-available-quantity/', views.get_available_quantity, name='get_available_quantity'),

    path('delete-supply-order/<int:order_id>/', views.delete_supply_order, name='delete_supply_order'),

    # filter for product supplied table 
    path('store-admin/orders/ajax-stock-summary/', views.ajax_stock_summary, name='ajax_stock_summary'),

    # for filter and export in dashboard first table 
    path('dashboard/product-status/filter/', views.get_filtered_product_status, name='product_status_filter'),
    path('dashboard/product-status/export/', views.export_product_status_csv, name='product_status_export'),

    # dashboard second table 
    path('dashboard/product-status/summary-category/', views.product_status_summary_by_category, name='product_status_summary_category'),


    # First chart - stacked bar chart for received vs supplied
    path('dashboard/chart-data/category/', views.category_chart_data, name='category_chart_data'),
    # second chart - stacked bar chart for model vise received vs supplied
    path('dashboard/model-chart-data/', views.model_chart_data, name='model_chart_data'),
    
    # third chart - 
    path('dashboard/user-category-supply-chart/', views.user_category_supply_chart, name='user_category_supply_chart'),
    # fourth chart 
    path('dashboard/model-supply-by-user/', views.model_supply_by_user, name='model_supply_by_user'),



]