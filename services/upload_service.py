import os
from datetime import datetime
from uuid import uuid4

from werkzeug.utils import secure_filename

from models import Attachment, db

ALLOWED_UPLOAD_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def save_ticket_attachments(app, ticket, files):
    for photo in files:
        if not photo or not photo.filename:
            continue
        if not allowed_file(photo.filename):
            continue

        ext = photo.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex}.{ext}"
        safe_name = secure_filename(unique_name)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        photo.save(save_path)

        db.session.add(
            Attachment(
                ticket=ticket,
                file_url=f'uploads/{safe_name}',
                uploaded_at=datetime.utcnow(),
            )
        )
