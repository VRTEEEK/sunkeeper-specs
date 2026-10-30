/**
 * SunAlignment — milestone 4: the sun that follows the viewer, and the alignment cues.
 *
 * Every frame the sun disc is placed on the line from the temple centre through the
 * viewer's head (the Camera Object, which Device Tracking moves in the preview), at a
 * fixed distance from the temple and eased so it never jitters. The key light is carried
 * with it, so light always comes from where the viewer stands.
 *
 * The alignment target is the spot where the real sun stands twice a year: low and on the
 * temple's main axis, in front of the entrance. The tolerances are the constants below.
 * Two warm cues report closeness: a ring on the floor in front of the plinth, and a faint
 * shaft from the doorway towards the sun. Both scale smoothly with closeness; nothing flashes.
 *
 * The visible disc is separate from the light. The key light stays on the temple -> viewer
 * line; the disc keeps the same azimuth but is raised so it sits above the façade's top edge
 * in the viewer's view (re-placed every frame, also after lock), never over the doorway. It
 * dims as the score rises and settles to a soft glow at lock, so the shaft (disc -> doorway)
 * and the reveal carry the moment.
 *
 * When the viewer stays inside the tolerance for HOLD_SEC the sun locks, the caption shows
 * for CAPTION_SEC, and "ALIGNED" is logged. The caption appears under the doorway, over the
 * plinth's front face (darker than the lit façade, which matters on an additive display), with
 * a warm arrow on the side of the viewing spot pointing to it. It is kept inside the camera's
 * field of view (the SPECS display) while it is up, so standing up and turning never clips it.
 * The beam travel and the statue lighting are milestone 5: they subscribe through onAligned().
 */

// ---------------------------------------------------------------------------
// Tunables (all angles in degrees, all lengths in centimetres, times in seconds)
// ---------------------------------------------------------------------------

/** Half-width of the azimuth window around the temple axis. */
const AZIMUTH_TOL_DEG = 7;
/** Head elevation window, measured from the entrance point at temple floor level. */
const ELEV_MIN_DEG = 0;
const ELEV_MAX_DEG = 25;
/** Horizontal distance window from the entrance. */
const DIST_MIN_CM = 50;
const DIST_MAX_CM = 150;
/** Time the viewer must stay inside the window before the sun locks. */
const HOLD_SEC = 1.0;
/** How long the lock caption stays up (long enough to read while standing up). */
const CAPTION_SEC = 4.0;

/** Distance of the sun (the light) from the temple centre. */
const SUN_DISTANCE_CM = 60;

/** The visible disc is raised this much above the light's direction, seen from the viewer. */
const DISC_RAISE_DEG = 12;
/** Minimum gap between the disc's lower edge and the façade's top edge, seen from the viewer. */
const DISC_CLEAR_DEG = 3;
/** Disc size relative to the authored Sun scale. */
const DISC_SCALE = 0.75;
/** Disc brightness when the score reaches 1 (before lock) and once locked. */
const DISC_ALIGNED_GLOW = 0.4;
const DISC_LOCKED_GLOW = 0.25;
/** Easing rate for the disc brightness (per second). */
const DISC_GLOW_SMOOTHING = 3;
/** Easing rate for the sun (per second). Higher follows faster; 6 settles in ~0.5 s. */
const SUN_SMOOTHING = 6;

/** Cues fade in over this many tolerances outside the window (2 = fully off at 2x). */
const CUE_FALLOFF = 2.0;
/** Floor ring opacity when far away and when on the spot. */
const RING_MIN_ALPHA = 0.10;
const RING_MAX_ALPHA = 0.85;
/** Light shaft opacity when fully aligned. */
const SHAFT_MAX_ALPHA = 0.45;
/** Shaft width (cm) when fully aligned; it narrows as alignment is lost. */
const SHAFT_WIDTH_CM = 4;

const CAPTION_LOCKED = 'Now walk to the side\nand look inside.';
/** Arrows on the lock caption point at most this far above or below horizontal. */
const ARROW_MAX_TILT_DEG = 35;

/** Safety margin (degrees) between the caption's edge and the edge of the field of view. */
const CAPTION_FOV_MARGIN_DEG = 2.5;
/** The caption never comes closer than this (cm), so it stays comfortable to read. */
const CAPTION_MIN_DEPTH_CM = 35;

// ---------------------------------------------------------------------------

@component
export class SunAlignment extends BaseScriptComponent {
  /** The Camera Object: its world position is the viewer's head. */
  @input camera: SceneObject;

