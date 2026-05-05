from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, OuterRef, Subquery
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, datetime
from collections import defaultdict
import datetime as datetime_module
import pandas as pd
from io import BytesIO
from xhtml2pdf import pisa
from .forms import UserProfileForm
from .models import Document, DocumentHistory, Notification, UserProfile

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




from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q


def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required(login_url='loginpage')
def user_management(request):
    """
    List all system users. Only admins can add/edit/delete;
    regular staff see the list read-only.
    """
    search_query = request.GET.get('q', '').strip()

    users = User.objects.select_related('userprofile').all().order_by(
        'first_name', 'last_name'
    )

    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)  |
            Q(username__icontains=search_query)   |
            Q(email__icontains=search_query)      |
            Q(userprofile__department__icontains=search_query) |
            Q(userprofile__position__icontains=search_query)
        )

    total_users    = users.count()
    active_users   = users.filter(is_active=True).count()
    inactive_users = users.filter(is_active=False).count()
    admin_users    = users.filter(is_staff=True).count()

    for user in users:
        UserProfile.objects.get_or_create(user=user)

    context = {
        'users':             users,
        'total_users':       total_users,
        'active_users':      active_users,
        'inactive_users':    inactive_users,
        'admin_users':       admin_users,
        'search_query':      search_query,
        'department_choices': UserProfile.DEPARTMENT_CHOICES,
    }
    return render(request, 'user_management.html', context)


@login_required(login_url='loginpage')
@user_passes_test(is_admin, login_url='dashboard')
def user_management_add(request):
    """Create a new user from the Add User modal."""
    if request.method != 'POST':
        return redirect('user_management')

    first_name   = request.POST.get('first_name', '').strip()
    last_name    = request.POST.get('last_name',  '').strip()
    username     = request.POST.get('username',   '').strip()
    email        = request.POST.get('email',      '').strip()
    department   = request.POST.get('department', '').strip()
    position     = request.POST.get('position',   '').strip()
    password     = request.POST.get('password',   '')
    confirm_pw   = request.POST.get('confirm_password', '')
    is_staff_val = request.POST.get('is_staff', '0') == '1'

    # Basic validation
    if not all([first_name, last_name, username, password]):
        messages.error(request, "Please fill in all required fields.")
        return redirect('user_management')

    if password != confirm_pw:
        messages.error(request, "Passwords do not match.")
        return redirect('user_management')

    if len(password) < 8:
        messages.error(request, "Password must be at least 8 characters.")
        return redirect('user_management')

    if User.objects.filter(username=username).exists():
        messages.error(request, f"Username '{username}' is already taken.")
        return redirect('user_management')

    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff=is_staff_val,
    )

    # Update UserProfile fields for the new user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.department = department
    profile.position = position
    profile.save()

    messages.success(request, f"User {user.get_full_name()} created successfully.")
    return redirect('user_management')


@login_required(login_url='loginpage')
@user_passes_test(is_admin, login_url='dashboard')
def user_management_edit(request, pk):
    """Edit an existing user from the Edit User modal."""
    if request.method != 'POST':
        return redirect('user_management')

    target_user = get_object_or_404(User, pk=pk)

    first_name   = request.POST.get('first_name', '').strip()
    last_name    = request.POST.get('last_name',  '').strip()
    email        = request.POST.get('email',      '').strip()
    department   = request.POST.get('department', '').strip()
    position     = request.POST.get('position',   '').strip()
    password     = request.POST.get('password',   '').strip()
    is_staff_val = request.POST.get('is_staff', '0') == '1'
    is_active    = 'is_active' in request.POST

    if not all([first_name, last_name]):
        messages.error(request, "First and last name are required.")
        return redirect('user_management')

    # Prevent admin from revoking their own staff status
    if target_user == request.user and not is_staff_val:
        messages.error(request, "You cannot remove your own admin privileges.")
        return redirect('user_management')

    target_user.first_name = first_name
    target_user.last_name  = last_name
    target_user.email      = email
    target_user.is_staff   = is_staff_val
    target_user.is_active  = is_active

    if password:
        if len(password) < 8:
            messages.error(request, "New password must be at least 8 characters.")
            return redirect('user_management')
        target_user.set_password(password)

    target_user.save()

    # Update or create the user's profile fields
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    profile.department = department
    profile.position = position
    profile.save()

    messages.success(request, f"User {target_user.get_full_name()} updated successfully.")
    return redirect('user_management')


