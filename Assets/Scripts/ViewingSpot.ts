/**
 * ViewingSpot — milestone 6 addition: a second, softer floor marker beside the plinth at
 * the sanctuary end, where the lit sanctuary is best seen (the m5r-b viewpoint).
 *
 * It fades in when the sun locks and fades out once the viewer's head is within
 * `reachRadius` of it (horizontally) or the reveal completes, whichever comes first.
 * `reset()` hides it again. "VIEWING_SPOT reached" is printed once per run.
 */

import { SunAlignment } from './SunAlignment';
import { SunReveal } from './SunReveal';

const FADE_IN_SEC = 1.0;
const FADE_OUT_SEC = 1.0;

@component
export class ViewingSpot extends BaseScriptComponent {
  @input alignment: SunAlignment;
  @input reveal: SunReveal;

  /** The Camera Object: its world position is the viewer's head. */
  @input camera: SceneObject;

  /** The marker: a flat unit plane with an unlit, blended ring material, placed on the floor. */
  @input marker: SceneObject;

  /** Horizontal distance (cm) from the marker centre that counts as "reached". */
  @input
  reachRadius: number = 35;

  /** Opacity of the marker when fully shown (softer than the alignment ring). */
  @input
  maxAlpha: number = 0.5;

  private pass: Pass | null = null;
  private alpha = 0;
  private target = 0;
  private reached = false;

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => this.start());
    this.createEvent('UpdateEvent').bind(() => this.update());
  }

  isReached(): boolean {
    return this.reached;
  }

  reset() {
    this.target = 0;
    this.reached = false;
  }

  private start() {
    if (this.marker) {
      const rmv = this.marker.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
      if (rmv && rmv.mainMaterial) this.pass = rmv.mainMaterial.mainPass;
    }
    this.setAlpha(0);
    if (this.alignment) this.alignment.onAligned(() => this.show());
  }

  private show() {
    this.reached = false;
    this.target = 1;
  }

  private update() {
    if (this.target > 0 && !this.reached && this.camera && this.marker) {
      const head = this.camera.getTransform().getWorldPosition();
      const at = this.marker.getTransform().getWorldPosition();
      const dx = head.x - at.x;
      const dz = head.z - at.z;
      const here = Math.sqrt(dx * dx + dz * dz) <= this.reachRadius;
      const done = this.reveal ? this.reveal.isComplete() : false;
      if (here || done) {
        this.reached = true;
        this.target = 0;
        print('VIEWING_SPOT ' + (here ? 'reached' : 'skipped (reveal complete)'));
      }
    }
    const rate = this.target > this.alpha ? 1 / FADE_IN_SEC : 1 / FADE_OUT_SEC;
    const step = getDeltaTime() * rate;
    this.alpha = this.alpha < this.target ? Math.min(this.alpha + step, this.target) : Math.max(this.alpha - step, this.target);
    this.setAlpha(this.alpha);
  }

  private setAlpha(k: number) {
    if (this.marker) this.marker.enabled = k > 0.005;
    if (!this.pass) return;
    const c = this.pass.baseColor as vec4;
    this.pass.baseColor = new vec4(c.x, c.y, c.z, this.maxAlpha * k);
  }
}
