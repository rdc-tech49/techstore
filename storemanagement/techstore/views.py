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
from .models import ProductCategory, Product, SupplyOrder, LoanRegister
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
from django.views.decorators.csrf import csrf_exempt



def home(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_superuser:
                return redirect('store_admin_dashboard')  # URL name for admin dashboard
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
def store_admin_loanregister(request):
    categories = ProductCategory.objects.all()
    users = User.objects.all()
    products = Product.objects.select_related('category').all()
    loan_records = LoanRegister.objects.select_related('category', 'model', 'supplied_to').order_by('-date_supplied')

    # Calculate available quantity per product for loan
    supplied_totals = SupplyOrder.objects.values('model_id').annotate(total_supplied=Sum('quantity_supplied'))
    loaned_totals = LoanRegister.objects.values('model_id').annotate(total_loaned=Sum('quantity_supplied_in_loan'))
    
    supplied_dict = {item['model_id']: item['total_supplied'] for item in supplied_totals}
    loaned_dict = {item['model_id']: item['total_loaned'] for item in loaned_totals}

    available_for_loan = []
    for product in products:
        total_supplied = supplied_dict.get(product.id, 0)
        total_loaned = loaned_dict.get(product.id, 0)
        # Now calculate the total that has been returned via LoanRegister
        total_returned = (
            LoanRegister.objects
            .filter(model_id=product.id, loaned_item_returned_date__isnull=False)
            .aggregate(total=Sum('quantity_supplied_in_loan'))
        )['total'] or 0

        # Effective loaned quantity = total loaned - total returned
        effective_loaned = total_loaned - total_returned

        remaining = product.quantity - total_supplied - effective_loaned
        if remaining > 0:
            available_for_loan.append({
                'category': product.category.name,
                'model': product.model,
                'purchased_date': product.purchased_date,
                'available_quantity': remaining
            })

    context = {
        'categories': categories,
        'users': users,
        'loan_records': loan_records,
        'available_for_loan': available_for_loan,
    }
    return render(request, 'techstore/store_admin_loanregister.html', context)


@csrf_exempt
def loan_product_to_user(request):
    if request.method == 'POST':
        loan_id = request.POST.get("loan_id")
        returned_date = request.POST.get("loaned_item_returned_date")

        if loan_id:
            # Update existing loan record
            loan = get_object_or_404(LoanRegister, id=loan_id)
            loan.loaned_item_returned_date = returned_date
            loan.save()
            messages.success(request, "Loan return updated successfully.")
            return redirect('/store-admin/loan-register/')
        
        category_id = request.POST['category']
        model_id = request.POST['model']
        quantity = int(request.POST['quantity'])
        description= request.POST['description']
        date_supplied = request.POST['date_supplied']
        supplied_to_id = request.POST['supplied_to']
        received_person_name = request.POST['received_person_name']

        LoanRegister.objects.create(
            category_id=category_id,
            model_id=model_id,
            quantity_supplied_in_loan=quantity,
            description=description,
            date_supplied=date_supplied,
            supplied_to_id=supplied_to_id,
            received_person_name=received_person_name
        )
        return redirect('store_admin_loanregister')

def get_models_by_category(request, category_id):
    models = Product.objects.filter(category_id=category_id)
    data = [{'id': m.id, 'model': m.model, 'quantity': m.quantity} for m in models]
    return JsonResponse({'models': data}) 

def get_available_loan_quantity(request, model_id):
    current_loan_id = request.GET.get('loan_id')
    product = get_object_or_404(Product, id=model_id)

    supplied_qty = SupplyOrder.objects.filter(model_id=model_id).aggregate(
        total=Sum('quantity_supplied'))['total'] or 0

    loaned_qs = LoanRegister.objects.filter(
        model_id=model_id,
        loaned_item_returned_date__isnull=True
    )

    if current_loan_id:
        loaned_qs = loaned_qs.exclude(id=current_loan_id)

    loaned_qty = loaned_qs.aggregate(total=Sum('quantity_supplied_in_loan'))['total'] or 0

    available_qty = product.quantity - supplied_qty - loaned_qty
    available_qty = max(available_qty, 0)

    return JsonResponse({'available_quantity': available_qty})


# loan record first table filter and export
def filter_loan_records(request):
    search = request.GET.get('search', '').strip()
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    export = request.GET.get('export')

    records = LoanRegister.objects.select_related('category', 'model', 'supplied_to')

    if search:
        records = records.filter(
            Q(category__name__icontains=search) |
            Q(model__model__icontains=search) |
            Q(supplied_to__username__icontains=search) |
            Q(received_person_name__icontains=search)
        )
    if start_date:
        records = records.filter(date_supplied__gte=start_date)
    if end_date:
        records = records.filter(date_supplied__lte=end_date)

        # Sorting logic
    sort_field = request.GET.get('sort', 'date')  # default field
    order = request.GET.get('order', 'desc')      # default order

    sort_map = {
        'category': 'category__name',
        'model': 'model__model',
        'quantity': 'quantity_supplied_in_loan',
        'date': 'date_supplied',
        'supplied_to': 'supplied_to__username',
    }

    sort_by = sort_map.get(sort_field, 'date_supplied')
    if order == 'desc':
        sort_by = '-' + sort_by

    records = records.order_by(sort_by)

    if export == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="loan_products.csv"'
        writer = csv.writer(response)
        writer.writerow(['Category', 'Model', 'Quantity Supplied', 'Loan Date', 'Supplied To', 'Received Person'])
        for r in records:
            writer.writerow([
                r.category.name,
                r.model.model,
                r.quantity_supplied_in_loan,
                r.date_supplied.strftime('%d-%m-%Y'),
                r.supplied_to.username,
                r.received_person_name
            ])
        return response
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        rows = ""
        for i, r in enumerate(records, 1):
            if not r.loaned_item_returned_date:
                action_btn = f"""
                <button class="btn btn-sm btn-success receive-btn"
                        data-id="{r.id}"
                        data-category="{r.category.id}"
                        data-model="{r.model.id}"
                        data-quantity="{r.quantity_supplied_in_loan}"
                        data-description="{r.description}"
                        data-date-supplied="{r.date_supplied}"
                        data-supplied-to="{r.supplied_to.id}"
                        data-received-person="{r.received_person_name}">
                  Item Received
                </button>
            """
            else:
                action_btn = '<span class="badge bg-secondary">Returned</span>'

            rows += f"""
            <tr>
                <td>{i}</td>
                <td>{r.category.name}</td>
                <td>{r.model.model}</td>
                <td>{r.quantity_supplied_in_loan}</td>
                <td>{r.date_supplied.strftime('%Y-%m-%d')}</td>
                <td>{r.supplied_to.username}</td>
                <td>{r.received_person_name}</td>
                <td>{action_btn}</td>
             </tr>
            """
        return HttpResponse(rows)


@login_required
def dashboard_view(request): 
    # Get all products (ordered by ID descending for example)
    products = Product.objects.all().order_by('-id')

    # Aggregate SupplyOrder data grouped by product model
    supply_data = SupplyOrder.objects.values('model__model').annotate(
        total_supplied=Sum('quantity_supplied')
    )
    supplied_dict = {item['model__model']: item['total_supplied'] for item in supply_data}

    # Aggregate LoanRegister data grouped by product model (only where item is NOT returned)
    loan_data = LoanRegister.objects.filter(loaned_item_returned_date__isnull=True).values('model__model').annotate(
        total_loaned=Sum('quantity_supplied_in_loan')
    )
    loaned_dict = {item['model__model']: item['total_loaned'] for item in loan_data}

    # Prepare product status list with the new column
    product_status = []
    for product in products:
        model_name = product.model  # Assuming model is stored as string

        supplied_qty = supplied_dict.get(model_name, 0) or 0
        loaned_qty = loaned_dict.get(model_name, 0) or 0
        quantity_received = product.quantity
        quantity_in_stock = quantity_received - (supplied_qty + loaned_qty)

        product_status.append({
            'id': product.id,
            'category': product.category.name,
            'model': model_name,
            'purchased_date': product.purchased_date.strftime('%Y-%m-%d'),
            'quantity_received': quantity_received,
            'quantity_supplied': supplied_qty,
            'quantity_given_in_loan': loaned_qty,
            'quantity_in_stock': quantity_in_stock,
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
    # Total supplied per product
    supplied_totals = SupplyOrder.objects.values('model_id').annotate(total_supplied=Sum('quantity_supplied'))
    supplied_dict = {item['model_id']: item['total_supplied'] for item in supplied_totals}

    # Total loaned per product
    loaned_totals = LoanRegister.objects.filter(loaned_item_returned_date__isnull=True).values('model_id').annotate(total_loaned=Sum('quantity_supplied_in_loan'))

    loaned_dict = {item['model_id']: item['total_loaned'] for item in loaned_totals}

    # Available quantity = total received - (supplied + loaned)
    available_quantities = {
        product.id: max(product.quantity - supplied_dict.get(product.id, 0) - loaned_dict.get(product.id, 0), 0)
        for product in products}

    
    product_search = request.GET.get('product_search', '').strip()
    product_start_date = request.GET.get('product_start_date')
    product_end_date = request.GET.get('product_end_date')
    product_export = request.GET.get('product_export')

    products_to_supply = []
    for product in products:
        total_supplied = supplied_dict.get(product.id, 0)
        total_loaned = loaned_dict.get(product.id, 0)
        remaining_quantity = max(product.quantity - total_supplied - total_loaned, 0)
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
    
    #  sort for second table 
    product_sort_field = request.GET.get('product_sort_field', 'purchased_date')
    product_sort_direction = request.GET.get('product_sort_direction', 'desc')
    # Map frontend sort fields to real fields
    product_sort_field_map = {
        'category_name': 'category__name',
        'model': 'model__model',
        'purchased_date': 'purchased_date',
        'remaining_quantity': 'remaining_quantity',
    }
    order_by_field = product_sort_field_map.get(product_sort_field, 'purchased_date')
    if product_sort_direction == 'desc':
        order_by_field = '-' + order_by_field
    # Define a key mapper for sorting
    def sort_key(item):
        if product_sort_field == 'category_name':
            return item['category_name']
        elif product_sort_field == 'model':
            return item['model']
        elif product_sort_field == 'purchased_date':
            return item['purchased_date']
        elif product_sort_field == 'remaining_quantity':
            return item['remaining_quantity']
        return item['purchased_date']  # default
    reverse_sort = (product_sort_direction == 'desc')
    products_to_supply = sorted(products_to_supply, key=sort_key, reverse=reverse_sort)
    # end of sort for second table


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

    sort_field = request.GET.get('sort_field', 'supplied_date')
    sort_direction = request.GET.get('sort_direction', 'desc')

    if sort_field in ['category', 'model', 'quantity_supplied', 'supplied_date', 'supplied_to']:
        if sort_field == 'category':
            order_by_field = 'category__name'
        elif sort_field == 'model':
            order_by_field = 'model__model'
        elif sort_field == 'supplied_to':
            order_by_field = 'supplied_to__username'
        else:
            order_by_field = sort_field
        if sort_direction == 'desc':
            order_by_field = '-' + order_by_field
        supply_orders = supply_orders.order_by(order_by_field)

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
        # Recalculate loaned quantity too
        total_loaned = loaned_dict.get(model_obj.id, 0)
        max_available = model_obj.quantity - total_supplied_excl_self - total_loaned
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
            total_loaned = loaned_dict.get(model_obj.id, 0)
            available_quantity = model_obj.quantity - total_supplied_excl - total_loaned

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
        total_quantity = product.quantity

        # Total supplied to users
        total_supplied = SupplyOrder.objects.filter(model_id=product_id)\
                            .aggregate(total=Sum('quantity_supplied'))['total'] or 0

        # Total loaned out
        total_loaned = LoanRegister.objects.filter(model_id=product_id)\
                           .aggregate(total=Sum('quantity_supplied_in_loan'))['total'] or 0

        # Total loaned items returned
        total_returned = LoanRegister.objects.filter(
            model_id=product_id, loaned_item_returned_date__isnull=False
        ).aggregate(total=Sum('quantity_supplied_in_loan'))['total'] or 0

        # Effective loaned = loaned - returned
        effective_loaned = total_loaned - total_returned

        # Final available quantity
        available_quantity = total_quantity - total_supplied - effective_loaned

        return JsonResponse({'available_quantity': max(available_quantity, 0)})

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
        products = products.filter(
            Q(model__icontains=search) | Q(category__name__icontains=search)
        )
    if start_date:
        products = products.filter(purchased_date__gte=start_date)
    if end_date:
        products = products.filter(purchased_date__lte=end_date)

    data = []
    for p in products:
        supplied_quantity = SupplyOrder.objects.filter(model=p).aggregate(total=Sum('quantity_supplied'))['total'] or 0
        loaned_quantity = LoanRegister.objects.filter(model=p, loaned_item_returned_date__isnull=True).aggregate(total=Sum('quantity_supplied_in_loan'))['total'] or 0
        quantity_in_stock = p.quantity - (supplied_quantity + loaned_quantity)

        data.append({
            'id': p.id,
            'category': p.category.name,
            'model': p.model,
            'purchased_date': p.purchased_date.strftime('%Y-%m-%d'),
            'quantity_received': p.quantity,
            'quantity_supplied': supplied_quantity,
            'quantity_given_in_loan': loaned_quantity,
            'quantity_in_stock': quantity_in_stock
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


def product_status_summary_by_category(request):
    category_filter = request.GET.get('category', '').strip().lower()
    export_csv = request.GET.get('export') == '1'

    categories = Product.objects.values_list('category__name', flat=True).distinct()

    data = []
    for category_name in categories:
        if category_filter and category_filter not in category_name.lower():
            continue

        # Quantity received
        received_qty = Product.objects.filter(category__name=category_name).aggregate(
            total=Sum('quantity')
        )['total'] or 0

        # Quantity supplied
        supplied_qty = SupplyOrder.objects.filter(category__name=category_name).aggregate(
            total=Sum('quantity_supplied')
        )['total'] or 0

        # Quantity loaned (only where loaned_item_returned_date is NULL)
        loaned_qty = LoanRegister.objects.filter(
            category__name=category_name,
            loaned_item_returned_date__isnull=True
        ).aggregate(
            total=Sum('quantity_supplied_in_loan')
        )['total'] or 0

        # Quantity in stock
        in_stock = received_qty - (supplied_qty + loaned_qty)

        data.append({
            'category': category_name,
            'quantity_received': received_qty,
            'quantity_supplied': supplied_qty,
            'quantity_loaned': loaned_qty,
            'quantity_in_stock': in_stock,
        })

    # CSV export
    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="product_summary_by_category.csv"'
        writer = csv.writer(response)
        writer.writerow(['Category', 'Quantity Received', 'Quantity Supplied', 'Quantity Supplied in Loan', 'Quantity in Stock'])
        for row in data:
            writer.writerow([
                row['category'],
                row['quantity_received'],
                row['quantity_supplied'],
                row['quantity_loaned'],
                row['quantity_in_stock']
            ])
        return response

    # JSON response for AJAX
    return JsonResponse({'data': data})



# First chart - stacked bar chart for received vs supplied
def category_chart_data(request):
    categories = Product.objects.values_list('category__name', flat=True).distinct()
    data = {
        'categories': [],
        'received': [],
        'supplied': [],
        'in_stock': [],
    }

    for category_name in categories:
        received_qty = Product.objects.filter(category__name=category_name).aggregate(total=Sum('quantity'))['total'] or 0
        supplied_qty = SupplyOrder.objects.filter(category__name=category_name).aggregate(total=Sum('quantity_supplied'))['total'] or 0
        in_stock = received_qty - supplied_qty

        data['categories'].append(category_name)
        data['received'].append(received_qty)
        data['supplied'].append(supplied_qty)
        data['in_stock'].append(in_stock)

    return JsonResponse(data)

# second chart - stacked bar chart for model vise received vs supplied
def model_chart_data(request):
    category_name = request.GET.get('category')

    # First, filter products by selected category
    products = Product.objects.filter(category__name=category_name)

    # Get unique model names within that category only
    model_names = products.values_list('model', flat=True).distinct()

    data = {
        'models': [],
        'received': [],
        'supplied': [],
        'in_stock': [],
    }

    for model in model_names:
        received_qty = products.filter(model=model).aggregate(total=Sum('quantity'))['total'] or 0
        supplied_qty = SupplyOrder.objects.filter(model__model=model, category__name=category_name).aggregate(total=Sum('quantity_supplied'))['total'] or 0
        in_stock = received_qty - supplied_qty

        label = f"{model}"
        data['models'].append(label)
        data['received'].append(received_qty)
        data['supplied'].append(supplied_qty)
        data['in_stock'].append(in_stock)

    return JsonResponse(data)

# third chart - pie chart for product status
def user_category_supply_chart(request):
    users = SupplyOrder.objects.values_list('supplied_to__username', flat=True).distinct()
    categories = SupplyOrder.objects.values_list('category__name', flat=True).distinct()
    
    supplied = {category: [] for category in categories}

    for user in users:
        for category in categories:
            qty = SupplyOrder.objects.filter(
                supplied_to__username=user,
                category__name=category
            ).aggregate(total=Sum('quantity_supplied'))['total'] or 0
            supplied[category].append(qty)

    return JsonResponse({
        'users': list(users),
        'categories': list(categories),
        'supplied': supplied,
    })

# fourth chart
def model_supply_by_user(request):
    username = request.GET.get('username')
    supplies = SupplyOrder.objects.filter(supplied_to__username=username)

    models = []
    quantities = []

    for entry in supplies.values('model__model', 'category__name').distinct():
        model_name = entry['model__model']
        category_name = entry['category__name']
        label = f"{model_name} ({category_name})"

        total_qty = supplies.filter(
            model__model=model_name,
            category__name=category_name
        ).aggregate(total=Sum('quantity_supplied'))['total'] or 0

        models.append(label)
        quantities.append(total_qty)

    return JsonResponse({
        'models': models,
        'quantities': quantities,
    })


def user_dashboard_view(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('login')
    return render(request, 'techstore/user_dashboard.html')

def user_products_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user_supply_orders = SupplyOrder.objects.select_related('model__category', 'supplied_to').filter(
        supplied_to=request.user
    ).order_by('-supplied_date')

    return render(request, 'techstore/user_products.html', {
        'user_supply_orders': user_supply_orders,
    })


def user_orders_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'techstore/user_orders.html')

def user_loan_records_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'techstore/user_loan_records.html')
