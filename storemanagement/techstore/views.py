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
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.core.files.storage import FileSystemStorage
import csv
from django.db.models import Q, Sum
from django.views.decorators.http import require_POST
from datetime import datetime

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
            rv_details = request.POST.get('rv_details')
            description = request.POST.get('description')
            warranty_expiry_date = request.POST.get('warranty_expiry_date') or None
            vendor_details = request.POST.get('vendor_details')
            delivery_challan = request.FILES.get('delivery_challan')

            if not all([category_id, model, quantity, purchased_date, reference_details,rv_details]):
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
                product.rv_details = rv_details
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
                    rv_details=rv_details,
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


# def orders_view(request):
#     categories = ProductCategory.objects.all()
#     users = User.objects.all()
#     products = Product.objects.select_related('category').all()
#     supply_orders = SupplyOrder.objects.select_related('category', 'model', 'supplied_to').order_by('-supplied_date')

#     # Available quantity calculation
#     supplied_totals = SupplyOrder.objects.values('model_id').annotate(total_supplied=Sum('quantity_supplied'))
#     supplied_dict = {item['model_id']: item['total_supplied'] for item in supplied_totals}

#     available_quantities = {
#         product.id: max(product.quantity - supplied_dict.get(product.id, 0), 0)
#         for product in products
#     }

#     # Filters for 'Products to be Supplied' table
#     product_search = request.GET.get('product_search', '').strip()
#     product_start_date = request.GET.get('product_start_date')
#     product_end_date = request.GET.get('product_end_date')

#     products_to_supply = []
#     for product in products:
#         total_supplied = supplied_dict.get(product.id, 0)
#         remaining_quantity = max(product.quantity - total_supplied, 0)
#         if remaining_quantity > 0:
#             # Search filter
#             if product_search:
#                 if (product.category.name.lower().find(product_search.lower()) == -1 and
#                     product.model.lower().find(product_search.lower()) == -1):
#                     continue
#             # Date range filter
#             if product_start_date:
#                 try:
#                     start = datetime.strptime(product_start_date, '%Y-%m-%d').date()
#                     if product.purchased_date < start:
#                         continue
#                 except ValueError:
#                     pass
#             if product_end_date:
#                 try:
#                     end = datetime.strptime(product_end_date, '%Y-%m-%d').date()
#                     if product.purchased_date > end:
#                         continue
#                 except ValueError:
#                     pass

#             products_to_supply.append({
#                 'category_name': product.category.name,
#                 'model': product.model,
#                 'purchased_date': product.purchased_date,
#                 'remaining_quantity': remaining_quantity,
#             })



#     # Filters
#     search = request.GET.get('search', '').strip()
#     start_date = request.GET.get('start_date')
#     end_date = request.GET.get('end_date')
#     export = request.GET.get('export')

#     if search:
#         supply_orders = supply_orders.filter(
#             Q(category__name__icontains=search) |
#             Q(model__model__icontains=search) |
#             Q(supplied_to__username__icontains=search)
#         )
#     if start_date:
#         supply_orders = supply_orders.filter(supplied_date__gte=start_date)
#     if end_date:
#         supply_orders = supply_orders.filter(supplied_date__lte=end_date)

#     supply_orders = supply_orders.order_by('-supplied_date')

#     # Export CSV
#     export = request.GET.get('export')

#     if export == 'csv':
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="stock_summary.csv"'
#         writer = csv.writer(response)
#         writer.writerow(['Category', 'Model', 'Quantity Supplied', 'Supplied Date', 'Supplied To', 'Received Person', 'IV Number'])

#         for order in supply_orders:
#             writer.writerow([
#                 order.category.name,
#                 order.model.model,
#                 order.quantity_supplied,
#                 order.supplied_date,
#                 order.supplied_to.username,
#                 order.received_person_name,
#                 order.iv_number
#             ])
#         return response


#     # Inline edit logic
#     edit_order = None
#     max_quantity_range = []
#     edit_id = request.GET.get('edit')
#     if edit_id:
#         edit_order = get_object_or_404(SupplyOrder, id=edit_id)
#         model = edit_order.model
#         total_supplied = supplied_dict.get(model.id, 0)
#         # Exclude the current order's own quantity
#         total_supplied_excl_self = total_supplied - edit_order.quantity_supplied
#         max_available = model.quantity - total_supplied_excl_self
#         max_quantity_range = list(range(1, max_available + 1))

        

