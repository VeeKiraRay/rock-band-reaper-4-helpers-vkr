"""Tk-compatible VENUE spritesheet lookup and animation.

JPEG sheets use Pillow when it is installed. GIF sheets use Tk directly and
remain the dependency-free fallback supported by Tk 8.5.

Python 2.7 compatible.
"""

from __future__ import unicode_literals

import os
import re
from fractions import Fraction

try:
    import Tkinter as tk
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import ttk


SPRITE_COLUMNS = 8
SPRITE_FRAME_MS = 33
TK_96_DPI_SCALING = 96.0 / 72.0

_CATEGORY_FOLDERS = {
    'Camera': 'camera',
    'Lighting': 'lighting',
    'PostProc': 'postproc',
}

_DIRECTED_SPRITE_NAMES = {
    'directed_all': 'dall',
    'directed_all_cam': 'dallcam',
    'directed_all_lt': 'dalllt',
    'directed_all_yeah': 'dallyeah',
    'directed_crowd': 'dcrowd',
    'directed_drums': 'ddrums',
    'directed_drums_pnt': 'ddrumspoint',
    'directed_drums_np': 'ddrumsnp',
    'directed_drums_lt': 'ddrumslt',
    'directed_drums_kd': 'ddrumskd',
    'directed_vocals': 'dvocals',
    'directed_vocals_np': 'dvoxnp',
    'directed_vocals_cls': 'dvoxcls',
    'directed_vocals_cam_pr': 'dvoxcampr',
    'directed_vocals_cam_pt': 'dvoxcampt',
    'directed_stagedive': 'dstagedive',
    'directed_crowdsurf': 'dcrowdsurf',
    'directed_bass': 'dbass',
    'directed_crowd_b': 'dcrowdbass',
    'directed_bass_np': 'dbassnp',
    'directed_bass_cam': 'dbasscam',
    'directed_bass_cls': 'dbasscls',
    'directed_guitar': 'dgtr',
    'directed_crowd_g': 'dcrowdgtr',
    'directed_guitar_np': 'dgtrnp',
    'directed_guitar_cls': 'dgtrcls',
    'directed_guitar_cam_pr': 'dgtrcampr',
    'directed_guitar_cam_pt': 'dgtrcampt',
    'directed_keys': 'dkeys',
    'directed_keys_cam': 'dkeyscam',
    'directed_keys_np': 'dkeysnp',
    'directed_duo_drums': 'dduodrums',
    'directed_duo_bass': 'dduobass',
    'directed_duo_guitar': 'dduogtr',
    'directed_duo_kv': 'dduokv',
    'directed_duo_gb': 'dduogb',
    'directed_duo_kb': 'dduokb',
    'directed_duo_kg': 'dduokg',
}

_POSTPROC_SPRITE_NAMES = {
    'contrast_a': 'contrastbw',
    'desat_posterize_trails': 'desatposterize',
    'film_16mm': '16mmfilm',
    'film_b+w': 'filmbw',
    'film_blue_filter': 'bluefilter',
    'film_sepia_ink': 'sepiaink',
    'film_silvertone': 'silvertone',
    'horror_movie_special': 'horrormovie',
    'ProFilm_b': 'colormuted',
    'ProFilm_mirror_a': 'mirror',
    'ProFilm_psychedelic_blue_red': 'psychbluered',
    'video_a': 'videograiny',
}

_SHEET_RE = re.compile(
    r'^(.+)_f(\d+)_spritesheet\.(gif|jpe?g)$', re.IGNORECASE)


def default_sprite_root():
    package_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(
        os.path.dirname(package_dir), 'resources', 'img', 'spritesheets')


def tk_display_scale(widget):
    """Return Tk's monitor scale relative to 96-DPI logical pixels."""
    try:
        value = float(widget.tk.call('tk', 'scaling')) / TK_96_DPI_SCALING
    except (AttributeError, TypeError, ValueError, tk.TclError):
        value = 1.0
    return max(0.75, min(3.0, value))


def preview_dimensions(logical_scale, display_scale=1.0):
    """Convert the Preview's logical 1x/2x size to physical image pixels."""
    multiplier = int(logical_scale) * float(display_scale)
    return (int(round(213 * multiplier)), int(round(120 * multiplier)))


def normalize_sprite_key(category, bare_name):
    bare_name = bare_name or ''
    if category == 'Lighting':
        return bare_name.replace('_', '').replace(' ', '').lower()
    if category == 'PostProc':
        bare = re.sub(r'\.pp$', '', bare_name, flags=re.IGNORECASE)
        mapped = _POSTPROC_SPRITE_NAMES.get(bare, bare)
        return mapped.replace('_', '').replace(' ', '').lower()
    mapped = _DIRECTED_SPRITE_NAMES.get(bare_name, bare_name)
    return mapped.replace('_', '').replace(' ', '').lower()


