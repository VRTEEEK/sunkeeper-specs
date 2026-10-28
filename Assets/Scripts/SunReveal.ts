/**
 * SunReveal — milestone 5: the revelation.
 *
 * Listens for SunAlignment's lock. After the caption time the light enters the doorway
 * and travels down the temple axis to the sanctuary: a warm patch on the floor with a
 * soft, additive shaft extending behind it to the doorway. When the light arrives the
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

import { SunAlignment } from './SunAlignment';
import { InteriorLift } from './InteriorLift';

// ---------------------------------------------------------------------------
// Tunables (seconds, centimetres)
// ---------------------------------------------------------------------------

/** Delay from lock to the light entering the doorway (the "stand up" caption time). */
const START_DELAY_SEC = 2.0;
/** Travel time of the light patch from the doorway to the sanctuary. */
const TRAVEL_SEC = 8.0;
/** Beam fade-in at the start of the travel. */
const BEAM_FADE_IN_SEC = 0.6;
/** Gap between successive statues lighting up. */
const STATUE_GAP_SEC = 0.8;
/** Time each statue takes to ease from base to lit. */
const STATUE_RISE_SEC = 1.0;
/** The floor ring fades out over this time once the beam starts. */
const RING_FADE_SEC = 1.5;

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

  /** Beam root: two crossed unit quads as children; +Z runs along the beam. Scaled (w, w, length). */
  @input beam: SceneObject;

  /** Flat unit quad with the soft patch texture, moved along the floor. */
  @input lightPatch: SceneObject;

  /** Where the light enters: the doorway sill, in cm along the temple's own axes. */
  @input('vec3', '{0, 1.7, 23.7}')
  doorwayOffset: vec3;

  /** Where the light stops: the sanctuary floor in front of the statues, temple axes. */
  @input('vec3', '{0, 1.7, -32}')
  sanctuaryOffset: vec3;

  /** Beam width (cm), about the doorway width. */
  @input
  beamWidth: number = 3;

  /** Length of the floor patch along the axis (cm). */
  @input
  patchLength: number = 7;

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
  private t = 0;
  private lockTime = 0;
  private loggedPhases: { [phase: string]: boolean } = {};
  private completeListeners: (() => void)[] = [];

  private beamPasses: Pass[] = [];
  private beamBase: vec4[] = [];
  private patchPasses: Pass[] = [];
  private patchBase: vec4[] = [];
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

  /** Put everything back to the pre-lock state (Try again, milestone 6). */
  reset() {
    this.running = false;
    this.complete = false;
    this.t = 0;
    this.loggedPhases = {};
    this.setGlow(this.beamPasses, this.beamBase, 0);
    this.setGlow(this.patchPasses, this.patchBase, 0);
    if (this.beam) this.beam.enabled = false;
    if (this.lightPatch) this.lightPatch.enabled = false;
    const base = this.lift ? this.lift.getEmissive() : new vec3(0.14, 0.11, 0.07);
    for (const s of this.statues) this.setStatueLit(s, base, 0);
    if (this.alignment) this.alignment.setCueFade(1, 1);
  }

  private start() {
    if (!this.alignment || !this.lift || !this.beam || !this.lightPatch) {
      print('SunReveal: alignment, lift, beam and lightPatch must be assigned');
      return;
    }
    this.beamPasses = this.collectPasses(this.beam);
    this.beamBase = this.beamPasses.map((p) => p.baseColor as vec4);
    this.patchPasses = this.collectPasses(this.lightPatch);
    this.patchBase = this.patchPasses.map((p) => p.baseColor as vec4);
    this.setGlow(this.beamPasses, this.beamBase, 0);
    this.setGlow(this.patchPasses, this.patchBase, 0);
    this.beam.enabled = false;
    this.lightPatch.enabled = false;
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
    if (!this.running) return;
    if (this.debugFreezeAt >= 0) {
      this.t = this.debugFreezeAt;
    } else {
      this.t += getDeltaTime();
    }
    const t = this.t;

    // --- Beam and floor patch ---
    const travel = this.clamp((t - START_DELAY_SEC) / TRAVEL_SEC, 0, 1);
    const started = t >= START_DELAY_SEC;
    const glow = this.clamp((t - START_DELAY_SEC) / BEAM_FADE_IN_SEC, 0, 1);
    this.beam.enabled = started;
    this.lightPatch.enabled = started;
    if (started) {
      const doorway = this.alignment.templePoint(this.doorwayOffset);
      const sanctuary = this.alignment.templePoint(this.sanctuaryOffset);
      const head = vec3.lerp(doorway, sanctuary, this.smooth(travel));
      this.placeBeam(doorway, head);
      this.placePatch(head, sanctuary.sub(doorway).normalize());
      this.setGlow(this.beamPasses, this.beamBase, glow);
      this.setGlow(this.patchPasses, this.patchBase, glow);
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

  private placeBeam(from: vec3, to: vec3) {
    const seg = to.sub(from);
    const len = Math.max(seg.length, 0.5);
    const w = this.beamWidth;
    const tr = this.beam.getTransform();
    // Parent sits half a width above the floor so the vertical quad stands on it.
    tr.setWorldPosition(from.add(seg.uniformScale(0.5)).add(new vec3(0, w * 0.5, 0)));
    tr.setWorldRotation(quat.lookAt(seg.normalize(), vec3.up()));
    tr.setLocalScale(new vec3(w, w, len));
  }

  private placePatch(at: vec3, along: vec3) {
    const tr = this.lightPatch.getTransform();
    tr.setWorldPosition(at.add(new vec3(0, 0.25, 0)));
    tr.setWorldRotation(quat.lookAt(along, vec3.up()));
    tr.setLocalScale(new vec3(this.beamWidth * 1.8, 1, this.patchLength));
  }

  /** Drive one statue's emissive, gold tint, halo and pool to lit fraction k (0 = base). */
  private setStatueLit(s: StatueEntry, base: vec3, k: number) {
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
    this.setGlow(s.haloPasses, s.haloBase, k);
    this.setGlow(s.poolPasses, s.poolBase, k);
  }

  /** Put each halo card behind its statue and each pool on the floor in front, from the statue bounds. */
  private placeGlow() {
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
