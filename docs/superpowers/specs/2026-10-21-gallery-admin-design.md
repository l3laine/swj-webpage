# Gallery management — approved design

Extend the existing authenticated admin with Aktualności and Galeria tabs.
Import all existing gallery images, captions, and Kościół/Klasztor/Wspólnota
sections into JSON. Keep existing image files and public gallery styling.
Gallery supports one-image uploads with required titles and optional section,
editing titles and section assignments, confirmed single/bulk deletion, section
creation, and section deletion preserving images in Bez sekcji. Deleting an image
removes its gallery entry; preserve original files because legacy content may
reference them. New uploads are validated image files with generated thumbnails.
Regenerate every gallery URL variant after successful changes. Require login and
CSRF tokens for all writes. News behavior remains unchanged.