def find_sprite_sheets(sprite_root, category, bare_name, preferred_size=None):
    """Prefer original-size sheets, with GIF and small-sheet fallbacks."""
    folder = _CATEGORY_FOLDERS.get(category, category.lower())
    wanted = normalize_sprite_key(category, bare_name)
    found = []
    suffixes = ('', ' gif', ' small', ' small gif')
    for suffix in suffixes:
        directory = os.path.join(sprite_root, folder + suffix)
        try:
            names = sorted(os.listdir(directory))
        except OSError:
            continue
        matches = []
        for name in names:
            match = _SHEET_RE.match(name)
            if not match:
                continue
            key = match.group(1).replace('_', '').replace(' ', '').lower()
            if key == wanted:
                matches.append((name, int(match.group(2))))
        if matches:
            # Source folders prefer the original JPEG. Dedicated GIF folders
            # are checked only after both original-size choices.
            matches.sort(key=lambda row: (row[0].lower().endswith('.gif'),
                                          row[0].lower()))
            found.extend((os.path.join(directory, name), count)
                         for name, count in matches)
    return found


def find_sprite_sheet(sprite_root, category, bare_name):
    """Return the first available ``(path, frame_count)`` for compatibility."""
    found = find_sprite_sheets(sprite_root, category, bare_name)
    return found[0] if found else (None, 0)


