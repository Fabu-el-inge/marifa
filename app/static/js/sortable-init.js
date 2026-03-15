/**
 * Marifé — Drag & Drop Setlist con SortableJS
 */

let setlistSortable = null;

function initSortable(showId) {
  const list = document.getElementById('setlist-list');
  if (!list) return;

  setlistSortable = Sortable.create(list, {
    group: { name: 'setlist', pull: true, put: true }, // Permite arrastrar hacia el catálogo también
    animation: 200,
    ghostClass: 'sortable-ghost',
    dragClass: 'sortable-drag',
    easing: 'cubic-bezier(1, 0, 0, 1)',
    // Excluir botones de acción del drag (click normal sigue funcionando)
    filter: '.btn, button, a, textarea',
    preventOnFilter: false,

    onAdd: function(evt) {
      // Item arrastrado desde el catálogo al setlist
      const songId   = evt.item.dataset.songId;
      const newIndex = evt.newIndex;
      if (songId) {
        // Mantener el clon como placeholder con estado de carga
        evt.item.style.opacity = '0.4';
        evt.item.style.pointerEvents = 'none';
        addSongToSetlist(parseInt(songId), null, newIndex, evt.item);
      }
    },

    onEnd: function(evt) {
      // Solo re-ordenar si es un item del setlist (tiene data-item-id)
      if (evt.item.dataset.itemId) {
        persistOrder(showId);
      }
    },
  });
}

function persistOrder(showId) {
  const list = document.getElementById('setlist-list');
  if (!list) return;

  const items = list.querySelectorAll('[data-item-id]');
  const order = [];

  items.forEach((el, index) => {
    const itemId = el.getAttribute('data-item-id');
    order.push({ id: itemId, position: index + 1 });

    // Update visual number
    const numEl = el.querySelector('.setlist-number');
    if (numEl && !el.classList.contains('is-break')) {
      // Count only non-break items
      let songCount = 0;
      for (let i = 0; i <= Array.from(items).indexOf(el); i++) {
        if (!items[i].classList.contains('is-break')) songCount++;
      }
      numEl.textContent = songCount;
    }
  });

  fetch(`/setlist/${showId}/reorder`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify(order),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        updateDurationDisplay(data.total_duration, data.song_count);
      }
    })
    .catch(console.error);
}

let _pendingRemoveShowId = null;
let _pendingRemoveItemId = null;

function removeItem(showId, itemId) {
  const el = document.querySelector(`[data-item-id="${itemId}"]`);
  const titleEl = el ? el.querySelector('.font-serif') : null;
  const name = titleEl ? titleEl.textContent.trim() : '';

  _pendingRemoveShowId = showId;
  _pendingRemoveItemId = itemId;

  const nameEl = document.getElementById('confirm-modal-name');
  if (nameEl) nameEl.textContent = name || 'Esta canción se quitará del setlist.';

  const modal = document.getElementById('confirm-modal');
  if (modal) { modal.style.display = 'flex'; return; }

  // Fallback si no existe el modal
  _doRemoveItem(showId, itemId);

}

function closeConfirmModal() {
  const modal = document.getElementById('confirm-modal');
  if (modal) modal.style.display = 'none';
  _pendingRemoveShowId = null;
  _pendingRemoveItemId = null;
}

function confirmDeleteAction() {
  closeConfirmModal();
  if (_pendingRemoveShowId !== null && _pendingRemoveItemId !== null) {
    _doRemoveItem(_pendingRemoveShowId, _pendingRemoveItemId);
  }
}

function _doRemoveItem(showId, itemId) {
  const el = document.querySelector(`[data-item-id="${itemId}"]`);
  const songId = el ? parseInt(el.dataset.songId) : null;

  fetch(`/setlist/${showId}/item/${itemId}/delete`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() },
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        if (el) {
          el.style.opacity = '0';
          el.style.transform = 'translateX(30px)';
          el.style.transition = 'all 0.3s';
          setTimeout(() => {
            el.remove();
            renumberItems();
          }, 300);
        }
        updateDurationDisplay(data.total_duration, data.song_count);

        // Devolver la canción al catálogo
        if (songId && typeof addedSongIds !== 'undefined') {
          addedSongIds.delete(songId);
          // Verificar que no haya otro item con la misma canción en el setlist
          const duplicate = document.querySelector(`#setlist-list [data-song-id="${songId}"]`);
          if (!duplicate || duplicate === el) {
            performSearch(); // Refrescar catálogo para que reaparezca la canción
          }
        }
      }
    })
    .catch(console.error);
}

function renumberItems() {
  const list = document.getElementById('setlist-list');
  if (!list) return;
  const items = list.querySelectorAll('[data-item-id]');
  let songNum = 0;
  items.forEach((el) => {
    if (!el.classList.contains('is-break')) {
      songNum++;
      const numEl = el.querySelector('.setlist-number');
      if (numEl) numEl.textContent = songNum;
    }
  });
}

function saveNotes(showId, itemId) {
  const textarea = document.getElementById(`notes-${itemId}`);
  if (!textarea) return;

  fetch(`/setlist/${showId}/item/${itemId}/notes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify({ notes: textarea.value }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        showMiniToast('Notas guardadas ✓');
      }
    })
    .catch(console.error);
}

function addBreak(showId) {
  const label = prompt('Etiqueta del intermedio:', 'INTERMEDIO 15 MIN');
  if (label === null) return;

  fetch(`/setlist/${showId}/add-break`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify({ label: label || 'INTERMEDIO' }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        appendBreakToList(data.item);
        hideEmptyState();
      }
    })
    .catch(console.error);
}

function appendBreakToList(item) {
  const list = document.getElementById('setlist-list');
  if (!list) return;

  const div = document.createElement('div');
  div.className = 'setlist-item is-break flex items-center gap-3 p-3 slide-in';
  div.setAttribute('data-item-id', item.id);
  div.style.cursor = 'grab';
  div.innerHTML = `
    <div class="flex-1 text-center">
      <span class="text-yellow-400 font-bold tracking-widest text-sm">
        ⏸ ${item.break_label}
      </span>
    </div>
    <button onclick="removeItem(window.SHOW_ID, ${item.id})"
            class="text-gray-600 hover:text-red-400 transition-colors text-sm">
      <i class="fas fa-times"></i>
    </button>
  `;
  list.appendChild(div);
}

function updateDurationDisplay(duration, count) {
  const durationEl = document.getElementById('total-duration');
  const countEl = document.getElementById('song-count');
  if (durationEl) durationEl.textContent = duration;
  if (countEl) countEl.textContent = count;

  // Check 2h warning
  const warnEl = document.getElementById('duration-warning');
  if (warnEl && duration) {
    // Simple check: if duration has 'h' and hours >= 2
    if (duration.includes('h')) {
      const hours = parseInt(duration.split('h')[0]);
      warnEl.style.display = hours >= 2 ? 'flex' : 'none';
    } else {
      warnEl.style.display = 'none';
    }
  }
}

function showMiniToast(msg) {
  const t = document.createElement('div');
  t.className = 'fixed bottom-4 right-4 bg-gray-800 text-green-400 text-sm px-4 py-2 rounded-lg shadow-lg z-50';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transition = 'opacity 0.5s';
    setTimeout(() => t.remove(), 500);
  }, 2000);
}

function hideEmptyState() {
  const empty = document.getElementById('setlist-empty');
  if (empty) empty.style.display = 'none';
}

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}
