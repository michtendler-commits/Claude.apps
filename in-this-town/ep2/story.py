# "In This Town: The Jump" - script data shared by the audio builder and the Blender scene.
# who: narrator | mayor | jax | dave | linda | crowd
# say: what the voice actually says (defaults to text). text: caption.
# sfx: list of (sound, offset_seconds_from_line_start) ; negative offset = from line end.

VOICES = {
    "narrator": ("am_michael", 0.88),
    "mayor": ("bm_george", 0.92),
    "jax": ("am_puck", 1.05),
    "dave": ("am_adam", 0.95),
    "linda": ("af_bella", 1.0),
}
CROWD = [("af_nicole", 1.0), ("am_eric", 1.0), ("bf_emma", 1.0), ("am_adam", 1.0), ("af_bella", 1.0)]

NAMES = {"narrator": "", "mayor": "MAYOR GERALD", "jax": "JAXON", "dave": "DAVE", "linda": "LINDA", "crowd": "EVERYONE"}

LINES = [
    # --- Act 1: the law ---
    dict(id="n1", who="narrator", text="In this town... nobody jumps.", gap=0.6),
    dict(id="n2", who="narrator", text="Not on trampolines. Not over puddles. Not even on your birthday.", gap=0.8),
    dict(id="m1", who="mayor", text="Citizens of Geraldville!", gap=0.4),
    dict(id="m2", who="mayor", text="Jumping is chaos. Jumping is disrespectful to the ground. And the ground has done NOTHING wrong.",
         say="Jumping is chaos. Jumping is disrespectful to the ground. And the ground has done nothing wrong!", gap=0.5),
    dict(id="m3", who="mayor", text="Anyone caught jumping will be sent... to the Shadow Realm.", gap=0.6, sfx=[("sting", -0.3)]),
    dict(id="d1", who="dave", text="...the Shadow Realm is just Ohio.", gap=0.4),
    dict(id="m4", who="mayor", text="SILENCE, Dave.", say="Silence, Dave.", gap=0.9),
    dict(id="n3", who="narrator", text="For forty years, nobody jumped. The town was peaceful. Quiet. Extremely... flat.", gap=0.7),
    dict(id="n4", who="narrator", text="Until one day... a new kid moved in.", gap=0.5),
    # --- Act 2: the kid ---
    dict(id="j1", who="jax", text="Hi! I'm Jaxon! What's up, everybody?", gap=0.5, sfx=[("scratch", -0.1)]),
    dict(id="l1", who="linda", text="Sweetie... we don't say \"up\" here.", say="Sweetie... we don't say, up, here.", gap=0.5),
    dict(id="j2", who="jax", text="O-kay...", say="Ohh... kay.", gap=0.6),
    dict(id="d2", who="dave", text="Kid. That's a puddle. Walk around it. Slowly.", gap=0.4),
    dict(id="j3", who="jax", text="Why? I can just...", gap=1.4, sfx=[("boing", -0.1)]),
    dict(id="c1", who="crowd", text="*GASP*", say="Ohhh!", gap=0.3),
    dict(id="l2", who="linda", text="He... he JUMPED!", say="He... he jumped!", gap=0.3, sfx=[("thunk", -0.2)]),
    dict(id="d3", who="dave", text="The bread knows. The bread KNOWS.", say="The bread knows. The bread knows!", gap=0.4, sfx=[("siren", -0.1)]),
    # --- Act 3: the mayor ---
    dict(id="m5", who="mayor", text="WHO. JUMPED.", say="Who. Jumped.", gap=0.4),
    dict(id="j4", who="jax", text="Me? It was literally just a puddle.", gap=0.4),
    dict(id="m6", who="mayor", text="Young man, do you know what you've done?", gap=0.3),
    dict(id="j5", who="jax", text="Moved my legs... upward?", gap=0.3),
    dict(id="m7", who="mayor", text="We do NOT say that word here!", say="We do not say that word here!", gap=0.3),
    dict(id="j6", who="jax", text="What, legs?", gap=0.6),
    dict(id="m8", who="mayor", text="...the other one.", gap=0.8),
    dict(id="j7", who="jax", text="Okay, but WHY can't anyone jump?", say="Okay, but why can't anyone jump?", gap=0.6),
    dict(id="m9", who="mayor", text="Because... forty years ago... I tried to jump.", gap=0.5),
    dict(id="m10", who="mayor", text="And I couldn't. My hat... was too heavy.", gap=0.6),
    dict(id="m11", who="mayor", text="So I banned it. For everyone. Forever.", gap=0.8),
    dict(id="j8", who="jax", text="That is the dumbest thing I have ever heard.", gap=0.5),
    dict(id="j9", who="jax", text="Watch.", gap=1.3, sfx=[("boing", 0.6)]),
    # --- Act 4: the town jumps ---
    dict(id="d4", who="dave", text="...I mean... it DOES look kind of fun.", say="I mean... it does look kind of fun.", gap=1.2, sfx=[("boing", -0.1)]),
    dict(id="l3", who="linda", text="Oh, what the heck!", gap=1.2, sfx=[("boing", 0.2)]),
    dict(id="n5", who="narrator", text="And one by one... the town remembered how to jump.", gap=3.0,
         sfx=[("music", 0.0), ("boing", 0.6), ("boing", 1.4), ("boing", 2.1), ("boing", 3.0)]),
    dict(id="m12", who="mayor", text="No! NO! Stop that! I am the MAYOR!", say="No! No! Stop that! I am the mayor!", gap=0.6, sfx=[("scratch", 0.0), ("musicstop", 0.0)]),
    dict(id="m13", who="mayor", text="...fine. FINE. Without the hat, then.", say="Fine. Fine! Without the hat, then.", gap=0.5),
    dict(id="sfx1", who="none", text="", dur=2.6, sfx=[("bigboing", 0.3), ("whoosh", 0.5)], gap=0.3),
    dict(id="n6", who="narrator", text="Mayor Gerald was never seen again.", gap=0.6),
    dict(id="n7", who="narrator", text="Some say he's still going up.", gap=0.9),
    # --- Ending ---
    dict(id="j10", who="jax", text="New law, everybody.", gap=0.5),
    dict(id="j11", who="jax", text="In this town... NO HATS.", say="In this town... no hats.", gap=0.3),
    dict(id="c2", who="crowd", text="YAAAY!", say="Yaaay!", gap=4.5, sfx=[("music", 0.0), ("boing", 0.2), ("boing", 0.5), ("boing", 0.8)]),
]
