/**
 * SunReveal — milestone 5: the revelation.
 *
 * Listens for SunAlignment's lock. The sun's ray is one unbroken line: SunAlignment's shaft
 * runs from the disc to the ray's entry point in the doorway, and from there this script
 * grows the inside ray down the temple axis to the three lit statues. The ray grows from the
 * doorway and stays lit behind its tip (nothing travels away leaving darkness), with a lit
 * strip on the floor under it and a soft glow where the light enters the doorway. It widens
 * a little on its way, so at the end it covers exactly the three lit statues and not Ptah.
 * As the ray starts, the outside shaft is brought up to the same brightness. The ray is a soft
 * wide layer plus a narrow bright core (two crossed pairs of quads, additive, low overdraw).
 * The light falls on the statues rather than making them glow: a warm spotlight from the doorway
 * covers exactly the three lit statues (never Ptah) and rises with them in order, with a gentle
 * gold tint and emissive, a faint rim halo and a floor pool. When the light arrives the
 * sanctuary statues ease up one by one, in the order given by `statueOrder`: the emissive
 * rises, the base colour shifts from sandstone toward gold, a soft additive halo card
 * glows behind the statue and a small warm pool lights the floor in front of it (all on
 * the same 1 s rise). Ptah stays at the base level set by InteriorLift, neutral, with no
 * halo or pool. The lit state holds. `onRevealComplete()` fires once when the last statue is fully lit
 * (milestone 6 narration hooks in there).
 *
 * Timeline from lock (defaults): 0 s caption, 2 s beam starts, 10 s light reaches the
 * sanctuary, statues at 10.0 / 10.8 / 11.6 s each rising over 1 s, complete at 12.6 s.
 * The actual times are printed when `debugLog` is on and once at completion.
 */

import { SunAlignment, SHAFT_WIDTH_CM } from './SunAlignment';
import { InteriorLift } from './InteriorLift';

// ---------------------------------------------------------------------------
// Tunables (seconds, centimetres)
// ---------------------------------------------------------------------------

/** Delay from lock to the light entering the doorway (the "stand up" caption time). */
const START_DELAY_SEC = 2.0;
/** Time the ray takes to grow from the doorway to the sanctuary. */
const TRAVEL_SEC = 8.0;
/** Beam fade-in at the start of the travel. */
const BEAM_FADE_IN_SEC = 0.6;
/** Gap between successive statues lighting up. */
const STATUE_GAP_SEC = 0.8;
/** Time each statue takes to ease from base to lit. */
const STATUE_RISE_SEC = 1.0;
/** The floor ring fades out over this time once the beam starts. */
const RING_FADE_SEC = 1.5;
/** The doorway glow rises over this time from lock (the shaft reaches the door at lock). */
const DOOR_GLOW_SEC = 0.6;
/** Brightness of the floor strip relative to the ray. */
const FLOOR_STRIP_GLOW = 0.7;
/** The floor strip sits this far above the floor (cm) so it never z-fights with it. */
const FLOOR_STRIP_LIFT_CM = 0.12;
/** Width of the ray's bright core relative to the ray. */
const RAY_CORE_WIDTH = 0.35;
/** Halo cards are only a faint rim; the floor pools stay a little stronger. */
const HALO_LEVEL = 0.3;
const POOL_LEVEL = 0.8;
/** Spotlight on the lit statues: peak intensity and the cone's soft edge (inner = outer x this). */
const SPOT_INTENSITY = 6.0;
const SPOT_INNER_RATIO = 0.6;
/** Peak intensity of the sanctuary's warm fill. */
const WARM_INTENSITY = 1.6;

// ---------------------------------------------------------------------------

interface StatueEntry {
  name: string;
  mat: Material | null;
  baseColor: vec4 | null;
  halo: SceneObject | null;
  haloPasses: Pass[];
  haloBase: vec4[];
  pool: SceneObject | null;
  poolPasses: Pass[];
  poolBase: vec4[];
}

@component
export class SunReveal extends BaseScriptComponent {
  /** The alignment script: gives the lock event and temple-space helpers. */
  @input alignment: SunAlignment;

  /** The interior lift script: owns the statue materials and the base emissive. */
  @input lift: InteriorLift;

