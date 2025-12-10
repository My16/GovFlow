import qrcode
from io import BytesIO
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files import File
from django.db.models.signals import pre_save, post_delete, post_save
from django.dispatch import receiver


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

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("In Transit", "In Transit"),
        ("Received", "Received"),
        ("Returned", "Returned"),
        ("Archived", "Archived"),
    ]

    tracking_id = models.CharField(max_length=15, unique=True, editable=False)
    sender = models.ForeignKey(User, on_delete=models.PROTECT)
    title = models.CharField(max_length=255)  # Document title
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="Medium")
    description = models.TextField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    current_office = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="current_documents")
    created_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.tracking_id} - {self.title}"

    def save(self, *args, **kwargs):
        # Generate tracking ID if not set
        if not self.tracking_id:
            current_year = timezone.now().year
            last_doc = Document.objects.filter(tracking_id__startswith=f"TRK-{current_year}").order_by("id").last()
            next_number = int(last_doc.tracking_id[-5:]) + 1 if last_doc else 1
            self.tracking_id = f"TRK-{current_year}-{next_number:05d}"

        # Set current_office automatically if not set
        if not self.current_office:
            self.current_office = self.sender  # default to sender

        # Generate QR code before saving
        qr_data = (
            f"Tracking ID: {self.tracking_id}\n"
            f"Title: {self.title}\n"
            f"Sender: {self.sender.get_full_name() if self.sender else 'N/A'}\n"
            f"Priority: {self.get_priority_display()}\n"
            f"Status: {self.status}\n"
            f"Description: {self.description}\n"
            f"Current Office: {self.current_office.get_full_name() if self.current_office else 'N/A'}"
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

        # Attach QR code to instance but don't save yet
        self.qr_code.save(file_name, File(buffer), save=False)
        buffer.close()

        # Save the instance once
        super().save(*args, **kwargs)

    # Forward document to another location
    def forward_to(self, new_office, forwarded_by=None, note=None):
        old_office = self.current_office
        self.current_office = new_office
        self.status = "In Transit"  # <-- update status
        self.save(update_fields=["current_office", "status"])

        DocumentHistory.objects.create(
            document=self,
            action="Forwarded",
            from_office=old_office,
            to_office=new_office,
            note=note,
            performed_by=forwarded_by or self.sender
        )


    def mark_received(self, receiving_office, received_by=None, note=None):
        old_office = self.current_office
        self.current_office = receiving_office
        self.status = "Received"
        self.received_at = timezone.now()
        self.save(update_fields=["current_office", "received_at", "status"])

        DocumentHistory.objects.create(
            document=self,
            action="Received",
            from_office=old_office,
            to_office=receiving_office,
            note=note,
            performed_by=received_by
        )

    def return_document(self, return_to_office, returned_by=None, note=None):
        old_office = self.current_office
        self.current_office = return_to_office
        self.status = "Returned"  # <-- update status
        self.save(update_fields=["current_office", "status"])

        DocumentHistory.objects.create(
            document=self,
            action="Returned",
            from_office=old_office,
            to_office=return_to_office,
            note=note,
            performed_by=returned_by
        )

# Signal to delete old QR code when updating
@receiver(pre_save, sender=Document)
def delete_old_qr_code_file(sender, instance, **kwargs):
    if not instance.pk:
        return  # skip if new instance
    try:
        old_instance = Document.objects.get(pk=instance.pk)
    except Document.DoesNotExist:
        return
    if old_instance.qr_code and old_instance.qr_code != instance.qr_code:
        old_instance.qr_code.delete(save=False)

# Signal to delete QR code file when deleting the Document
@receiver(post_delete, sender=Document)
def delete_qr_code_file(sender, instance, **kwargs):
    if instance.qr_code:
        instance.qr_code.delete(save=False)

class DocumentHistory(models.Model):
    ACTION_CHOICES = [
        ("Pending", "Pending"),
        ("Forwarded", "Forwarded"),
        ("Received", "Received"),
        ("Returned", "Returned"),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    from_office = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="history_from")
    to_office = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="history_to")
    note = models.TextField(blank=True, null=True)  # ⬅️ Optional forwarding/return/receive note
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.tracking_id} - {self.action} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

@receiver(post_save, sender=Document)
def create_initial_history(sender, instance, created, **kwargs):
    if created:
        DocumentHistory.objects.create(
            document=instance,
            action=instance.status,
            from_office=None,
            to_office=instance.current_office,  # store the user object
            note="Document created",
            performed_by=instance.sender
        )