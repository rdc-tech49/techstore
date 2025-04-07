from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.safestring import mark_safe
from .forms import CustomUserCreationForm, UpdateUserForm
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
# Create your views here.

from .models import ProductCategory, Product
from django.http import HttpResponseRedirect
from django.core.files.storage import FileSystemStorage


def home(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_superuser:
                return redirect('store_admin')  # URL name for admin dashboard
            else:
                return redirect('store_user')   # URL name for regular user dashboard
        else:
            messages.error(request, mark_safe("⚠️ Invalid Username or Password.<br>Try Again..."))
            return redirect('home')
    else:
        return render(request, "techstore/home.html", {})
    
@login_required
def store_admin_dashboard(request):
    return render(request, 'techstore/storeadmin-page.html')

@login_required
def store_user_dashboard(request):
    return render(request, 'techstore/storeuser-page.html') 

def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. You can now log in.")
            return redirect('home')  # Redirect to login page after successful registration
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'techstore/signup.html', {'form': form})

def store_admin(request):
    return render(request, "techstore/storeadmin-page.html", {})

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'techstore/password_change_form.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed successfully. Login again.")
        return super().form_valid(form)


@login_required
def update_user(request):
    if request.method == "POST":
        form = UpdateUserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            logout(request)  # Log the user out after updating
            messages.success(request, "Your profile has been updated successfully! Login again")
            return redirect('home')  # Redirect to a profile page or any other page.
    else:
        form = UpdateUserForm(instance=request.user)
    return render(request, 'techstore/update_user.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')  # Replace 'login' with the name or path to your login page

@login_required
def home_view(request):
    return render(request, 'techstore/store_admin_home.html')

@login_required
def dashboard_view(request):
    return render(request, 'techstore/store_admin_dashboard.html')

@login_required
def products_view(request):
    # Handle category creation
    if request.method == 'POST' and request.POST.get('form_type') == 'create_category':
        category_name = request.POST.get('category_name', '').strip()
        if category_name:
            if not ProductCategory.objects.filter(name__iexact=category_name).exists():
                ProductCategory.objects.create(name=category_name)
                messages.success(request, "Product category created successfully.")
            else:
                messages.warning(request, "This category already exists.")
        else:
            messages.error(request, "Category name cannot be empty.")
        return HttpResponseRedirect(reverse('store_admin_products') + '#create')

    # Handle product addition
    elif request.method == 'POST' and request.POST.get('form_type') == 'add_product':
        category_id = request.POST.get('category')
        model = request.POST.get('model', '').strip()
        quantity = request.POST.get('quantity')
        purchased_date = request.POST.get('purchased_date')
        reference_details = request.POST.get('reference_details', '').strip()
        description = request.POST.get('description', '')
        warranty_expiry_date = request.POST.get('warranty_expiry_date') or None
        vendor_details = request.POST.get('vendor_details', '')
        delivery_challan = request.FILES.get('delivery_challan')

        if category_id and model and quantity and purchased_date and reference_details:
            category = ProductCategory.objects.get(id=category_id)
            Product.objects.create(
                category=category,
                model=model,
                quantity=quantity,
                purchased_date=purchased_date,
                reference_details=reference_details,
                description=description,
                warranty_expiry_date=warranty_expiry_date,
                vendor_details=vendor_details,
                delivery_challan=delivery_challan
            )
            messages.success(request, "Product added successfully.")
        else:
            messages.error(request, "Please fill all the required fields.")
        return HttpResponseRedirect(reverse('store_admin_products') + '#add')

    categories = ProductCategory.objects.all().order_by('id')
    products = Product.objects.select_related('category').all().order_by('-id')

    return render(request, 'techstore/store_admin_products.html', {
        'categories': categories,
        'products': products,
    })



def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect(reverse('store_admin_products') + '#received')


def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        category_id = request.POST.get('category')
        product.model = request.POST.get('model')
        product.quantity = request.POST.get('quantity')
        product.purchased_date = request.POST.get('purchased_date')
        product.reference_details = request.POST.get('reference_details')
        product.description = request.POST.get('description')
        product.warranty_expiry_date = request.POST.get('warranty_expiry_date') or None
        product.vendor_details = request.POST.get('vendor_details')
        if request.FILES.get('delivery_challan'):
            product.delivery_challan = request.FILES.get('delivery_challan')
        product.category_id = category_id
        product.save()

        messages.success(request, "Product updated successfully.")
        return redirect(reverse('store_admin_products') + '#received')

    categories = ProductCategory.objects.all()
    products = Product.objects.select_related('category').all()
    return render(request, 'techstore/store_admin_products.html', {
        'edit_product': product,
        'categories': categories,
        'products': products
    })
