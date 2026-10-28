/**
 * CameraRig — demo recording helper (not used in the experience). When `active`, drives the
 * Camera Object along a keyframed path after the Lens starts, so the preview footage has
 * smooth, eased, human-paced moves. Everything else in the Lens keeps reading the camera's
 * live transform (sun, cues, lock, viewing spot, captions), so the interaction stays real.
 *
 * `path` is a list of keyframes "t x y z lx ly lz" separated by ';' (world cm, seconds from
 * Lens start): position (x, y, z) and look-at point (lx, ly, lz). Between keyframes the
 * position and look-at are interpolated with an ease-in/out, and a very slight head sway is
 * added so nothing looks mechanical. Before the first keyframe the camera holds the first
 * pose; after the last it holds the last. Set `active` false for the shipped Lens.
 */

interface Key { t: number; pos: vec3; look: vec3 }

@component
export class CameraRig extends BaseScriptComponent {
  @input camera: SceneObject;

  @input
  active: boolean = false;

  /** Keyframes: "t x y z lx ly lz; t x y z lx ly lz; ..." */
  @input
  path: string = '';

  /** Head sway amplitude (cm) and rate (Hz); 0 disables. */
  @input
  swayCm: number = 0.4;
  @input
  swayHz: number = 0.5;

  private keys: Key[] = [];
  private t = 0;
  private logged = false;

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => this.start());
    // Early in the frame so the alignment scripts read the rig's pose (the rig object must sit
    // above them in the hierarchy), and again late so the render uses it.
    this.createEvent('UpdateEvent').bind(() => this.update(true));
    this.createEvent('LateUpdateEvent').bind(() => this.update(false));
  }

  private start() {
    this.keys = [];
    for (const part of this.path.split(';')) {
      const n = part.trim().split(/[\s,]+/).map((s) => parseFloat(s)).filter((v) => !isNaN(v));
      if (n.length >= 7) this.keys.push({ t: n[0], pos: new vec3(n[1], n[2], n[3]), look: new vec3(n[4], n[5], n[6]) });
    }
    if (this.active && this.keys.length === 0) print('CameraRig: active but no valid keyframes');
    if (this.active && this.keys.length > 0) {
      // Device Tracking would rewrite the camera pose every frame before the other scripts
      // read it; while the rig drives the camera, tracking is switched off so every script
      // (sun, cues, lock, captions) sees the rig's pose. Nothing else is changed.
      const tracking = this.camera ? (this.camera.getComponent('Component.DeviceTracking') as DeviceTracking | null) : null;
      if (tracking) tracking.enabled = false;
      print('CameraRig: ' + this.keys.length + ' keyframes, ' + this.keys[this.keys.length - 1].t.toFixed(1) + ' s' + (tracking ? ', device tracking paused' : ''));
      this.update(false);
    }
  }

  private update(advance: boolean) {
    if (!this.active || !this.camera || this.keys.length === 0) return;
    if (advance) this.t += getDeltaTime();
    const k = this.keys;
    let pos: vec3;
    let look: vec3;
    if (this.t <= k[0].t) {
      pos = k[0].pos; look = k[0].look;
    } else if (this.t >= k[k.length - 1].t) {
      pos = k[k.length - 1].pos; look = k[k.length - 1].look;
      if (!this.logged) { this.logged = true; print('CameraRig: path finished at ' + this.t.toFixed(1) + ' s'); }
    } else {
      let i = 0;
      while (i + 1 < k.length && this.t > k[i + 1].t) i++;
      const a = k[i]; const b = k[i + 1];
      const u = this.smooth((this.t - a.t) / Math.max(b.t - a.t, 0.001));
      pos = vec3.lerp(a.pos, b.pos, u);
      look = vec3.lerp(a.look, b.look, u);
    }
    if (this.swayCm > 0) {
      const w = 2 * Math.PI * this.swayHz * this.t;
      pos = pos.add(new vec3(Math.sin(w) * this.swayCm, Math.sin(w * 1.7 + 1) * this.swayCm * 0.5, 0));
    }
    const tr = this.camera.getTransform();
    tr.setWorldPosition(pos);
    const dir = look.sub(pos);
    if (dir.length > 0.01) tr.setWorldRotation(quat.lookAt(dir.normalize().uniformScale(-1), vec3.up()));
  }

  private smooth(x: number): number {
    const t = x < 0 ? 0 : x > 1 ? 1 : x;
    return t * t * (3 - 2 * t);
  }
}
