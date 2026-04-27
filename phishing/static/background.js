/**
 * AnoAI Aurora Background
 * Vanilla JS port of the React/Three.js shader background component.
 * Renders a full-screen GLSL aurora / nebula animation behind the dashboard.
 */
(function () {
  'use strict';

  // ── Container ─────────────────────────────────────────────────────────────
  const container = document.createElement('div');
  container.id = 'ano-bg';
  container.setAttribute('aria-hidden', 'true');
  container.style.cssText = [
    'position:fixed',
    'inset:0',
    'z-index:-1',
    'pointer-events:none',
    'overflow:hidden',
  ].join(';');
  document.body.insertBefore(container, document.body.firstChild);

  // ── Three.js scene ────────────────────────────────────────────────────────
  const scene    = new THREE.Scene();
  const camera   = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;';
  container.appendChild(renderer.domElement);

  // ── Shaders ───────────────────────────────────────────────────────────────
  const vertexShader = /* glsl */`
    void main() {
      gl_Position = vec4(position, 1.0);
    }
  `;

  const fragmentShader = /* glsl */`
    uniform float iTime;
    uniform vec2  iResolution;

    #define NUM_OCTAVES 3

    float rand(vec2 n) {
      return fract(sin(dot(n, vec2(12.9898, 4.1414))) * 43758.5453);
    }

    float noise(vec2 p) {
      vec2 ip = floor(p);
      vec2 u  = fract(p);
      u = u * u * (3.0 - 2.0 * u);
      return mix(
        mix(rand(ip),               rand(ip + vec2(1.0, 0.0)), u.x),
        mix(rand(ip + vec2(0.0,1.0)), rand(ip + vec2(1.0,1.0)), u.x),
        u.y
      );
    }

    float fbm(vec2 x) {
      float v   = 0.0;
      float a   = 0.3;
      vec2 shift = vec2(100.0);
      mat2 rot  = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.5));
      for (int i = 0; i < NUM_OCTAVES; ++i) {
        v   += a * noise(x);
        x    = rot * x * 2.0 + shift;
        a   *= 0.4;
      }
      return v;
    }

    void main() {
      vec2 shake = vec2(sin(iTime * 1.2) * 0.005, cos(iTime * 2.1) * 0.005);
      vec2 p = ((gl_FragCoord.xy + shake * iResolution.xy)
                - iResolution.xy * 0.5) / iResolution.y
               * mat2(6.0, -4.0, 4.0, 6.0);

      vec4 o = vec4(0.0);
      float f = 2.0 + fbm(p + vec2(iTime * 5.0, 0.0)) * 0.5;

      for (float i = 0.0; i < 35.0; i++) {
        vec2 v = p
          + cos(i * i + (iTime + p.x * 0.08) * 0.025 + i * vec2(13.0, 11.0)) * 3.5
          + vec2(sin(iTime * 3.0 + i) * 0.003, cos(iTime * 3.5 - i) * 0.003);

        float tailNoise = fbm(v + vec2(iTime * 0.5, i)) * 0.3 * (1.0 - (i / 35.0));

        vec4 auroraColors = vec4(
          0.1 + 0.3 * sin(i * 0.2 + iTime * 0.4),
          0.3 + 0.5 * cos(i * 0.3 + iTime * 0.5),
          0.7 + 0.3 * sin(i * 0.4 + iTime * 0.3),
          1.0
        );

        vec4 contribution = auroraColors
          * 1.8
          / (length(max(v, vec2(v.x * f * 0.015, v.y * 1.5))) + 0.4);

        float thinness = smoothstep(0.0, 1.0, i / 35.0) * 0.6;
        o += contribution * (1.0 + tailNoise * 0.4) * thinness;
      }

      o = tanh(pow(o / 100.0, vec4(1.6)));
      gl_FragColor = o * 1.5;
    }
  `;

  // ── Mesh ──────────────────────────────────────────────────────────────────
  const material = new THREE.ShaderMaterial({
    uniforms: {
      iTime:       { value: 0.0 },
      iResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
    },
    vertexShader,
    fragmentShader,
    transparent: true,
  });

  const geometry = new THREE.PlaneGeometry(2, 2);
  const mesh     = new THREE.Mesh(geometry, material);
  scene.add(mesh);

  // ── Animation loop ────────────────────────────────────────────────────────
  let frameId;
  function animate() {
    material.uniforms.iTime.value += 0.016;
    renderer.render(scene, camera);
    frameId = requestAnimationFrame(animate);
  }
  animate();

  // ── Resize handler ────────────────────────────────────────────────────────
  function onResize() {
    renderer.setSize(window.innerWidth, window.innerHeight);
    material.uniforms.iResolution.value.set(window.innerWidth, window.innerHeight);
  }
  window.addEventListener('resize', onResize);

}());
