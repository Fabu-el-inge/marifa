from datetime import datetime
from app.extensions import db


class SetlistItem(db.Model):
    __tablename__ = 'setlist_items'

    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    notes_override = db.Column(db.Text, nullable=True)
    is_break = db.Column(db.Boolean, default=False, nullable=False)
    break_label = db.Column(db.String(100), nullable=True, default='INTERMEDIO')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        if self.is_break:
            return {
                'id': self.id,
                'position': self.position,
                'is_break': True,
                'break_label': self.break_label or 'INTERMEDIO',
            }
        if not self.song:
            return {'id': self.id, 'position': self.position, 'is_break': False}
        return {
            'id': self.id,
            'position': self.position,
            'is_break': False,
            'song_id': self.song_id,
            'title': self.song.title,
            'original_artist': self.song.original_artist,
            'genre': self.song.genre,
            'genre_emoji': self.song.genre_emoji,
            'key': self.song.key or '',
            'bpm': self.song.bpm,
            'duration_display': self.song.duration_display,
            'notes': self.notes_override or self.song.musician_notes or '',
            'lyrics': self.song.lyrics or '',
            'musician_notes': self.song.musician_notes or '',
            'youtube_embed_url': self.song.youtube_embed_url or '',
            'recording_url': self.song.recording_url or '',
            'edit_url': f'/songs/{self.song_id}/edit',
            'print_url': f'/songs/{self.song_id}/print',
        }

    def __repr__(self):
        return f'<SetlistItem show={self.show_id} pos={self.position}>'
