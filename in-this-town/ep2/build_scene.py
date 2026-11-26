# "In This Town: The Jump" - blocky-character Blender scene, fully scripted.
# Run: blender -b -P build_scene.py -- [res_percent]
import bpy, json, math, os, sys, random
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from story import NAMES

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RES_PCT = int(argv[0]) if argv else 50

T = json.load(open(os.path.join(HERE, "timing.json")))
FPS = 24
END = int(T["dur"] * FPS)
LN = {L["id"]: L for L in T["lines"]}
ENV = T["env"]
SFX_T = T["sfx"]


def S(i): return LN[i]["start"]
def E(i): return LN[i]["end"]
def F(t): return int(round(t * FPS)) + 1


def env_at(who, t):
    a = ENV.get(who)
    if not a:
        return 0.0
    i = int(t * FPS)
    return a[i] if 0 <= i < len(a) else 0.0


def boings_between(t0, t1):
    return [s["t"] for s in SFX_T if s["name"] == "boing" and t0 <= s["t"] < t1]


# ---------- reset ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, END
scn.render.resolution_x, scn.render.resolution_y = 1080, 1920
scn.render.resolution_percentage = RES_PCT
random.seed(11)


# ---------- helpers ----------
MATS = {}
def mat(name, color, rough=0.6, emit=0.0, metal=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    MATS[name] = m
    return m


def setmat(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def par(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw


def bevel(o, w=0.04, seg=3):
    md = o.modifiers.new("bev", "BEVEL")
    md.width = w
    md.segments = seg
    md.limit_method = "NONE"
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.use_auto_smooth = True if hasattr(o.data, "use_auto_smooth") else None
    return o


def box(name, loc, half, m, rot=(0, 0, 0), bev=0.0, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = half
    setmat(o, m)
    if bev:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel(o, bev)
    if parent:
        par(o, parent)
    return o


def cyl(name, loc, r, depth, m, rot=(0, 0, 0), parent=None, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    for p in o.data.polygons:
        p.use_smooth = True
    setmat(o, m)
    if parent:
        par(o, parent)
    return o


def cone(name, loc, r1, depth, m, rot=(0, 0, 0), verts=4):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    return setmat(o, m)


def sphere(name, loc, scale, m, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    for p in o.data.polygons:
        p.use_smooth = True
    setmat(o, m)
    if parent:
        par(o, parent)
    return o


def text(name, body, loc, size, m, rot=(math.radians(90), 0, 0), extrude=0.02):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.body = body
    o.data.size = size
    o.data.extrude = extrude
    o.data.align_x = "CENTER"
    o.data.align_y = "CENTER"
    return setmat(o, m)


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    scn.collection.objects.link(o)
    o.location = loc
    if parent:
        o.parent = parent
    return o


def vis(o, ranges):
    """Render-visible only during the given frame ranges."""
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=0)
    for s, e in ranges:
        o.hide_render = False
        o.keyframe_insert("hide_render", frame=s)
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=e)
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


BLACK = mat("black", (0.01, 0.01, 0.01), 0.4)
SKIN = mat("skin", (1.0, 0.78, 0.55), 0.6)
SKIN2 = mat("skin2", (0.62, 0.42, 0.28), 0.6)
SKIN3 = mat("skin3", (0.95, 0.68, 0.5), 0.6)
WHITE = mat("white", (0.95, 0.95, 0.95), 0.5)
GOLD = mat("gold", (1.0, 0.72, 0.2), 0.3, metal=0.8)
RED = mat("red", (0.8, 0.05, 0.05), 0.5)
WOOD = mat("wood", (0.4, 0.22, 0.1), 0.7)


# ---------- blocky character ----------
class Char:
    def __init__(self, name, shirt, pants, skin=SKIN, scale=1.0, speaker=None, gestures=False):
        self.name, self.scale, self.speaker, self.gestures = name, scale, speaker, gestures
        self.path = []      # (t0, t1, p0, p1, kind)
        self.faces = []     # (t, rz, dur)
        self.jumps = []     # (t, h, dur)
        self.loops = []     # (t0, t1, period, h, phase)
        self.waves = []     # (t0, t1)
        self.handsup = []   # (t0, t1)
        self.lookups = []   # (t0, t1)
        self.angry = []     # (t0, t1)
        self.fly_t = None
        self.extra_talk = [] # (t0, t1, who)
        self.holding = None  # (t0, t1) arms forward holding something

        r = empty(name)
        self.root = r
        ms, mp = mat(name + "_shirt", shirt, 0.7), mat(name + "_pants", pants, 0.7)
        # torso
        box(name + "_torso", (0, 0, 1.5), (0.45, 0.22, 0.5), ms, bev=0.03, parent=r)
        # legs
        self.legs = []
        for sx in (-1, 1):
            hip = empty(f"{name}_hip{sx}", (sx * 0.225, 0, 1.0), r)
            box(f"{name}_leg{sx}", (sx * 0.225, 0, 0.5), (0.22, 0.22, 0.5), mp, bev=0.03, parent=hip)
            box(f"{name}_shoe{sx}", (sx * 0.225, -0.02, 0.06), (0.23, 0.25, 0.07), BLACK, bev=0.02, parent=hip)
            self.legs.append(hip)
        # arms
        self.arms = []
        for sx in (-1, 1):
            sh = empty(f"{name}_sh{sx}", (sx * 0.65, 0, 1.9), r)
            box(f"{name}_arm{sx}", (sx * 0.65, 0, 1.5), (0.2, 0.2, 0.5), ms, bev=0.03, parent=sh)
            box(f"{name}_hand{sx}", (sx * 0.65, 0, 1.05), (0.19, 0.19, 0.1), skin, bev=0.03, parent=sh)
            self.arms.append(sh)
        # head
        nk = empty(name + "_neck", (0, 0, 2.0), r)
        self.neck = nk
        cyl(name + "_neckc", (0, 0, 2.03), 0.15, 0.1, skin, parent=nk)
        self.head = box(name + "_head", (0, 0, 2.36), (0.33, 0.3, 0.3), skin, bev=0.09, parent=nk)
        self.eyes = []
        for sx in (-1, 1):
            self.eyes.append(box(f"{name}_eye{sx}", (sx * 0.12, -0.305, 2.42), (0.04, 0.012, 0.065), BLACK, bev=0.015, parent=nk))
        self.mouth = box(name + "_mouth", (0, -0.305, 2.24), (0.11, 0.012, 0.025), BLACK, bev=0.008, parent=nk)
        self.mouth_base = self.mouth.scale.copy()

    def finalize(self):
        bpy.context.view_layer.update()
        self.root.scale = (self.scale,) * 3

    # --- accessories ---
    def brows(self, angle=18, m=BLACK):
        for sx in (-1, 1):
            b = box(f"{self.name}_brow{sx}", (sx * 0.13, -0.31, 2.53), (0.08, 0.012, 0.02), m, parent=self.neck)
            b.rotation_euler = (0, -sx * math.radians(angle), 0)

    def stache(self, m):
        box(self.name + "_stache", (0, -0.32, 2.31), (0.16, 0.02, 0.035), m, bev=0.015, parent=self.neck)

    def cap(self, m, backwards=False):
        box(self.name + "_cap", (0, 0, 2.68), (0.35, 0.32, 0.08), m, bev=0.04, parent=self.neck)
        y = 0.42 if backwards else -0.42
        box(self.name + "_brim", (0, y, 2.62), (0.3, 0.14, 0.02), m, bev=0.01, parent=self.neck)

    def hair(self, m, bun=False):
        box(self.name + "_hair", (0, 0.04, 2.6), (0.36, 0.32, 0.1), m, bev=0.05, parent=self.neck)
        box(self.name + "_hairback", (0, 0.27, 2.35), (0.36, 0.08, 0.3), m, bev=0.04, parent=self.neck)
        if bun:
            sphere(self.name + "_bun", (0, 0.2, 2.82), (0.17, 0.17, 0.15), m, parent=self.neck)

    def tophat(self):
        hat = empty(self.name + "_tophat", (0, 0, 2.66), self.neck)
        cyl(self.name + "_hatbrim", (0, 0, 2.68), 0.5, 0.04, BLACK, parent=hat)
        cyl(self.name + "_hatcrown", (0, 0, 3.08), 0.33, 0.8, BLACK, parent=hat)
        cyl(self.name + "_hatband", (0, 0, 2.78), 0.335, 0.12, RED, parent=hat)
        return hat

    # --- choreography ---
    def place(self, t, p, rz=None):
        p = Vector((*p, 0)) if len(p) == 2 else Vector(p)
        self.path.append((t, t, p, p, "place"))
        if rz is not None:
            self.faces.append((t, math.radians(rz), 0.0))

    def walk(self, t0, t1, p1, kind="walk", face=True):
        p0 = self.pos_at(t0)
        p1 = Vector((*p1, p0.z)) if len(p1) == 2 else Vector(p1)
        self.path.append((t0, t1, p0, p1, kind))
        if face and (p1 - p0).xy.length > 0.01:
            d = p1 - p0
            self.faces.append((t0, math.atan2(d.x, -d.y), 0.2))

    def face(self, t, rz, dur=0.3):
        self.faces.append((t, math.radians(rz), dur))

    def face_toward(self, t, other_xy, dur=0.3):
        p = self.pos_at(t)
        d = Vector(other_xy) - p.xy
        self.faces.append((t, math.atan2(d.x, -d.y), dur))

    def pos_at(self, t):
        cur = Vector((0, 0, 0)); seg = None
        for s in sorted(self.path, key=lambda s: s[0]):
            if s[0] <= t:
                if t < s[1]:
                    u = (t - s[0]) / (s[1] - s[0])
                    return s[2].lerp(s[3], u)
                cur = s[3]
        return cur.copy()

    def walking_at(self, t):
        for s in self.path:
            if s[4] in ("walk", "stiff", "march") and s[0] <= t < s[1]:
                return s[4]
        return None

    def rz_at(self, t):
        rz = 0.0
        prev = 0.0
        for (t0, a, d) in sorted(self.faces, key=lambda f: f[0]):
            if t0 > t:
                break
            if d > 0 and t < t0 + d:
                u = (t - t0) / d
                u = u * u * (3 - 2 * u)
                # shortest arc
                diff = (a - prev + math.pi) % (2 * math.pi) - math.pi
                return prev + diff * u
            prev = a
            rz = a
        return rz

    def head_pos(self, t):
        p = self.pos_at(t)
        return Vector((p.x, p.y, p.z + self.jump_z(t) + 2.35 * self.scale))

    def front(self, t):
        rz = self.rz_at(t)
        return Vector((math.sin(rz), -math.cos(rz), 0))

    def jump_z(self, t):
        z = 0.0
        for (t0, h, d) in self.jumps:
            if t0 <= t < t0 + d:
                u = (t - t0) / d
                z = max(z, h * 4 * u * (1 - u))
        for (t0, t1, per, h, ph) in self.loops:
            if t0 <= t < t1:
                u = ((t - t0) / per + ph) % 1.0
                z = max(z, h * 4 * u * (1 - u))
        if self.fly_t is not None and t >= self.fly_t:
            dt = t - self.fly_t
            z = 6 * dt + 9 * dt * dt
        return z

    def airborne(self, t):
        return self.jump_z(t) > 0.05

    def in_any(self, lst, t):
        return any(a <= t < b for a, b in lst)

    def bake(self, frames):
        for f in frames:
            t = (f - 1) / FPS
            p = self.pos_at(t)
            jz = self.jump_z(t)
            wk = self.walking_at(t)
            idle = 0.015 * math.sin(t * 2.2 + hash(self.name) % 7)
            self.root.location = (p.x, p.y, p.z + jz + (0 if wk else idle))
            self.root.rotation_euler = (0, 0, self.rz_at(t))
            self.root.keyframe_insert("location", frame=f)
            self.root.keyframe_insert("rotation_euler", frame=f)

            leg = [0.0, 0.0]; armx = [0.0, 0.0]; army = [0.0, 0.0]
            if wk:
                speed = 11 if wk == "march" else 8
                amp = math.radians(40 if wk == "march" else 30)
                s = math.sin(t * speed)
                leg = [s * amp, -s * amp]
                if wk != "stiff":
                    armx = [-s * amp, s * amp]
            if self.airborne(t):
                leg = [math.radians(-25), math.radians(15)]
                armx = [0, 0]
                army = [math.radians(150), math.radians(-150)]
            if self.holding and self.holding[0] <= t < self.holding[1]:
                armx = [math.radians(-55), math.radians(-55)]
            # talking gestures
            who = self.speaker
            a = env_at(who, t) if who else 0.0
            for (t0, t1, w) in self.extra_talk:
                if t0 <= t < t1:
                    a = max(a, env_at(w, t))
            if self.gestures and a > 0.1 and not self.airborne(t):
                armx[1] = math.radians(-50 - 25 * math.sin(t * 5))
                army[1] = math.radians(-10)
            if self.in_any(self.angry, t):
                armx = [math.radians(-100 - 40 * math.sin(t * 9)), math.radians(-100 - 40 * math.sin(t * 9 + 2))]
                army = [math.radians(20), math.radians(-20)]
            for (t0, t1) in self.waves:
                if t0 <= t < t1:
                    armx[1] = math.radians(-165)
                    army[1] = math.radians(-20 + 25 * math.sin(t * 14))
            if self.in_any(self.handsup, t):
                armx = [math.radians(-160), math.radians(-160)]
                army = [math.radians(25), math.radians(-25)]
            if self.fly_t is not None and t >= self.fly_t - 0.25 and t < self.fly_t:
                leg = [math.radians(-30), math.radians(-30)]  # crouch
                self.root.location.z -= 0.15
                self.root.keyframe_insert("location", frame=f)
            if self.fly_t is not None and t >= self.fly_t:
                armx = [math.radians(-180), math.radians(-180)]
                army = [0, 0]
                leg = [0, 0]
            for i in range(2):
                self.legs[i].rotation_euler = (leg[i], 0, 0)
                self.legs[i].keyframe_insert("rotation_euler", frame=f)
                self.arms[i].rotation_euler = (armx[i], army[i], 0)
                self.arms[i].keyframe_insert("rotation_euler", frame=f)
            # head
            hx = -0.12 * a + 0.03 * math.sin(t * 1.3)
            if self.in_any(self.lookups, t):
                hx = math.radians(-35)
            if self.in_any(self.handsup, t):
                hx = math.radians(-12)
            self.neck.rotation_euler = (hx, 0, 0.06 * math.sin(t * 0.9 + len(self.name)))
            self.neck.keyframe_insert("rotation_euler", frame=f)
            # mouth
            ms = self.mouth_base
            self.mouth.scale = (ms.x * (1 - 0.2 * a), ms.y, ms.z * (1 + 3.5 * a))
            self.mouth.keyframe_insert("scale", frame=f)
        # blinks
        bt = 2.0 + (hash(self.name) % 10) / 10
        while bt < T["dur"]:
            for e in self.eyes:
                base = e.scale.copy()
                for df, k in ((0, 1.0), (2, 0.1), (4, 1.0)):
                    e.scale = (base.x, base.y, base.z * k)
                    e.keyframe_insert("scale", frame=F(bt) + df)
                e.scale = base
            bt += random.uniform(3.0, 5.5)


# ---------- world ----------
world = bpy.data.worlds.new("sky")
scn.world = world
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
coord = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB")
nt.links.new(coord.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (1.0, 0.75, 0.45, 1)
ramp.color_ramp.elements[1].position = 0.35
ramp.color_ramp.elements[1].color = (0.25, 0.5, 0.95, 1)
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0

# ---------- set ----------
GRASS = mat("grass", (0.25, 0.6, 0.18), 0.9)
box("ground", (0, 10, -0.1), (80, 80, 0.1), GRASS)
cyl("plaza", (0, 1, 0.005), 10, 0.01, mat("plaza", (0.6, 0.58, 0.55), 0.8), verts=64)
box("road", (0, -5.5, 0.01), (80, 1.6, 0.01), mat("road", (0.13, 0.13, 0.14), 0.9))
for x in range(-30, 31, 4):
    box(f"stripe{x}", (x, -5.5, 0.025), (0.8, 0.08, 0.01), WHITE)

# stage + podium
box("stage", (0, 5.6, 0.15), (2.4, 1.4, 0.15), WOOD, bev=0.03)
box("podium", (0, 4.75, 0.95), (0.6, 0.35, 0.65), mat("podwood", (0.3, 0.15, 0.06), 0.6), bev=0.03)
cyl("seal", (0, 4.39, 1.0), 0.35, 0.03, GOLD, rot=(math.radians(90), 0, 0))
text("sealtxt", "G", (0, 4.36, 1.0), 0.4, mat("podwood", (0.3, 0.15, 0.06)), extrude=0.01)

# town hall
HALL = mat("hall", (0.9, 0.88, 0.8), 0.7)
box("hall", (0, 10.5, 2.5), (4.5, 2.0, 2.5), HALL, bev=0.05)
cone("hallroof", (0, 10.5, 6.0), 4.2, 2.0, mat("hallroof", (0.55, 0.15, 0.1), 0.7), rot=(0, 0, math.radians(45)))
for cx in (-3, -1, 1, 3):
    cyl(f"col{cx}", (cx, 8.3, 2.2), 0.25, 4.4, HALL)
box("halldoor", (0, 8.45, 1.1), (0.8, 0.05, 1.1), WOOD)
text("halltxt", "GERALDVILLE TOWN HALL", (0, 8.4, 4.6), 0.45, mat("dark", (0.1, 0.1, 0.12)), extrude=0.03)

# houses
HOUSE_COLS = [(0.85, 0.35, 0.35), (0.35, 0.55, 0.85), (0.95, 0.8, 0.4), (0.55, 0.8, 0.5), (0.75, 0.5, 0.8), (0.95, 0.6, 0.35)]
WIN = mat("window", (1.0, 0.85, 0.5), 0.3, emit=2.0)
spots = [(-9, 9), (-14, 11), (-19, 8), (9, 9), (14, 11), (19, 8), (-11, 3), (11, 3), (-24, 12), (24, 12), (-16, 17), (16, 17)]
for i, (x, y) in enumerate(spots):
    h = random.uniform(2.2, 3.4); w = random.uniform(1.5, 2.0)
    box(f"house{i}", (x, y, h / 2), (w, 1.6, h / 2), mat(f"hc{i}", HOUSE_COLS[i % 6], 0.8), bev=0.04)
    cone(f"roof{i}", (x, y, h + 0.9), w * 1.55, 1.8, mat(f"rc{i}", (0.4, 0.15, 0.1), 0.8), rot=(0, 0, math.radians(45)))
    for wx in (-0.5, 0.5):
        box(f"win{i}{wx}", (x + wx * w, y - 1.62, h * 0.62), (0.28, 0.02, 0.3), WIN)
    box(f"door{i}", (x, y - 1.62, 0.55), (0.32, 0.02, 0.55), WOOD)

# water tower
cyl("tleg", (-12, 22, 4), 0.15, 8, WOOD)
cyl("ttank", (-12, 22, 9), 2.2, 3.0, mat("tank", (0.7, 0.72, 0.75), 0.4))
cone("ttop", (-12, 22, 11.2), 2.3, 1.4, mat("tank2", (0.5, 0.52, 0.55), 0.4), verts=32)
text("ttxt", "GERALD\nKNOWS", (-12, 19.75, 9), 0.75, RED)

# trees
for i, (tx, ty) in enumerate([(-6.5, 6), (6.5, 6), (-12, -1), (12, -1), (-7, -8), (8, -8), (20, 2), (-20, 2)]):
    cyl(f"trunk{i}", (tx, ty, 0.7), 0.2, 1.4, WOOD, verts=8)
    box(f"leaf{i}", (tx, ty, 2.1), (0.9, 0.9, 0.9), mat(f"leaf{i}", (0.12, 0.4 + 0.03 * i, 0.12), 0.9), bev=0.1)

# NO JUMPING signs
SIGNW = mat("signw", (0.97, 0.97, 0.95), 0.5)
for i, (sx, sy, rz) in enumerate([(-4.5, 3.8, 15), (5.2, 3.5, -15), (-8.5, -2.5, 30)]):
    post = cyl(f"spost{i}", (sx, sy, 1.0), 0.06, 2.0, mat("metal", (0.5, 0.5, 0.55), 0.3, metal=1.0), verts=8)
    sg = box(f"sign{i}", (sx, sy - 0.05, 2.1), (0.6, 0.03, 0.45), SIGNW, rot=(0, 0, math.radians(rz)))
    t1 = text(f"signt{i}", "NO\nJUMPING", (sx, sy - 0.09, 2.1), 0.22, RED, rot=(math.radians(90), 0, math.radians(rz)), extrude=0.005)

# puddle
PUDDLE = (2.6, -1.0)
pud = cyl("puddle", (PUDDLE[0], PUDDLE[1], 0.02), 0.65, 0.01, mat("water", (0.15, 0.35, 0.7), 0.05, metal=0.3), verts=48)
pud.scale = (1.3, 0.8, 1)

# ---------- cast ----------
mayor = Char("mayor", (0.05, 0.05, 0.07), (0.05, 0.05, 0.07), scale=1.05, speaker="mayor", gestures=True)
box("mayor_shirtv", (0, -0.225, 1.75), (0.13, 0.01, 0.25), WHITE, parent=mayor.root)
box("mayor_tie", (0, -0.235, 1.7), (0.05, 0.01, 0.2), RED, parent=mayor.root)
sash = box("mayor_sash", (0, -0.235, 1.5), (0.09, 0.01, 0.62), mat("sash", (0.85, 0.1, 0.1)), parent=mayor.root)
sash.rotation_euler = (0, math.radians(35), 0)
mayor.brows(22)
mayor.stache(mat("gray", (0.6, 0.6, 0.62), 0.8))
mayor_hat = mayor.tophat()

jax = Char("jax", (0.1, 0.65, 0.75), (0.2, 0.2, 0.25), skin=SKIN2, scale=0.8, speaker="jax", gestures=True)
jax.head.data.materials[0] = SKIN2
jax.cap(mat("jaxcap", (0.9, 0.1, 0.1), 0.6), backwards=True)

dave = Char("dave", (0.95, 0.5, 0.1), (0.15, 0.25, 0.6), skin=SKIN3, speaker="dave")
dave.cap(mat("davecap", (0.2, 0.5, 0.2), 0.6))
dave.brows(-8)
dave.stache(mat("brown", (0.3, 0.17, 0.08), 0.8))

linda = Char("linda", (0.6, 0.25, 0.7), (0.35, 0.15, 0.4), speaker="linda")
linda.hair(mat("lhair", (0.45, 0.25, 0.1), 0.8), bun=True)
bread_held = box("bread_held", (0, -0.55, 1.2), (0.32, 0.14, 0.12), mat("bread", (0.85, 0.55, 0.25), 0.8), bev=0.07, parent=linda.root)

extras = []
for i, (sh, pa, hr) in enumerate([((0.9, 0.85, 0.2), (0.3, 0.3, 0.35), (0.1, 0.07, 0.05)),
                                  ((0.3, 0.7, 0.4), (0.15, 0.15, 0.2), (0.85, 0.75, 0.4)),
                                  ((0.9, 0.4, 0.55), (0.25, 0.25, 0.6), None)]):
    c = Char(f"town{i}", sh, pa, skin=[SKIN, SKIN2, SKIN3][i])
    if hr:
        c.hair(mat(f"thair{i}", hr, 0.8), bun=(i == 1))
    else:
        c.cap(mat("tcap", (0.1, 0.2, 0.6)))
    extras.append(c)
TOWN = [dave, linda] + extras
CAST = [mayor, jax] + TOWN
for c in CAST:
    c.finalize()

# ---------- choreography ----------
STAGE = (0, 5.7, 0.3)
mayor.place(-1, STAGE, 0)
jax.place(-1, (-16, -1.2), 0)
spots_final = {"dave": (4.6, 0.6), "linda": (-1.8, 0.9), "town0": (-4.6, 1.8), "town1": (1.4, 2.6), "town2": (6.4, 2.2)}
starts = {"dave": (14, -3.0), "linda": (-13, -3.5), "town0": (-15, 1.0), "town1": (-6, -9), "town2": (15, 2.0)}
for c in TOWN:
    c.place(-1, starts[c.name], 0)
    # stiff, slow walk into the plaza during the narrator intro
    c.walk(0.3 + random.uniform(0, 1.0), S("m1") - 0.2, spots_final[c.name], kind="stiff")
    c.face(S("m1") - 0.2, 180, 0.4)  # face podium
for c in TOWN:
    c.extra_talk.append((S("c1"), E("c1") + 0.1, "crowd"))
    c.extra_talk.append((S("c2"), E("c2") + 0.1, "crowd"))
linda.holding = (0, E("l2") - 0.3)
mayor.face(S("m1"), 0)

# the kid arrives
jax.walk(S("n4") + 0.6, S("j1") + 0.2, (0.6, -1.2))
jax.face(S("j1") + 0.2, 0, 0.3)
jax.waves.append((S("j1") + 0.1, E("j1")))
for c in TOWN:
    c.face_toward(S("n4") + 1.8 + random.uniform(0, 0.6), (0.6, -1.2), 0.4)
jax.face_toward(S("l1"), spots_final["linda"])
jax.face_toward(S("d2"), spots_final["dave"])
# the jump
jt = E("j3") - 0.1
jax.walk(S("j3"), jt, (1.4, -1.0))
jax.jumps.append((jt, 1.6, 0.8))
jax.walk(jt, jt + 0.8, (3.9, -1.0), kind="air")
for c in TOWN:
    c.face_toward(jt + 0.4, (3.0, -1.0), 0.3)
    c.handsup.append((S("c1") - 0.1, S("c1") + 1.0))
# bread drop
DROP_T = E("l2") - 0.3
# mayor marches over
MPOS = (7.6, -1.2)
mayor.walk(S("d3") - 0.2, S("m5") - 0.1, (MPOS[0], MPOS[1], 0.0), kind="march")
mayor.face(S("m5") - 0.1, -90, 0.2)  # face -x toward jax
jax.face(S("m5"), 90, 0.3)
for c in TOWN:
    c.face_toward(S("m5") + 0.3, (5.7, -1.1), 0.5)
mayor.angry.append((S("m7"), E("m7")))
# "Watch." jump
jw = S("j9") + 0.6
jax.jumps.append((jw, 2.0, 0.9))
# dave and linda join
db = E("d4") - 0.1
dave.jumps.append((db, 1.3, 0.75))
lb = S("l3") + 0.2
linda.jumps.append((lb, 1.2, 0.75))
# everyone jumps
t_music, t_stop = S("n5"), S("m12")
for i, c in enumerate([jax, dave, linda] + extras):
    c.loops.append((t_music + 0.6 + 0.25 * i, t_stop, 0.75, 1.3 + 0.2 * (i % 3), 0.0))
mayor.angry.append((S("m12"), E("m12")))
for c in [jax] + TOWN:
    c.face_toward(S("m12") + 0.2, MPOS, 0.3)
# hat toss + launch
TOSS_T = E("m13") - 0.2
LAUNCH_T = S("sfx1") + 0.35
mayor.fly_t = LAUNCH_T
mayor.face(TOSS_T, 180, 0.4)
for c in [jax] + TOWN:
    c.lookups.append((LAUNCH_T + 0.3, S("j10") - 0.1))
# ending: kid on the stage
jax.place(S("j10") - 0.05, STAGE, 0)
for c in TOWN:
    c.face(S("j10") - 0.05, 180, 0.0)
for i, c in enumerate([jax] + TOWN):
    c.loops.append((S("c2") + 0.1 + 0.2 * i, T["dur"] + 1, 0.7, 1.2 + 0.2 * (i % 3), 0.0))

# props: dropped bread + tossed hat (world-space copies)
def world_from(c, t, local):
    p = c.pos_at(t); rz = c.rz_at(t); s = c.scale
    v = Vector(local) * s
    v.rotate(Euler((0, 0, rz)))
    return Vector((p.x, p.y, p.z + c.jump_z(t))) + v

bread_drop = box("bread_drop", (0, 0, 0), (0.32, 0.14, 0.12), mat("bread", (0.85, 0.55, 0.25)), bev=0.07)
b0 = world_from(linda, DROP_T, (0, -0.55, 1.2)); b1 = Vector((b0.x + 0.2, b0.y - 0.3, 0.13))
for k in range(0, 9):
    u = k / 8
    bread_drop.location = b0.lerp(b1, u) + Vector((0, 0, -(b0.z - 0.13) * (u * u) + (b0.z - 0.13) * u - (b0.z - 0.13) * u))
    bread_drop.location.z = b0.z + (0.13 - b0.z) * u * u
    bread_drop.rotation_euler = (0, 0, 0.6 * u)
    bread_drop.keyframe_insert("location", frame=F(DROP_T) + k)
    bread_drop.keyframe_insert("rotation_euler", frame=F(DROP_T) + k)
vis(bread_held, [(0, F(DROP_T))])
vis(bread_drop, [(F(DROP_T), END + 10)])

hat_toss = empty("hat_toss")
cyl("htb", (0, 0, 0.02), 0.5 * 1.05, 0.04, BLACK, parent=hat_toss)
cyl("htc", (0, 0, 0.42 * 1.05), 0.33 * 1.05, 0.8 * 1.05, BLACK, parent=hat_toss)
cyl("hbd", (0, 0, 0.12 * 1.05), 0.335 * 1.05, 0.12 * 1.05, RED, parent=hat_toss)
h0 = world_from(mayor, TOSS_T, (0, 0, 2.66)); h1 = Vector((h0.x + 1.6, h0.y - 0.8, 0.0))
for k in range(0, 15):
    u = k / 14
    pos = h0.lerp(h1, u)
    pos.z = h0.z * (1 - u) + 1.4 * 4 * u * (1 - u)
    hat_toss.location = pos
    hat_toss.rotation_euler = (math.radians(200) * u, 0, 0) if k < 14 else (0, 0, 0)
    hat_toss.keyframe_insert("location", frame=F(TOSS_T) + k)
    hat_toss.keyframe_insert("rotation_euler", frame=F(TOSS_T) + k)
for o in mayor_hat.children:
    vis(o, [(0, F(TOSS_T))])
for o in hat_toss.children:
    vis(o, [(F(TOSS_T), END + 10)])

FRAMES = list(range(1, END + 2, 2))
for c in CAST:
    c.bake(FRAMES)

# ---------- lights ----------
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(12), math.radians(-35)))
sun = bpy.context.object
sun.data.energy = 3.5
sun.data.color = (1.0, 0.93, 0.82)
sun.data.angle = math.radians(3)
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(60), 0, math.radians(150)))
fill = bpy.context.object
fill.data.energy = 0.8
fill.data.color = (0.7, 0.8, 1.0)
fill.data.use_shadow = False

# ---------- camera ----------
bpy.ops.object.camera_add()
cam = bpy.context.object
scn.camera = cam
cam.data.lens = 32
cam.data.clip_end = 2000
tgt = empty("cam_target")
con = cam.constraints.new("TRACK_TO")
con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"

V = Vector


def close(c, dist=2.6, side=0.0, up=0.15, aim=-0.05):
    def fn(t, u):
        h = c.head_pos(t); fr = c.front(t)
        rt = V((-fr.y, fr.x, 0))
        loc = h + fr * dist + rt * side + V((0, 0, up))
        return loc, h + V((0, 0, aim))
    return fn


def static(loc, target):
    return lambda t, u: (V(loc), V(target))


def push(l0, t0, l1, t1):
    return lambda t, u: (V(l0).lerp(V(l1), u), V(t0).lerp(V(t1), u))


def follow(c, off=(0, -7.5, 2.0), aim=1.3):
    def fn(t, u):
        p = c.pos_at(t)
        return V((p.x, p.y, 0)) + V(off), V((p.x, p.y, aim))
    return fn


def two_shot(a, b, dist=6.0, up=1.6):
    def fn(t, u):
        pa, pb = a.pos_at(t), b.pos_at(t)
        mid = (pa + pb) / 2
        return V((mid.x, mid.y - dist, up)), V((mid.x, mid.y, 1.6))
    return fn


def mix(fa, fb, k):
    return lambda t, u: tuple(x.lerp(y, k(u)) for x, y in zip(fa(t, u), fb(t, u)))


SHOTS = [
    (0, E("n1") + 0.3, push((0, -22, 7), (0, 4, 2), (0, -16, 5), (0, 4, 2))),
    (E("n1") + 0.3, S("m1") - 0.1, push((-6, -12, 2.4), (-2, 0, 1.2), (2, -11, 2.4), (1, 0, 1.2))),
    (S("m1") - 0.1, S("m2"), static((0, -1.5, 3.6), (0, 5.7, 3.0))),
    (S("m2"), S("m3"), push((0, 2.0, 3.2), (0, 5.7, 2.95), (0, 3.2, 3.15), (0, 5.7, 2.95))),
    (S("m3"), E("m3") - 0.6, static((0, 3.0, 3.1), (0, 5.7, 2.95))),
    (E("m3") - 0.6, S("d1"), static((0, 4.1, 2.95), (0, 5.7, 2.95))),
    (S("d1"), S("m4"), close(dave, 2.4)),
    (S("m4"), S("n3"), static((0, 3.9, 2.95), (0, 5.7, 2.95))),
    (S("n3"), S("n4"), push((0, -14, 9), (0, 3, 0.5), (0, -14, 6), (0, 3, 0.5))),
    (S("n4"), S("j1") + 0.1, follow(jax)),
    (S("j1") + 0.1, S("l1"), close(jax, 3.2, up=0.0)),
    (S("l1"), S("j2"), close(linda, 2.6)),
    (S("j2"), S("d2"), close(jax, 2.4)),
    (S("d2"), S("j3"), close(dave, 2.5)),
    (S("j3"), S("c1"), static((2.6, -10.5, 2.4), (2.6, -1.0, 2.0))),
    (S("c1"), S("l2"), static((3.6, -6.5, 1.8), (0.5, 1.5, 1.8))),
    (S("l2"), S("d3"), close(linda, 3.2, up=-0.2, aim=-0.6)),
    (S("d3"), S("m5"), close(dave, 2.6)),
    (S("m5"), S("j4"), close(mayor, 2.0, up=-0.4)),
    (S("j4"), S("m6"), close(jax, 2.2, up=0.2)),
    (S("m6"), S("j5"), close(mayor, 2.4, side=0.4)),
    (S("j5"), S("m7"), close(jax, 2.2, side=-0.3)),
    (S("m7"), S("j6"), close(mayor, 1.6, up=-0.2)),
    (S("j6"), S("m8"), close(jax, 2.0)),
    (S("m8"), S("j7"), close(mayor, 2.6, side=-0.5)),
    (S("j7"), S("m9"), two_shot(jax, mayor, 9.5, up=2.0)),
    (S("m9"), S("m10"), mix(close(mayor, 3.0), close(mayor, 2.2), lambda u: u)),
    (S("m10"), S("m11"), close(mayor, 2.0, side=0.3)),
    (S("m11"), S("j8"), mix(close(mayor, 2.0), close(mayor, 1.4), lambda u: u)),
    (S("j8"), S("j9"), close(jax, 2.2, up=0.1)),
    (S("j9"), S("d4"), two_shot(jax, mayor, 11.0, up=2.2)),
    (S("d4"), S("l3"), close(dave, 4.5, up=0.0)),
    (S("l3"), S("n5"), close(linda, 4.5, up=0.0)),
    (S("n5"), S("m12"), push((0, -13, 3.5), (1, 1, 1.8), (0, -10, 3.0), (1, 1, 1.8))),
    (S("m12"), S("m13"), close(mayor, 2.8)),
    (S("m13"), LAUNCH_T, close(mayor, 4.2, up=-0.3, aim=-0.5)),
    (LAUNCH_T, S("n6"), lambda t, u: (V((MPOS[0], MPOS[1] - 7, 1.0)), mayor.head_pos(t) if mayor.head_pos(t).z < 60 else V((MPOS[0], MPOS[1], 60)))),
    (S("n6"), S("n7"), static((MPOS[0] + 2, MPOS[1] - 4, 0.5), (MPOS[0], MPOS[1] + 6, 40))),
    (S("n7"), S("j10") - 0.05, static((2.5, -6.5, 0.6), (2.5, 0, 2.4))),
    (S("j10") - 0.05, S("j11"), static((0, 0.5, 2.8), (0, 5.7, 2.4))),
    (S("j11"), S("c2"), static((0, 3.0, 2.55), (0, 5.7, 2.35))),
    (S("c2"), T["dur"] + 1, push((0, -6, 3.0), (0, 4, 2.0), (0, -15, 6.0), (0, 4, 2.0))),
]


def cam_at(t):
    for (a, b, fn) in SHOTS:
        if a <= t < b:
            u = (t - a) / max(1e-6, b - a)
            return fn(t, u)
    return SHOTS[-1][2](t, 1.0)


for f in FRAMES:
    t = (f - 1) / FPS
    loc, target = cam_at(t)
    cam.location = loc
    tgt.location = target
    cam.keyframe_insert("location", frame=f)
    tgt.keyframe_insert("location", frame=f)

# ---------- captions ----------
cap_root = empty("captions", parent=cam)
cap_root.location = (0, -0.172, -0.5)
cap_root.scale = (0.25, 0.25, 0.25)
CAPW = mat("capw", (1, 1, 1), 0.5, emit=1.5)
CAPY = mat("capy", (1.0, 0.85, 0.15), 0.5, emit=1.5)
CAPN = mat("capn", (1.0, 0.95, 0.75), 0.5, emit=1.5)
BAN = mat("banner", (0, 0, 0), 1.0)
BAN.blend_method = "BLEND"
BAN.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.55
ban = box("banner", (0, 0, 0), (0.6, 0.23, 0.001), BAN)
ban.parent = cap_root
ban.location = (0, -0.01, -0.02)
ban.visible_shadow = False


def caption(name, body, header=None, mat_body=CAPW):
    full = (header + "\n" + body) if header else body
    o = text(name, full, (0, 0, 0), 0.085, mat_body, rot=(0, 0, 0), extrude=0.0)
    o.parent = cap_root
    o.location = (0, 0, 0)
    o.data.space_line = 1.05
    tb = o.data.text_boxes[0]
    tb.width, tb.height, tb.x, tb.y = 1.1, 0.42, -0.55, 0.2
    o.visible_shadow = False
    if header:
        o.data.materials.append(CAPY)
        for ci in range(len(header)):
            o.data.body_format[ci].material_index = 1
    return o


ranges = []
for L in T["lines"]:
    if not L["text"]:
        continue
    nm = NAMES.get(L["who"], "")
    o = caption("cap_" + L["id"], L["text"], nm or None, CAPW if nm else CAPN)
    st, en = F(L["start"]) - 2, F(L["end"] + 0.35)
    vis(o, [(st, en)])
    ranges.append((st, en))
vis(ban, ranges)

title = text("title", "IN THIS TOWN...", (0, 0, 0), 0.13, CAPY, rot=(0, 0, 0), extrude=0.0)
title.parent = cap_root; title.location = (0, 1.25, 0); title.visible_shadow = False
sub = text("subtitle", "Episode 2: THE JUMP", (0, 0, 0), 0.07, CAPW, rot=(0, 0, 0), extrude=0.0)
sub.parent = cap_root; sub.location = (0, 1.08, 0); sub.visible_shadow = False
vis(title, [(1, F(E("n1")))])
vis(sub, [(1, F(E("n1")))])
endc = text("theend", "THE END", (0, 0, 0), 0.16, CAPY, rot=(0, 0, 0), extrude=0.0)
endc.parent = cap_root; endc.location = (0, 1.15, 0); endc.visible_shadow = False
vis(endc, [(F(E("c2") + 1.0), END + 10)])

# ---------- render ----------
scn.render.engine = "BLENDER_EEVEE"
ee = scn.eevee
ee.taa_render_samples = 16
ee.use_gtao = True
ee.gtao_distance = 1.0
ee.use_soft_shadows = True
ee.shadow_cascade_size = "2048"
scn.view_settings.look = "AgX - Punchy"
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = os.path.join(HERE, "frames", "f_")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "in_this_town_ep2.blend"))
print("BUILT", END, "frames")
