"""Shared explanatory text for VENUE authoring controls.

Modern counterparts: venue_camera.lua, venue_themes.lua, and defaults.lua.

Python 2.7 compatible.
"""

from __future__ import unicode_literals


DIRECTED_TIPS = {
    'directed_all': 'Shots where guitar, bass, keys, and vocals interact, such as jumping, kicking toward the camera or crowd, or dramatically dropping to their knees.',
    'directed_all_cam': 'Like Directed All, but typically lasts longer. Examples include jumping, kicking toward the camera or crowd, or dramatically dropping to their knees.',
    'directed_all_lt': 'A long panning shot of the entire band. It is more dynamic than standard normal-camera shots such as All Near or All Far.',
    'directed_all_yeah': 'A very dramatic cut, such as the singer pointing into the air in slow motion before a pan across the band. On larger venues without keys, the guitarist may leap and slide on their knees.',
    'directed_crowd': 'A dynamic shot including the crowd, such as a wide stage shot or, in larger venues, an individual shot with nearby crowd members.',
    'directed_drums': 'The drummer hits the cymbals on their kit and may twirl their sticks first.',
    'directed_drums_pnt': 'The drummer points toward the camera with their sticks. The drummer does not always play during this animation.',
    'directed_drums_np': 'Idle drummer animations such as swirling drumsticks, stick tricks, or gesturing toward the camera.',
    'directed_drums_lt': 'A longer directed drum shot.',
    'directed_drums_kd': "Close-up of the drummer's kick pedal.",
    'directed_vocals': 'A broad range of vocalist animations such as pointing upward or toward the crowd, kicking into the air, or kicking the camera.',
    'directed_vocals_np': 'Idle vocalist actions such as kicking into the air or jumping.',
    'directed_vocals_cls': 'A dramatic close-up which may show the vocalist holding the microphone, moving their head, or falling to the floor or their knees.',
    'directed_vocals_cam_pr': 'Exciting vocalist interactions with the crowd, camera, or microphone. Has a longer pre-roll and shorter post-roll than directed_vocals_cam_pt.',
    'directed_vocals_cam_pt': 'Exciting vocalist interactions with the crowd, camera, or microphone. Has a shorter pre-roll and longer post-roll than directed_vocals_cam_pr.',
    'directed_stagedive': 'The vocalist runs off the stage and jumps into the crowd. The shot usually cuts away as the vocalist reaches the crowd.',
    'directed_crowdsurf': 'Like Stage Dive, but includes the vocalist crowd-surfing. It may begin with the vocalist already in the crowd.',
    'directed_bass': 'A wide variety of bassist actions such as kicking, kicking over the camera, or bumping the camera with the instrument. Less theatrical than the guitar equivalent.',
    'directed_crowd_b': 'The bassist interacts with the audience through high-fives or showing off. Useful for quieter breakdown sections.',
    'directed_bass_np': 'Idle bassist actions such as kicking or kicking into the air, but not toward the camera.',
    'directed_bass_cam': 'The bassist shows off for the camera, usually more calmly than the guitarist, and may hit the camera with the instrument.',
    'directed_bass_cls': "Close-up of the bassist's fretboard.",
    'directed_guitar': 'A wide variety of guitarist actions such as sliding on their knees, kicking, kicking over the camera, or bumping the camera with the guitar.',
    'directed_crowd_g': 'The guitarist interacts with the audience through high-fives or showing off. Useful for quieter breakdown sections.',
    'directed_guitar_np': 'Idle guitarist actions such as kicking or kicking into the air, but not toward the camera.',
    'directed_guitar_cls': "Close-up of the guitarist's fretboard.",
    'directed_guitar_cam_pr': 'A broad range of guitar animations such as dropping to the floor or showing off to the camera or crowd. Has a longer pre-roll and shorter post-roll than directed_guitar_cam_pt.',
    'directed_guitar_cam_pt': 'A broad range of guitar animations such as dropping to the floor or showing off to the camera or crowd. Has a shorter pre-roll and longer post-roll than directed_guitar_cam_pr.',
    'directed_keys': 'The keyboard player jumps in the air or slams their hands on the keyboard.',
    'directed_keys_cam': 'The keyboard player rocks out and grooves.',
    'directed_keys_np': 'One of a small set of idle animations in which the keyboard player rocks back and forth.',
    'directed_duo_drums': 'The drummer turns toward or interacts with the camera. Use only while the drummer is singing; otherwise it can look awkward.',
    'directed_duo_bass': 'The bassist and vocalist interact by jamming, leaning together, or sharing the microphone.',
    'directed_duo_guitar': 'The guitarist and vocalist interact by jamming, leaning together, or sharing the microphone.',
    'directed_duo_kv': 'The vocalist and keyboard player rock out together.',
    'directed_duo_gb': 'The guitarist and bassist jam together.',
    'directed_duo_kb': 'The bassist and keyboard player rock out together.',
    'directed_duo_kg': 'The guitarist and keyboard player rock out together.',
    'directed_bre': 'Big Rock Ending camera cut. Author manually at the BRE section only.',
    'directed_brej': 'Big Rock Ending camera cut, jump variant. Author manually at the BRE section only.',
}