  /** Beam root with two children (RenderMeshVisual + soft-edged additive material): the first
   * becomes the floor strip, the second the ray. Their meshes are built here, in world space. */
  @input beam: SceneObject;

  /** Soft radial glow card (unit plane, additive) placed at the ray's entry point in the doorway. */
  @input doorwayGlow: SceneObject;

  /** The doorway sill (start of the floor strip), in cm along the temple's own axes. */
  @input('vec3', '{0, 1.7, 23.7}')
  doorwayOffset: vec3;

  /** Height (cm above the statues' base) where the ray meets the lit statues: about chest height. */
  @input
  rayTargetHeight: number = 2.2;

  /** Width (cm) of one statue, added to the spread of the lit statues for the ray's end width. */
  @input
  statueWidth: number = 1.6;

  /** Diameter (cm) of the doorway glow. */
  @input
  doorwayGlowSize: number = 7;

  /** Warm spotlight that falls on the lit statues (a Spot LightSource), aimed from the doorway. */
  @input('Component.LightSource')
  @allowUndefined
  sanctuaryLight: LightSource;

  /**
   * Optional warm fill (a point light in the sanctuary, on the interior light layer only, Ptah's
   * layer excluded): the sanctuary warms gradually as the statues light. Off before the reveal.
   */
  @input('Component.LightSource')
  @allowUndefined
  sanctuaryWarm: LightSource;

  /** Statues in lighting order (names of the temple objects). Ptah is never listed. */
  @input
  statueOrder: string = 'Statue_RaHorakhty,Statue_Ramesses,Statue_AmunRa';

  /** Emissive of a lit statue: about 2x the base (0.14, 0.11, 0.07) in luminance, warmer. */
  @input('vec3', '{0.30, 0.22, 0.11}')
  litEmissive: vec3;

  /** Base-colour multiplier of a lit statue: shifts the sandstone toward gold (1,1,1 = no tint). */
  @input('vec3', '{1.0, 0.82, 0.45}')
  goldTint: vec3;

  /** Parent of the per-statue glow objects, named "Halo <i>" and "Pool <i>" for statue index i. */
  @input glowRoot: SceneObject;

  /** Halo card width and height (cm); it stands behind the statue, facing the entrance. */
  @input
  haloWidth: number = 5;
  @input
  haloHeight: number = 6;
  /** Halo card tilt back from vertical (degrees) so it also reads from above. */
  @input
  haloTilt: number = 25;
  /** Diameter of the floor pool in front of each lit statue (cm). */
  @input
  poolSize: number = 3;
  /** Front-to-back depth of a statue (cm); the halo sits just behind it, the pool just in front. */
  @input
  statueDepth: number = 1.4;

  /** Print the phase times (relative to lock). */
  @input
  debugLog: boolean = false;

  /** >= 0 freezes the sequence clock at that many seconds after lock (for screenshots). */
  @input
  debugFreezeAt: number = -1;

  private running = false;
  private complete = false;
  private fading = false;
  private pendingBegin = false;
  private fadeSec = 0;
  private fadeLeft = 0;
  private fadeFromStatues: number[] = [];
  private fadeFromGlow = 0;
  private fadeFromDoor = 0;
  private t = 0;
  private lockTime = 0;
  private loggedPhases: { [phase: string]: boolean } = {};
  private completeListeners: (() => void)[] = [];

