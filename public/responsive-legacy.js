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

  function addPrototypeHeader() {
    if (document.querySelector(".prototype-title")) {
      return;
    }

    var header = document.createElement("a");
    header.className = "prototype-title";
    header.href = "index.html";
    header.setAttribute("aria-label", "Przejdź do strony głównej");
    header.innerHTML = '<div>Zakon Nawiedzenia Najświętszej Maryi Panny</div><div>Siostry wizytki w Jaśle</div>';
    document.body.insertBefore(header, document.body.firstChild);
  }

  function labelPrototypeButtons() {
    var buttonLabels = {
      but1: "Strona główna",
      but2: "Aktualności",
      but3: "Salezjańska duchowość",
      but4: "Charyzmat zakonu",
      but5: "Kult Serca Jezusa",
      but6: "Arcybractwa",
      but7: "Powołanie",
      but8: "Formacja",
      but9: "Rekolekcje",
      but10: "Historia",
      but11: "Galeria",
      but12: "Kontakt",
      but13: "Msze i nabożeństwa"
    };

    document.querySelectorAll('a > img[name^="but"]').forEach(function (image) {
      var link = image.parentElement;
      if (!link) {
        return;
      }

      link.setAttribute("aria-label", buttonLabels[image.getAttribute("name")] || image.getAttribute("alt") || "");
    });
  }

  function removeLegacyNavBackdrop() {
    document.querySelectorAll('[background*="luk2.gif"], [background*="Bitmapy/luk2.gif"]').forEach(function (element) {
      element.removeAttribute("background");
      element.style.background = "transparent";
      element.style.backgroundImage = "none";
    });
  }

  function markSubpage() {
    var path = window.location.pathname.split("/").pop() || "index.html";
    var isHome = path === "" || path === "index.html";
    var decodedPath = decodeURIComponent(path);
    var query = decodedPath.indexOf("index.php") === 0 ? decodedPath.replace(/^index\.php(?:\?)/, "") : "";
    var params = new URLSearchParams(query.replace(/&amp;/g, "&"));
    var pageId = params.get("id");
    var topicId = params.get("temat");

    document.body.classList.toggle("prototype-subpage", !isHome);
    if (pageId) {
      document.body.classList.add("prototype-page-id-" + pageId);
    }
    if (pageId && topicId !== null) {
      document.body.classList.add("prototype-page-id-" + pageId + "-topic-" + topicId);
    }
    if (pageId === "5" && topicId === "0") {
      document.body.classList.add("prototype-kult-serca-main");
    }
  }

  function removeLegacyBottomFrame() {
    function markMainRow(element) {
      var mainTable = document.querySelector("body > center > table:first-of-type");
      var current = element;
      var candidate = null;

      while (current && current !== mainTable) {
        if (current.tagName && current.tagName.toLowerCase() === "tr") {
          candidate = current;
        }
        current = current.parentElement;
      }

      (candidate || element).classList.add("prototype-remove-bottom-frame");
    }

    document.querySelectorAll('[background*="bd_bar.gif"], [background*="d_bar.gif"], [background*="d_bar2.gif"]').forEach(function (element) {
      markMainRow(element);
    });

    document.querySelectorAll("td").forEach(function (cell) {
      if (cell.textContent && cell.textContent.indexOf("Konto bankowe") !== -1) {
        var text = cell.textContent;
        if (text.indexOf("KONTAKT") === -1 && text.indexOf("Adresy innych klasztorów") === -1) {
          markMainRow(cell);
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      markSubpage();
      addPrototypeHeader();
      labelPrototypeButtons();
      removeLegacyNavBackdrop();
      removeLegacyBottomFrame();
    });
  } else {
    markSubpage();
    addPrototypeHeader();
    labelPrototypeButtons();
    removeLegacyNavBackdrop();
    removeLegacyBottomFrame();
  }
})();
