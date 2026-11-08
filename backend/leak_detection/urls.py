from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # User URLs
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('upload/', views.upload_image, name='upload_image'),
    path('check-leaks/', views.check_leaks, name='check_leaks'),
    path('run-scan/<int:image_id>/', views.run_scan, name='run_scan'),
    path('report/', views.leak_report, name='leak_report'),
    
    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('add-officer/', views.add_officer, name='add_officer'),
    path('view-officers/', views.view_officers, name='view_officers'),
    path('toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('admin-scan/<int:user_id>/', views.admin_leak_detection, name='admin_leak_detection'),
    path('admin-run-scan/<int:image_id>/', views.admin_run_scan, name='admin_run_scan'),
    path('global-report/', views.global_leak_report, name='global_report'),
    path('assign-user/<int:user_id>/', views.assign_user_case, name='assign_user_case'),
    
    # Complaints
    path('my-complaints/', views.user_view_complaints, name='user_view_complaints'),
    path('add-complaint/', views.add_complaint, name='add_complaint'),
    path('view-complaints/', views.view_complaints, name='view_complaints'),
    path('assign-complaint/<int:complaint_id>/', views.assign_complaint_case, name='assign_complaint_case'),
    
    # Fake Apps URLs
    path('fake-app/social-media/', views.fake_social_media, name='fake_social_media'),
    path('fake-app/news-portal/', views.fake_news_portal, name='fake_news_portal'),
    path('fake-app/dating-app/', views.fake_dating_app, name='fake_dating_app'),
    
    # Mask Action
    path('mask-image/<int:result_id>/', views.mask_image, name='mask_image'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
