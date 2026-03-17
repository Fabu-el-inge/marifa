import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.show import Show
from app.models.song import Song
from app.models.setlist_item import SetlistItem

setlist_bp = Blueprint('setlist', __name__)


def _get_show(show_id):
    return Show.query.filter_by(id=show_id, user_id=current_user.id).first_or_404()


@setlist_bp.route('/<int:show_id>/builder')
@login_required
def builder(show_id):
    show = _get_show(show_id)
    items = show.setlist_items.order_by(SetlistItem.position).all()
    from app.models.song import GENRE_CHOICES
    genres = [g[0] for g in GENRE_CHOICES]
    return render_template('setlist/builder.html', show=show, items=items, genres=genres)


@setlist_bp.route('/<int:show_id>/add', methods=['POST'])
@login_required
def add(show_id):
    show = _get_show(show_id)
    data = request.get_json()
    song_id = data.get('song_id')

    song = Song.query.filter_by(id=song_id, user_id=current_user.id, is_active=True).first()
    if not song:
        return jsonify({'error': 'Canción no encontrada'}), 404

    # Get next position
    last = show.setlist_items.order_by(SetlistItem.position.desc()).first()
    next_pos = (last.position + 1) if last else 1

    item = SetlistItem(
        show_id=show.id,
        song_id=song.id,
        position=next_pos,
        is_break=False,
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({
        'success': True,
        'item': item.to_dict(),
        'total_duration': show.total_duration_display,
        'song_count': show.song_count,
    })


@setlist_bp.route('/<int:show_id>/reorder', methods=['POST'])
@login_required
def reorder(show_id):
    show = _get_show(show_id)
    data = request.get_json()  # [{id: X, position: Y}, ...]

    item_map = {item.id: item for item in show.setlist_items.all()}

    for entry in data:
        item_id = int(entry['id'])
        new_pos = int(entry['position'])
        if item_id in item_map:
            item_map[item_id].position = new_pos

    db.session.commit()

    return jsonify({
        'success': True,
        'total_duration': show.total_duration_display,
        'song_count': show.song_count,
    })


@setlist_bp.route('/<int:show_id>/item/<int:item_id>/notes', methods=['POST'])
@login_required
def update_notes(show_id, item_id):
    show = _get_show(show_id)
    item = SetlistItem.query.filter_by(id=item_id, show_id=show.id).first_or_404()
    data = request.get_json()
    item.notes_override = data.get('notes', '').strip() or None
    db.session.commit()
    return jsonify({'success': True})


@setlist_bp.route('/<int:show_id>/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(show_id, item_id):
    show = _get_show(show_id)
    item = SetlistItem.query.filter_by(id=item_id, show_id=show.id).first_or_404()
    db.session.delete(item)
    db.session.commit()

    # Re-number positions
    items = show.setlist_items.order_by(SetlistItem.position).all()
    for i, it in enumerate(items, 1):
        it.position = i
    db.session.commit()

    return jsonify({
        'success': True,
        'total_duration': show.total_duration_display,
        'song_count': show.song_count,
    })


@setlist_bp.route('/<int:show_id>/add-break', methods=['POST'])
@login_required
def add_break(show_id):
    show = _get_show(show_id)
    data = request.get_json()
    label = data.get('label', 'INTERMEDIO').strip() or 'INTERMEDIO'

    last = show.setlist_items.order_by(SetlistItem.position.desc()).first()
    next_pos = (last.position + 1) if last else 1

    item = SetlistItem(
        show_id=show.id,
        song_id=None,
        position=next_pos,
        is_break=True,
        break_label=label,
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({'success': True, 'item': item.to_dict()})


@setlist_bp.route('/<int:show_id>/export-pdf')
@login_required
def export_pdf(show_id):
    show = _get_show(show_id)
    items = show.setlist_items.order_by(SetlistItem.position).all()

    from datetime import datetime
    html = render_template('setlist/print.html', show=show, items=items, now=datetime.now())

    try:
        from xhtml2pdf import pisa
        import tempfile
        import io

        pdf_buffer = io.BytesIO()
        pisa.CreatePDF(html.encode('utf-8'), dest=pdf_buffer, encoding='utf-8')
        pdf_buffer.seek(0)

        filename = f"MariFa_{show.name.replace(' ', '_')}_{show.date.strftime('%Y%m%d')}.pdf"
        return send_file(pdf_buffer, as_attachment=True, download_name=filename,
                         mimetype='application/pdf')
    except Exception as e:
        flash(f'Error generando PDF: {str(e)}', 'error')
        return redirect(url_for('setlist.builder', show_id=show_id))
