/* ===== MariFá Tour & Tutorial ===== */

// ---- Page detection ----
function detectPage() {
  const path = window.location.pathname;
  if (path.includes('/setlist/')) return 'builder';
  if (path.includes('/songs/new') || path.includes('/songs/edit')) return 'song_form';
  if (path.includes('/songs')) return 'songs';
  if (path.includes('/shows/new') || path.includes('/shows/edit')) return 'show_form';
  if (path.includes('/shows')) return 'shows';
  if (path.includes('/bands/new') || path.includes('/bands/edit')) return 'band_form';
  if (path.includes('/bands')) return 'bands';
  if (path.includes('/musicians/new') || path.includes('/musicians/edit')) return 'musician_form';
  if (path.includes('/musicians')) return 'musicians';
  return null;
}

// ---- Tour definitions ----
const TOURS = {
  welcome: {
    key: 'marifa_tour_welcome',
    steps: function() {
      const isMobile = window.innerWidth < 768;
      if (isMobile) {
        return [
          { element: '.mobile-menu-btn', popover: { title: '¡Bienvenido a MariFá! 🎵', description: 'Tu gestor de setlists para shows en vivo. Desde este menú accedés a todas las secciones.', side: 'bottom' }},
          { element: '.mobile-bottom-nav a:nth-child(1)', popover: { title: 'Canciones', description: 'Tu catálogo completo: letras, acordes, tonalidades y grabaciones de referencia.', side: 'top' }},
          { element: '.mobile-bottom-nav a:nth-child(2)', popover: { title: 'Shows', description: 'Creá shows y eventos, y armá el setlist para cada uno.', side: 'top' }},
          { element: '.mobile-bottom-nav a:nth-child(3)', popover: { title: 'Bandas', description: 'Armá bandas prearmadas con integrantes y presupuesto.', side: 'top' }},
          { element: '.mobile-bottom-nav a:nth-child(4)', popover: { title: 'Músicos', description: 'Tu directorio de músicos con contacto rápido por WhatsApp.', side: 'top' }},
        ];
      }
      return [
        { element: '.marifa-logo', popover: { title: '¡Bienvenido a MariFá! 🎵', description: 'Tu gestor de setlists para shows en vivo. Te mostramos cómo funciona.', side: 'right' }},
        { element: '[data-tour="nav-songs"]', popover: { title: 'Catálogo de Canciones', description: 'Acá gestionás todas tus canciones: letras, acordes, tonalidades, BPM y grabaciones de referencia.', side: 'right' }},
        { element: '[data-tour="nav-shows"]', popover: { title: 'Shows & Eventos', description: 'Creá shows con fecha, lugar y músicos. Desde cada show armás el setlist.', side: 'right' }},
        { element: '[data-tour="nav-bands"]', popover: { title: 'Bandas', description: 'Armá bandas prearmadas con sus integrantes y presupuesto total.', side: 'right' }},
        { element: '[data-tour="nav-musicians"]', popover: { title: 'Músicos', description: 'Tu directorio de músicos con instrumento, contacto y acceso rápido a WhatsApp.', side: 'right' }},
      ];
    }
  },

  songs: {
    key: 'marifa_tour_songs',
    steps: function() {
      const steps = [
        { element: '[data-tour="add-btn"]', popover: { title: 'Agregar Canciones', description: 'Agregá canciones con título, artista, género, tonalidad, BPM, letra y acordes.', side: 'bottom' }},
      ];
      if (document.querySelector('[data-tour="filters"]')) {
        steps.push({ element: '[data-tour="filters"]', popover: { title: 'Buscar y Filtrar', description: 'Buscá por título o artista, filtrá por género y ordená como prefieras.', side: 'bottom' }});
      }
      if (document.querySelector('.catalog-song')) {
        steps.push({ element: '.catalog-song', popover: { title: 'Tarjetas de Canción', description: 'Hacé click en una canción para ver su letra, acordes y grabación. Usá los íconos para editar o eliminar.', side: 'bottom' }});
      }
      return steps;
    }
  },

  shows: {
    key: 'marifa_tour_shows',
    steps: function() {
      const steps = [
        { element: '[data-tour="add-btn"]', popover: { title: 'Crear Shows', description: 'Creá un show con fecha, lugar, ciudad y los músicos que van a tocar.', side: 'bottom' }},
      ];
      if (document.querySelector('.show-card')) {
        steps.push({ element: '.show-card', popover: { title: 'Tus Shows', description: 'Hacé click en un show para abrir el Setlist Builder y armar la lista de canciones. El estado (hoy, próximo, pasado) se calcula automáticamente.', side: 'bottom' }});
      }
      return steps;
    }
  },

  builder: {
    key: 'marifa_tour_builder',
    steps: function() {
      const steps = [];
      if (document.querySelector('#song-count')) {
        steps.push({ element: '#song-count', popover: { title: 'Estadísticas', description: 'Cantidad de canciones y duración total del setlist en tiempo real.', side: 'bottom' }});
      }
      if (document.querySelector('#setlist-list')) {
        steps.push({ element: '#setlist-list', popover: { title: 'Tu Setlist', description: 'Arrastrá las canciones para reordenar. Hacé click en una para ver la letra y acordes.', side: 'right' }});
      }
      if (document.querySelector('#catalog-search')) {
        steps.push({ element: '#catalog-search', popover: { title: 'Catálogo', description: 'Buscá canciones de tu catálogo y hacé click en + para agregarlas al setlist.', side: 'left' }});
      }
      return steps;
    }
  },

  bands: {
    key: 'marifa_tour_bands',
    steps: function() {
      const steps = [
        { element: '[data-tour="add-btn"]', popover: { title: 'Crear Bandas', description: 'Armá bandas prearmadas con músicos y calculá el presupuesto total.', side: 'bottom' }},
      ];
      return steps;
    }
  },

  musicians: {
    key: 'marifa_tour_musicians',
    steps: function() {
      const steps = [
        { element: '[data-tour="add-btn"]', popover: { title: 'Agregar Músicos', description: 'Agregá músicos con instrumento, teléfono y email. Contactalos directo por WhatsApp.', side: 'bottom' }},
      ];
      return steps;
    }
  }
};