LIGHTING_TIPS = {
    'verse': 'Tends toward soft yet full blends, such as orange and green. Varies between venues.',
    'chorus': 'Tends toward stark, dramatic colors such as saturated blue and red. Invokes a peak state and varies between venues.',
    'manual_cool': 'Cool-temperature lighting.',
    'manual_warm': 'Warm-temperature lighting.',
    'dischord': 'Harsh lighting with a blend of dissonant colors.',
    'stomp': 'All lights are either on or off.',
    'loop_cool': 'A blend of cool-temperature colors.',
    'loop_warm': 'A blend of warm-temperature colors.',
    'harmony': 'A blend of lights with a harmonious color palette.',
    'frenzy': 'Frenetic, dissonant lighting that alternates quickly.',
    'silhouettes': 'Dark, atmospheric lighting that shows character silhouettes.',
    'silhouettes_spot': 'Dark, atmospheric lighting that shows illuminated character silhouettes.',
    'searchlights': 'Searchlights that sweep individually.',
    'sweep': 'Lights that sweep together in banks.',
    'strobe_slow': 'Strobe lights that blink on every eighth note.',
    'strobe_fast': 'Strobe lights that blink on every sixteenth note.',
    'blackout_slow': 'Darkens the stage slowly to blackout over two seconds. It does not work if the previous lighting state is too close.',
    'blackout_fast': 'Darkens the stage quickly to blackout over 0.2 seconds.',
    'blackout_spot': 'A blackout state with added underlighting.',
    'flare_slow': 'A bright white flare that fades slowly into the next lighting preset.',
    'flare_fast': 'A bright white flare that fades quickly into the next lighting preset.',
    'bre': 'Frenetic lighting for a Big Rock Ending. It resembles Frenzy, but is more intense.',
}

POSTPROC_TIPS = {
    'bloom.pp': 'Brightens the picture slightly and adds a choppy, low-frame-rate effect.',
    'bright.pp': 'Brightens toward a bloom-like effect and lightens dark colors.',
    'clean_trails.pp': 'Creates a small video-feed delay, like a visual echo.',
    'contrast_a.pp': 'A very gritty, somewhat polarized black-and-white filter.',
    'desat_blue.pp': 'A slightly grainy image with a blue tinge.',
    'desat_posterize_trails.pp': 'Creates a long video-feed delay and flattens colors.',
    'film_16mm.pp': 'A grainy video effect.',
    'film_b+w.pp': 'Reduces colors to a range of gray tones narrower than Film Silvertone.',
    'film_blue_filter.pp': 'Reduces colors to a wide range of blue shades.',
    'film_contrast.pp': 'Makes dark colors darker and light colors lighter.',
    'film_contrast_blue.pp': 'Increases contrast and adds a slight blue hue.',
    'film_contrast_green.pp': 'Increases contrast and adds slightly green hues.',
    'film_contrast_red.pp': 'Increases contrast and adds slightly red hues.',
    'film_sepia_ink.pp': 'Reduces colors to a wide range of yellowish-gray shades.',
    'film_silvertone.pp': 'Reduces colors to a wide range of gray shades.',
    'flicker_trails.pp': 'Creates a video-feed delay, slightly darkens the image, and mutes colors.',
    'horror_movie_special.pp': 'Polarizes colors to either red or black.',
    'photo_negative.pp': 'Inverts colors.',
    'photocopy.pp': 'A choppy, low-frame-rate effect.',
    'posterize.pp': 'Flattens colors, most noticeably in shadows.',
    'ProFilm_a.pp': 'The default post-process effect, with no notable visual treatment.',
    'ProFilm_b.pp': 'Slightly mutes all colors.',
    'ProFilm_mirror_a.pp': 'Mirrors one side of the screen and shifts colors toward oranges, greens, and yellows.',
    'ProFilm_psychedelic_blue_red.pp': 'Polarizes colors to either red or blue.',
    'shitty_tv.pp': 'Very grainy video that dramatically lightens colors.',
    'space_woosh.pp': 'Dramatically lightens colors and creates small red, green, and blue video-feed delays.',
    'video_a.pp': 'Slightly grainy video.',
    'video_bw.pp': 'Reduces colors to gray shades with slight grit and a narrower range than Film Silvertone.',
    'video_security.pp': 'Grainy video with colors reduced to a wide range of green shades.',
    'video_trails.pp': 'Creates a video-feed delay longer than Clean Trails.',
}

