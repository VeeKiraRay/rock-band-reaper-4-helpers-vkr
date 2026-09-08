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
- Phase 4A: General Helper Tk shell, read-only Tab Input, Metadata Genre, and
  calibrated Metadata Difficulty WIPs implemented.
- Phase 4C: Difficulty validation includes read-only Keys, Pro Keys,
  Guitar/Bass, and Drums workflows.

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

## Current WIP: Metadata Difficulty

The Metadata tab's Difficulty view reads the completed Expert charts and
suggests game difficulty ranks for Guitar, Bass, Drums, Keys, Pro Keys, and
Vocals using the frozen calibrated models from the modern helper. Vocal
scoring includes lyric syllables and continuations, authored phrase markers,
pitch movement and register, percussion ranges, and populated HARM2/HARM3
parts. Press **Refresh suggestions** to run the read-only analysis; merely
opening the tab does not scan the project or create an undo point. The cards
show Rock Band-style difficulty dots, the rank's position in its tier, and
warnings. Optional plain-language observations can be shown with **Show
observations**, which is off by default to keep all six ranks compact. **Copy
result** copies the complete author-facing summary, including observations,
without the internal verification measurements.

Suggestions are snapshots. Switching to another REAPER project tab clears
them automatically using the active project identity exposed by REAPER 4.20.
The project name and refresh timestamp are included in the result as an
additional guard against mistaking an older snapshot for the current project.

## Current WIP: Difficulty validation

The General Helper's Difficulty tab includes read-only authoring validation for
`PART KEYS`, the four `PART REAL_KEYS_X/H/M/E` tracks, `PART GUITAR`,
`PART BASS`, and `PART DRUMS`. It auto-detects the tracks and validates Expert,
Hard, Medium, Easy, or all four difficulties.
Keys reports chord, spacing, note-length, sustain, range, and adjacent-tier
reduction issues. Its guarded Copy actions optionally use the same-tier Pro
Keys track to filter onsets and match sustain lengths. Pro Keys additionally
checks lane shifts, chord spans, interval jumps, overlapping gems, Expert
coverage, and missing measures when the host exposes measure formatting. Its
guarded Copy actions transfer playable notes and lane-shift markers from the
immediately higher Pro Keys track. Guitar/Bass checks chord shapes,
note length, overlaps, sustain gaps, force-HOPO markers, trill/tremolo marker
velocity, easier-tier density guidance, and adjacent reductions. The checks
always inspect complete tracks and do not modify the project or create an undo
point. Guitar/Bass also provides guarded Copy to Hard/Medium/Easy actions,
including lower-tier chord-lane compression.

Drums checks kick reductions, fills, roll markers and velocity, crash
preparation, tempo-sensitive density limits, and disco-mix guidance. Across
the four instrument views, guarded Copy to Hard/Medium/Easy actions replace
their defined target ranges, confirm before overwriting authored notes, verify
item chunks immediately before and after writing, refuse unsafe targets, and
create one Undo point.

The repository does not yet contain a supported end-user build or installation
procedure. Those will be added here when the first production slice is ready.