#     # Handle POST (Create or Update)
#     if request.method == 'POST':
#         form_type = request.POST.get('form_type')
#         category_id = request.POST.get('category')
#         model_id = request.POST.get('model')
#         quantity = request.POST.get('quantity')
#         supplied_date = request.POST.get('supplied_date')
#         supplied_to_id = request.POST.get('supplied_to')
#         received_person_name = request.POST.get('received_person_name')
#         iv_number = request.POST.get('iv_number')

#         if not all([category_id, model_id, quantity, supplied_date, supplied_to_id, received_person_name, iv_number]):
#             messages.error(request, "Please fill all required fields.")
#             return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

#         model = get_object_or_404(Product, id=model_id)
#         total_supplied = supplied_dict.get(model.id, 0)
#         max_available = model.quantity - total_supplied

#         if form_type == 'create_order':
#             if int(quantity) > max_available:
#                 messages.error(request, "Supplied quantity exceeds available stock.")
#                 return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

#             SupplyOrder.objects.create(
#                 category_id=category_id,
#                 model_id=model_id,
#                 quantity_supplied=quantity,
#                 supplied_date=supplied_date,
#                 supplied_to_id=supplied_to_id,
#                 received_person_name=received_person_name,
#                 iv_number=iv_number
#             )
#             messages.success(request, "Supply order created successfully.")
#             return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

#         elif form_type == 'edit_order':
#             order_id = request.POST.get('order_id')
#             order = get_object_or_404(SupplyOrder, id=order_id)
            
#             category_id = request.POST.get('category')
#             model_id = request.POST.get('model')
#             quantity = int(request.POST.get('quantity'))
#             supplied_date = request.POST.get('supplied_date')
#             supplied_to_id = request.POST.get('supplied_to')
#             received_person_name = request.POST.get('received_person_name')
#             iv_number = request.POST.get('iv_number')

#             if not all([category_id, model_id, quantity, supplied_date, supplied_to_id, received_person_name, iv_number]):
#                 messages.error(request, "Please fill all required fields.")
#                 return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

#             model = get_object_or_404(Product, id=model_id)

#             # Compute updated available quantity (excluding the current order)
#             total_supplied = SupplyOrder.objects.filter(model_id=model.id).exclude(id=order.id).aggregate(total=Sum('quantity_supplied'))['total'] or 0
#             available_quantity = model.quantity - total_supplied

#             if quantity > available_quantity:
#                 messages.error(request, "Supplied quantity exceeds available stock.")
#                 return HttpResponseRedirect(reverse('store_admin_orders') + f'?edit={order.id}#create')

#             # Update the order

#             order.category_id = category_id
#             order.model_id = model_id
#             order.quantity_supplied = quantity
#             order.supplied_date = supplied_date
#             order.supplied_to_id = supplied_to_id
#             order.received_person_name = received_person_name
#             order.iv_number = iv_number
#             order.save()

#             messages.success(request, "Supply order updated successfully.")
#             return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

#     # Delete logic
#     if request.GET.get('delete'):
#         delete_id = request.GET.get('delete')
#         order = get_object_or_404(SupplyOrder, id=delete_id)
#         order.delete()
#         messages.success(request, "Supply order deleted successfully.")
#         return HttpResponseRedirect(reverse('store_admin_orders') + '#stock')


#     if request.GET.get('product_export') == 'csv':
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="products_to_be_supplied.csv"'
#         writer = csv.writer(response)
#         writer.writerow(['Category', 'Model', 'Purchased Date', 'Quantity to be Supplied'])
#         for item in products_to_supply:
#             writer.writerow([
#                 item['category_name'],
#                 item['model'],
#                 item['purchased_date'],
#                 item['remaining_quantity'],
#             ])
#         return response

