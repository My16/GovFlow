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
from django.urls import reverse

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

    # Base queryset: ONLY documents user can access
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
        search_query = ""  # clear the query so template shows no search

    # Summary counts (based on filtered documents)
    total_documents = user_documents.count()
    in_progress = user_documents.filter(received_at__isnull=True).count()
    received = user_documents.filter(received_at__isnull=False).count()
    high_priority = user_documents.filter(priority='High').count()

    # Recent documents (search-aware)
    if search_query:
        recent_documents = user_documents.order_by('-created_at')
    else:
        recent_documents = user_documents.order_by('-created_at')[:6]


    # Departments for forwarding
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
    # Get documents where user is sender OR current office
    documents = Document.objects.filter(
        Q(sender=request.user) | Q(current_office=request.user)
    ).order_by('-created_at')

     # Filters
    status_filter = request.GET.get('status', 'All')
    priority_filter = request.GET.get('priority', 'All')
    search_query = request.GET.get('q', '').strip()  # search query

    # Apply filters
    if priority_filter != 'All':
        documents = documents.filter(priority=priority_filter)
    if status_filter != 'All':
        documents = documents.filter(status=status_filter)

    # Apply search only if >=3 characters
    if len(search_query) >= 3:
        documents = documents.filter(
            Q(tracking_id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query)
        )
    else:
        search_query = ""  # clear so template knows no search

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(documents, 15)  # 15 documents per page
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
        'search_query': search_query,
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



from django.db.models import Q

@login_required
def completed_documents(request):
    # Get filter from query params (priority)
    priority_filter = request.GET.get('priority', 'All')
    search_query = request.GET.get('q', '')  # Global search

    # Base queryset: only Completed documents
    documents_qs = Document.objects.filter(status='Completed').order_by('-created_at')

    # Apply priority filter if selected
    if priority_filter != 'All':
        documents_qs = documents_qs.filter(priority=priority_filter)

    # Apply search filter
    if search_query:
        documents_qs = documents_qs.filter(
            Q(tracking_id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(documents_qs, 15)  # 15 per page
    page_number = request.GET.get('page')
    documents = paginator.get_page(page_number)

    context = {
        'documents': documents,
        'priority_filter': priority_filter,
        'search_query': search_query,  # Pass this to template
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

    # Authorization check
    if request.user != document.sender and request.user != document.current_office:
        messages.error(request, "You are not authorized to view this document.")
        return redirect("all_documents")

    from collections import defaultdict
    departments = defaultdict(list)

    all_users = User.objects.select_related("userprofile").all()
    for u in all_users:
        if hasattr(u, "userprofile") and u.userprofile.department:
            departments[u.userprofile.department].append(u)

    forwards = document.history.filter(action="Forwarded").order_by("-timestamp")

    if forwards.exists():
        prev_forward = forwards[1] if forwards.count() > 1 else None
        return_target = prev_forward.to_office if prev_forward else document.sender
    else:
        return_target = None

    history = document.history.order_by("-timestamp")

    context = {
        "document": document,
        "history": history,
        "departments": dict(departments),
        "return_target": return_target,
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

    # Find the last action that sent this document to the current office
    last_received_action = document.history.filter(
        to_office=request.user,
        action__in=["Forwarded", "Returned"]
    ).order_by("-timestamp").first()

    if not last_received_action:
        messages.error(request, "Cannot determine where to return this document.")
        return redirect("document_detail", pk=pk)

    return_office = last_received_action.from_office or document.sender

    # Update document
    document.current_office = return_office
    document.status = "In Transit"
    document.save()

    # Log history
    DocumentHistory.objects.create(
        document=document,
        action="Returned",
        from_office=request.user,
        to_office=return_office,
        performed_by=request.user,
        note=note or "Returned to previous office"
    )

    # Notify receiving office
    if return_office != request.user:
        notify(
            return_office,
            f"Document {document.title} with tracking ID {document.tracking_id} was returned to you by {request.user.get_full_name()}.",
            url=reverse("receive_page")
        )

    # Notify sender if sender is not the return office (to avoid double)
    # if document.sender != return_office:
    #     notify(
    #         document.sender,
    #         f"Document {document.title} with tracking ID {document.tracking_id} was returned to {return_office.get_full_name()}."
    #     )

    messages.success(request, f"Document {document.title} with tracking ID {document.tracking_id} was returned to {return_office.get_full_name()}.")
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