  /** The Great Temple prefab instance (pivot at the base centre, façade facing +Z). */
  @input temple: SceneObject;

  /** The glowing sun disc (an unlit emissive sphere). */
  @input sun: SceneObject;

  /** The key light that travels with the sun (a LightSource component). Optional. */
  @input('Component.LightSource')
  @allowUndefined
  keyLight: LightSource;

  /** The floor ring in front of the plinth (RenderMeshVisual with an unlit, blended material). */
  @input ring: SceneObject;

  /** The light shaft from the doorway towards the sun (unit cube with an unlit, blended material). */
  @input shaft: SceneObject;

  /** The caption object (Component.Text on it). Hidden until lock. */
  @input caption: SceneObject;

  /** The warm arrow beside the caption (a child of it, RenderMeshVisual; the mesh is built here). */
  @input
  @allowUndefined
  captionArrow: SceneObject;

  /** The viewing spot marker the arrow points to. */
  @input
  @allowUndefined
  viewingSpot: SceneObject;

  /** Offset of the temple centre from the temple pivot, in cm along the temple's own axes. */
  @input('vec3', '{0, 10, 0}')
  centreOffset: vec3;

  /** Offset of the entrance (doorway at floor level) from the temple pivot, in cm along the temple's own axes. */
  @input('vec3', '{0, 1, 39}')
  entranceOffset: vec3;

  /** Centre of the façade's top front edge, in cm along the temple's own axes (the disc stays above it). */
  @input('vec3', '{0, 27, 36}')
  facadeTopOffset: vec3;

  /** Depth (cm) of the façade block's top, and half its width: from above, the back edge is the visible top. */
  @input
  facadeTopDepthCm: number = 20;
  @input
  facadeTopHalfWidthCm: number = 17;

  /** Direction the façade faces, in the temple's own axes (+Z = out of the doorway). */
  @input('vec3', '{0, 0, 1}')
  axisDirection: vec3;

  /** Flip the key light if it shines the wrong way after wiring. */
  @input
  lightFacesBackwards: boolean = false;

  /** Print azimuth / elevation / distance once a second for tuning. */
  @input
  debugLog: boolean = false;

  /** Lock caption anchor: this far above the doorway floor (cm); negative is below, on the plinth front. */
  @input
  captionLiftCm: number = -12;

  /** Lock caption anchor: pulled this far from the doorway towards the viewer, horizontally (cm). */
  @input
  captionTowardViewerCm: number = 14;

  /** Arrow centre from the caption centre, in the caption's local units (beside the longer line). */
  @input
  captionArrowOffset: number = 6.4;

  /** Half the lock caption's on-screen size in cm (two lines of text at its scale), for the FOV clamp. */
  @input
  captionHalfWidthCm: number = 15;
  @input
  captionHalfHeightCm: number = 4;

  /** Keep the caption up after lock instead of hiding it after CAPTION_SEC (for screenshots). */
  @input
  debugHoldCaption: boolean = false;

  private sunPos: vec3 | null = null;
  private discPos: vec3 | null = null;
  private discPass: Pass | null = null;
  private discBaseColor: vec4 | null = null;
  private discGlow = 1;
  private holdTimer = 0;
  private captionTimer = 0;
  private locked = false;
  private debugTimer = 0;
  private alignedListeners: (() => void)[] = [];
  private lastScore = 0;

  private ringPass: Pass | null = null;
  private shaftPasses: Pass[] = [];
  private shaftBaseColors: vec4[] = [];
  private captionText: Text | null = null;
  private cameraComp: Camera | null = null;
  private ringFade = 1;
  private shaftFade = 1;

  onAwake() {
    this.createEvent('OnStartEvent').bind(() => this.start());
    this.createEvent('UpdateEvent').bind(() => this.update());
  }

  /** Milestone 5 hook: called once when the sun locks. */
  onAligned(listener: () => void) {
    this.alignedListeners.push(listener);
  }

  isLocked(): boolean {
    return this.locked;
  }

  /** Closeness to the alignment window, 0 (far) to 1 (inside), as scored on the last frame. */
  getScore(): number {
    return this.locked ? 1 : this.lastScore;
  }

  /** World position of the entrance at floor level (start of the beam path, milestone 5). */
  getEntrance(): vec3 {
    return this.temple.getTransform().getWorldPosition().add(this.templeToWorld(this.entranceOffset));
  }

