import urllib.request
import urllib.parse
import json
import re
import os
import time
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange
from app.extensions import db
from app.models.song import Song, GENRE_CHOICES

songs_bp = Blueprint('songs', __name__)

RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'recordings')
ALLOWED_AUDIO = {'webm', 'ogg', 'mp3', 'wav', 'm4a', 'opus', 'mp4'}

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
USE_SUPABASE_STORAGE = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def _save_recording_supabase(file_obj, old_path=None):
    """Sube grabación a Supabase Storage."""
    raw_name = file_obj.filename or ''
    ext = raw_name.rsplit('.', 1)[-1].lower() if '.' in raw_name else 'webm'
    if ext not in ALLOWED_AUDIO:
        ext = 'webm'
    filename = f"rec_{int(time.time() * 1000)}.{ext}"

    data = file_obj.read()
    content_type = file_obj.content_type or 'audio/webm'

    req = urllib.request.Request(
        f"{SUPABASE_URL}/storage/v1/object/recordings/{filename}",
        data=data,
        headers={
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            'apikey': SUPABASE_SERVICE_KEY,
            'Content-Type': content_type,
        },
        method='POST'
    )
    urllib.request.urlopen(req, timeout=30)

    # Borrar archivo anterior si existe
    if old_path:
        try:
            del_req = urllib.request.Request(
                f"{SUPABASE_URL}/storage/v1/object/recordings/{old_path}",
                headers={
                    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                    'apikey': SUPABASE_SERVICE_KEY,
                },
                method='DELETE'
            )
            urllib.request.urlopen(del_req, timeout=10)
        except Exception:
            pass

    return filename


def _save_recording(file_obj, old_path=None):
    """Guarda el archivo de grabación."""
    if USE_SUPABASE_STORAGE:
        return _save_recording_supabase(file_obj, old_path)

    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    raw_name = file_obj.filename or ''
    ext = raw_name.rsplit('.', 1)[-1].lower() if '.' in raw_name else 'webm'
    if ext not in ALLOWED_AUDIO:
        ext = 'webm'
    filename = f"rec_{int(time.time() * 1000)}.{ext}"
    file_obj.save(os.path.join(RECORDINGS_DIR, filename))
    if old_path:
        old_full = os.path.join(RECORDINGS_DIR, old_path)
        if os.path.exists(old_full):
            os.remove(old_full)
    return filename


class SongForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    original_artist = StringField('Artista original', validators=[Optional()])
    genre = SelectField('Género', choices=GENRE_CHOICES, validators=[DataRequired()])
    key = StringField('Tonalidad', validators=[Optional()])
    bpm = IntegerField('BPM', validators=[Optional(), NumberRange(min=1, max=400)])
    duration_min = IntegerField('Duración (minutos)', validators=[Optional(), NumberRange(min=0, max=60)])
    duration_sec_part = IntegerField('Segundos', validators=[Optional(), NumberRange(min=0, max=59)])
    musician_notes = TextAreaField('Notas para músicos', validators=[Optional()])
    lyrics = TextAreaField('Letra', validators=[Optional()])
    youtube_url = StringField('Link de YouTube', validators=[Optional()])


@songs_bp.route('/')
@login_required
def index():
    genre_filter = request.args.get('genre', '')
    search_q = request.args.get('q', '')
    sort = request.args.get('sort', 'custom')

    query = Song.query.filter_by(user_id=current_user.id, is_active=True)

    if genre_filter:
        query = query.filter_by(genre=genre_filter)
    if search_q:
        query = query.filter(
            db.or_(
                Song.title.ilike(f'%{search_q}%'),
                Song.original_artist.ilike(f'%{search_q}%')
            )
        )

    if sort == 'custom':
        query = query.order_by(Song.position.asc().nullslast(), Song.title)
    elif sort == 'artist':
        query = query.order_by(Song.original_artist, Song.title)
    elif sort == 'genre':
        query = query.order_by(Song.genre, Song.title)
    elif sort == 'updated':
        query = query.order_by(Song.updated_at.desc())
    else:
        query = query.order_by(Song.title)

    songs = query.all()

    # Genres for filter
    genres = [g[0] for g in GENRE_CHOICES]

    return render_template('songs/index.html',
                           songs=songs,
                           genres=genres,
                           genre_filter=genre_filter,
                           search_q=search_q,
                           sort=sort)


