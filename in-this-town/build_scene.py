# Builds the "In This Town" raccoon mayor scene and animation.
# Run: blender -b -P build_scene.py -- [engine] [res_percent]
import bpy, json, math, os, sys, random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENGINE = argv[0] if len(argv) > 0 else "CYCLES"
RES_PCT = int(argv[1]) if len(argv) > 1 else 100

T = json.load(open(os.path.join(HERE, "timing.json")))
FPS = 24
ENV = T["env"]
END = int(T["dur"] * FPS)

CAPTIONS = [
    "IN THIS TOWN...\nwe don't say good morning.\nWe whisper: THE BREAD KNOWS.",
    "IN THIS TOWN,\nstairs are optional.\nYou WILL be judged for using them.",
    "IN THIS TOWN,\nwe don't have a Walmart.\nWe have GERALD.\nDon't ask Gerald how.",
    "IN THIS TOWN,\nTUESDAY IS CANCELED.",
    "Microwave fish in the break room?\nYou simply...\ndon't come back.",
]

# ---------- reset ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, END
scn.render.resolution_x, scn.render.resolution_y = 1080, 1920
scn.render.resolution_percentage = RES_PCT
random.seed(7)


# ---------- helpers ----------
def mat(name, color, rough=0.6, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def setmat(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def sphere(name, loc, scale, m, parent=None, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    smooth(setmat(o, m))
    if parent:
        par(o, parent)
    return o


def cyl(name, loc, r, depth, m, rot=(0, 0, 0), parent=None, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    smooth(setmat(o, m))
    if parent:
        par(o, parent)
    return o


def cube(name, loc, scale, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    return setmat(o, m)


def cone(name, loc, r1, depth, m, rot=(0, 0, 0), verts=32, parent=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    smooth(setmat(o, m))
    if parent:
        par(o, parent)
    return o


def par(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw


def text(name, body, loc, size, m, rot=(math.radians(90), 0, 0), extrude=0.02, align="CENTER"):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.body = body
    o.data.size = size
    o.data.extrude = extrude
    o.data.align_x = align
    o.data.align_y = "CENTER"
    return setmat(o, m)


# ---------- materials ----------
M = {
    "fur": mat("fur", (0.32, 0.31, 0.33), 0.9),
    "fur_dark": mat("fur_dark", (0.05, 0.05, 0.06), 0.9),
    "fur_light": mat("fur_light", (0.85, 0.84, 0.82), 0.9),
    "eye": mat("eye", (0.97, 0.97, 0.97), 0.2),
    "pupil": mat("pupil", (0.01, 0.01, 0.01), 0.05),
    "nose": mat("nose", (0.02, 0.02, 0.02), 0.15),
    "mouth": mat("mouth", (0.25, 0.02, 0.04), 0.5),
    "hat": mat("hat", (0.02, 0.02, 0.025), 0.35),
    "band": mat("band", (0.7, 0.05, 0.05), 0.4),
    "sash": mat("sash", (0.75, 0.05, 0.08), 0.5),
    "gold": mat("gold", (1.0, 0.7, 0.15), 0.25),
    "wood": mat("wood", (0.35, 0.18, 0.07), 0.7),
    "grass": mat("grass", (0.18, 0.45, 0.12), 0.9),
    "road": mat("road", (0.12, 0.12, 0.13), 0.9),
    "white": mat("white", (0.95, 0.95, 0.95), 0.5),
    "sign": mat("sign", (0.08, 0.35, 0.15), 0.5),
    "cap": mat("cap", (1.0, 0.95, 0.2), 0.5, emit=1.5),
    "capw": mat("capw", (1.0, 1.0, 1.0), 0.5, emit=1.5),
    "banner": mat("banner", (0.0, 0.0, 0.0), 1.0),
    "window": mat("window", (1.0, 0.8, 0.4), 0.3, emit=3.0),
}
HOUSE_COLS = [(0.8, 0.3, 0.3), (0.3, 0.5, 0.8), (0.9, 0.75, 0.35), (0.55, 0.75, 0.5), (0.75, 0.5, 0.75), (0.9, 0.55, 0.3)]

# ---------- world / sky ----------
world = bpy.data.worlds.new("sky")
scn.world = world
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
grad = nt.nodes.new("ShaderNodeTexGradient")
coord = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB")
nt.links.new(coord.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].position = 0.02
ramp.color_ramp.elements[0].color = (1.0, 0.45, 0.2, 1)
ramp.color_ramp.elements[1].position = 0.3
ramp.color_ramp.elements[1].color = (0.25, 0.35, 0.8, 1)
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0

# ---------- ground / town ----------
g = cube("ground", (0, 10, -0.05), (40, 40, 0.05), M["grass"])
cube("road", (0, 6, 0.005), (40, 1.2, 0.01), M["road"])
for x in range(-20, 21, 3):
    cube(f"stripe{x}", (x, 6, 0.02), (0.6, 0.08, 0.01), M["white"])

for i, x in enumerate(range(-14, 15, 4)):
    y = 11 + random.uniform(-1, 1.5)
    h = random.uniform(1.8, 3.2)
    w = random.uniform(1.2, 1.7)
    col = HOUSE_COLS[i % len(HOUSE_COLS)]
    cube(f"house{i}", (x, y, h / 2), (w, 1.4, h / 2), mat(f"hc{i}", col, 0.8))
    cone(f"roof{i}", (x, y, h + 0.8), w * 1.55, 1.6, mat(f"rc{i}", (0.35, 0.12, 0.08), 0.8),
         rot=(0, 0, math.radians(45)), verts=4)
    for wx in (-0.5, 0.5):
        cube(f"win{i}{wx}", (x + wx * w, y - 1.41, h * 0.6), (0.25, 0.02, 0.3), M["window"])
    cube(f"door{i}", (x, y - 1.41, 0.5), (0.3, 0.02, 0.5), M["wood"])

# water tower
cyl("tower_leg1", (9, 16, 3), 0.1, 6, M["wood"])
cyl("tower_tank", (9, 16, 6.8), 1.6, 2.2, mat("tank", (0.7, 0.72, 0.75), 0.4))
cone("tower_top", (9, 16, 8.4), 1.7, 1.0, mat("tank2", (0.5, 0.52, 0.55), 0.4))
text("tower_txt", "GERALD\nKNOWS", (9, 14.35, 6.8), 0.55, M["band"], extrude=0.02)

# welcome sign
for sx in (-4.6, -2.4):
    cyl(f"post{sx}", (sx, 4.0, 1.0), 0.08, 2.0, M["wood"])
cube("signboard", (-3.5, 4.0, 1.7), (1.35, 0.05, 0.55), M["sign"])
text("signtxt", "WELCOME TO\nGERALDVILLE\npop. ???", (-3.5, 3.93, 1.72), 0.3, M["white"])

# trees
for i, (tx, ty) in enumerate([(4.5, 4.5), (6, 8), (-7, 8), (13, 9), (-12, 7)]):
    cyl(f"trunk{i}", (tx, ty, 0.6), 0.15, 1.2, M["wood"])
    sphere(f"leaf{i}", (tx, ty, 1.7), (0.9, 0.9, 1.1), mat(f"leafm{i}", (0.1, 0.35 + 0.05 * i, 0.1), 0.9), seg=16)

# ---------- podium ----------
pod = cube("podium", (0, 0.2, 0.75), (0.75, 0.45, 0.75), M["wood"])
cube("podium_top", (0, 0.1, 1.53), (0.9, 0.6, 0.04), M["wood"], rot=(math.radians(-12), 0, 0))
cyl("seal", (0, -0.26, 0.85), 0.42, 0.04, M["gold"], rot=(math.radians(90), 0, 0))
text("sealtxt", "MAYOR", (0, -0.29, 0.85), 0.2, M["wood"], extrude=0.01)
# microphone
cyl("mic_stand", (0.25, -0.15, 1.75), 0.015, 0.45, M["hat"], rot=(math.radians(25), 0, 0))
sphere("mic", (0.25, -0.25, 1.97), (0.07, 0.07, 0.09), M["hat"])

# ---------- raccoon ----------
root = bpy.data.objects.new("raccoon", None)
scn.collection.objects.link(root)
root.location = (0, 0.6, 0)

body = sphere("body", (0, 0.6, 1.55), (0.62, 0.5, 0.75), M["fur"], root)
belly = sphere("belly", (0, 0.25, 1.55), (0.42, 0.2, 0.55), M["fur_light"], root)
# sash
sash = cyl("sash", (0, 0.55, 1.7), 0.6, 0.12, M["sash"], rot=(math.radians(10), math.radians(35), 0), parent=root)
sash.scale = (1.06, 0.88, 1)
sphere("medal", (0.18, 0.08, 1.85), (0.09, 0.03, 0.09), M["gold"], root)

# head pivot (neck)
head = bpy.data.objects.new("head", None)
scn.collection.objects.link(head)
head.location = (0, 0.55, 2.25)
head.parent = root
head.location = (0, -0.05, 2.25)

def hpart(fn, *a, **k):
    o = fn(*a, **k)
    par(o, head)
    return o

HZ = 2.75
hpart(sphere, "skull", (0, 0.55, HZ), (0.55, 0.5, 0.48), M["fur"])
hpart(sphere, "cheekL", (-0.38, 0.4, HZ - 0.12), (0.28, 0.25, 0.22), M["fur_light"])
hpart(sphere, "cheekR", (0.38, 0.4, HZ - 0.12), (0.28, 0.25, 0.22), M["fur_light"])
hpart(sphere, "mask", (0, 0.2, HZ + 0.05), (0.5, 0.22, 0.17), M["fur_dark"])
hpart(sphere, "brow", (0, 0.17, HZ + 0.22), (0.3, 0.12, 0.07), M["fur_light"])
hpart(sphere, "muzzle", (0, 0.07, HZ - 0.17), (0.22, 0.22, 0.15), M["fur_light"])
hpart(sphere, "nose", (0, -0.13, HZ - 0.1), (0.075, 0.06, 0.055), M["nose"])
mouth = hpart(sphere, "mouth", (0, 0.0, HZ - 0.3), (0.12, 0.08, 0.02), M["mouth"])
jaw = hpart(sphere, "jaw", (0, 0.07, HZ - 0.3), (0.17, 0.17, 0.08), M["fur_light"])
eyes = []
for sx in (-1, 1):
    e = hpart(sphere, f"eye{sx}", (sx * 0.2, 0.03, HZ + 0.06), (0.09, 0.06, 0.09), M["eye"])
    hpart(sphere, f"pupil{sx}", (sx * 0.19, -0.03, HZ + 0.05), (0.045, 0.02, 0.05), M["pupil"])
    eyes.append(e)
    # suspicious eyelid (half-closed)
    lid = hpart(sphere, f"lid{sx}", (sx * 0.2, 0.025, HZ + 0.11), (0.1, 0.07, 0.055), M["fur_dark"])
    lid.rotation_euler = (0, sx * math.radians(-15), 0)
    eyes.append(lid)
    hpart(cone, f"ear{sx}", (sx * 0.38, 0.6, HZ + 0.45), 0.17, 0.35, M["fur"], rot=(0, sx * math.radians(25), 0))
    hpart(cone, f"earin{sx}", (sx * 0.37, 0.52, HZ + 0.43), 0.1, 0.25, M["fur_dark"], rot=(0, sx * math.radians(25), 0))
# top hat
hpart(cyl, "hat_brim", (0, 0.6, HZ + 0.43), 0.55, 0.04, M["hat"])
hat = hpart(cyl, "hat_crown", (0, 0.6, HZ + 0.8), 0.36, 0.72, M["hat"])
hpart(cyl, "hat_band", (0, 0.6, HZ + 0.53), 0.37, 0.12, M["band"])

# arms gripping podium
for sx in (-1, 1):
    a = cyl(f"arm{sx}", (sx * 0.62, 0.2, 1.62), 0.11, 0.7, M["fur"], rot=(math.radians(70), 0, sx * math.radians(-20)), parent=root)
    sphere(f"paw{sx}", (sx * 0.68, -0.15, 1.6), (0.13, 0.13, 0.1), M["fur_dark"], root)

# striped tail
for i in range(7):
    t = i / 6
    sphere(f"tail{i}", (0.6 + t * 0.7, 0.9, 0.9 + math.sin(t * 2.5) * 0.9), (0.2 - t * 0.04,) * 3,
           M["fur_dark"] if i % 2 else M["fur"], root, seg=16)

# ---------- lighting ----------
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(10), math.radians(-30)))
sun = bpy.context.object
sun.data.energy = 3.0
sun.data.color = (1.0, 0.85, 0.7)
bpy.ops.object.light_add(type="AREA", location=(-2.5, -4, 4))
key = bpy.context.object
key.data.energy = 400
key.data.size = 3
key.rotation_euler = (Vector((0, 0.5, 2.6)) - key.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="AREA", location=(2.5, 3, 4))
rim = bpy.context.object
rim.data.energy = 300
rim.data.color = (0.6, 0.7, 1.0)
rim.rotation_euler = (Vector((0, 0.5, 2.6)) - rim.location).to_track_quat("-Z", "Y").to_euler()
# dramatic red light for final line
bpy.ops.object.light_add(type="POINT", location=(0, -1.6, 2.0))
red = bpy.context.object
red.data.color = (1, 0.05, 0.05)
red.data.energy = 0

# ---------- camera ----------
bpy.ops.object.camera_add()
cam = bpy.context.object
scn.camera = cam
cam.data.lens = 35
target = bpy.data.objects.new("cam_target", None)
scn.collection.objects.link(target)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"

WIDE = ((0, -7.5, 2.4), (0, 1, 2.2))
MED = ((0, -4.2, 2.6), (0, 1, 2.55))
CLOSE = ((0, -2.4, 2.75), (0, 1, 2.75))
XCLOSE = ((0, -1.55, 2.78), (0, 1, 2.78))


def shot(frame, s, interp="BEZIER"):
    cam.location = s[0]
    target.location = s[1]
    for o in (cam, target):
        o.keyframe_insert("location", frame=frame)
        for fc in o.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                if kp.co.x == frame:
                    kp.interpolation = interp


def F(t):
    return int(round(t * FPS)) + 1


segs = T["segs"]
shot(1, WIDE)
shot(F(1.0), WIDE)
# line 1: slow push, snap close on "the bread knows"
shot(F(segs[0]["start"] + 0.1), MED, "CONSTANT")
shot(F(segs[0]["start"] + 3.6), CLOSE)
shot(F(segs[0]["end"] + 0.5), CLOSE, "CONSTANT")
# line 2: wide then punch in on "judged"
shot(F(segs[1]["start"]), MED, "BEZIER")
shot(F(segs[1]["start"] + 2.9), MED, "CONSTANT")
shot(F(segs[1]["start"] + 3.0), XCLOSE, "CONSTANT")
# line 3: medium, close on "Gerald", xclose on "don't ask"
shot(F(segs[2]["start"]), WIDE, "BEZIER")
shot(F(segs[2]["start"] + 3.2), MED, "CONSTANT")
shot(F(segs[2]["start"] + 3.3), CLOSE, "CONSTANT")
shot(F(segs[2]["start"] + 4.7), XCLOSE, "CONSTANT")
# line 4: quick snap zoom
shot(F(segs[3]["start"]), MED, "CONSTANT")
shot(F(segs[3]["start"] + 1.2), MED, "CONSTANT")
shot(F(segs[3]["start"] + 1.3), CLOSE, "CONSTANT")
# line 5: slow creepy push to extreme close-up
shot(F(segs[4]["start"]), MED, "BEZIER")
shot(F(segs[4]["end"]), XCLOSE, "BEZIER")
shot(END, XCLOSE)

# red light on final line
red.data.energy = 0
red.data.keyframe_insert("energy", frame=F(segs[4]["start"] + 2.5))
red.data.energy = 250
red.data.keyframe_insert("energy", frame=F(segs[4]["start"] + 3.5))
key.data.keyframe_insert("energy", frame=F(segs[4]["start"] + 2.5))
key.data.energy = 60
key.data.keyframe_insert("energy", frame=F(segs[4]["start"] + 3.5))

# ---------- lip sync & body motion ----------
JAW_Z = jaw.location.z
for f in range(1, END + 1):
    a = ENV[min(f - 1, len(ENV) - 1)]
    mouth.scale = (0.12, 0.08, 0.02 + 0.1 * a)
    mouth.keyframe_insert("scale", frame=f)
    jaw.location.z = JAW_Z - 0.11 * a
    jaw.keyframe_insert("location", index=2, frame=f)
    if f % 2 == 0:
        head.rotation_euler = (math.radians(-6 * a + 2 * math.sin(f * 0.09)),
                               math.radians(3 * math.sin(f * 0.05)),
                               math.radians(8 * math.sin(f * 0.031)))
        head.keyframe_insert("rotation_euler", frame=f)
        root.location.z = 0.02 * math.sin(f * 0.12)
        root.keyframe_insert("location", index=2, frame=f)

# blinks
for bt in [3.0, 9.5, 15.0, 19.2, 26.0]:
    for e in eyes:
        base = e.scale.copy()
        for df, k in ((0, 1.0), (2, 0.1), (4, 1.0)):
            e.scale = (base.x, base.y, base.z * k)
            e.keyframe_insert("scale", frame=F(bt) + df)
        e.scale = base

# ---------- captions (attached to camera) ----------
cap_root = bpy.data.objects.new("captions", None)
scn.collection.objects.link(cap_root)
cap_root.parent = cam
cap_root.location = (0, -0.165, -0.5)  # lower third in camera space, in front of everything
cap_root.scale = (0.25, 0.25, 0.25)

ban = cube("banner", (0, 0, -0.02), (0.6, 0.27, 0.001), M["banner"])
ban.parent = cap_root
ban.location = (0, 0, -0.02)
ban.rotation_euler = (0, 0, 0)
bm = ban.active_material
bm.blend_method = "BLEND"
b = bm.node_tree.nodes["Principled BSDF"]
b.inputs["Alpha"].default_value = 0.6
ban.visible_shadow = False


def vis(o, ranges):
    o.hide_render = True
    o.hide_viewport = True
    o.keyframe_insert("hide_render", frame=1)
    for s, e in ranges:
        o.hide_render = False
        o.keyframe_insert("hide_render", frame=s)
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=e)
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


ranges_all = []
for i, s in enumerate(segs):
    lines = CAPTIONS[i].split("\n")
    o = text(f"cap{i}", CAPTIONS[i], (0, 0, 0), 0.075, M["capw"], rot=(0, 0, 0), extrude=0.0)
    o.parent = cap_root
    o.location = (0, 0, 0)
    o.data.space_line = 1.1
    o.visible_shadow = False
    # colour the first line yellow
    o.data.materials.append(M["cap"])
    for ci in range(len(lines[0])):
        o.data.body_format[ci].material_index = 1
    st, en = F(s["start"]) - 2, F(s["end"] + 0.5)
    vis(o, [(st, en)])
    ranges_all.append((st, en))
vis(ban, ranges_all)

# title card
title = text("title", "IN THIS TOWN...", (0, 0, 0), 0.105, M["cap"], rot=(0, 0, 0), extrude=0.0)
title.parent = cap_root
title.location = (0, 0.95, 0)
title.visible_shadow = False
vis(title, [(1, F(1.0) - 2)])

# ---------- render settings ----------
scn.render.engine = ENGINE
if ENGINE == "CYCLES":
    scn.cycles.samples = 20
    scn.cycles.adaptive_threshold = 0.05
    scn.cycles.blur_glossy = 1.0
    scn.render.threads_mode = "AUTO"
    scn.cycles.use_denoising = False
    scn.cycles.max_bounces = 4
    scn.cycles.device = "CPU"
else:
    scn.eevee.taa_render_samples = 32
scn.view_settings.look = "AgX - Punchy"
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = os.path.join(HERE, "frames", "f_")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "in_this_town.blend"))
print("BUILT", END, "frames")
