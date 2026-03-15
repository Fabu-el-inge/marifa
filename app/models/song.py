from datetime import datetime
from app.extensions import db

GENRES = [
    ('Pop', '🎵', 'badge-primary'),
    ('Rock', '🎸', 'badge-error'),
    ('Tango', '🎹', 'badge-secondary'),
    ('Folklore', '🪗', 'badge-warning'),
    ('Cumbia', '🥁', 'badge-success'),
    ('Salsa', '🎺', 'badge-info'),
    ('Bolero', '🌹', 'badge-secondary'),
    ('Jazz', '🎷', 'badge-accent'),
    ('Blues', '🎸', 'badge-neutral'),
    ('Bossa Nova', '🎻', 'badge-success'),
    ('Balada', '💫', 'badge-primary'),
    ('R&B', '🎤', 'badge-error'),
    ('Soul', '✨', 'badge-warning'),
    ('Reggaetón', '🔥', 'badge-error'),
    ('Tropical', '🌴', 'badge-success'),
    ('Clásico', '🎼', 'badge-neutral'),
    ('Otro', '🎵', 'badge-ghost'),
]

GENRE_MAP = {g[0]: {'emoji': g[1], 'badge': g[2]} for g in GENRES}
GENRE_CHOICES = [(g[0], f"{g[1]} {g[0]}") for g in GENRES]


class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    original_artist = db.Column(db.String(200), nullable=False, default='')
    genre = db.Column(db.String(50), nullable=False, default='Otro')
    key = db.Column(db.String(20), nullable=True)  # Tonalidad: Do, Re, Mi...
    bpm = db.Column(db.Integer, nullable=True)
    duration_sec = db.Column(db.Integer, nullable=True)  # Duración en segundos
    lyrics = db.Column(db.Text, nullable=True)
    musician_notes = db.Column(db.Text, nullable=True)
    youtube_url = db.Column(db.String(500), nullable=True)
    recording_path = db.Column(db.String(500), nullable=True)
    position = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    setlist_items = db.relationship('SetlistItem', backref='song', lazy='dynamic')

    @property
    def recording_url(self):
        if not self.recording_path:
            return None
        import os
        supabase_url = os.environ.get('SUPABASE_URL', '')
        if supabase_url:
            return f'{supabase_url}/storage/v1/object/public/recordings/{self.recording_path}'
        return f'/songs/recordings/{self.recording_path}'

    @property
    def youtube_embed_url(self):
        """Convierte cualquier link de YouTube a URL embebible."""
        if not self.youtube_url:
            return None
        url = self.youtube_url.strip()
        # Extraer video ID
        import re
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})',
        ]
        for pat in patterns:
            m = re.search(pat, url)
            if m:
                return f'https://www.youtube.com/embed/{m.group(1)}?autoplay=1'
        return None

    @property
    def duration_display(self):
        if not self.duration_sec:
            return '--:--'
        minutes = self.duration_sec // 60
        seconds = self.duration_sec % 60
        return f'{minutes}:{seconds:02d}'

    @property
    def genre_emoji(self):
        return GENRE_MAP.get(self.genre, {}).get('emoji', '🎵')

    @property
    def genre_badge(self):
        return GENRE_MAP.get(self.genre, {}).get('badge', 'badge-ghost')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'original_artist': self.original_artist,
            'genre': self.genre,
            'genre_emoji': self.genre_emoji,
            'genre_badge': self.genre_badge,
            'key': self.key or '',
            'bpm': self.bpm,
            'duration_sec': self.duration_sec,
            'duration_display': self.duration_display,
            'musician_notes': self.musician_notes or '',
            'youtube_url': self.youtube_url or '',
            'youtube_embed_url': self.youtube_embed_url or '',
            'recording_url': self.recording_url or '',
        }

    def __repr__(self):
        return f'<Song {self.title}>'