BLEND_LIGHTING_TIP = (
    'Copy the lighting preset currently running to the edit cursor so the game '
    'blends into the next lighting event instead of cutting to it.\n\n'
    'Place the anchor a beat or two before the new preset. This reads the VENUE '
    'track, not the dropdown, and refuses an existing blend, an event already at '
    'the cursor, or no preceding preset. The copy carries no keyframes. Fully undoable.')

BLEND_POSTPROC_TIP = (
    'Copy the post-process effect currently running to the edit cursor so the '
    'game blends into the next effect instead of cutting to it.\n\n'
    'Place the anchor a beat or two before the new effect. This reads the VENUE '
    'track, not the dropdown, and refuses an existing blend, an event already at '
    'the cursor, or no preceding effect. Fully undoable.')

KEYFRAME_ALIGN_TIP = (
    'Controls where the first [next] event lands. [first] always remains on the '
    'manual lighting event itself.\n\nKeyframe rate only starts after the chosen '
    'rate; Closest beat snaps to the nearest beat; Downbeat starts at the next '
    'measure. Instrument modes emit [next] only at qualifying note positions.')

KEYFRAME_GENERATE_TIP = (
    'Generate [first]/[next] keyframes from the edit cursor to the next lighting '
    'event, the active time-selection end, or the VENUE item end.\n\nThe cursor '
    'must be on a manual lighting event. Existing keyframes in the range are '
    'cleared first. Fully undoable.')

KEYFRAME_RATE_TIP = (
    'Keyframe rate in beats: how often [next] events are placed. It does not '
    'move [first], which remains on the lighting event. Valid range: 1-8.')

CAMERA_PACING_TIP = (
    'Camera-cut spacing. Named values are measured in sixteenth notes. At 150 '
    'BPM or above, intervals are multiplied by 1.5 to avoid overly rapid cuts.\n\n'
    'Vocal phrase start advances directly to the next PART VOCALS phrase-marker '
    'start; jitter has no effect in that mode.')

CAMERA_JITTER_TIP = (
    'Randomize camera-cut intervals within +/-20% of the selected pacing value '
    'for a more natural feel. Disable it for metrically exact spacing.')

CAMERA_CUSTOM_TIP = (
    'Custom camera-cut interval in sixteenth notes, from 2 to 128. At 150 BPM '
    'or above, this value is multiplied by 1.5 like the named presets.')

CAMERA_ADVANCE_TIP = (
    'Move the edit cursor forward by one camera-pacing interval. After advancing, '
    'choose and add the camera event wanted at the new position.')

REMOVE_TIPS = {
    'Camera': 'Removes all [coop_*] and [directed_*] camera events.',
    'Lighting': 'Removes all [lighting (...)] events.',
    'Post proc': 'Removes all post-process [*.pp] events.',
    'Special': 'Removes [bonusfx], [bonusfx_optional], [first], [next], and [previous] events.',
    'All': 'Removes all camera, lighting, post-process, and special events.',
}


def remove_tip(label):
    detail = REMOVE_TIPS.get(label, '')
    return detail + '\n\nUses the active time selection when present. Fully undoable.'
