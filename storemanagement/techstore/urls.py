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

    path('store-admin/home/', views.home_view, name='store_admin_home'),
    path('store-admin/dashboard/', views.dashboard_view, name='store_admin_dashboard'),
    path('store-admin/products/', views.products_view, name='store_admin_products'),
    
    # add/edit product 
    path('store-admin/products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('store-admin/products/delete/<int:product_id>/', views.delete_product, name='delete_product'),



]