@login_required(login_url='loginpage')
@user_passes_test(is_admin, login_url='dashboard')
def user_management_delete(request, pk):
    """Delete a user (POST only)."""
    if request.method != 'POST':
        return redirect('user_management')

    target_user = get_object_or_404(User, pk=pk)

    if target_user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_management')

    full_name = target_user.get_full_name() or target_user.username
    target_user.delete()

    messages.success(request, f"User '{full_name}' has been deleted.")
    return redirect('user_management')


@login_required(login_url='loginpage')
@user_passes_test(is_admin, login_url='dashboard')
def user_management_toggle(request, pk):
    """AJAX endpoint: toggle is_active on a user."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method.'}, status=405)

    target_user = get_object_or_404(User, pk=pk)

    if target_user == request.user:
        return JsonResponse({'success': False, 'error': 'You cannot deactivate yourself.'})

    target_user.is_active = not target_user.is_active
    target_user.save()

    action = "activated" if target_user.is_active else "deactivated"
    name   = target_user.get_full_name() or target_user.username

    return JsonResponse({
        'success':   True,
        'is_active': target_user.is_active,
        'message':   f"User '{name}' has been {action}.",
    })


@login_required(login_url='loginpage')
def settings(request):
    """User settings page for updating personal profile."""
    if request.method == 'POST':
        first_name   = request.POST.get('first_name', '').strip()
        last_name    = request.POST.get('last_name',  '').strip()
        email        = request.POST.get('email',      '').strip()
        department   = request.POST.get('department', '').strip()
        position     = request.POST.get('position',   '').strip()
        current_pw   = request.POST.get('current_password', '').strip()
        password     = request.POST.get('password',   '').strip()
        confirm_pw   = request.POST.get('confirm_password', '').strip()

        if not all([first_name, last_name]):
            messages.error(request, "First and last name are required.")
            return redirect('settings')

        # If password change is requested, validate current password
        if password:
            if not current_pw:
                messages.error(request, "Current password is required to change password.")
                return redirect('settings')
            if not request.user.check_password(current_pw):
                messages.error(request, "Current password is incorrect.")
                return redirect('settings')
            if password != confirm_pw:
                messages.error(request, "New passwords do not match.")
                return redirect('settings')
            if len(password) < 8:
                messages.error(request, "New password must be at least 8 characters.")
                return redirect('settings')

        request.user.first_name = first_name
        request.user.last_name  = last_name
        request.user.email      = email

        if password:
            request.user.set_password(password)

        request.user.save()

        # Update profile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.department = department
        profile.position = position
        profile.save()

        messages.success(request, "Your settings have been updated successfully.")
        return redirect('settings')

    context = {
        'department_choices': UserProfile.DEPARTMENT_CHOICES,
    }
    return render(request, 'settings.html', context)


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
            # if user.is_staff:
            #     return redirect('create_user')   # admin sees create user page
            # else:
            #     return redirect('dashboard')     # regular user goes to dashboard

            return redirect('dashboard')

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
    
    # Fetch unread notifications for the current user
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by("-created_at")[:5]
    
    context = {
        'notifications': notifications
    }

    return render(request, 'homepage.html', context)

# @login_required(login_url='loginpage')
# def dashboard(request):
#     # Get documents where user is sender OR current office
#     user_documents = Document.objects.filter(
#         Q(sender=request.user) | Q(current_office=request.user)
#     )

#     # Summary counts for this user
#     total_documents = user_documents.count()
#     in_progress = user_documents.filter(received_at__isnull=True).count()
#     received = user_documents.filter(received_at__isnull=False).count()
#     high_priority = user_documents.filter(priority='High').count()

#     # 6 most recent documents for this user
#     recent_documents = user_documents.order_by('-created_at')[:6]

#     departments = defaultdict(list)
#     all_users = User.objects.select_related("userprofile").all()
#     for u in all_users:
#         if hasattr(u, "userprofile") and u.userprofile.department:
#             departments[u.userprofile.department].append(u)

#     context = {
#         "total_documents": total_documents,
#         "in_progress": in_progress,
#         "received": received,
#         "high_priority": high_priority,
#         "recent_documents": recent_documents,
#         "departments": dict(departments),
#     }

#     return render(request, 'dashboard.html', context)

@login_required(login_url='loginpage')
def dashboard(request):
    search_query = request.GET.get("q", "").strip()

    # Admins/superusers see all documents
    if request.user.is_staff or request.user.is_superuser:
        user_documents = Document.objects.all()
    else:
        user_documents = Document.objects.filter(
            Q(sender=request.user) |
            Q(current_office=request.user)
        )

    # Only apply search if query is 3 or more characters
    if len(search_query) >= 3:
        user_documents = user_documents.filter(
            Q(tracking_id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query)
        )
    else:
        search_query = ""

    # Summary counts
    total_documents = user_documents.count()
    in_progress = user_documents.filter(received_at__isnull=True).count()
    received = user_documents.filter(received_at__isnull=False).count()
    high_priority = user_documents.filter(priority='High').count()

    # Recent documents
    if search_query:
        recent_documents = user_documents.order_by('-created_at')
    else:
        recent_documents = user_documents.order_by('-created_at')[:6]

    # Departments for forwarding modal
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
        "search_query": search_query,
    }

    return render(request, "dashboard.html", context)

@login_required(login_url='loginpage')
def all_documents(request):
    # Superusers and staff can see all documents; normal users see only theirs.
    if request.user.is_superuser or request.user.is_staff:
        documents = Document.objects.all().order_by('-created_at')
    else:
        documents = Document.objects.filter(
            Q(sender=request.user) | Q(current_office=request.user)
        ).order_by('-created_at')

    # Filters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    search_query = request.GET.get('q', '').strip()
    per_page = request.GET.get('per_page', 10)

    # Convert per_page to int
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10

    # Apply filters
    if priority_filter and priority_filter != 'All':
        documents = documents.filter(priority=priority_filter)
    if status_filter and status_filter != 'All':
        documents = documents.filter(status=status_filter)

    # Apply search only if >=3 characters
    if len(search_query) >= 3:
        documents = documents.filter(
            Q(tracking_id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query)
        )
    elif search_query and len(search_query) < 3:
        search_query = ""

    # Store original queryset for summary stats (before pagination)
    all_documents_queryset = documents
    
    # Get all status counts for summary cards
    total_count = all_documents_queryset.count()
    pending_count = all_documents_queryset.filter(status='Pending').count()
    in_transit_count = all_documents_queryset.filter(status='In Transit').count()
    received_count = all_documents_queryset.filter(status='Received').count()
    returned_count = all_documents_queryset.filter(status='Returned').count()
    completed_count = all_documents_queryset.filter(status='Completed').count()
    high_priority_count = all_documents_queryset.filter(priority='High').count()
    
    # For alert panels (get recent items)
    high_priority_docs = all_documents_queryset.filter(priority='High').order_by('-created_at')[:5]
    pending_docs = all_documents_queryset.filter(status='Pending').order_by('-created_at')[:5]
    in_transit_docs = all_documents_queryset.filter(status='In Transit').order_by('-created_at')[:5]

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(documents, per_page)
    page_obj = paginator.get_page(page_number)

    # GROUP USERS BY DEPARTMENT
    from collections import defaultdict
    departments = defaultdict(list)

    all_users = User.objects.select_related("userprofile").all()
    for u in all_users:
        if hasattr(u, "userprofile") and u.userprofile.department:
            departments[u.userprofile.department].append(u)

    context = {
        'documents': page_obj,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'paginator': paginator,
        'departments': dict(departments),
        'search_query': search_query,
        'per_page': per_page,
        
        # Summary stats for cards
        'total_count': total_count,
        'pending_count': pending_count,
        'in_transit_count': in_transit_count,
        'received_count': received_count,
        'returned_count': returned_count,
        'completed_count': completed_count,
        'high_priority_count': high_priority_count,
        
        # Alert panel data
        'high_priority_docs': high_priority_docs,
        'pending_docs': pending_docs,
        'in_transit_docs': in_transit_docs,
    }
    return render(request, 'all_documents.html', context)


@login_required
def complete_document(request, pk):
    document = get_object_or_404(Document, pk=pk)

    # Only allow if current user is NOT the sender/creator
    if document.sender == request.user:
        messages.error(request, "You cannot finalize a document you created.")
        return redirect('document_detail', pk=document.pk)

    if request.method == "POST":
        # Mark the document as completed
        document.mark_completed(completed_by=request.user, note="Finalized via modal")

        # Notify the document creator
        if document.sender != request.user:  # safety check
            notify(
                document.sender,
                f"Your document {document.title} with tracking ID {document.tracking_id} was finalized by {request.user.get_full_name()}.",
                url=reverse("document_detail", kwargs={"pk": document.pk})
            )

        messages.success(request, f"Document {document.title} with tracking ID {document.tracking_id} has been finalized.")
        return redirect('document_detail', pk=document.pk)

    # If someone tries GET request, just redirect
    return redirect('document_detail', pk=document.pk)


@login_required
def completed_documents(request):
    user = request.user
    priority_filter = request.GET.get('priority', 'All')
    sender_filter = request.GET.get('sender', 'All')
    search_query = request.GET.get('q', '')

    # Admins/superusers see ALL completed documents
    if user.is_staff or user.is_superuser:
        documents_qs = Document.objects.filter(status='Completed').order_by('-created_at')
    else:
        completed_docs_ids = DocumentHistory.objects.filter(
            action="Completed",
            performed_by=user
        ).values_list('document_id', flat=True)

        documents_qs = Document.objects.filter(
            Q(status='Completed', sender=user) | Q(id__in=completed_docs_ids)
        ).order_by('-created_at')

    # Store unfiltered qs for counts (before priority/sender filters)
    base_qs = documents_qs

    # Apply priority filter
    if priority_filter != 'All':
        documents_qs = documents_qs.filter(priority=priority_filter)

    # Apply sender filter
    if sender_filter != 'All':
        documents_qs = documents_qs.filter(sender_id=sender_filter)

    # Apply search filter
    if search_query:
        documents_qs = documents_qs.filter(
            Q(tracking_id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query)
        )

    paginator = Paginator(documents_qs, 15)
    page_number = request.GET.get('page')
    documents = paginator.get_page(page_number)

    if user.is_staff or user.is_superuser:
        all_senders = User.objects.filter(document__status='Completed').distinct()
    else:
        all_senders = User.objects.filter(document__status='Completed').distinct()

    context = {
        'documents': documents,
        'priority_filter': priority_filter,
        'search_query': search_query,
        'sender_filter': sender_filter,
        'all_senders': all_senders,
        'high_count': base_qs.filter(priority='High').count(),
        'medium_count': base_qs.filter(priority='Medium').count(),
        'low_count': base_qs.filter(priority='Low').count(),
    }
    return render(request, 'completed_documents.html', context)


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

        messages.success(request, "Document registered successfully.")
        return redirect("dashboard")
    
    # No need to pass 'users' if they are not used in the form
    return render(request, 'new_document.html')

@login_required
def edit_document(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if document.sender != request.user:
        messages.error(request, "You are not authorized to edit this document.")
        return redirect("document_detail", pk=pk)

    if document.status == "Completed":
        messages.error(request, "Completed documents can no longer be edited.")
        return redirect("document_detail", pk=pk)

    if document.history.filter(action="Forwarded").exists():
        messages.error(request, "This document can no longer be edited after forwarding.")
        return redirect("document_detail", pk=pk)

    if request.method == "POST":
        document.title = request.POST.get("title")
        document.priority = request.POST.get("priority")
        document.description = request.POST.get("description")
        document.save()

        DocumentHistory.objects.create(
            document=document,
            action="Edited",
            performed_by=request.user,
            note="Document metadata updated"
        )

        messages.success(request, "Document updated successfully.")
        return redirect("document_detail", pk=pk)


@login_required
def edit_document_modal(request, pk):
    if request.method != "GET":
        return HttpResponse(status=405)

    document = get_object_or_404(Document, pk=pk)

    if document.sender != request.user or document.status == "Completed":
        return HttpResponse(status=403)

    return render(
        request,
        "documents/partials/edit_document_form.html",
        {"document": document}
    )




@login_required(login_url='loginpage')
def delete_document(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        Notification.objects.filter(
            url=f"/documents/{document.pk}/"
        ).delete()

        document.delete()
        messages.success(request, "Document successfully deleted.")
        return redirect("all_documents")

    messages.error(request, "Invalid request.")
    return redirect("all_documents")


@login_required
def document_detail(request, pk):
    document = Document.objects.filter(pk=pk).first()
    if not document:
        messages.warning(request, "This document no longer exists.")
        return redirect("all_documents")

    # Authorization check — allow superusers and staff to view any document
    if not (request.user.is_staff or request.user.is_superuser):
        if request.user != document.sender and request.user != document.current_office:
            messages.error(request, "You are not authorized to view this document.")
            return redirect("all_documents")
        
    departments = defaultdict(list)
    all_users = User.objects.select_related("userprofile").all()
    for u in all_users:
        if hasattr(u, "userprofile") and u.userprofile.department:
            departments[u.userprofile.department].append(u)

    forwards = document.history.filter(action="Forwarded").order_by("-timestamp")
    prev_forward = forwards[1] if forwards.count() > 1 else None
    return_target = prev_forward.to_office if prev_forward else document.sender if forwards.exists() else None

    history = document.history.order_by("-timestamp")

    # Can retract if last forward exists and has not been received
    last_forward = document.history.filter(action="Forwarded").order_by('-timestamp').first()
    can_retract = last_forward and not document.history.filter(
        action="Received", timestamp__gte=last_forward.timestamp
    ).exists() and document.current_office == request.user

    # Can forward if user is current holder, not completed, and not retractable
    can_forward = document.current_office == request.user and document.status != "Completed" and not can_retract

    # 🔹 Offices that previously handled the document (for return dropdown)
    previous_offices = (
        document.history
        .filter(action__in=["Forwarded", "Returned", "Received"])
        .exclude(from_office__isnull=True)
        .values_list("from_office", flat=True)
        .distinct()
    )

    return_offices = User.objects.filter(
        id__in=previous_offices
    ).exclude(id=document.current_office_id)


    context = {
        "document": document,
        "history": history,
        "departments": dict(departments),
        "return_target": return_target,
        "can_retract": can_retract,
        "can_forward": can_forward,
        "return_offices": return_offices,
    }

    return render(request, "document_detail.html", context)


@login_required
def forward_document(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        new_office_id = request.POST.get("new_office")
        note = request.POST.get("note")

        new_office_user = get_object_or_404(User, id=new_office_id)

        # Prevent forwarding to self
        if new_office_user == request.user:
            messages.error(request, "You cannot forward the document to yourself.")
            return redirect("document_detail", pk=pk)

        # Use model method you already created
        document.forward_to(
            new_office=new_office_user,
            forwarded_by=request.user,
            note=note
        )

        # Notify the receiving office (if not self)
        if new_office_user != request.user:
            notify(
                new_office_user,
                f"Document {document.title} with tracking ID {document.tracking_id} was forwarded to you by {request.user.get_full_name()}.",
                url=reverse("receive_page")
            )

        # Notify sender if it's not the same as the new office
        # if document.sender != new_office_user:
        #     notify(
        #         document.sender,
        #         f"Your document {document.title} with tracking ID {document.tracking_id} was forwarded to {new_office_user.get_full_name()}."
        #     )


        messages.success(request, "Document forwarded successfully.")
        return redirect("document_detail", pk=pk)

    messages.error(request, "Invalid request.")
    return redirect("document_detail", pk=pk)


@login_required
def retract_document(request, pk):
    document = get_object_or_404(Document, pk=pk)

    # Only the current holder can retract
    if request.user != document.current_office:
        messages.error(request, "Only the current document holder can retract this document.")
        return redirect("document_detail", pk=pk)

    # Find the last forward action
    last_forward = document.history.filter(action="Forwarded").order_by('-timestamp').first()
    if not last_forward:
        messages.error(request, "This document has not been forwarded yet, so it cannot be retracted.")
        return redirect("document_detail", pk=pk)

    # Check if the document has been received by the wrong recipient
    received_after_forward = document.history.filter(
        action="Received", timestamp__gte=last_forward.timestamp
    ).exists()
    if received_after_forward:
        messages.error(request, "This document has already been received and cannot be retracted.")
        return redirect("document_detail", pk=pk)

    # Mark the last forward as retracted (instead of deleting it)
    last_forward.action = "Retracted"
    last_forward.note = f"Retracted by {request.user.get_full_name()}"
    last_forward.save()

    # Keep document with current holder and reset status so it can be forwarded again
    document.current_office = request.user
    document.status = "Pending"  # or whatever status indicates ready to forward
    document.save()

    messages.success(request, f"The last forward of document '{document.title}' has been successfully retracted.")
    return redirect("document_detail", pk=pk)



@login_required
def return_document(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("document_detail", pk=pk)

    # Only current holder can return
    if document.current_office != request.user:
        messages.error(request, "You are not authorized to return this document.")
        return redirect("document_detail", pk=pk)

    note = request.POST.get("note", "").strip()
    return_office_id = request.POST.get("return_to")

    # 🔹 Get all previous offices from history (safe options)
    previous_offices = (
        document.history
        .filter(action__in=["Forwarded", "Returned", "Received"])
        .exclude(from_office__isnull=True)
        .values_list("from_office", flat=True)
        .distinct()
    )

    allowed_offices = User.objects.filter(
        id__in=previous_offices
    ).exclude(id=request.user.id)

    if not return_office_id:
        messages.error(request, "Please select an office to return the document to.")
        return redirect("document_detail", pk=pk)

    # 🔐 Validate selected office
    return_office = get_object_or_404(
        User,
        id=return_office_id,
        id__in=allowed_offices.values_list("id", flat=True)
    )

    # ✅ Update document
    document.current_office = return_office
    document.status = "In Transit"
    document.save()

    # 🧾 Log history
    DocumentHistory.objects.create(
        document=document,
        action="Returned",
        from_office=request.user,
        to_office=return_office,
        performed_by=request.user,
        note=note or "Returned to selected office"
    )

    # 🔔 Notify receiving office
    notify(
        return_office,
        f"Document {document.title} with tracking ID {document.tracking_id} "
        f"was returned to you by {request.user.get_full_name()}.",
        url=reverse("receive_page")
    )

    messages.success(
        request,
        f"Document {document.title} with tracking ID {document.tracking_id} "
        f"was returned to {return_office.get_full_name()}."
    )

    return redirect("document_detail", pk=pk)




@login_required
def receive_page(request):
    # Get the latest "Forwarded" or "Returned" action to this user
    latest_routing_subquery = DocumentHistory.objects.filter(
        document=OuterRef('pk'),
        action__in=["Forwarded", "Returned"],
        to_office=request.user
    ).order_by('-timestamp')

    # Annotate document with latest routing info
    incoming = Document.objects.annotate(
        latest_routing_action=Subquery(latest_routing_subquery.values('action')[:1]),
        latest_routing_from_office_id=Subquery(latest_routing_subquery.values('from_office')[:1]),
        latest_routing_timestamp=Subquery(latest_routing_subquery.values('timestamp')[:1])
    ).filter(
        status="In Transit",  # only documents currently "in transit"
        latest_routing_from_office_id__isnull=False
    ).order_by('-latest_routing_timestamp')

    # Fetch actual User objects
    user_ids = [doc.latest_routing_from_office_id for doc in incoming]
    users_map = {u.id: u for u in User.objects.filter(id__in=user_ids)}

    # Attach User objects to documents
    for doc in incoming:
        doc.forwarded_from_office = users_map.get(doc.latest_routing_from_office_id)

    context = {"incoming": incoming}
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

   # Get the last routing action (Forwarded OR Returned)
    last_routing = document.history.filter(
        action__in=["Forwarded", "Returned"]
    ).order_by("-timestamp").first()

    if not last_routing:
        messages.error(request, "This document has not been routed to any office yet.")
        return redirect("receive_page")

    # Check if the logged-in user is the intended receiver
    if request.user != last_routing.to_office:
        messages.error(
            request,
            f"You are not authorized to receive this document. "
            f"This document is assigned to {last_routing.to_office.get_full_name()}."
        )
        return redirect("receive_page")

    
    # Suppose this is after receiving the document
    document_detail_url = reverse('document_detail', kwargs={'pk': document.pk})

    # Get who forwarded the document here
    last_action = document.history.filter(
        to_office=request.user,
        action__in=["Forwarded", "Returned"]
    ).order_by("-timestamp").first()

    from_office = last_action.from_office if last_action else None

    # Update the document
    document.current_office = request.user
    document.status = "Received"
    document.save()

    # Log history properly
    DocumentHistory.objects.create(
        document=document,
        action="Received",
        from_office=from_office,
        to_office=request.user,
        performed_by=request.user,
        note="Received via QR/manual entry"
    )
    
    # Send notifications
    notify(
        document.sender,
        f"Document {document.title} with tracking ID {document.tracking_id} was received by {request.user.get_full_name()}.",
        url=document_detail_url
    )

    messages.success(request, f"Document {document.title} with tracking ID {document.tracking_id} received successfully.")
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
def mark_all_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid method'}, status=405)

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

@login_required
def add_status(request, document_id):
    # Get the document
    document = get_object_or_404(Document, pk=document_id)

    # Only the current holder can add a status
    if request.user != document.current_office:
        messages.error(request, "You are not authorized to add a status to this document.")
        return redirect("document_detail", pk=document.pk)

    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        if not note:
            messages.error(request, "Status note cannot be empty.")
            return redirect("document_detail", pk=document.pk)

        # Add the status
        try:
            document.add_status_update(by_user=request.user, note=note)
            messages.success(request, "Status update added successfully.")
        except Exception as e:
            messages.error(request, f"Failed to add status: {str(e)}")

        return redirect("document_detail", pk=document.pk)

    # If GET request, just redirect back
    return redirect("document_detail", pk=document.pk)



# REPORTS generation view

@login_required
def document_report_api(request, report_type):
    today = timezone.now()
    report_data = []

    user = request.user
    document_id = request.GET.get("document_id")  # single document option

    # --- SINGLE DOCUMENT LOGIC ---
    if document_id:
        document = Document.objects.filter(
            id=document_id
        ).filter(
            Q(sender=user) | Q(current_office=user)
        ).first()

        if not document:
            return JsonResponse({"error": "Document not found or access denied."}, status=404)

        histories = DocumentHistory.objects.select_related(
            "document", "from_office", "to_office", "performed_by"
        ).filter(document=document).order_by("timestamp")

    else:
        # --- Determine date range ---
        if report_type == "weekly":
            start_date = request.GET.get("start")
            end_date = request.GET.get("end")
            if start_date and end_date:
                start_date = datetime.fromisoformat(start_date)
                end_date = datetime.fromisoformat(end_date) + timedelta(days=1)
            else:
                start_date = today - timedelta(days=7)
                end_date = today
        elif report_type == "monthly":
            month_year = request.GET.get("month_year")
            if month_year:
                year, month = map(int, month_year.split("-"))
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)
            else:
                start_date = today - timedelta(days=30)
                end_date = today
        else:
            return JsonResponse({"error": "Invalid report type"}, status=400)

        histories = DocumentHistory.objects.select_related(
            "document", "from_office", "to_office", "performed_by"
        ).filter(
            timestamp__gte=start_date,
            timestamp__lt=end_date
        ).filter(
            Q(document__sender=user) |
            Q(document__current_office=user) |
            Q(from_office=user) |
            Q(to_office=user) |
            Q(performed_by=user)
        ).order_by("document", "timestamp")

    # --- Prepare report ---
    for h in histories:
        next_h = DocumentHistory.objects.filter(
            document=h.document,
            timestamp__gt=h.timestamp
        ).order_by("timestamp").first()

        # Calculate days:hours:minutes:seconds
        delta = (next_h.timestamp - h.timestamp) if next_h else (timezone.now() - h.timestamp)
        total_seconds = int(delta.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        days_stayed_str = f"{days}d {hours}h {minutes}m {seconds}s"

        report_data.append({
            "tracking_id": h.document.tracking_id,
            "title": h.document.title,
            "action": h.action,
            "from_office": h.from_office.get_full_name() if h.from_office else "",
            "to_office": h.to_office.get_full_name() if h.to_office else "",
            "performed_by": h.performed_by.get_full_name() if h.performed_by else "",
            "timestamp": h.timestamp.strftime("%b %d, %Y %H:%M"),
            "days_stayed": days_stayed_str,
            "note": h.note or ""
        })

    # --- Export handling ---
    export = request.GET.get("export")
    filename_prefix = 'single_document' if document_id else report_type

    if export == "excel":
        df = pd.DataFrame(report_data)
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        response = HttpResponse(
            buffer,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename={filename_prefix}_report_{today.strftime("%Y%m%d")}.xlsx'
        return response

    if export == "pdf":
        html = render_to_string("reports/report_pdf_template.html", {
            "report_data": report_data,
            "report_type": f"Document: {document.title}" if document_id else report_type
        })
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={filename_prefix}_report_{today.strftime("%Y%m%d")}.pdf'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse("Error generating PDF", status=500)
        return response

    return JsonResponse({"report_data": report_data})