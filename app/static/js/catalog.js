/**
 * MariFá — Búsqueda AJAX del catálogo en el Builder
 */

let searchTimeout = null;

// IDs de canciones que ya están en el setlist (para ocultarlas del catálogo)
const addedSongIds = new Set();

function initCatalog(showId) {
  window.SHOW_ID = showId;

  // Inicializar desde los items ya en el setlist (renderizados por el servidor)
  document.querySelectorAll('#setlist-list [data-item-id]:not(.is-break)').forEach(function(el) {
    const sid = parseInt(el.dataset.songId);
    if (sid) addedSongIds.add(sid);
  });

  const searchInput = document.getElementById('catalog-search');
  const genreFilter = document.getElementById('catalog-genre');
  const sortFilter  = document.getElementById('catalog-sort');

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(performSearch, 300);
    });
  }
  if (genreFilter) genreFilter.addEventListener('change', performSearch);
  if (sortFilter)  sortFilter.addEventListener('change', performSearch);

  // Initial load
  performSearch();
}

function performSearch() {
  const q     = document.getElementById('catalog-search')?.value || '';
  const genre = document.getElementById('catalog-genre')?.value  || '';
  const sort  = document.getElementById('catalog-sort')?.value   || 'title';

  const params = new URLSearchParams();
  if (q)     params.set('q', q);
  if (genre) params.set('genre', genre);
  if (sort)  params.set('sort', sort);

  const resultsEl = document.getElementById('catalog-results');
  if (resultsEl) {
    resultsEl.innerHTML = '<div class="text-center py-4"><div class="loading-spinner mx-auto"></div></div>';
  }

  fetch(`/songs/search?${params}`)
    .then((r) => r.json())
    .then((songs) => renderCatalog(songs))
    .catch(() => {
      if (resultsEl) {
        resultsEl.innerHTML = '<p class="text-red-400 text-sm text-center py-4">Error cargando catálogo</p>';
      }
    });
}

function renderCatalog(songs) {
  const resultsEl = document.getElementById('catalog-results');
  if (!resultsEl) return;

  if (songs.length === 0) {
    resultsEl.innerHTML = `
      <div class="empty-state py-8">
        <div class="empty-state-icon">🎵</div>
        <p class="text-sm">No se encontraron canciones</p>
        <a href="/songs/new" class="text-violet-600 text-sm hover:underline mt-2 inline-block">
          + Agregar canción
        </a>
      </div>
    `;
    return;
  }

  resultsEl.innerHTML = songs.map((song) => renderSongCard(song)).join('');

  // Init Sortable en el catálogo para permitir drag al setlist
  if (typeof Sortable !== 'undefined') {
    Sortable.create(resultsEl, {
      group: { name: 'setlist', pull: 'clone', put: true },
      sort: false,
      animation: 150,
      ghostClass: 'sortable-ghost',
      filter: '.btn, button, a',
      preventOnFilter: false,
      onAdd: function(evt) {
        // Canción arrastrada desde el setlist de vuelta al catálogo
        const itemId  = evt.item.dataset.itemId;
        const songId  = parseInt(evt.item.dataset.songId);
        if (itemId) {
          evt.item.remove();
          // Actualizar estado y refrescar catálogo inmediatamente (posición correcta)
          if (songId) addedSongIds.delete(songId);
          performSearch();
          // Eliminar del setlist en el servidor
          fetch(`/setlist/${window.SHOW_ID}/item/${itemId}/delete`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
          })
            .then(r => r.json())
            .then(data => {
              if (data.success) {
                renumberItems();
                updateDurationDisplay(data.total_duration, data.song_count);
              }
            })
            .catch(console.error);
        }
      },
    });
  }
}

