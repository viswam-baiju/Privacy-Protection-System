from django.contrib import admin
from .models import UploadedImage, LeakScanResult

admin.site.register(UploadedImage)
admin.site.register(LeakScanResult)