  /** World direction the façade faces (the temple axis, pointing out of the doorway). */
  getAxis(): vec3 {
    return this.templeToWorld(this.axisDirection).normalize();
  }

  /**
   * Rotate a vector given in the temple's own axes into world axes. Only the temple's
   * rotation is applied: the offsets are in cm, the prefab's x100 scale must not touch them.
   */
  templeToWorld(v: vec3): vec3 {
    return this.temple.getTransform().getWorldRotation().multiplyVec3(v);
  }

  /** World position of a point given in cm along the temple's own axes from its pivot. */
  templePoint(local: vec3): vec3 {
    return this.temple.getTransform().getWorldPosition().add(this.templeToWorld(local));
  }

  /**
   * Multipliers on the two cues once locked (milestone 5 fades the ring out while the
   * beam plays). 1 = as scored, 0 = hidden.
   */
  setCueFade(ring: number, shaft: number) {
    this.ringFade = this.clamp(ring, 0, 1);
    this.shaftFade = this.clamp(shaft, 0, 1);
  }

  /** Where the light comes from (on the temple -> viewer line). */
  getSunPosition(): vec3 {
    return this.sunPos ? this.sunPos : this.sun.getTransform().getWorldPosition();
  }

  /** Where the visible disc is drawn (raised above the façade in the viewer's view). */
  getDiscPosition(): vec3 {
    return this.discPos ? this.discPos : this.sun.getTransform().getWorldPosition();
  }

  /** Reset to the start state (used by Try again, milestone 6). */
  reset() {
    this.locked = false;
    this.holdTimer = 0;
    this.captionTimer = 0;
    this.ringFade = 1;
    this.shaftFade = 1;
    if (this.caption) this.caption.enabled = false;
  }

  private start() {
    this.ringPass = this.passOf(this.ring);
    this.shaftPasses = this.collectPasses(this.shaft);
    this.shaftBaseColors = this.shaftPasses.map((p) => p.baseColor as vec4);
    if (this.caption) {
      this.captionText = this.caption.getComponent('Component.Text') as Text | null;
      this.caption.enabled = false;
    }
    if (!this.camera || !this.temple || !this.sun) {
      print('SunAlignment: camera, temple and sun must be assigned');
    } else {
      this.cameraComp = this.camera.getComponent('Component.Camera') as Camera | null;
      const st = this.sun.getTransform();
      st.setLocalScale(st.getLocalScale().uniformScale(DISC_SCALE));
      this.discPass = this.passOf(this.sun);
      if (this.discPass) this.discBaseColor = this.discPass.baseColor as vec4;
    }
    if (this.captionArrow) this.buildArrow(this.captionArrow);
    this.setAlpha(this.ringPass, RING_MIN_ALPHA);
    this.setShaftGlow(0);
  }

