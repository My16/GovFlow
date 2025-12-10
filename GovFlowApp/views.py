from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm
from .models import Document
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import base64, os
from django.conf import settings

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
    # Get only documents created by the logged-in user
    user_documents = Document.objects.filter(sender=request.user)

    # Summary counts for this user
    total_documents = user_documents.count()
    in_progress = user_documents.filter(received_at__isnull=True).count()
    received = user_documents.filter(received_at__isnull=False).count()
    high_priority = user_documents.filter(priority='High').count()

    # 6 most recent documents for this user
    recent_documents = user_documents.order_by('-created_at')[:6]

    context = {
        "total_documents": total_documents,
        "in_progress": in_progress,
        "received": received,
        "high_priority": high_priority,
        "recent_documents": recent_documents,
    }

    return render(request, 'dashboard.html', context)

@login_required(login_url='loginpage')
def all_documents(request):
    # Filter documents created by the current logged-in user
    documents = Document.objects.filter(sender=request.user).order_by('-created_at')

    # Apply filters
    status_filter = request.GET.get('status', 'All')
    priority_filter = request.GET.get('priority', 'All')
    if priority_filter != 'All':
        documents = documents.filter(priority=priority_filter)
    if status_filter != 'All':
        documents = documents.filter(status=status_filter)

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(documents, 10)  # 10 documents per page
    page_obj = paginator.get_page(page_number)

    context = {
        'documents': page_obj,  # pass page object
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'paginator': paginator,
    }
    return render(request, 'all_documents.html', context)

@login_required(login_url='loginpage')
def new_document(request):
    if request.method == "POST":
        title = request.POST.get("title")
        priority = request.POST.get("priority")
        description = request.POST.get("description")

        # current_office defaults to sender in models.py, no need to get from form
        Document.objects.create(
            title=title,
            sender=request.user,
            priority=priority,
            description=description
        )

        messages.success(request, "Document registered successfully.")
        return redirect("dashboard")
    
    # No need to pass 'users' if they are not used in the form
    return render(request, 'new_document.html')


@login_required(login_url='loginpage')
def delete_document(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        document.delete()
        messages.success(request, "Document successfully deleted.")
        return redirect("all_documents")  # update your list view name

    messages.error(request, "Invalid request.")
    return redirect("all_documents")

@login_required
def document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk)

    # Only allow viewing if:
    # - User is sender OR current office
    if request.user != document.sender and request.user != document.current_office:
        messages.error(request, "You are not authorized to view this document.")
        return redirect("documents:list")

    history = document.history.order_by("-timestamp")

    context = {
        "document": document,
        "history": history,
    }

    return render(request, "document_detail.html", context)


def document_pdf(request, pk):
    document = get_object_or_404(Document, pk=pk)
    template_path = 'document_pdf.html'

    # Convert QR code to base64
    qr_base64 = ""
    if document.qr_code:
        with open(document.qr_code.path, "rb") as qr_file:
            qr_bytes = qr_file.read()
            qr_base64 = base64.b64encode(qr_bytes).decode("utf-8")

     # Convert logos to Base64
    mharsmc_logo_path = r"D:\Code\GovFlow\GovFlowApp\static\img\mharsmc.png"
    doh_logo_path = r"D:\Code\GovFlow\GovFlowApp\static\img\doh_logo.png"

    def img_to_base64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    mharsmc_logo_base64 = img_to_base64(mharsmc_logo_path)
    doh_logo_base64 = img_to_base64(doh_logo_path)

    context = {
        'document': document,
        'qr_base64': qr_base64,
        'mharsmc_logo_base64': mharsmc_logo_base64,
        'doh_logo_base64': doh_logo_base64,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="document_{document.tracking_id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF <pre>' + html + '</pre>')

    return response