class VenueSpritePlayer(ttk.Frame):
    """Display and animate one event preview, with a useful text fallback."""

    def __init__(self, parent, sprite_root, category, bare_name, raw_event,
                 description='', animate=True, preferred_size=None,
                 show_event_label=True, display_scale=1.0):
        ttk.Frame.__init__(self, parent)
        self.sprite_root = sprite_root
        self.category = category
        self.bare_name = bare_name
        self.raw_event = raw_event
        self.description = description or ''
        self.animate = bool(animate)
        self.preferred_size = preferred_size
        self.show_event_label = bool(show_event_label)
        self.display_scale = float(display_scale)
        self.frames = []
        self.frame_index = 0
        self.after_id = None
        self.backend = 'fallback'
        self.frame_cache = {}
        self.cache_order = []

        self.image_label = ttk.Label(self, anchor='center', justify=tk.CENTER)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.event_label = ttk.Label(
            self, text=raw_event, foreground='#666666', anchor='center')
        if self.show_event_label:
            self.event_label.pack(fill=tk.X, pady=(5, 0))
        self.description_label = ttk.Label(
            self, justify=tk.LEFT, anchor='w', wraplength=420)
        self._show_description()
        self._load()

    def set_event(self, sprite_root, category, bare_name, raw_event,
                  description=''):
        """Replace the displayed event without replacing the preview widget."""
        self.stop()
        self.frames = []
        self.frame_index = 0
        self.backend = 'fallback'
        self.image_label.configure(image='', text='')
        self.image_label.image = None
        self.sprite_root = sprite_root
        self.category = category
        self.bare_name = bare_name
        self.raw_event = raw_event
        self.description = description or ''
        self.event_label.configure(text=raw_event)
        self._show_description()
        self._load()

    def _show_description(self):
        self.description_label.configure(text=self.description)
        if self.description:
            self.description_label.pack(fill=tk.X, pady=(5, 0))
        else:
            self.description_label.pack_forget()

    def clear_event(self):
        """Show an empty selection without retaining the previous preview."""
        self.stop()
        self.frames = []
        self.frame_index = 0
        self.backend = 'fallback'
        self.image_label.configure(
            image='', text='Choose an event to preview.', width=0,
            padding=0, relief='flat')
        self.image_label.image = None
        self.event_label.configure(text='')
        self.description = ''
        self._show_description()

    def _load(self):
        candidates = find_sprite_sheets(
            self.sprite_root, self.category, self.bare_name,
            self.preferred_size)
        if not candidates:
            self._show_fallback(
                'No preview found\nChoose the spritesheets folder if previews '
                'are stored elsewhere.')
            return
        errors = []
        backend = 'fallback'
        for path, frame_count in candidates:
            cache_key = (path, frame_count)
            cached = self.frame_cache.get(cache_key)
            if cached is not None:
                self.frames, backend = cached
                break
            try:
                if path.lower().endswith('.gif'):
                    self.frames = self._load_gif(path, frame_count)
                    backend = 'Tk GIF'
                else:
                    self.frames = self._load_jpeg(path, frame_count)
                    backend = 'Pillow JPEG'
            except Exception as exc:
                self.frames = []
                errors.append('%s: %s' % (exc.__class__.__name__, exc))
                continue
            if self.frames:
                self.frame_cache[cache_key] = (self.frames, backend)
                self.cache_order.append(cache_key)
                if len(self.cache_order) > 4:
                    oldest = self.cache_order.pop(0)
                    del self.frame_cache[oldest]
                break
        if not self.frames:
            detail = errors[-1] if errors else 'No usable frames were found.'
            self._show_fallback('Preview could not load\n%s' % detail)
            return
        first_index = 0 if self.animate else int(len(self.frames) / 2)
        self.frame_index = first_index
        self.image_label.configure(image=self.frames[first_index], text='')
        self.image_label.image = self.frames[first_index]
        self.image_label.configure(takefocus=False)
        self.backend = backend
        if self.animate:
            self._tick()

    def _load_gif(self, path, frame_count):
        sheet = tk.PhotoImage(file=path)
        return self._crop_tk_sheet(sheet, frame_count)

    def _crop_tk_sheet(self, sheet, frame_count):
        tile_width = int(sheet.width() / SPRITE_COLUMNS)
        tile_height = int(round(tile_width * 120.0 / 213.0))
        if tile_width < 1 or tile_height < 1:
            raise ValueError('invalid spritesheet dimensions')
        capacity = SPRITE_COLUMNS * int(sheet.height() / tile_height)
        frame_count = min(max(int(frame_count), 1), capacity)
        frames = []
        for index in range(frame_count):
            column = index % SPRITE_COLUMNS
            row = int(index / SPRITE_COLUMNS)
            x1 = column * tile_width
            y1 = row * tile_height
            frame = tk.PhotoImage(width=tile_width, height=tile_height)
            frame.tk.call(
                str(frame), 'copy', str(sheet), '-from', x1, y1,
                x1 + tile_width, y1 + tile_height, '-to', 0, 0)
            frame = self._scale_tk_frame(frame)
            frames.append(frame)
        return frames

    def _scale_tk_frame(self, frame):
        if self.preferred_size not in (1, 2):
            return frame
        target_width, target_height = preview_dimensions(
            self.preferred_size, self.display_scale)
        width = int(frame.width())
        height = int(frame.height())
        if width == target_width and height == target_height:
            return frame
        ratio = (float(target_width) / width +
                 float(target_height) / height) / 2.0
        fraction = Fraction(ratio).limit_denominator(8)
        scaled = frame
        if fraction.numerator > 1:
            scaled = scaled.zoom(fraction.numerator)
        if fraction.denominator > 1:
            scaled = scaled.subsample(fraction.denominator)
        return scaled

    def _load_jpeg(self, path, frame_count):
        try:
            from PIL import Image, ImageTk
        except ImportError:
            raise RuntimeError(
                'JPEG previews require Pillow; GIF previews work with Tk 8.5')
        sheet = Image.open(path)
        tile_width = int(sheet.size[0] / SPRITE_COLUMNS)
        tile_height = int(round(tile_width * 120.0 / 213.0))
        capacity = SPRITE_COLUMNS * int(sheet.size[1] / tile_height)
        frame_count = min(max(int(frame_count), 1), capacity)
        frames = []
        for index in range(frame_count):
            column = index % SPRITE_COLUMNS
            row = int(index / SPRITE_COLUMNS)
            box = (column * tile_width, row * tile_height,
                   (column + 1) * tile_width, (row + 1) * tile_height)
            image = sheet.crop(box)
            if self.preferred_size in (1, 2):
                target = preview_dimensions(
                    self.preferred_size, self.display_scale)
                if image.size != target:
                    image = image.resize(target, Image.BILINEAR)
            frames.append(ImageTk.PhotoImage(image))
        return frames

    def _show_fallback(self, message):
        self.image_label.configure(
            image='', text=message, width=34, padding=12,
            relief='sunken')

    def _tick(self):
        if not self.frames:
            return
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        frame = self.frames[self.frame_index]
        self.image_label.configure(image=frame)
        self.image_label.image = frame
        self.after_id = self.after(SPRITE_FRAME_MS, self._tick)

    def stop(self):
        if self.after_id is not None:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def start(self):
        """Resume an existing animated player without reloading its frames."""
        if self.animate and self.frames and self.after_id is None:
            self._tick()

    def destroy(self):
        self.stop()
        ttk.Frame.destroy(self)