@songs_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = SongForm()
    if form.validate_on_submit():
        duration_sec = None
        if form.duration_min.data is not None or form.duration_sec_part.data is not None:
            mins = form.duration_min.data or 0
            secs = form.duration_sec_part.data or 0
            duration_sec = mins * 60 + secs

        rec_file = request.files.get('recording')
        rec_path = _save_recording(rec_file) if rec_file and rec_file.filename else None

        # Empujar todas las canciones existentes una posición abajo
        Song.query.filter_by(user_id=current_user.id, is_active=True).filter(
            Song.position.isnot(None)
        ).update({Song.position: Song.position + 1})

        song = Song(
            title=form.title.data.strip(),
            original_artist=form.original_artist.data.strip() if form.original_artist.data else '',
            genre=form.genre.data,
            key=form.key.data.strip() if form.key.data else None,
            bpm=form.bpm.data,
            duration_sec=duration_sec if duration_sec else None,
            musician_notes=form.musician_notes.data.strip() if form.musician_notes.data else None,
            lyrics=form.lyrics.data.strip() if form.lyrics.data else None,
            youtube_url=form.youtube_url.data.strip() if form.youtube_url.data else None,
            recording_path=rec_path,
            position=0,
            user_id=current_user.id,
        )
        db.session.add(song)
        db.session.commit()
        flash(f'🎵 "{song.title}" agregada al catálogo.', 'success')
        next_url = request.args.get('next', '')
        return redirect(next_url if next_url.startswith('/') else url_for('songs.index'))

    return render_template('songs/form.html', form=form, song=None)


