from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional
from app.extensions import db
from app.models.show import Show
from app.models.musician import Musician, ShowMusician

shows_bp = Blueprint('shows', __name__)


class ShowForm(FlaskForm):
    name = StringField('Nombre del show', validators=[DataRequired()])
    date = DateField('Fecha', validators=[DataRequired()])
    venue = StringField('Venue / Lugar', validators=[Optional()])
    city = StringField('Ciudad', validators=[Optional()])
    general_notes = TextAreaField('Notas generales', validators=[Optional()])


@shows_bp.route('/')
@login_required
def index():
    today = date.today()
    upcoming = Show.query.filter(
        Show.user_id == current_user.id,
        Show.date >= today
    ).order_by(Show.date.asc()).all()

    past = Show.query.filter(
        Show.user_id == current_user.id,
        Show.date < today
    ).order_by(Show.date.desc()).limit(10).all()

    return render_template('shows/index.html', upcoming=upcoming, past=past, today=today)


def _sync_musicians(show, musician_ids):
    """Sincroniza los músicos asignados al show."""
    current_ids = {sm.musician_id for sm in show.musicians}
    new_ids = set(musician_ids)

    # Agregar nuevos
    for mid in new_ids - current_ids:
        m = Musician.query.filter_by(id=mid, user_id=current_user.id, is_active=True).first()
        if m:
            db.session.add(ShowMusician(show_id=show.id, musician_id=m.id))

    # Quitar los que ya no están
    for sm in list(show.musicians):
        if sm.musician_id not in new_ids:
            db.session.delete(sm)


@shows_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = ShowForm()
    musicians = (Musician.query
                 .filter_by(user_id=current_user.id, is_active=True)
                 .order_by(Musician.instrument, Musician.name).all())

    if form.validate_on_submit():
        show = Show(
            name=form.name.data.strip(),
            date=form.date.data,
            venue=form.venue.data.strip() if form.venue.data else None,
            city=form.city.data.strip() if form.city.data else None,
            general_notes=form.general_notes.data.strip() if form.general_notes.data else None,
            user_id=current_user.id,
        )
        db.session.add(show)
        db.session.flush()  # Para obtener show.id antes del commit

        # Músicos seleccionados
        raw_ids = request.form.getlist('musician_ids')
        musician_ids = [int(x) for x in raw_ids if x.isdigit()]
        _sync_musicians(show, musician_ids)

        db.session.commit()
        flash(f'Show "{show.name}" creado.', 'success')
        return redirect(url_for('setlist.builder', show_id=show.id))

    return render_template('shows/form.html', form=form, show=None, musicians=musicians, assigned_ids=[])


@shows_bp.route('/<int:show_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(show_id):
    show = Show.query.filter_by(id=show_id, user_id=current_user.id).first_or_404()
    form = ShowForm(obj=show)
    musicians = (Musician.query
                 .filter_by(user_id=current_user.id, is_active=True)
                 .order_by(Musician.instrument, Musician.name).all())
    assigned_ids = [sm.musician_id for sm in show.musicians]

    if form.validate_on_submit():
        show.name = form.name.data.strip()
        show.date = form.date.data
        show.venue = form.venue.data.strip() if form.venue.data else None
        show.city = form.city.data.strip() if form.city.data else None
        show.general_notes = form.general_notes.data.strip() if form.general_notes.data else None

        raw_ids = request.form.getlist('musician_ids')
        musician_ids = [int(x) for x in raw_ids if x.isdigit()]
        _sync_musicians(show, musician_ids)

        db.session.commit()
        flash(f'Show "{show.name}" actualizado.', 'success')
        next_url = request.args.get('next', '')
        return redirect(next_url if next_url.startswith('/') else url_for('shows.index'))

    return render_template('shows/form.html', form=form, show=show,
                           musicians=musicians, assigned_ids=assigned_ids)


@shows_bp.route('/<int:show_id>/delete', methods=['POST'])
@login_required
def delete(show_id):
    show = Show.query.filter_by(id=show_id, user_id=current_user.id).first_or_404()
    name = show.name
    db.session.delete(show)
    db.session.commit()
    flash(f'Show "{name}" eliminado.', 'info')
    return redirect(url_for('shows.index'))


@shows_bp.route('/<int:show_id>/toggle-public', methods=['POST'])
@login_required
def toggle_public(show_id):
    show = Show.query.filter_by(id=show_id, user_id=current_user.id).first_or_404()
    show.is_public = not show.is_public
    db.session.commit()
    status = 'activado' if show.is_public else 'desactivado'
    flash(f'Link público {status}.', 'success')
    return redirect(request.referrer or url_for('setlist.builder', show_id=show_id))