  private update() {
    if (!this.camera || !this.temple || !this.sun) return;
    const dt = getDeltaTime();

    const head = this.camera.getTransform().getWorldPosition();
    const templePos = this.temple.getTransform().getWorldPosition();
    const centre = templePos.add(this.templeToWorld(this.centreOffset));
    const entrance = templePos.add(this.templeToWorld(this.entranceOffset));

    // --- Sun: on the line temple centre -> head, eased, frozen once locked ---
    if (!this.locked) {
      const toHead = head.sub(centre);
      const dir = toHead.length > 0.001 ? toHead.normalize() : this.getAxis();
      const target = centre.add(dir.uniformScale(SUN_DISTANCE_CM));
      if (this.sunPos === null) {
        this.sunPos = target;
      } else {
        const k = 1 - Math.exp(-SUN_SMOOTHING * dt);
        this.sunPos = vec3.lerp(this.sunPos, target, k);
      }
      this.placeKeyLight(this.sunPos, centre);
    }
    // The disc is re-placed every frame, also after lock (the light stays frozen): standing up
    // or walking round must never bring it down over the façade or the doorway.
    if (this.sunPos) {
      this.discPos = this.raisedDisc(head, this.sunPos);
      this.sun.getTransform().setWorldPosition(this.discPos);
    }

    // --- Alignment measure ---
    const axis = this.getAxis();
    const up = vec3.up();
    const rel = head.sub(entrance);
    const flat = rel.projectOnPlane(up);
    const dist = flat.length;
    const azimuth = dist > 0.001 ? this.degrees(Math.acos(this.clamp(flat.normalize().dot(axis), -1, 1))) : 0;
    const elevation = this.degrees(Math.atan2(rel.y, Math.max(dist, 0.001)));

    const cAz = this.closeness(azimuth, -AZIMUTH_TOL_DEG, AZIMUTH_TOL_DEG);
    const cEl = this.closeness(elevation, ELEV_MIN_DEG, ELEV_MAX_DEG);
    const cDist = this.closeness(dist, DIST_MIN_CM, DIST_MAX_CM);
    const score = cAz * cEl * cDist;
    this.lastScore = score;
    const inside = azimuth <= AZIMUTH_TOL_DEG
      && elevation >= ELEV_MIN_DEG && elevation <= ELEV_MAX_DEG
      && dist >= DIST_MIN_CM && dist <= DIST_MAX_CM;

    if (this.debugLog) {
      this.debugTimer += dt;
      if (this.debugTimer >= 1) {
        this.debugTimer = 0;
        print('SunAlignment: az ' + azimuth.toFixed(1) + '° el ' + elevation.toFixed(1)
          + '° dist ' + dist.toFixed(0) + ' cm score ' + score.toFixed(2)
          + (inside ? ' INSIDE' : '') + (this.locked ? ' LOCKED' : ''));
      }
    }

    // --- Cues ---
    const cue = this.locked ? 1 : score;
    this.setAlpha(this.ringPass, (RING_MIN_ALPHA + (RING_MAX_ALPHA - RING_MIN_ALPHA) * cue) * this.ringFade);
    this.placeShaft(entrance, this.getDiscPosition(), cue * this.shaftFade);
    const glow = this.locked ? DISC_LOCKED_GLOW : 1 - (1 - DISC_ALIGNED_GLOW) * score;
    this.discGlow += (glow - this.discGlow) * (1 - Math.exp(-DISC_GLOW_SMOOTHING * dt));
    this.setDiscGlow(this.discGlow);

    // --- Lock ---
    if (!this.locked) {
      this.holdTimer = inside ? this.holdTimer + dt : 0;
      if (this.holdTimer >= HOLD_SEC) this.lock(head, entrance);
    } else if (this.captionTimer > 0 && !this.debugHoldCaption) {
      this.captionTimer -= dt;
      if (this.captionTimer <= 0 && this.caption) this.caption.enabled = false;
    }

    if (this.caption && this.caption.enabled) {
      this.keepInView(this.caption, head);
      this.faceViewer(this.caption, head);
      this.pointArrow();
    }
  }

  private lock(head: vec3, entrance: vec3) {
    this.locked = true;
    this.captionTimer = CAPTION_SEC;
    if (this.captionText) this.captionText.text = CAPTION_LOCKED;
    if (this.caption) {
      // Anchor in the gaze at the moment of lock: under the doorway the viewer is looking
      // along, pulled towards them so it floats just in front of the plinth's front face.
      const toHead = head.sub(entrance);
      const flat = new vec3(toHead.x, 0, toHead.z);
      const pullDir = flat.length > 0.001 ? flat.normalize() : this.getAxis();
      const pull = pullDir.uniformScale(this.captionTowardViewerCm);
      this.caption.getTransform().setWorldPosition(entrance.add(vec3.up().uniformScale(this.captionLiftCm)).add(pull));
      this.keepInView(this.caption, head);
      this.faceViewer(this.caption, head);
      this.pointArrow();
      this.caption.enabled = true;
    }
    print('ALIGNED');
    for (const l of this.alignedListeners) l();
  }

  // --- helpers ---

  /** 1 inside [lo, hi]; eases to 0 at CUE_FALLOFF tolerances outside the window. */
  private closeness(value: number, lo: number, hi: number): number {
    const halfWidth = (hi - lo) / 2;
    const excess = value < lo ? lo - value : value > hi ? value - hi : 0;
    const t = this.clamp(excess / (halfWidth * (CUE_FALLOFF - 1)), 0, 1);
    return 1 - t * t * (3 - 2 * t);
  }

  private placeKeyLight(sunPos: vec3, centre: vec3) {
    if (!this.keyLight) return;
    const t = this.keyLight.getSceneObject().getTransform();
    t.setWorldPosition(sunPos);
    if (this.keyLight.lightType === LightType.Directional) {
      // A directional LightSource emits along its object's -Z (like a camera looks), and
      // quat.lookAt aims +Z, so aim +Z from the temple back towards the sun to shine sun -> temple.
      // Verified in the preview on 28 Oct 2026 (façade, side wall and plinth top brighten).
      let aim = sunPos.sub(centre).normalize();
      if (this.lightFacesBackwards) aim = aim.uniformScale(-1);
      t.setWorldRotation(quat.lookAt(aim, vec3.up()));
    }
  }

