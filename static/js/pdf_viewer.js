(function () {
  const viewer = document.querySelector('.interactive-viewer');
  if (!viewer || typeof pdfjsLib === 'undefined') return;

  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

  const url = viewer.dataset.pdfUrl;
  viewer.addEventListener('contextmenu', function (event) { event.preventDefault(); });

  const canvas = document.getElementById('pdfCanvas');
  const ctx = canvas.getContext('2d');
  const pageNumEl = document.getElementById('pageNum');
  const pageCountEl = document.getElementById('pageCount');
  const prevBtn = document.getElementById('prevPage');
  const nextBtn = document.getElementById('nextPage');
  const zoomOutBtn = document.getElementById('zoomOut');
  const zoomInBtn = document.getElementById('zoomIn');
  const fullscreenBtn = document.getElementById('fullscreen');
  const canvasWrap = document.querySelector('.canvas-wrap');

  let pdfDoc = null;
  let pageNum = 1;
  let pageRendering = false;
  let pageNumPending = null;
  let zoomFactor = 1;
  let resizeTimer = null;

  function availableWidth() {
    if (!canvasWrap) return window.innerWidth - 24;
    const styles = window.getComputedStyle(canvasWrap);
    const paddingLeft = parseFloat(styles.paddingLeft) || 0;
    const paddingRight = parseFloat(styles.paddingRight) || 0;
    return Math.max(240, canvasWrap.clientWidth - paddingLeft - paddingRight - 2);
  }

  function getFitScale(page) {
    const baseViewport = page.getViewport({ scale: 1 });
    const fit = availableWidth() / baseViewport.width;
    const desktopCap = window.innerWidth >= 900 ? 1.65 : 1.15;
    return Math.min(desktopCap, Math.max(0.35, fit)) * zoomFactor;
  }

  function renderPage(num) {
    if (!pdfDoc) return;
    pageRendering = true;

    pdfDoc.getPage(num).then(function (page) {
      const scale = getFitScale(page);
      const viewport = page.getViewport({ scale: scale });
      const outputScale = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = Math.floor(viewport.width) + 'px';
      canvas.style.height = Math.floor(viewport.height) + 'px';

      const transform = outputScale !== 1
        ? [outputScale, 0, 0, outputScale, 0, 0]
        : null;

      const renderContext = {
        canvasContext: ctx,
        transform: transform,
        viewport: viewport
      };

      const renderTask = page.render(renderContext);
      return renderTask.promise.then(function () {
        pageRendering = false;
        pageNumEl.textContent = num;
        if (canvasWrap && zoomFactor <= 1.03) {
          canvasWrap.scrollLeft = 0;
        }
        if (pageNumPending !== null) {
          const pending = pageNumPending;
          pageNumPending = null;
          renderPage(pending);
        }
      });
    }).catch(function () {
      pageRendering = false;
      viewer.insertAdjacentHTML('beforeend', '<p class="hint">No se pudo renderizar esta página del PDF.</p>');
    });
  }

  function queueRenderPage(num) {
    if (pageRendering) {
      pageNumPending = num;
    } else {
      renderPage(num);
    }
  }

  function onPrevPage() {
    if (pageNum <= 1) return;
    pageNum--;
    queueRenderPage(pageNum);
  }

  function onNextPage() {
    if (!pdfDoc || pageNum >= pdfDoc.numPages) return;
    pageNum++;
    queueRenderPage(pageNum);
  }

  function updateZoom(delta) {
    zoomFactor = Math.min(2.4, Math.max(0.65, zoomFactor + delta));
    queueRenderPage(pageNum);
  }

  prevBtn.addEventListener('click', onPrevPage);
  nextBtn.addEventListener('click', onNextPage);
  zoomOutBtn.addEventListener('click', function () { updateZoom(-0.15); });
  zoomInBtn.addEventListener('click', function () { updateZoom(0.15); });

  fullscreenBtn.addEventListener('click', function () {
    if (viewer.requestFullscreen) {
      viewer.requestFullscreen();
    } else if (viewer.webkitRequestFullscreen) {
      viewer.webkitRequestFullscreen();
    }
  });

  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (pdfDoc) queueRenderPage(pageNum);
    }, 180);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'ArrowLeft') onPrevPage();
    if (event.key === 'ArrowRight') onNextPage();
    const key = (event.key || '').toLowerCase();
    if ((event.ctrlKey || event.metaKey) && ['s', 'p'].includes(key)) {
      event.preventDefault();
    }
  });

  pdfjsLib.getDocument(url).promise.then(function (pdfDoc_) {
    pdfDoc = pdfDoc_;
    pageCountEl.textContent = pdfDoc.numPages;
    renderPage(pageNum);
  }).catch(function () {
    viewer.insertAdjacentHTML('beforeend', '<p class="hint">No se pudo cargar el visor interactivo. Abre el PDF desde la vista normal del material.</p>');
  });
})();
