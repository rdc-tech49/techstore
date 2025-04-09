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
from io import StringIO
from django.utils.dateformat import DateFormat
from django.utils.formats import date_format
from django.template.loader import render_to_string
from django.utils.html import escape  # For HTML safety
from collections import defaultdict

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
    # Get all products
    products = Product.objects.all().order_by('-id')

    # Get total quantity supplied per model
    supply_data = SupplyOrder.objects.values('model__model').annotate(
        total_supplied=Sum('quantity_supplied')
    )
    supplied_dict = {item['model__model']: item['total_supplied'] for item in supply_data}

    # Prepare product status list
    product_status = []
    for product in products:
        supplied_qty = supplied_dict.get(product.model, 0)
        stock_qty = product.quantity - supplied_qty

        product_status.append({
            'id': product.id,
            'category': product.category.name,
            'model': product.model,
            'purchased_date': product.purchased_date,
            'quantity_received': product.quantity,
            'quantity_supplied': supplied_qty,
            'quantity_in_stock': stock_qty,
        })

    context = {
        'product_status': product_status,
    }

    return render(request, 'techstore/store_admin_dashboard.html', context)

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

    # Check if products are already used in supply orders
    from .models import SupplyOrder  # Make sure it's imported
    supplied_product_ids = set(
        SupplyOrder.objects.values_list('model_id', flat=True)
    )

    products_with_status = []
    for product in products:
        has_been_supplied = product.id in supplied_product_ids
        products_with_status.append({
            'id': product.id,
            'category_name': product.category.name,
            'model': product.model,
            'quantity': product.quantity,
            'purchased_date': product.purchased_date,
            'has_been_supplied': has_been_supplied,
        })


    context = {
        'categories': categories,
        'products': products,
        'edit_product': edit_product,
        'products_with_status': products_with_status,
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

    
    product_search = request.GET.get('product_search', '').strip()
    product_start_date = request.GET.get('product_start_date')
    product_end_date = request.GET.get('product_end_date')
    product_export = request.GET.get('product_export')

    products_to_supply = []
    for product in products:
        total_supplied = supplied_dict.get(product.id, 0)
        remaining_quantity = max(product.quantity - total_supplied, 0)
        if remaining_quantity > 0:
            # Search filter
            if product_search:
                if (product.category.name.lower().find(product_search.lower()) == -1 and
                    product.model.lower().find(product_search.lower()) == -1):
                    continue
            # Date filters
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
                'purchased_date': product.purchased_date.strftime('%Y-%m-%d'),
                'remaining_quantity': remaining_quantity,
            })

    # CSV Export
    if product_export == 'csv':
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

    # AJAX CSV export for "Products to be Supplied"
    if product_export == 'csv':
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

    # AJAX live filtering response (return HTML table rows directly)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.GET.get('product_live') == 'true':
        table_html = ""
        if products_to_supply:
            for i, item in enumerate(products_to_supply, 1):
                table_html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{escape(item['category_name'])}</td>
                        <td>{escape(item['model'])}</td>
                        <td>{escape(item['purchased_date'])}</td>
                        <td>{item['remaining_quantity']}</td>
                    </tr>
                """
        else:
            table_html = """
                <tr>
                    <td colspan="5">All products are fully supplied.</td>
                </tr>
            """
        return HttpResponse(table_html)
    

    # ===== Filters for Supply Orders (Stock Summary) Table =====
    search = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

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

     # Handle AJAX request for filtering
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = []
        for order in supply_orders:
            data.append({
                'category': order.category.name,
                'model': order.model.model,
                'quantity_supplied': order.quantity_supplied,
                'supplied_date': date_format(order.supplied_date, format='F j, Y'),
                'supplied_to': order.supplied_to.username,
                'received_person': order.received_person_name,
                'iv_number': order.iv_number,
                'edit_url': reverse('store_admin_orders') + f"?edit={order.id}#create",
                'delete_url': reverse('delete_supply_order', args=[order.id]),
            })
        return JsonResponse({'supply_orders': data})
    
    # Handle CSV export via AJAX
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_summary.csv"'
        writer = csv.writer(response)
        writer.writerow(['Category', 'Model', 'Quantity Supplied', 'Supplied Date', 'Supplied To', 'Received Person', 'IV Number'])
        for order in supply_orders:
            writer.writerow([
                order.category.name,
                order.model.model,
                order.quantity_supplied,
                order.supplied_date.strftime('%d-%m-%Y'),
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

# for product supplied table 
def ajax_stock_summary(request):
    search = request.GET.get('search', '')
    supply_orders = SupplyOrder.objects.select_related('category', 'model', 'supplied_to')

    if search:
        supply_orders = supply_orders.filter(
            Q(category__name__icontains=search) |
            Q(model__model__icontains=search) |
            Q(supplied_to__username__icontains=search)
        )

    data = []
    for order in supply_orders.order_by('-supplied_date'):
        data.append({
            'id': order.id,
            'category': order.category.name,
            'model': order.model.model,
            'quantity': order.quantity_supplied,
            'supplied_date': order.supplied_date.strftime('%d-%m-%Y'),
            'supplied_to': order.supplied_to.username,
            'received_person': order.received_person_name,
            'iv_number': order.iv_number,
        })

    return JsonResponse({'orders': data})

# dashboard view table filter
def get_filtered_product_status(request):
    search = request.GET.get('search', '').lower()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    products = Product.objects.all()

    if search:
        products = products.filter(model__icontains=search) | products.filter(category__name__icontains=search)
    if start_date:
        products = products.filter(purchased_date__gte=start_date)
    if end_date:
        products = products.filter(purchased_date__lte=end_date)

    data = []
    for p in products:
        supplied_quantity = SupplyOrder.objects.filter(model=p).aggregate(total=Sum('quantity_supplied'))['total'] or 0
        data.append({
            'id': p.id,
            'category': p.category.name,
            'model': p.model,
            'purchased_date': p.purchased_date.strftime('%Y-%m-%d'),
            'quantity_received': p.quantity,
            'quantity_supplied': supplied_quantity,
            'quantity_in_stock': p.quantity - supplied_quantity
        })

    return JsonResponse(data, safe=False)

# dashboard table export 
def export_product_status_csv(request):
    search = request.GET.get('search', '').lower()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    products = Product.objects.all()

    if search:
        products = products.filter(model__icontains=search) | products.filter(category__name__icontains=search)
    if start_date:
        products = products.filter(purchased_date__gte=start_date)
    if end_date:
        products = products.filter(purchased_date__lte=end_date)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="product_status.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Category', 'Model', 'Purchased Date', 'Quantity Received', 'Quantity Supplied', 'Quantity in Stock'])

    for p in products:
        supplied_quantity = SupplyOrder.objects.filter(model=p).aggregate(total=Sum('quantity_supplied'))['total'] or 0
        writer.writerow([
            p.id,
            p.category.name,
            p.model,
            p.purchased_date,
            p.quantity,
            supplied_quantity,
            p.quantity - supplied_quantity
        ])

    return response

# chart 1
def get_received_vs_supplied_data(request):
    received_data = defaultdict(int)
    supplied_data = defaultdict(int)

    # Group received quantity by category
    for product in Product.objects.select_related('category'):
        category_name = product.category.name
        received_data[category_name] += product.quantity

    # Group supplied quantity by category
    for order in SupplyOrder.objects.select_related('category'):
        category_name = order.category.name
        supplied_data[category_name] += order.quantity_supplied

    # Combine all unique categories
    labels = sorted(set(received_data.keys()) | set(supplied_data.keys()))
    received = [received_data.get(label, 0) for label in labels]
    supplied = [supplied_data.get(label, 0) for label in labels]

    return JsonResponse({
        'labels': labels,
        'received': received,
        'supplied': supplied,
    })

# chart 2 
def get_supply_vs_stock_data(request):
    category_received = defaultdict(int)
    category_supplied = defaultdict(int)

    for product in Product.objects.select_related('category'):
        category_name = product.category.name
        category_received[category_name] += product.quantity

    for order in SupplyOrder.objects.select_related('category'):
        category_name = order.category.name
        category_supplied[category_name] += order.quantity_supplied

    categories = sorted(set(category_received.keys()) | set(category_supplied.keys()))

    data = []
    for cat in categories:
        received = category_received.get(cat, 0)
        supplied = category_supplied.get(cat, 0)
        in_stock = max(received - supplied, 0)
        data.append({
            'category': cat,
            'received': received,
            'supplied': supplied,
            'in_stock': in_stock
        })

    return JsonResponse({'data': data})

# chart 3 
def get_categorywise_userwise_supply_data(request):
    # Total quantity received per category
    total_received_per_category = defaultdict(int)
    for product in Product.objects.select_related('category'):
        total_received_per_category[product.category.name] += product.quantity

    # Supplied quantity per category per user
    category_data = defaultdict(lambda: defaultdict(int))  # {category: {username: qty}}
    for order in SupplyOrder.objects.select_related('category', 'supplied_to'):
        category_data[order.category.name][order.supplied_to.username] += order.quantity_supplied

    result = []

    for category, user_data in category_data.items():
        labels = list(user_data.keys())
        values = list(user_data.values())

        total_supplied = sum(values)
        total_received = total_received_per_category.get(category, 0)
        not_supplied = total_received - total_supplied

        if not_supplied > 0:
            labels.append("Not Supplied")
            values.append(not_supplied)

        result.append({
            'category': f"{category} ({total_received})",
            'labels': labels,
            'data': values,
        })

    return JsonResponse({'data': result})

# chart 4 
def get_modelwise_received_vs_supplied(request):
    received_data = defaultdict(int)
    supplied_data = defaultdict(int)
    model_category_map = {}

    # Aggregate received data and map model to category
    for product in Product.objects.all():
        key = f"{product.model} ({product.category.name})"
        received_data[key] += product.quantity
        model_category_map[product.model] = product.category.name

    # Aggregate supplied data
    for order in SupplyOrder.objects.all():
        category_name = model_category_map.get(order.model.model, "Unknown")
        key = f"{order.model.model} ({category_name})"
        supplied_data[key] += order.quantity_supplied

    all_keys = sorted(set(received_data.keys()) | set(supplied_data.keys()))

    data = {
        'models': [],
        'received': [],
        'supplied': [],
    }

    for key in all_keys:
        data['models'].append(key)
        data['received'].append(received_data.get(key, 0))
        data['supplied'].append(supplied_data.get(key, 0))

    return JsonResponse(data)