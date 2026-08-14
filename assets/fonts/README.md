Optional: drop a custom `.ttf`/`.otf` here for captions, then update the `Fontname` in
`src/assemble.py`'s `ASS_HEADER` and pass `fontsdir=assets/fonts` to the `ass=` filter in
`mux_final()` so libass picks it up without a system install.

By default the pipeline uses "DejaVu Sans" (installed on the GitHub Actions runner via
`fonts-dejavu-core`), so this folder can stay empty.
