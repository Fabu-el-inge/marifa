import secrets
from datetime import datetime, date
from app.extensions import db


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    general_notes = db.Column(db.Text, nullable=True)
    public_token = db.Column(db.String(32), unique=True, nullable=False,
                             default=lambda: secrets.token_urlsafe(16))
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    musicians = db.relationship(
        'ShowMusician',
        backref='show',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    setlist_items = db.relationship(
        'SetlistItem',
        backref='show',
        lazy='dynamic',
        order_by='SetlistItem.position',
        cascade='all, delete-orphan'
    )

    @property
    def status(self):
        today = date.today()
        if self.date == today:
            return 'today'
        elif self.date > today:
            return 'upcoming'
        else:
            return 'past'

    @property
    def days_until(self):
        today = date.today()
        delta = (self.date - today).days
        return delta

    @property
    def status_label(self):
        if self.status == 'today':
            return 'Hoy'
        elif self.status == 'upcoming':
            days = self.days_until
            if days == 1:
                return 'Mañana'
            return f'En {days} días'
        else:
            days = abs(self.days_until)
            return f'Hace {days} días'

    @property
    def total_duration_sec(self):
        total = 0
        for item in self.setlist_items:
            if not item.is_break and item.song and item.song.duration_sec:
                total += item.song.duration_sec
        return total

    @property
    def total_duration_display(self):
        total = self.total_duration_sec
        if total == 0:
            return '--'
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60
        if hours > 0:
            return f'{hours}h {minutes:02d}m'
        return f'{minutes}m {seconds:02d}s'

    @property
    def song_count(self):
        return self.setlist_items.filter_by(is_break=False).count()

    def __repr__(self):
        return f'<Show {self.name}>'
