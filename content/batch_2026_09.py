"""Builds batch 1: concepts + fully-specified scripts with real shot lists.

Run this before ingesting. Every item goes through the project's own
validate_script(), so hand-written work cannot skip a check the API path had
to pass. No Anthropic client is imported anywhere here - free by construction.

Shot lists are built by splitting each beat's exact words across that beat's
planned visuals, which guarantees the shot narration reconstructs the script
byte-for-byte while still letting each shot carry real visual direction.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from src import gen_scripts as gs  # noqa: E402


def V(media_type, stock_query, visual_prompt):
    return (media_type, stock_query, visual_prompt)


MAX_SHOT_SECONDS = 5.0

B = {}
ORDER = []


def add(key, **kw):
    B[key] = kw
    ORDER.append(key)


add("hubble",
    cluster="observation_and_instruments", pattern="MISSING_THING", fmt="C",
    mood="mysterious",
    title="Hubble Aimed at Nothing and Found Three Thousand Galaxies",
    overlay="POINTED AT EMPTY SKY",
    hook_a="What hides in a patch of sky with nothing in it?",
    hook_b="Astronomers stared at an empty sky for ten days",
    spine="Hubble stared at an apparently empty patch of sky and found three thousand galaxies.",
    anchor="3,000 galaxies", anchor_spoken="roughly three thousand galaxies",
    mechanism="Ten days of exposure gathered enough faint light to reveal galaxies too dim for any single glance.",
    consequence="No patch of sky is actually empty.",
    source="Hubble Deep Field, NASA and STScI, December 1995",
    confidence="confirmed", saturation="low",
    sources=["Hubble Deep Field, NASA/STScI, December 1995 - 342 exposures over 10 days, ~3,000 galaxies"],
    beats={
        "hook": "What hides in a patch of sky with nothing in it?",
        "turn": "Astronomers picked a dark spot near the Big Dipper, no wider than a pinhead held at arm's length. Nothing was there. Colleagues called it a waste of the telescope.",
        "mechanism": "Hubble stared into that emptiness for ten days, collecting three hundred and forty two separate exposures.",
        "spike": "The darkness filled with roughly three thousand galaxies. Not stars. Galaxies, each holding billions of suns.",
        "loop": "Every blank patch of sky you glance past holds the same crowd. You have never once seen an empty sky.",
    },
    visuals={
        "hook": [V("ai", None, "A perfectly black square of empty night sky, faint film grain only, vertical composition, cinematic")],
        "turn": [V("ai", None, "The Big Dipper constellation with one tiny dark box marked between its stars, vertical"),
                 V("stock", "pinhead needle macro", "A pinhead held up at arm's length against a night sky, shallow focus"),
                 V("ai", None, "An observatory control room, astronomers arguing over a schedule, seen from behind, no faces")],
        "mechanism": [V("ai", None, "The Hubble Space Telescope in orbit above Earth's limb, shutter open, long exposure star trails"),
                      V("ai", None, "Exposure frames stacking one on top of another, faint smudges slowly brightening")],
        "spike": [V("ai", None, "The black square blooming into thousands of multicoloured galaxies, Hubble Deep Field style"),
                  V("ai", None, "Push in on one spiral galaxy in that field until its arms fill the frame")],
        "loop": [V("ai", None, "A person on a rooftop looking up at an ordinary night sky, seen from behind"),
                 V("ai", None, "The same sky slowly revealing hidden galaxies packed into every dark gap")],
    })

add("venus",
    cluster="solar_system_oddities", pattern="INVERTED_ASSUMPTION", fmt="A",
    mood="mysterious",
    title="Venus Takes Longer to Spin Than to Orbit the Sun",
    overlay="VENUS SPINS SLOWER THAN IT ORBITS",
    hook_a="Venus takes longer to spin once than to circle the Sun.",
    hook_b="One planet finishes its year before it finishes turning around",
    spine="Venus rotates so slowly that one rotation outlasts one orbit.",
    anchor="243 Earth days", anchor_spoken="two hundred forty three Earth days",
    mechanism="Venus rotates once every 243 Earth days while orbiting in 225, and it turns backwards.",
    consequence="Our intuition that a day is shorter than a year is not universal.",
    source="Radar rotation measurements of Venus, NASA Magellan",
    confidence="confirmed", saturation="medium",
    sources=["Sidereal rotation period of Venus 243.0 d vs orbital period 224.7 d - radar measurement, NASA Magellan",
             "The solar day on Venus is 117 d. This script uses the SIDEREAL day throughout and the loop claims only the backwards spin, not a day-length comparison."],
    beats={
        "hook": "Venus takes longer to spin once than to circle the Sun.",
        "turn": "Every other planet spins many times in a single orbit. Venus cannot manage even one.",
        "mechanism": "Radar bounced off its clouds clocked a single turn at two hundred forty three Earth days. Its orbit takes only two hundred twenty five.",
        "spike": "A point on its equator crawls around slower than you walk.",
        "loop": "And it turns backwards. Stand there and you would watch the Sun rise in the west.",
    },
    visuals={
        "hook": [V("ai", None, "Venus as a pale cloud-wrapped sphere barely rotating, one surface marking creeping, vertical")],
        "turn": [V("ai", None, "Earth spinning rapidly beside Venus turning almost imperceptibly, side by side comparison"),
                 V("ai", None, "Venus tracing a full orbital arc while a marker on its surface has barely moved")],
        "mechanism": [V("ai", None, "A radar pulse sweeping from Earth across the cloud deck of Venus and returning"),
                      V("ai", None, "Two dials side by side, one labelled spin and one labelled orbit, the spin dial lagging behind")],
        "spike": [V("stock", "person walking pavement", "Feet walking at an ordinary pace along a path, low angle"),
                  V("ai", None, "The equator of Venus creeping past at walking speed, surface detail sliding slowly by")],
        "loop": [V("ai", None, "Sunrise over a hostile volcanic Venusian landscape, Sun rising on the wrong horizon"),
                 V("ai", None, "The Sun tracking backwards across a thick orange Venusian sky")],
    })

add("timedilation",
    cluster="physics_limits", pattern="SECOND_PERSON_IMPLICATION", fmt="E",
    mood="mysterious",
    title="Your Head Is Ageing Faster Than Your Feet",
    overlay="YOUR HEAD AGES FASTER",
    hook_a="Your head is ageing faster than your feet.",
    hook_b="Gravity makes the top of you older than the bottom",
    spine="Gravitational time dilation is measurable across the height of a single person.",
    anchor="33 centimetres", anchor_spoken="thirty three centimetres",
    mechanism="Clocks closer to Earth's mass run slower, and the effect is measurable over a third of a metre.",
    consequence="Time is not a single universal rate, even inside one body.",
    source="NIST aluminium optical clock experiment, 2010",
    confidence="confirmed", saturation="low",
    sources=["NIST aluminium ion optical clock experiment, 2010 - gravitational time dilation measured across a 33 cm height difference"],
    beats={
        "hook": "Your head is ageing faster than your feet.",
        "turn": "Gravity drags on time itself. The closer you sit to the mass of the Earth, the slower your clock runs.",
        "mechanism": "Physicists at NIST proved it with two atomic clocks raised thirty three centimetres apart.",
        "spike": "That is one school ruler of height, and the higher clock measurably won.",
        "loop": "Stand up, and your head pulls ahead of your feet again. You are not quite a single age.",
    },
    visuals={
        "hook": [V("ai", None, "A standing human silhouette split by a glowing horizontal line, clock faces at head and feet showing different times, vertical")],
        "turn": [V("ai", None, "Spacetime drawn as a grid sagging under the Earth, grid lines stretching near the surface"),
                 V("ai", None, "A clock face visibly slowing as it descends toward the ground")],
        "mechanism": [V("ai", None, "Two laboratory atomic clocks on benches at slightly different heights, optics and cables"),
                      V("ai", None, "Close up on the upper clock's readout drifting ahead of the lower one")],
        "spike": [V("stock", "ruler measuring", "A thirty centimetre ruler held upright against a plain background"),
                  V("ai", None, "The height of the ruler mapped between the two clocks as a glowing measured gap")],
        "loop": [V("ai", None, "A person rising from a chair to standing, faint time ripples moving up their body"),
                 V("ai", None, "The same figure with head and feet labelled by two subtly different clock readings")],
    })

add("moon",
    cluster="deep_time", pattern="SCALE_COLLAPSE", fmt="A", mood="dramatic",
    title="The Moon Once Orbited Five Times Closer to Earth",
    overlay="THE MOON WAS FIVE TIMES CLOSER",
    hook_a="The Moon once orbited five times closer to Earth.",
    hook_b="The Moon used to fill a huge bite of the sky",
    spine="The Moon formed far closer and has been receding ever since, so ancient tides were vastly stronger.",
    anchor="75,000 km", anchor_spoken="seventy five thousand kilometres",
    mechanism="The Moon settled at about 75,000 km and now sits near 384,000, and tidal force scales as the inverse cube of distance.",
    consequence="Earth's tides were once more than a hundred times stronger.",
    source="Lunar Laser Ranging via Apollo retroreflectors, and lunar formation models",
    confidence="confirmed", saturation="low",
    sources=["Post-formation lunar distance ~75,000 km - lunar formation models",
             "Current mean distance 384,400 km and 3.8 cm/yr recession - Lunar Laser Ranging, Apollo retroreflectors",
             "Tidal force scales as the inverse cube of distance: (384400/75000)^3 is about 134. The multiplier is derived FROM the sourced distances, not the reverse."],
    beats={
        "hook": "The Moon once orbited five times closer to Earth.",
        "turn": "It settled in at roughly seventy five thousand kilometres out. Today it sits near four hundred thousand.",
        "mechanism": "Lasers fired at mirrors the Apollo crews left behind still clock it drifting further every year.",
        "spike": "Tides pull by the cube of distance, so early tides ran more than a hundred times stronger than the water you paddle in.",
        "loop": "Tonight's Moon is the smallest one any human has ever seen. Every year you get a slightly worse view.",
    },
    visuals={
        "hook": [V("ai", None, "An enormous Moon filling half the sky above a molten early Earth, vertical, cinematic")],
        "turn": [V("ai", None, "Young Earth with the Moon hanging impossibly close, glowing lava seas below"),
                 V("ai", None, "Time lapse of the Moon shrinking as it retreats across billions of years")],
        "mechanism": [V("ai", None, "A green laser beam lancing from an Earth observatory dome up toward the Moon"),
                      V("ai", None, "An Apollo era retroreflector array sitting on grey lunar dust, close up")],
        "spike": [V("ai", None, "Titanic ancient tides surging kilometres up a barren primordial coastline"),
                  V("stock", "ocean waves shore", "Gentle modern waves lapping at an ordinary beach")],
        "loop": [V("ai", None, "Tonight's ordinary Moon seen small above a suburban rooftop"),
                 V("ai", None, "The Moon receding frame by frame, each year fractionally smaller")],
    })

add("sun_giant",
    cluster="stellar_lifecycle", pattern="TIMEBOMB", fmt="D", mood="dramatic",
    title="The Sun Will Swallow Two of Its Own Planets",
    overlay="THE SUN EATS TWO PLANETS",
    hook_a="Our Sun will swallow two of its own planets.",
    hook_b="Two planets are already scheduled to be eaten",
    spine="When the Sun becomes a red giant it expands past Mercury and Venus, consuming both.",
    anchor="5 billion years", anchor_spoken="five billion years",
    mechanism="Hydrogen exhaustion makes the Sun expand into a red giant far past the inner orbits.",
    consequence="Every planet has an end date set by its star.",
    source="Standard stellar evolution models for a one solar mass star",
    confidence="confirmed", saturation="medium",
    sources=["Standard stellar evolution models for a one solar mass star - core hydrogen exhaustion and red giant expansion in roughly 5 billion years",
             "Mercury and Venus lie inside the projected red giant radius; Earth's fate is model-dependent, so the script says 'might' rather than asserting it."],
    beats={
        "hook": "Our Sun will swallow two of its own planets.",
        "turn": "In about five billion years its hydrogen runs dry and it balloons into a red giant. Picture a grape swelling until it fills your living room.",
        "mechanism": "First Mercury goes. Then Venus. Both orbit inside where the new surface will sit.",
        "spike": "Earth might keep its orbit but not its oceans. They boil away long before the fire arrives.",
        "loop": "Every planet carries an expiry date written by its star. Yours is simply too distant to frighten you.",
    },
    visuals={
        "hook": [V("ai", None, "A vast swollen red Sun filling the frame with two small dark planets silhouetted against it, vertical")],
        "turn": [V("ai", None, "The core of the Sun dimming and contracting as its outer layers begin to billow outward"),
                 V("stock", "single green grape", "A single green grape held between finger and thumb"),
                 V("ai", None, "The grape swelling surreally until it fills an ordinary living room")],
        "mechanism": [V("ai", None, "Mercury being engulfed by an advancing wall of red stellar plasma"),
                      V("ai", None, "Venus disappearing into the same glowing surface moments later")],
        "spike": [V("ai", None, "Earth's oceans boiling away into white vapour, continents drying to bare rock"),
                  V("ai", None, "A scorched Earth still holding its orbit beneath an enormous red Sun")],
        "loop": [V("ai", None, "A calm present day Sun setting over a quiet ordinary horizon"),
                 V("ai", None, "A long slow pull back from Earth to the Sun, small and yellow and harmless")],
    })

add("meteor",
    cluster="things_we_got_wrong", pattern="WRONG_NAME", fmt="B", mood="energetic",
    title="Shooting Stars Do Not Burn Up From Friction",
    overlay="NOT FRICTION. COMPRESSION.",
    hook_a="Shooting stars are not burning from friction.",
    hook_b="The meteor is killed by air it never touches",
    spine="Meteors are destroyed by compression heating of the air ahead of them, not by friction.",
    anchor="70 km per second", anchor_spoken="seventy kilometres per second",
    mechanism="At those speeds the air cannot move aside, so it compresses in front of the rock and superheats.",
    consequence="A widely taught explanation is simply wrong.",
    source="settled atmospheric entry physics, deliberately unattributed",
    confidence="confirmed", saturation="low",
    sources=["Compression (ram) heating of the shock layer is settled atmospheric-entry physics. No single mission owns it, so style.md says credit nothing rather than invent an attribution."],
    beats={
        "hook": "Shooting stars are not burning from friction.",
        "turn": "The streak you wish upon is usually a pebble smaller than a grain of rice. Everyone learns it rubs against the air and catches fire.",
        "mechanism": "It arrives at up to seventy kilometres per second, far too fast to shove the air aside. The air piles up in front and compresses, and compressed gas turns violently hot.",
        "spike": "Squeeze a bicycle pump and feel the barrel warm. Same effect, wildly faster.",
        "loop": "That pebble is destroyed by air it never quite touches. Your wish rides on a shockwave.",
    },
    visuals={
        "hook": [V("ai", None, "A brilliant meteor streak tearing across a dark starfield, glowing compressed air piled ahead of it, vertical")],
        "turn": [V("stock", "grain of rice macro", "A single grain of rice resting on a fingertip, macro"),
                 V("ai", None, "A tiny dark pebble tumbling silently through space toward the blue limb of Earth"),
                 V("ai", None, "A classroom style diagram of the wrong explanation, arrows rubbing against the air")],
        "mechanism": [V("ai", None, "Slow motion meteor with a bright compressed shock layer glowing ahead of the rock"),
                      V("ai", None, "Air molecules stacking and compressing in front of a hypersonic object"),
                      V("ai", None, "The compressed cushion flaring white hot while the rock behind it stays dark")],
        "spike": [V("stock", "bicycle pump hands", "Hands working a bicycle pump, close on the metal barrel"),
                  V("ai", None, "Heat shimmer rising off the pump barrel, thermal glow effect")],
        "loop": [V("ai", None, "The pebble vaporising into glowing dust behind the shockwave ahead of it"),
                 V("ai", None, "A person watching a meteor streak overhead from a dark hillside, seen from behind")],
    })

add("horizon",
    cluster="cosmology_and_origins", pattern="OBSERVER_LIMIT", fmt="E",
    mood="mysterious",
    title="There Is a Wall in Space You Can Never Cross",
    overlay="A WALL YOU CANNOT CROSS",
    hook_a="There is a wall in space you can never cross.",
    hook_b="Some galaxies have already sent you their last light",
    spine="The observable universe has a hard edge set by light travel time, and expansion makes it permanent.",
    anchor="46 billion light years", anchor_spoken="forty six billion light years",
    mechanism="Light has had only a finite time to travel, so beyond a set distance nothing can ever reach us.",
    consequence="Part of reality is permanently unobservable.",
    source="Observable universe radius from standard cosmological parameters",
    confidence="confirmed", saturation="medium",
    sources=["Comoving radius of the observable universe about 46.5 billion light years, from standard cosmological parameters",
             "Accelerating expansion places distant galaxies permanently beyond the future event horizon"],
    beats={
        "hook": "There is a wall in space you can never cross.",
        "turn": "Not a barrier. A limit made of time, like hearing thunder only from storms close enough to reach you.",
        "mechanism": "That edge sits about forty six billion light years away in every direction.",
        "spike": "Worse, expansion hauls the most distant galaxies away faster than their light can close the gap.",
        "loop": "Some of them have already sent you their final photon. You will simply never receive it.",
    },
    visuals={
        "hook": [V("ai", None, "A lone observer at the centre of an enormous glowing sphere with a hard luminous edge, vertical")],
        "turn": [V("stock", "distant lightning storm", "A distant thunderstorm on the horizon at dusk"),
                 V("ai", None, "Sound rings spreading out from a storm and fading before reaching a listener")],
        "mechanism": [V("ai", None, "A vast sphere of galaxies with a sharply defined boundary shell around it"),
                      V("ai", None, "A measuring line extending from the observer out to the glowing boundary")],
        "spike": [V("ai", None, "Galaxies sliding outward faster than their light beams can travel inward"),
                  V("ai", None, "A light beam losing ground against stretching space, falling steadily behind")],
        "loop": [V("ai", None, "A single galaxy emitting one last photon before dimming away to nothing"),
                 V("ai", None, "That photon travelling forever through empty stretching space, never arriving")],
    })

add("sgr_a",
    cluster="galactic_structure", pattern="NAKED_NUMBER", fmt="A", mood="dramatic",
    title="Four Million Suns Are Crushed Into One Point",
    overlay="OUR GALAXY'S BLACK HOLE",
    hook_a="Four million Suns are crushed into a single point.",
    hook_b="Every star you can see is circling one dark point",
    spine="Sagittarius A star is a supermassive black hole at the centre of the Milky Way.",
    anchor="4.3 million solar masses", anchor_spoken="four point three million times our Sun",
    mechanism="Stellar orbits around an invisible point reveal its mass.",
    consequence="Our whole galaxy turns around something we cannot see.",
    source="Event Horizon Telescope image 2022, and decades of stellar orbit tracking",
    confidence="confirmed", saturation="medium",
    sources=["Sagittarius A* mass 4.297 million solar masses, from tracking the orbits of stars at the galactic centre",
             "Event Horizon Telescope image of Sagittarius A*, 2022",
             "The loop is constrained to stars in our own galaxy - Andromeda does not orbit Sagittarius A*."],
    beats={
        "hook": "Four million Suns are crushed into a single point.",
        "turn": "It sits twenty six thousand light years away at the centre of our galaxy, and nobody can see it directly.",
        "mechanism": "We found it by watching stars whip around something invisible. Their orbits gave the mass away. Sagittarius A star weighs about four point three million times our Sun.",
        "spike": "One of those stars moves fast enough to cross the whole width of the Earth in under two seconds.",
        "loop": "Nearly every star you can pick out by eye is circling it, including the Sun above your head.",
    },
    visuals={
        "hook": [V("ai", None, "A pitch black point at the centre of a blazing ring of superheated gas, vertical, Event Horizon Telescope style")],
        "turn": [V("ai", None, "Looking down the crowded glowing core of the Milky Way toward a dark centre"),
                 V("ai", None, "The galactic centre obscured behind thick dust lanes, nothing visible at the middle")],
        "mechanism": [V("ai", None, "Bright stars tracing tight elongated orbits around an empty black point"),
                      V("ai", None, "Orbit traces drawn as glowing ellipses all converging on one unseen mass"),
                      V("ai", None, "A mass scale tipping, millions of tiny suns stacked against one dark point")],
        "spike": [V("ai", None, "A star streaking past the black hole at extreme speed, heavily motion blurred"),
                  V("ai", None, "Earth shown for scale being crossed in a heartbeat by that same streak")],
        "loop": [V("ai", None, "A wide night sky full of stars, all faintly drifting in one vast circular current"),
                 V("ai", None, "Pull back from a person looking up, to the Sun, to the whole galaxy wheeling")],
    })


add("saturn_rings",
    cluster="deep_time", pattern="SCALE_COLLAPSE", fmt="B", mood="dramatic",
    title="Saturn's Rings Are Younger Than the Dinosaurs",
    overlay="RINGS YOUNGER THAN T-REX",
    hook_a="Saturn's rings are younger than the dinosaurs.",
    hook_b="The rings are a phase, not a feature",
    spine="Saturn's rings formed long after the planet, recently enough to postdate the dinosaurs.",
    anchor="<100 million years", anchor_spoken="a hundred million years",
    mechanism="Ring mass and dust contamination measured by Cassini imply a recent origin.",
    consequence="Saturn has not always looked the way we picture it.",
    source="Cassini Grand Finale ring mass measurement, 2017",
    confidence="contested", saturation="medium",
    sources=["Cassini Grand Finale gravity measurement of ring mass, 2017, implying an age of 10-100 million years",
             "Genuinely contested - some models still allow an ancient ring system. The script flags this in four words rather than stating it flat."],
    beats={
        "hook": "Saturn's rings are younger than the dinosaurs.",
        "turn": "Everyone assumes they formed with the planet, four and a half billion years ago. The ice says otherwise.",
        "mechanism": "Cassini weighed the rings on its final dive. Too little dark dust had settled on them. The best estimate puts them under a hundred million years old.",
        "spike": "A Tyrannosaurus could have looked up at a ringless Saturn. This is still debated, but the measurement stands.",
        "loop": "The rings are a phase, not a feature. You happen to be alive for it, and you are watching Saturn wear them.",
    },
    visuals={
        "hook": [V("ai", None, "Saturn with brilliant rings above a dinosaur silhouette on a dark ridge, vertical, cinematic")],
        "turn": [V("ai", None, "Saturn coalescing out of the early solar nebula four and a half billion years ago"),
                 V("ai", None, "The rings glittering clean and bright, close on individual ice boulders")],
        "mechanism": [V("ai", None, "The Cassini spacecraft diving through the narrow gap between Saturn and its rings"),
                      V("ai", None, "Dark dust slowly settling onto bright ice particles, thin coating building up"),
                      V("ai", None, "A glowing scale weighing the ring system against the planet")],
        "spike": [V("ai", None, "A Tyrannosaurus raising its head toward a ringless Saturn in a prehistoric sky"),
                  V("ai", None, "Two competing model diagrams of ring age shown side by side, neither settled")],
        "loop": [V("ai", None, "Saturn's rings thinning and dispersing away into empty space over time"),
                 V("ai", None, "Saturn seen through a small backyard telescope, rings sharp and present")],
    })

add("io",
    cluster="solar_system_oddities", pattern="NAKED_NUMBER", fmt="A", mood="energetic",
    title="Jupiter's Moon Io Has Four Hundred Erupting Volcanoes",
    overlay="JUPITER'S VOLCANO MOON",
    hook_a="One moon of Jupiter has four hundred erupting volcanoes.",
    hook_b="A moon being kneaded until it melts",
    spine="Io is squeezed by competing gravity until its interior melts and erupts.",
    anchor="400 volcanoes", anchor_spoken="four hundred erupting volcanoes",
    mechanism="Tidal flexing between Jupiter and the other large moons melts Io from inside.",
    consequence="Gravity alone can keep a world molten with no sunlight involved.",
    source="Voyager 1 plume discovery 1979, and NASA Galileo and Juno observations",
    confidence="confirmed", saturation="medium",
    sources=["Voyager 1 discovered active plumes on Io in 1979",
             "Roughly 400 active volcanoes catalogued from Galileo and Juno observations",
             "Plume heights up to ~300 km; ISS orbits at ~400 km, so the comparison is 'higher than most of the way to the station', phrased conservatively."],
    beats={
        "hook": "One moon of Jupiter has four hundred erupting volcanoes.",
        "turn": "Io is the innermost of Jupiter's big moons, and it is being kneaded like dough.",
        "mechanism": "Jupiter pulls it one way while the other moons pull back. Voyager saw the plumes in nineteen seventy nine. That constant flexing melts Io from the inside.",
        "spike": "Its plumes throw sulphur hundreds of kilometres up, roughly as high as the space station you sometimes see crossing the sky.",
        "loop": "Nothing you could stand on there would stay still. The ground itself rises and falls like a tide.",
    },
    visuals={
        "hook": [V("ai", None, "Io's sulphur yellow cratered surface erupting with plumes, Jupiter looming enormous behind it, vertical")],
        "turn": [V("ai", None, "Io orbiting close in against Jupiter's banded cloud tops, tiny against the giant"),
                 V("stock", "kneading dough hands", "Hands kneading and folding dough on a floured surface")],
        "mechanism": [V("ai", None, "Gravity arrows stretching Io from opposite sides, the moon visibly deforming"),
                      V("ai", None, "Voyager era grainy image of a plume rising off Io's edge against black space"),
                      V("ai", None, "Cutaway of Io showing molten rock churning beneath a thin crust")],
        "spike": [V("ai", None, "A sulphur plume arcing hundreds of kilometres above Io's limb into space"),
                  V("ai", None, "The space station passing as a bright moving point across a twilight sky")],
        "loop": [V("ai", None, "Io's surface visibly rising and falling, cracks opening and closing"),
                 V("ai", None, "A lone figure standing on that heaving volcanic plain, tiny in frame")],
    })

add("galaxy_collision",
    cluster="galactic_structure", pattern="INVERTED_ASSUMPTION", fmt="C", mood="mysterious",
    title="Two Galaxies Will Collide and Nothing Will Hit",
    overlay="TWO GALAXIES, ZERO CRASHES",
    hook_a="What happens when two galaxies crash and nothing collides?",
    hook_b="The Milky Way is about to hit something",
    spine="Galaxies merge without their stars colliding, because the space between stars is vast.",
    anchor="4 billion years", anchor_spoken="four billion years",
    mechanism="Stellar separations are so large that a galactic merger produces essentially no stellar collisions.",
    consequence="Emptiness, not matter, is what a galaxy is mostly made of.",
    source="Hubble measurements of Andromeda's transverse motion",
    confidence="confirmed", saturation="medium",
    sources=["Hubble measurement of Andromeda's proper motion, giving a merger in roughly 4 billion years",
             "Typical stellar separations make direct stellar collisions vanishingly unlikely during a merger",
             "Scale analogy: Sun as a grain of sand puts the nearest star tens of kilometres away."],
    beats={
        "hook": "What happens when two galaxies crash and nothing collides?",
        "turn": "Andromeda is falling toward us. In about four billion years the two galaxies merge completely.",
        "mechanism": "Hubble measured its approach across the sky. But stars sit so far apart that almost none of them will ever touch.",
        "spike": "Shrink the Sun to a grain of sand and the next grain sits tens of kilometres away.",
        "loop": "The sky you would stand under just fills with unfamiliar stars. Not one of them hits you.",
    },
    visuals={
        "hook": [V("ai", None, "Two spiral galaxies passing through one another, stars sliding past untouched, vertical")],
        "turn": [V("ai", None, "Andromeda growing larger in a night sky over a still landscape, time lapse"),
                 V("ai", None, "Two galaxies drawn together by gravity, arms beginning to distort")],
        "mechanism": [V("ai", None, "Hubble tracking tiny shifts in Andromeda's position, measurement grid overlaid"),
                      V("ai", None, "Zoom from a dense-looking galaxy arm to the vast empty gaps between its stars")],
        "spike": [V("stock", "grain of sand fingertip", "A single grain of sand on a fingertip, extreme macro"),
                  V("ai", None, "Two grains of sand separated by an enormous empty landscape, scale comparison")],
        "loop": [V("ai", None, "A night sky slowly filling with a second galaxy's worth of new stars"),
                 V("ai", None, "A person standing safely beneath that transformed sky, seen from behind")],
    })

add("gold",
    cluster="stellar_lifecycle", pattern="SECOND_PERSON_IMPLICATION", fmt="E", mood="dramatic",
    title="The Gold in Your Ring Came From Colliding Stars",
    overlay="YOUR GOLD CAME FROM A CRASH",
    hook_a="The gold on your finger was made by colliding stars.",
    hook_b="Gold needs something more violent than a star",
    spine="Heavy elements like gold are forged in neutron star mergers, not ordinary stellar fusion.",
    anchor="130 million light years", anchor_spoken="one hundred and thirty million light years",
    mechanism="Ordinary fusion stops at iron, so gold requires a neutron star collision.",
    consequence="Jewellery is debris from one of the most violent events in physics.",
    source="LIGO and Virgo detection of the neutron star merger GW170817, 2017",
    confidence="confirmed", saturation="low",
    sources=["GW170817 neutron star merger detected by LIGO/Virgo in 2017, at about 130 million light years",
             "Follow-up observations identified heavy element production including gold",
             "Mass estimates for gold produced are model-dependent, so the script says 'several Earth masses' rather than a precise figure."],
    beats={
        "hook": "The gold on your finger was made by colliding stars.",
        "turn": "Ordinary stars fuse elements up to iron and then stop. Gold needs something far more violent than that.",
        "mechanism": "In twenty seventeen, detectors caught two neutron stars colliding one hundred and thirty million light years away. Neutron stars are the collapsed cores of dead suns. The crash flung out heavy elements, gold among them.",
        "spike": "One collision made several times the Earth's mass in gold, scattered into space.",
        "loop": "Every gold thing you own is wreckage from a crash like that. You are wearing it.",
    },
    visuals={
        "hook": [V("stock", "gold ring close up", "A gold ring on a finger, warm light, extreme close up"),
                 V("ai", None, "Two dense dead star cores spiralling together, spacetime rippling around them")],
        "turn": [V("ai", None, "Cutaway of a star's layered fusion shells ending at an iron core"),
                 V("ai", None, "The fusion chain halting at iron, the process visibly stalling")],
        "mechanism": [V("ai", None, "Two neutron stars merging in a blinding burst, gravitational waves spreading outward"),
                      V("ai", None, "A detector readout spiking as the gravitational wave arrives"),
                      V("ai", None, "Heavy elements spraying outward from the merger as glowing debris")],
        "spike": [V("ai", None, "A cloud of golden material expanding outward from the merger site"),
                  V("ai", None, "Earth shown small beside that cloud, dwarfed by the mass of gold in it")],
        "loop": [V("stock", "gold jewellery", "Gold jewellery laid out on a dark surface"),
                 V("ai", None, "The jewellery dissolving back into the glowing debris cloud that made it")],
    })

add("laser_mirrors",
    cluster="observation_and_instruments", pattern="MISSING_THING", fmt="A", mood="uplifting",
    title="Apollo Left Mirrors on the Moon and We Still Use Them",
    overlay="WE STILL SHOOT THE MOON",
    hook_a="Apollo left mirrors on the Moon that we still use.",
    hook_b="Hardware nobody maintains is still answering",
    spine="Apollo retroreflectors still return laser pulses, measuring the Moon's distance today.",
    anchor="3.8 cm per year", anchor_spoken="three point eight centimetres",
    mechanism="Reflector panels need no power, so timing a laser's round trip still gives the distance.",
    consequence="The Moon's retreat is measured, not inferred.",
    source="Lunar Laser Ranging, Apollo 11, 14 and 15 retroreflector arrays",
    confidence="confirmed", saturation="low",
    sources=["Apollo 11, 14 and 15 left retroreflector arrays; Lunar Laser Ranging still uses them",
             "Measured lunar recession 3.8 cm/yr, with range precision at the millimetre level"],
    beats={
        "hook": "Apollo left mirrors on the Moon that we still use.",
        "turn": "Three crews set down panels of reflectors and aimed them back at Earth. Nobody switched them off, because they need no power at all.",
        "mechanism": "Observatories still fire lasers at those panels. Timing how long the light takes to come back gives the distance to within a few millimetres.",
        "spike": "That is how we know the Moon drifts three point eight centimetres further away each year, about as fast as your fingernails grow.",
        "loop": "Fifty years on, abandoned hardware is still answering. You can watch the Moon leave, one nail's length at a time.",
    },
    visuals={
        "hook": [V("ai", None, "An Apollo retroreflector array on grey lunar dust, Earth small in the black sky above, vertical")],
        "turn": [V("ai", None, "An Apollo astronaut setting a reflector panel down and levelling it"),
                 V("ai", None, "The panel sitting alone on the Moon as decades pass, undisturbed and unpowered")],
        "mechanism": [V("ai", None, "A green laser beam lancing up from an observatory dome into the night"),
                      V("ai", None, "The beam striking the lunar panel and bouncing straight back along its path"),
                      V("ai", None, "A timing readout counting the round trip in fractions of a second")],
        "spike": [V("ai", None, "The Moon's orbit expanding by a hair's width, measurement callout on screen"),
                  V("stock", "fingernails hand", "A close up of a hand, fingernails in sharp focus")],
        "loop": [V("ai", None, "The abandoned reflector panel still catching a pulse of laser light in the dark"),
                 V("ai", None, "The Moon slowly receding from Earth across a long time lapse")],
    })

add("freeze",
    cluster="physics_limits", pattern="INVERTED_ASSUMPTION", fmt="B", mood="mysterious",
    title="You Would Not Freeze Instantly in Space",
    overlay="SPACE WON'T FREEZE YOU FAST",
    hook_a="Space would not freeze you. Not quickly, anyway.",
    hook_b="A vacuum is one of the best insulators there is",
    spine="A vacuum removes heat only by radiation, so freezing is slow; oxygen loss is what kills first.",
    anchor="15 seconds", anchor_spoken="about fifteen seconds",
    mechanism="With no matter to conduct heat away, the body loses warmth only by radiation.",
    consequence="The danger in vacuum is oxygen, not cold.",
    source="NASA vacuum chamber accident, 1966",
    confidence="confirmed", saturation="low",
    sources=["NASA vacuum chamber decompression accident, 1966 - the subject lost consciousness in roughly 15 seconds and survived",
             "Radiative heat loss only, with no conduction or convection in vacuum - settled thermodynamics"],
    beats={
        "hook": "Space would not freeze you. Not quickly, anyway.",
        "turn": "Films show instant ice. But cold needs something to carry heat off, the way a winter wind strips warmth from your hands. A vacuum has nothing to carry it.",
        "mechanism": "Heat can only leave your body as radiation, which is slow. A NASA chamber accident in nineteen sixty six showed what actually happens first.",
        "spike": "The air in your lungs would rush out, and you would black out in about fifteen seconds.",
        "loop": "You would not be frozen. You would be unconscious, and still warm.",
    },
    visuals={
        "hook": [V("ai", None, "A figure floating in shadow just outside a spacecraft, faint body heat glowing off them, vertical")],
        "turn": [V("ai", None, "A dramatic film style shot of a body flash freezing, then cracking apart as false"),
                 V("stock", "cold wind hands", "Bare hands in a biting winter wind, breath visible"),
                 V("ai", None, "Air molecules carrying heat away, then vanishing to leave nothing at all")],
        "mechanism": [V("ai", None, "Faint infrared heat radiating slowly off a body into black empty space"),
                      V("ai", None, "A nineteen sixties NASA vacuum test chamber, heavy steel door and viewing port")],
        "spike": [V("ai", None, "Air rushing out of a suit in an instant, vapour flashing away into vacuum"),
                  V("ai", None, "A countdown of about fifteen seconds ticking as the figure goes limp")],
        "loop": [V("ai", None, "The floating figure unconscious but still radiating warmth, drifting slowly")],
    })

add("neptune_diamonds",
    cluster="solar_system_oddities", pattern="NAKED_NUMBER", fmt="A", mood="dramatic",
    title="It Rains Diamonds Inside Neptune",
    overlay="IT RAINS DIAMONDS THERE",
    hook_a="Inside Neptune, it rains diamonds.",
    hook_b="Something is quietly snowing gemstones",
    spine="Extreme pressure inside Neptune splits carbon out of methane and compresses it into diamond.",
    anchor="millions of atmospheres", anchor_spoken="millions of times the pressure at sea level",
    mechanism="Shock compression experiments show methane breaking down into diamond at Neptune's interior pressures.",
    consequence="Ordinary chemistry behaves unrecognisably under enough pressure.",
    source="Laboratory shock compression experiments on hydrocarbons",
    confidence="confirmed", saturation="medium",
    sources=["Laboratory shock compression experiments producing nanodiamonds from hydrocarbons at ice giant interior conditions",
             "Lab-supported and modelled, never directly observed inside Neptune - the script says so explicitly."],
    beats={
        "hook": "Inside Neptune, it rains diamonds.",
        "turn": "Neptune's interior is a crushed soup of water, ammonia and methane, at millions of times the pressure at sea level.",
        "mechanism": "Squeeze methane hard enough and its carbon splits out and locks into diamond. Laboratories have made it happen with shock waves.",
        "spike": "Those diamonds then sink, falling for thousands of kilometres through the dark like hail. Nobody has seen it directly.",
        "loop": "The blue dot you can barely find out there may be quietly snowing gemstones you will never catch.",
    },
    visuals={
        "hook": [V("ai", None, "Diamond shards falling through the crushing blue interior of Neptune, vertical, cinematic")],
        "turn": [V("ai", None, "Cutaway of Neptune showing its dense hot interior beneath the blue cloud tops"),
                 V("ai", None, "A pressure gauge needle spinning past every marking into the far extreme")],
        "mechanism": [V("ai", None, "A methane molecule compressed until its carbon atom breaks free"),
                      V("ai", None, "Carbon atoms locking into a diamond lattice under enormous force"),
                      V("ai", None, "A laboratory shock compression rig firing, bright flash behind shielding")],
        "spike": [V("ai", None, "Diamonds sinking slowly through dark dense fluid, catching faint light"),
                  V("stock", "hail falling", "Hailstones falling and bouncing on a hard surface")],
        "loop": [V("ai", None, "Neptune as a small pale blue dot seen from very far away in black space"),
                 V("ai", None, "Diamonds drifting down endlessly inside that distant blue point, unreachable")],
    })


add("wider_than_old",
    cluster="deep_time", pattern="SCALE_COLLAPSE", fmt="C", mood="mysterious",
    title="The Universe Is Wider Than It Is Old",
    overlay="WIDER THAN IT IS OLD",
    hook_a="How is the universe wider than it is old?",
    hook_b="Nothing outran light, but the road got longer",
    spine="Space expanded while light was in flight, so the observable universe is far wider than light travel time alone allows.",
    anchor="93 billion light years", anchor_spoken="ninety three billion light years",
    mechanism="Expansion stretches the space light has already crossed, carrying sources further away than the light's own travel.",
    consequence="Distance in cosmology does not mean what everyday distance means.",
    source="Standard cosmological parameters for the observable universe",
    confidence="confirmed", saturation="medium",
    sources=["Observable universe diameter about 93 billion light years, against an age of 13.8 billion years",
             "The gap comes from metric expansion, not from anything travelling faster than light"],
    beats={
        "hook": "How is the universe wider than it is old?",
        "turn": "Light has had thirteen point eight billion years to travel. So the whole thing should be twice that across. It is not.",
        "mechanism": "Space itself stretched while the light was still in flight. That carries distant galaxies further out than their light alone could ever reach. The measured span is about ninety three billion light years.",
        "spike": "Picture ants walking across a balloon that keeps inflating underneath them.",
        "loop": "Nothing outran light. The road you are looking down simply got longer while you were looking.",
    },
    visuals={
        "hook": [V("ai", None, "A vast sphere of galaxies with a light beam racing across it and losing ground, vertical")],
        "turn": [V("ai", None, "A clock counting 13.8 billion years beside a measuring line across the cosmos"),
                 V("ai", None, "The measuring line overshooting the clock's reach, mismatch highlighted")],
        "mechanism": [V("ai", None, "A grid of space stretching outward while a photon crawls across it"),
                      V("ai", None, "Galaxies riding the stretching grid away from a central observer"),
                      V("ai", None, "The full span of the observable universe drawn as a glowing measured diameter")],
        "spike": [V("stock", "inflating balloon", "A balloon being inflated in close up against a plain background"),
                  V("ai", None, "Ants walking on an inflating balloon, the gaps between them widening")],
        "loop": [V("ai", None, "A long straight road stretching and lengthening ahead of a still viewer"),
                 V("ai", None, "A lone observer under a sky of galaxies drifting steadily further out")],
    })

add("apollo_memory",
    cluster="human_spaceflight", pattern="NAKED_NUMBER", fmt="D", mood="uplifting",
    title="Apollo Flew to the Moon on Four Kilobytes of Memory",
    overlay="FOUR KILOBYTES WENT TO THE MOON",
    hook_a="Apollo reached the Moon on four kilobytes of memory.",
    hook_b="Almost everything you own beats the Moon computer",
    spine="The Apollo Guidance Computer ran the lunar missions on about four kilobytes of working memory.",
    anchor="4 kilobytes", anchor_spoken="four kilobytes",
    mechanism="The guidance computer's erasable memory was about four kilobytes, and it flew every crewed lunar mission.",
    consequence="Capability and computing power are not the same thing.",
    source="Apollo Guidance Computer specifications",
    confidence="confirmed", saturation="medium",
    sources=["Apollo Guidance Computer erasable memory: 2048 words of 16 bits, about 4 KB",
             "24 people flew to the Moon across Apollo 8 to 17; 12 walked on it"],
    beats={
        "hook": "Apollo reached the Moon on four kilobytes of memory.",
        "turn": "Count the things that beat it. A musical greetings card holds more memory than that.",
        "mechanism": "The Apollo Guidance Computer worked with about four kilobytes. It flew twenty four people to the Moon and landed twelve of them safely.",
        "spike": "A pocket calculator beats it. Your car key beats it. One photo on your phone is thousands of times larger.",
        "loop": "None of that extra memory has taken anyone back since. You are carrying more computer than they landed with.",
    },
    visuals={
        "hook": [V("ai", None, "The Apollo lunar module on the Moon beside a single tiny memory chip, scale comparison, vertical")],
        "turn": [V("stock", "greeting card open", "A greetings card being opened on a table"),
                 V("ai", None, "The tiny sound chip inside the card shown in macro detail")],
        "mechanism": [V("ai", None, "The Apollo Guidance Computer panel with its numeric display and keypad, period accurate"),
                      V("ai", None, "The lunar module descending toward the grey surface, dust kicking up"),
                      V("ai", None, "Twelve boot prints pressed into lunar dust")],
        "spike": [V("stock", "pocket calculator", "A basic pocket calculator on a desk"),
                  V("stock", "car key fob", "A car key fob held in a hand"),
                  V("stock", "phone photo gallery", "A phone screen showing a grid of photos")],
        "loop": [V("ai", None, "A modern smartphone resting beside the old guidance computer panel"),
                 V("ai", None, "The empty lunar surface with old boot prints and no new ones")],
    })

add("glass_rain",
    cluster="exoplanets", pattern="INVERTED_ASSUMPTION", fmt="A", mood="dramatic",
    title="On This Planet It Rains Glass, Sideways",
    overlay="IT RAINS GLASS SIDEWAYS",
    hook_a="There is a blue planet where it rains glass.",
    hook_b="Its ocean blue colour is not water at all",
    spine="HD 189733b's deep blue comes from silicate particles, driven sideways by extreme winds.",
    anchor="8,000 km/h winds", anchor_spoken="eight thousand kilometres an hour",
    mechanism="Silicates condense in the hot atmosphere and are driven horizontally by extreme winds.",
    consequence="A familiar colour can mean something completely unfamiliar.",
    source="Hubble colour measurement of the exoplanet HD 189733b",
    confidence="confirmed", saturation="low",
    sources=["Hubble measured the visible colour of HD 189733b directly - deep blue from silicate scattering, not water",
             "Modelled wind speeds around 8,000 km/h (about 2 km/s), faster than a rifle bullet"],
    beats={
        "hook": "There is a blue planet where it rains glass.",
        "turn": "From far away it looks like a deep blue ocean world. That colour is not water. It is silicate particles hanging in the air.",
        "mechanism": "Hubble measured the blue directly. The atmosphere runs hot enough to melt silicate into droplets, and the winds drive them sideways at eight thousand kilometres an hour.",
        "spike": "That is faster than a rifle bullet, and the rain travelling with it is molten glass.",
        "loop": "You would not get wet standing there. You would be sandblasted.",
    },
    visuals={
        "hook": [V("ai", None, "A deep cobalt blue exoplanet with horizontal streaks of molten glass across it, vertical")],
        "turn": [V("ai", None, "The blue planet seen from a great distance, looking deceptively like an ocean world"),
                 V("ai", None, "Push in until the blue resolves into a haze of suspended glass particles")],
        "mechanism": [V("ai", None, "Hubble observing a planet transiting its star, colour spectrum splitting out"),
                      V("ai", None, "Silicate droplets condensing in a superheated atmosphere"),
                      V("ai", None, "Horizontal glass rain streaking flat across the sky at enormous speed")],
        "spike": [V("ai", None, "A bullet in flight, heavily motion blurred against a dark background"),
                  V("ai", None, "Molten glass streaking horizontally at the same blurred speed")],
        "loop": [V("ai", None, "A figure standing on the surface being stripped by horizontal glass rain")],
    })

add("twinkle",
    cluster="things_we_got_wrong", pattern="WRONG_NAME", fmt="B", mood="mysterious",
    title="Stars Do Not Actually Twinkle",
    overlay="STARS DON'T TWINKLE",
    hook_a="Stars do not actually twinkle.",
    hook_b="The shimmer is coming from the air, not the star",
    spine="Twinkling is atmospheric refraction, not anything the star is doing.",
    anchor="100 km of atmosphere", anchor_spoken="a hundred kilometres",
    mechanism="Moving pockets of warm and cool air bend starlight slightly differently moment to moment.",
    consequence="Something everyone has watched their whole life is misattributed.",
    source="settled atmospheric optics, deliberately unattributed",
    confidence="confirmed", saturation="medium",
    sources=["Atmospheric scintillation is settled optics with no single owning mission, so style.md says credit nothing rather than invent an attribution",
             "Planets show a resolvable disc and so scintillate far less than point-source stars"],
    beats={
        "hook": "Stars do not actually twinkle.",
        "turn": "That shimmer everyone has watched since childhood is not something the star is doing. It is coming from the air above your head.",
        "mechanism": "Starlight crosses a hundred kilometres of restless atmosphere on the way down. Pockets of warm and cool air bend it slightly differently, moment to moment.",
        "spike": "It is the same wobble you see rising off hot tarmac in summer, only far away and far fainter.",
        "loop": "Planets barely shimmer, because they are discs and not points. On the next clear night you can tell them apart by eye.",
    },
    visuals={
        "hook": [V("ai", None, "Split frame: a rock steady star seen from space beside the same star shimmering through air, vertical")],
        "turn": [V("ai", None, "A child on grass looking up at a twinkling night sky, seen from behind"),
                 V("ai", None, "Layers of turbulent air drawn over a dark sky, moving and rippling")],
        "mechanism": [V("ai", None, "A starlight ray bending repeatedly as it descends through the atmosphere"),
                      V("ai", None, "Warm and cool air pockets shown as shifting lenses in the dark"),
                      V("ai", None, "A single star's image jittering and brightening in a telescope view")],
        "spike": [V("stock", "heat haze road", "Heat shimmer rising off a hot tarmac road in summer"),
                  V("ai", None, "The same wobbling distortion applied to a distant star point in the dark")],
        "loop": [V("ai", None, "A steady planet beside a shimmering star in the same patch of sky"),
                 V("ai", None, "A person on a hillside picking out the steady point among the flickering ones")],
    })

add("mercury_ice",
    cluster="solar_system_oddities", pattern="INVERTED_ASSUMPTION", fmt="A", mood="mysterious",
    title="Mercury Has Ice Despite Sitting Closest to the Sun",
    overlay="ICE ON THE CLOSEST PLANET",
    hook_a="Mercury sits closest to the Sun and still has ice.",
    hook_b="Shade beats distance, even next to the Sun",
    spine="Mercury's negligible tilt leaves polar crater floors in permanent shadow, cold enough to hold water ice.",
    anchor="400 degrees C", anchor_spoken="four hundred degrees",
    mechanism="With almost no axial tilt, some polar crater floors never receive sunlight at all.",
    consequence="Temperature is set by exposure, not only by distance.",
    source="NASA MESSENGER, water ice at Mercury's poles confirmed 2012",
    confidence="confirmed", saturation="low",
    sources=["NASA MESSENGER confirmed water ice in permanently shadowed polar craters on Mercury, 2012",
             "Mercury's axial tilt is about 0.03 degrees, so polar crater floors never see the Sun",
             "Daytime equatorial surface temperatures reach roughly 430 C; lead melts at 327 C"],
    beats={
        "hook": "Mercury sits closest to the Sun and still has ice.",
        "turn": "Daytime there passes four hundred degrees. Lead would melt on the open ground.",
        "mechanism": "But Mercury barely tilts, so the floors of its polar craters never see sunlight at all. NASA's MESSENGER found water ice sitting in that permanent shadow.",
        "spike": "Some of those crater floors are colder than Pluto, a few kilometres from ground hot enough to melt metal.",
        "loop": "Distance from the Sun is not what sets temperature. Shade is, the same way it is for you when you cross to the shady side of a street.",
    },
    visuals={
        "hook": [V("ai", None, "Mercury's scorched cratered surface with white ice hidden in a polar crater shadow, vertical")],
        "turn": [V("ai", None, "The Sun looming enormous over Mercury's blasted equatorial plains"),
                 V("ai", None, "Metal glowing and softening on sunlit rock")],
        "mechanism": [V("ai", None, "Mercury shown upright with almost no axial tilt, polar craters in permanent dark"),
                      V("ai", None, "The MESSENGER spacecraft in orbit scanning the polar region"),
                      V("ai", None, "Radar bright deposits mapped inside shadowed crater floors")],
        "spike": [V("ai", None, "A sharp line across a crater rim, blazing sunlight one side, deep shadow the other"),
                  V("ai", None, "Frost sitting in the shadowed floor metres from sun-blasted rock")],
        "loop": [V("stock", "shaded street sunlight", "A street with one side in bright sun and the other in deep shade"),
                 V("ai", None, "A person stepping from glare into shadow, the temperature shift implied by light"),
                 V("ai", None, "Mercury rotating with its permanently shadowed poles marked in cool blue")],
    })

add("sun_vanishes",
    cluster="physics_limits", pattern="OBSERVER_LIMIT", fmt="C", mood="mysterious",
    title="If the Sun Vanished We Would Not Know for Eight Minutes",
    overlay="EIGHT MINUTES OF NOT KNOWING",
    hook_a="If the Sun vanished, how long until you noticed?",
    hook_b="Earth would keep curving around nothing",
    spine="Gravity propagates at light speed, so Earth's orbit and the daylight would both persist for over eight minutes.",
    anchor="8 min 20 s", anchor_spoken="eight minutes and twenty seconds",
    mechanism="Gravitational influence travels at the speed of light, confirmed by the arrival timing of a neutron star merger.",
    consequence="No influence in physics is instant, not even gravity.",
    source="LIGO and Virgo GW170817 timing against its gamma ray burst, 2017",
    confidence="confirmed", saturation="medium",
    sources=["GW170817: gravitational waves and light from the same neutron star merger arrived within about two seconds after 130 million years of travel, constraining gravity's speed to light speed",
             "Mean Sun to Earth light travel time is 8 minutes 20 seconds"],
    beats={
        "hook": "If the Sun vanished, how long until you noticed?",
        "turn": "Most people assume Earth would be flung off immediately. Gravity does not work that fast.",
        "mechanism": "Gravity travels at the speed of light. When two neutron stars collided in twenty seventeen, their gravitational waves and their light reached us together, which pinned it down.",
        "spike": "So Earth would keep curving around nothing for eight minutes and twenty seconds, and the sky would stay lit the whole time.",
        "loop": "You could finish a conversation before the dark arrived. The Sun you can see right now already left.",
    },
    visuals={
        "hook": [V("ai", None, "Earth orbiting calmly around an empty patch of black space where the Sun used to be, vertical")],
        "turn": [V("ai", None, "A dramatic depiction of Earth flung out of orbit, then marked as wrong"),
                 V("ai", None, "Earth's orbital path holding steady and unchanged")],
        "mechanism": [V("ai", None, "A gravitational wave front expanding outward at the same pace as a light front"),
                      V("ai", None, "Two neutron stars merging, waves and light leaving together"),
                      V("ai", None, "Two detector traces spiking at almost the same instant, side by side")],
        "spike": [V("ai", None, "A sunlit Earth with a countdown of eight minutes running, Sun already absent"),
                  V("ai", None, "The last of the sunlight sweeping across the planet and going out")],
        "loop": [V("stock", "two people talking", "Two people in conversation at a table, warm daylight"),
                 V("ai", None, "A calm present day Sun in a blue sky, unremarkable")],
    })

add("betelgeuse",
    cluster="stellar_lifecycle", pattern="TIMEBOMB", fmt="E", mood="mysterious",
    title="Orion's Red Shoulder Star Is Six Centuries Out of Date",
    overlay="ORION'S STAR IS LATE",
    hook_a="The red star in Orion is six centuries out of date.",
    hook_b="You are watching a six hundred year old message",
    spine="Betelgeuse is so distant that tonight's view of it left before Columbus sailed.",
    anchor="650 light years", anchor_spoken="six hundred and fifty light years",
    mechanism="Light travel time means the star's current state is unobservable from here.",
    consequence="Every star you see is a delayed report, not a live view.",
    source="Distance estimates for Betelgeuse, roughly 650 light years",
    confidence="confirmed", saturation="medium",
    sources=["Betelgeuse distance is about 650 light years; estimates carry real uncertainty, so the script says 'about'",
             "Betelgeuse will end as a supernova, but a 2025 companion-star finding weakens any 'imminent' framing - the script explicitly says nobody can say when",
             "Its radius would extend past the orbit of Jupiter if placed at the Sun's position"],
    beats={
        "hook": "The red star in Orion is six centuries out of date.",
        "turn": "Find Orion tonight and look at its shoulder. The red one is Betelgeuse, a dying supergiant star.",
        "mechanism": "It sits about six hundred and fifty light years away. The light landing on your eye left before Columbus sailed.",
        "spike": "It has swollen enough to swallow the orbit of Jupiter. When it does explode, it will be visible in daylight. Nobody can say when.",
        "loop": "You are not really watching a star. You are watching a very old message about one.",
    },
    visuals={
        "hook": [V("ai", None, "The Orion constellation with its shoulder star blazing deep red, recognisable shape, vertical")],
        "turn": [V("ai", None, "A person outdoors tracing the Orion pattern in a clear night sky, seen from behind"),
                 V("ai", None, "Push in on the red shoulder star until it fills frame as a churning supergiant")],
        "mechanism": [V("ai", None, "A light wave leaving Betelgeuse and crossing centuries of empty space"),
                      V("ai", None, "A fifteenth century sailing ship at sea beneath the same red star")],
        "spike": [V("ai", None, "Betelgeuse scaled against the solar system, its surface engulfing Jupiter's orbit"),
                  V("ai", None, "A supernova flaring bright enough to cast shadows in daytime"),
                  V("ai", None, "A question mark of uncertainty over a calendar of unknown dates")],
        "loop": [V("ai", None, "The red star seen small again in Orion above a quiet rooftop"),
                 V("ai", None, "The starlight rendered as an old sealed letter arriving centuries late")],
    })


add("hawking",
    cluster="physics_limits", pattern="INVERTED_ASSUMPTION", fmt="C", mood="mysterious",
    title="Black Holes Are Slowly Evaporating",
    overlay="BLACK HOLES ARE DYING",
    hook_a="What happens to a black hole that stops eating?",
    hook_b="Even these do not last forever",
    spine="Black holes should lose mass over time through Hawking radiation and eventually disappear.",
    anchor="10^67 years", anchor_spoken="sixty seven zeros",
    mechanism="Particle pairs at the horizon let one escape while the other falls in, costing the hole mass.",
    consequence="Nothing in physics is genuinely permanent.",
    source="Hawking's 1974 prediction of black hole radiation",
    confidence="hypothesis", saturation="medium",
    sources=["Hawking radiation, predicted 1974 - theoretically well established but never observed",
             "Evaporation time for a solar mass black hole is of order 10^67 years",
             "The script flags 'never yet observed' in four words rather than presenting it as measured."],
    beats={
        "hook": "What happens to a black hole that stops eating?",
        "turn": "Everyone treats them as permanent. Hawking showed they should slowly leak away instead.",
        "mechanism": "Empty space constantly throws up pairs of particles. Right at the edge of a black hole, one can escape while the other falls in, so the hole loses a little mass. Never yet observed.",
        "spike": "It is absurdly slow. A black hole as heavy as our Sun would need a number of years written with sixty seven zeros.",
        "loop": "Nothing you can point at lasts forever, not even these. They will simply outlive you by more zeros than you can say.",
    },
    visuals={
        "hook": [V("ai", None, "A black hole visibly shrinking, faint light bleeding off its edge into darkness, vertical")],
        "turn": [V("ai", None, "A black hole rendered as a permanent fixed void against stars"),
                 V("ai", None, "The same void beginning to fray faintly at its boundary")],
        "mechanism": [V("ai", None, "Particle pairs flickering into existence in empty space and annihilating"),
                      V("ai", None, "One particle of a pair escaping the horizon while its partner falls in"),
                      V("ai", None, "The black hole's boundary contracting by an imperceptible amount")],
        "spike": [V("ai", None, "A vast string of zeros scrolling endlessly across a dark starfield"),
                  V("ai", None, "A Sun mass black hole beside a clock whose hands never visibly move")],
        "loop": [V("ai", None, "Stars and galaxies winking out one by one across an emptying universe"),
                 V("ai", None, "A final faint black hole glow fading into total darkness")],
    })

add("black_hole_photo",
    cluster="observation_and_instruments", pattern="WRONG_NAME", fmt="B", mood="mysterious",
    title="We Have Never Photographed a Black Hole",
    overlay="THAT PHOTO ISN'T THE HOLE",
    hook_a="Nobody has ever photographed a black hole.",
    hook_b="The famous orange ring is not the thing itself",
    spine="Every black hole image shows the glowing gas around it; the hole itself emits nothing.",
    anchor="55 million light years", anchor_spoken="fifty five million light years",
    mechanism="The Event Horizon Telescope imaged superheated gas orbiting M87; the hole is the dark gap.",
    consequence="The subject of the most reproduced space image is an absence.",
    source="Event Horizon Telescope image of M87, 2019",
    confidence="confirmed", saturation="medium",
    sources=["Event Horizon Telescope image of the M87 black hole, released 2019",
             "M87 lies about 55 million light years away",
             "The image shows the accretion glow and shadow; the event horizon itself emits no light"],
    beats={
        "hook": "Nobody has ever photographed a black hole.",
        "turn": "You have seen the famous orange ring. That ring is not the black hole.",
        "mechanism": "The Event Horizon Telescope imaged superheated gas whipping around a monster at the heart of a giant galaxy, fifty five million light years away. The hole itself sits in the middle, giving off nothing at all.",
        "spike": "You are seeing a hole in the picture, the way you would recognise someone by the gap they leave in a crowd.",
        "loop": "That picture is a portrait of an absence. The one thing you are looking for is the part that is not there.",
    },
    visuals={
        "hook": [V("ai", None, "The famous orange accretion ring with its true black centre marked as an absence, vertical")],
        "turn": [V("ai", None, "The orange ring image displayed on a screen, widely reproduced"),
                 V("ai", None, "The ring with the glowing gas highlighted and the centre left untouched")],
        "mechanism": [V("ai", None, "A global array of radio dishes across the Earth all pointing at one target"),
                      V("ai", None, "Superheated gas whipping in a tight circle around an invisible centre"),
                      V("ai", None, "The elliptical galaxy M87 with a bright jet streaming from its core")],
        "spike": [V("stock", "crowd of people", "A dense crowd of people from above"),
                  V("ai", None, "A person shaped gap opening in that crowd, the absence obvious")],
        "loop": [V("ai", None, "The ring image framed like a formal portrait with an empty centre"),
                 V("ai", None, "Everything around the dark centre dimming until only the void remains"),
                 V("ai", None, "Slow push into the black centre of the ring until darkness fills frame")],
    })

add("iapetus",
    cluster="solar_system_oddities", pattern="MISSING_THING", fmt="A", mood="mysterious",
    title="Saturn's Moon Iapetus Is Two Different Colours",
    overlay="ONE MOON, TWO COLOURS",
    hook_a="One moon of Saturn is black on one side.",
    hook_b="A moon painted dark on the face that leads",
    spine="Iapetus sweeps up dark dust on its leading face, and the resulting heating makes the contrast worse.",
    anchor="~10x brightness difference", anchor_spoken="about ten times in brightness",
    mechanism="Tidally locked, its leading hemisphere collects dark dust, then warms and loses its ice.",
    consequence="A runaway feedback can paint a whole world.",
    source="NASA Cassini observations of Iapetus, and the Phoebe dust ring",
    confidence="confirmed", saturation="low",
    sources=["Cassini mapped the two-tone surface of Iapetus in detail",
             "Dark material originates from outer moons, notably the Phoebe ring discovered by Spitzer in 2009",
             "Thermal runaway: the darkened leading face absorbs more sunlight, sublimates its ice, and darkens further"],
    beats={
        "hook": "One moon of Saturn is black on one side.",
        "turn": "Iapetus is a moon of Saturn, and its two halves differ by about ten times in brightness. One face is snow bright, the other closer to coal.",
        "mechanism": "Iapetus always keeps the same face forward as it orbits. That leading face sweeps up dark dust shed by another moon much further out, and Cassini mapped the result.",
        "spike": "The darkened side then absorbs more sunlight, warms up, and loses its ice, which makes it darker still.",
        "loop": "You would call them two separate worlds if you ever saw the halves apart.",
    },
    visuals={
        "hook": [V("ai", None, "Iapetus with one hemisphere bright white and the other near black, Saturn behind, vertical")],
        "turn": [V("stock", "fresh snow surface", "A field of clean fresh snow in bright light"),
                 V("stock", "lump of coal", "A lump of coal on a dark surface, close up"),
                 V("ai", None, "The stark dividing line running across the surface of Iapetus")],
        "mechanism": [V("ai", None, "Iapetus orbiting Saturn with the same face always pointing forward"),
                      V("ai", None, "A faint dust ring from an outer moon drifting inward across its path"),
                      V("ai", None, "The Cassini spacecraft passing over the two-tone surface, mapping it")],
        "spike": [V("ai", None, "The dark hemisphere absorbing sunlight and warming, ice sublimating away"),
                  V("ai", None, "The boundary between light and dark creeping further across the moon")],
        "loop": [V("ai", None, "The bright hemisphere alone in frame, looking like an ordinary icy moon"),
                 V("ai", None, "The dark hemisphere alone in frame, looking like a different world entirely")],
    })

add("tv_static",
    cluster="cosmology_and_origins", pattern="SECOND_PERSON_IMPLICATION", fmt="E", mood="uplifting",
    title="Old TV Static Was Partly the Big Bang",
    overlay="THE BIG BANG ON YOUR TV",
    hook_a="Old television static was partly the Big Bang.",
    hook_b="You turned off the oldest light there is",
    spine="A small fraction of analogue TV static was the cosmic microwave background.",
    anchor="~1% of static", anchor_spoken="about one percent",
    mechanism="Leftover heat from the early universe fills all space and registers as radio noise.",
    consequence="The origin of everything was on an unused channel.",
    source="Penzias and Wilson's detection of the cosmic microwave background, 1965",
    confidence="confirmed", saturation="medium",
    sources=["Penzias and Wilson detected the cosmic microwave background in 1965 while eliminating antenna noise",
             "A small percentage of analogue TV snow on a dead channel came from the CMB",
             "They famously cleaned pigeon droppings from the horn antenna before accepting the signal was real"],
    beats={
        "hook": "Old television static was partly the Big Bang.",
        "turn": "Tune an analogue set to a dead channel, and about one percent of that hiss arrived from the early universe.",
        "mechanism": "Space is filled with faint leftover heat from the moment it first turned transparent. Penzias and Wilson found it in nineteen sixty five while trying to hunt down noise in an antenna.",
        "spike": "They checked the antenna for pigeons first. The signal stayed.",
        "loop": "You were watching the oldest light there is, and you switched over to find something on.",
    },
    visuals={
        "hook": [V("ai", None, "An old CRT television hissing with static in a dark room, vertical composition")],
        "turn": [V("stock", "old tv static", "Close up of analogue television static filling a CRT screen"),
                 V("ai", None, "The static resolving into the mottled cosmic microwave background map")],
        "mechanism": [V("ai", None, "The early universe turning from opaque fog to transparent, light streaming free"),
                      V("ai", None, "A large horn antenna pointed at the sky in a nineteen sixties setting"),
                      V("ai", None, "Two researchers checking readouts beside the antenna, backs to camera")],
        "spike": [V("stock", "pigeon perched", "A pigeon perched on metal structure"),
                  V("ai", None, "The antenna cleaned out, the same faint hiss still showing on the readout")],
        "loop": [V("ai", None, "A hand turning an old television dial away from the static channel"),
                 V("ai", None, "The static fading out, the cosmic background map dissolving with it")],
    })

add("webb_cold",
    cluster="observation_and_instruments", pattern="NAKED_NUMBER", fmt="A", mood="dramatic",
    title="The Webb Telescope Must Never Warm Up",
    overlay="IT MUST NEVER WARM UP",
    hook_a="The Webb telescope must never be allowed to warm up.",
    hook_b="A telescope that would be blinded by its own heat",
    spine="Webb observes in infrared, so its own warmth would swamp the signal it is built to see.",
    anchor="-220 C", anchor_spoken="minus two hundred and twenty degrees",
    mechanism="An infrared telescope must run colder than the heat it is trying to detect.",
    consequence="Some instruments are defined by what they must avoid, not what they collect.",
    source="James Webb Space Telescope sunshield and operating temperature specifications",
    confidence="confirmed", saturation="medium",
    sources=["JWST operates below about -220 C, maintained by a five layer sunshield roughly the size of a tennis court",
             "The sunshield's Sun-facing side reaches roughly 85 C while the cold side stays near -233 C",
             "The sunshield deployment was single-attempt with no repair option at L2"],
    beats={
        "hook": "The Webb telescope must never be allowed to warm up.",
        "turn": "It sees in infrared, which is another word for heat. Its own warmth would blind it.",
        "mechanism": "So it runs below minus two hundred and twenty degrees, held there by a sunshield the size of a tennis court with five separate layers.",
        "spike": "One side of that shield sits near boiling point. The other stays colder than anywhere you could ever stand.",
        "loop": "There is no repair trip and no spare. Every image you have seen from it rests on a sunshade that had one chance to unfold.",
    },
    visuals={
        "hook": [V("ai", None, "Webb's gold hexagonal mirrors behind a vast sunshield, one side blazing and one frozen, vertical")],
        "turn": [V("ai", None, "An infrared view of a warm object glowing brightly against a cool background"),
                 V("ai", None, "A telescope's own structure glowing in infrared and washing out the view")],
        "mechanism": [V("ai", None, "The five layered sunshield fully deployed, layers separated in vacuum"),
                      V("stock", "tennis court overhead", "A tennis court seen from directly above"),
                      V("ai", None, "A temperature gauge plunging far below every marked value")],
        "spike": [V("ai", None, "The Sun-facing side of the sunshield blazing orange under direct light"),
                  V("ai", None, "The shaded side of the shield in deep frozen blue, mirrors behind it")],
        "loop": [V("ai", None, "The telescope alone at its distant station, far beyond any reach"),
                 V("ai", None, "The sunshield unfolding in deep space in a single tense sequence"),
                 V("ai", None, "A deep field of distant galaxies captured by the cold telescope")],
    })

add("red_dwarf",
    cluster="stellar_lifecycle", pattern="SCALE_COLLAPSE", fmt="C", mood="mysterious",
    title="No Red Dwarf Star Has Ever Died",
    overlay="NO RED DWARF HAS DIED",
    hook_a="Why has no red dwarf star ever died?",
    hook_b="The galaxy has not run long enough to kill one",
    spine="Red dwarfs burn so slowly that the universe is not old enough for any to have finished.",
    anchor="trillions of years", anchor_spoken="trillions of years",
    mechanism="Low mass and full convection make red dwarfs burn their fuel over trillions of years.",
    consequence="The universe is early, not late.",
    source="Stellar evolution models for low mass main sequence stars",
    confidence="confirmed", saturation="low",
    sources=["Stellar evolution models give red dwarfs main sequence lifetimes of trillions of years",
             "The universe is 13.8 billion years old, far short of that, so no red dwarf has yet left the main sequence",
             "Red dwarfs are the most numerous stellar type in the galaxy"],
    beats={
        "hook": "Why has no red dwarf star ever died?",
        "turn": "Red dwarfs are small, cool stars, and they are the commonest kind in our galaxy.",
        "mechanism": "They burn their fuel so slowly that models give them lifetimes of trillions of years. The universe has existed for only thirteen point eight billion.",
        "spike": "So every red dwarf ever formed is still burning. Not one has had the time to finish.",
        "loop": "You are alive in the era before any of them have aged. Every one you can see will outlast the question.",
    },
    visuals={
        "hook": [V("ai", None, "A tiny dim red star still burning steadily while galaxies age and drift around it, vertical")],
        "turn": [V("ai", None, "A red dwarf beside the Sun for scale, small and deep red"),
                 V("ai", None, "A star field where most points resolve into faint red dwarfs")],
        "mechanism": [V("ai", None, "A red dwarf's interior churning slowly, fuel consumed at a crawl"),
                      V("ai", None, "A fuel gauge barely moving off full across an enormous span of time"),
                      V("ai", None, "A timeline bar of trillions of years with the universe's age a sliver at one end")],
        "spike": [V("ai", None, "Countless red dwarfs across the galaxy all still lit, none extinguished"),
                  V("ai", None, "A graveyard of dead massive stars beside untouched red dwarfs")],
        "loop": [V("ai", None, "A vast stretch of future time unrolling with the red dwarfs still burning"),
                 V("ai", None, "A person looking up at a faint red star from a dark field, seen from behind")],
    })

add("triton",
    cluster="solar_system_oddities", pattern="TIMEBOMB", fmt="A", mood="dramatic",
    title="Neptune Is Slowly Pulling Its Main Moon Apart",
    overlay="TRITON IS FALLING IN",
    hook_a="Neptune is slowly pulling its main moon apart.",
    hook_b="A captured moon spiralling to its destruction",
    spine="Triton's retrograde orbit causes tidal decay, so it is spiralling inward toward destruction.",
    anchor="~3.6 billion years", anchor_spoken="a few billion years",
    mechanism="A retrograde orbit loses energy to tides rather than gaining it, so the orbit decays.",
    consequence="Moons are not permanent fixtures.",
    source="Voyager 2 flyby of Neptune, 1989, and tidal decay models",
    confidence="confirmed", saturation="low",
    sources=["Triton orbits Neptune retrograde, indicating capture rather than co-formation",
             "Voyager 2 flew past Neptune and Triton in 1989",
             "Tidal decay of a retrograde orbit leads to eventual breakup inside the Roche limit, on a timescale of billions of years"],
    beats={
        "hook": "Neptune is slowly pulling its main moon apart.",
        "turn": "Triton is a large moon of Neptune, and it orbits backwards. That means it was captured, not formed alongside the planet.",
        "mechanism": "A backwards orbit bleeds energy into tides instead of gaining it. Voyager Two flew past in nineteen eighty nine and measured the setup. Triton is spiralling inward.",
        "spike": "In a few billion years it will pass too close and be torn into a ring, the way Saturn's rings may have formed.",
        "loop": "Neptune is the plain one you always skip past. It is quietly eating a moon while you do.",
    },
    visuals={
        "hook": [V("ai", None, "Triton spiralling backwards toward a looming blue Neptune, vertical, cinematic")],
        "turn": [V("ai", None, "Triton's orbit traced in the opposite direction to Neptune's rotation"),
                 V("ai", None, "Triton drifting in from the outer solar system and being captured")],
        "mechanism": [V("ai", None, "Tidal bulges raised on Neptune dragging against Triton's backwards motion"),
                      V("ai", None, "Voyager 2 passing Neptune's blue crescent in near darkness"),
                      V("ai", None, "Triton's orbit visibly tightening over a long time lapse")],
        "spike": [V("ai", None, "Triton breaking apart under tidal stress into a stream of debris"),
                  V("ai", None, "The debris spreading into a bright new ring around Neptune")],
        "loop": [V("ai", None, "Neptune as a plain featureless blue disc, easy to overlook"),
                 V("ai", None, "The same Neptune with Triton slowly closing in, unnoticed")],
    })


add("white_sun",
    cluster="things_we_got_wrong", pattern="WRONG_NAME", fmt="B", mood="energetic",
    title="The Sun Is Actually White, Not Yellow",
    overlay="THE SUN ISN'T YELLOW",
    hook_a="The Sun is not yellow. It is white.",
    hook_b="The sky is made of the Sun's missing colour",
    spine="Sunlight is essentially white; the atmosphere removes blue from the direct beam and spreads it across the sky.",
    anchor="5,500 C surface", anchor_spoken="five thousand five hundred degrees",
    mechanism="Rayleigh scattering removes short wavelengths from the direct beam and redistributes them across the sky.",
    consequence="The colour of the sky and the colour of the Sun are the same fact.",
    source="Solar spectrum and atmospheric scattering; confirmed by observation above the atmosphere",
    confidence="confirmed", saturation="medium",
    sources=["Solar photosphere temperature about 5,500 C, giving a near-white emitted spectrum",
             "Rayleigh scattering preferentially removes short (blue) wavelengths from the direct beam",
             "Observed directly from orbit, where the Sun appears white"],
    beats={
        "hook": "The Sun is not yellow. It is white.",
        "turn": "Every drawing you made of it as a child got the colour wrong, and so does nearly every photograph.",
        "mechanism": "The Sun's surface sits near five thousand five hundred degrees, and the light leaving it comes out essentially white. Our atmosphere then scatters the short blue wavelengths across the whole sky, so what reaches your eye directly has had that blue taken out of it.",
        "spike": "That scattered blue is the sky. The sky is made of the Sun's missing colour.",
        "loop": "Astronauts above the air see a plain white Sun. Yours looks yellow only because you are standing under an ocean of gas.",
    },
    visuals={
        "hook": [V("ai", None, "Split frame: a pure white Sun seen from space beside a yellow Sun seen through atmosphere, vertical")],
        "turn": [V("stock", "child crayon drawing", "A child's crayon drawing of a yellow sun on paper"),
                 V("ai", None, "A gallery of photographs all rendering the Sun warm yellow or orange")],
        "mechanism": [V("ai", None, "The Sun's churning white photosphere in close detail"),
                      V("ai", None, "A temperature readout beside the surface, thousands of degrees"),
                      V("ai", None, "A white light beam entering the atmosphere and its blue component scattering away"),
                      V("ai", None, "Blue light spreading across the whole dome of the sky while the beam warms")],
        "spike": [V("ai", None, "A clear blue sky rendered as scattered light filling the whole dome"),
                  V("ai", None, "The blue draining out of the sky and back into a white Sun")],
        "loop": [V("ai", None, "An astronaut's view from orbit with a stark white Sun against black"),
                 V("ai", None, "The same Sun seen from the ground, warm yellow through thick air")],
    })

add("laika",
    cluster="human_spaceflight", pattern="MISSING_THING", fmt="A", mood="dramatic",
    title="The Dog Sent to Orbit Who Never Came Home",
    overlay="SHE NEVER CAME HOME",
    hook_a="A stray dog reached orbit and never came home.",
    hook_b="The capsule was built with no way back",
    spine="Laika orbited Earth in 1957 in a capsule with no return capability, and died within hours.",
    anchor="1957", anchor_spoken="nineteen fifty seven",
    mechanism="Sputnik 2 had no re-entry system; later records showed she died of overheating within hours.",
    consequence="Crewed spaceflight safety practice was built on this.",
    source="Sputnik 2, 1957, and Russian records released in 2002",
    confidence="confirmed", saturation="medium",
    sources=["Sputnik 2 launched November 1957 carrying Laika, with no return capability designed",
             "Records made public in 2002 established death from overheating within hours, not the days originally reported",
             "Oleg Gazenko, one of the scientists involved, said in 1998 that the mission had not taught them enough to justify it"],
    beats={
        "hook": "A stray dog reached orbit and never came home.",
        "turn": "Her name was Laika. Soviet engineers took her from the streets of Moscow, and the capsule was built with no way to bring her back.",
        "mechanism": "Sputnik Two launched in nineteen fifty seven. For decades the official account said she lasted days. Records released in two thousand two showed she died within hours, from heat.",
        "spike": "One of the scientists involved said, years afterwards, that they had not learned enough from it to justify what they did.",
        "loop": "You know her name because she did not come back. Every crewed flight you have watched since was built around making sure that does not happen again.",
    },
    visuals={
        "hook": [V("ai", None, "A small dog's face at a capsule window with Earth curving below, vertical, sombre")],
        "turn": [V("ai", None, "A stray dog on a snowy Moscow street in the nineteen fifties"),
                 V("ai", None, "The dog being fitted into a small harness inside a cramped capsule"),
                 V("ai", None, "Engineers sealing that capsule, no hatch mechanism for return")],
        "mechanism": [V("ai", None, "A period rocket lifting off at night, nineteen fifties Soviet launch site"),
                      V("ai", None, "The capsule in orbit above a dark Earth, interior temperature rising"),
                      V("ai", None, "An archive folder being opened decades later, papers revealed")],
        "spike": [V("ai", None, "An elderly scientist sitting quietly in an office, seen from behind, no face"),
                  V("ai", None, "An old mission photograph on a desk, the room otherwise empty")],
        "loop": [V("ai", None, "A memorial statue of a small dog atop a rocket, simple and still"),
                 V("ai", None, "A modern crew capsule descending safely under full parachutes"),
                 V("ai", None, "A recovery team reaching the capsule, crew brought out unharmed")],
    })

add("seven_worlds",
    cluster="exoplanets", pattern="NAKED_NUMBER", fmt="D", mood="mysterious",
    title="Seven Earth-Sized Worlds Orbit One Tiny Star",
    overlay="SEVEN EARTHS, ONE STAR",
    hook_a="Seven Earth-sized worlds orbit one tiny star.",
    hook_b="Neighbour planets that hang huge in the sky",
    spine="A single red dwarf hosts seven rocky planets packed inside Mercury's orbital distance.",
    anchor="40 light years", anchor_spoken="forty light years",
    mechanism="Repeated transit dips revealed seven rocky planets in tightly packed orbits.",
    consequence="Compact planetary systems around small stars may be common.",
    source="Spitzer and ground-based transit observations of the TRAPPIST-1 system",
    confidence="confirmed", saturation="medium",
    sources=["Seven Earth-sized planets confirmed around TRAPPIST-1, about 40 light years away",
             "Spitzer transit photometry established the seven planet count; three lie in the temperate zone",
             "All seven orbit closer to their star than Mercury does to the Sun, so neighbours appear large in each other's skies",
             "The catalogue name is not spoken: it contains a digit, and it means nothing to the audience."],
    beats={
        "hook": "Seven Earth-sized worlds orbit one tiny star.",
        "turn": "Count them. Seven rocky planets, all of them packed closer in than Mercury sits to our Sun.",
        "mechanism": "The star is a red dwarf, small and cool, about forty light years away. Spitzer tracked the tiny dips in its light as each planet crossed in front. Three of the seven sit in the temperate zone.",
        "spike": "They orbit so close together that from the surface of one, its neighbours would hang larger than our Moon does.",
        "loop": "You could watch another world drift overhead, close enough that you might pick out weather on it.",
    },
    visuals={
        "hook": [V("ai", None, "Seven rocky planets in tight orbits around a small dim red star, vertical")],
        "turn": [V("ai", None, "The seven orbits drawn nested inside Mercury's orbit for scale"),
                 V("ai", None, "Each of the seven planets shown in a row, comparable in size to Earth")],
        "mechanism": [V("ai", None, "A small red dwarf star burning dimly against deep space"),
                      V("ai", None, "The Spitzer telescope in orbit watching a faint distant star"),
                      V("ai", None, "A light curve dipping repeatedly as each planet transits the star"),
                      V("ai", None, "Three of the seven planets highlighted in a temperate band")],
        "spike": [V("ai", None, "Standing on a rocky surface with sibling planets hanging huge in the sky"),
                  V("ai", None, "Our Moon shown small beside one of those enormous neighbour worlds")],
        "loop": [V("ai", None, "A neighbouring planet drifting slowly overhead, filling much of the sky"),
                 V("ai", None, "Close on that world's surface, cloud bands and weather visible from across space")],
    })

add("barycentre",
    cluster="solar_system_oddities", pattern="INVERTED_ASSUMPTION", fmt="B", mood="mysterious",
    title="Jupiter Does Not Actually Orbit the Sun",
    overlay="JUPITER MISSES THE SUN",
    hook_a="Jupiter does not actually orbit the Sun.",
    hook_b="Both of them circle an empty point in space",
    spine="The Sun-Jupiter centre of mass lies outside the Sun's surface, so both bodies orbit a point in space.",
    anchor="1.07 solar radii", anchor_spoken="just outside the Sun's surface",
    mechanism="Jupiter is massive enough to push the shared centre of mass beyond the Sun's radius.",
    consequence="This same wobble is how planets around other stars are found.",
    source="Orbital mechanics of the Sun-Jupiter barycentre",
    confidence="confirmed", saturation="low",
    sources=["The Sun-Jupiter barycentre sits at about 1.07 solar radii from the Sun's centre, just outside the photosphere",
             "For every other planet the barycentre lies inside the Sun",
             "The radial velocity method for detecting exoplanets measures exactly this stellar wobble"],
    beats={
        "hook": "Jupiter does not actually orbit the Sun.",
        "turn": "Two bodies both circle their shared centre of mass. For every other planet, that point sits deep inside the Sun.",
        "mechanism": "Jupiter is heavy enough to drag it out. Their balance point sits just outside the Sun's surface, in open space.",
        "spike": "So the Sun is not standing still with Jupiter going round it. Both of them swing around an empty spot, like two skaters spinning while holding hands.",
        "loop": "That same wobble is how you find planets around other stars. You watch the star move, never the planet.",
    },
    visuals={
        "hook": [V("ai", None, "The Sun visibly wobbling around an empty point in space with Jupiter opposite it, vertical")],
        "turn": [V("ai", None, "A balance point marked deep inside the Sun for a small inner planet"),
                 V("ai", None, "The Sun and a small planet circling that internal point, the Sun barely moving")],
        "mechanism": [V("ai", None, "The balance point sliding outward past the Sun's surface as Jupiter's mass is added"),
                      V("ai", None, "An empty marked point just above the Sun's boiling surface")],
        "spike": [V("ai", None, "The Sun clearly moving rather than sitting fixed at the centre"),
                  V("ai", None, "Sun and Jupiter both circling a marked empty point, neither one stationary"),
                  V("stock", "figure skaters spinning", "Two figure skaters spinning together holding hands")],
        "loop": [V("ai", None, "A distant star wobbling slightly against a fixed background of stars"),
                 V("ai", None, "A radial velocity trace oscillating up and down on a readout")],
    })

add("you_are_moving",
    cluster="physics_limits", pattern="SECOND_PERSON_IMPLICATION", fmt="E", mood="energetic",
    title="You Are Moving at Six Hundred Kilometres Per Second",
    overlay="YOU ARE NOT SITTING STILL",
    hook_a="You are moving six hundred kilometres every second.",
    hook_b="You have never once been at rest",
    spine="Measured against the cosmic microwave background, the Local Group moves at about 630 km/s.",
    anchor="630 km/s", anchor_spoken="six hundred and thirty kilometres a second",
    mechanism="The dipole in the cosmic microwave background reveals our motion relative to it.",
    consequence="There is no state of rest to return to.",
    source="Cosmic microwave background dipole measured by COBE and Planck",
    confidence="confirmed", saturation="medium",
    sources=["CMB dipole gives the Local Group a velocity of roughly 630 km/s relative to the background",
             "COBE and later Planck mapped the dipole precisely",
             "At 630 km/s, two seconds of reading covers about 1,260 km"],
    beats={
        "hook": "You are moving six hundred kilometres every second.",
        "turn": "Sitting still is a local illusion. The Earth spins, it orbits the Sun, it rides around the galaxy, and the galaxy is falling somewhere too.",
        "mechanism": "Measured against the leftover glow of the Big Bang, our whole local group of galaxies is moving at six hundred and thirty kilometres a second. Planck mapped that lopsidedness precisely.",
        "spike": "In the time it took to read that sentence, you crossed more than a thousand kilometres.",
        "loop": "There is nothing you can brace against out here. You have never once been at rest.",
    },
    visuals={
        "hook": [V("ai", None, "A completely still human figure with the galaxy streaking past in motion blur, vertical")],
        "turn": [V("ai", None, "Earth spinning, then pulling back to show it orbiting the Sun"),
                 V("ai", None, "The solar system sweeping around the galactic centre in a long arc"),
                 V("ai", None, "The whole galaxy falling through space toward a distant mass")],
        "mechanism": [V("ai", None, "The cosmic microwave background map with one side subtly warmer than the other"),
                      V("ai", None, "A velocity arrow drawn from our local group of galaxies toward the warm side"),
                      V("ai", None, "The Planck spacecraft scanning the whole sky in slow sweeps")],
        "spike": [V("stock", "reading text screen", "Eyes scanning a line of text on a screen, close up"),
                  V("ai", None, "A distance counter racing upward past a thousand kilometres in seconds")],
        "loop": [V("ai", None, "A person sitting perfectly still while everything around them streaks past"),
                 V("ai", None, "Pull back from that figure through Earth, galaxy, and the wider cosmos")],
    })

add("rogue_planets",
    cluster="exoplanets", pattern="MISSING_THING", fmt="A", mood="mysterious",
    title="Most Planets May Have No Sun at All",
    overlay="PLANETS WITH NO SUN",
    hook_a="Most planets may have no sun at all.",
    hook_b="Worlds drifting forever between the stars",
    spine="Free-floating planets, ejected during system formation, may outnumber stars in the galaxy.",
    anchor="billions of rogue worlds", anchor_spoken="billions of them",
    mechanism="Gravitational microlensing surveys detect free-floating planets by their brief lensing of background stars.",
    consequence="The default state of a planet may be starless.",
    source="Gravitational microlensing surveys of free-floating planets",
    confidence="hypothesis", saturation="low",
    sources=["Microlensing surveys detect free-floating planets via brief brightening of background stars",
             "Population estimates run to billions in the galaxy, but remain a leading estimate rather than a settled count - the script says so",
             "Subsurface oceans on rogue worlds are a modelled possibility, phrased as 'may' in the script"],
    beats={
        "hook": "Most planets may have no sun at all.",
        "turn": "Worlds can be flung out of their systems while those systems are still forming. Once loose, they drift between the stars forever.",
        "mechanism": "Surveys catch them by the way their gravity briefly bends the light of a star behind them. The counts point to billions of them in our galaxy. This is the leading estimate, not a settled one.",
        "spike": "A rogue world has no sunrise and no seasons. Some may still hold liquid water beneath ice, warmed from within.",
        "loop": "For every star you can see up there, there may be a starless world you never will.",
    },
    visuals={
        "hook": [V("ai", None, "A dark rogue world drifting through starless black, faintly lit at its edge, vertical")],
        "turn": [V("ai", None, "A young chaotic planetary system flinging a planet outward on a slingshot path"),
                 V("ai", None, "The ejected planet receding into total darkness, its star shrinking away")],
        "mechanism": [V("ai", None, "A background star briefly brightening as an unseen mass passes in front"),
                      V("ai", None, "A light curve spiking once and returning to flat"),
                      V("ai", None, "A galaxy map dotted with faint unlit worlds between the stars")],
        "spike": [V("ai", None, "A frozen rogue planet surface in permanent night, no sun on any horizon"),
                  V("ai", None, "Cutaway showing a liquid ocean beneath a thick ice shell, warmed from below")],
        "loop": [V("ai", None, "A bright star field, every visible point a star with planets around it"),
                 V("ai", None, "The dark gaps between them slowly revealing hidden unlit drifting worlds")],
    })

add("taller",
    cluster="human_spaceflight", pattern="SECOND_PERSON_IMPLICATION", fmt="E", mood="energetic",
    title="Astronauts Come Home Two Inches Taller",
    overlay="SPACE MAKES YOU TALLER",
    hook_a="Astronauts come home taller than they left.",
    hook_b="Your height is just how hard the floor pushes back",
    spine="Without gravity compressing the spine, the discs expand and astronauts gain measurable height.",
    anchor="5 cm", anchor_spoken="five centimetres",
    mechanism="Spinal discs decompress in microgravity, lengthening the spine measurably.",
    consequence="Body dimensions are a response to load, not a constant.",
    source="NASA crew height measurements in orbit",
    confidence="confirmed", saturation="low",
    sources=["NASA has measured crew height gains of up to about 5 cm (2 inches) in microgravity",
             "The gain reverses within months of return as the discs recompress",
             "The same mechanism produces the everyday diurnal height variation on Earth"],
    beats={
        "hook": "Astronauts come home taller than they left.",
        "turn": "Your spine is a stack of bones with soft cushions between them. Gravity presses that stack down all day long.",
        "mechanism": "Take the weight off and the cushions swell back out. NASA has measured crew members gaining up to five centimetres in orbit.",
        "spike": "You do a smaller version of this nightly. You are measurably taller waking up than you were going to bed.",
        "loop": "Your height is not a fixed number. It is just how hard the floor is pushing back.",
    },
    visuals={
        "hook": [V("ai", None, "An astronaut floating with spine visibly lengthened against a height chart, vertical")],
        "turn": [V("ai", None, "A cutaway of the human spine showing discs between the vertebrae"),
                 V("ai", None, "Gravity arrows compressing that stack of discs downward through a day")],
        "mechanism": [V("ai", None, "The same discs expanding as the compressing load is removed"),
                      V("ai", None, "A crew member being measured against a marked wall inside a space station")],
        "spike": [V("stock", "person waking up bed", "A person waking and sitting up on the edge of a bed"),
                  V("ai", None, "A height chart showing a small morning to evening difference")],
        "loop": [V("ai", None, "A figure standing on a floor with force arrows pressing up through their feet"),
                 V("ai", None, "The same figure floating free, taller, with no floor beneath them")],
    })


def build_shots(beats, visuals):
    """Splits each beat's exact words across that beat's planned visuals.
    Reconstruction is exact by construction, so the render pipeline's
    narration/shot sync cannot drift from what was written."""
    shots = []
    for name in gs.BEAT_ORDER:
        words = beats[name].split()
        plan = visuals[name]
        size = -(-len(words) // len(plan))  # ceil
        chunks = [" ".join(words[i:i + size]) for i in range(0, len(words), size)]
        for (media_type, stock_query, visual_prompt), chunk in zip(plan, chunks):
            shot = {
                "index": len(shots),
                "beat": name,
                "narration_segment": chunk,
                "media_type": media_type,
                "visual_prompt": visual_prompt,
            }
            if media_type == "stock":
                shot["stock_query"] = stock_query
            shots.append(shot)
    return shots


def refresh_queued(config, bank_by_title, items):
    """Rewrites still-queued entries whose script was edited since ingest.

    Correcting a script and re-running the batch file is routine, so a second
    run updates the queue rather than leaving the stale version to publish.
    Only entries still in 'queued' status are touched: anything popped or
    published is history and stays exactly as it shipped.
    """
    from src import gen_scripts, queue as q

    queue = q.load_queue()
    by_id = {e["id"]: e for e in queue["entries"]}
    changed = 0
    for item in items:
        concept = bank_by_title[item["title"]]
        entry = by_id.get(concept["id"])
        if entry is None or entry.get("status") != "queued":
            continue
        item = dict(item, id=concept["id"])
        rebuilt = gen_scripts.templatize(concept, item, config)
        if rebuilt["shot_list"] == entry["shot_list"] and rebuilt["script"] == entry["script"]:
            continue
        # Keep the queue's own bookkeeping; replace only the content.
        rebuilt.update({k: entry[k] for k in ("status", "video_id", "queued_at", "published_at")})
        entry.clear()
        entry.update(rebuilt)
        changed += 1
    if changed:
        q.save_queue(queue)
    print(f"[batch] Refreshed {changed} already-queued entr{'y' if changed == 1 else 'ies'}.")


def ingest(concepts, items):
    """Concepts first (the bank assigns the real ids), then scripts keyed to
    those ids. Doing it in one process removes the hand-remapping step that
    sat between the two files - the only place in this flow where a human
    could silently pair a script with the wrong concept."""
    from src import config as cfg
    from src import gen_ideas, gen_scripts

    # Re-running a batch file after correcting one script is normal, so titles
    # already in the bank are skipped rather than queued a second time. Title
    # is the key because ids do not exist until the bank assigns them.
    bank = gen_ideas.load_idea_bank()
    already = {c["title"]: c for c in bank}
    fresh_titles = {c["title"] for c in concepts} - set(already)

    revised = [i for i in items if i["title"] in already]
    if revised:
        refresh_queued(cfg.load_config(), already, revised)

    concepts = [c for c in concepts if c["title"] in fresh_titles]
    items = [i for i in items if i["title"] in fresh_titles]
    if not concepts:
        print("[batch] No new concepts to add.")
        return

    saved = gen_ideas.finalize_and_save(concepts, pre_approved=True)
    if len(saved) != len(concepts):
        raise SystemExit(f"bank saved {len(saved)} of {len(concepts)} concepts - not ingesting scripts")
    by_title = {c["title"]: c["id"] for c in saved}

    tmp = Path("output/drafts/_ingest.json")
    for it in items:
        it["id"] = by_title[it["title"]]
    tmp.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    gen_scripts.ingest_file(cfg.load_config(), str(tmp))


def main():
    concepts, items, failures = [], [], []
    prev = gs.last_format_used()
    print(f"rotation continues from: {prev}\n")

    for key in ORDER:
        d = B[key]
        script = gs.reconstruct_beats(d["beats"])
        shots = build_shots(d["beats"], d["visuals"])
        # The id is a placeholder: append_idea_bank() assigns the real one at
        # ingest. remap_ids.py writes it back into the scripts file.
        concept = {
            "id": key, "title": d["title"], "hook_a": d["hook_a"], "hook_b": d["hook_b"],
            "hook": d["hook_a"], "spine": d["spine"], "anchor": d["anchor"],
            "anchor_spoken": d["anchor_spoken"], "mechanism": d["mechanism"],
            "consequence": d["consequence"], "cluster": d["cluster"], "pattern": d["pattern"],
            "source": d["source"], "confidence": d["confidence"], "saturation": d["saturation"],
        }
        item = {
            "id": key, "script": script, "beats": d["beats"],
            "format_letter": d["fmt"], "hook_overlay": d["overlay"], "mood": d["mood"],
            "title": d["title"], "sources": d["sources"], "shot_list": shots,
            "word_count": len(script.split()), "pattern_used": d["pattern"],
        }
        try:
            gs.validate_script(concept, item, prev_format=prev)
        except ValueError as e:
            failures.append((key, str(e)))
            print(f"FAIL {key:<13} {e}")
            prev = d["fmt"]
            continue
        warnings = gs.check_traps(script)
        # style.md: the frame changes every two to four seconds. A beat with
        # too few planned visuals for its length leaves one image on screen
        # far too long, which reads as a slideshow however good the image is.
        slow = [f"{s['beat']} {s['word_count'] / gs.WORDS_PER_SECOND:.1f}s"
                for s in shots if s["word_count"] / gs.WORDS_PER_SECOND > MAX_SHOT_SECONDS]
        if slow:
            failures.append((key, f"shots over {MAX_SHOT_SECONDS}s: {', '.join(slow)}"))
            print(f"FAIL {key:<13} needs more visuals: {', '.join(slow)}")
            prev = d["fmt"]
            continue
        print(f"PASS {key:<13} {d['fmt']} {gs.estimated_seconds(script):>4.0f}s "
              f"{len(shots):>2} shots {len(script.split()):>3}w"
              + (f"\n       WARN: {'; '.join(warnings)}" if warnings else ""))
        concepts.append(concept)
        items.append(item)
        prev = d["fmt"]

    print(f"\n{len(items)}/{len(ORDER)} passed, {len(failures)} failed")
    if failures:
        sys.exit(1)

    out = Path("output/drafts")
    with open(out / "concepts_batch1.jsonl", "w", encoding="utf-8") as f:
        for c in concepts:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(out / "scripts_batch1.json", "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"wrote {out}/concepts_batch1.jsonl and {out}/scripts_batch1.json")

    if "--ingest" in sys.argv:
        print()
        ingest(concepts, items)
    else:
        print("(dry: pass --ingest to load these into the idea bank and queue)")


if __name__ == "__main__":
    main()
