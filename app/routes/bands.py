from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange
from app.extensions import db
from app.models.band import Band, BandMusician
from app.models.musician import Musician

bands_bp = Blueprint('bands', __name__)

CURRENCY_CHOICES = [
    ('PYG', '₲ Guaraníes (PYG)'),
    ('USD', 'USD Dólares'),
    ('ARS', 'ARS Pesos Arg.'),
    ('BRL', 'BRL Reales'),
]


class BandForm(FlaskForm):
    name = StringField('Nombre de la banda', validators=[DataRequired()])
    description = TextAreaField('Descripción', validators=[Optional()])
    price = DecimalField('Presupuesto total', validators=[Optional(), NumberRange(min=0)],
                         places=0)
    currency = SelectField('Moneda', choices=CURRENCY_CHOICES, default='PYG')


@bands_bp.route('/')
@login_required
def index():
    bands = (Band.query
             .filter_by(user_id=current_user.id)
             .order_by(Band.name)
             .all())
    return render_template('bands/index.html', bands=bands)


@bands_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = BandForm()
    musicians = (Musician.query
                 .filter_by(user_id=current_user.id, is_active=True)
                 .order_by(Musician.instrument, Musician.name).all())

    if form.validate_on_submit():
        band = Band(
            name=form.name.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            price=form.price.data if form.price.data is not None else None,
            currency=form.currency.data,
            user_id=current_user.id,
        )
        db.session.add(band)
        db.session.flush()

        raw_ids = request.form.getlist('musician_ids')
        for mid_str in raw_ids:
            if mid_str.isdigit():
                mid = int(mid_str)
                m = Musician.query.filter_by(id=mid, user_id=current_user.id, is_active=True).first()
                if m:
                    db.session.add(BandMusician(band_id=band.id, musician_id=m.id))

        db.session.commit()
        flash(f'Banda "{band.name}" creada.', 'success')
        return redirect(url_for('bands.index'))

    return render_template('bands/form.html', form=form, band=None, musicians=musicians, assigned_ids=[])


@bands_bp.route('/<int:band_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(band_id):
    band = Band.query.filter_by(id=band_id, user_id=current_user.id).first_or_404()
    form = BandForm(obj=band)
    musicians = (Musician.query
                 .filter_by(user_id=current_user.id, is_active=True)
                 .order_by(Musician.instrument, Musician.name).all())
    assigned_ids = [bm.musician_id for bm in band.members]

    if form.validate_on_submit():
        band.name = form.name.data.strip()
        band.description = form.description.data.strip() if form.description.data else None
        band.price = form.price.data if form.price.data is not None else None
        band.currency = form.currency.data

        # Resync musicians
        BandMusician.query.filter_by(band_id=band.id).delete()
        raw_ids = request.form.getlist('musician_ids')
        for mid_str in raw_ids:
            if mid_str.isdigit():
                mid = int(mid_str)
                m = Musician.query.filter_by(id=mid, user_id=current_user.id, is_active=True).first()
                if m:
                    db.session.add(BandMusician(band_id=band.id, musician_id=m.id))

        db.session.commit()
        flash(f'Banda "{band.name}" actualizada.', 'success')
        return redirect(url_for('bands.index'))

    return render_template('bands/form.html', form=form, band=band,
                           musicians=musicians, assigned_ids=assigned_ids)


@bands_bp.route('/<int:band_id>/delete', methods=['POST'])
@login_required
def delete(band_id):
    band = Band.query.filter_by(id=band_id, user_id=current_user.id).first_or_404()
    name = band.name
    db.session.delete(band)
    db.session.commit()
    flash(f'Banda "{name}" eliminada.', 'info')
    return redirect(url_for('bands.index'))


@bands_bp.route('/api/list')
@login_required
def api_list():
    """Devuelve todas las bandas con sus músicos (para el formulario de show)."""
    bands = Band.query.filter_by(user_id=current_user.id).order_by(Band.name).all()
    return jsonify([b.to_dict() for b in bands])


@bands_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    """Crea una banda rápida y devuelve JSON."""
    data = request.get_json()
    name = (data.get('name') or '').strip()
    price_raw = data.get('price')
    currency = (data.get('currency') or 'PYG').strip()

    if not name:
        return jsonify({'error': 'El nombre es requerido'}), 400

    try:
        price = float(price_raw) if price_raw not in (None, '', '0') else None
    except (ValueError, TypeError):
        price = None

    description = (data.get('description') or '').strip() or None
    musician_ids = data.get('musician_ids') or []

    band = Band(name=name, description=description, price=price, currency=currency, user_id=current_user.id)
    db.session.add(band)
    db.session.flush()

    for mid in musician_ids:
        try:
            m = Musician.query.filter_by(id=int(mid), user_id=current_user.id, is_active=True).first()
            if m:
                db.session.add(BandMusician(band_id=band.id, musician_id=m.id))
        except (ValueError, TypeError):
            pass

    db.session.commit()
    return jsonify({'success': True, 'band': band.to_dict()}), 201