  private beamPasses: Pass[] = [];
  private beamBase: vec4[] = [];
  private doorPasses: Pass[] = [];
  private doorBase: vec4[] = [];
  private stripPasses: Pass[] = [];
  private stripBase: vec4[] = [];
  private rayMesh: MeshBuilder | null = null;
  private stripMesh: MeshBuilder | null = null;
  private rayObj: SceneObject | null = null;
  private stripObj: SceneObject | null = null;
  private rayTarget: vec3 | null = null;
  private rayEndWidth = 5;
  private litNow: { [name: string]: number } = {};
  private statues: StatueEntry[] = [];
  private glowPlaced = false;

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => this.start());
    this.createEvent('UpdateEvent').bind(() => this.update());
  }

  /** Milestone 6 hook: called once when the last statue is fully lit. */
  onRevealComplete(listener: () => void) {
    this.completeListeners.push(listener);
  }

  isComplete(): boolean {
    return this.complete;
  }

  /** Seconds since lock while the sequence runs (frozen value when debugFreezeAt >= 0). */
  getSequenceTime(): number {
    return this.t;
  }

  /** Milestone 6: ease everything back to the pre-lock state over `sec` seconds, then reset(). */
  fadeOut(sec: number) {
    if (this.fading) return;
    this.fadeFromStatues = this.statues.map((s) => this.litFraction(s));
    this.fadeFromGlow = this.clamp((this.t - START_DELAY_SEC) / BEAM_FADE_IN_SEC, 0, 1);
    this.fadeFromDoor = this.clamp(this.t / DOOR_GLOW_SEC, 0, 1);
    this.running = false;
    this.fading = true;
    this.fadeSec = Math.max(sec, 0.01);
    this.fadeLeft = this.fadeSec;
  }

  /** Put everything back to the pre-lock state (Try again, milestone 6). */
  reset() {
    this.running = false;
    this.complete = false;
    this.fading = false;
    this.pendingBegin = false;
    this.t = 0;
    this.loggedPhases = {};
    this.setRayGlow(0, 0);
    if (this.beam) this.beam.enabled = false;
    if (this.doorwayGlow) this.doorwayGlow.enabled = false;
    const base = this.lift ? this.lift.getEmissive() : new vec3(0.14, 0.11, 0.07);
    for (const s of this.statues) this.setStatueLit(s, base, 0);
    if (this.alignment) this.alignment.setCueFade(1, 1);
  }

  private start() {
    if (!this.alignment || !this.lift || !this.beam || !this.doorwayGlow || this.beam.getChildrenCount() < 2) {
      print('SunReveal: alignment, lift, beam (with two children) and doorwayGlow must be assigned');
      return;
    }
    // The meshes are written in world space, so the beam and its children carry no transform.
    for (const o of [this.beam, this.beam.getChild(0), this.beam.getChild(1)]) {
      const tr = o.getTransform();
      if (o === this.beam) {
        tr.setWorldPosition(vec3.zero());
        tr.setWorldRotation(quat.quatIdentity());
        tr.setWorldScale(vec3.one());
      } else {
        tr.setLocalPosition(vec3.zero());
        tr.setLocalRotation(quat.quatIdentity());
        tr.setLocalScale(vec3.one());
      }
    }
    this.stripObj = this.beam.getChild(0);
    this.rayObj = this.beam.getChild(1);
    this.stripMesh = this.makeQuadsMesh(this.stripObj, 1);
    this.rayMesh = this.makeQuadsMesh(this.rayObj, 4);
    this.stripPasses = this.collectPasses(this.stripObj);
    this.stripBase = this.stripPasses.map((p) => p.baseColor as vec4);
    this.beamPasses = this.collectPasses(this.rayObj);
    this.beamBase = this.beamPasses.map((p) => p.baseColor as vec4);
    this.doorPasses = this.collectPasses(this.doorwayGlow);
    this.doorBase = this.doorPasses.map((p) => p.baseColor as vec4);
    this.setRayGlow(0, 0);
    this.beam.enabled = false;
    this.doorwayGlow.enabled = false;
    this.statues = this.statueOrder
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
      .map((name, i) => {
        const halo = this.findGlow('Halo ' + i);
        const pool = this.findGlow('Pool ' + i);
        const haloPasses = this.ownPasses(halo);
        const poolPasses = this.ownPasses(pool);
        const entry: StatueEntry = {
          name,
          mat: null as Material | null,
          baseColor: null as vec4 | null,
          halo,
          haloPasses,
          haloBase: haloPasses.map((p) => p.baseColor as vec4),
          pool,
          poolPasses,
          poolBase: poolPasses.map((p) => p.baseColor as vec4),
        };
        this.setGlow(entry.haloPasses, entry.haloBase, 0);
        this.setGlow(entry.poolPasses, entry.poolBase, 0);
        if (halo) halo.enabled = false;
        if (pool) pool.enabled = false;
        return entry;
      });
    this.alignment.onAligned(() => this.begin());
  }

  private begin() {
    if (this.fading) {
      // Locked again while the reset fade runs: start as soon as the fade has finished.
      this.pendingBegin = true;
      return;
    }
    if (this.running || this.complete) return;
    // InteriorLift resolved the materials at its own start; fetch the handles now.
    for (const s of this.statues) {
      s.mat = this.lift.getMaterial(s.name);
      if (!s.mat) print('SunReveal: no material for ' + s.name);
      else if (!s.baseColor) s.baseColor = this.readTint(s.mat);
    }
    if (!this.glowPlaced) this.placeGlow();
    this.running = true;
    this.t = 0;
    this.lockTime = getTime();
    this.log('lock');
  }

  private update() {
    if (this.fading) {
      this.fadeLeft -= getDeltaTime();
      const f = this.clamp(this.fadeLeft / this.fadeSec, 0, 1);
      const base = this.lift.getEmissive();
      for (let i = 0; i < this.statues.length; i++) this.setStatueLit(this.statues[i], base, this.fadeFromStatues[i] * f);
      this.setRayGlow(this.fadeFromGlow * f, this.fadeFromDoor * f);
      this.alignment.setShaftBoost(this.fadeFromGlow * f);
      if (f <= 0) {
        this.reset();
        if (this.pendingBegin) {
          this.pendingBegin = false;
          this.begin();
        }
      }
      return;
    }
    if (!this.running) return;
    if (this.debugFreezeAt >= 0) {
      this.t = this.debugFreezeAt;
    } else {
      this.t += getDeltaTime();
    }
    const t = this.t;

    // --- The ray: doorway glow from lock, then the inside ray grows to the statues ---
    const travel = this.clamp((t - START_DELAY_SEC) / TRAVEL_SEC, 0, 1);
    const started = t >= START_DELAY_SEC;
    const glow = this.clamp((t - START_DELAY_SEC) / BEAM_FADE_IN_SEC, 0, 1);
    const door = this.clamp(t / DOOR_GLOW_SEC, 0, 1);
    this.placeDoorwayGlow();
    this.beam.enabled = started;
    this.setRayGlow(glow, door);
    this.alignment.setShaftBoost(glow);
    if (started) {
      this.placeRay(this.smooth(travel));
      // The floor ring has done its job: fade it while the light travels.
      const ringFade = 1 - this.clamp((t - START_DELAY_SEC) / RING_FADE_SEC, 0, 1);
      this.alignment.setCueFade(ringFade, 1);
      if (travel > 0 && travel < 1) this.log('travel');
      if (travel >= 1) this.log('arrived');
    }

    // --- Statues ---
    const base = this.lift.getEmissive();
    const arrival = START_DELAY_SEC + TRAVEL_SEC;
    let allLit = this.statues.length > 0;
    for (let i = 0; i < this.statues.length; i++) {
      const s = this.statues[i];
      const p = this.clamp((t - (arrival + i * STATUE_GAP_SEC)) / STATUE_RISE_SEC, 0, 1);
      this.setStatueLit(s, base, this.smooth(p));
      if (p > 0) this.log('lit ' + s.name);
      if (p < 1) allLit = false;
    }

    if (allLit && !this.complete) {
      this.complete = true;
      this.running = this.debugFreezeAt >= 0; // keep refreshing a frozen frame
      print('REVEAL_COMPLETE +' + t.toFixed(2) + ' s after lock (wall ' + (getTime() - this.lockTime).toFixed(2) + ' s)');
      for (const l of this.completeListeners) l();
    }
  }

  // --- placement ---

  /** A mesh of `quads` quads (4 vertices each, position + normal + uv), filled in by setQuad. */
  private makeQuadsMesh(obj: SceneObject, quads: number): MeshBuilder | null {
    const rmv = obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
    if (!rmv) return null;
    const mb = new MeshBuilder([
      { name: 'position', components: 3 },
      { name: 'normal', components: 3 },
      { name: 'texture0', components: 2 },
    ]);
    mb.topology = MeshTopology.Triangles;
    mb.indexType = MeshIndexType.UInt16;
    const verts: number[] = [];
    const idx: number[] = [];
    for (let q = 0; q < quads; q++) {
      for (const uv of [[0, 0], [1, 0], [1, 1], [0, 1]]) verts.push(0, 0, 0, 0, 1, 0, uv[0], uv[1]);
      const b = q * 4;
      idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
    }
    mb.appendVerticesInterleaved(verts);
    mb.appendIndices(idx);
    mb.updateMesh();
    rmv.mesh = mb.getMesh();
    return mb;
  }

  /** Quad q from a (start) to b (end): half-widths ha / hb along `side`. u runs across, v along. */
  private setQuad(mb: MeshBuilder, q: number, a: vec3, b: vec3, side: vec3, ha: number, hb: number, n: vec3) {
    const pts = [a.sub(side.uniformScale(ha)), a.add(side.uniformScale(ha)), b.add(side.uniformScale(hb)), b.sub(side.uniformScale(hb))];
    const uvs = [[0, 0], [1, 0], [1, 1], [0, 1]];
    for (let i = 0; i < 4; i++) {
      mb.setVertexInterleaved(q * 4 + i, [pts[i].x, pts[i].y, pts[i].z, n.x, n.y, n.z, uvs[i][0], uvs[i][1]]);
    }
  }

  /**
   * The inside ray from the entry point to `grow` (0..1) of the way to the statues: two crossed
   * quads, widening from the shaft's width to the lit statues' spread; and the floor strip
   * under it from the sill to below the ray's tip.
   */
  private placeRay(grow: number) {
    if (!this.rayMesh || !this.stripMesh || !this.rayTarget) return;
    const from = this.alignment.getRayEntry();
    const tip = vec3.lerp(from, this.rayTarget, Math.max(grow, 0.01));
    const dir = this.rayTarget.sub(from).normalize();
    const side = dir.cross(vec3.up()).normalize();
    const upv = side.cross(dir).normalize();
    const w0 = SHAFT_WIDTH_CM;
    const wTip = w0 + (this.rayEndWidth - w0) * grow;
    this.setQuad(this.rayMesh, 0, from, tip, side, w0 / 2, wTip / 2, upv);
    this.setQuad(this.rayMesh, 1, from, tip, upv, w0 / 2, w0 / 2, side);
    const c = RAY_CORE_WIDTH;
    this.setQuad(this.rayMesh, 2, from, tip, side, (w0 * c) / 2, (wTip * c) / 2, upv);
    this.setQuad(this.rayMesh, 3, from, tip, upv, (w0 * c) / 2, (w0 * c) / 2, side);
    this.rayMesh.updateMesh();
    const floorY = this.alignment.templePoint(this.doorwayOffset).y + FLOOR_STRIP_LIFT_CM;
    const sill = this.alignment.templePoint(this.doorwayOffset);
    const a = new vec3(sill.x, floorY, sill.z);
    const b = new vec3(tip.x, floorY, tip.z);
    const flatSide = b.sub(a).cross(vec3.up()).normalize();
    this.setQuad(this.stripMesh, 0, a, b, flatSide, w0 * 0.45, wTip * 0.45, vec3.up());
    this.stripMesh.updateMesh();
  }

  /** The soft glow where the light enters: at the entry point, facing out of the doorway. */
  private placeDoorwayGlow() {
    const tr = this.doorwayGlow.getTransform();
    const axis = this.alignment.getAxis();
    tr.setWorldPosition(this.alignment.getRayEntry().add(axis.uniformScale(0.3)));
    tr.setWorldRotation(quat.lookAt(vec3.up(), axis));
    tr.setWorldScale(new vec3(this.doorwayGlowSize, 1, this.doorwayGlowSize));
  }

  /** Ray (and shaft-matched) brightness, floor strip at FLOOR_STRIP_GLOW of it, doorway glow. */
  private setRayGlow(ray: number, door: number) {
    this.setGlow(this.beamPasses, this.beamBase, ray);
    this.setGlow(this.stripPasses, this.stripBase, ray * FLOOR_STRIP_GLOW);
    this.setGlow(this.doorPasses, this.doorBase, door);
    if (this.doorwayGlow) this.doorwayGlow.enabled = door > 0.001;
  }

  /**
   * Where the ray ends: in front of the lit statues (their centres averaged), at chest height,
   * and its end width: their spread across the axis plus one statue, so it touches all three
   * lit statues and stops short of Ptah.
   */
  private placeRayTarget() {
    const fwd = this.alignment.templeToWorld(new vec3(0, 0, 1));
    const side = this.alignment.templeToWorld(new vec3(1, 0, 0));
    let sum = vec3.zero();
    let lo = Number.MAX_VALUE;
    let hi = -Number.MAX_VALUE;
    let base = Number.MAX_VALUE;
    let n = 0;
    for (const s of this.statues) {
      const obj = this.lift.getObject(s.name);
      const rmv = obj ? (obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null) : null;
      if (!rmv) continue;
      const c = rmv.worldAabbMin().add(rmv.worldAabbMax()).uniformScale(0.5);
      sum = sum.add(c);
      lo = Math.min(lo, c.dot(side));
      hi = Math.max(hi, c.dot(side));
      base = Math.min(base, rmv.worldAabbMin().y);
      n++;
    }
    if (n === 0) return;
    const c = sum.uniformScale(1 / n);
    const front = c.add(fwd.uniformScale(this.statueDepth * 0.5));
    this.rayTarget = new vec3(front.x, base + this.rayTargetHeight, front.z);
    this.rayEndWidth = hi - lo + this.statueWidth;
    this.alignment.setRayTarget(this.rayTarget);
    this.placeSpot();
  }

  private litFractionNow(s: StatueEntry): number {
    return this.litNow[s.name] || 0;
  }

  /** Aim the spotlight from the doorway entry at the lit statues; its cone just covers them. */
  private placeSpot() {
    if (!this.sanctuaryLight || !this.rayTarget) return;
    const from = this.alignment.getRayEntry();
    const toTarget = this.rayTarget.sub(from);
    const tr = this.sanctuaryLight.getSceneObject().getTransform();
    tr.setWorldPosition(from);
    tr.setWorldRotation(quat.lookAt(toTarget.normalize(), vec3.up()));
    const outer = (Math.atan((this.rayEndWidth / 2 + 0.2) / toTarget.length) * 180) / Math.PI;
    this.sanctuaryLight.outerConeAngleDegrees = outer;
    this.sanctuaryLight.innerConeAngleDegrees = outer * SPOT_INNER_RATIO;
  }

  /** Current lit fraction of a statue in the running sequence (0 = base, 1 = fully lit). */
  private litFraction(s: StatueEntry): number {
    const i = this.statues.indexOf(s);
    const p = this.clamp((this.t - (START_DELAY_SEC + TRAVEL_SEC + i * STATUE_GAP_SEC)) / STATUE_RISE_SEC, 0, 1);
    return this.smooth(p);
  }

  /** Drive one statue's emissive, gold tint, halo and pool to lit fraction k (0 = base). */
  private setStatueLit(s: StatueEntry, base: vec3, k: number) {
    this.litNow[s.name] = k;
    if (s.mat) {
      s.mat.mainPass.emissiveFactor = vec3.lerp(base, this.litEmissive, k);
      if (s.baseColor) {
        const b = s.baseColor;
        const tint = vec3.lerp(new vec3(1, 1, 1), this.goldTint, k);
        this.writeTint(s.mat, new vec4(b.x * tint.x, b.y * tint.y, b.z * tint.z, b.w));
      }
    }
    if (s.halo) s.halo.enabled = k > 0;
    if (s.pool) s.pool.enabled = k > 0;
    this.setGlow(s.haloPasses, s.haloBase, k * HALO_LEVEL);
    this.setGlow(s.poolPasses, s.poolBase, k * POOL_LEVEL);
    this.updateSpot();
  }

  /** The spotlight follows the statues' lit fractions (so it rises in their order). */
  private updateSpot() {
    let sum = 0;
    for (const st of this.statues) sum += this.litFractionNow(st);
    const k = this.statues.length > 0 ? sum / this.statues.length : 0;
    if (this.sanctuaryLight) {
      this.sanctuaryLight.intensity = SPOT_INTENSITY * k;
      this.sanctuaryLight.getSceneObject().enabled = k > 0.001;
    }
    if (this.sanctuaryWarm) {
      // eased so the room warms after the statues catch the light, not in step with them
      const w = k * k * (3 - 2 * k);
      this.sanctuaryWarm.intensity = WARM_INTENSITY * w;
      this.sanctuaryWarm.getSceneObject().enabled = w > 0.001;
    }
  }

  /** Put each halo card behind its statue and each pool on the floor in front, from the statue bounds. */
  private placeGlow() {
    this.placeRayTarget();
    const rot = this.temple().getWorldRotation();
    const fwd = this.alignment.templeToWorld(new vec3(0, 0, 1)); // toward the entrance
    const haloRot = rot.multiply(quat.angleAxis((90 - this.haloTilt) * Math.PI / 180, vec3.right()));
    for (const s of this.statues) {
      const obj = this.lift.getObject(s.name);
      const rmv = obj ? (obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null) : null;
      if (!rmv) continue;
      const lo = rmv.worldAabbMin();
      const hi = rmv.worldAabbMax();
      const centre = lo.add(hi).uniformScale(0.5);
      const depth = this.statueDepth; // the world AABB is inflated by the temple's rotation, so use the known depth
      if (s.halo) {
        const t = s.halo.getTransform();
        t.setWorldPosition(new vec3(centre.x, lo.y + this.haloHeight * 0.5 - 0.3, centre.z).sub(fwd.uniformScale(depth * 0.5 + 0.3)));
        t.setWorldRotation(haloRot);
        t.setLocalScale(new vec3(this.haloWidth, 1, this.haloHeight));
      }
      if (s.pool) {
        const t = s.pool.getTransform();
        t.setWorldPosition(new vec3(centre.x, lo.y + 0.2, centre.z).add(fwd.uniformScale(depth * 0.5 + this.poolSize * 0.5)));
        t.setWorldRotation(rot);
        t.setLocalScale(new vec3(this.poolSize, 1, this.poolSize));
      }
      if (this.debugLog) print('SunReveal: glow for ' + s.name + ' at ' + centre.toString() + ' depth ' + depth.toFixed(2));
    }
    this.glowPlaced = true;
  }

  /** The glTF PBR material exposes its colour as baseColorFactor; plain materials use baseColor. */
  private tintParam(mat: Material): string {
    const pass = mat.mainPass as any;
    return pass.baseColorFactor !== undefined ? 'baseColorFactor' : 'baseColor';
  }

  private readTint(mat: Material): vec4 | null {
    const v = (mat.mainPass as any)[this.tintParam(mat)];
    return v ? (v as vec4) : null;
  }

  private writeTint(mat: Material, v: vec4) {
    (mat.mainPass as any)[this.tintParam(mat)] = v;
  }

  private temple(): Transform {
    return this.alignment.temple.getTransform();
  }

  /** Child of glowRoot by name; its material is cloned so each glow fades on its own. */
  private findGlow(name: string): SceneObject | null {
    if (!this.glowRoot) return null;
    const n = this.glowRoot.getChildrenCount();
    for (let i = 0; i < n; i++) {
      const c = this.glowRoot.getChild(i);
      if (c.name !== name) continue;
      const rmv = c.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
      if (rmv && rmv.mainMaterial) rmv.mainMaterial = rmv.mainMaterial.clone();
      return c;
    }
    print('SunReveal: no glow object named "' + name + '" under ' + this.glowRoot.name);
    return null;
  }

  private ownPasses(obj: SceneObject | null): Pass[] {
    if (!obj) return [];
    const rmv = obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
    return rmv && rmv.mainMaterial ? [rmv.mainMaterial.mainPass] : [];
  }

  // --- helpers ---

  private log(phase: string) {
    if (!this.debugLog || this.loggedPhases[phase]) return;
    this.loggedPhases[phase] = true;
    print('SunReveal: ' + phase + ' at +' + this.t.toFixed(2) + ' s');
  }

  /** Additive materials: scale colour and alpha together. */
  private setGlow(passes: Pass[], base: vec4[], k: number) {
    const g = this.clamp(k, 0, 1);
    for (let i = 0; i < passes.length; i++) {
      const b = base[i];
      passes[i].baseColor = new vec4(b.x * g, b.y * g, b.z * g, g);
    }
  }

  private collectPasses(obj: SceneObject | null): Pass[] {
    const out: Pass[] = [];
    if (!obj) return out;
    const rmv = obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
    if (rmv && rmv.mainMaterial) out.push(rmv.mainMaterial.mainPass);
    const n = obj.getChildrenCount();
    for (let i = 0; i < n; i++) {
      for (const c of this.collectPasses(obj.getChild(i))) out.push(c);
    }
    return out;
  }

  private smooth(x: number): number {
    const t = this.clamp(x, 0, 1);
    return t * t * (3 - 2 * t);
  }

  private clamp(v: number, lo: number, hi: number): number {
    return v < lo ? lo : v > hi ? hi : v;
  }
}
