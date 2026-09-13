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
- Phase 4A: General Helper Tk shell, project-aware Workflow checklist,
  read-only Tab Input, Metadata Genre, and calibrated Metadata Difficulty
  WIPs implemented.
- Phase 4C: Difficulty validation includes read-only Keys, Pro Keys,
  Guitar/Bass, and Drums workflows.
- Phase 4D: guarded MIDI Length and Pattern views are implemented for
  target-host testing.
- Phase 4E: read-only Venue Actions listing and validation are implemented for
  target-host testing.
- Phase 4F: guarded Venue Events insertion is implemented for target-host
  testing.
- Phase 4G: guarded whole-song Venue theme generation is implemented for
  target-host testing.
- Phase 4H: guarded single-section Venue generation is implemented for
  target-host testing.
- Phase 4I: guarded Venue keyframe regeneration is implemented for target-host
  testing.

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

## Current WIP: General Workflow

The General tab contains a scrollable authoring checklist loaded from the
bundled `resources/workflow/Default.txt` template. It shows completion
progress, can hide completed entries, and can display completion timestamps.
Checking an item saves immediately. For a saved project, progress is stored in
a human-readable `.rbhelper-workflow.json` sidecar beside the `.rpp` file; an
unsaved project's progress lasts only while the helper remains open. Switching
project tabs loads that project's separate checklist state.

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

## Current WIP: MIDI Length and Pattern

The MIDI tab now contains working Length and Pattern views. Length can unify
non-sustain note sizes or normalize sustain gaps for one difficulty range,
using the active time selection when present. Pattern captures Search and
Replace material from a time selection, then lists or navigates matches,
replaces all matches, or tiles the replacement across a selected range.
Opening the MIDI tab and its Refresh buttons scan for MIDI items, so audio-only
tracks are omitted from the selectors. Pattern actions remain disabled until
their required Search and/or Replace capture has been set.

These note operations use the legacy item-chunk codec with pooled-source,
stale-state, verified read-back, rollback, and one-step Undo guards. Pattern
captures are cleared when the active project tab changes. MIDI-item length
sync can safely shrink items; a batch requiring source extension is currently
refused because REAPER 4.20 lacks the MIDI note API used by the modern helper
to extend the underlying source. This limitation remains pending target-host
research rather than silently producing an item with unusable extended space.

## Current WIP: Venue Actions

The Venue tab now exposes the modern helper's seven-sub-tab layout. Its first
working slice is the read-only Actions area: list all VENUE events, list EVENTS
track practice sections, list lighting/post-process events, validate lighting
keyframes and blend anchors, and validate stacked camera coverage for every
possible band lineup. The reports inspect complete MIDI tracks through the
legacy item-chunk reader and optionally scope validation findings to the active
time selection. They never modify the project or create an Undo point.

## Current WIP: Venue Events

The Events sub-tab inserts the modern helper's complete section, crowd, and
global event vocabulary into the `EVENTS` track at the edit cursor. It supports
bare, numbered, and letter-suffixed practice sections and refuses duplicates,
mixed section forms, out-of-order numbering, misplaced sequence entries, and
non-crowd same-position collisions. Each accepted insertion re-reads the track,
checks pooled-source and stale-state safety, writes one FF 01 text event,
verifies the exact result, and creates one Undo point.

Insert bookends remains disabled because its time-signature-safe measure walk
uses an API not yet verified on REAPER 4.20. Clear all remains disabled until a
separately confirmed bulk text-event deletion workflow is implemented.

## Current WIP: Venue Themes gen

The Themes gen sub-tab loads user-provided `.rbtheme` files from the empty
`resources/themes/` folder and generates a complete set of type-1 text events
inside one `VENUE` MIDI item. Theme files are intentionally not distributed or
tracked by this project: copy your own `.rbtheme` files into that folder before
opening the helper. With no themes present, the view displays an alert and
disables generation. It supports theme or user-selected camera pacing, optional interval
jitter, custom cadence, vocal-phrase-start cadence, all keyframe alignment
choices, and beat/half-beat/quarter-beat instrument grids. Section markers on
the `EVENTS` track select theme lighting and post-process pools, keyframe rates,
blend anchors, forced directed cuts, and bonus FX. Projects containing Guitar,
Bass, and Keys receive stacked companion shots for their possible in-game
lineups.

