import os
import glob
import re
from django.conf import settings
from .models import LeakScanResult

def get_images_shown_in_templates():
    """
    Parses the fake app templates to find which images are actually being displayed.
    """
    templates_dir = os.path.join(settings.BASE_DIR, 'templates', 'fake_apps')
    shown_images = set()
    
    if not os.path.exists(templates_dir):
        return shown_images

    # Support patterns like: {{ MEDIA_URL }}fake_apps/dating_app/fake_profile.jpg
    # Stopping at quotes or template tags '{%'
    img_pattern = re.compile(r'(?:MEDIA_URL\s*\}\}|/media/)(fake_apps/[^"\'\'{]+)')

    for template_file in glob.glob(os.path.join(templates_dir, '*.html')):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = img_pattern.findall(content)
                for match in matches:
                    # Clean up the path and normalize
                    clean_path = match.strip().replace('/', os.sep)
                    shown_images.add(clean_path)
        except Exception as e:
            print(f"Error parsing template {template_file}: {e}")
            
    return shown_images

def scan_for_leaks(user, uploaded_image):
    """
    Compares user's uploaded_image against images in the fake apps media directories,
    but only if they are actually shown in the fake app templates.
    """
    try:
        from deepface import DeepFace
        has_deepface = True
    except ImportError:
        has_deepface = False
        print("CRITICAL: DeepFace library not found. ML-based privacy scanning is disabled.")
    
    if not has_deepface:
        return

    source_img_path = uploaded_image.image.path
    shown_image_rel_paths = get_images_shown_in_templates()
    
    # Mapping of directory names to readable App labels
    app_label_map = {
        'social_media': 'Social Media App',
        'news_portal': 'News Portal',
        'dating_app': 'Dating App'
    }
    
    # Clear previous scans for this exactly image to avoid duplicates
    LeakScanResult.objects.filter(target_image=uploaded_image).delete()
    
    for rel_path in shown_image_rel_paths:
        # rel_path is like 'fake_apps\dating_app\fake_profile.jpg'
        full_target_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        
        if not os.path.exists(full_target_path):
            continue
            
        # Determine app name from path
        parts = rel_path.split(os.sep)
        app_slug = parts[1] if len(parts) > 1 else 'Unknown'
        app_name = app_label_map.get(app_slug, app_slug.replace('_', ' ').title())
        
        try:
            result = DeepFace.verify(img1_path=source_img_path, img2_path=full_target_path, enforce_detection=False)
            is_match = result.get('verified', False)
            distance = result.get('distance', 1.0)
            confidence = max(0, 100 - (distance * 100))
            
            if is_match:
                # Result in relative path for web display
                web_path = f"{settings.MEDIA_URL}{rel_path.replace(os.sep, '/')}"
                LeakScanResult.objects.create(
                    user=user,
                    target_image=uploaded_image,
                    source_app_name=app_name,
                    matched_image_path=web_path,
                    confidence_score=round(confidence, 2),
                    is_leaked=True
                )
        except Exception as e:
            print(f"Error comparing images: {str(e)}")
            continue
