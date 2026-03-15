from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional
from app.extensions import db
from app.models.musician import Musician, ShowMusician, ROLE_CHOICES, INSTRUMENT_ROLES
from app.models.show import Show

musicians_bp = Blueprint('musicians', __name__)


class MusicianForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()])
    instrument = SelectField('Instrumento', choices=ROLE_CHOICES, validators=[DataRequired()])
    phone = StringField('Teléfono / WhatsApp', validators=[Optional()])
    email = StringField('Email', validators=[Optional()])
    notes = TextAreaField('Notas', validators=[Optional()])


@musicians_bp.route('/')
@login_required
def index():
    # Agrupar por instrumento
    musicians = (Musician.query
                 .filter_by(user_id=current_user.id, is_active=True)
                 .order_by(Musician.instrument, Musician.name)
                 .all())

    # Agrupar por instrumento
    grouped = {}
    for m in musicians:
        grouped.setdefault(m.instrument, []).append(m)

    # Orden de los instrumentos según INSTRUMENT_ROLES
    role_order = [r[0] for r in INSTRUMENT_ROLES]
    grouped_ordered = {k: grouped[k] for k in role_order if k in grouped}
    # Agregar cualquier rol no listado al final
    for k in grouped:
        if k not in grouped_ordered:
            grouped_ordered[k] = grouped[k]

    return render_template('musicians/index.html',
                           grouped=grouped_ordered,
                           total=len(musicians))


@musicians_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = MusicianForm()
    # Pre-seleccionar instrumento si viene por query param
    if request.method == 'GET' and request.args.get('instrument'):
        form.instrument.data = request.args.get('instrument')

    if form.validate_on_submit():
        musician = Musician(
            name=form.name.data.strip(),
            instrument=form.instrument.data,
            phone=form.phone.data.strip() if form.phone.data else None,
            email=form.email.data.strip() if form.email.data else None,
            notes=form.notes.data.strip() if form.notes.data else None,
            user_id=current_user.id,
        )
        db.session.add(musician)
        db.session.commit()
        flash(f'{musician.instrument_emoji} {musician.name} agregado a tu banda.', 'success')
        return redirect(url_for('musicians.index'))

    return render_template('musicians/form.html', form=form, musician=None)


@musicians_bp.route('/<int:musician_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(musician_id):
    musician = Musician.query.filter_by(
        id=musician_id, user_id=current_user.id, is_active=True
    ).first_or_404()
    form = MusicianForm(obj=musician)

    if form.validate_on_submit():
        musician.name = form.name.data.strip()
        musician.instrument = form.instrument.data
        musician.phone = form.phone.data.strip() if form.phone.data else None
        musician.email = form.email.data.strip() if form.email.data else None
        musician.notes = form.notes.data.strip() if form.notes.data else None
        db.session.commit()
        flash(f'{musician.name} actualizado.', 'success')
        return redirect(url_for('musicians.index'))

    return render_template('musicians/form.html', form=form, musician=musician)


@musicians_bp.route('/<int:musician_id>/delete', methods=['POST'])
@login_required
def delete(musician_id):
    musician = Musician.query.filter_by(
        id=musician_id, user_id=current_user.id, is_active=True
    ).first_or_404()
    musician.is_active = False
    db.session.commit()
    flash(f'{musician.name} eliminado.', 'info')
    return redirect(url_for('musicians.index'))


# ── API para el show builder ──────────────────────────────────────────────────

@musicians_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    """Crea un músico rápido y devuelve JSON."""
    data = request.get_json()
    name = (data.get('name') or '').strip()
    instrument = (data.get('instrument') or 'Otro').strip()
    phone = (data.get('phone') or '').strip() or None
    email = (data.get('email') or '').strip() or None

    if not name:
        return jsonify({'error': 'El nombre es requerido'}), 400

    musician = Musician(
        name=name,
        instrument=instrument,
        phone=phone,
        email=email,
        user_id=current_user.id,
    )
    db.session.add(musician)
    db.session.commit()
    return jsonify({'success': True, 'musician': musician.to_dict()}), 201


@musicians_bp.route('/api/list')
@login_required
def api_list():
    """Devuelve todos los músicos agrupados por instrumento."""
    musicians = (Musician.query
                 .filter_by(user_id=current_user.id, is_active=True)
                 .order_by(Musician.instrument, Musician.name)
                 .all())
    return jsonify([m.to_dict() for m in musicians])


@musicians_bp.route('/api/show/<int:show_id>/assign', methods=['POST'])
@login_required
def assign(show_id):
    """Agrega un músico a un show."""
    show = Show.query.filter_by(id=show_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    musician_id = data.get('musician_id')
    role_override = data.get('role_override', '').strip() or None

    musician = Musician.query.filter_by(
        id=musician_id, user_id=current_user.id, is_active=True
    ).first_or_404()

    # Evitar duplicados
    existing = ShowMusician.query.filter_by(
        show_id=show.id, musician_id=musician.id
    ).first()
    if existing:
        return jsonify({'error': 'Ya está en el show'}), 409

    sm = ShowMusician(show_id=show.id, musician_id=musician.id,
                      role_override=role_override)
    db.session.add(sm)
    db.session.commit()

    role = role_override or musician.instrument
    return jsonify({
        'success': True,
        'assignment': {
            'id': sm.id,
            'musician_id': musician.id,
            'name': musician.name,
            'instrument': role,
            'emoji': musician.instrument_emoji,
            'badge': musician.instrument_badge,
            'phone': musician.phone or '',
            'whatsapp': musician.whatsapp_link,
        }
    })


@musicians_bp.route('/api/show/<int:show_id>/remove/<int:assignment_id>', methods=['POST'])
@login_required
def remove_from_show(show_id, assignment_id):
    """Quita un músico de un show."""
    show = Show.query.filter_by(id=show_id, user_id=current_user.id).first_or_404()
    sm = ShowMusician.query.filter_by(id=assignment_id, show_id=show.id).first_or_404()
    db.session.delete(sm)
    db.session.commit()
    return jsonify({'success': True})
