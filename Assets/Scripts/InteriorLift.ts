/**
 * InteriorLift — lifts the temple interior so it reads at least as bright as the façade.
 *
 * The temple materials live inside the packed Temple.glb, so an editor-side edit of
 * their emissive factor is not saved with the project. This script applies the lift
 * at Lens start instead: it walks the temple hierarchy and sets emissiveFactor on the
 * materials of the named interior objects (shell, pillars, sanctuary statues).
 *
 * Milestone 5 (statues lighting up one by one) reuses the same material handles through
 * getMaterial(name) / getEmissive(): the lit statues go to about 2x this base emissive,
 * Ptah stays at it.
 */
@component
export class InteriorLift extends BaseScriptComponent {
  /** Root of the imported temple (the Great Temple prefab instance). */
  @input temple: SceneObject;

  /** Warm emissive term added to the interior materials (linear RGB). */
  @input('vec3', '{0.14, 0.11, 0.07}')
  emissive: vec3;

  /** Comma-separated names of the interior objects whose materials get the lift. */
  @input
  targetNames: string = 'Interior_Shell,Interior_Pillars,Statue_Ptah,Statue_AmunRa,Statue_Ramesses,Statue_RaHorakhty';

  private applied: Material[] = [];
  private byName: { [name: string]: Material } = {};

  /** Material of a named interior object (e.g. 'Statue_AmunRa'), or null if not found. */
  getMaterial(name: string): Material | null {
    return this.byName[name] || null;
  }

  /** The base emissive term applied to every interior material (Ptah's resting level). */
  getEmissive(): vec3 {
    return this.emissive;
  }

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => this.apply());
  }

  apply() {
    if (!this.temple) {
      print('InteriorLift: no temple object assigned');
      return;
    }
    const names = new Set(this.targetNames.split(',').map((s) => s.trim()).filter((s) => s.length > 0));
    this.applied = [];
    this.byName = {};
    this.walk(this.temple, names);
    print('InteriorLift: lifted ' + this.applied.length + ' material(s)');
  }

  private walk(obj: SceneObject, names: Set<string>) {
    if (names.has(obj.name)) {
      const rmv = obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
      const mat = rmv ? rmv.mainMaterial : null;
      if (mat) this.byName[obj.name] = mat;
      if (mat && this.applied.indexOf(mat) < 0) {
        mat.mainPass.emissiveFactor = this.emissive;
        this.applied.push(mat);
      }
    }
    const n = obj.getChildrenCount();
    for (let i = 0; i < n; i++) {
      this.walk(obj.getChild(i), names);
    }
  }
}