@songs_bp.route('/<int:song_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(song_id):
    song = Song.query.filter_by(id=song_id, user_id=current_user.id, is_active=True).first_or_404()
    form = SongForm(obj=song)

    if request.method == 'GET':
        if song.duration_sec:
            form.duration_min.data = song.duration_sec // 60
            form.duration_sec_part.data = song.duration_sec % 60

    if form.validate_on_submit():
        duration_sec = None
        if form.duration_min.data is not None or form.duration_sec_part.data is not None:
            mins = form.duration_min.data or 0
            secs = form.duration_sec_part.data or 0
            duration_sec = mins * 60 + secs

        song.title = form.title.data.strip()
        song.original_artist = form.original_artist.data.strip() if form.original_artist.data else ''
        song.genre = form.genre.data
        song.key = form.key.data.strip() if form.key.data else None
        song.bpm = form.bpm.data
        song.duration_sec = duration_sec if duration_sec else None
        song.musician_notes = form.musician_notes.data.strip() if form.musician_notes.data else None
        song.lyrics = form.lyrics.data.strip() if form.lyrics.data else None
        song.youtube_url = form.youtube_url.data.strip() if form.youtube_url.data else None
        rec_file = request.files.get('recording')
        if rec_file and rec_file.filename:
            song.recording_path = _save_recording(rec_file, old_path=song.recording_path)

        db.session.commit()
        flash(f'✏️ "{song.title}" actualizada.', 'success')
        next_url = request.args.get('next', '')
        return redirect(next_url if next_url.startswith('/') else url_for('songs.index'))

    return render_template('songs/form.html', form=form, song=song)


@songs_bp.route('/<int:song_id>/delete', methods=['POST'])
@login_required
def delete(song_id):
    song = Song.query.filter_by(id=song_id, user_id=current_user.id, is_active=True).first_or_404()
    song.is_active = False
    db.session.commit()
    flash(f'"{song.title}" eliminada del catálogo.', 'info')
    return redirect(url_for('songs.index'))


@songs_bp.route('/<int:song_id>/print')
@login_required
def print_song(song_id):
    song = Song.query.filter_by(id=song_id, user_id=current_user.id, is_active=True).first_or_404()
    return render_template('songs/print.html', song=song)


@songs_bp.route('/recordings/<path:filename>')
@login_required
def serve_recording(filename):
    """Sirve archivos de grabación (solo al dueño de la canción)."""
    song = Song.query.filter_by(recording_path=filename, user_id=current_user.id).first_or_404()
    if USE_SUPABASE_STORAGE:
        return redirect(f'{SUPABASE_URL}/storage/v1/object/public/recordings/{song.recording_path}')
    return send_from_directory(RECORDINGS_DIR, song.recording_path)


@songs_bp.route('/<int:song_id>/save-recording', methods=['POST'])
@login_required
def save_recording(song_id):
    song = Song.query.filter_by(id=song_id, user_id=current_user.id, is_active=True).first_or_404()
    rec_file = request.files.get('recording')
    if not rec_file or not rec_file.filename:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    song.recording_path = _save_recording(rec_file, old_path=song.recording_path)
    db.session.commit()
    if USE_SUPABASE_STORAGE:
        rec_url = f'{SUPABASE_URL}/storage/v1/object/public/recordings/{song.recording_path}'
    else:
        rec_url = url_for('songs.serve_recording', filename=song.recording_path)
    return jsonify({'ok': True, 'url': rec_url})


@songs_bp.route('/<int:song_id>/delete-recording', methods=['POST'])
@login_required
def delete_recording(song_id):
    song = Song.query.filter_by(id=song_id, user_id=current_user.id, is_active=True).first_or_404()
    if song.recording_path:
        if USE_SUPABASE_STORAGE:
            try:
                del_req = urllib.request.Request(
                    f"{SUPABASE_URL}/storage/v1/object/recordings/{song.recording_path}",
                    headers={
                        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                        'apikey': SUPABASE_SERVICE_KEY,
                    },
                    method='DELETE'
                )
                urllib.request.urlopen(del_req, timeout=10)
            except Exception:
                pass
        else:
            full_path = os.path.join(RECORDINGS_DIR, song.recording_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        song.recording_path = None
        db.session.commit()
    return jsonify({'ok': True})


@songs_bp.route('/api/search-youtube', methods=['POST'])
@login_required
def search_youtube():
    """Busca canciones scrapeando YouTube directamente (sin API key)."""
    data = request.get_json()
    query = (data.get('q') or '').strip()
    if not query:
        return jsonify({'error': 'Ingresá el nombre de la canción'}), 400

    url = 'https://www.youtube.com/results?' + urllib.parse.urlencode({'search_query': query})
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml',
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception:
        return jsonify({'error': 'No se pudo conectar con YouTube. Probá pegar el link directamente.'}), 503

    # Extraer ytInitialData del HTML
    idx = html.find('ytInitialData = ')
    if idx == -1:
        idx = html.find('ytInitialData=')
    if idx == -1:
        return jsonify({'error': 'No se pudo leer la respuesta de YouTube.'}), 500

    try:
        idx = html.index('{', idx)
        decoder = json.JSONDecoder()
        yt_data, _ = decoder.raw_decode(html, idx)
    except Exception:
        return jsonify({'error': 'Error al procesar la respuesta de YouTube.'}), 500

    # Navegar al listado de videos
    try:
        sections = (yt_data['contents']['twoColumnSearchResultsRenderer']
                    ['primaryContents']['sectionListRenderer']['contents'])
    except (KeyError, TypeError):
        return jsonify({'error': 'No se encontraron resultados.'}), 404

    def parse_secs(text):
        try:
            parts = str(text).split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except Exception:
            pass
        return 0

    results = []
    for section in sections:
        items = section.get('itemSectionRenderer', {}).get('contents', [])
        for item in items:
            v = item.get('videoRenderer')
            if not v:
                continue
            vid_id = v.get('videoId', '')
            if not vid_id:
                continue

            title = ''
            runs = v.get('title', {}).get('runs', [])
            if runs:
                title = runs[0].get('text', '')

            author = ''
            owner_runs = v.get('ownerText', {}).get('runs', [])
            if owner_runs:
                author = owner_runs[0].get('text', '')

            dur_text = v.get('lengthText', {}).get('simpleText', '')
            secs = parse_secs(dur_text)

            results.append({
                'videoId':          vid_id,
                'title':            title,
                'author':           author,
                'duration':         secs,
                'duration_display': dur_text or (f"{secs//60}:{secs%60:02d}" if secs else ''),
                'thumbnail':        f'https://img.youtube.com/vi/{vid_id}/mqdefault.jpg',
                'url':              f'https://www.youtube.com/watch?v={vid_id}',
                'embed_url':        f'https://www.youtube.com/embed/{vid_id}?autoplay=1',
            })
            if len(results) >= 6:
                break
        if len(results) >= 6:
            break

    if not results:
        return jsonify({'error': 'No se encontraron resultados para esa búsqueda.'}), 404

    return jsonify({'results': results})


@songs_bp.route('/api/fetch-youtube', methods=['POST'])
@login_required
def fetch_youtube():
    """Obtiene título y artista desde un link de YouTube via oEmbed (sin API key)."""
    data = request.get_json()
    yt_url = (data.get('url') or '').strip()

    if not yt_url:
        return jsonify({'error': 'URL requerida'}), 400

    # Validar que sea un link de YouTube
    if 'youtube.com' not in yt_url and 'youtu.be' not in yt_url:
        return jsonify({'error': 'Ingresá un link de YouTube válido'}), 400

    try:
        oembed_url = 'https://www.youtube.com/oembed?' + urllib.parse.urlencode({
            'url': yt_url, 'format': 'json'
        })
        req = urllib.request.Request(oembed_url, headers={'User-Agent': 'MariFa-App/1.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            info = json.loads(resp.read().decode())
    except Exception:
        return jsonify({'error': 'No se pudo obtener información. Verificá el link.'}), 400

    raw_title  = info.get('title', '').strip()
    raw_author = info.get('author_name', '').strip()
    thumbnail  = info.get('thumbnail_url', '')

    # Separar "Artista - Título" (formato más común en YouTube)
    song_title = raw_title
    artist     = raw_author

    if ' - ' in raw_title:
        parts  = raw_title.split(' - ', 1)
        artist = parts[0].strip()
        song_title = parts[1].strip()

    # Limpiar sufijos comunes de YouTube
    SUFFIXES = [
        r'\(Official\s*(Music\s*)?Video\)',
        r'\(Official\s*Audio\)',
        r'\(Lyric\s*Video\)',
        r'\(Audio\)',
        r'\(HD\)', r'\(4K\)', r'\(Remastered.*?\)',
        r'\[Official.*?\]', r'\[Lyric.*?\]',
        r'ft\..*$', r'feat\..*$',
    ]
    for pat in SUFFIXES:
        song_title = re.sub(pat, '', song_title, flags=re.IGNORECASE).strip()

    return jsonify({
        'title':     song_title,
        'artist':    artist,
        'thumbnail': thumbnail,
    })


@songs_bp.route('/api/fetch-lyrics', methods=['POST'])
@login_required
def fetch_lyrics():
    """Busca la letra de una canción usando lrclib.net y lyrics.ovh como fallback."""
    data = request.get_json()
    title  = (data.get('title')  or '').strip()
    artist = (data.get('artist') or '').strip()

    if not title:
        return jsonify({'error': 'Necesitás al menos el título de la canción'}), 400

    headers = {'User-Agent': 'MariFa-App/1.0'}

    # Intento 1: lrclib.net
    try:
        params = urllib.parse.urlencode({'track_name': title, 'artist_name': artist})
        req = urllib.request.Request(
            f'https://lrclib.net/api/get?{params}', headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                result = json.loads(resp.read().decode())
                lyrics = (result.get('plainLyrics') or '').strip()
                if lyrics:
                    return jsonify({'lyrics': lyrics, 'source': 'lrclib'})
    except Exception:
        pass

    # Intento 2: lyrics.ovh
    try:
        if artist:
            path = f'{urllib.parse.quote(artist)}/{urllib.parse.quote(title)}'
        else:
            path = f'_/{urllib.parse.quote(title)}'
        req = urllib.request.Request(
            f'https://api.lyrics.ovh/v1/{path}', headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            result = json.loads(resp.read().decode())
            lyrics = (result.get('lyrics') or '').strip()
            if lyrics:
                return jsonify({'lyrics': lyrics, 'source': 'lyrics.ovh'})
    except Exception:
        pass

    return jsonify({'error': 'No se encontró la letra. Podés escribirla manualmente.'}), 404


@songs_bp.route('/<int:song_id>/quick-update', methods=['POST'])
@login_required
def quick_update(song_id):
    """Actualiza BPM y/o duración desde el modal."""
    song = Song.query.filter_by(id=song_id, user_id=current_user.id, is_active=True).first_or_404()
    data = request.get_json()
    if 'bpm' in data:
        val = data['bpm']
        song.bpm = int(val) if val else None
    if 'duration_sec' in data:
        val = data['duration_sec']
        song.duration_sec = int(val) if val else None
    db.session.commit()
    return jsonify({'ok': True, 'bpm': song.bpm, 'duration_display': song.duration_display})


@songs_bp.route('/reorder', methods=['POST'])
@login_required
def reorder():
    """Guarda el orden personalizado de las canciones del catálogo."""
    data = request.get_json()
    order = data.get('order', [])  # lista de song IDs en el nuevo orden
    if not order:
        return jsonify({'error': 'No se recibió orden'}), 400
    for pos, song_id in enumerate(order):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first()
        if song:
            song.position = pos
    db.session.commit()
    return jsonify({'success': True})


@songs_bp.route('/search')
@login_required
def search():
    q = request.args.get('q', '').strip()
    genre = request.args.get('genre', '').strip()

    query = Song.query.filter_by(user_id=current_user.id, is_active=True)

    if q:
        query = query.filter(
            db.or_(
                Song.title.ilike(f'%{q}%'),
                Song.original_artist.ilike(f'%{q}%')
            )
        )
    if genre:
        query = query.filter_by(genre=genre)

    sort = request.args.get('sort', 'title').strip()
    if sort == 'artist':
        query = query.order_by(Song.original_artist, Song.title)
    elif sort == 'genre':
        query = query.order_by(Song.genre, Song.title)
    elif sort == 'updated':
        query = query.order_by(Song.updated_at.desc())
    else:
        query = query.order_by(Song.title)

    songs = query.limit(50).all()
    return jsonify([s.to_dict() for s in songs])




def _slugify(text):
    """Convierte texto a slug para URLs (sin acentos, minúsculas, guiones)."""
    import unicodedata
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s_]+', '-', text.strip())
    return re.sub(r'-+', '-', text)


_SCRAPE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'es-ES,es;q=0.9,pt;q=0.8,en;q=0.7',
}


def _is_tab_line(line):
    """Detecta líneas de tablatura (ej: E|---2---| ) y basura similar."""
    s = line.strip()
    if not s:
        return False
    # Líneas de tablatura: empiezan con E|, B|, G|, D|, A| o similar
    if re.match(r'^[EBAGDe]\|', s):
        return True
    # "Parte X de Y"
    if re.match(r'^Parte\s+\d+\s+de\s+\d+', s, re.IGNORECASE):
        return True
    return False


def _is_chord_only_line(line):
    """Detecta si una línea tiene SOLO acordes (sin letra)."""
    s = line.strip()
    if not s:
        return False
    # Sacar todo lo que parece acorde y espacios, si no queda nada es solo acordes
    without_chords = re.sub(r'\b[A-G][#b]?(?:m|maj|dim|aug|sus[24]?|add\d+)?[0-9]?(?:/[A-G][#b]?)?\b', '', s)
    return not without_chords.strip()


def _clean_cifra_text(text):
    """Filtra tablatura y basura, deja solo letra + acordes + secciones."""
    lines = text.split('\n')
    cleaned = []
    skip_block = False
    for line in lines:
        # Detectar inicio de bloque de tab/dedilhado/tablatura
        if re.match(r'^\s*\[(Tab|Dedilhado|Tablatura|Solo|Riff)', line, re.IGNORECASE):
            skip_block = True
            continue
        # Detectar fin de bloque (nueva sección normal)
        if skip_block and re.match(r'^\s*\[(?!Tab|Dedilhado|Tablatura|Solo|Riff)', line, re.IGNORECASE):
            skip_block = False
        if skip_block:
            continue
        if _is_tab_line(line):
            continue
        cleaned.append(line)

    # Filtrar marcadores de sección en portugués (Cifra Club)
    section_tags = re.compile(
        r'^\s*\[('
        r'Primeira Parte|Segunda Parte|Terceira Parte|Quarta Parte|Quinta Parte'
        r'|Intro|Introdução|Refrão|Final|Ponte|Outro|Instrumental'
        r'|Pre-Refrão|Pré-Refrão|Interlúdio'
        r')\]\s*$', re.IGNORECASE)
    cleaned = [line for line in cleaned if not section_tags.match(line)]

    # Segunda pasada: una línea de solo acordes se queda SOLO si la siguiente tiene letra
    final = []
    for i, line in enumerate(cleaned):
        if _is_chord_only_line(line):
            # Mirar si la siguiente línea tiene letra (no vacía, no solo acordes, no sección)
            next_line = cleaned[i + 1].strip() if i + 1 < len(cleaned) else ''
            if next_line and not _is_chord_only_line(cleaned[i + 1]) and not re.match(r'^\[', next_line):
                final.append(line)
            # Si no, descartar (es acorde suelto de intro/dedilhado/etc)
        else:
            final.append(line)

    # Limpiar líneas vacías consecutivas
    result = []
    prev_empty = False
    for line in final:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        result.append(line)
        prev_empty = is_empty
    return '\n'.join(result).strip()


def _extract_cifraclub_chords(html):
    """Extrae acordes del HTML de Cifra Club (contenido en <pre>)."""
    pre_match = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.DOTALL)
    if not pre_match:
        return None
    cifra_html = pre_match.group(1)
    cifra_text = re.sub(r'<b>([^<]+)</b>', r'\1', cifra_html)
    cifra_text = re.sub(r'<span[^>]*>([^<]*)</span>', r'\1', cifra_text)
    cifra_text = re.sub(r'<a[^>]*>([^<]*)</a>', r'\1', cifra_text)
    cifra_text = re.sub(r'<[^>]+>', '', cifra_text)
    cifra_text = (cifra_text.replace('&amp;', '&').replace('&lt;', '<')
                  .replace('&gt;', '>').replace('&#x27;', "'").replace('&quot;', '"'))
    cifra_text = _clean_cifra_text(cifra_text)
    if len(cifra_text) > 50 and re.search(r'\b[A-G][#b]?m?\b', cifra_text):
        return cifra_text
    return None


def _search_cifraclub(title, artist):
    """Busca acordes reales en Cifra Club por URL directa (slug)."""
    if not title:
        return None
    title_slug = _slugify(title)
    artist_slug = _slugify(artist) if artist else None

    urls = []
    if artist_slug:
        urls.append(f'https://www.cifraclub.com.br/{artist_slug}/{title_slug}/')
    urls.append(f'https://www.cifraclub.com.br/{title_slug}/')

    for url in urls:
        try:
            req = urllib.request.Request(url, headers=_SCRAPE_HEADERS)
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status != 200:
                    continue
                html = resp.read().decode('utf-8', errors='ignore')
                result = _extract_cifraclub_chords(html)
                if result:
                    return result
        except Exception:
            continue
    return None




@songs_bp.route('/api/generate-chords', methods=['POST'])
@login_required
def api_generate_chords():
    data    = request.get_json()
    lyrics  = (data.get('lyrics') or '').strip()
    key     = (data.get('key') or '').strip()
    title   = (data.get('title') or '').strip()
    artist  = (data.get('artist') or '').strip()

    if not lyrics:
        return jsonify({'error': 'No hay letra para procesar.'}), 400

    # ── Paso 1: Buscar acordes reales en sitios de cifrado ──
    real_chords = None
    source = None

    if title:
        real_chords = _search_cifraclub(title, artist)
        if real_chords:
            source = 'cifraclub'

    # Si encontramos acordes reales, devolver directamente
    if real_chords:
        return jsonify({'lyrics': real_chords, 'source': source})

    # No se encontraron acordes online
    return jsonify({'error': 'No se encontraron acordes para esta canción en CifraClub.'}), 404