function renderSongCard(song) {
  // Si ya está en el setlist, no mostrar en catálogo
  if (addedSongIds.has(song.id)) return '';

  const mob = window.innerWidth < 768;

  const notes = song.musician_notes
    ? `<p style="font-size:${mob ? '0.85rem' : '0.75rem'}; color:#4b5563; margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(song.musician_notes)}</p>`
    : '';

  const key = song.key
    ? `<span style="color:#facc15; font-size:${mob ? '0.85rem' : '0.75rem'}; font-weight:700;">${escapeHtml(song.key)}</span>`
    : '';
  const bpm = song.bpm
    ? `<span style="color:#6b7280; font-size:${mob ? '0.85rem' : '0.75rem'};">${song.bpm} BPM</span>`
    : '';
  const dur = song.duration_display && song.duration_display !== '--:--'
    ? `<span style="color:#6b7280; font-size:${mob ? '0.85rem' : '0.75rem'};">⏱ ${song.duration_display}</span>`
    : '';

  const btnSize = mob ? 'min-width:40px; min-height:40px; font-size:1rem;' : 'min-width:28px; min-height:28px; font-size:0.75rem;';

  // Botón YouTube
  const ytBtn = song.youtube_embed_url
    ? `<button onclick="event.stopPropagation(); openYtPlayer('${escapeHtml(song.youtube_embed_url)}', '${escapeHtml(song.title)}')"
               class="btn btn-xs btn-ghost flex-shrink-0" style="color:#ff0000; ${btnSize} padding:4px;"
               title="Reproducir en YouTube">
        <i class="fab fa-youtube"></i>
      </button>`
    : '';

  // Botón grabación de referencia
  const recBtn = song.recording_url
    ? `<button onclick="event.stopPropagation(); openCatalogAudio('${escapeHtml(song.recording_url)}', '${escapeHtml(song.title)}')"
               class="btn btn-xs btn-ghost flex-shrink-0" style="color:#7c3aed; ${btnSize} padding:4px;"
               title="Escuchar grabación de referencia">
        <i class="fas fa-microphone"></i>
      </button>`
    : '';

  if (mob) {
    // MOBILE: botones abajo en fila, texto usa todo el ancho
    return `
      <div class="catalog-song mb-2 slide-in"
           id="catalog-song-${song.id}"
           data-song-id="${song.id}"
           style="cursor:grab; padding:12px 14px;"
           title="Arrastrá para agregar al setlist">
        <p style="font-weight:600; font-size:1.05rem; color:#1e1b2e; margin:0 0 2px 0;">${escapeHtml(song.title)}</p>
        <p style="font-size:0.9rem; color:#4b5563; margin:0 0 6px 0;">${escapeHtml(song.original_artist)}</p>
        <div style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
          <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; flex:1; min-width:0;">
            <span class="genre-badge badge ${escapeHtml(song.genre_badge)}" style="font-size:0.78rem;">
              ${song.genre_emoji} ${escapeHtml(song.genre)}
            </span>
            ${key}${bpm}${dur}
          </div>
          <div style="display:flex; align-items:center; gap:4px; flex-shrink:0;">
            ${ytBtn}
            ${recBtn}
            <button onclick="addSongToSetlist(${song.id}, this)"
                    class="btn btn-sm btn-marifa"
                    title="Agregar al setlist"
                    style="min-width:38px; min-height:38px; padding:4px;">
              <i class="fas fa-plus"></i>
            </button>
          </div>
        </div>
        ${notes}
      </div>
    `;
  }

  // DESKTOP: layout original con botones a la derecha
  return `
    <div class="catalog-song p-3 mb-2 slide-in"
         id="catalog-song-${song.id}"
         data-song-id="${song.id}"
         style="cursor:grab;"
         title="Arrastrá para agregar al setlist">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-sm truncate" style="color:#1e1b2e;">${escapeHtml(song.title)}</p>
          <p class="text-xs truncate" style="color:#4b5563;">${escapeHtml(song.original_artist)}</p>
          <div class="flex items-center gap-2 mt-1 flex-wrap">
            <span class="genre-badge badge ${escapeHtml(song.genre_badge)} text-xs">
              ${song.genre_emoji} ${escapeHtml(song.genre)}
            </span>
            ${key}${bpm}${dur}
          </div>
          ${notes}
        </div>
        <div class="flex flex-col items-center gap-1 flex-shrink-0">
          ${ytBtn}
          ${recBtn}
          <button onclick="addSongToSetlist(${song.id}, this)"
                  class="btn btn-sm btn-marifa gap-1" title="Agregar al setlist">
            <i class="fas fa-plus text-xs"></i>
          </button>
        </div>
      </div>
    </div>
  `;
}

