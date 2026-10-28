/**
 * SurfaceProbe — preview-setup helper: ray-casts against the preview environment with the
 * World Query module and prints where surfaces are, so the temple can be placed on a real
 * table in a simulated room. Two rays each `intervalSec`: from the head along its gaze, and
 * straight down from `dropFrom` (temple-local cm, world when `dropFrom` is set). Disable or
 * remove the component for the shipped Lens.
 */

const WorldQueryModule = require('LensStudio:WorldQueryModule') as WorldQueryModule;

@component
export class SurfaceProbe extends BaseScriptComponent {
  @input camera: SceneObject;

  /** World point to drop a ray from (down 300 cm); leave at 0,0,0 to skip. */
  @input('vec3', '{0, 0, 0}')
  dropFrom: vec3;

  @input
  intervalSec: number = 1.0;

  private session: HitTestSession | null = null;
  private t = 0;

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => {
      try {
        const opts = HitTestSessionOptions.create();
        opts.filter = true;
        this.session = WorldQueryModule.createHitTestSessionWithOptions(opts);
        print('SurfaceProbe: hit-test session created');
      } catch (e) {
        print('SurfaceProbe: no world query in this preview: ' + e);
      }
    });
    this.createEvent('UpdateEvent').bind(() => this.update());
  }

  private update() {
    if (!this.session || !this.camera) return;
    this.t += getDeltaTime();
    if (this.t < this.intervalSec) return;
    this.t = 0;
    const tr = this.camera.getTransform();
    const head = tr.getWorldPosition();
    const fwd = tr.forward.uniformScale(-1); // the camera looks down its −Z
    this.session.hitTest(head, head.add(fwd.uniformScale(1200)), (hit) => {
      if (hit) print('SurfaceProbe gaze hit ' + this.fmt(hit.position) + ' normal ' + this.fmt(hit.normal));
      else print('SurfaceProbe gaze: no hit');
    });
    if (this.dropFrom.length > 0.01) {
      const from = this.dropFrom;
      this.session.hitTest(from, from.add(new vec3(0, -300, 0)), (hit) => {
        if (hit) print('SurfaceProbe drop from ' + this.fmt(from) + ' hit ' + this.fmt(hit.position) + ' normal ' + this.fmt(hit.normal));
        else print('SurfaceProbe drop: no hit');
      });
    }
  }

  private fmt(v: vec3): string {
    return '(' + v.x.toFixed(1) + ', ' + v.y.toFixed(1) + ', ' + v.z.toFixed(1) + ')';
  }
}
