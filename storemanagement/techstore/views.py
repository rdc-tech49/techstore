from django.shortcuts import get_object_or_404, render, redirect
 
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.safestring import mark_safe
from .forms import CustomUserCreationForm, UpdateUserForm
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
# Create your views here.
from django.contrib.auth.models import User
from .models import ProductCategory, Product, SupplyOrder
from django.http import HttpResponseRedirect, JsonResponse
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
def customers_view(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'add_user':
            user_id = request.POST.get('user_id')
            username = request.POST.get('username').strip()
            email = request.POST.get('email')
            password = request.POST.get('password')

            if user_id:
                # Update existing user
                user = get_object_or_404(User, id=user_id)
                user.username = username
                user.email = email
                
                if password:
                    user.set_password(password)
                user.save()
                messages.success(request, "User updated successfully.")
                return HttpResponseRedirect(reverse('store_admin_customers') + '#list')
            else:
                # Create new user
                if User.objects.filter(username=username).exists():
                    messages.warning(request, "Username already exists.")
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password
                    )
                    messages.success(request, "User created successfully.")
                    return HttpResponseRedirect(reverse('store_admin_customers') + '#list')
            return redirect(reverse('store_admin_customers') + '#list')

    users = User.objects.filter(is_superuser=False).order_by('-id')
    edit_user_id = request.GET.get('edit_user')
    edit_user = User.objects.filter(id=edit_user_id).first() if edit_user_id else None

    return render(request, 'techstore/store_admin_customers.html', {
        'users': users,
        'edit_user': edit_user,
    })

def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect(reverse('store_admin_customers') + '#list')


@login_required
def products_view(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # Category Creation
        if form_type == 'add_category':
            category_name = request.POST.get('category_name', '').strip()
            edit_id = request.POST.get('edit_id')

            if category_name:
                if edit_id:
                    # Update existing category
                    category = get_object_or_404(ProductCategory, id=edit_id)
                    category.name = category_name
                    category.save()
                    messages.success(request, "Category updated successfully.")
                else:
                    # Add new category
                    if not ProductCategory.objects.filter(name__iexact=category_name).exists():
                        ProductCategory.objects.create(name=category_name)
                        messages.success(request, "Product category created successfully.")
                        return HttpResponseRedirect(reverse('store_admin_products') + '#create')
                    else:
                        messages.warning(request, "This category already exists.")
                        return HttpResponseRedirect(reverse('store_admin_products') + '#create')
            else:
                messages.error(request, "Category name cannot be empty.")
                return HttpResponseRedirect(reverse('store_admin_products') + '#create')

        # Product Add or Update
        elif form_type == 'add_product':
            product_id = request.POST.get('product_id')
            category_id = request.POST.get('category')
            model = request.POST.get('model')
            quantity = request.POST.get('quantity')
            purchased_date = request.POST.get('purchased_date')
            reference_details = request.POST.get('reference_details')
            description = request.POST.get('description')
            warranty_expiry_date = request.POST.get('warranty_expiry_date') or None
            vendor_details = request.POST.get('vendor_details')
            delivery_challan = request.FILES.get('delivery_challan')

            if not all([category_id, model, quantity, purchased_date, reference_details]):
                messages.error(request, "Please fill all the required fields.")
                return HttpResponseRedirect(reverse('store_admin_products') + '#add')

            category = get_object_or_404(ProductCategory, id=category_id)

            if product_id:
                # Update existing product
                product = get_object_or_404(Product, id=product_id)
                product.category = category
                product.model = model
                product.quantity = quantity
                product.purchased_date = purchased_date
                product.reference_details = reference_details
                product.description = description
                product.warranty_expiry_date = warranty_expiry_date
                product.vendor_details = vendor_details
                if delivery_challan:
                    product.delivery_challan = delivery_challan
                product.save()
                messages.success(request, "Product updated successfully.")
            else:
                # Add new product
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
            return HttpResponseRedirect(reverse('store_admin_products') + '#received')

    # GET request
    categories = ProductCategory.objects.all().order_by('id')
    products = Product.objects.all().order_by('-id')

    product_id_to_edit = request.GET.get('edit')
    edit_product = Product.objects.filter(id=product_id_to_edit).first() if product_id_to_edit else None

    context = {
        'categories': categories,
        'products': products,
        'edit_product': edit_product,
    }
    return render(request, 'techstore/store_admin_products.html', context)


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


def orders_view(request):
    categories = ProductCategory.objects.all()
    users = User.objects.all()
    products = Product.objects.select_related('category').all()
    supply_orders = SupplyOrder.objects.select_related('category', 'model', 'supplied_to').order_by('-supplied_date')


    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'create_order':
            category_id = request.POST.get('category')
            model_id = request.POST.get('model')
            quantity = request.POST.get('quantity')
            supplied_date = request.POST.get('supplied_date')
            supplied_to_id = request.POST.get('supplied_to')
            received_person_name = request.POST.get('received_person_name')
            iv_number = request.POST.get('iv_number')

            if not all([category_id, model_id, quantity, supplied_date, supplied_to_id, received_person_name, iv_number]):
                messages.error(request, "Please fill all required fields.")
                return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

            model = get_object_or_404(Product, id=model_id)

            if int(quantity) > model.quantity:
                messages.error(request, "Supplied quantity exceeds available stock.")
                return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

            SupplyOrder.objects.create(
                category_id=category_id,
                model_id=model_id,
                quantity_supplied=quantity,
                supplied_date=supplied_date,
                supplied_to_id=supplied_to_id,
                received_person_name=received_person_name,
                iv_number=iv_number
            )

            model.quantity -= int(quantity)
            model.save()

            messages.success(request, "Supply order created successfully.")
            return HttpResponseRedirect(reverse('store_admin_orders') + '#create')
    context = {
        'categories': categories,
        'users': users,
        'products': products,
        'supply_orders': supply_orders,
    }
    return render(request, 'techstore/store_admin_supplyorders.html', context)


def get_models_by_category(request, category_id):
    models = Product.objects.filter(category_id=category_id).values('id', 'model', 'quantity')
    return JsonResponse(list(models), safe=False)