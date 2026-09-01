# Rock Band REAPER 4 Helpers VKR

Work-in-progress Python 2/Tkinter compatibility port of
[`rock-band-reaper-helpers-vkr`](https://github.com/VeeKiraRay/rock-band-reaper-helpers-vkr)
for the fixed REAPER 4.20 target.

The project is still in development and does not yet contain an end-user
release. Its first runnable implementation slice is now available for target-
host testing.

## Current status

- Phase 1: REAPER 4.20 API and populated-project reads verified.
- Phase 2: Python 2/Tkinter UI runtime accepted with documented keyboard limits.
- Phase 3: guarded audio alignment, verification, and one-step Undo passed.
- Phase 4: initial WIP/V1 feature scope and implementation order selected.
- Phase 4A: General Helper Tk shell, read-only Tab Input, and Metadata Genre
  WIPs implemented.

## Current WIP: General Helper Tab Input

`rock_band_general_helper_vkr.py` opens the first production-style Tkinter
window. The Tab Input area includes Guitar/Bass, Keys/Pro Keys, and Vocal
guide modes; horizontal and vertical six-string input; Add note; result copy;
and the Pro Keys animation-range option. This feature does not modify the
REAPER project.

For REAPER 4.20 testing, preserve the repository layout and register only
`rock_band_general_helper_vkr.py` in the Action List. The entry point imports
its feature modules from `rock_band_general_helper_vkr/` and shared Tk helpers
from `lib/`.

The accepted Tk limitation still applies: while the window is open, REAPER
keyboard shortcuts are unavailable. Mouse interaction with REAPER remains
available, and closing the helper restores normal keyboard handling. The
window defaults to **Always on top** so it remains visible while using REAPER;
the option can be disabled from the bottom bar.

Because REAPER 4.20 runs Python ReaScripts synchronously, launching the helper
with the Action List's **Run** button leaves that particular Action List dialog
waiting until the Tk window closes. This does not freeze REAPER itself. For
normal use, bind the action to a toolbar button or another mouse-driven action
and close the Action List before opening the helper.

## Current WIP: Metadata Genre

The Metadata tab's Genre view ports the modern helper's complete advisory
lookup: 29 supported Rock Band genres, 126 supported subgenres, and 227
real-world genre entries. Choose a broad family and the genre you would use to
describe the song; the Result panel shows ranked supported display names,
reasoning, optional documentation, and redirects for easily confused styles.
It does not read or modify the REAPER project. **Copy result** copies the
current recommendation.

The repository does not yet contain a supported end-user build or installation
procedure. Those will be added here when the first production slice is ready.
