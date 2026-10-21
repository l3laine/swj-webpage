(function () {
  function classifyDevice() {
    var coarsePointer = window.matchMedia("(pointer: coarse)").matches;
    var narrowViewport = window.matchMedia("(max-width: 640px)").matches;
    var mediumViewport = window.matchMedia("(max-width: 1024px)").matches;
    var hasTouch = navigator.maxTouchPoints > 0;

    if ((coarsePointer || hasTouch) && narrowViewport) {
      document.body.dataset.device = "mobile";
      return;
    }

    if ((coarsePointer || hasTouch) && mediumViewport) {
      document.body.dataset.device = "tablet";
      return;
    }

    document.body.dataset.device = "desktop";
  }

  classifyDevice();
  window.addEventListener("resize", classifyDevice);
})();
