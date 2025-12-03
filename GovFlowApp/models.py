import qrcode
from io import BytesIO
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files import File


class UserProfile(models.Model):
    DEPARTMENT_CHOICES = [
        ("Medical Service", "Medical Service"),
        ("Allied Health Professional Service", "Allied Health Professional Service"),
        ("Nursing Service", "Nursing Service"),
        ("Hospital Operations and Patient Support Services", "Hospital Operations and Patient Support Services"),
        ("Finance Service", "Finance Service"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(
        max_length=100,
        choices=DEPARTMENT_CHOICES,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Document(models.Model):
    PRIORITY_CHOICES = [
        ("High", "Urgent"),
        ("Medium", "Standard"),
        ("Low", "Routine"),
    ]

    tracking_id = models.CharField(max_length=15, unique=True, editable=False)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)  # Document title
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="Medium")
    description = models.TextField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    current_location = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.tracking_id} - {self.title}"

    def save(self, *args, **kwargs):
        # Generate tracking ID if not set
        if not self.tracking_id:
            current_year = timezone.now().year
            last_doc = Document.objects.filter(tracking_id__startswith=f"TR-{current_year}").order_by("id").last()
            next_number = int(last_doc.tracking_id[-5:]) + 1 if last_doc else 1
            self.tracking_id = f"TR-{current_year}-{next_number:05d}"

        # Set current_location automatically if not set
        if not self.current_location:
            dept = getattr(getattr(self.sender, 'userprofile', None), 'department', None)
            self.current_location = dept or "Office of Origin"

        super().save(*args, **kwargs)  # Save to get ID

        # Generate/update QR code every save
        qr_data = (
            f"Tracking ID: {self.tracking_id}\n"
            f"Title: {self.title}\n"
            f"Sender: {self.sender.get_full_name() if self.sender else 'N/A'}\n"
            f"Priority: {self.get_priority_display()}\n"
            f"Description: {self.description}\n"
            f"Current Location: {self.current_location or 'N/A'}"
        )

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        file_name = f"QR_{self.tracking_id}.png"

        self.qr_code.save(file_name, File(buffer), save=False)
        buffer.close()

        super().save(update_fields=["qr_code"])

    # Forward document to another location
    def forward_to(self, new_location, forwarded_by=None):
        old_location = self.current_location
        self.current_location = new_location
        self.save(update_fields=["current_location"])

        DocumentHistory.objects.create(
            document=self,
            action="Forwarded",
            from_location=old_location,
            to_location=new_location,
            performed_by=forwarded_by or self.sender
        )

    # Mark document as received
    def mark_received(self, receiving_office, received_by=None):
        self.current_location = receiving_office
        self.received_at = timezone.now()
        self.save(update_fields=["current_location", "received_at"])

        DocumentHistory.objects.create(
            document=self,
            action="Received",
            from_location=None,
            to_location=receiving_office,
            performed_by=received_by
        )


class DocumentHistory(models.Model):
    ACTION_CHOICES = [
        ("Forwarded", "Forwarded"),
        ("Received", "Received"),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    from_location = models.CharField(max_length=200, blank=True, null=True)
    to_location = models.CharField(max_length=200, blank=True, null=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.tracking_id} - {self.action} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
