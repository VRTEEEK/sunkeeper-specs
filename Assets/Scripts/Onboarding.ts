/**
 * Onboarding — milestone 7: two short captions at the start, near the plinth and inside a
 * level gaze from the start position: "Abu Simbel, at dawn", then "Find where the sun must
 * stand". They fade out as soon as the viewer starts moving (head more than `moveDistance`
 * from where it started) or the alignment score rises above `scoreToHide`. Text only, no panel.
 */

import { SunAlignment } from './SunAlignment';

const FIRST_LINE = 'Abu Simbel, at dawn';
const SECOND_LINE = 'Find where the sun must stand';
/** Seconds the first line stays before the second replaces it. */
const FIRST_LINE_SEC = 3.0;
const FADE_IN_SEC = 0.8;
const FADE_OUT_SEC = 0.8;
/** Start delay so the caption appears as the temple finishes rising. */
const START_DELAY_SEC = 1.0;

@component
export class Onboarding extends BaseScriptComponent {
  @input alignment: SunAlignment;

  /** The Camera Object: its world position is the viewer's head. */
  @input camera: SceneObject;

  /** The onboarding caption object (Component.Text on it). */
  @input caption: SceneObject;

  /** Head movement (cm) from the start position that counts as "started moving". */
  @input
  moveDistance: number = 25;

  /** Alignment score (0..1) at which the caption gives way to the cues. */
  @input
  scoreToHide: number = 0.3;

  private text: Text | null = null;
  private baseColor: vec4 = new vec4(1, 0.96, 0.88, 1);
  private t = 0;
  private alpha = 0;
  private done = false;
  private startHead: vec3 | null = null;
  private secondShown = false;

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => this.start());
    this.createEvent('UpdateEvent').bind(() => this.update());
  }

  private start() {
    if (!this.caption) return;
    this.text = this.caption.getComponent('Component.Text') as Text | null;
    if (this.text) {
      this.baseColor = this.text.textFill.color;
      this.text.text = FIRST_LINE;
    }
    this.setAlpha(0);
  }

  private update() {
    if (this.done || !this.caption) return;
    const dt = getDeltaTime();
    this.t += dt;
    const head = this.camera ? this.camera.getTransform().getWorldPosition() : null;
    if (head && this.startHead === null && this.t >= START_DELAY_SEC) this.startHead = head;

    // Hide once the viewer moves or gets close to the spot.
    const moved = head && this.startHead ? head.distance(this.startHead) > this.moveDistance : false;
    const closing = this.alignment ? this.alignment.getScore() >= this.scoreToHide : false;
    const target = this.t >= START_DELAY_SEC && !moved && !closing ? 1 : 0;
    const hiding = target === 0 && this.t >= START_DELAY_SEC;

    if (!this.secondShown && this.t >= START_DELAY_SEC + FIRST_LINE_SEC && this.text) {
      this.secondShown = true;
      this.text.text = SECOND_LINE;
    }

    const step = dt / (target > this.alpha ? FADE_IN_SEC : FADE_OUT_SEC);
    this.alpha = this.alpha < target ? Math.min(this.alpha + step, target) : Math.max(this.alpha - step, target);
    this.setAlpha(this.alpha);
    if (head) this.faceViewer(this.caption, head);

    if (hiding && this.alpha <= 0) {
      this.done = true;
      this.caption.enabled = false;
      print('ONBOARDING hidden at ' + this.t.toFixed(1) + ' s (' + (moved ? 'viewer moved' : 'alignment cue rising') + ')');
    }
  }

  private setAlpha(a: number) {
    this.caption.enabled = a > 0.001;
    if (!this.text) return;
    const c = this.baseColor;
    this.text.textFill.color = new vec4(c.x, c.y, c.z, a);
  }

  private faceViewer(obj: SceneObject, head: vec3) {
    const t = obj.getTransform();
    const d = head.sub(t.getWorldPosition());
    t.setWorldRotation(quat.angleAxis(Math.atan2(d.x, d.z), vec3.up()));
  }
}
