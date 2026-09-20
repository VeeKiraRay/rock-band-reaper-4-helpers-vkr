# Resources — Installation Guide

The `resources` folder holds optional Venue preview images and user-provided
theme files. Keep this folder beside `rock_band_general_helper_vkr.py` and use
**Extract Here** inside it when installing an image package.

## Expected folder structure

```text
resources/
  img/
    spritesheets/
      camera/             *.jpg  — full-size camera sprites
      camera small/       *.jpg  — smaller camera sprites
      lighting/           *.jpg  — full-size lighting sprites
      lighting small/     *.jpg  — smaller lighting sprites
      postproc/           *.jpg  — full-size post-process sprites
      postproc small/     *.jpg  — smaller post-process sprites
      camera gif/         *.gif  — full-size Tk-compatible camera sprites
      camera small gif/   *.gif  — smaller Tk-compatible camera sprites
      lighting gif/       *.gif  — full-size Tk-compatible lighting sprites
      lighting small gif/ *.gif  — smaller Tk-compatible lighting sprites
      postproc gif/       *.gif  — full-size Tk-compatible post-process sprites
      postproc small gif/ *.gif  — smaller Tk-compatible post-process sprites
  themes/                 *.rbtheme
```

The full-size sheets use 426×240-pixel frames. The smaller sheets use
213×120-pixel frames. The helper resizes either source as needed for the chosen
Preview size and the monitor's display scaling.

## Image packages

The separately distributed packages are available from the project's
[Google Drive resource folder](https://drive.google.com/drive/folders/17JGZVDkMj2JeOipHHXfdxSV8zazmHP0D).

| Priority (highest first) | Package | Format and installed folders | Pillow required |
| ---: | --- | --- | --- |
| 1 | `img_large.zip` | Full-size JPEG: `camera`, `lighting`, `postproc` | Yes |
| 2 | `img_large_gif.zip` | Full-size GIF: `camera gif`, `lighting gif`, `postproc gif` | No |
| 3 | `img_small.zip` | Smaller JPEG: `camera small`, `lighting small`, `postproc small` | Yes |
| 4 | `img_small_gif.zip` | Smaller GIF: `camera small gif`, `lighting small gif`, `postproc small gif` | No |

Choose a GIF package for a dependency-free installation. Choose a JPEG package
with Pillow for higher-color previews. The large and small packages populate
different folders and may be installed side by side. JPEG and GIF packages may
also coexist.

The helper designates one installed package when the script starts and uses it
for the entire session. The first package in the priority table with any of its
expected category folders present is selected. The selected Preview size does
not change the package—the loaded frames are resized for the view.

Files are never mixed between packages. If the designated package is missing a
sheet or a sheet cannot be decoded, Preview names that package and reports the
problem instead of silently borrowing the same event from a lower-priority
set. Likewise, a designated JPEG package without Pillow reports that Pillow is
missing; it does not switch to an installed GIF package. This makes incomplete
or incorrectly extracted packages visible so they can be corrected.

Package detection is fixed until the script closes. After installing, removing,
or repairing a package, restart the General Helper. Remove all three category
folders belonging to an unwanted higher-priority package if you want the next
package in the table to be designated.

To install a package:

1. Download the desired zip.
2. Open the `resources` folder beside the helper launcher.
3. Use **Extract Here** in that folder.
4. Confirm that the result is under `resources/img/spritesheets`, not inside an
   extra directory named after the zip.
5. Reopen the General Helper if it was running during extraction.

For example, extracting `img_large.zip` should create:

```text
resources/img/spritesheets/camera/
resources/img/spritesheets/lighting/
resources/img/spritesheets/postproc/
```

Extracting `img_small_gif.zip` should create:

```text
resources/img/spritesheets/camera small gif/
resources/img/spritesheets/lighting small gif/
resources/img/spritesheets/postproc small gif/
```

## Optional Pillow installation

Pillow is needed only when a JPEG package is designated. The GIF packages work
through Python's bundled Tkinter support without any third-party dependency.

REAPER 4.20 uses Python 2.7 for this helper, so install the pinned
**Pillow 6.2.2** release. Newer Pillow releases do not support Python 2.7.
Close REAPER before changing its Python environment.

First check the architecture of the exact Python installation configured in
REAPER. Adjust the path if yours is installed elsewhere:

```bat
C:\Python27\python.exe -c "import struct; print(struct.calcsize('P') * 8)"
```

The result must match REAPER: `64` for 64-bit REAPER or `32` for 32-bit
REAPER. If that interpreter has a working `pip`, install the pinned binary
package:

```bat
C:\Python27\python.exe -m pip install --only-binary=:all: Pillow==6.2.2
```

If the old version of `pip` cannot connect to PyPI, download the appropriate
wheel from [Pillow 6.2.2 on PyPI](https://pypi.org/project/Pillow/6.2.2/) using
another computer and install the local file. Use the `win_amd64` wheel for the
verified 64-bit configuration, or `win32` only for a matching experimental
32-bit REAPER/Python configuration:

```bat
C:\Python27\python.exe -m pip install C:\path\to\Pillow-6.2.2-cp27-cp27m-win_amd64.whl
```

Verify the installation with the same interpreter:

```bat
C:\Python27\python.exe -c "import PIL; from PIL import Image, ImageTk; print(PIL.__version__)"
```

The expected version is `6.2.2`. Restart REAPER afterward. If the helper still
cannot import Pillow, it is usually using a different Python installation from
the one where Pillow was installed.

Python 2.7 and Pillow 6.2.2 are end-of-life software. Use this old image decoder
only with trusted spritesheets.

## Themes — adding your own

Place `.rbtheme` files directly in `resources/themes`. Reopen the General
Helper to make newly added themes available in **Venue > Themes gen** and the
Template mode of **Venue > Section gen**.

Theme files are not distributed with this project. Existing `.rbtheme` presets
from another Rock Band authoring setup can be copied into this folder.

## What works without optional resources

| Feature | Without the optional resource |
| --- | --- |
| Venue sprite previews | Events fall back to names and descriptive text; authoring actions remain available. |
| Venue theme generation | Themes gen remains unavailable without a `.rbtheme`; Section gen Custom mode and the other Venue tools remain available. |
| Pillow | GIF previews continue to work when a GIF package is installed. |
