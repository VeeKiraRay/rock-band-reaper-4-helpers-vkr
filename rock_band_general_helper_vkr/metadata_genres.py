"""Generated genre data.

Modern counterpart: rock_band_general_helper_vkr/metadata_genres.lua
Regenerate with dev/tools/export_genre_tables.lua.
Python 2.7 compatible.
"""

RB3_GENRE_ORDER = [
    "alternative",
    "blues",
    "classical",
    "classic_rock",
    "country",
    "emo",
    "fusion",
    "glam",
    "grunge",
    "hip_hop_rap",
    "indie_rock",
    "inspirational",
    "jazz",
    "j_rock",
    "latin",
    "metal",
    "new_wave",
    "novelty",
    "nu_metal",
    "pop_dance_electronic",
    "pop_rock",
    "prog",
    "punk",
    "rnb_soul_funk",
    "reggae_ska",
    "rock",
    "southern_rock",
    "world",
    "other",
]

RB3_GENRES = {
    "alternative": {
        "label": "Alternative",
        "subgenres": [
            {
                "key": "alternative",
                "label": "Alternative",
            },
            {
                "albums": "Document, Talking with the Taxman About Poetry",
                "artists": "R.E.M. (early), Billy Bragg",
                "blurb": "melodic, punky",
                "elements": "melodic pop sound, jangling guitars, post-punk/new wave experimentation",
                "key": "college",
                "label": "College",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "blues": {
        "label": "Blues",
        "subgenres": [
            {
                "key": "acoustic",
                "label": "Acoustic",
            },
            {
                "key": "chicago",
                "label": "Chicago",
            },
            {
                "key": "classic",
                "label": "Classic",
            },
            {
                "key": "contemporary",
                "label": "Contemporary",
            },
            {
                "key": "country",
                "label": "Country",
            },
            {
                "key": "delta",
                "label": "Delta",
            },
            {
                "key": "electric",
                "label": "Electric",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "classic_rock": {
        "label": "Classic Rock",
        "subgenres": [
            {
                "key": "classic_rock",
                "label": "Classic Rock",
            },
        ],
    },
    "classical": {
        "label": "Classical",
        "subgenres": [
            {
                "artists": "JS Bach, Beethoven, Mozart, etc",
                "elements": "Any Western music created in the \"old style\" of pre-popular music (pre blues, jazz, rock, etc), Often utilizing orchestras or choirs",
                "key": "classical",
                "label": "Classical",
            },
        ],
    },
    "country": {
        "label": "Country",
        "subgenres": [
            {
                "key": "alternative",
                "label": "Alternative",
            },
            {
                "key": "bluegrass",
                "label": "Bluegrass",
            },
            {
                "key": "contemporary",
                "label": "Contemporary",
            },
            {
                "key": "honky_tonk",
                "label": "Honky Tonk",
            },
            {
                "key": "outlaw",
                "label": "Outlaw",
            },
            {
                "key": "traditional_folk",
                "label": "Traditional Folk",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "emo": {
        "label": "Emo",
        "subgenres": [
            {
                "key": "emo",
                "label": "Emo",
            },
        ],
    },
    "fusion": {
        "label": "Fusion",
        "subgenres": [
            {
                "key": "fusion",
                "label": "Fusion",
            },
        ],
    },
    "glam": {
        "label": "Glam",
        "subgenres": [
            {
                "key": "glam",
                "label": "Glam",
            },
            {
                "key": "goth",
                "label": "Goth",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "grunge": {
        "label": "Grunge",
        "subgenres": [
            {
                "albums": "Nevermind, Ten",
                "artists": "Nirvana, Pearl Jam",
                "blurb": "dirty, distorted, aggressive",
                "elements": "distorted guitars, contrasting dynamics",
                "key": "grunge",
                "label": "Grunge",
            },
        ],
    },
    "hip_hop_rap": {
        "label": "Hip-Hop/Rap",
        "subgenres": [
            {
                "key": "alternative_rap",
                "label": "Alternative Rap",
            },
            {
                "key": "gangsta",
                "label": "Gangsta",
            },
            {
                "key": "hardcore_rap",
                "label": "Hardcore Rap",
            },
            {
                "key": "hip_hop",
                "label": "Hip Hop",
            },
            {
                "key": "old_school_hip_hop",
                "label": "Old School Hip Hop",
            },
            {
                "key": "rap",
                "label": "Rap",
            },
            {
                "key": "trip_hop",
                "label": "Trip Hop",
            },
            {
                "key": "underground_rap",
                "label": "Underground Rap",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "indie_rock": {
        "label": "Indie Rock",
        "subgenres": [
            {
                "albums": "The Moon and Antarctica, Bee Thousand",
                "artists": "Death Cab for Cutie, Guided by Voices",
                "blurb": "unpolished, unconventional",
                "elements": "lack of professional production, non-mainstream song elements",
                "key": "indie_rock",
                "label": "Indie Rock",
            },
            {
                "artists": "Say Hi, Cat Power",
                "blurb": "minimal, unpolished",
                "elements": "clear evidence of home production, unusual mixing characteristics",
                "key": "lo_fi",
                "label": "Lo-fi",
            },
            {
                "artists": "American Football, Don Caballero, Minus the Bear",
                "elements": "typical \"indie\" sound qualities, written with incredibly complex time signatures, chords and melodies",
                "key": "math_rock",
                "label": "Math Rock",
            },
            {
                "artists": "Sonic Youth, The Jesus Lizard",
                "elements": "Off-shoot of Post-Punk, High amounts of effects, strong levels of dissonance, complex song structures",
                "key": "noise",
                "label": "Noise",
            },
            {
                "artists": "Godspeed You! Black Emperor, Mogwai, Sigur Ros",
                "elements": "\"Rock\" instruments used in unconventional ways musically, often instrumental, unusual song structures (lack of clear verse/chorus), spacey/atmospheric mixing and production",
                "key": "post_rock",
                "label": "Post-Rock",
            },
            {
                "artists": "My Bloody Valentine, Lush",
                "blurb": "spacy, layered",
                "elements": "distorted/sustained guitar work, vocals 'as an instrument', focus on texture over riff",
                "key": "shoegazing",
                "label": "Shoegazing",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "inspirational": {
        "label": "Inspirational",
        "subgenres": [
            {
                "key": "inspirational",
                "label": "Inspirational",
            },
        ],
    },
    "j_rock": {
        "label": "J-Rock",
        "subgenres": [
            {
                "key": "j_rock",
                "label": "J-Rock",
            },
        ],
    },
    "jazz": {
        "label": "Jazz",
        "subgenres": [
            {
                "key": "acid_jazz",
                "label": "Acid Jazz",
            },
            {
                "key": "contemporary",
                "label": "Contemporary",
            },
            {
                "key": "experimental",
                "label": "Experimental",
            },
            {
                "key": "ragtime",
                "label": "Ragtime",
            },
            {
                "key": "smooth_jazz",
                "label": "Smooth Jazz",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "latin": {
        "label": "Latin",
        "subgenres": [
            {
                "key": "latin",
                "label": "Latin",
            },
        ],
    },
    "metal": {
        "label": "Metal",
        "subgenres": [
            {
                "key": "alternative",
                "label": "Alternative",
            },
            {
                "artists": "Emperor, Bathory, Mayhem, Darkthrone",
                "elements": "lo-fi production quality, unconventional song structures, raspy vocals, prevalence of fast tremelo-picking and blast beats over more \"melodic\" instrumentation",
                "key": "black",
                "label": "Black",
            },
            {
                "artists": "All That Remains, The Devil Wears Prada, Underoath, As I Lay Dying",
                "elements": "Combination of \"traditional\" metal elements and hardcore punk elements, thrash riffs, hardcore breakdowns, utilizes both aggressive and clean vocals",
                "key": "metalcore",
                "label": "Metalcore",
            },
            {
                "artists": "Cannibal Corpse, Dying Fetus",
                "elements": "aggressive, loud and violent extreme Metal, often using downtuned heavy guitars, extremely fast and/or complex drumming with a lot of double bass pedal involved, and guttural growling as the main source of vocals.",
                "key": "death",
                "label": "Death",
            },
            {
                "artists": "Poison, Motley Crue, Ratt, The Scorpions, Whitesnake, Night Ranger",
                "elements": "highly-produced \"pop metal\" popular in the 80's, simple power chord riffs and fast, melodic soloing with standard song structures, lyrics about living the \"rock star life\"",
                "key": "hair",
                "label": "Hair",
            },
            {
                "albums": "Psalm 69, The Downward Spiral",
                "artists": "Ministry, KMFDM, Nine Inch Nails, Rammstein, Marilyn Manson",
                "elements": "mixes elements of Heavy and Thrash Metal with noise and electronic elements, sometimes using samples, effect heavy vocals, repetitive guitar and drums and playing with inhuman loudness as an artistic choice.",
                "key": "industrial",
                "label": "Industrial",
            },
            {
                "key": "metal",
                "label": "Metal",
            },
            {
                "artists": "Dragonforce, Nightwish, Firewind, Kamelot, Helloween",
                "elements": "High tempo, highly produced, technically complex musicianship, simple, \"epic feeling\" major-key melodies, highly melodic vocals",
                "key": "power",
                "label": "Power",
            },
            {
                "artists": "Dream Theater, Queensryche",
                "blurb": "genre-mixing, seeks to push boundaries of what Metal can be",
                "elements": "complex rhythm, longer length, detailed instrumentation",
                "key": "progressive",
                "label": "Progressive",
            },
            {
                "key": "speed",
                "label": "Speed",
            },
            {
                "artists": "\"The Big 4\": Metallica, Megadeth, Anthrax, Slayer. Other examples: Machinehead, Testament, Evile, Municipal Waste, Anvil",
                "elements": "fast, palm-muted guitar riffs and technically complex solos, fast, straightforward drum beats, shouted or harshly-song (but still melodic) vocals",
                "key": "thrash",
                "label": "Thrash",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "new_wave": {
        "label": "New Wave",
        "subgenres": [
            {
                "blurb": "Somber or introspective tone + sequenced synths and / or ambient processed guitars = moody textural atmosphere. Historical precursor to Gothic Rock, now the contemporary expansion of that genre.",
                "key": "dark_wave",
                "label": "Dark Wave",
            },
            {
                "key": "electroclash",
                "label": "Electroclash",
            },
            {
                "blurb": "Brit: Mashed Punk & Disco ca. '76-'83. Amer: Rock without the \"Prog\", \"Hard\" or \"Soft\". Danceable, synthy songs. ca. '81-'88 . Resurfaced in the 21st Century.",
                "key": "new_wave",
                "label": "New Wave",
            },
            {
                "blurb": "Friendly, rock song structures, eschews instrumental virtuosity, signature use of arpeggiated electronics, or later into the '80s, programmed sequences.",
                "key": "synthpop",
                "label": "Synthpop",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "novelty": {
        "label": "Novelty",
        "subgenres": [
            {
                "artists": "Weird Al, Parry Grip",
                "elements": "songs that are primarily made to be funny or comedic as it's main point. Can span any and all genres of music, and sometimes it's a cover version of a serious song with new lyrics to create a parody of the original.",
                "key": "novelty",
                "label": "Novelty",
            },
        ],
    },
    "nu_metal": {
        "label": "Nu-Metal",
        "subgenres": [
            {
                "albums": "Life is Peachy/Follow the Leader (KoRn), The Sickness (Disturbed), Significant Other (Limp Bizkit), Vol. 3 (The Subliminal Verses) (Slipknot)",
                "artists": "KoRn, Early Disturbed/Slipknot/Linkin Park (all three have moved away from nu metal since then), Saliva, Limp Bizkit, Godsmack",
                "elements": "Dark and heavy, yet relatively mainstream music. Mashes hip-hop style syncopated drum beats with down-tuned, chunky metal/industrial guitar riffs, and avoids guitar solos. Aggressive (but often still melodic) vocals and introspective, dark, often depressive/angry lyrics. Gained popularity in the late 90's/early 2000's, but has mostly died off since then.",
                "key": "nu_metal",
                "label": "Nu-Metal",
            },
        ],
    },
    "other": {
        "label": "Other",
        "subgenres": [
            {
                "artists": "The Nylons, Van Canto",
                "elements": "Music created using only human vocalization, and occasionally percussion",
                "key": "a_capella",
                "label": "A Capella",
            },
            {
                "key": "acoustic",
                "label": "Acoustic",
            },
            {
                "key": "contemporary_folk",
                "label": "Contemporary Folk",
            },
            {
                "key": "experimental",
                "label": "Experimental",
            },
            {
                "key": "oldies",
                "label": "Oldies",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "pop_dance_electronic": {
        "label": "Pop/Dance/Electronic",
        "subgenres": [
            {
                "key": "ambient",
                "label": "Ambient",
            },
            {
                "artists": "The Prodigy, The Crystal Method",
                "key": "breakbeat",
                "label": "Breakbeat",
            },
            {
                "key": "chiptune",
                "label": "Chiptune",
            },
            {
                "key": "dance",
                "label": "Dance",
            },
            {
                "key": "downtempo",
                "label": "Downtempo",
            },
            {
                "key": "dub",
                "label": "Dub",
            },
            {
                "artists": "Goldie, Squarepusher",
                "key": "drum_and_bass",
                "label": "Drum and Bass",
            },
            {
                "key": "electronica",
                "label": "Electronica",
            },
            {
                "key": "garage",
                "label": "Garage",
            },
            {
                "key": "hardcore_dance",
                "label": "Hardcore Dance",
            },
            {
                "key": "house",
                "label": "House",
            },
            {
                "artists": "Throbbing Gristle, God Lives Underwater",
                "key": "industrial",
                "label": "Industrial",
            },
            {
                "key": "techno",
                "label": "Techno",
            },
            {
                "key": "trance",
                "label": "Trance",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "pop_rock": {
        "label": "Pop-Rock",
        "subgenres": [
            {
                "key": "contemporary",
                "label": "Contemporary",
            },
            {
                "artists": "Lady Gaga, Madonna",
                "key": "pop",
                "label": "Pop",
            },
            {
                "key": "soft_rock",
                "label": "Soft Rock",
            },
            {
                "key": "teen_rock",
                "label": "Teen Rock",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "prog": {
        "label": "Prog",
        "subgenres": [
            {
                "artists": "Rush, King Crimson, Genesis, Yes, Pink Floyd, Tool",
                "elements": "melodic and epic Rock music that often focuses on strange time signatures, complex instrumental parts, avant-garde and/or complex lyrics, uncommon song structures and long running times.",
                "key": "prog_rock",
                "label": "Prog Rock",
            },
        ],
    },
    "punk": {
        "label": "Punk",
        "subgenres": [
            {
                "key": "alternative",
                "label": "Alternative",
            },
            {
                "key": "classic",
                "label": "Classic",
            },
            {
                "key": "dance_punk",
                "label": "Dance Punk",
            },
            {
                "key": "garage",
                "label": "Garage",
            },
            {
                "key": "hardcore",
                "label": "Hardcore",
            },
            {
                "artists": "Green Day, Blink 182, Simple Plan, Sum 41, Good Charlotte",
                "elements": "high energy, high tempo, instrumentally simple music. Differentiated from standard punk by high production values and palatable vocal harmonies",
                "key": "pop_punk",
                "label": "Pop-Punk",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "reggae_ska": {
        "label": "Reggae/Ska",
        "subgenres": [
            {
                "artists": "Bob Marley",
                "key": "reggae",
                "label": "Reggae",
            },
            {
                "artists": "Reel Big Fish, Less Than Jake",
                "key": "ska",
                "label": "Ska",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "rnb_soul_funk": {
        "label": "R&B/Soul/Funk",
        "subgenres": [
            {
                "key": "disco",
                "label": "Disco",
            },
            {
                "key": "funk",
                "label": "Funk",
            },
            {
                "key": "motown",
                "label": "Motown",
            },
            {
                "key": "rhythm_and_blues",
                "label": "Rhythm and Blues",
            },
            {
                "key": "soul",
                "label": "Soul",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "rock": {
        "label": "Rock",
        "subgenres": [
            {
                "key": "arena",
                "label": "Arena",
            },
            {
                "key": "blues_rock",
                "label": "Blues-Rock",
            },
            {
                "key": "folk",
                "label": "Folk",
            },
            {
                "key": "garage",
                "label": "Garage",
            },
            {
                "key": "hard_rock",
                "label": "Hard Rock",
            },
            {
                "key": "psychedelic",
                "label": "Psychedelic",
            },
            {
                "key": "rock",
                "label": "Rock",
            },
            {
                "artists": "The Reverend Horton Heat, Stray Cats",
                "key": "rockabilly",
                "label": "Rockabilly",
            },
            {
                "artists": "Chuck Berry, Chubby Checker",
                "key": "rock_and_roll",
                "label": "Rock and Roll",
            },
            {
                "key": "surf",
                "label": "Surf",
            },
            {
                "key": "other",
                "label": "Other",
            },
        ],
    },
    "southern_rock": {
        "label": "Southern Rock",
        "subgenres": [
            {
                "key": "southern_rock",
                "label": "Southern Rock",
            },
        ],
    },
    "world": {
        "label": "World",
        "subgenres": [
            {
                "key": "world",
                "label": "World",
            },
        ],
    },
}

