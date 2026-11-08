from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import UploadedImage, LeakScanResult, Complaint
from .utils_face_rec import scan_for_leaks
from login.models import User
from django.db.models import Q
import os
from django.conf import settings

# ... (rest of the imports and user views)

@login_required
def add_complaint(request):
    if request.method == 'POST':
        subject = request.POST.get('subject')
        description = request.POST.get('description')
        
        if subject and description:
            Complaint.objects.create(
                user=request.user,
                subject=subject,
                description=description
            )
            messages.success(request, 'Your complaint has been submitted successfully.')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Please provide both a subject and a description.')
            
    return render(request, 'leak_detection/add_complaint.html')

@login_required
def user_view_complaints(request):
    user_complaints = Complaint.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'leak_detection/user_complaint_list.html', {'user_complaints': user_complaints})

@login_required
def view_complaints(request):
    # Only Admin (superuser) and Officers can view complaints
    if not (request.user.is_superuser or request.user.role == 'officer'):
        return redirect('user_dashboard')
        
    complaints = Complaint.objects.all().order_by('-created_at')
    if request.user.role == 'officer':
        complaints = complaints.filter(Q(user__place=request.user.place) | Q(assigned_officer=request.user))
    
    # Handle status updates
    if request.method == 'POST':
        complaint_id = request.POST.get('complaint_id')
        new_status = request.POST.get('status')
        if complaint_id and new_status:
            complaint = get_object_or_404(Complaint, id=complaint_id)
            complaint.status = new_status
            complaint.save()
            messages.success(request, f'Complaint #{complaint.id} status updated to {new_status}.')
            return redirect('view_complaints')

    officers = User.objects.filter(role=User.OFFICER)
    return render(request, 'leak_detection/complaint_list.html', {
        'complaints': complaints,
        'officers': officers
    })

# User Views
@login_required
def user_dashboard(request):
    images = UploadedImage.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'leak_detection/user_dashboard.html', {'images': images})

@login_required
def upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        UploadedImage.objects.create(
            user=request.user,
            image=request.FILES['image']
        )
        messages.success(request, 'Image uploaded successfully.')
        return redirect('user_dashboard')
    return render(request, 'leak_detection/upload_image.html')

@login_required
def check_leaks(request):
    images = UploadedImage.objects.filter(user=request.user)
    results = LeakScanResult.objects.filter(user=request.user).order_by('-scan_date')
    return render(request, 'leak_detection/check_leaks.html', {
        'images': images,
        'results': results
    })

@login_required
def run_scan(request, image_id):
    image = get_object_or_404(UploadedImage, id=image_id, user=request.user)
    # Run the face recognition utility
    scan_for_leaks(request.user, image)
    messages.success(request, f'Scan completed for image {image.id}')
    return redirect('check_leaks')

@login_required
def leak_report(request):
    results = LeakScanResult.objects.filter(user=request.user).order_by('-scan_date')
    return render(request, 'leak_detection/leak_report.html', {'results': results})

# Admin Views
@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.role == 'officer'):
        return redirect('user_dashboard')
    
    # Separate users and officers
    all_users = User.objects.all().exclude(is_superuser=True)
    if request.user.role == 'officer':
        all_users = all_users.filter(Q(place=request.user.place) | Q(assigned_officer=request.user))
        
    users = all_users.filter(role=User.USER)
    officers = all_users.filter(role=User.OFFICER)
    
    # attach image count to users
    for user in all_users:
        user.image_count = UploadedImage.objects.filter(user=user).count()
    
    total_leaks = LeakScanResult.objects.filter(is_leaked=True).count()
    return render(request, 'leak_detection/admin_dashboard.html', {
        'users': users,
        'officers': officers,
        'total_leaks': total_leaks
    })

@login_required
def add_officer(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        fullname = request.POST.get('fullname')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        age = request.POST.get('age')
        place = request.POST.get('place', '')

        try:
            age = int(age) if age else None
        except ValueError:
            age = None
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'User with this email already exists.')
        else:
            User.objects.create_user(
                email=email,
                fullname=fullname,
                password=password,
                phone=phone,
                age=age,
                place=place,
                role=User.OFFICER,
                is_staff=True # Officers can have staff access
            )
            messages.success(request, f'Officer {fullname} added successfully.')
            
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))

