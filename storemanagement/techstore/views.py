from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils.safestring import mark_safe
from .forms import CustomUserCreationForm
# Create your views here.



def home(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        # Authenticate
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # messages.success(request, "You Have Been Logged In!")
            return redirect('admin/')
        else:
            messages.success(request, mark_safe("! Invalid Username or Password. <br> Try Again..."))
            return redirect('home')
    else:
        return render(request, "techstore/home.html",{})
    

def register(request):
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
    return render(request, 'techstore/register.html', {'form': form})