  private placeShaft(from: vec3, to: vec3, cue: number) {
    if (!this.shaft) return;
    const alpha = SHAFT_MAX_ALPHA * cue * cue;
    this.setShaftGlow(alpha);
    this.shaft.enabled = alpha > 0.01;
    if (!this.shaft.enabled) return;
    const seg = to.sub(from);
    const len = seg.length;
    if (len < 0.01) return;
    const t = this.shaft.getTransform();
    t.setWorldPosition(from.add(seg.uniformScale(0.5)));
    t.setWorldRotation(quat.lookAt(seg.normalize(), vec3.up()));
    const w = SHAFT_WIDTH_CM * (0.4 + 0.6 * cue);
    t.setLocalScale(new vec3(w, w, len));
  }

  /**
   * Keeps obj inside the camera's field of view with its whole text block visible: the object
   * stays where it is while it fits, and is moved to the nearest in-view point when the head
   * turns or moves so that it would be clipped (a lazy follow, nothing moves while it fits).
   */
  private keepInView(obj: SceneObject, head: vec3) {
    if (!this.camera) return;
    const rot = this.camera.getTransform().getWorldRotation();
    const look = rot.multiplyVec3(new vec3(0, 0, -1));
    const right = rot.multiplyVec3(new vec3(1, 0, 0));
    const upv = rot.multiplyVec3(new vec3(0, 1, 0));
    const t = obj.getTransform();
    const v = t.getWorldPosition().sub(head);
    let z = Math.max(v.dot(look), CAPTION_MIN_DEPTH_CM);
    const fovV = this.cameraComp ? this.cameraComp.fov : 0.64;
    const aspect = this.cameraComp ? this.cameraComp.aspect : 0.73;
    const margin = (CAPTION_FOV_MARGIN_DEG * Math.PI) / 180;
    const halfV = fovV / 2;
    const halfH = Math.atan(Math.tan(halfV) * aspect);
    const limH = Math.max(halfH - Math.atan(this.captionHalfWidthCm / z) - margin, 0);
    const limV = Math.max(halfV - Math.atan(this.captionHalfHeightCm / z) - margin, 0);
    const ax = this.clamp(Math.atan2(v.dot(right), z), -limH, limH);
    const ay = this.clamp(Math.atan2(v.dot(upv), z), -limV, limV);
    const p = head.add(look.uniformScale(z)).add(right.uniformScale(z * Math.tan(ax))).add(upv.uniformScale(z * Math.tan(ay)));
    if (p.distance(t.getWorldPosition()) > 0.01) t.setWorldPosition(p);
  }

  /**
   * The visible disc: same azimuth and distance from the viewer as the light, raised by
   * DISC_RAISE_DEG, and further if needed so its lower edge clears the façade's top as seen
   * from the head: the highest of six points on the front and back top edges (seen from
   * above, the back edge is the visible top).
   */
  private raisedDisc(head: vec3, light: vec3): vec3 {
    const v = light.sub(head);
    const d = v.length;
    const flat = new vec3(v.x, 0, v.z);
    const fl = flat.length;
    if (d < 0.001 || fl < 0.001) return light;
    let topElev = -Math.PI / 2;
    for (const dz of [0, -this.facadeTopDepthCm]) {
      for (const dx of [-this.facadeTopHalfWidthCm, 0, this.facadeTopHalfWidthCm]) {
        const top = this.templePoint(this.facadeTopOffset.add(new vec3(dx, 0, dz))).sub(head);
        topElev = Math.max(topElev, Math.atan2(top.y, Math.sqrt(top.x * top.x + top.z * top.z)));
      }
    }
    const r = this.sun.getTransform().getWorldScale().x * 0.5;
    const rad = Math.PI / 180;
    const clear = topElev + Math.asin(Math.min(r / d, 1)) + DISC_CLEAR_DEG * rad;
    const e = Math.max(Math.atan2(v.y, fl) + DISC_RAISE_DEG * rad, clear);
    return head.add(flat.uniformScale((d * Math.cos(e)) / fl)).add(vec3.up().uniformScale(d * Math.sin(e)));
  }

  /** The disc material is additive, so brightness scales the base colour (as for the shaft). */
  private setDiscGlow(k: number) {
    if (!this.discPass || !this.discBaseColor) return;
    const b = this.discBaseColor;
    this.discPass.baseColor = new vec4(b.x * k, b.y * k, b.z * k, b.w);
  }