@login_required
def view_officers(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    officers = User.objects.filter(role=User.OFFICER).order_by('-date_joined')
    return render(request, 'leak_detection/officer_list.html', {'officers': officers})

@login_required
def admin_leak_detection(request, user_id):
    if not (request.user.is_superuser or request.user.role == 'officer'):
        return redirect('user_dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    if request.user.role == 'officer' and target_user.place != request.user.place and target_user.assigned_officer != request.user:
        messages.error(request, 'You do not have permission to view users outside your district.')
        return redirect('admin_dashboard')
        
    images = UploadedImage.objects.filter(user=target_user)
    results = LeakScanResult.objects.filter(user=target_user).order_by('-scan_date')
    leak_count = results.filter(is_leaked=True).count()
    
    if request.method == 'POST':
        for img in images:
            scan_for_leaks(target_user, img)
        messages.success(request, f'Scanned all images for {target_user.fullname or target_user.email}')
        return redirect('admin_leak_detection', user_id=target_user.id)
        
    return render(request, 'leak_detection/admin_leak_detection.html', {
        'target_user': target_user,
        'images': images,
        'results': results,
        'leak_count': leak_count
    })

@login_required
def global_leak_report(request):
    if not (request.user.is_superuser or request.user.role == 'officer'):
        return redirect('user_dashboard')
    results = LeakScanResult.objects.all().order_by('-scan_date')
    if request.user.role == 'officer':
        results = results.filter(Q(user__place=request.user.place) | Q(user__assigned_officer=request.user))
    return render(request, 'leak_detection/global_report.html', {'results': results})

@login_required
def admin_run_scan(request, image_id):
    if not (request.user.is_superuser or request.user.role == 'officer'):
        return redirect('user_dashboard')
        
    image = get_object_or_404(UploadedImage, id=image_id)
    if request.user.role == 'officer' and image.user.place != request.user.place and image.user.assigned_officer != request.user:
        messages.error(request, 'You are not authorized to scan images for users outside your district.')
        return redirect('admin_dashboard')
        
    scan_for_leaks(image.user, image)
    messages.success(request, f'Targeted scan completed for Evidence #{image.id}.')
    return redirect('admin_leak_detection', user_id=image.user.id)

@login_required
def toggle_user_status(request, user_id):
    if not request.user.is_superuser:
        return redirect('user_dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    
    # Toggle is_active
    target_user.is_active = not target_user.is_active
    
    # Sync status field
    if target_user.is_active:
        target_user.status = 'active'
        action = "unblocked"
        msg_type = messages.success
    else:
        target_user.status = 'blocked'
        action = "blocked"
        msg_type = messages.warning
        
    target_user.save()
    msg_type(request, f"User {target_user.email} has been {action}.")
    
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))

@login_required
def assign_user_case(request, user_id):
    if not request.user.is_superuser:
        return redirect('user_dashboard')
        
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)
        officer_id = request.POST.get('officer_id')
        if officer_id:
            officer = get_object_or_404(User, id=officer_id, role=User.OFFICER)
            target_user.assigned_officer = officer
        else:
            target_user.assigned_officer = None
        target_user.save()
        messages.success(request, f'Case assignment updated for {target_user.fullname or target_user.email}.')
        
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))

@login_required
def assign_complaint_case(request, complaint_id):
    if not request.user.is_superuser:
        return redirect('user_dashboard')
        
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, id=complaint_id)
        officer_id = request.POST.get('officer_id')
        if officer_id:
            officer = get_object_or_404(User, id=officer_id, role=User.OFFICER)
            complaint.assigned_officer = officer
        else:
            complaint.assigned_officer = None
        complaint.save()
        messages.success(request, f'Complaint #{complaint.id} assignment updated.')
        
    return redirect(request.META.get('HTTP_REFERER', 'view_complaints'))

