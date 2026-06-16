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

  let pdfDoc = null;
  let pageNum = 1;
  let pageRendering = false;
  let pageNumPending = null;
  let scale = 1.15;

  function renderPage(num) {
    pageRendering = true;
    pdfDoc.getPage(num).then(function (page) {
      const viewport = page.getViewport({ scale: scale });
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      const renderContext = { canvasContext: ctx, viewport: viewport };
      const renderTask = page.render(renderContext);
      renderTask.promise.then(function () {
        pageRendering = false;
        if (pageNumPending !== null) {
          renderPage(pageNumPending);
          pageNumPending = null;
        }
      });
    });
    pageNumEl.textContent = num;
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
    scale = Math.min(2.5, Math.max(0.5, scale + delta));
    queueRenderPage(pageNum);
  }

  prevBtn.addEventListener('click', onPrevPage);
  nextBtn.addEventListener('click', onNextPage);
  zoomOutBtn.addEventListener('click', function () { updateZoom(-0.15); });
  zoomInBtn.addEventListener('click', function () { updateZoom(0.15); });
  fullscreenBtn.addEventListener('click', function () {
    const element = viewer;
    if (element.requestFullscreen) element.requestFullscreen();
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