  /** A flat arrow pointing along local +X, one unit long, in the local XY plane. */
  private buildArrow(obj: SceneObject) {
    const rmv = obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
    if (!rmv) return;
    const mb = new MeshBuilder([
      { name: 'position', components: 3 },
      { name: 'normal', components: 3 },
      { name: 'texture0', components: 2 },
    ]);
    mb.topology = MeshTopology.Triangles;
    mb.indexType = MeshIndexType.UInt16;
    const pts = [[0.5, 0], [-0.05, 0.4], [-0.05, -0.4], [-0.5, 0.13], [-0.05, 0.13], [-0.05, -0.13], [-0.5, -0.13]];
    const verts: number[] = [];
    for (const p of pts) verts.push(p[0], p[1], 0, 0, 0, 1, p[0] + 0.5, p[1] + 0.5);
    mb.appendVerticesInterleaved(verts);
    mb.appendIndices([0, 1, 2, 3, 6, 5, 3, 5, 4]);
    mb.updateMesh();
    rmv.mesh = mb.getMesh();
  }

  /**
   * Puts the arrow beside the caption on the viewing spot's side and points it at the spot,
   * tilted at most ARROW_MAX_TILT_DEG from horizontal so it reads as "walk this way".
   */
  private pointArrow() {
    if (!this.captionArrow || !this.viewingSpot || !this.caption) return;
    const ct = this.caption.getTransform();
    const rot = ct.getWorldRotation();
    const rel = this.viewingSpot.getTransform().getWorldPosition().sub(ct.getWorldPosition());
    const rx = rel.dot(rot.multiplyVec3(new vec3(1, 0, 0)));
    const ry = rel.dot(rot.multiplyVec3(new vec3(0, 1, 0)));
    const side = rx < 0 ? -1 : 1;
    const maxTilt = (ARROW_MAX_TILT_DEG * Math.PI) / 180;
    const tilt = this.clamp(Math.atan2(ry, Math.abs(rx)), -maxTilt, maxTilt);
    const angle = side > 0 ? tilt : Math.PI - tilt;
    const at = this.captionArrow.getTransform();
    const p = at.getLocalPosition();
    at.setLocalPosition(new vec3(side * this.captionArrowOffset, p.y, p.z));
    at.setLocalRotation(quat.angleAxis(angle, new vec3(0, 0, 1)));
  }

  private faceViewer(obj: SceneObject, head: vec3) {
    const t = obj.getTransform();
    const d = head.sub(t.getWorldPosition());
    const yaw = Math.atan2(d.x, d.z);
    t.setWorldRotation(quat.angleAxis(yaw, vec3.up()));
  }

  /** Every RenderMeshVisual pass on an object and its children (the shaft is two crossed quads). */
  private collectPasses(obj: SceneObject | null): Pass[] {
    const out: Pass[] = [];
    if (!obj) return out;
    const p = this.passOf(obj);
    if (p) out.push(p);
    const n = obj.getChildrenCount();
    for (let i = 0; i < n; i++) {
      for (const c of this.collectPasses(obj.getChild(i))) out.push(c);
    }
    return out;
  }

  /**
   * The shaft material is additive, so brightness is driven by scaling the base colour
   * (and alpha) by k rather than by alpha alone.
   */
  private setShaftGlow(k: number) {
    const g = this.clamp(k, 0, 1);
    for (let i = 0; i < this.shaftPasses.length; i++) {
      const b = this.shaftBaseColors[i];
      this.shaftPasses[i].baseColor = new vec4(b.x * g, b.y * g, b.z * g, g);
    }
  }

  private passOf(obj: SceneObject | null): Pass | null {
    if (!obj) return null;
    const rmv = obj.getComponent('Component.RenderMeshVisual') as RenderMeshVisual | null;
    return rmv && rmv.mainMaterial ? rmv.mainMaterial.mainPass : null;
  }

  private setAlpha(pass: Pass | null, a: number) {
    if (!pass) return;
    const c = pass.baseColor as vec4;
    pass.baseColor = new vec4(c.x, c.y, c.z, this.clamp(a, 0, 1));
  }

  private clamp(v: number, lo: number, hi: number): number {
    return v < lo ? lo : v > hi ? hi : v;
  }

  private degrees(rad: number): number {
    return (rad * 180) / Math.PI;
  }
}