# Fake App Views (Demo purposes)
def fake_social_media(request):
    return render(request, 'fake_apps/social_media.html')

def fake_news_portal(request):
    return render(request, 'fake_apps/news_portal.html')

def fake_dating_app(request):
    return render(request, 'fake_apps/dating_app.html')

# Mask Image Action
@login_required
def mask_image(request, result_id):
    """
    Mask the leaked image in the fake app by replacing it with a black/masked image.
    Only Admins and Officers can trigger this.
    """
    if not (request.user.is_superuser or request.user.role == 'officer'):
        messages.error(request, 'You do not have permission to mask images.')
        return redirect('user_dashboard')
        
    result = get_object_or_404(LeakScanResult, id=result_id)
    if request.user.role == 'officer' and result.user.place != request.user.place and result.user.assigned_officer != request.user:
        messages.error(request, 'You are not authorized to mask images for users outside your district.')
        return redirect('admin_dashboard')
        
    target_user_id = result.user.id
    
    # matched_image_path is like /media/fake_apps/dating_app/fake_profile.jpg
    # Convert it to an absolute path on disk
    rel_path = result.matched_image_path.lstrip('/')
    # Strip the MEDIA_URL prefix to get the relative path under MEDIA_ROOT
    media_url_stripped = settings.MEDIA_URL.lstrip('/')
    if rel_path.startswith(media_url_stripped):
        rel_path = rel_path[len(media_url_stripped):]
    
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    
    if not os.path.exists(full_path):
        messages.error(request, 'Image file not found on server.')
        return redirect('check_leaks')
    
    try:
        from PIL import Image, ImageFilter
        import shutil, time, numpy as np
        import cv2
        
        # Backup the original with a timestamp so it can be recovered if needed
        backup_path = full_path + f'.backup_{int(time.time())}'
        if not os.path.exists(backup_path):
            shutil.copy2(full_path, backup_path)
        
        # Open original image
        with Image.open(full_path) as orig:
            img_pil = orig.convert('RGB')
        
        img_np = np.array(img_pil)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Use OpenCV's built-in Haar Cascade for face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(30, 30)
        )
        
        if len(faces) == 0:
            # No face detected — fallback: blur full image
            for _ in range(8):
                img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=15))
            img_pil.save(full_path)
            messages.success(request, f'No face detected; full image blurred on {result.source_app_name}.')
        else:
            from deepface import DeepFace
            import tempfile
            
            # Get the user's reference photo (the image that was originally uploaded)
            reference_img_path = result.target_image.image.path
            
            matched_faces = 0
            
            for (x, y, w, h) in faces:
                # Padding around face bounding box (20%)
                pad_x = int(w * 0.2)
                pad_y = int(h * 0.2)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(img_pil.width, x + w + pad_x)
                y2 = min(img_pil.height, y + h + pad_y)
                
                # Crop this face to a temp file so DeepFace can compare it
                face_crop = img_pil.crop((x1, y1, x2, y2))
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                    face_crop.save(tmp_path, 'JPEG')
                
                try:
                    verify_result = DeepFace.verify(
                        img1_path=reference_img_path,
                        img2_path=tmp_path,
                        enforce_detection=False
                    )
                    is_match = verify_result.get('verified', False)
                except Exception:
                    is_match = False
                finally:
                    # Clean up temp file
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
                
                if is_match:
                    # Only blur THIS face
                    face_region = img_pil.crop((x1, y1, x2, y2))
                    for _ in range(10):
                        face_region = face_region.filter(ImageFilter.GaussianBlur(radius=15))
                    img_pil.paste(face_region, (x1, y1))
                    matched_faces += 1
            
            img_pil.save(full_path)
            
            if matched_faces > 0:
                messages.success(request, f'Your face blurred successfully on {result.source_app_name}.')
            else:
                messages.warning(request, f'Could not confidently identify your face in the image to blur it.')
    except ImportError:
        messages.error(request, 'Pillow library is required for masking. Install it with: pip install Pillow')
    except Exception as e:
        messages.error(request, f'Error masking image: {str(e)}')
    
    return redirect('admin_leak_detection', user_id=target_user_id)
