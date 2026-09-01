"""Generated genre data.

Modern counterpart: rock_band_general_helper_vkr/metadata_genres_ext.lua
Regenerate with dev/tools/export_genre_tables.lua.
Python 2.7 compatible.
"""

GENRE_FAMILY_ORDER = [
    "rock",
    "metal",
    "punk",
    "pop",
    "electronic",
    "hiphop",
    "rnb",
    "country_folk",
    "jazz_blues",
    "world_other",
]

GENRE_FAMILIES = {
    "country_folk": "Country and Folk",
    "electronic": "Electronic",
    "hiphop": "Hip-Hop and Rap",
    "jazz_blues": "Jazz and Blues",
    "metal": "Metal",
    "pop": "Pop and New Wave",
    "punk": "Punk and Hardcore",
    "rnb": "R&B, Soul and Funk",
    "rock": "Rock",
    "world_other": "World, Classical and Other",
}

EXTENDED_GENRES = [
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "rock",
                "why": "The catch-all for guitar-led rock with no stronger pull in another direction.",
            },
        ],
        "family": "rock",
        "key": "rock_general",
        "label": "Rock (general)",
    },
    {
        "candidates": [
            {
                "genre": "classic_rock",
                "subgenre": "classic_rock",
                "why": "Its own major genre. Use it for the 60s to 80s rock canon.",
            },
            {
                "genre": "rock",
                "subgenre": "rock",
                "why": "A modern band writing in the period style is usually filed as plain rock instead.",
            },
        ],
        "family": "rock",
        "key": "classic_rock",
        "label": "Classic Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "hard_rock",
                "why": "Heavy and riff-driven while still radio-facing. The catalogue leans on this one heavily.",
            },
        ],
        "family": "rock",
        "key": "hard_rock",
        "label": "Hard Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "arena",
                "why": "Big, anthemic and built for singalongs.",
            },
            {
                "genre": "rock",
                "subgenre": "hard_rock",
                "why": "Use this instead when the riffing matters more than the chorus.",
            },
        ],
        "family": "rock",
        "key": "arena_rock",
        "label": "Arena Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "psychedelic",
                "why": "Effects-soaked, exploratory rock.",
            },
        ],
        "family": "rock",
        "key": "psychedelic_rock",
        "label": "Psychedelic Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "garage",
                "why": "Raw, simple and deliberately unpolished.",
            },
            {
                "genre": "punk",
                "subgenre": "garage",
                "why": "Use the punk side when it is faster and shorter than it is bluesy.",
            },
        ],
        "family": "rock",
        "key": "garage_rock",
        "label": "Garage Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "surf",
                "why": "Reverb-drenched instrumental guitar leads.",
            },
        ],
        "family": "rock",
        "key": "surf_rock",
        "label": "Surf Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "rockabilly",
                "why": "Exact match. The documentation names Stray Cats and Reverend Horton Heat.",
            },
        ],
        "family": "rock",
        "key": "rockabilly",
        "label": "Rockabilly",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "rock_and_roll",
                "why": "The 50s original. The documentation names Chuck Berry.",
            },
        ],
        "family": "rock",
        "key": "rock_and_roll",
        "label": "Rock and Roll",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "blues_rock",
                "why": "Blues form played with rock weight and volume.",
            },
            {
                "genre": "blues",
                "subgenre": "electric",
                "why": "Use Blues instead when the blues idiom leads and the rock is the accent.",
            },
        ],
        "family": "rock",
        "key": "blues_rock",
        "label": "Blues Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "folk",
                "why": "Acoustic-rooted songwriting played by a rock band.",
            },
        ],
        "family": "rock",
        "key": "folk_rock",
        "label": "Folk Rock",
    },
    {
        "candidates": [
            {
                "genre": "southern_rock",
                "subgenre": "southern_rock",
                "why": "Its own major genre.",
            },
        ],
        "family": "rock",
        "key": "southern_rock",
        "label": "Southern Rock",
    },
    {
        "candidates": [
            {
                "genre": "glam",
                "subgenre": "glam",
                "why": "Its own major genre. The 70s glitter era rather than the 80s metal one.",
            },
            {
                "genre": "metal",
                "subgenre": "hair",
                "why": "Use Metal / Hair for the 80s Sunset Strip sound instead.",
            },
        ],
        "family": "rock",
        "key": "glam_rock",
        "label": "Glam Rock",
    },
    {
        "candidates": [
            {
                "genre": "glam",
                "subgenre": "goth",
                "why": "The supported home for goth, sitting under Glam.",
            },
            {
                "genre": "new_wave",
                "subgenre": "dark_wave",
                "why": "Prefer Dark Wave when synths carry the song rather than guitars.",
            },
        ],
        "family": "rock",
        "key": "gothic_rock",
        "label": "Gothic Rock",
    },
    {
        "candidates": [
            {
                "genre": "grunge",
                "subgenre": "grunge",
                "why": "Its own major genre. The documentation names Nirvana and Pearl Jam.",
            },
        ],
        "family": "rock",
        "key": "grunge",
        "label": "Grunge",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "hard_rock",
                "why": "Where the catalogue actually files it. Creed and Seether both land here, not under Grunge.",
            },
        ],
        "family": "rock",
        "key": "post_grunge",
        "label": "Post-Grunge",
        "see_also": [
            {
                "key": "grunge",
                "when": "the song belongs to the early 90s wave rather than following it",
            },
        ],
    },
    {
        "candidates": [
            {
                "genre": "alternative",
                "subgenre": "alternative",
                "why": "Its own major genre, and one of the largest buckets in the catalogue.",
            },
        ],
        "family": "rock",
        "key": "alternative_rock",
        "label": "Alternative Rock",
    },
    {
        "candidates": [
            {
                "genre": "alternative",
                "subgenre": "college",
                "why": "Exact match. The documentation names early R.E.M.",
            },
        ],
        "family": "rock",
        "key": "college_rock",
        "label": "College Rock",
    },
    {
        "candidates": [
            {
                "genre": "indie_rock",
                "subgenre": "indie_rock",
                "why": "Its own major genre.",
            },
        ],
        "family": "rock",
        "key": "indie_rock",
        "label": "Indie Rock",
    },
    {
        "candidates": [
            {
                "genre": "alternative",
                "subgenre": "alternative",
                "why": "The 90s British guitar-pop wave sits with alternative.",
            },
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Use Pop-Rock when the song is more hook than edge.",
            },
        ],
        "family": "rock",
        "key": "britpop",
        "label": "Britpop",
    },
    {
        "candidates": [
            {
                "genre": "indie_rock",
                "subgenre": "post_rock",
                "why": "Exact match. Often instrumental, built on texture and dynamics.",
            },
        ],
        "family": "rock",
        "key": "post_rock",
        "label": "Post-Rock",
    },
    {
        "candidates": [
            {
                "genre": "indie_rock",
                "subgenre": "math_rock",
                "why": "Exact match. Odd meters and angular writing with an indie tone.",
            },
        ],
        "family": "rock",
        "key": "math_rock",
        "label": "Math Rock",
    },
    {
        "candidates": [
            {
                "genre": "indie_rock",
                "subgenre": "shoegazing",
                "why": "Exact match. Layered guitar wash with vocals buried as texture.",
            },
        ],
        "family": "rock",
        "key": "shoegaze",
        "label": "Shoegaze",
    },
    {
        "candidates": [
            {
                "genre": "indie_rock",
                "subgenre": "shoegazing",
                "why": "The closest supported sound: hazy, texture-led and vocal-soft.",
            },
            {
                "genre": "indie_rock",
                "subgenre": "indie_rock",
                "why": "Use the plain indie entry when the songs are more direct than atmospheric.",
            },
        ],
        "family": "rock",
        "key": "dream_pop",
        "label": "Dream Pop",
    },
    {
        "candidates": [
            {
                "genre": "indie_rock",
                "subgenre": "lo_fi",
                "why": "Exact match. Audible home production is the defining trait.",
            },
        ],
        "family": "rock",
        "key": "lo_fi",
        "label": "Lo-fi",
    },
    {
        "candidates": [
            {
                "genre": "indie_rock",
                "subgenre": "noise",
                "why": "Exact match. Dissonance and effects over conventional structure.",
            },
        ],
        "family": "rock",
        "key": "noise_rock",
        "label": "Noise Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "rock",
                "why": "No jam category exists, and extended improvisation alone does not move the genre.",
            },
            {
                "genre": "rock",
                "subgenre": "psychedelic",
                "why": "Use this when the jamming is exploratory rather than groove-based.",
            },
        ],
        "family": "rock",
        "key": "jam_band",
        "label": "Jam Band",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "Down-tuned and riff-led enough that the catalogue treats it as metal.",
            },
            {
                "genre": "rock",
                "subgenre": "hard_rock",
                "why": "Prefer this when the songs stay groovy rather than heavy.",
            },
        ],
        "family": "rock",
        "key": "stoner_rock",
        "label": "Stoner Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "psychedelic",
                "why": "Long, drifting and effects-led.",
            },
            {
                "genre": "prog",
                "subgenre": "prog_rock",
                "why": "Use Prog when the arrangements are composed rather than drifting.",
            },
        ],
        "family": "rock",
        "key": "space_rock",
        "label": "Space Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "psychedelic",
                "why": "Repetition-driven experimental rock, closest to the psychedelic entry.",
            },
            {
                "genre": "indie_rock",
                "subgenre": "post_rock",
                "why": "Prefer this for the motorik, largely instrumental end.",
            },
        ],
        "family": "rock",
        "key": "krautrock",
        "label": "Krautrock",
    },
    {
        "candidates": [
            {
                "genre": "prog",
                "subgenre": "prog_rock",
                "why": "Its own major genre with a single subgenre. The documentation names Rush and Yes.",
            },
        ],
        "family": "rock",
        "key": "prog_rock",
        "label": "Progressive Rock",
    },
    {
        "candidates": [
            {
                "genre": "prog",
                "subgenre": "prog_rock",
                "why": "The supported home for composed, unconventional rock.",
            },
            {
                "genre": "alternative",
                "subgenre": "alternative",
                "why": "Use this when it is more left-field than technical.",
            },
        ],
        "family": "rock",
        "key": "art_rock",
        "label": "Art Rock",
    },
    {
        "candidates": [
            {
                "genre": "prog",
                "subgenre": "prog_rock",
                "why": "Orchestral scale and long forms put it with prog.",
            },
        ],
        "family": "rock",
        "key": "symphonic_rock",
        "label": "Symphonic Rock",
    },
    {
        "candidates": [
            {
                "genre": "j_rock",
                "subgenre": "j_rock",
                "why": "Its own major genre, defined by origin rather than by sound.",
            },
        ],
        "family": "rock",
        "key": "j_rock",
        "label": "J-Rock",
    },
    {
        "candidates": [
            {
                "genre": "inspirational",
                "subgenre": "inspirational",
                "why": "The supported genre is defined by lyrical content, not by the arrangement.",
            },
            {
                "genre": "rock",
                "subgenre": "rock",
                "why": "Use the musical genre instead if the lyrics are not the point of the song.",
            },
        ],
        "family": "rock",
        "key": "christian_rock",
        "label": "Christian Rock",
    },
    {
        "candidates": [
            {
                "genre": "rock",
                "subgenre": "rock",
                "why": "No instrumental category exists; file by the music rather than by the absence of vocals.",
            },
        ],
        "family": "rock",
        "key": "instrumental_rock",
        "label": "Instrumental Rock",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "The general metal bucket, and a large one in the catalogue.",
            },
        ],
        "family": "metal",
        "key": "heavy_metal",
        "label": "Heavy Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "No era-specific category exists; the plain metal entry is the home for it.",
            },
            {
                "genre": "classic_rock",
                "subgenre": "classic_rock",
                "why": "Only for the earliest, most rock-leaning end of it.",
            },
        ],
        "family": "metal",
        "key": "nwobhm",
        "label": "NWOBHM",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "thrash",
                "why": "Exact match. The documentation names the Big 4.",
            },
        ],
        "family": "metal",
        "key": "thrash_metal",
        "label": "Thrash Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "speed",
                "why": "Exact match, under the Metal genre.",
            },
            {
                "genre": "metal",
                "subgenre": "thrash",
                "why": "Prefer Thrash when the riffing is palm-muted and aggressive rather than melodic.",
            },
        ],
        "family": "metal",
        "key": "speed_metal",
        "label": "Speed Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "thrash",
                "why": "Grew directly out of thrash and keeps its riff vocabulary at lower tempo.",
            },
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "Use the general entry when the groove is closer to mainstream metal.",
            },
        ],
        "family": "metal",
        "key": "groove_metal",
        "label": "Groove Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "death",
                "why": "Exact match. Growled vocals and double-bass drumming.",
            },
        ],
        "family": "metal",
        "key": "death_metal",
        "label": "Death Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "death",
                "why": "Still death metal by vocal and rhythm; the melody does not move it out.",
            },
            {
                "genre": "metal",
                "subgenre": "power",
                "why": "Only when clean vocals carry the song and the melodies turn major-key. Gothenburg-style melodeath stays minor and growled.",
            },
        ],
        "family": "metal",
        "key": "melodic_death_metal",
        "label": "Melodic Death Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "death",
                "why": "The parent style. Technicality does not move it out of death metal.",
            },
            {
                "genre": "metal",
                "subgenre": "progressive",
                "why": "Use this when the foundation is prog metal rather than death metal: clean passages, dynamics, odd meters as structure rather than as difficulty.",
            },
        ],
        "family": "metal",
        "key": "technical_death_metal",
        "label": "Technical Death Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "death",
                "why": "The closest supported extreme-metal bucket; no grind category exists.",
            },
            {
                "genre": "punk",
                "subgenre": "hardcore",
                "why": "Prefer this for the punk-rooted end with short, fast songs.",
            },
        ],
        "family": "metal",
        "key": "grindcore",
        "label": "Grindcore",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "black",
                "why": "Exact match. The documentation names Emperor and Mayhem.",
            },
        ],
        "family": "metal",
        "key": "black_metal",
        "label": "Black Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "black",
                "why": "Keeps black metal tremolo and blast beats underneath the wash.",
            },
            {
                "genre": "indie_rock",
                "subgenre": "shoegazing",
                "why": "Use this when the atmosphere leads and the metal is texture.",
            },
        ],
        "family": "metal",
        "key": "blackgaze",
        "label": "Blackgaze",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "black",
                "why": "The style grew out of black metal and most of its founders played it. Listen for tremolo riffing and blast beats.",
            },
            {
                "genre": "metal",
                "subgenre": "power",
                "why": "Prefer Power when the vocals are clean and the melodies are anthemic.",
            },
            {
                "genre": "metal",
                "subgenre": "death",
                "why": "Norse themes over melodic death metal riffing and growls. Amon Amarth is the band most often called Viking metal by mistake.",
            },
        ],
        "family": "metal",
        "key": "viking_metal",
        "label": "Viking Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "power",
                "why": "The melodic, anthemic branch, where clean vocals sit over folk instrumentation.",
            },
            {
                "genre": "metal",
                "subgenre": "black",
                "why": "Use this for the harsh-vocal, pagan branch built on black metal.",
            },
            {
                "genre": "metal",
                "subgenre": "death",
                "why": "Use this for the melodic death metal branch, where the growls and riffing carry the song.",
            },
        ],
        "family": "metal",
        "key": "folk_metal",
        "label": "Folk Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "power",
                "why": "Exact match, and the single largest metal subgenre in the catalogue.",
            },
        ],
        "family": "metal",
        "key": "power_metal",
        "label": "Power Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "power",
                "why": "The documentation lists Nightwish under Power, which is this style exactly.",
            },
            {
                "genre": "metal",
                "subgenre": "progressive",
                "why": "Use this when the arrangements are complex rather than anthemic.",
            },
        ],
        "family": "metal",
        "key": "symphonic_metal",
        "label": "Symphonic Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "progressive",
                "why": "Exact match. The documentation names Dream Theater.",
            },
            {
                "genre": "prog",
                "subgenre": "prog_rock",
                "why": "Use Prog when the song is more progressive than it is heavy.",
            },
        ],
        "family": "metal",
        "key": "progressive_metal",
        "label": "Progressive Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "progressive",
                "why": "Where Periphery is filed. Extended-range riffing with prog structure.",
            },
            {
                "genre": "prog",
                "subgenre": "prog_rock",
                "why": "Where TesseracT is filed. Use this for the atmospheric, clean-sung end.",
            },
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "The catalogue also uses the plain metal entry for After the Burial.",
            },
        ],
        "family": "metal",
        "key": "djent",
        "label": "Djent",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "progressive",
                "why": "The documentation describes Progressive as genre-mixing and boundary-pushing.",
            },
        ],
        "family": "metal",
        "key": "avant_garde_metal",
        "label": "Avant-Garde Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "No doom category exists; slow and heavy still files as metal.",
            },
            {
                "genre": "metal",
                "subgenre": "black",
                "why": "Only for genuinely blackened doom: tremolo riffing, blast beats and black metal atmosphere. Harsh vocals alone are not enough.",
            },
        ],
        "family": "metal",
        "key": "doom_metal",
        "label": "Doom Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "The general metal entry is the closest supported home.",
            },
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "Prefer this when hardcore vocals and breakdowns are present.",
            },
        ],
        "family": "metal",
        "key": "sludge_metal",
        "label": "Sludge Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "Down-tuned riff metal with no dedicated category.",
            },
        ],
        "family": "metal",
        "key": "stoner_metal",
        "label": "Stoner Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "No drone category exists; the general metal entry is the fallback.",
            },
            {
                "genre": "other",
                "subgenre": "experimental",
                "why": "Use this when the piece is closer to sound art than to a song.",
            },
        ],
        "family": "metal",
        "key": "drone_metal",
        "label": "Drone Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "Metal underneath, with the goth element in the atmosphere.",
            },
            {
                "genre": "glam",
                "subgenre": "goth",
                "why": "Use this when the goth identity outweighs the metal.",
            },
        ],
        "family": "metal",
        "key": "gothic_metal",
        "label": "Gothic Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "industrial",
                "why": "Exact match. The documentation names Ministry and Rammstein.",
            },
        ],
        "family": "metal",
        "key": "industrial_metal",
        "label": "Industrial Metal",
    },
    {
        "candidates": [
            {
                "genre": "nu_metal",
                "subgenre": "nu_metal",
                "why": "Its own major genre. The documentation names KoRn and Limp Bizkit.",
            },
        ],
        "family": "metal",
        "key": "nu_metal",
        "label": "Nu-Metal",
    },
    {
        "candidates": [
            {
                "genre": "nu_metal",
                "subgenre": "nu_metal",
                "why": "The documentation defines Nu-Metal as hip-hop rhythm over down-tuned riffs.",
            },
            {
                "genre": "metal",
                "subgenre": "alternative",
                "why": "Use this when the rapping is occasional rather than the main vocal.",
            },
        ],
        "family": "metal",
        "key": "rap_metal",
        "label": "Rap Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "alternative",
                "why": "Exact match, under the Metal genre.",
            },
            {
                "genre": "rock",
                "subgenre": "hard_rock",
                "why": "The catalogue often uses Hard Rock for the radio-facing end of this.",
            },
        ],
        "family": "metal",
        "key": "alternative_metal",
        "label": "Alternative Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "alternative",
                "why": "The closest supported bucket for groove-led crossover metal.",
            },
        ],
        "family": "metal",
        "key": "funk_metal",
        "label": "Funk Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metal",
                "why": "No post-metal category exists; slow, heavy and atmospheric still files as metal.",
            },
            {
                "genre": "indie_rock",
                "subgenre": "post_rock",
                "why": "Use this when it is post-rock dynamics with metal weight rather than metal with long builds.",
            },
        ],
        "family": "metal",
        "key": "post_metal",
        "label": "Post-Metal",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "industrial",
                "why": "The supported Industrial entry sits under Metal and fits guitar-led industrial.",
            },
            {
                "genre": "pop_dance_electronic",
                "subgenre": "industrial",
                "why": "Use the electronic Industrial entry when programming leads and the guitars are texture.",
            },
        ],
        "family": "metal",
        "key": "industrial_rock",
        "label": "Industrial Rock",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "Exact match, and the largest metal subgenre bucket after Power.",
            },
        ],
        "family": "metal",
        "key": "metalcore",
        "label": "Metalcore",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "Sits in the same -core bucket; the clean choruses do not move it out.",
            },
        ],
        "family": "metal",
        "key": "melodic_metalcore",
        "label": "Melodic Metalcore",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "The catalogue treats the whole -core family as one bucket.",
            },
            {
                "genre": "metal",
                "subgenre": "death",
                "why": "Prefer this when growls and blast beats outweigh the breakdowns.",
            },
        ],
        "family": "metal",
        "key": "deathcore",
        "label": "Deathcore",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "Where Converge and The Dillinger Escape Plan are filed.",
            },
            {
                "genre": "metal",
                "subgenre": "progressive",
                "why": "Use this when the complexity is the point rather than the aggression.",
            },
        ],
        "family": "metal",
        "key": "mathcore",
        "label": "Mathcore",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "Sits inside the same -core bucket.",
            },
            {
                "genre": "punk",
                "subgenre": "hardcore",
                "why": "Prefer the punk side when the songs keep hardcore length and tempo.",
            },
        ],
        "family": "metal",
        "key": "metallic_hardcore",
        "label": "Metallic Hardcore",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "hair",
                "why": "Exact match. The documentation names Poison and Motley Crue.",
            },
        ],
        "family": "metal",
        "key": "hair_metal",
        "label": "Hair Metal",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "classic",
                "why": "The original three-chord form.",
            },
            {
                "genre": "punk",
                "subgenre": "alternative",
                "why": "The catalogue uses this broadly for modern punk of no fixed sub-style.",
            },
        ],
        "family": "punk",
        "key": "punk_rock",
        "label": "Punk Rock",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "pop_punk",
                "why": "Exact match. The documentation names Green Day and Blink 182.",
            },
        ],
        "family": "punk",
        "key": "pop_punk",
        "label": "Pop-Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "pop_punk",
                "why": "The pop-punk half: catchy melodies and pop-punk song structure carry the track.",
            },
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "The other half: heavy breakdowns and screamed vocals. Pick by which one dominates.",
            },
            {
                "genre": "rock",
                "subgenre": "hard_rock",
                "why": "What the RB3-era catalogue used for A Day to Remember, the defining band of the style.",
            },
        ],
        "family": "punk",
        "key": "easycore",
        "label": "Easycore",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "pop_punk",
                "why": "Shares the tempo and production values of pop-punk.",
            },
            {
                "genre": "punk",
                "subgenre": "alternative",
                "why": "Where the catalogue files MxPx and Teenage Bottlerocket.",
            },
        ],
        "family": "punk",
        "key": "skate_punk",
        "label": "Skate Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "hardcore",
                "why": "Exact match. Fast, short and shouted.",
            },
        ],
        "family": "punk",
        "key": "hardcore_punk",
        "label": "Hardcore Punk",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "Where the heavier end sits: screamed vocals and breakdowns.",
            },
            {
                "genre": "rock",
                "subgenre": "hard_rock",
                "why": "Use it for the melodic, radio-facing end, which the catalogue files as hard rock.",
            },
            {
                "genre": "alternative",
                "subgenre": "alternative",
                "why": "The catalogue also files Emarosa and A Skylit Drive here.",
            },
        ],
        "family": "punk",
        "key": "post_hardcore",
        "label": "Post-Hardcore",
    },
    {
        "candidates": [
            {
                "genre": "emo",
                "subgenre": "emo",
                "why": "Screamo is an offshoot of emo, and Emo is its own supported genre. Right for the original 90s style.",
            },
            {
                "genre": "punk",
                "subgenre": "hardcore",
                "why": "The other half of its ancestry. Use this for the chaotic, hardcore-paced end.",
            },
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "Right only for the loose 2000s use of the word, meaning post-hardcore and melodic metalcore bands.",
            },
        ],
        "family": "punk",
        "key": "screamo",
        "label": "Screamo",
    },
    {
        "candidates": [
            {
                "genre": "emo",
                "subgenre": "emo",
                "why": "Its own major genre.",
            },
        ],
        "family": "punk",
        "key": "emo",
        "label": "Emo",
    },
    {
        "candidates": [
            {
                "genre": "emo",
                "subgenre": "emo",
                "why": "Its own major genre covers this directly.",
            },
            {
                "genre": "punk",
                "subgenre": "pop_punk",
                "why": "Use this when the hooks and tempo are pop-punk first.",
            },
        ],
        "family": "punk",
        "key": "emo_pop",
        "label": "Emo Pop",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "classic",
                "why": "Keeps the classic punk form and attitude.",
            },
        ],
        "family": "punk",
        "key": "street_punk",
        "label": "Street Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "classic",
                "why": "A classic-era punk offshoot with no category of its own.",
            },
        ],
        "family": "punk",
        "key": "oi",
        "label": "Oi!",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "hardcore",
                "why": "Hardcore punk with metal weight.",
            },
            {
                "genre": "metal",
                "subgenre": "death",
                "why": "Use this for the most extreme, growled end.",
            },
        ],
        "family": "punk",
        "key": "crust_punk",
        "label": "Crust Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "hardcore",
                "why": "Defined by a hardcore punk drum pattern.",
            },
        ],
        "family": "punk",
        "key": "d_beat",
        "label": "D-Beat",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "hardcore",
                "why": "Hardcore taken to its fastest and shortest extreme.",
            },
        ],
        "family": "punk",
        "key": "powerviolence",
        "label": "Powerviolence",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "hardcore",
                "why": "Musically hardcore; the politics do not change the filing.",
            },
            {
                "genre": "punk",
                "subgenre": "classic",
                "why": "Use this for the earlier, less aggressive end.",
            },
        ],
        "family": "punk",
        "key": "anarcho_punk",
        "label": "Anarcho-Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "garage",
                "why": "Exact match, under the Punk genre.",
            },
        ],
        "family": "punk",
        "key": "garage_punk",
        "label": "Garage Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "dance_punk",
                "why": "Exact match, under the Punk genre.",
            },
        ],
        "family": "punk",
        "key": "dance_punk",
        "label": "Dance-Punk",
    },
    {
        "candidates": [
            {
                "genre": "new_wave",
                "subgenre": "new_wave",
                "why": "The supported genre closest to the late 70s and early 80s post-punk wave.",
            },
            {
                "genre": "indie_rock",
                "subgenre": "noise",
                "why": "The documentation calls Noise an off-shoot of post-punk.",
            },
            {
                "genre": "alternative",
                "subgenre": "alternative",
                "why": "Use this for modern post-punk revival bands.",
            },
        ],
        "family": "punk",
        "key": "post_punk",
        "label": "Post-Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "classic",
                "why": "Classic punk form with horror imagery.",
            },
            {
                "genre": "glam",
                "subgenre": "goth",
                "why": "Use this when the goth presentation leads.",
            },
        ],
        "family": "punk",
        "key": "horror_punk",
        "label": "Horror Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "alternative",
                "why": "Where Flogging Molly and Flatfoot 56 are filed.",
            },
        ],
        "family": "punk",
        "key": "celtic_punk",
        "label": "Celtic Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "alternative",
                "why": "The catalogue uses the alternative punk entry for folk-inflected punk.",
            },
        ],
        "family": "punk",
        "key": "folk_punk",
        "label": "Folk Punk",
    },
    {
        "candidates": [
            {
                "genre": "reggae_ska",
                "subgenre": "ska",
                "why": "The documentation names Reel Big Fish and Less Than Jake under Ska.",
            },
            {
                "genre": "punk",
                "subgenre": "alternative",
                "why": "Use this when the punk outweighs the horns.",
            },
        ],
        "family": "punk",
        "key": "ska_punk",
        "label": "Ska Punk",
    },
    {
        "candidates": [
            {
                "genre": "punk",
                "subgenre": "alternative",
                "why": "The closest supported bucket for the 90s punk underground.",
            },
            {
                "genre": "alternative",
                "subgenre": "alternative",
                "why": "Use this for the more indie-leaning end.",
            },
        ],
        "family": "punk",
        "key": "riot_grrrl",
        "label": "Riot Grrrl",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "The documentation names Lady Gaga and Madonna here.",
            },
        ],
        "family": "pop",
        "key": "pop",
        "label": "Pop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Hook-led rock with pop structure.",
            },
            {
                "genre": "punk",
                "subgenre": "pop_punk",
                "why": "Use this when the tempo and edge lean punk.",
            },
        ],
        "family": "pop",
        "key": "power_pop",
        "label": "Power Pop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "teen_rock",
                "why": "The closest supported category. It is named Teen Rock, so expect a band sound rather than produced pop.",
            },
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Use plain Pop when it is not aimed at a teen market specifically.",
            },
        ],
        "family": "pop",
        "key": "teen_pop",
        "label": "Teen Pop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "soft_rock",
                "why": "Exact match, under the Pop-Rock genre.",
            },
        ],
        "family": "pop",
        "key": "soft_rock",
        "label": "Soft Rock",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "contemporary",
                "why": "The supported category intended to cover this area: polished, adult-facing pop rock.",
            },
        ],
        "family": "pop",
        "key": "adult_contemporary",
        "label": "Adult Contemporary",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "contemporary_folk",
                "why": "The supported home for acoustic, lyric-led solo writing.",
            },
            {
                "genre": "pop_rock",
                "subgenre": "contemporary",
                "why": "Use this when the production is full-band and radio-facing.",
            },
        ],
        "family": "pop",
        "key": "singer_songwriter",
        "label": "Singer-Songwriter",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Straightforward pop with no dedicated category.",
            },
        ],
        "family": "pop",
        "key": "bubblegum_pop",
        "label": "Bubblegum Pop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Pop songwriting with orchestral arrangement.",
            },
            {
                "genre": "indie_rock",
                "subgenre": "indie_rock",
                "why": "Use this for the modern indie end of it.",
            },
        ],
        "family": "pop",
        "key": "baroque_pop",
        "label": "Baroque Pop",
    },
    {
        "candidates": [
            {
                "genre": "indie_rock",
                "subgenre": "indie_rock",
                "why": "The supported indie bucket covers pop-leaning indie too.",
            },
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Use this when the production is polished rather than homemade.",
            },
        ],
        "family": "pop",
        "key": "indie_pop",
        "label": "Indie Pop",
    },
    {
        "candidates": [
            {
                "genre": "new_wave",
                "subgenre": "synthpop",
                "why": "Pop songs built on synths, which is what the supported Synthpop entry describes.",
            },
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Use this when it reads as mainstream pop that happens to be produced electronically.",
            },
        ],
        "family": "pop",
        "key": "electropop",
        "label": "Electropop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Pop first. The documentation files Lady Gaga and Madonna here, which is this exactly.",
            },
            {
                "genre": "pop_dance_electronic",
                "subgenre": "dance",
                "why": "Use this when the track is built for the floor rather than for the radio.",
            },
        ],
        "family": "pop",
        "key": "dance_pop",
        "label": "Dance-Pop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "Pop songwriting is still the frame, however unusual the arrangement.",
            },
            {
                "genre": "indie_rock",
                "subgenre": "indie_rock",
                "why": "Use this for the independent, left-field end.",
            },
            {
                "genre": "other",
                "subgenre": "experimental",
                "why": "Only when the song abandons pop structure altogether.",
            },
        ],
        "family": "pop",
        "key": "art_pop",
        "label": "Art Pop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "File by sound. There is no supported category for national origin except J-Rock.",
            },
        ],
        "family": "pop",
        "key": "k_pop",
        "label": "K-Pop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "pop",
                "why": "File by sound rather than origin.",
            },
            {
                "genre": "j_rock",
                "subgenre": "j_rock",
                "why": "Use J-Rock if the song is guitar-led enough to read as rock.",
            },
        ],
        "family": "pop",
        "key": "j_pop",
        "label": "J-Pop",
    },
    {
        "candidates": [
            {
                "genre": "pop_rock",
                "subgenre": "soft_rock",
                "why": "Smooth, session-played pop rock is the closest supported sound.",
            },
            {
                "genre": "rnb_soul_funk",
                "subgenre": "funk",
                "why": "Use this when the groove and horns lead.",
            },
        ],
        "family": "pop",
        "key": "city_pop",
        "label": "City Pop",
    },
    {
        "candidates": [
            {
                "genre": "new_wave",
                "subgenre": "new_wave",
                "why": "Its own major genre with a detailed description in the documentation.",
            },
        ],
        "family": "pop",
        "key": "new_wave",
        "label": "New Wave",
    },
    {
        "candidates": [
            {
                "genre": "new_wave",
                "subgenre": "synthpop",
                "why": "Exact match. Where the catalogue files Freezepop and Plushgun.",
            },
        ],
        "family": "pop",
        "key": "synthpop",
        "label": "Synthpop",
    },
    {
        "candidates": [
            {
                "genre": "new_wave",
                "subgenre": "electroclash",
                "why": "Exact match, under the New Wave genre.",
            },
        ],
        "family": "pop",
        "key": "electroclash",
        "label": "Electroclash",
    },
    {
        "candidates": [
            {
                "genre": "new_wave",
                "subgenre": "dark_wave",
                "why": "Exact match. The documentation calls it the modern expansion of gothic rock.",
            },
        ],
        "family": "pop",
        "key": "darkwave",
        "label": "Dark Wave",
    },
    {
        "candidates": [
            {
                "genre": "new_wave",
                "subgenre": "new_wave",
                "why": "A new wave movement with no separate category.",
            },
            {
                "genre": "new_wave",
                "subgenre": "synthpop",
                "why": "Use this when synths and sequencing carry the song.",
            },
        ],
        "family": "pop",
        "key": "new_romantic",
        "label": "New Romantic",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "oldies",
                "why": "Exact match on the supported category.",
            },
            {
                "genre": "rock",
                "subgenre": "rock_and_roll",
                "why": "Prefer this when the song is specifically 50s rock and roll.",
            },
        ],
        "family": "pop",
        "key": "oldies",
        "label": "Oldies",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "oldies",
                "why": "The supported home for pre-rock vocal pop.",
            },
            {
                "genre": "rnb_soul_funk",
                "subgenre": "rhythm_and_blues",
                "why": "Use this when the group is filed as an R&B act.",
            },
        ],
        "family": "pop",
        "key": "doo_wop",
        "label": "Doo-Wop",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "a_capella",
                "why": "Exact match. Note the supported list spells it \"A Capella\".",
            },
        ],
        "family": "pop",
        "key": "a_cappella",
        "label": "A Cappella",
    },
    {
        "candidates": [
            {
                "genre": "novelty",
                "subgenre": "novelty",
                "why": "Its own major genre. The documentation names Weird Al.",
            },
        ],
        "family": "pop",
        "key": "novelty",
        "label": "Novelty",
    },
    {
        "candidates": [
            {
                "genre": "novelty",
                "subgenre": "novelty",
                "why": "The documentation names parody covers specifically.",
            },
        ],
        "family": "pop",
        "key": "parody",
        "label": "Parody",
    },
    {
        "candidates": [
            {
                "genre": "novelty",
                "subgenre": "novelty",
                "why": "The documentation defines Novelty as songs made primarily to be funny.",
            },
        ],
        "family": "pop",
        "key": "comedy",
        "label": "Comedy",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "other",
                "why": "Holiday music is an occasion, not a sound. File by the arrangement if you can.",
            },
            {
                "genre": "novelty",
                "subgenre": "novelty",
                "why": "Use this only when the song is comedic.",
            },
        ],
        "family": "pop",
        "key": "holiday",
        "label": "Holiday / Christmas",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "other",
                "why": "No show-tune category exists.",
            },
        ],
        "family": "pop",
        "key": "musical_theatre",
        "label": "Musical Theatre",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "other",
                "why": "A source, not a style. File by the arrangement where you can.",
            },
            {
                "genre": "pop_dance_electronic",
                "subgenre": "chiptune",
                "why": "Use this when the sound is genuinely chip-based.",
            },
        ],
        "family": "pop",
        "key": "video_game_music",
        "label": "Video Game Music",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "electronica",
                "why": "The general supported bucket for electronic music.",
            },
        ],
        "family": "electronic",
        "key": "electronica",
        "label": "Electronica",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "house",
                "why": "Exact match, under the Pop/Dance/Electronic genre.",
            },
        ],
        "family": "electronic",
        "key": "house",
        "label": "House",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "techno",
                "why": "Exact match, under the Pop/Dance/Electronic genre.",
            },
        ],
        "family": "electronic",
        "key": "techno",
        "label": "Techno",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "trance",
                "why": "Exact match, under the Pop/Dance/Electronic genre.",
            },
        ],
        "family": "electronic",
        "key": "trance",
        "label": "Trance",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "dance",
                "why": "Exact match, under the Pop/Dance/Electronic genre.",
            },
        ],
        "family": "electronic",
        "key": "dance",
        "label": "Dance",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "dance",
                "why": "The supported dance entry is the closest fit.",
            },
        ],
        "family": "electronic",
        "key": "eurodance",
        "label": "Eurodance",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "drum_and_bass",
                "why": "Exact match. The documentation names Goldie and Squarepusher.",
            },
        ],
        "family": "electronic",
        "key": "drum_and_bass",
        "label": "Drum and Bass",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "drum_and_bass",
                "why": "The style drum and bass grew out of, and the supported entry that covers it.",
            },
            {
                "genre": "pop_dance_electronic",
                "subgenre": "breakbeat",
                "why": "Use this for the earlier, breakbeat-led form.",
            },
        ],
        "family": "electronic",
        "key": "jungle",
        "label": "Jungle",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "breakbeat",
                "why": "Exact match. The documentation names The Prodigy.",
            },
        ],
        "family": "electronic",
        "key": "breakbeat",
        "label": "Breakbeat",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "breakbeat",
                "why": "The documentation files The Prodigy under Breakbeat, which is this sound.",
            },
        ],
        "family": "electronic",
        "key": "big_beat",
        "label": "Big Beat",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "electronica",
                "why": "No dubstep category exists; the general electronic entry is the fallback.",
            },
            {
                "genre": "pop_dance_electronic",
                "subgenre": "hardcore_dance",
                "why": "Use this for the aggressive, high-energy end.",
            },
        ],
        "family": "electronic",
        "key": "dubstep",
        "label": "Dubstep",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "garage",
                "why": "The electronic Garage entry, not the rock one. Both names exist in the supported list.",
            },
        ],
        "family": "electronic",
        "key": "uk_garage",
        "label": "UK Garage / 2-Step",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "electronica",
                "why": "The general electronic entry; no glitch category exists.",
            },
            {
                "genre": "other",
                "subgenre": "experimental",
                "why": "Use this when the artefacts are the piece rather than an effect applied to it.",
            },
        ],
        "family": "electronic",
        "key": "glitch",
        "label": "Glitch",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "ambient",
                "why": "Exact match, under the Pop/Dance/Electronic genre.",
            },
        ],
        "family": "electronic",
        "key": "ambient",
        "label": "Ambient",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "downtempo",
                "why": "Exact match, under the Pop/Dance/Electronic genre.",
            },
        ],
        "family": "electronic",
        "key": "downtempo",
        "label": "Downtempo",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "electronica",
                "why": "The general electronic entry; no IDM category exists.",
            },
            {
                "genre": "other",
                "subgenre": "experimental",
                "why": "Use this for the most abstract end.",
            },
        ],
        "family": "electronic",
        "key": "idm",
        "label": "IDM",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "chiptune",
                "why": "Exact match, and well attested in the catalogue.",
            },
        ],
        "family": "electronic",
        "key": "chiptune",
        "label": "Chiptune",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "electronica",
                "why": "The general electronic bucket; the style postdates the supported list.",
            },
            {
                "genre": "new_wave",
                "subgenre": "synthpop",
                "why": "Use this when it is written as songs with vocals rather than as instrumentals.",
            },
        ],
        "family": "electronic",
        "key": "synthwave",
        "label": "Synthwave",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "downtempo",
                "why": "Slow, sample-led and atmospheric.",
            },
            {
                "genre": "other",
                "subgenre": "experimental",
                "why": "Use this when the piece is a collage rather than a track.",
            },
        ],
        "family": "electronic",
        "key": "vaporwave",
        "label": "Vaporwave",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "hardcore_dance",
                "why": "The closest supported category, covering the hard, high-BPM end of dance music.",
            },
        ],
        "family": "electronic",
        "key": "hardcore_techno",
        "label": "Hardcore Techno",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "hardcore_dance",
                "why": "The supported hardcore dance entry covers it.",
            },
        ],
        "family": "electronic",
        "key": "gabber",
        "label": "Gabber",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "industrial",
                "why": "The electronic-side industrial entry, for the non-metal form.",
            },
            {
                "genre": "metal",
                "subgenre": "industrial",
                "why": "Use the metal side when guitars carry the riffs.",
            },
        ],
        "family": "electronic",
        "key": "industrial",
        "label": "Industrial",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "industrial",
                "why": "The supported home for body music and its industrial relatives.",
            },
        ],
        "family": "electronic",
        "key": "ebm",
        "label": "EBM",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "industrial",
                "why": "Where the catalogue files Aesthetic Perfection.",
            },
            {
                "genre": "new_wave",
                "subgenre": "synthpop",
                "why": "Use this when the melodies are pop-forward.",
            },
        ],
        "family": "electronic",
        "key": "futurepop",
        "label": "Futurepop",
    },
    {
        "candidates": [
            {
                "genre": "metal",
                "subgenre": "metalcore",
                "why": "Where Attack Attack! is filed. The -core side wins over the synths.",
            },
        ],
        "family": "electronic",
        "key": "electronicore",
        "label": "Electronicore",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "trip_hop",
                "why": "Exact match, filed under Hip-Hop/Rap rather than under electronic.",
            },
            {
                "genre": "pop_dance_electronic",
                "subgenre": "downtempo",
                "why": "Use this when there are no hip-hop elements at all.",
            },
        ],
        "family": "electronic",
        "key": "trip_hop",
        "label": "Trip-Hop",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "garage",
                "why": "The electronic Garage entry, not the rock one. Both names exist in the list.",
            },
        ],
        "family": "electronic",
        "key": "garage_electronic",
        "label": "Garage (electronic)",
    },
    {
        "candidates": [
            {
                "genre": "pop_dance_electronic",
                "subgenre": "dub",
                "why": "The supported Dub entry sits under the electronic genre.",
            },
            {
                "genre": "reggae_ska",
                "subgenre": "reggae",
                "why": "Use Reggae for a conventional song with vocals, where the dub effects are incidental. Dub proper is a production-led instrumental remix.",
            },
        ],
        "family": "electronic",
        "key": "dub",
        "label": "Dub",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "hip_hop",
                "why": "Exact match, under the Hip-Hop/Rap genre.",
            },
        ],
        "family": "hiphop",
        "key": "hip_hop",
        "label": "Hip-Hop",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "rap",
                "why": "Exact match, under the Hip-Hop/Rap genre.",
            },
        ],
        "family": "hiphop",
        "key": "rap",
        "label": "Rap",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "old_school_hip_hop",
                "why": "Exact match, under the Hip-Hop/Rap genre.",
            },
        ],
        "family": "hiphop",
        "key": "old_school_hip_hop",
        "label": "Old School Hip-Hop",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "old_school_hip_hop",
                "why": "Sampled breaks and hard drums, which is the era the supported Old School entry describes.",
            },
            {
                "genre": "hip_hop_rap",
                "subgenre": "hip_hop",
                "why": "Use the general entry for a modern boom bap revival record.",
            },
        ],
        "family": "hiphop",
        "key": "boom_bap",
        "label": "Boom Bap",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "hip_hop",
                "why": "The general supported entry. Trap postdates this list, so it has no category of its own.",
            },
            {
                "genre": "hip_hop_rap",
                "subgenre": "gangsta",
                "why": "Use this when the subject matter and delivery follow the gangsta tradition.",
            },
        ],
        "family": "hiphop",
        "key": "trap",
        "label": "Trap",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "hardcore_rap",
                "why": "The closest supported category for its aggression and subject matter.",
            },
            {
                "genre": "hip_hop_rap",
                "subgenre": "gangsta",
                "why": "Use this when it sits squarely in the gangsta lineage.",
            },
        ],
        "family": "hiphop",
        "key": "drill",
        "label": "Drill",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "alternative_rap",
                "why": "Jazz-sampling hip-hop is the archetype of what Alternative Rap covers.",
            },
        ],
        "family": "hiphop",
        "key": "jazz_rap",
        "label": "Jazz Rap",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "trip_hop",
                "why": "Downtempo, sample-led and usually instrumental, which is what Trip Hop describes.",
            },
            {
                "genre": "pop_dance_electronic",
                "subgenre": "downtempo",
                "why": "Use this when there is no hip-hop vocal or sampling element at all.",
            },
        ],
        "family": "hiphop",
        "key": "lofi_hiphop",
        "label": "Lo-fi Hip-Hop",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "gangsta",
                "why": "Exact match, under the Hip-Hop/Rap genre.",
            },
        ],
        "family": "hiphop",
        "key": "gangsta_rap",
        "label": "Gangsta Rap",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "hardcore_rap",
                "why": "The closest supported category. It is named Hardcore Rap, but covers the same ground.",
            },
        ],
        "family": "hiphop",
        "key": "hardcore_hip_hop",
        "label": "Hardcore Hip-Hop",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "alternative_rap",
                "why": "The closest supported category. It is named Alternative Rap, but covers the same ground.",
            },
        ],
        "family": "hiphop",
        "key": "alternative_hip_hop",
        "label": "Alternative Hip-Hop",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "underground_rap",
                "why": "The closest supported category. It is named Underground Rap, but covers the same ground.",
            },
        ],
        "family": "hiphop",
        "key": "underground_hip_hop",
        "label": "Underground Hip-Hop",
    },
    {
        "candidates": [
            {
                "genre": "nu_metal",
                "subgenre": "nu_metal",
                "why": "The documentation describes exactly this crossover under Nu-Metal.",
            },
            {
                "genre": "metal",
                "subgenre": "alternative",
                "why": "Use this when it is closer to alt-metal than to nu-metal.",
            },
        ],
        "family": "hiphop",
        "key": "rap_rock",
        "label": "Rap Rock",
    },
    {
        "candidates": [
            {
                "genre": "hip_hop_rap",
                "subgenre": "alternative_rap",
                "why": "Hip-hop first; the subject matter does not change the form.",
            },
            {
                "genre": "novelty",
                "subgenre": "novelty",
                "why": "Use this when the song is written to be funny above all.",
            },
        ],
        "family": "hiphop",
        "key": "nerdcore",
        "label": "Nerdcore",
    },
    {
        "candidates": [
            {
                "genre": "rnb_soul_funk",
                "subgenre": "rhythm_and_blues",
                "why": "Exact match, under the R&B/Soul/Funk genre.",
            },
        ],
        "family": "rnb",
        "key": "rnb",
        "label": "R&B",
    },
    {
        "candidates": [
            {
                "genre": "rnb_soul_funk",
                "subgenre": "rhythm_and_blues",
                "why": "The supported R&B entry covers the modern form too.",
            },
        ],
        "family": "rnb",
        "key": "contemporary_rnb",
        "label": "Contemporary R&B",
    },
    {
        "candidates": [
            {
                "genre": "rnb_soul_funk",
                "subgenre": "soul",
                "why": "Exact match, under the R&B/Soul/Funk genre.",
            },
        ],
        "family": "rnb",
        "key": "soul",
        "label": "Soul",
    },
    {
        "candidates": [
            {
                "genre": "rnb_soul_funk",
                "subgenre": "soul",
                "why": "The supported Soul entry is the closest fit.",
            },
        ],
        "family": "rnb",
        "key": "neo_soul",
        "label": "Neo-Soul",
    },
    {
        "candidates": [
            {
                "genre": "rnb_soul_funk",
                "subgenre": "rhythm_and_blues",
                "why": "R&B first; the atmospheric production does not move it to another genre.",
            },
            {
                "genre": "rnb_soul_funk",
                "subgenre": "soul",
                "why": "Use this when the vocal performance is the centre of the song.",
            },
        ],
        "family": "rnb",
        "key": "alternative_rnb",
        "label": "Alternative R&B",
    },
    {
        "candidates": [
            {
                "genre": "rnb_soul_funk",
                "subgenre": "motown",
                "why": "Exact match, under the R&B/Soul/Funk genre.",
            },
        ],
        "family": "rnb",
        "key": "motown",
        "label": "Motown",
    },
    {
        "candidates": [
            {
                "genre": "rnb_soul_funk",
                "subgenre": "funk",
                "why": "Exact match, under the R&B/Soul/Funk genre.",
            },
        ],
        "family": "rnb",
        "key": "funk",
        "label": "Funk",
    },
    {
        "candidates": [
            {
                "genre": "rnb_soul_funk",
                "subgenre": "disco",
                "why": "Exact match, under the R&B/Soul/Funk genre.",
            },
        ],
        "family": "rnb",
        "key": "disco",
        "label": "Disco",
    },
    {
        "candidates": [
            {
                "genre": "inspirational",
                "subgenre": "inspirational",
                "why": "The supported genre defined by devotional content.",
            },
            {
                "genre": "rnb_soul_funk",
                "subgenre": "soul",
                "why": "Use this when the arrangement is soul first.",
            },
        ],
        "family": "rnb",
        "key": "gospel",
        "label": "Gospel",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "contemporary",
                "why": "The default for modern country.",
            },
            {
                "genre": "country",
                "subgenre": "traditional_folk",
                "why": "Use this for older, string-band styled country.",
            },
        ],
        "family": "country_folk",
        "key": "country",
        "label": "Country",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "traditional_folk",
                "why": "The supported home for pre-Nashville-pop country.",
            },
            {
                "genre": "country",
                "subgenre": "honky_tonk",
                "why": "Prefer this for barroom country specifically.",
            },
        ],
        "family": "country_folk",
        "key": "classic_country",
        "label": "Classic Country",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "honky_tonk",
                "why": "Exact match, under the Country genre.",
            },
        ],
        "family": "country_folk",
        "key": "honky_tonk",
        "label": "Honky Tonk",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "outlaw",
                "why": "Exact match, under the Country genre.",
            },
        ],
        "family": "country_folk",
        "key": "outlaw_country",
        "label": "Outlaw Country",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "alternative",
                "why": "Exact match, and well attested in the catalogue.",
            },
        ],
        "family": "country_folk",
        "key": "alt_country",
        "label": "Alt-Country",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "alternative",
                "why": "The supported bucket closest to roots-leaning modern country.",
            },
            {
                "genre": "other",
                "subgenre": "contemporary_folk",
                "why": "Use this when it is folk rather than country.",
            },
        ],
        "family": "country_folk",
        "key": "americana",
        "label": "Americana",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "alternative",
                "why": "Use this when country leads.",
            },
            {
                "genre": "rock",
                "subgenre": "folk",
                "why": "Use this when the band reads as a rock band.",
            },
            {
                "genre": "southern_rock",
                "subgenre": "southern_rock",
                "why": "Prefer Southern Rock for the twin-guitar southern sound.",
            },
        ],
        "family": "country_folk",
        "key": "country_rock",
        "label": "Country Rock",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "bluegrass",
                "why": "Exact match, under the Country genre.",
            },
        ],
        "family": "country_folk",
        "key": "bluegrass",
        "label": "Bluegrass",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "contemporary_folk",
                "why": "The supported folk entry sits under Other, not under Country.",
            },
            {
                "genre": "country",
                "subgenre": "traditional_folk",
                "why": "Use the Country one for traditional string-band folk.",
            },
        ],
        "family": "country_folk",
        "key": "folk",
        "label": "Folk",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "contemporary_folk",
                "why": "Exact match, under the Other genre.",
            },
        ],
        "family": "country_folk",
        "key": "contemporary_folk",
        "label": "Contemporary Folk",
    },
    {
        "candidates": [
            {
                "genre": "country",
                "subgenre": "traditional_folk",
                "why": "Exact match, filed under Country.",
            },
        ],
        "family": "country_folk",
        "key": "traditional_folk",
        "label": "Traditional Folk",
    },
    {
        "candidates": [
            {
                "genre": "world",
                "subgenre": "world",
                "why": "The supported home for regional traditional music.",
            },
            {
                "genre": "other",
                "subgenre": "contemporary_folk",
                "why": "Use this for modern singer-led Celtic folk.",
            },
        ],
        "family": "country_folk",
        "key": "celtic",
        "label": "Celtic / Irish",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "acoustic",
                "why": "Exact match. An instrumentation, so prefer a real genre if one fits.",
            },
            {
                "genre": "blues",
                "subgenre": "acoustic",
                "why": "Use the Blues one when the material is blues.",
            },
        ],
        "family": "country_folk",
        "key": "acoustic",
        "label": "Acoustic",
    },
    {
        "candidates": [
            {
                "genre": "jazz",
                "subgenre": "contemporary",
                "why": "Right for modern jazz, which is what Contemporary means here.",
            },
            {
                "genre": "jazz",
                "subgenre": "other",
                "why": "Use this for jazz from an earlier era, which Contemporary would misdate.",
            },
        ],
        "family": "jazz_blues",
        "key": "jazz",
        "label": "Jazz",
    },
    {
        "candidates": [
            {
                "genre": "jazz",
                "subgenre": "other",
                "why": "There is no swing-era category, and Contemporary means modern jazz, so Other is the honest fit.",
            },
            {
                "genre": "jazz",
                "subgenre": "contemporary",
                "why": "Only for a present-day big band, or if you would rather not use an Other category.",
            },
        ],
        "family": "jazz_blues",
        "key": "big_band",
        "label": "Big Band / Swing",
    },
    {
        "candidates": [
            {
                "genre": "jazz",
                "subgenre": "other",
                "why": "No bebop category exists, and it predates what Contemporary describes.",
            },
            {
                "genre": "jazz",
                "subgenre": "experimental",
                "why": "Use this for the outward-bound post-bop end.",
            },
        ],
        "family": "jazz_blues",
        "key": "bebop",
        "label": "Bebop",
    },
    {
        "candidates": [
            {
                "genre": "jazz",
                "subgenre": "smooth_jazz",
                "why": "Exact match, under the Jazz genre.",
            },
        ],
        "family": "jazz_blues",
        "key": "smooth_jazz",
        "label": "Smooth Jazz",
    },
    {
        "candidates": [
            {
                "genre": "jazz",
                "subgenre": "acid_jazz",
                "why": "Exact match, under the Jazz genre.",
            },
        ],
        "family": "jazz_blues",
        "key": "acid_jazz",
        "label": "Acid Jazz",
    },
    {
        "candidates": [
            {
                "genre": "jazz",
                "subgenre": "ragtime",
                "why": "Exact match, under the Jazz genre.",
            },
        ],
        "family": "jazz_blues",
        "key": "ragtime",
        "label": "Ragtime",
    },
    {
        "candidates": [
            {
                "genre": "jazz",
                "subgenre": "experimental",
                "why": "Exact for experimental jazz, and the closest supported category for free jazz, which has none of its own.",
            },
        ],
        "family": "jazz_blues",
        "key": "free_jazz",
        "label": "Free / Experimental Jazz",
    },
    {
        "candidates": [
            {
                "genre": "fusion",
                "subgenre": "fusion",
                "why": "Its own major genre, kept separate from Jazz on purpose.",
            },
        ],
        "family": "jazz_blues",
        "key": "jazz_fusion",
        "label": "Jazz Fusion",
    },
    {
        "candidates": [
            {
                "genre": "blues",
                "subgenre": "classic",
                "why": "The general supported blues entry.",
            },
        ],
        "family": "jazz_blues",
        "key": "blues",
        "label": "Blues",
    },
    {
        "candidates": [
            {
                "genre": "blues",
                "subgenre": "delta",
                "why": "Exact match, under the Blues genre.",
            },
        ],
        "family": "jazz_blues",
        "key": "delta_blues",
        "label": "Delta Blues",
    },
    {
        "candidates": [
            {
                "genre": "blues",
                "subgenre": "chicago",
                "why": "Exact match, under the Blues genre.",
            },
        ],
        "family": "jazz_blues",
        "key": "chicago_blues",
        "label": "Chicago Blues",
    },
    {
        "candidates": [
            {
                "genre": "blues",
                "subgenre": "electric",
                "why": "Exact match, and the best attested blues subgenre in the catalogue.",
            },
        ],
        "family": "jazz_blues",
        "key": "electric_blues",
        "label": "Electric Blues",
    },
    {
        "candidates": [
            {
                "genre": "blues",
                "subgenre": "acoustic",
                "why": "Exact match, under the Blues genre.",
            },
        ],
        "family": "jazz_blues",
        "key": "acoustic_blues",
        "label": "Acoustic Blues",
    },
    {
        "candidates": [
            {
                "genre": "blues",
                "subgenre": "country",
                "why": "Exact match. This is Blues / Country, not the Country genre.",
            },
        ],
        "family": "jazz_blues",
        "key": "country_blues",
        "label": "Country Blues",
    },
    {
        "candidates": [
            {
                "genre": "blues",
                "subgenre": "contemporary",
                "why": "Exact match, under the Blues genre.",
            },
        ],
        "family": "jazz_blues",
        "key": "contemporary_blues",
        "label": "Contemporary Blues",
    },
    {
        "candidates": [
            {
                "genre": "world",
                "subgenre": "world",
                "why": "Its own major genre, for music outside the western pop tradition.",
            },
        ],
        "family": "world_other",
        "key": "world",
        "label": "World",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "Its own major genre.",
            },
        ],
        "family": "world_other",
        "key": "latin",
        "label": "Latin",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "The Latin genre has a single subgenre covering all of it.",
            },
        ],
        "family": "world_other",
        "key": "salsa",
        "label": "Salsa",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "The Latin genre has a single subgenre covering all of it.",
            },
        ],
        "family": "world_other",
        "key": "samba",
        "label": "Samba",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "Brazilian in origin, so the Latin genre fits.",
            },
            {
                "genre": "jazz",
                "subgenre": "contemporary",
                "why": "Use Jazz when the performance is a jazz reading of the form.",
            },
        ],
        "family": "world_other",
        "key": "bossa_nova",
        "label": "Bossa Nova",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "The Latin genre has a single subgenre covering all of it.",
            },
        ],
        "family": "world_other",
        "key": "cumbia",
        "label": "Cumbia",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "The Latin genre has a single subgenre covering all of it.",
            },
        ],
        "family": "world_other",
        "key": "bachata",
        "label": "Bachata",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "The Latin genre has a single subgenre covering all of it.",
            },
        ],
        "family": "world_other",
        "key": "merengue",
        "label": "Merengue",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "The Latin genre has a single subgenre covering all of it.",
            },
            {
                "genre": "world",
                "subgenre": "world",
                "why": "Use World when the recording is presented as a traditional performance.",
            },
        ],
        "family": "world_other",
        "key": "mariachi",
        "label": "Mariachi",
    },
    {
        "candidates": [
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "Latin is the supported catch-all for Caribbean and Latin American popular styles.",
            },
            {
                "genre": "hip_hop_rap",
                "subgenre": "hip_hop",
                "why": "Use this when the track is built around rapping and reads as hip-hop first.",
            },
        ],
        "family": "world_other",
        "key": "reggaeton",
        "label": "Reggaeton",
    },
    {
        "candidates": [
            {
                "genre": "world",
                "subgenre": "world",
                "why": "Traditional flamenco is a regional folk tradition, which is what World covers.",
            },
            {
                "genre": "latin",
                "subgenre": "latin",
                "why": "A compatibility choice for modern flamenco fusion sitting closer to Latin pop.",
            },
        ],
        "family": "world_other",
        "key": "flamenco",
        "label": "Flamenco",
    },
    {
        "candidates": [
            {
                "genre": "world",
                "subgenre": "world",
                "why": "The supported home for African popular music.",
            },
            {
                "genre": "rnb_soul_funk",
                "subgenre": "funk",
                "why": "Use this when the groove is the point and the horns lead.",
            },
        ],
        "family": "world_other",
        "key": "afrobeat",
        "label": "Afrobeat",
    },
    {
        "candidates": [
            {
                "genre": "world",
                "subgenre": "world",
                "why": "Regional traditional music with no category of its own.",
            },
        ],
        "family": "world_other",
        "key": "klezmer",
        "label": "Klezmer",
    },
    {
        "candidates": [
            {
                "genre": "reggae_ska",
                "subgenre": "reggae",
                "why": "Exact match. The documentation names Bob Marley.",
            },
        ],
        "family": "world_other",
        "key": "reggae",
        "label": "Reggae",
    },
    {
        "candidates": [
            {
                "genre": "reggae_ska",
                "subgenre": "reggae",
                "why": "The supported Reggae entry is the closest fit.",
            },
        ],
        "family": "world_other",
        "key": "dancehall",
        "label": "Dancehall",
    },
    {
        "candidates": [
            {
                "genre": "reggae_ska",
                "subgenre": "ska",
                "why": "Exact match, under the Reggae/Ska genre.",
            },
        ],
        "family": "world_other",
        "key": "ska",
        "label": "Ska",
    },
    {
        "candidates": [
            {
                "genre": "classical",
                "subgenre": "classical",
                "why": "Its own major genre. The documentation names Bach and Mozart.",
            },
        ],
        "family": "world_other",
        "key": "classical",
        "label": "Classical",
    },
    {
        "candidates": [
            {
                "genre": "classical",
                "subgenre": "classical",
                "why": "The Classical genre has a single subgenre covering all of it.",
            },
        ],
        "family": "world_other",
        "key": "opera",
        "label": "Opera",
    },
    {
        "candidates": [
            {
                "genre": "classical",
                "subgenre": "classical",
                "why": "The Classical genre has a single subgenre covering all of it.",
            },
        ],
        "family": "world_other",
        "key": "baroque",
        "label": "Baroque",
    },
    {
        "candidates": [
            {
                "genre": "classical",
                "subgenre": "classical",
                "why": "The documentation describes Classical as orchestral writing in the old style.",
            },
            {
                "genre": "other",
                "subgenre": "other",
                "why": "Use this when the score is electronic or otherwise not orchestral.",
            },
        ],
        "family": "world_other",
        "key": "film_score",
        "label": "Film / Orchestral Score",
    },
    {
        "candidates": [
            {
                "genre": "inspirational",
                "subgenre": "inspirational",
                "why": "Its own major genre, defined by lyrical content.",
            },
        ],
        "family": "world_other",
        "key": "inspirational",
        "label": "Inspirational / Worship",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "experimental",
                "why": "Exact match. Use it when no conventional genre applies.",
            },
        ],
        "family": "world_other",
        "key": "experimental",
        "label": "Experimental",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "other",
                "why": "No spoken-word category exists.",
            },
            {
                "genre": "other",
                "subgenre": "experimental",
                "why": "Use this when it is presented as an art piece.",
            },
        ],
        "family": "world_other",
        "key": "spoken_word",
        "label": "Spoken Word",
    },
    {
        "candidates": [
            {
                "genre": "other",
                "subgenre": "other",
                "why": "The final fallback when nothing else in the list is closer.",
            },
        ],
        "family": "world_other",
        "key": "soundtrack_other",
        "label": "Other / Unclassifiable",
    },
]