#     context = {
#         'categories': categories,
#         'users': users,
#         'products': products,
#         'supply_orders': supply_orders,
#         'available_quantities': available_quantities,
#         'edit_order': edit_order,
#         'max_quantity_range': max_quantity_range,
#         'products_to_supply': products_to_supply,  
#         'product_search': product_search,
#         'product_start_date': product_start_date,
#         'product_end_date': product_end_date,
#         'search': search,
#         'start_date': start_date,
#         'end_date': end_date,
#     }
#     return render(request, 'techstore/store_admin_supplyorders.html', context)

def orders_view(request):
    # Basic queries
    categories = ProductCategory.objects.all()
    users = User.objects.all()
    products = Product.objects.select_related('category').all()
    supply_orders = SupplyOrder.objects.select_related('category', 'model', 'supplied_to').order_by('-supplied_date')

    # Available quantity calculation for Products (for dynamic quantity dropdowns)
    supplied_totals = SupplyOrder.objects.values('model_id').annotate(total_supplied=Sum('quantity_supplied'))
    supplied_dict = {item['model_id']: item['total_supplied'] for item in supplied_totals}
    available_quantities = {product.id: max(product.quantity - supplied_dict.get(product.id, 0), 0)
                            for product in products}

    # ===== Filters for Products to be Supplied Table =====
    product_search = request.GET.get('product_search', '').strip()
    product_start_date = request.GET.get('product_start_date')
    product_end_date = request.GET.get('product_end_date')

    products_to_supply = []
    for product in products:
        total_supplied = supplied_dict.get(product.id, 0)
        remaining_quantity = max(product.quantity - total_supplied, 0)
        if remaining_quantity > 0:
            # Apply search filter if provided
            if product_search:
                if (product.category.name.lower().find(product_search.lower()) == -1 and
                    product.model.lower().find(product_search.lower()) == -1):
                    continue
            # Apply date range filter if provided
            if product_start_date:
                try:
                    start = datetime.strptime(product_start_date, '%Y-%m-%d').date()
                    if product.purchased_date < start:
                        continue
                except ValueError:
                    pass
            if product_end_date:
                try:
                    end = datetime.strptime(product_end_date, '%Y-%m-%d').date()
                    if product.purchased_date > end:
                        continue
                except ValueError:
                    pass

            products_to_supply.append({
                'category_name': product.category.name,
                'model': product.model,
                'purchased_date': product.purchased_date,
                'remaining_quantity': remaining_quantity,
            })

    # ===== Filters for Supply Orders (Stock Summary) Table =====
    search = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export = request.GET.get('export')  # For supply orders CSV export

    if search:
        supply_orders = supply_orders.filter(
            Q(category__name__icontains=search) |
            Q(model__model__icontains=search) |
            Q(supplied_to__username__icontains=search)
        )
    if start_date:
        supply_orders = supply_orders.filter(supplied_date__gte=start_date)
    if end_date:
        supply_orders = supply_orders.filter(supplied_date__lte=end_date)
    supply_orders = supply_orders.order_by('-supplied_date')

    # ===== Export Supply Orders to CSV =====
    if export == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_summary.csv"'
        writer = csv.writer(response)
        writer.writerow(['Category', 'Model', 'Quantity Supplied', 'Supplied Date', 'Supplied To', 'Received Person', 'IV Number'])
        for order in supply_orders:
            writer.writerow([
                order.category.name,
                order.model.model,
                order.quantity_supplied,
                order.supplied_date,
                order.supplied_to.username,
                order.received_person_name,
                order.iv_number
            ])
        return response

    # ===== Export Products to be Supplied to CSV =====
    if request.GET.get('product_export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products_to_be_supplied.csv"'
        writer = csv.writer(response)
        writer.writerow(['Category', 'Model', 'Purchased Date', 'Quantity to be Supplied'])
        for item in products_to_supply:
            writer.writerow([
                item['category_name'],
                item['model'],
                item['purchased_date'],
                item['remaining_quantity'],
            ])
        return response

    # ===== Inline Edit Logic for Supply Orders =====
    edit_order = None
    max_quantity_range = []
    edit_id = request.GET.get('edit')
    if edit_id:
        edit_order = get_object_or_404(SupplyOrder, id=edit_id)
        model_obj = edit_order.model
        # Calculate total supplied for this model
        total_supplied = supplied_dict.get(model_obj.id, 0)
        # Exclude the current order's quantity for an accurate available stock calculation
        total_supplied_excl_self = total_supplied - edit_order.quantity_supplied
        max_available = model_obj.quantity - total_supplied_excl_self
        max_quantity_range = list(range(1, max_available + edit_order.quantity_supplied + 1))

    # ===== Handle POST Requests (Creation / Update) =====
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        # Common fields for both create and update:
        category_id = request.POST.get('category')
        model_id = request.POST.get('model')
        quantity_str = request.POST.get('quantity')
        supplied_date = request.POST.get('supplied_date')
        supplied_to_id = request.POST.get('supplied_to')
        received_person_name = request.POST.get('received_person_name')
        iv_number = request.POST.get('iv_number')

        if not all([category_id, model_id, quantity_str, supplied_date, supplied_to_id, received_person_name, iv_number]):
            messages.error(request, "Please fill all required fields.")
            return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

        try:
            quantity = int(quantity_str)
        except ValueError:
            messages.error(request, "Invalid quantity value.")
            return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

        model_obj = get_object_or_404(Product, id=model_id)
        # Recalculate total supplied and available quantity for this product
        total_supplied = supplied_dict.get(model_obj.id, 0)
        max_available = model_obj.quantity - total_supplied

        if form_type == 'create_order':
            if quantity > max_available:
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
            messages.success(request, "Supply order created successfully.")
            return HttpResponseRedirect(reverse('store_admin_orders') + '#create')

        elif form_type == 'edit_order':
            order_id = request.POST.get('order_id')
            order = get_object_or_404(SupplyOrder, id=order_id)
            # Recalculate available quantity for update: exclude this order's current quantity
            total_supplied_excl = SupplyOrder.objects.filter(model_id=model_obj.id).exclude(id=order.id).aggregate(total=Sum('quantity_supplied'))['total'] or 0
            available_quantity = model_obj.quantity - total_supplied_excl

            if quantity > available_quantity:
                messages.error(request, "Supplied quantity exceeds available stock.")
                return HttpResponseRedirect(reverse('store_admin_orders') + f'?edit={order.id}#create')

            # Update the order fields
            order.category_id = category_id
            order.model_id = model_id
            order.quantity_supplied = quantity
            order.supplied_date = supplied_date
            order.supplied_to_id = supplied_to_id
            order.received_person_name = received_person_name
            order.iv_number = iv_number
            order.save()

            messages.success(request, "Supply order updated successfully.")
            return HttpResponseRedirect(reverse('store_admin_orders') + '#stock')

    # ===== Delete Logic =====
    if request.GET.get('delete'):
        delete_id = request.GET.get('delete')
        order = get_object_or_404(SupplyOrder, id=delete_id)
        order.delete()
        messages.success(request, "Supply order deleted successfully.")
        return HttpResponseRedirect(reverse('store_admin_orders') + '#stock')

    context = {
        'categories': categories,
        'users': users,
        'products': products,
        'supply_orders': supply_orders,
        'available_quantities': available_quantities,
        'edit_order': edit_order,
        'max_quantity_range': max_quantity_range,
        'products_to_supply': products_to_supply,
        'product_search': product_search,
        'product_start_date': product_start_date,
        'product_end_date': product_end_date,
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'techstore/store_admin_supplyorders.html', context)


def get_models_by_category(request, category_id):
    models = Product.objects.filter(category_id=category_id).values('id', 'model', 'quantity')
    return JsonResponse(list(models), safe=False)


def get_available_quantity(request):
    product_id = request.GET.get('product_id')
    try:
        product = Product.objects.get(id=product_id)
        total_supplied = SupplyOrder.objects.filter(model_id=product_id).aggregate(total=Sum('quantity_supplied'))['total'] or 0
        available_quantity = product.quantity - total_supplied
        return JsonResponse({'available_quantity': available_quantity})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@require_POST
def delete_supply_order(request, order_id):
    order = get_object_or_404(SupplyOrder, id=order_id)
    order.delete()
    messages.success(request, "Supply order deleted successfully.")
    return HttpResponseRedirect(reverse('store_admin_orders') + '#stock')