// ---- Driver.js initialization ----
function createDriver() {
  return window.driver.js.driver({
    showProgress: true,
    animate: true,
    overlayColor: 'rgba(30, 27, 46, 0.75)',
    stagePadding: 8,
    stageRadius: 16,
    popoverClass: 'marifa-tour-popover',
    nextBtnText: 'Siguiente →',
    prevBtnText: '← Anterior',
    doneBtnText: '¡Listo!',
    progressText: '{{current}} de {{total}}',
  });
}

function startTour(tourName) {
  const tour = TOURS[tourName];
  if (!tour) return;
  const steps = tour.steps();
  if (!steps || steps.length === 0) return;

  // Filter out steps whose elements don't exist
  const validSteps = steps.filter(function(s) {
    return !s.element || document.querySelector(s.element);
  });
  if (validSteps.length === 0) return;

  const d = createDriver();
  d.setSteps(validSteps);
  d.drive();

  // Mark as done when destroyed
  if (tour.key) {
    var origDestroy = d.destroy.bind(d);
    d.destroy = function() {
      localStorage.setItem(tour.key, 'done');
      origDestroy();
    };
  }
}

function replayCurrentTour() {
  const page = detectPage();
  if (page && TOURS[page]) {
    startTour(page);
  } else {
    startTour('welcome');
  }
}

// ---- Auto-start on first visit ----
function autoStartTour() {
  // Welcome tour first
  if (!localStorage.getItem(TOURS.welcome.key)) {
    startTour('welcome');
    return;
  }

  // Then page-specific tour
  const page = detectPage();
  if (page && TOURS[page] && !localStorage.getItem(TOURS[page].key)) {
    startTour(page);
  }
}

// ---- Tutorial Modal ----
function openTutorialModal() {
  document.getElementById('tutorial-modal').style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

function closeTutorialModal() {
  document.getElementById('tutorial-modal').style.display = 'none';
  document.body.style.overflow = '';
}

function showTutorialSection(sectionId) {
  document.querySelectorAll('.tutorial-section').forEach(function(el) {
    el.style.display = 'none';
  });
  document.querySelectorAll('.tutorial-tab').forEach(function(el) {
    el.classList.remove('active');
  });
  document.getElementById('tut-' + sectionId).style.display = 'block';
  document.querySelector('[data-tut-tab="' + sectionId + '"]').classList.add('active');
}

// ---- Help menu ----
function toggleHelpMenu() {
  var menu = document.getElementById('help-menu');
  menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

// ---- Init on DOM ready ----
document.addEventListener('DOMContentLoaded', function() {
  // Wait a bit for Alpine.js and dynamic content
  setTimeout(autoStartTour, 800);

  // Close help menu on outside click
  document.addEventListener('click', function(e) {
    var menu = document.getElementById('help-menu');
    var btn = document.getElementById('help-btn');
    if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
      menu.style.display = 'none';
    }
  });
});
