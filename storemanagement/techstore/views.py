from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils.safestring import mark_safe
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