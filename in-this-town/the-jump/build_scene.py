# "In this town..." Roblox-style first-person story. Run: blender -b -P build_scene.py -- [res_pct]
import bpy, json, math, os, sys, random
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RES_PCT = int(argv[0]) if argv else 60
T = json.load(open(os.path.join(HERE, "timing.json")))
FPS = 24
DUR = T["dur"]
END = int(DUR * FPS)
LN = {L["id"]: L for L in T["lines"]}
def S(i): return LN[i]["start"]
def E(i): return LN[i]["end"]
def F(t): return int(round(t * FPS)) + 1
def NX(i):  # start of next line (or end)
    ids = [L["id"] for L in T["lines"]]
    k = ids.index(i)
    return LN[ids[k + 1]]["start"] if k + 1 < len(ids) else DUR + 1
V = Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, END
scn.render.resolution_x, scn.render.resolution_y = 1080, 1920
scn.render.resolution_percentage = RES_PCT
random.seed(5)

# ---------------- helpers ----------------
MATS = {}
def mat(name, color, rough=0.55, emit=0.0, metal=0.0):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = 0.35
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    MATS[name] = m
    return m

def setmat(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o

def par(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy(); child.parent = parent; child.matrix_world = mw

def smooth(o, angle=40):
    for p in o.data.polygons: p.use_smooth = True
    if hasattr(o.data, "use_auto_smooth"):
        o.data.use_auto_smooth = True; o.data.auto_smooth_angle = math.radians(angle)

def bev(o, w, seg=2):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    md = o.modifiers.new("bev", "BEVEL"); md.width = w; md.segments = seg; md.limit_method = "ANGLE"
    smooth(o)

def box(name, loc, half, m, rot=(0, 0, 0), b=0.0, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = half; setmat(o, m)
    if b: bev(o, b)
    if parent: par(o, parent)
    return o

def cyl(name, loc, r, d, m, rot=(0, 0, 0), parent=None, verts=32, b=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; setmat(o, m); smooth(o, 50)
    if b: bev(o, b, 4)
    if parent: par(o, parent)
    return o

def ball(name, loc, sc, m, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=loc)
    o = bpy.context.object; o.name = name; o.scale = sc; setmat(o, m); smooth(o, 180)
    if parent: par(o, parent)
    return o

def torus(name, loc, R, r, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; setmat(o, m); smooth(o, 180); return o

def cone(name, loc, r, d, m, rot=(0, 0, 0), verts=4, parent=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, depth=d, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; setmat(o, m)
    if parent: par(o, parent)
    return o

def text(name, body, loc, size, m, rz=0, extrude=0.01):
    bpy.ops.object.text_add(location=loc, rotation=(math.radians(90), 0, math.radians(rz)))
    o = bpy.context.object; o.name = name; o.data.body = body; o.data.size = size
    o.data.extrude = extrude; o.data.align_x = "CENTER"; o.data.align_y = "CENTER"
    return setmat(o, m)

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); scn.collection.objects.link(o); o.location = loc
    if parent: o.parent = parent
    return o

def arc(name, pts, m, thick, parent):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = thick; cu.bevel_resolution = 2
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    o = bpy.data.objects.new(name, cu); scn.collection.objects.link(o); cu.materials.append(m)
    par(o, parent); return o

def vis(o, ranges):
    o.hide_render = True; o.keyframe_insert("hide_render", frame=0)
    for s, e in ranges:
        o.hide_render = False; o.keyframe_insert("hide_render", frame=s)
        o.hide_render = True; o.keyframe_insert("hide_render", frame=e)
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"

BLACK = mat("black", (0.02, 0.02, 0.02), 0.4)
WHITE = mat("white", (0.95, 0.95, 0.95))
RED = mat("red", (0.85, 0.08, 0.06))
GOLD = mat("gold", (1.0, 0.75, 0.2), 0.3, metal=0.7)
WOOD = mat("wood", (0.45, 0.27, 0.12), 0.7)
METAL = mat("metal", (0.6, 0.6, 0.65), 0.3, metal=0.9)
SKINS = [mat("skin_y", (0.96, 0.8, 0.25)), mat("skin_l", (1.0, 0.8, 0.62)), mat("skin_m", (0.75, 0.52, 0.35)), mat("skin_d", (0.45, 0.3, 0.2))]

# ---------------- Roblox-style R6 character ----------------
def face_y(x, R=0.3): return -math.sqrt(max(0.0, R * R - x * x)) - 0.004

class Char:
    def __init__(self, name, shirt, pants, skin, arms=None, scale=1.0):
        self.name, self.scale = name, scale
        self.path, self.faces, self.jumps, self.loops, self.poses, self.expr = [], [], [], [], [], []
        self.lookups, self.angry_arms, self.fly_t, self.tilt = [], [], None, []
        r = self.root = empty(name)
        ms, mp = mat(name + "_shirt", shirt), mat(name + "_pants", pants)
        ma = mat(name + "_arms", arms) if arms else (skin if arms is None else ms)
        box(name + "_torso", (0, 0, 1.5), (0.5, 0.25, 0.5), ms, b=0.015, parent=r)
        self.legs, self.arms = [], []
        for sx in (-1, 1):
            hip = empty(f"{name}_hip{sx}", (sx * 0.25, 0, 1.0), r)
            box(f"{name}_leg{sx}", (sx * 0.25, 0, 0.5), (0.249, 0.25, 0.5), mp, b=0.015, parent=hip)
            self.legs.append(hip)
            sh = empty(f"{name}_sh{sx}", (sx * 0.75, 0, 1.95), r)
            box(f"{name}_arm{sx}", (sx * 0.75, 0, 1.5), (0.249, 0.25, 0.5), ma, b=0.015, parent=sh)
            self.arms.append(sh)
        nk = self.neck = empty(name + "_neck", (0, 0, 2.0), r)
        cyl(name + "_head", (0, 0, 2.3), 0.3, 0.6, skin, parent=nk, b=0.11)
        # classic face decal
        for sx in (-1, 1):
            e = ball(f"{name}_eye{sx}", (sx * 0.1, face_y(sx * 0.1) + 0.012, 2.37), (0.035, 0.012, 0.065), BLACK, parent=nk)
            e.rotation_euler = (0, 0, sx * math.atan2(0.1, 0.29))
        self.mouths = {}
        pts = [(x, face_y(x), 2.215 + 0.9 * x * x) for x in [i / 40 * 0.26 - 0.13 for i in range(41)]]
        self.mouths["smile"] = arc(name + "_smile", pts, BLACK, 0.012, nk)
        self.mouths["O"] = ball(name + "_O", (0, face_y(0) + 0.01, 2.2), (0.05, 0.012, 0.065), BLACK, parent=nk)
        pts = [(x, face_y(x), 2.21) for x in [i / 20 * 0.16 - 0.08 for i in range(21)]]
        self.mouths["flat"] = arc(name + "_flat", pts, BLACK, 0.012, nk)
        pts = [(x, face_y(x), 2.2 - 0.9 * x * x) for x in [i / 40 * 0.22 - 0.11 for i in range(41)]]
        self.mouths["frown"] = arc(name + "_frown", pts, BLACK, 0.012, nk)
        self.brows = []
        self.expr.append((-1, "smile"))

    def add_brows(self):
        for sx in (-1, 1):
            pts = [(x, face_y(x) - 0.002, 2.47 + sx * (x - sx * 0.1) * 0.8) for x in [sx * 0.04 + i / 10 * sx * 0.12 for i in range(11)]]
            self.brows.append(arc(f"{self.name}_brow{sx}", pts, BLACK, 0.014, self.neck))

    def cap(self, m, back=True):
        hat = empty(self.name + "_capE", (0, 0, 2.6), self.neck)
        cyl(self.name + "_cap", (0, 0, 2.6), 0.32, 0.14, m, parent=hat, b=0.05)
        box(self.name + "_brim", (0, 0.4 if back else -0.4, 2.56), (0.22, 0.14, 0.02), m, parent=hat)
        return hat

    def hair(self, m, bun=False, long=False):
        box(self.name + "_hairtop", (0, 0.02, 2.58), (0.33, 0.33, 0.07), m, b=0.05, parent=self.neck)
        box(self.name + "_hairback", (0, 0.2, 2.3 if not long else 2.15), (0.32, 0.12, 0.28 if not long else 0.42), m, b=0.04, parent=self.neck)
        if bun: ball(self.name + "_bun", (0, 0.18, 2.75), (0.16, 0.16, 0.13), m, parent=self.neck)

    def tophat(self):
        h = empty(self.name + "_tophatE", (0, 0, 2.58), self.neck)
        cyl(self.name + "_hb", (0, 0, 2.6), 0.48, 0.04, BLACK, parent=h)
        cyl(self.name + "_hc", (0, 0, 2.98), 0.31, 0.76, BLACK, parent=h)
        cyl(self.name + "_hband", (0, 0, 2.7), 0.315, 0.12, RED, parent=h)
        return h

    def finalize(self):
        bpy.context.view_layer.update(); self.root.scale = (self.scale,) * 3

    # choreography
    def place(self, t, p, rz=None):
        p = V((*p, 0)) if len(p) == 2 else V(p)
        self.path.append((t, t, p, p, "place"))
        if rz is not None: self.faces.append((t, math.radians(rz), 0.0))
    def walk(self, t0, t1, p1, kind="walk"):
        p0 = self.pos_at(t0); p1 = V((*p1, p0.z)) if len(p1) == 2 else V(p1)
        self.path.append((t0, t1, p0, p1, kind))
        d = p1 - p0
        if d.xy.length > 0.01: self.faces.append((t0, math.atan2(d.x, -d.y), 0.12))
    def face(self, t, rz, dur=0.12): self.faces.append((t, math.radians(rz), dur))
    def face_to(self, t, xy, dur=0.12):
        d = V(xy) - self.pos_at(t).xy; self.faces.append((t, math.atan2(d.x, -d.y), dur))
    def set_expr(self, t, e): self.expr.append((t, e))
    def seg_at(self, t):
        best = None
        for i, s in enumerate(self.path):
            if s[0] <= t and (best is None or (s[0], i) >= (best[0], best[1])): best = (s[0], i, s)
        return best[2] if best else None
    def pos_at(self, t):
        s = self.seg_at(t)
        if s is None: return V((0, 0, 0))
        if t < s[1]: return s[2].lerp(s[3], (t - s[0]) / (s[1] - s[0]))
        return s[3].copy()
    def walking(self, t):
        s = self.seg_at(t)
        if s and s[4] != "place" and t < s[1]: return s[4]
    def rz_at(self, t):
        prev = 0.0
        for (t0, a, d) in sorted(self.faces, key=lambda f: f[0]):
            if t0 > t: break
            if d > 0 and t < t0 + d:
                u = (t - t0) / d; diff = (a - prev + math.pi) % (2 * math.pi) - math.pi
                return prev + diff * u
            prev = a
        return prev
    def jump_z(self, t):
        z = 0.0
        for (t0, h, d) in self.jumps:
            if t0 <= t < t0 + d: u = (t - t0) / d; z = max(z, h * 4 * u * (1 - u))
        for (t0, t1, per, h, ph) in self.loops:
            if t0 <= t < t1:
                u = ((t - t0) / per + ph) % 1.0
                if u < 0.8: z = max(z, h * 4 * (u / 0.8) * (1 - u / 0.8))
        if self.fly_t is not None and t >= self.fly_t:
            dt = t - self.fly_t; z = 9 * dt + 14 * dt * dt
        return z
    def head(self, t):
        p = self.pos_at(t); return V((p.x, p.y, p.z + self.jump_z(t) + 2.3 * self.scale))
    def front(self, t):
        rz = self.rz_at(t); return V((math.sin(rz), -math.cos(rz), 0))
    def bake(self, frames):
        for f in frames:
            t = (f - 1) / FPS
            p = self.pos_at(t); jz = self.jump_z(t); wk = self.walking(t)
            air = jz > 0.04
            self.root.location = (p.x, p.y, p.z + jz)
            tilt = 0.0
            for (t0, t1, a0, a1) in self.tilt:
                if t0 <= t: tilt = a0 + (a1 - a0) * min(1, (t - t0) / max(1e-6, t1 - t0))
            self.root.rotation_euler = (0, tilt, self.rz_at(t))
            leg = [0.0, 0.0]; ax = [0.0, 0.0]; ay = [0.0, 0.0]
            # idle sway (R6 idle)
            sw = 0.06 * math.sin(t * 2.4 + len(self.name))
            ax = [sw, -sw]
            if wk:
                s = math.sin(t * (13 if wk == "run" else 9.5)) * math.radians(55 if wk == "run" else 48)
                leg = [s, -s]; ax = [-s, s]
            if air:
                ax = [math.radians(-180), math.radians(-180)]; leg = [0, 0]
            for (t0, t1, kind) in self.poses:
                if t0 <= t < t1:
                    if kind == "point": ax[1] = math.radians(-90)
                    if kind == "wave": ax[1] = math.radians(-170); ay[1] = math.radians(-15 + 20 * math.sin(t * 14))
                    if kind == "handsup": ax = [math.radians(-170), math.radians(-170)]; ay = [math.radians(15), math.radians(-15)]
                    if kind == "hold": ax = [math.radians(-70), math.radians(-70)]
                    if kind == "gesture": ax[1] = math.radians(-60 - 30 * math.sin(t * 6)); ax[0] = math.radians(-40 - 25 * math.sin(t * 6 + 1.5))
                    if kind == "angry": ax = [math.radians(-110 - 50 * math.sin(t * 11)), math.radians(-110 - 50 * math.sin(t * 11 + 2))]
                    if kind == "hatoff": ax[1] = math.radians(-175)
                    if kind == "crouch":
                        leg = [math.radians(-35), math.radians(-35)]; self.root.location.z -= 0.15
                    if kind == "fly": ax = [math.radians(-180)] * 2; leg = [0, 0]
                    if kind == "sit": leg = [math.radians(-90), math.radians(-90)]; ax = [math.radians(-80)] * 2
            for i in range(2):
                self.legs[i].rotation_euler = (leg[i], 0, 0); self.legs[i].keyframe_insert("rotation_euler", frame=f)
                self.arms[i].rotation_euler = (ax[i], ay[i], 0); self.arms[i].keyframe_insert("rotation_euler", frame=f)
            hx = 0.0
            for (t0, t1) in self.lookups:
                if t0 <= t < t1: hx = math.radians(-35)
            self.neck.rotation_euler = (hx, 0, 0); self.neck.keyframe_insert("rotation_euler", frame=f)
            self.root.keyframe_insert("location", frame=f); self.root.keyframe_insert("rotation_euler", frame=f)
        # expressions -> visibility
        ex = sorted(self.expr, key=lambda e: e[0])
        for k, o in self.mouths.items():
            rng_ = []
            for i, (t0, e) in enumerate(ex):
                t1 = ex[i + 1][0] if i + 1 < len(ex) else DUR + 2
                if e == k: rng_.append((max(0, F(t0)), F(t1)))
            vis(o, rng_)

def R6(name, shirt, pants, skin, arms=None, scale=1.0):
    return Char(name, shirt, pants, skin, arms, scale)

# ---------------- world ----------------
world = bpy.data.worlds.new("sky"); scn.world = world; world.use_nodes = True
nt = world.node_tree; bgn = nt.nodes["Background"]
co = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); rp = nt.nodes.new("ShaderNodeValToRGB")
nt.links.new(co.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], rp.inputs["Fac"])
rp.color_ramp.elements[0].position = 0.0; rp.color_ramp.elements[0].color = (0.75, 0.88, 1.0, 1)
rp.color_ramp.elements[1].position = 0.4; rp.color_ramp.elements[1].color = (0.2, 0.5, 1.0, 1)
nt.links.new(rp.outputs["Color"], bgn.inputs["Color"]); bgn.inputs["Strength"].default_value = 1.1

GRASS = mat("grass", (0.25, 0.62, 0.2), 0.8)
box("baseplate", (0, 0, -0.25), (120, 120, 0.25), GRASS)
CONC = mat("concrete", (0.55, 0.55, 0.57), 0.8)
ASPH = mat("asphalt", (0.16, 0.16, 0.18), 0.8)
box("plaza", (0, 2, 0.02), (9, 7, 0.02), CONC)
box("road", (0, -7, 0.015), (120, 2.2, 0.015), ASPH)
box("sidewalk", (0, -3.6, 0.03), (120, 1.2, 0.03), CONC)
box("sidewalk2", (0, -10.4, 0.03), (120, 1.2, 0.03), CONC)
for x in range(-60, 61, 6): box(f"stripe{x}", (x, -7, 0.035), (1.2, 0.12, 0.01), mat("yel", (1, 0.85, 0.1)))

# clouds
CLOUD = mat("cloud", (1, 1, 1), 0.9)
for i in range(18):
    cx, cy, cz = random.uniform(-70, 70), random.uniform(20, 90), random.uniform(25, 45)
    for k in range(3):
        box(f"cloud{i}_{k}", (cx + k * random.uniform(2, 4), cy + random.uniform(-1, 1), cz + random.uniform(-1, 1)),
            (random.uniform(2, 4), random.uniform(1.5, 3), random.uniform(0.8, 1.5)), CLOUD)

# stage, podium, town hall
box("stage", (0, 6.2, 0.2), (2.6, 1.6, 0.2), WOOD)
box("podium", (0, 5.2, 0.98), (0.6, 0.35, 0.6), mat("podwood", (0.35, 0.18, 0.08)))
cyl("seal", (0, 4.84, 1.05), 0.32, 0.03, GOLD, rot=(math.radians(90), 0, 0))
HALL = mat("hall", (0.92, 0.9, 0.84))
box("hall", (0, 11.5, 3), (5, 2.2, 3), HALL)
cone("hallroof", (0, 11.5, 7.0), 4.9, 2.0, mat("hroof", (0.6, 0.15, 0.12)), rot=(0, 0, math.radians(45)))
for cx in (-3.6, -1.2, 1.2, 3.6): cyl(f"col{cx}", (cx, 9.0, 2.6), 0.3, 5.2, HALL, verts=16)
box("halldoor", (0, 9.28, 1.2), (0.9, 0.05, 1.2), WOOD)
text("halltxt", "TOWN HALL", (0, 9.2, 5.4), 0.6, mat("dk", (0.12, 0.12, 0.15)), extrude=0.03)

# NO JUMPING signs
SIGN = mat("sign", (0.97, 0.97, 0.95))
def nojump(i, x, y, rz=0, sc=1.0):
    cyl(f"sp{i}", (x, y, 1.1 * sc), 0.07 * sc, 2.2 * sc, METAL, verts=8)
    e = empty(f"sgn{i}", (x, y, 2.4 * sc)); e.rotation_euler = (0, 0, math.radians(rz))
    b = box(f"sb{i}", (x, y - 0.06, 2.4 * sc), (0.7 * sc, 0.03, 0.55 * sc), SIGN); par(b, e)
    t = text(f"st{i}", "NO\nJUMPING", (x, y - 0.1, 2.4 * sc), 0.27 * sc, RED); par(t, e)
    e.rotation_euler = (0, 0, math.radians(rz))
nojump(0, -4.8, 4.0, 15); nojump(1, 5.4, 4.0, -15); nojump(2, 7.0, -2.6, 0); nojump(3, -12, -2.6, 0, 1.3)

# houses / bakery / work
HC = [(0.9, 0.35, 0.3), (0.3, 0.55, 0.9), (0.95, 0.8, 0.35), (0.5, 0.8, 0.45), (0.7, 0.45, 0.85), (1.0, 0.6, 0.3)]
WIN = mat("win", (0.6, 0.85, 1.0), 0.1, metal=0.2)
def house(i, x, y, label=None, col=None):
    h = random.uniform(3.0, 4.2); w = random.uniform(2.2, 2.8)
    box(f"house{i}", (x, y, h / 2), (w, 2.0, h / 2), mat(f"hc{i}", col or HC[i % 6]))
    cone(f"roof{i}", (x, y, h + 1.0), w * 1.5, 2.0, mat("roofm", (0.35, 0.2, 0.15)), rot=(0, 0, math.radians(45)))
    for wx in (-0.55, 0.55): box(f"win{i}{wx}", (x + wx * w, y - 2.02, h * 0.6), (0.35, 0.02, 0.4), WIN)
    box(f"door{i}", (x, y - 2.02, 0.65), (0.4, 0.02, 0.65), WOOD)
    if label: text(f"lab{i}", label, (x, y - 2.06, h - 0.45), 0.42, WHITE, extrude=0.02)
spots = [(-10, 10, None), (10, 10, None), (-17, 9, "BAKERY"), (17, 9, "WORK"), (-24, 11, None), (24, 11, None),
         (-6, -15, None), (2, -15, None), (10, -15, None), (18, -15, None), (-14, -15, None), (26, -15, None), (-22, -15, None)]
for i, (x, y, lab) in enumerate(spots): house(i, x, y, lab)

# trees (blocky)
LEAF = mat("leaf", (0.15, 0.5, 0.15), 0.8)
for i, (tx, ty) in enumerate([(-7, 7), (7, 7), (-13, 2), (17, 4.5), (-26, -1), (20, -3), (-30, 5), (30, 5), (-4, -13), (14, -13)]):
    box(f"trunk{i}", (tx, ty, 1.0), (0.3, 0.3, 1.0), WOOD)
    box(f"leafA{i}", (tx, ty, 2.6), (1.2, 1.2, 0.9), LEAF)
    box(f"leafB{i}", (tx, ty, 3.6), (0.8, 0.8, 0.5), LEAF)

# trampoline (decoration only)
TR = V((-9, 2))
for a in range(4):
    ang = a * math.pi / 2 + 0.6
    cyl(f"trleg{a}", (TR.x + 1.2 * math.cos(ang), TR.y + 1.2 * math.sin(ang), 0.35), 0.05, 0.7, METAL, verts=8)
torus("trrim", (TR.x, TR.y, 0.7), 1.35, 0.1, mat("trblue", (0.1, 0.4, 0.95)))
cyl("trmat", (TR.x, TR.y, 0.68), 1.3, 0.02, BLACK)
cyl("trsp", (TR.x + 1.9, TR.y - 0.4, 0.7), 0.05, 1.4, METAL, verts=8)
box("trsign", (TR.x + 1.9, TR.y - 0.45, 1.5), (0.75, 0.03, 0.35), SIGN)
text("trtxt", "DECORATION\nONLY", (TR.x + 1.9, TR.y - 0.49, 1.5), 0.2, RED)

# basketball court + scoreboard
BC = V((12, 0.5))
box("court", (BC.x, BC.y, 0.04), (3.2, 3.5, 0.02), mat("court", (0.85, 0.5, 0.25)))
cyl("hpole", (BC.x, BC.y + 3.0, 1.7), 0.08, 3.4, METAL, verts=12)
box("board", (BC.x, BC.y + 2.8, 3.4), (0.9, 0.04, 0.6), WHITE)
torus("hoop", (BC.x, BC.y + 2.45, 3.0), 0.32, 0.03, mat("orng", (1, 0.45, 0.05)))
box("score", (BC.x + 2.5, BC.y + 3.2, 3.0), (1.3, 0.05, 0.7), BLACK)
text("scoretxt", "HOME  0\nAWAY 87", (BC.x + 2.5, BC.y + 3.14, 3.0), 0.35, mat("led", (1, 0.3, 0.1), emit=4), extrude=0.0)

# jail
JL = V((-20, -2.5))
box("jailfloor", (JL.x, JL.y, 0.05), (1.6, 1.4, 0.05), mat("jf", (0.4, 0.4, 0.42)))
box("jailroof", (JL.x, JL.y, 3.0), (1.7, 1.5, 0.1), mat("jf", (0.4, 0.4, 0.42)))
for k in range(9): cyl(f"bar{k}", (JL.x - 1.5 + k * 0.375, JL.y - 1.4, 1.5), 0.04, 3.0, METAL, verts=8)
box("jailback", (JL.x, JL.y + 1.4, 1.5), (1.6, 0.08, 1.5), mat("jf2", (0.55, 0.55, 0.58)))
box("jailsign", (JL.x, JL.y - 1.5, 3.4), (1.2, 0.04, 0.3), SIGN)
text("jailtxt", "JAIL (he tripped)", (JL.x, JL.y - 1.55, 3.4), 0.2, RED)

# puddle
PUD = V((3.0, -3.6))
pud = cyl("puddle", (PUD.x, PUD.y, 0.065), 0.7, 0.01, mat("water", (0.15, 0.45, 0.9), 0.05, metal=0.2), verts=48)
pud.scale = (1.5, 0.85, 1)

# ---------------- cast ----------------
me = R6("me", (0.08, 0.08, 0.1), (0.35, 0.35, 0.4), SKINS[1], arms=(0.08, 0.08, 0.1))
me.hair(mat("mehair", (0.1, 0.07, 0.05)))
me_cap = me.cap(mat("mecap", (0.9, 0.1, 0.08)), back=True)
mayor = R6("mayor", (0.06, 0.06, 0.08), (0.06, 0.06, 0.08), SKINS[1], arms=(0.06, 0.06, 0.08))
box("mayor_shirtV", (0, -0.252, 1.75), (0.13, 0.005, 0.25), WHITE, parent=mayor.root)
box("mayor_tie", (0, -0.258, 1.7), (0.05, 0.005, 0.22), RED, parent=mayor.root)
s_ = box("mayor_sash", (0, -0.262, 1.5), (0.09, 0.005, 0.68), mat("sash", (0.9, 0.12, 0.12)), parent=mayor.root); s_.rotation_euler = (0, math.radians(35), 0)
box("mayor_stache", (0, face_y(0) - 0.01, 2.27), (0.13, 0.02, 0.03), mat("gray", (0.6, 0.6, 0.62)), b=0.01, parent=mayor.neck)
mayor.add_brows()
mayor_hat = mayor.tophat()
dave = R6("dave", (1.0, 0.55, 0.1), (0.15, 0.25, 0.65), SKINS[2])
dave.cap(mat("dcap", (0.15, 0.55, 0.2)), back=False)
linda = R6("linda", (0.65, 0.3, 0.8), (0.3, 0.15, 0.4), SKINS[1], arms=(0.65, 0.3, 0.8))
linda.hair(mat("lhair", (0.55, 0.3, 0.1)), bun=True)
bread = box("bread", (0, -0.75, 1.15), (0.36, 0.16, 0.13), mat("bread", (0.9, 0.6, 0.25)), b=0.08, parent=linda.root)
granny = R6("granny", (0.55, 0.75, 0.9), (0.4, 0.4, 0.45), SKINS[1])
granny.hair(mat("ghair", (0.85, 0.85, 0.88)), bun=True)
baby = R6("baby", (0.95, 0.75, 0.85), (0.95, 0.95, 0.95), SKINS[0], scale=0.5)
biker = R6("biker", (0.2, 0.7, 0.7), (0.2, 0.2, 0.25), SKINS[3])
biker.cap(mat("bcap", (0.95, 0.9, 0.2)), back=False)
jailguy = R6("jailguy", (1, 0.55, 0.0), (1, 0.55, 0.0), SKINS[0])
extras = [R6(f"tf{i}", c, p, SKINS[i % 4]) for i, (c, p) in enumerate([((0.2, 0.4, 0.9), (0.2, 0.2, 0.2)), ((0.9, 0.85, 0.2), (0.3, 0.3, 0.4)),
                                                                        ((0.9, 0.3, 0.5), (0.2, 0.3, 0.6)), ((0.3, 0.75, 0.35), (0.4, 0.3, 0.2))])]
extras[1].hair(mat("h1", (0.1, 0.1, 0.1)), long=True); extras[2].hair(mat("h2", (0.9, 0.75, 0.3)))
bd = cone("partyhat", (0, 0, 2.95), 0.18, 0.5, mat("party", (0.95, 0.2, 0.7)), verts=16, parent=extras[0].neck)
PEOPLE = [me, mayor, dave, linda, granny, baby, biker, jailguy] + extras
for c in PEOPLE: c.finalize()

# dog
dog = empty("dog")
DOGM = mat("dogm", (0.75, 0.5, 0.25))
box("dog_body", (0, 0, 0.6), (0.3, 0.55, 0.25), DOGM, b=0.02, parent=dog)
box("dog_head", (0, -0.65, 0.9), (0.25, 0.25, 0.22), DOGM, b=0.02, parent=dog)
box("dog_snout", (0, -0.92, 0.82), (0.12, 0.08, 0.08), mat("dogs", (0.9, 0.8, 0.6)), parent=dog)
box("dog_nose", (0, -1.0, 0.87), (0.05, 0.02, 0.04), BLACK, parent=dog)
for sx in (-1, 1):
    box(f"dog_ear{sx}", (sx * 0.2, -0.6, 1.15), (0.06, 0.08, 0.1), mat("doge", (0.45, 0.28, 0.12)), parent=dog)
    ball(f"dog_eye{sx}", (sx * 0.11, -0.905, 0.98), (0.03, 0.01, 0.04), BLACK, parent=dog)
    for sy in (-1, 1): box(f"dog_leg{sx}{sy}", (sx * 0.2, sy * 0.38, 0.2), (0.08, 0.08, 0.2), DOGM, parent=dog)
box("dog_tail", (0, 0.62, 0.85), (0.05, 0.05, 0.2), DOGM, rot=(math.radians(-30), 0, 0), parent=dog)

# bike
bike = empty("bike")
for sy in (-0.65, 0.65): torus(f"wheel{sy}", (0, sy, 0.42), 0.38, 0.05, BLACK, rot=(0, math.radians(90), 0)).parent = bike
cyl("bframe", (0, 0, 0.7), 0.04, 1.3, mat("bframe", (0.9, 0.1, 0.1)), rot=(math.radians(90), 0, 0), parent=bike)
for o in bike.children: pass

# ---------------- choreography (per-shot staging) ----------------
STAGE = V((0, 6.6, 0.4))
WALKERS = [dave, linda, granny] + extras
# Act A: opening - me in plaza facing camera
baby.place(-1, (-40, -40)); biker.place(-1, (-42, -40))
me.place(-1, (0, 0.5), 0); me.set_expr(-1, "smile")
mayor.place(-1, STAGE, 0); mayor.set_expr(-1, "flat")
mayor.poses.append((S("a3"), NX("a4"), "gesture"))
# a5: walkers stroll stiffly through the plaza
routes = [((-9, 1.5), (9, 1.5)), ((8, -0.5), (-8, -0.5)), ((-7, 3.5), (7, 3.0)), ((6, 2.5), (-7, 2.5)), ((-8, -1.5), (8, -1.8)),
          ((9, 4.2), (-6, 4.0)), ((-3, -2.6), (8, -2.6))]
for c, (a, b) in zip(WALKERS, routes):
    c.place(-1, a, 0); c.set_expr(-1, "flat")
    c.walk(S("a5") - 0.2, S("a6") + 0.5, b)
me.place(S("a5"), (-20, -15))  # off stage
# a6: dave walks to work, linda to bakery
for c in [granny] + extras[1:]:
    c.place(S("a6") - 0.1, (-50 - 2 * extras.index(c) if c in extras else -60, -50))
dave.place(S("a6") - 0.05, (10, -3.6)); dave.walk(S("a6"), S("a6") + 3.0, (16, -3.6))
linda.place(S("a6") + 0.9, (-11, -3.6)); linda.walk(S("a6") + 0.95, S("a7") + 0.5, (-17, -3.6))
linda.poses.append((0, E("b5") - 0.25, "hold"))
# a7: birthday guy standing alone (extras[0] with party hat)
extras[0].place(S("a7"), (-2, -3.6), 0); extras[0].set_expr(S("a7"), "frown")
# a7d: jailguy in jail
jailguy.place(-1, (JL.x, JL.y + 0.2), 0); jailguy.set_expr(-1, "frown")
# a8: me hero shot
me.place(S("a8") - 0.05, (-4, -3.6), 0); me.set_expr(S("a8"), "smile")
me.walk(S("a8b"), S("b1") - 0.05, (-14, -3.6))
# b1-b3: walking home toward puddle (east along sidewalk)
me.place(S("b1") - 0.05, (-6.0, -3.6))
me.walk(S("b1"), E("b1") - 0.3, (PUD.x - 2.2, PUD.y))
me.face(E("b1") - 0.3, -90, 0.12)  # faces +x: rz=-90 -> front=(-1,0)? (see front()) -> use face_to instead
me.faces.pop(); me.face_to(E("b1") - 0.3, (PUD.x + 5, PUD.y))
JT = E("b3") - 0.05
me.walk(S("b3") - 0.15, JT, (PUD.x - 1.6, PUD.y))
me.jumps.append((JT, 3.0, 0.6)); me.walk(JT, JT + 0.6, (PUD.x + 1.7, PUD.y), kind="air")
# b4: town gasps - crowd on the plaza facing me
crowd_spots = [(dave, (0.5, -1.0)), (linda, (2.0, -0.6)), (granny, (4.2, -0.8)), (extras[0], (5.8, -0.9)), (extras[1], (-1.2, -0.4)),
               (extras[2], (3.2, 0.6)), (extras[3], (6.8, 0.4)), (baby, (1.2, -1.1)), (biker, (-2.6, 0.3))]
for c, xy in crowd_spots:
    c.place(S("b4") - 0.4, xy); c.face_to(S("b4") - 0.39, (PUD.x + 1.7, PUD.y), 0.0)
    c.set_expr(S("b4"), "O")
    c.poses.append((S("b4") + 0.05, S("b4") + 1.1, "handsup"))
DROP = E("b5") - 0.25
# b6b: baby crying, dog fainted, biker falling slowly
baby.set_expr(S("b6b"), "O")
dog.location = (-3.5, -1.8, 0)
FAINT = S("b6b") + 1.2
dog.rotation_euler = (0, 0, math.radians(20)); dog.keyframe_insert("rotation_euler", frame=F(FAINT))
dog.rotation_euler = (0, math.radians(90), math.radians(20)); dog.keyframe_insert("rotation_euler", frame=F(FAINT) + 6)
dog.location = (-3.5, -1.8, 0); dog.keyframe_insert("location", frame=F(FAINT))
dog.location = (-3.5, -1.8, -0.05); dog.keyframe_insert("location", frame=F(FAINT) + 6)
BK = V((-8.0, -7.0))
bike.location = (BK.x, BK.y, 0); bike.rotation_euler = (0, 0, math.radians(90))
biker.place(S("b6b") + 1.9, (BK.x, BK.y, 0.15), -90 + 180)
biker.poses.append((S("b6b") + 1.9, NX("b6b"), "sit")); biker.set_expr(S("b6b") + 1.9, "O")
TILT0 = S("b6b") + 2.1
biker.tilt.append((TILT0, NX("b6b"), 0.0, math.radians(85)))
bike.keyframe_insert("rotation_euler", frame=F(TILT0))
bike.rotation_euler = (math.radians(-85), 0, math.radians(90)); bike.keyframe_insert("rotation_euler", frame=F(NX("b6b")))
biker.place(NX("b6b"), (-30, -30))
# Act C: mayor marches over
MP = V((PUD.x + 6.2, PUD.y))
mayor.set_expr(S("c1"), "frown")
mayor.place(S("c1") - 0.05, (PUD.x + 9, PUD.y - 0.1))
mayor.walk(S("c1") + 0.2, S("c1") + 1.2, MP, kind="run")
mayor.face_to(S("c1") + 1.2, (PUD.x + 1.7, PUD.y))
me.face_to(S("c1") + 0.4, MP)
mayor.poses.append((S("c2"), E("c2"), "angry"))
mayor.poses.append((S("c4"), E("c4"), "angry"))
mayor.poses.append((S("c6"), E("c7"), "gesture"))
mayor.set_expr(S("c6"), "flat")
me.set_expr(S("c8"), "flat")
# Act D: jumps
J2 = E("d1") - 0.05
me.jumps.append((J2, 3.0, 0.6))
me.set_expr(S("d1"), "smile")
for c, xy in crowd_spots:
    c.set_expr(S("c1"), "flat")
dave.jumps.append((E("d2") - 0.15, 2.8, 0.6)); dave.set_expr(E("d2") - 0.2, "smile")
linda.jumps.append((E("d3") - 0.15, 2.6, 0.6)); linda.set_expr(E("d3") - 0.2, "smile")
for i, (c, xy) in enumerate(crowd_spots):
    c.set_expr(S("d4"), "smile")
    c.loops.append((E("d4") - 0.1 + 0.13 * i, S("e1"), 0.8, 2.6, 0.0))
me.loops.append((E("d4"), S("e1"), 0.8, 3.0, 0.3))
dog.location = (-3.5, -1.8, 0); dog.keyframe_insert("location", frame=F(S("d4b")) - 1)
dog.rotation_euler = (0, 0, math.radians(20)); dog.keyframe_insert("rotation_euler", frame=F(S("d4b")) - 1)
for k in range(12):
    t0 = S("d4b") + k * 0.6
    for (dt, z) in ((0, 0), (0.15, 1.2), (0.3, 1.6), (0.45, 1.2), (0.59, 0)):
        dog.location = (-3.5, -1.8, z); dog.keyframe_insert("location", frame=F(t0 + dt))
# Act E: hat off + launch
mayor.set_expr(S("e1"), "frown")
mayor.poses.append((S("e1"), S("e1") + 1.6, "angry"))
HAT_T = E("e1") - 1.0
mayor.poses.append((HAT_T - 0.3, HAT_T, "hatoff"))
LAUNCH = E("e2") - 0.05
mayor.poses.append((LAUNCH - 0.3, LAUNCH, "crouch"))
mayor.poses.append((LAUNCH, DUR + 1, "fly"))
mayor.fly_t = LAUNCH
for c, xy in crowd_spots + [(me, None)]:
    c.lookups.append((S("e3b"), S("e4") - 0.05)); c.set_expr(S("e3"), "O")
# ending: me on stage
me.place(S("e4") - 0.05, STAGE, 0); me.set_expr(S("e4"), "smile")
FIN = [(dave, (-2.5, 2.0)), (linda, (-0.8, 2.4)), (granny, (1.0, 2.2)), (extras[0], (2.8, 2.0)), (extras[1], (-4.2, 2.6)),
       (extras[2], (4.4, 2.6)), (extras[3], (-1.8, 0.8)), (baby, (0.6, 1.0)), (biker, (2.2, 0.7))]
for c, xy in FIN:
    c.place(S("e4") - 0.05, xy, 0); c.face(S("e4") - 0.04, 180, 0.0); c.set_expr(S("e4"), "smile")
for i, (c, xy) in enumerate(FIN):
    c.loops.append((S("e6") + 0.4 + 0.1 * i, S("e7"), 0.8, 2.6, 0.0))
me.loops.append((S("e6") + 0.4, S("e7") - 0.1, 0.8, 2.8, 0.0))
# "Wait." -> everyone stares at my hat. "Oh no." -> they step closer
for c, xy in FIN:
    c.set_expr(S("e7") + 0.2, "flat")
    c.walk(S("e8") + 0.3, DUR, (xy[0] * 0.5, xy[1] + 1.6))
me.set_expr(S("e7") + 0.3, "O")
me.lookups.append((S("e7") + 0.2, S("e8") - 0.1))

# props: bread drop + tossed hat
def world_from(c, t, local):
    p = c.pos_at(t); v = V(local) * c.scale; v.rotate(Euler((0, 0, c.rz_at(t))))
    return V((p.x, p.y, p.z + c.jump_z(t))) + v
bread2 = box("bread2", (0, 0, 0), (0.36, 0.16, 0.13), mat("bread", (0.9, 0.6, 0.25)), b=0.08)
b0 = world_from(linda, DROP, (0, -0.75, 1.15))
for k in range(9):
    u = k / 8; bread2.location = (b0.x, b0.y - 0.2 * u, b0.z + (0.13 - b0.z) * u * u)
    bread2.rotation_euler = (0, 0, 0.5 * u); bread2.keyframe_insert("location", frame=F(DROP) + k); bread2.keyframe_insert("rotation_euler", frame=F(DROP) + k)
vis(bread, [(0, F(DROP))]); vis(bread2, [(F(DROP), F(S("d1")))])
hat2 = empty("hat2")
cyl("h2b", (0, 0, 0.02), 0.48, 0.04, BLACK, parent=hat2); cyl("h2c", (0, 0, 0.4), 0.31, 0.76, BLACK, parent=hat2); cyl("h2d", (0, 0, 0.12), 0.315, 0.12, RED, parent=hat2)
h0 = world_from(mayor, HAT_T, (0, 0, 2.95)); h1 = V((h0.x + 1.4, h0.y - 0.9, 0.0))
for k in range(17):
    u = k / 16; pp = h0.lerp(h1, u); pp.z = h0.z * (1 - u) + 1.2 * 4 * u * (1 - u)
    hat2.location = pp; hat2.rotation_euler = (math.radians(180) * u if k < 16 else 0, 0, 0)
    hat2.keyframe_insert("location", frame=F(HAT_T) + k); hat2.keyframe_insert("rotation_euler", frame=F(HAT_T) + k)
for o in mayor_hat.children: vis(o, [(0, F(HAT_T))])
for o in hat2.children: vis(o, [(F(HAT_T), F(S("e4")))])

FRAMES = list(range(1, END + 2))
for c in PEOPLE: c.bake(FRAMES)

# ---------------- lights ----------------
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(42), math.radians(8), math.radians(-30)))
sun = bpy.context.object; sun.data.energy = 3.2; sun.data.color = (1, 0.97, 0.9); sun.data.angle = math.radians(1.5)

# ---------------- camera ----------------
bpy.ops.object.camera_add(); cam = bpy.context.object; scn.camera = cam
cam.data.lens = 26; cam.data.clip_end = 3000
tgt = empty("cam_tgt"); con = cam.constraints.new("TRACK_TO"); con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"

def front_cam(c, dist=3.2, up=0.1, side=0.0, aim=-0.15):
    def fn(t, u):
        h = c.head(t); fr = c.front(t); rt = V((-fr.y, fr.x, 0))
        return h + fr * dist + rt * side + V((0, 0, up)), h + V((0, 0, aim))
    return fn
def behind(c, dist=6.5, up=2.6, aim=0.2):     # Roblox default 3rd-person camera
    def fn(t, u):
        h = c.head(t); fr = c.front(t)
        return h - fr * dist + V((0, 0, up)), h + V((0, 0, aim))
    return fn
def side_follow(c, off=(0, -7, 1.5), aim=1.4):
    def fn(t, u):
        p = c.pos_at(t); return V((p.x, p.y, 0)) + V(off), V((p.x, p.y, aim))
    return fn
def static(loc, target): return lambda t, u: (V(loc), V(target))
def push(l0, t0, l1, t1): return lambda t, u: (V(l0).lerp(V(l1), u), V(t0).lerp(V(t1), u))

PS = V(PUD.xy)
SHOTS = [
    ("a1", front_cam(me, 3.4, 0.2)),
    ("a2", static((-4.8, 1.3, 2.4), (-4.8, 4.0, 2.4))),
    ("a3", push((0, 1.0, 3.0), (0, 6.6, 2.7), (0, 3.2, 2.9), (0, 6.6, 2.7))),
    ("a4", static((0, 0.5, 0.25), (0, 8, 1.6))),
    ("a5", push((0, -12, 4.5), (0, 2, 1.0), (0, -10, 4.0), (0, 2, 1.0))),
    ("a6", lambda t, u: side_follow(dave, (0, -6.5, 2.0))(t, u) if t < S("a6") + 0.95 else side_follow(linda, (0, -6.5, 2.0))(t, u)),
    ("a7", front_cam(extras[0], 3.0, 0.3)),
    ("a7b", push((TR.x + 0.5, TR.y - 6, 2.0), (TR.x + 0.6, TR.y, 0.9), (TR.x + 0.5, TR.y - 4.5, 1.8), (TR.x + 0.6, TR.y, 0.9))),
    ("a7c", push((BC.x + 0.5, BC.y - 5, 1.8), (BC.x + 1.2, BC.y + 3, 2.9), (BC.x + 1.2, BC.y - 3, 2.4), (BC.x + 1.6, BC.y + 3, 3.0))),
    ("a7d", push((JL.x, JL.y - 6, 1.8), (JL.x, JL.y, 1.7), (JL.x, JL.y - 4.2, 1.8), (JL.x, JL.y, 1.9))),
    ("a8", static((-4, -6.6, 1.2), (-4, -3.6, 2.1))),
    ("a8b", side_follow(me)),
    ("b1", behind(me)),
    ("b2", front_cam(me, 3.0, 0.4, side=1.2)),
    ("b3", static((PS.x, PS.y - 7.8, 2.6), (PS.x, PS.y, 2.5))),
    ("b4", static((PS.x + 4.0, PS.y - 4.5, 2.6), (2.6, -0.5, 1.8))),
    ("b5", front_cam(linda, 3.4, 0.0, aim=-0.6)),
    ("b6", front_cam(dave, 3.0)),
    ("b6b", lambda t, u: (front_cam(baby, 2.2, 0.0)(t, u) if t < S("b6b") + 1.0 else
                          static((-3.5 + 1.0, -1.8 - 3.5, 1.2), (-3.5, -1.8, 0.6))(t, u) if t < S("b6b") + 1.9 else
                          static((BK.x + 0.5, BK.y - 5.0, 1.6), (BK.x, BK.y, 1.0))(t, u))),
    ("c1", static((PS.x + 5, PS.y - 8.0, 2.4), (PS.x + 5, PS.y, 1.6))),
    ("c2", front_cam(mayor, 2.6, 0.0, side=1.1)),
    ("c3", front_cam(me, 2.6, 0.1, side=-1.1)),
    ("c4", front_cam(mayor, 2.2, 0.0, side=0.9)),
    ("c5", static((PS.x + 4.0, PS.y - 8.0, 2.2), (PS.x + 4.0, PS.y, 1.8))),
    ("c6", lambda t, u: front_cam(mayor, 3.0 - 0.8 * u, 0.0, side=1.0 - 0.3 * u)(t, u)),
    ("c7", front_cam(mayor, 2.0, 0.0, side=0.7)),
    ("c8", front_cam(me, 2.2, 0.0, side=-0.8)),
    ("c8b", lambda t, u: front_cam(me, 2.2 - 0.6 * u, 0.0, side=-0.8 + 0.3 * u)(t, u)),
    ("d1", static((PS.x + 1.7, PS.y - 7.5, 2.5), (PS.x + 1.7, PS.y, 2.4))),
    ("d2", front_cam(dave, 5.0, 0.5, aim=-0.5)),
    ("d3", front_cam(linda, 5.0, 0.5, aim=-0.5)),
    ("d4", static((3.0, -9.5, 3.5), (3.0, -1.0, 2.0))),
    ("d4b", lambda t, u: (front_cam(granny, 5.0, 0.5, aim=-0.4)(t, u) if t < S("d4b") + 1.1 else
                          front_cam(baby, 3.5, 0.3, aim=-0.2)(t, u) if t < S("d4b") + 2.1 else
                          static((-3.5, -6.0, 1.4), (-3.5, -1.8, 1.0))(t, u))),
    ("e1", front_cam(mayor, 3.4, 0.2, side=1.4)),
    ("e2", lambda t, u: (V((MP.x - 2.0, MP.y - 6.5, 1.0)), mayor.head(t) if mayor.head(t).z < 80 else V((MP.x, MP.y, 80)))),
    ("e3", static((MP.x + 1, MP.y - 3, 0.6), (MP.x, MP.y + 4, 40))),
    ("e3b", static((2.5, -8.0, 0.6), (2.5, -1.0, 2.6))),
    ("e4", static((0, 1.2, 2.9), (0, 6.6, 2.6))),
    ("e5", push((0, 1.2, 2.9), (0, 6.6, 2.6), (0, 3.0, 2.9), (0, 6.6, 2.65))),
    ("e6", static((0, -7, 4.5), (0, 3.5, 2.0))),
    ("e7", front_cam(me, 2.3, 0.6, aim=0.15)),
    ("e8", static((0, -3.0, 2.2), (0, 4.0, 2.4))),
]
ids = [L["id"] for L in T["lines"]]
seg = []
for i, (sid, fn) in enumerate(SHOTS):
    a = 0 if i == 0 else S(sid) - 0.15
    b = (S(SHOTS[i + 1][0]) - 0.15) if i + 1 < len(SHOTS) else DUR + 1
    seg.append((a, b, fn))
prev = None
for f in FRAMES:
    t = (f - 1) / FPS
    for (a, b, fn) in seg:
        if a <= t < b: loc, target = fn(t, (t - a) / max(1e-6, b - a)); break
    cam.location = loc; tgt.location = target
    cam.keyframe_insert("location", frame=f); tgt.keyframe_insert("location", frame=f)

# ---------------- render ----------------
scn.render.engine = "BLENDER_EEVEE"
ee = scn.eevee; ee.taa_render_samples = 8; ee.use_gtao = True; ee.gtao_distance = 0.8
ee.use_soft_shadows = True; ee.shadow_cascade_size = "2048"
scn.view_settings.view_transform = "Standard"; scn.view_settings.exposure = -0.15
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = os.path.join(HERE, "frames", "f_")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "in_this_town.blend"))
print("BUILT", END)
