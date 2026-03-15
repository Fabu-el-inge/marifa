from datetime import datetime
from app.extensions import db

INSTRUMENT_ROLES = [
    ('Batería',      '🥁', 'badge-error'),
    ('Guitarra',     '🎸', 'badge-warning'),
    ('Bajo',         '🎸', 'badge-neutral'),
    ('Piano',        '🎹', 'badge-info'),
    ('Teclado',      '🎹', 'badge-info'),
    ('Violín',       '🎻', 'badge-success'),
    ('Saxofón',      '🎷', 'badge-accent'),
    ('Trompeta',     '🎺', 'badge-warning'),
    ('Percusión',    '🪘', 'badge-error'),
    ('Coros',        '🎤', 'badge-secondary'),
    ('Acordeón',     '🪗', 'badge-success'),
    ('Flauta',       '🪈', 'badge-info'),
    ('Contrabajo',   '🎻', 'badge-neutral'),
    ('Sonidista',    '🎚️', 'badge-ghost'),
    ('Otro',         '🎵', 'badge-ghost'),
]

ROLE_MAP = {r[0]: {'emoji': r[1], 'badge': r[2]} for r in INSTRUMENT_ROLES}
ROLE_CHOICES = [(r[0], f"{r[1]} {r[0]}") for r in INSTRUMENT_ROLES]


class Musician(db.Model):
    __tablename__ = 'musicians'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    instrument = db.Column(db.String(50), nullable=False, default='Otro')
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    show_assignments = db.relationship('ShowMusician', backref='musician', lazy='dynamic',
                                       cascade='all, delete-orphan')

    @property
    def instrument_emoji(self):
        return ROLE_MAP.get(self.instrument, {}).get('emoji', '🎵')

    @property
    def instrument_badge(self):
        return ROLE_MAP.get(self.instrument, {}).get('badge', 'badge-ghost')

    @property
    def whatsapp_link(self):
        if not self.phone:
            return None
        digits = ''.join(c for c in self.phone if c.isdigit())
        return f"https://wa.me/{digits}"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'instrument': self.instrument,
            'emoji': self.instrument_emoji,
            'badge': self.instrument_badge,
            'phone': self.phone or '',
            'whatsapp': self.whatsapp_link,
        }

    def __repr__(self):
        return f'<Musician {self.name} ({self.instrument})>'


class ShowMusician(db.Model):
    __tablename__ = 'show_musicians'

    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.id'), nullable=False)
    musician_id = db.Column(db.Integer, db.ForeignKey('musicians.id'), nullable=False)
    role_override = db.Column(db.String(50), nullable=True)  # Si toca otro instrumento ese día
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ShowMusician show={self.show_id} musician={self.musician_id}>'
