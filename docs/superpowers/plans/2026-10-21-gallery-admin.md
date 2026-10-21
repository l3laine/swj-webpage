# Gallery Admin Implementation Plan

> Execute inline using superpowers:executing-plans. User approved the design and requested proceeding.

**Goal:** Manage gallery images and sections through the existing news admin.
**Architecture:** gallery.py owns JSON migration, mutations, generation, and gallery admin markup. admin_server.py supplies authentication, CSRF, routing, and upload parsing.
**Tech Stack:** Python stdlib HTTP server, JSON, Pillow, existing HTML/CSS.

1. Back up prototype; preserve current uncommitted news title fix.
2. Add tests/test_gallery.py: import originals; require title; reject invalid image/section; edit caption and section; single/bulk deletion; delete section preserving images; generated escaping and all URL variants.
3. Run tests before implementation and confirm missing gallery module failure.
4. Implement gallery.py, importing the existing gallery once into data/gallery.json and storing data/gallery_template.html. Preserve original filenames and captions. Generate all id=11 HTML variants.
5. Add authenticated GET /dodaj/galeria and POST image/section actions with CSRF validation. Use separate tab navigation and thumbnail cards with edit forms and bulk selection.
6. Add HTTP regression coverage for unauthenticated access, CSRF rejection, upload/edit/delete and section actions. Run gallery tests, news title tests and news lifecycle tests in temporary copies.
7. Generate gallery pages, document commands, restart local server, and verify homepage/admin/gallery responses. Review diff and branch state.
