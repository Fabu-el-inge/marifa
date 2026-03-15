from flask import Blueprint, render_template, send_file
from app.models.show import Show
from app.models.setlist_item import SetlistItem

public_bp = Blueprint('public', __name__)


@public_bp.route('/<token>')
def show(token):
    show = Show.query.filter_by(public_token=token, is_public=True).first_or_404()
    items = show.setlist_items.order_by(SetlistItem.position).all()
    return render_template('public/show.html', show=show, items=items)


@public_bp.route('/<token>/pdf')
def pdf(token):
    show = Show.query.filter_by(public_token=token, is_public=True).first_or_404()
    items = show.setlist_items.order_by(SetlistItem.position).all()

    from datetime import datetime
    html = render_template('setlist/print.html', show=show, items=items, now=datetime.now())

    try:
        from xhtml2pdf import pisa
        import io

        pdf_buffer = io.BytesIO()
        pisa.CreatePDF(html.encode('utf-8'), dest=pdf_buffer, encoding='utf-8')
        pdf_buffer.seek(0)

        filename = f"Aria_{show.name.replace(' ', '_')}_{show.date.strftime('%Y%m%d')}.pdf"
        return send_file(pdf_buffer, as_attachment=True, download_name=filename,
                         mimetype='application/pdf')
    except Exception:
        from flask import abort
        abort(500)
