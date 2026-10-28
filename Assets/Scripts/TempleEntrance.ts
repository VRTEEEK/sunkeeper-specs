/**
 * TempleEntrance — milestone 7: the temple rises out of the plinth over RISE_SEC at start,
 * eased, while a soft warm glow on the plinth top around it brightens and fades. Calm:
 * one smooth motion, nothing flashes. `debugFreezeAt` (>= 0) holds the rise at that time
 * for screenshots.
 */

const RISE_SEC = 2.0;
/** How far below its resting place the temple starts (cm); hidden inside the plinth. */
const RISE_FROM_CM = 22;
/** The glow peaks a little after the start and is gone shortly after the rise ends. */
const GLOW_PEAK_SEC = 0.8;
const GLOW_END_SEC = 3.0;
const GLOW_MAX = 0.7;

@component
export class TempleEntrance extends BaseScriptComponent {
  /** The Great Temple prefab instance (rises to its authored position). */
  @input temple: SceneObject;

  /** Flat additive glow quad on the plinth top under the temple. */
  @input glow: SceneObject;

  /** >= 0 freezes the entrance at that many seconds (for screenshots). */
  @input
  debugFreezeAt: number = -1;

  private rest: vec3 | null = null;
  private t = 0;
  private done = false;
  private glowPasses: Pass[] = [];
  private glowBase: vec4[] = [];

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => this.start());
    this.createEvent('UpdateEvent').bind(() => this.update());
  }

  private start() {
    if (!this.temple) {
      print('TempleEntrance: temple must be assigned');
      return;
    }
    this.rest = this.temple.getTransform().getLocalPosition();
    this.glowPasses = this.collectPasses(this.glow);
    this.glowBase = this.glowPasses.map((p) => p.baseColor as vec4);
    this.apply(0);
  }

  private update() {
    if (this.done || !this.rest) return;
    this.t = this.debugFreezeAt >= 0 ? this.debugFreezeAt : this.t + getDeltaTime();
    this.apply(this.t);
    if (this.debugFreezeAt < 0 && this.t >= GLOW_END_SEC) {
      this.done = true;
      if (this.glow) this.glow.enabled = false;
      print('ENTRANCE done at ' + this.t.toFixed(2) + ' s');
    }
  }

  private apply(t: number) {
    const r = this.smooth(t / RISE_SEC);
    const p = this.rest as vec3;
    this.temple.getTransform().setLocalPosition(new vec3(p.x, p.y - RISE_FROM_CM * (1 - r), p.z));
    let g = 0;
    if (t < GLOW_PEAK_SEC) g = this.smooth(t / GLOW_PEAK_SEC);
    else g = 1 - this.smooth((t - GLOW_PEAK_SEC) / (GLOW_END_SEC - GLOW_PEAK_SEC));
    this.setGlow(g * GLOW_MAX);
  }

  /** Additive material: scale colour and alpha together. */
  private setGlow(k: number) {
    if (this.glow) this.glow.enabled = k > 0.002;
    for (let i = 0; i < this.glowPasses.length; i++) {
      const b = this.glowBase[i];
      this.glowPasses[i].baseColor = new vec4(b.x * k, b.y * k, b.z * k, k);
    }
  }

  private collectPasses(obj: SceneObject | null): Pass[] {
    const out: Pass[] = [];
    if (!obj) return out;
    const rmv = obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
    if (rmv && rmv.mainMaterial) out.push(rmv.mainMaterial.mainPass);
    const n = obj.getChildrenCount();
    for (let i = 0; i < n; i++) for (const c of this.collectPasses(obj.getChild(i))) out.push(c);
    return out;
  }

  private smooth(x: number): number {
    const t = x < 0 ? 0 : x > 1 ? 1 : x;
    return t * t * (3 - 2 * t);
  }
}
