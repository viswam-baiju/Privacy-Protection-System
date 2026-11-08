from django.db import models
from django.conf import settings

class UploadedImage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_images')
    image = models.ImageField(upload_to='user_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image by {self.user.username} at {self.uploaded_at}"

class LeakScanResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scan_results')
    target_image = models.ForeignKey(UploadedImage, on_delete=models.CASCADE, related_name='found_leaks')
    source_app_name = models.CharField(max_length=100) # e.g. "Fake Social Media"
    matched_image_path = models.CharField(max_length=255) # path to the leaked image
    confidence_score = models.FloatField()
    is_leaked = models.BooleanField(default=True)
    scan_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Leaked" if self.is_leaked else "No Match"
        return f"Scan for {self.user.username} - {status} in {self.source_app_name}"

class Complaint(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complaints')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Complaint #{self.id} - {self.subject} ({self.status})"