Generation preserves VENUE notes, its track-name and other meta-event types,
source metadata, and text outside the generated song range. It refuses
ambiguous multiple VENUE items, unsupported/shared sources, and stale read
inputs. An accepted generation is verified after read-back and creates one Undo
point; a failed verification restores the original chunk. Verification remains
byte-exact unless the code-controlled semantic fallback recognizes only a
known redundant extended-event header rewrite. The explicit `[end]` and
`[music_start]` EVENTS markers are preferred, with the same item-length and
approximately-three-second fallbacks used by the modern workflow.

## Current WIP: Venue Section gen

The Section gen sub-tab refreshes recognized `[prc_*]` sections from the
`EVENTS` track whenever the view is opened, including merged letter-suffixed
parts, and generates only the selected section. A manual Refresh button remains
available after project edits. **Custom** mode exposes the `.rbtheme`
section-preset values directly: lighting, keyframe rate and alignment,
lighting/post-process blend-in, post-process, a directed cut, and bonus FX.
Keyframe rate is limited to 1-8 beats; both blend-in values are limited to 0-8,
where zero means a hard cut. **Template** mode resolves the matching numbered,
named, or default preset from a user-provided theme.
Both modes share camera pacing, jitter, vocal-phrase pacing, instrument-aware
keyframes, and muted/absent-instrument camera filtering with Themes gen.

Section replacement preserves cameras in the preceding blend-in zone,
lighting/post-process events belonging to the following section, and all text
outside the selected range. It reads the incoming lighting and post-process
state before planning blends, avoids restating a preset already running, and
rechecks the selected EVENTS section and every dependent MIDI item before the
guarded write. Accepted changes create one Undo point.

## Current WIP: Venue Manual gen

Manual gen currently contains a read-only preview-presentation experiment.
Representative camera, lighting, and post-process dropdowns can use an
tooltip shared by closed and open dropdowns or one persistent preview window
shared by every row. Radio buttons switch between the two styles so the
preferred legacy Tk interaction can be selected before the event-insertion
controls are ported. Open-list hover and arrow-key navigation update the active
preview. In the persistent-window version,
hovering a dropdown or its Add button retargets the same window and replaces
its image in place; prototype Add buttons do not write to REAPER.

Tooltip previews are consistently placed to the right of their dropdown,
open option list, or action button so they do not cover selectable rows.

The popup behavior is implemented by a reusable preview manager rather than by
Manual gen itself. Tooltip preview is the proposed default and the persistent
window is the supported alternative. The eventual Settings view will choose
between them; no preference is stored yet. If a Tk build does not expose its
native combobox list, tooltip mode retains selected-value, closed-dropdown, and
Add-button previews while disabling only live movement inside the open list.

The experiment looks for optional camera, lighting, and post-process
spritesheets under `resources/img/spritesheets` by default, and can be pointed
at another spritesheet folder from the UI. Tk 8.5 loads GIF sheets directly;
JPEG sheets require optional Pillow. Missing or unreadable preview assets use a
plain text fallback and never prevent the view from opening.

## Completed Venue Keyframes slice

The Keyframes sub-tab regenerates `[first]`/`[next]` events for each manual
lighting change already present on the `VENUE` track. A repeated adjacent
lighting preset is treated as a blend restatement: it neither starts a new
keyframe sequence nor ends the active one. Each genuine manual-lighting span
ends at the next different lighting event.

Lighting start, closest-beat, downbeat, and instrument-aware alignment modes
are supported, including beat, half-beat, and quarter-beat instrument grids.
The keyframe rate is limited to 1-8 beats. With an active time selection, only
manual-lighting triggers beginning inside the selection are regenerated;
trains belonging to earlier triggers remain untouched. The guarded write
removes only `[first]`, `[next]`, and `[previous]` inside qualifying spans,
preserving all other VENUE events and keyframes outside those spans.

Manual gen event insertion, Preview, sing-along generation, and VENUE subtrack
copying remain deferred until their mutation or polling paths are implemented
and validated.

The repository does not yet contain a supported end-user build or installation
procedure. Those will be added here when the first production slice is ready.
