/**
 * SunReveal — milestone 5: the revelation.
 *
 * Listens for SunAlignment's lock. After the caption time the light enters the doorway
 * and travels down the temple axis to the sanctuary: a warm patch on the floor with a
 * soft, additive shaft extending behind it to the doorway. When the light arrives the
 * sanctuary statues ease up to about twice Ptah's brightness one by one, in the order
 * given by `statueOrder`; Ptah stays at the base level set by InteriorLift. The lit
 * state holds. `onRevealComplete()` fires once when the last statue is fully lit
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
  private statues: { name: string; mat: Material | null }[] = [];

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
    for (const s of this.statues) if (s.mat) s.mat.mainPass.emissiveFactor = base;
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
      .map((name) => ({ name, mat: null as Material | null }));
    this.alignment.onAligned(() => this.begin());
  }

  private begin() {
    if (this.running || this.complete) return;
    // InteriorLift resolved the materials at its own start; fetch the handles now.
    for (const s of this.statues) {
      s.mat = this.lift.getMaterial(s.name);
      if (!s.mat) print('SunReveal: no material for ' + s.name);
    }
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
      if (s.mat) s.mat.mainPass.emissiveFactor = vec3.lerp(base, this.litEmissive, this.smooth(p));
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