// Mini reproductor de audio para la grabación de referencia del catálogo
function openCatalogAudio(url, title) {
  let modal = document.getElementById('catalog-audio-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'catalog-audio-modal';
    modal.style = 'position:fixed;bottom:24px;right:24px;z-index:9999;background:#fff;border-radius:16px;padding:16px;box-shadow:0 8px 32px rgba(0,0,0,0.2);min-width:280px;border:1px solid #e9d5ff;';
    modal.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <p id="cat-audio-title" style="font-size:0.8rem;font-weight:600;color:#1e1b2e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></p>
        <button onclick="document.getElementById('catalog-audio-modal').remove()"
                style="margin-left:8px;background:none;border:none;cursor:pointer;color:#9ca3af;font-size:1rem;">✕</button>
      </div>
      <audio id="cat-audio-player" controls style="width:100%;height:36px;"></audio>
    `;
    document.body.appendChild(modal);
  }
  document.getElementById('cat-audio-title').textContent = title || '';
  const player = document.getElementById('cat-audio-player');
  player.src = url;
  player.play().catch(() => {});
}

function addSongToSetlist(songId, btnEl, targetIndex, placeholderEl) {
  const showId = window.SHOW_ID;

  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerHTML = '<div class="loading-spinner"></div>';
  }

  fetch(`/setlist/${showId}/add`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify({ song_id: songId }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        // Registrar en el Set para que no aparezca más en el catálogo
        addedSongIds.add(songId);

        // Actualizar SONGS_DATA para que el modal de letra funcione
        if (typeof SONGS_DATA !== 'undefined' && data.item) {
          SONGS_DATA[data.item.song_id] = {
            title:        data.item.title        || '',
            artist:       data.item.original_artist || '',
            lyrics:       data.item.lyrics        || '',
            notes:        data.item.musician_notes || '',
            key:          data.item.key            || '',
            bpm:          data.item.bpm            || null,
            duration:     data.item.duration_display || '',
            genre:        (data.item.genre_emoji || '') + ' ' + (data.item.genre || ''),
            editUrl:      (data.item.edit_url || '') + '?next=/setlist/' + window.SHOW_ID + '/builder',
            youtubeEmbed: data.item.youtube_embed_url || '',
            recordingUrl: data.item.recording_url  || '',
            printUrl:     data.item.print_url      || '',
          };
        }

        // Refrescar catálogo para que desaparezca la canción agregada
        performSearch();

        if (btnEl) {
          // Animación del botón "+"
          btnEl.disabled = false;
          btnEl.innerHTML = '<i class="fas fa-check text-xs"></i>';
          btnEl.classList.add('btn-success');
          btnEl.classList.remove('btn-marifa');
          setTimeout(() => {
            btnEl.innerHTML = '<i class="fas fa-plus text-xs"></i>';
            btnEl.classList.remove('btn-success');
            btnEl.classList.add('btn-marifa');
            btnEl.disabled = false;
          }, 1500);
        }
        appendSongToList(data.item, targetIndex, placeholderEl);
        updateDurationDisplay(data.total_duration, data.song_count);
        hideEmptyState();
        spawnFloatingNote(btnEl);
        // Si se soltó en una posición específica, persistir el nuevo orden
        if (targetIndex !== undefined) {
          persistOrder(window.SHOW_ID);
        }
      } else {
        if (btnEl) {
          btnEl.disabled = false;
          btnEl.innerHTML = '<i class="fas fa-plus text-xs"></i>';
        }
        if (placeholderEl && placeholderEl.parentNode) placeholderEl.remove();
        alert(data.error || 'Error al agregar canción');
      }
    })
    .catch(() => {
      if (btnEl) {
        btnEl.disabled = false;
        btnEl.innerHTML = '<i class="fas fa-plus text-xs"></i>';
      }
      if (placeholderEl && placeholderEl.parentNode) placeholderEl.remove();
    });
}

function appendSongToList(item, targetIndex, placeholderEl) {
  const list = document.getElementById('setlist-list');
  if (!list) return;

  const existing = list.querySelectorAll('[data-item-id]:not(.is-break)');
  const num = existing.length + 1;

  const div = document.createElement('div');
  div.className = 'bg-white rounded-2xl border border-gray-100 mb-3 overflow-hidden slide-in';
  div.style.cssText = 'cursor:grab; box-shadow:0 2px 12px rgba(0,0,0,0.06); transition: box-shadow 0.2s, transform 0.2s;';
  div.setAttribute('data-item-id', item.id);
  if (item.song_id) div.setAttribute('data-song-id', item.song_id);
  div.onmouseover = function() { this.style.boxShadow='0 6px 24px rgba(244,63,94,0.12)'; this.style.transform='translateY(-1px)'; };
  div.onmouseout  = function() { this.style.boxShadow='0 2px 12px rgba(0,0,0,0.06)'; this.style.transform=''; };
  div.onclick = function(e) {
    if (!e.target.closest('button') && !e.target.closest('textarea')) {
      if (typeof openLyricsModal === 'function') openLyricsModal(item.song_id);
    }
  };

  const keyBadge = item.key
    ? `<span class="flex-shrink-0 font-bold text-xs px-2 py-0.5 rounded-full" style="background:#fffbeb;color:#d97706;border:1px solid #fde68a;">${escapeHtml(item.key)}</span>`
    : '';
  const bpm = item.bpm ? `<span class="text-xs" style="color:#9ca3af;">${item.bpm} BPM</span>` : '';
  const dur = item.duration_display && item.duration_display !== '--:--'
    ? `<span class="text-xs" style="color:#9ca3af;">⏱ ${escapeHtml(item.duration_display)}</span>` : '';
  const notesBox = item.notes
    ? `<div class="mt-2 px-3 py-2 rounded-xl text-xs italic" style="background:#fffbeb;border-left:3px solid #fcd34d;color:#92400e;"><i class="fas fa-sticky-note mr-1"></i>${escapeHtml(item.notes)}</div>` : '';
  const ytBtn = item.youtube_embed_url
    ? `<button onclick="event.stopPropagation();openYtPlayer('${escapeHtml(item.youtube_embed_url)}','${escapeHtml(item.title)}')" class="btn btn-xs btn-ghost" style="color:#ff0000;" title="Reproducir"><i class="fab fa-youtube"></i></button>` : '';

  div.innerHTML = `
    <div class="flex items-stretch">
      <div class="flex items-center justify-center px-4 flex-shrink-0"
           style="background:linear-gradient(180deg,#fdf8f5 0%,#f9f3ee 100%);border-right:1px solid #f0e8f5;min-width:60px;">
        <span class="setlist-number">${num}</span>
      </div>
      <div class="flex-1 min-w-0 p-4">
        <div class="flex items-start justify-between gap-2 mb-1">
          <p class="font-serif font-bold leading-tight" style="font-size:1.1rem;color:#1e1b2e;">${escapeHtml(item.title)}</p>
          ${keyBadge}
        </div>
        <p class="text-sm mb-2" style="color:#6b7280;">${escapeHtml(item.original_artist)}</p>
        <div class="flex items-center gap-2 flex-wrap">
          <span class="genre-badge badge text-xs">${item.genre_emoji} ${escapeHtml(item.genre)}</span>
          ${bpm}${dur}
        </div>
        ${notesBox}
        <div id="notes-section-${item.id}" style="display:none;" class="mt-2">
          <textarea id="notes-${item.id}" class="notes-area w-full text-xs p-2 resize-none" rows="2"
                    placeholder="Notas para este show..."
                    onblur="saveNotes(window.SHOW_ID,${item.id})">${escapeHtml(item.notes||'')}</textarea>
        </div>
      </div>
      <div class="flex flex-col items-center justify-center gap-1 px-2 flex-shrink-0"
           style="border-left:1px solid #f0e8f5;background:#fdf8f5;">
        ${ytBtn}
        <button onclick="event.stopPropagation();toggleNotes(${item.id})" class="btn btn-xs btn-ghost text-gray-400 hover:text-yellow-500" title="Notas"><i class="fas fa-sticky-note"></i></button>
        <button onclick="event.stopPropagation();removeItem(window.SHOW_ID,${item.id})" class="btn btn-xs btn-ghost text-gray-400 hover:text-red-400" title="Quitar"><i class="fas fa-times"></i></button>
      </div>
    </div>
  `;

  if (placeholderEl && placeholderEl.parentNode) {
    // Replace the visual placeholder (placed by SortableJS) with the real card
    placeholderEl.parentNode.insertBefore(div, placeholderEl);
    placeholderEl.remove();
    renumberItems();
  } else if (targetIndex !== undefined) {
    const existingItems = list.querySelectorAll('[data-item-id]');
    if (targetIndex < existingItems.length) {
      list.insertBefore(div, existingItems[targetIndex]);
    } else {
      list.appendChild(div);
    }
    renumberItems();
  } else {
    list.appendChild(div);
  }
}

function toggleNotes(itemId) {
  const section = document.getElementById(`notes-section-${itemId}`);
  if (section) {
    if (section.style.display === 'none') {
      section.style.display = 'block';
      const ta = document.getElementById(`notes-${itemId}`);
      if (ta) ta.focus();
    } else {
      section.style.display = 'none';
    }
  }
}

function spawnFloatingNote(anchorEl) {
  const note = document.createElement('span');
  note.className = 'floating-note';
  note.textContent = '♪';

  if (anchorEl) {
    const rect = anchorEl.getBoundingClientRect();
    note.style.left = `${rect.left + rect.width / 2}px`;
    note.style.top  = `${rect.top}px`;
  } else {
    note.style.left = '50%';
    note.style.top  = '50%';
  }

  document.body.appendChild(note);
  setTimeout(() => note.remove(), 1100);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}
