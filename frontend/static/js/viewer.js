/* Minimal Three.js based 360 equirectangular panorama viewer.
   Renders the panorama on the inside of a sphere and lets the user
   drag/swipe to look around and zoom via the camera FOV. */

class PanoramaViewer {
  constructor(container) {
    this.container = container;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(this.renderer.domElement);

    const geometry = new THREE.SphereGeometry(500, 60, 40);
    geometry.scale(-1, 1, 1); // view from inside

    this.material = new THREE.MeshBasicMaterial({ color: 0x222222 });
    this.mesh = new THREE.Mesh(geometry, this.material);
    this.scene.add(this.mesh);

    this.lon = 0;
    this.lat = 0;
    this.isDragging = false;
    this.prevX = 0;
    this.prevY = 0;

    this._bindEvents();
    this._animate();

    window.addEventListener("resize", () => this._onResize());
  }

  loadImage(url) {
    const loader = new THREE.TextureLoader();
    loader.load(
      url,
      (texture) => {
        texture.minFilter = THREE.LinearFilter;
        this.material.map = texture;
        this.material.color.set(0xffffff);
        this.material.needsUpdate = true;
        if (this.onLoaded) this.onLoaded();
      },
      undefined,
      () => { if (this.onError) this.onError(); }
    );
  }

  _bindEvents() {
    const dom = this.renderer.domElement;

    const start = (x, y) => { this.isDragging = true; this.prevX = x; this.prevY = y; };
    const move = (x, y) => {
      if (!this.isDragging) return;
      const dx = x - this.prevX;
      const dy = y - this.prevY;
      this.lon -= dx * 0.2;
      this.lat += dy * 0.2;
      this.lat = Math.max(-85, Math.min(85, this.lat));
      this.prevX = x;
      this.prevY = y;
    };
    const end = () => { this.isDragging = false; };

    dom.addEventListener("mousedown", (e) => start(e.clientX, e.clientY));
    window.addEventListener("mousemove", (e) => move(e.clientX, e.clientY));
    window.addEventListener("mouseup", end);

    dom.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) start(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });
    dom.addEventListener("touchmove", (e) => {
      if (e.touches.length === 1) move(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });
    dom.addEventListener("touchend", end);

    dom.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.zoom(e.deltaY > 0 ? 5 : -5);
    }, { passive: false });

    // Basic pinch-to-zoom
    let lastPinchDist = null;
    dom.addEventListener("touchmove", (e) => {
      if (e.touches.length === 2) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        if (lastPinchDist != null) {
          this.zoom((lastPinchDist - dist) * 0.1);
        }
        lastPinchDist = dist;
      }
    }, { passive: true });
    dom.addEventListener("touchend", () => { lastPinchDist = null; });
  }

  zoom(delta) {
    this.camera.fov = Math.max(30, Math.min(100, this.camera.fov + delta));
    this.camera.updateProjectionMatrix();
  }

  _onResize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  _animate() {
    requestAnimationFrame(() => this._animate());
    const phi = THREE.MathUtils.degToRad(90 - this.lat);
    const theta = THREE.MathUtils.degToRad(this.lon);
    const target = new THREE.Vector3(
      500 * Math.sin(phi) * Math.cos(theta),
      500 * Math.cos(phi),
      500 * Math.sin(phi) * Math.sin(theta)
    );
    this.camera.lookAt(target);
    this.renderer.render(this.scene, this.camera);
  }
}
