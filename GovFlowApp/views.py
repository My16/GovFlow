from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm

# Create your views here.

def create_user(request):
    if request.method == "POST":
        form = UserProfileForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created successfully.")
            return redirect('homepage')
        else:
            messages.error(request, "Error creating user. Please check the form.")

    else:
        form = UserProfileForm()

    context = {'form': form}

    return render(request, 'create_user.html', context)


def loginpage(request):

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')  # checkbox

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Handle "Remember Me"
            if remember:
                request.session.set_expiry(21600)  # 2 weeks
            else:
                request.session.set_expiry(0)  # closes on browser close

            # Redirect based on user type
            if user.is_staff:
                return redirect('create_user')   # admin sees create user page
            else:
                return redirect('dashboard')     # regular user goes to dashboard

        else:
            messages.error(request, "Invalid username or password.")
    
    context = {}

    return render(request, 'loginpage.html', context)

def logout_user(request):
    logout(request)
    return redirect('loginpage')


@login_required(login_url='loginpage')
def homepage(request):
    # Redirect admins to create_user
    if request.user.is_staff:
        return redirect('create_user')
    
    context = {}

    return render(request, 'homepage.html', context)

@login_required(login_url='loginpage')
def dashboard(request):
    
    context = {}

    return render(request, 'dashboard.html', context)

@login_required(login_url='loginpage')
def all_documents(request):
    
    context = {}

    return render(request, 'all_documents.html', context)

@login_required(login_url='loginpage')
def new_document(request):
    
    context = {}

    return render(request, 'new_document.html', context)