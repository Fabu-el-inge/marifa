from datetime import datetime
from app.extensions import db


class Band(db.Model):
    """Banda prearmada con presupuesto."""
    __tablename__ = 'bands'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(12, 2), nullable=True)  # Presupuesto total
    currency = db.Column(db.String(10), default='PYG', nullable=False)  # Guaraníes por defecto
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('BandMusician', backref='band', lazy='dynamic',
                              cascade='all, delete-orphan')

    @property
    def price_display(self):
        if self.price is None:
            return None
        val = int(self.price)
        if self.currency == 'PYG':
            return f"₲ {val:,}".replace(',', '.')
        elif self.currency == 'USD':
            return f"USD {val:,}"
        else:
            return f"{self.currency} {val:,}"

    @property
    def member_count(self):
        return self.members.count()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description or '',
            'price': str(self.price) if self.price is not None else None,
            'price_display': self.price_display,
            'currency': self.currency,
            'member_count': self.member_count,
            'musician_ids': [bm.musician_id for bm in self.members],
        }

    def __repr__(self):
        return f'<Band {self.name}>'


class BandMusician(db.Model):
    """Músico integrante de una banda prearmada."""
    __tablename__ = 'band_musicians'

    id = db.Column(db.Integer, primary_key=True)
    band_id = db.Column(db.Integer, db.ForeignKey('bands.id'), nullable=False)
    musician_id = db.Column(db.Integer, db.ForeignKey('musicians.id'), nullable=False)
    fee = db.Column(db.Numeric(12, 2), nullable=True)  # Caché individual opcional

    musician = db.relationship('Musician', backref='band_memberships')

    def __repr__(self):
        return f'<BandMusician band={self.band_id} musician={self.musician_id}>'
