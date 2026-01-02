from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm
from .models import Document, DocumentHistory, Notification
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from collections import defaultdict
from django.db.models import Q, OuterRef, Subquery
from django.http import JsonResponse
from django.template.loader import render_to_string

# Create your views here.

def notify(user, message, url=""):
    if user:
        Notification.objects.create(
            recipient=user,
            message=message,
            url=url
        )

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
    # Get documents where user is sender OR current office
    user_documents = Document.objects.filter(
        Q(sender=request.user) | Q(current_office=request.user)
    )

    # Summary counts for this user
    total_documents = user_documents.count()
    in_progress = user_documents.filter(received_at__isnull=True).count()
    received = user_documents.filter(received_at__isnull=False).count()
    high_priority = user_documents.filter(priority='High').count()

    # 6 most recent documents for this user
    recent_documents = user_documents.order_by('-created_at')[:6]

    departments = defaultdict(list)
    all_users = User.objects.select_related("userprofile").all()
    for u in all_users:
        if hasattr(u, "userprofile") and u.userprofile.department:
            departments[u.userprofile.department].append(u)

    context = {
        "total_documents": total_documents,
        "in_progress": in_progress,
        "received": received,
        "high_priority": high_priority,
        "recent_documents": recent_documents,
        "departments": dict(departments),
    }

    return render(request, 'dashboard.html', context)

@login_required(login_url='loginpage')
def all_documents(request):
    # Get documents where user is sender OR current office
    documents = Document.objects.filter(
        Q(sender=request.user) | Q(current_office=request.user)
    ).order_by('-created_at')

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

    # GROUP USERS BY DEPARTMENT
    from collections import defaultdict
    departments = defaultdict(list)

    all_users = User.objects.select_related("userprofile").all()
    for u in all_users:
        if hasattr(u, "userprofile") and u.userprofile.department:
            departments[u.userprofile.department].append(u)


    context = {
        'documents': page_obj,  # pass page object
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'paginator': paginator,
        'departments': dict(departments),
    }
    return render(request, 'all_documents.html', context)

@login_required(login_url='loginpage')
def new_document(request):
    if request.method == "POST":
        title = request.POST.get("title")
        priority = request.POST.get("priority")
        description = request.POST.get("description")

        # current_office defaults to sender in models.py, no need to get from form
        document = Document.objects.create(
            title=title,
            sender=request.user,
            priority=priority,
            description=description
        )

        notify(
            request.user,
            f"Document {document.tracking_id} was created.",
            url=f"/documents/{document.pk}/"
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
        return redirect("all_documents")
    
    # GROUP USERS BY DEPARTMENT
    from collections import defaultdict
    departments = defaultdict(list)

    all_users = User.objects.select_related("userprofile").all()
    for u in all_users:
        if hasattr(u, "userprofile") and u.userprofile.department:
            departments[u.userprofile.department].append(u)


    history = document.history.order_by("-timestamp")

    context = {
        "document": document,
        "history": history,
        "departments": dict(departments),
    }

    return render(request, "document_detail.html", context)


@login_required
def forward_document(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        new_office_id = request.POST.get("new_office")
        note = request.POST.get("note")

        new_office_user = get_object_or_404(User, id=new_office_id)

        # Use model method you already created
        document.forward_to(
            new_office=new_office_user,
            forwarded_by=request.user,
            note=note
        )

        # Send notifications
        notify(
            new_office_user,
            f"Document {document.tracking_id} was forwarded to you.",
            url=f"/documents/{document.pk}/"
        )

        notify(
            document.sender,
            f"Your document {document.tracking_id} was forwarded to {new_office_user.get_full_name()}."
        )

        messages.success(request, "Document forwarded successfully.")
        return redirect("document_detail", pk=pk)

    messages.error(request, "Invalid request.")
    return redirect("document_detail", pk=pk)


@login_required(login_url='loginpage')
def receive_page(request):

    latest_forward = DocumentHistory.objects.filter(
        document=OuterRef("pk"),
        action="Forwarded"
    ).order_by("-timestamp")

    incoming = Document.objects.annotate(
        forwarded_to=Subquery(latest_forward.values("to_office")[:1]),
        forwarded_at=Subquery(latest_forward.values("timestamp")[:1]),
    ).filter(
        forwarded_to=request.user,
        status="In Transit"
    )

    context = {
        "incoming": incoming
    }
    return render(request, "receive.html", context)



def routing_slip_partial(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    return render(request, 'documents/partials/routing_slip.html', {'document': doc})


@login_required
def receive_document(request):
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("receive_page")

    tracking_id = request.POST.get("tracking_id")
    if not tracking_id:
        messages.error(request, "Tracking ID is required.")
        return redirect("receive_page")

    # Look for the document
    try:
        document = Document.objects.get(tracking_id=tracking_id)
    except Document.DoesNotExist:
        messages.error(request, "Document not found with this tracking ID.")
        return redirect("receive_page")

    # Check if document has already been received by this user/office
    if document.status == "Received" and document.current_office == request.user:
        messages.warning(request, f"Document {document.tracking_id} has already been received by your office.")
        return redirect("receive_page")

    # Get the last forward action from history
    last_forward = document.history.filter(action="Forwarded").order_by("-timestamp").first()

    if not last_forward:
        messages.error(request, "This document has not been forwarded to any office yet.")
        return redirect("receive_page")

    # Check if the logged-in user belongs to the forwarded office
    if request.user != last_forward.to_office:
        messages.error(
            request,
            f"You are not authorized to receive this document. "
            f"This document is assigned to {last_forward.to_office.get_full_name()}."
        )
        return redirect("receive_page")

    # Mark as received
    document.mark_received(
        receiving_office=request.user,
        received_by=request.user,
        note="Received via QR/manual entry"
    )

    # Send notifications
    notify(
        document.sender,
        f"Document {document.tracking_id} was received by {request.user.get_full_name()}."
    )

    messages.success(request, f"Document {document.tracking_id} received successfully.")
    return redirect("receive_page")


# notification starts here
@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(
        Notification, pk=pk, recipient=request.user
    )
    notification.is_read = True
    notification.save()

    if notification.url:
        return redirect(notification.url)

    return redirect(request.META.get("HTTP_REFERER", "dashboard"))

@login_required
def notifications_api(request):
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by("-created_at")[:5]

    html = render_to_string(
        "partials/notification_items.html",
        {"notifications": notifications},
        request=request
    )

    return JsonResponse({
        "count": notifications.count(),
        "html": html
    })