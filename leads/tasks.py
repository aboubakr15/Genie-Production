from celery import shared_task
from main.models import Sheet, Notification, User
from main.utils import send_websocket_message, NOTIFICATIONS_STATES
from IBH import settings
from django.core.files.storage import FileSystemStorage
import os
from datetime import datetime

@shared_task
def process_uploaded_sheet_for_leads(file_path, original_filename, user_id):
    """
    Celery task to save an uploaded sheet and notify the team leader.
    """
    try:
        user = User.objects.get(id=user_id)
        
        # The file is already saved in a temporary location by the view.
        # This task will move it to the final destination and create the notification.
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'upload')
        os.makedirs(upload_dir, exist_ok=True)
        
        fs = FileSystemStorage(location=upload_dir)
        filename = fs.save(original_filename, open(file_path, 'rb'))
        
        # Create or get the sheet
        sheet, created = Sheet.objects.get_or_create(
            name=filename,
            defaults={'user': user, 'created_at': datetime.now()}
        )
        
        # Create a notification for the team leader
        ops_tl = user.leader.leader
        notification = Notification.objects.create(
            sender=user,
            receiver=ops_tl,
            message=f'sheet {sheet.name} uploaded',
            notification_type=0,
            read=False
        )
        notification.sheets.set([sheet])
        notification.save()
        
        send_websocket_message(ops_tl.id, notification.id, notification.message, notification.read, NOTIFICATIONS_STATES['INFO'])
        
        print(f"Sheet '{original_filename}' uploaded and notification sent for user {user.username}.")
        
        # Clean up the temporary file
        os.remove(file_path)

    except Exception as e:
        print(f"Error processing uploaded sheet for leads: {e}")
