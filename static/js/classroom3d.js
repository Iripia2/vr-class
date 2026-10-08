// Browser-based 3D classroom scene using Three.js (no headset required).
(function () {
  const canvas = document.getElementById('classroom-canvas');
  if (!canvas || typeof THREE === 'undefined') return;

  const width = canvas.clientWidth || canvas.parentElement.clientWidth;
  const height = 520;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x12201b);
  scene.fog = new THREE.Fog(0x12201b, 12, 30);

  const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 100);
  camera.position.set(0, 6, 11);

  const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
  renderer.setSize(width, height, false);
  renderer.setPixelRatio(window.devicePixelRatio || 1);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1.5, 0);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI / 2.1;
  controls.minDistance = 4;
  controls.maxDistance = 20;

  // Lighting
  scene.add(new THREE.HemisphereLight(0xe9e4d6, 0x1a2b23, 0.9));
  const spot = new THREE.SpotLight(0xffe9b0, 1.1, 30, Math.PI / 5, 0.4);
  spot.position.set(0, 9, 4);
  spot.target.position.set(0, 0, -2);
  scene.add(spot, spot.target);

  // Floor
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(24, 24),
    new THREE.MeshStandardMaterial({ color: 0x1f2e28, roughness: 0.9 })
  );
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);

  // Front wall + board
  const wall = new THREE.Mesh(
    new THREE.PlaneGeometry(24, 8),
    new THREE.MeshStandardMaterial({ color: 0x16211d, roughness: 1 })
  );
  wall.position.set(0, 4, -8);
  scene.add(wall);

  const board = new THREE.Mesh(
    new THREE.PlaneGeometry(6, 2.6),
    new THREE.MeshStandardMaterial({ color: 0x283b33, roughness: 0.6 })
  );
  board.position.set(0, 3.2, -7.9);
  scene.add(board);

  // Teacher podium
  const podium = new THREE.Mesh(
    new THREE.CylinderGeometry(0.6, 0.7, 1.1, 24),
    new THREE.MeshStandardMaterial({ color: 0xc79a2b, roughness: 0.5 })
  );
  podium.position.set(0, 0.55, -5);
  scene.add(podium);

  // Student desks arranged in an arc
  const deskGeo = new THREE.BoxGeometry(1.1, 0.6, 0.7);
  const seatGeo = new THREE.SphereGeometry(0.35, 16, 16);
  const deskMat = new THREE.MeshStandardMaterial({ color: 0xa9b99e, roughness: 0.8 });
  const seatColors = [0xc79a2b, 0x8fa98a, 0xb5c4a8, 0xdcc077];

  const rows = [3, 6];
  let colorIndex = 0;
  rows.forEach((count, rowIndex) => {
    const radius = 4 + rowIndex * 2.6;
    const arcSpan = Math.PI * 0.62;
    for (let i = 0; i < count; i++) {
      const t = count === 1 ? 0.5 : i / (count - 1);
      const angle = -arcSpan / 2 + t * arcSpan;
      const x = Math.sin(angle) * radius;
      const z = -1 + Math.cos(angle) * radius * 0.4;

      const desk = new THREE.Mesh(deskGeo, deskMat);
      desk.position.set(x, 0.3, z);
      desk.rotation.y = -angle;
      scene.add(desk);

      const seat = new THREE.Mesh(
        seatGeo,
        new THREE.MeshStandardMaterial({ color: seatColors[colorIndex % seatColors.length], roughness: 0.5 })
      );
      seat.position.set(x, 0.95, z + 0.5);
      scene.add(seat);
      colorIndex++;
    }
  });

  function onResize() {
    const w = canvas.parentElement.clientWidth;
    camera.aspect = w / height;
    camera.updateProjectionMatrix();
    renderer.setSize(w, height, false);
  }
  window.addEventListener('resize', onResize);
  onResize();

  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();
})();
