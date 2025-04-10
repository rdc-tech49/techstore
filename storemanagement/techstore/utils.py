# storemanagement/utils.py
from .models import SupplyOrder, LoanRegister, Product
from django.db.models import Q, Sum

def get_available_quantity_for_model(model_id):
    try:
        product = Product.objects.get(id=model_id)
        total_supplied = SupplyOrder.objects.filter(model_id=model_id).aggregate(total=Sum('quantity_supplied'))['total'] or 0
        total_loaned = LoanRegister.objects.filter(model_id=model_id).aggregate(total=Sum('quantity_supplied_in_loan'))['total'] or 0
        return product.quantity - total_supplied - total_loaned
    except Product.DoesNotExist:
        return 0
