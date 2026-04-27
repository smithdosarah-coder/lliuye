"use client";

/**
 * Gargantua · Interstellar (2014, Kip Thorne × Double Negative) 黑洞 1:1 视觉复刻
 *
 * Shader 血统：
 *   · Schwarzschild 测地线 Leapfrog 积分（u = 1/r 参数化）· 移植自 oseiskar/black-hole (MIT)
 *     https://github.com/oseiskar/black-hole
 *   · 黑体 T → RGB · Tanner Helland 近似（替代 spectrum LUT 纹理）
 *   · 程序化星场 + 程序化吸积盘（零外部贴图依赖）
 *   · FBM value-noise 驱动的盘面湍流 + dust-lane（替代三层 sin 带状）→ 摄影感/画意，去 CGI 塑料
 *
 * Nolan 艺术版规则（为视觉对称刻意关掉的物理）：
 *   · Doppler shift · 否则迎面蓝白 / 背面暗红刺眼
 *   · Relativistic beaming · 否则一侧亮度 ~100×
 *   · 引力红移颜色映射 · 仅保留几何弯曲
 *
 * 关键参数（以史瓦西半径 rs 为单位）：
 *   · 事件视界 r_h = 1 rs
 *   · 吸积盘 3 rs → 15 rs（物理上 ISCO = 3 rs；DNEG paint-swatch 9.26 M→18.70 M）
 *   · 盘温 6500 K（D65 近纯白 · DNEG 论文 James et al. 2015 原版 Gargantua · 非金非橙）
 *   · 盘色处理 = base blackbody × FBM dust-lane × 象牙 ecru 偏色 → 读作 sepia 白而非金
 *   · MAX_REVS 3.5 · 足以出现 2 阶 photon ring（黑球左右两道薄白弧）
 *   · 相机距 16 rs · 倾角 2.5°（Gargantua 近 edge-on · 盘成水平扁带 + 上方薄帽 + 下方 Einstein 月牙）
 *   · BH 屏幕正中 · 右侧 aside 改为浮动 glass card，让盘从卡片背后流过（不再硬偏左）
 */

import { useRef, useMemo, useEffect } from "react";
import { Canvas, useFrame, useThree, extend, type ThreeElement } from "@react-three/fiber";
import { ScreenQuad, shaderMaterial } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import * as THREE from "three";

/* ─── Gargantua fragment shader ────────────────────────────────────── */
const VERT = /* glsl */ `
  void main() {
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

const FRAG = /* glsl */ `
  precision highp float;

  uniform float uTime;
  uniform vec2  uResolution;
  uniform vec3  uCamPos;
  uniform vec3  uCamTarget;
  uniform int   uSteps;

  #define PI 3.14159265359
  #define MAX_REVS 3.5
  #define R_INNER  3.0
  #define R_OUTER  15.0
  #define DISK_T   6500.0

  // ── Tanner Helland blackbody T → RGB (1000-40000 K) ─────────────────
  vec3 temp2rgb(float T) {
    T = clamp(T, 1000.0, 40000.0) / 100.0;
    float r, g, b;
    if (T <= 66.0) r = 1.0;
    else r = clamp(1.29293618 * pow(T - 60.0, -0.1332047), 0.0, 1.0);
    if (T <= 66.0) g = clamp(0.39008157 * log(T) - 0.63184144, 0.0, 1.0);
    else g = clamp(1.12989086 * pow(T - 60.0, -0.0755148), 0.0, 1.0);
    if (T >= 66.0) b = 1.0;
    else if (T <= 19.0) b = 0.0;
    else b = clamp(0.54320679 * log(T - 10.0) - 1.19625408, 0.0, 1.0);
    return vec3(r, g, b);
  }

  float hash21(vec2 p) {
    p = fract(p * vec2(234.34, 435.345));
    p += dot(p, p + 34.23);
    return fract(p.x * p.y);
  }

  // ── Value-noise FBM（盘面湍流 · 取代三层 sin 条纹）──────────────────
  float vhash(vec2 p) {
    // 独立 hash · 与 hash21 的系数不同，避免与星场相干
    p = fract(p * vec2(127.1, 311.7));
    p += dot(p, p + 47.31);
    return fract(p.x * p.y * 0.5731);
  }
  float vnoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    // smoothstep 平滑插值，比 linear 少方格感
    vec2 u = f * f * (3.0 - 2.0 * f);
    float a = vhash(i);
    float b = vhash(i + vec2(1.0, 0.0));
    float c = vhash(i + vec2(0.0, 1.0));
    float d = vhash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
  }
  float fbm(vec2 p) {
    float v = 0.0;
    float amp = 0.5;
    float freq = 1.0;
    // 5 octaves
    for (int k = 0; k < 5; k++) {
      v += amp * vnoise(p * freq);
      freq *= 2.03;
      amp *= 0.5;
    }
    return v;
  }

  // ── 程序化星场（equirectangular + 2 层网格）────────────────────────
  vec3 starfield(vec3 dir) {
    vec2 uv = vec2(atan(dir.y, dir.x) / (2.0 * PI) + 0.5,
                   asin(clamp(dir.z, -1.0, 1.0)) / PI + 0.5);
    vec3 col = vec3(0.0);
    for (int L = 0; L < 2; L++) {
      float scale = 260.0 + float(L) * 180.0;
      vec2 g    = uv * scale;
      vec2 cell = floor(g);
      float h   = hash21(cell + float(L) * 17.19);
      float th  = 0.9968 - float(L) * 0.0008;
      if (h > th) {
        vec2 local = fract(g) - 0.5 -
          (vec2(hash21(cell + 3.7), hash21(cell + 7.1)) - 0.5) * 0.5;
        float d = length(local);
        float b = smoothstep(0.12, 0.0, d) * (0.4 + 0.6 * hash21(cell + 11.3));
        float T = 3000.0 + hash21(cell + 13.7) * 9000.0;
        col += temp2rgb(T) * b * (1.0 - float(L) * 0.3);
      }
    }
    // 极淡的银河尘带背景
    float haze = 0.5 + 0.5 * sin(uv.x * 6.3) * cos(uv.y * 3.7 + 1.0);
    col += vec3(0.006, 0.008, 0.015) * (0.4 + 0.6 * haze);
    return col;
  }

  // ── 程序化吸积盘（盘面 z=0）· FBM 湍流 + dust-lane · Hubble 摄影风 ──
  vec3 disk_emission(vec3 p) {
    float r   = length(p.xy);
    float phi = atan(p.y, p.x);

    // Shakura-Sunyaev 径向温度 T ∝ r^(-3/4)
    float ts   = pow(R_INNER / max(r, R_INNER), 0.75);
    float temp = DISK_T * ts;
    vec3  base = temp2rgb(temp);

    // 象牙 ecru 偏色 · 往暖灰白靠，避免纯 blackbody 出金橙
    vec3 ecru = vec3(1.0, 0.93, 0.80);
    vec3 tint = mix(ecru, base, 0.35);

    // Keplerian rotation Ω ∝ r^(-3/2) · 流体向前 shear 的 uv 坐标
    float omega   = uTime * 0.35 * pow(R_INNER / max(r, R_INNER), 1.5);
    float ustreak = phi + omega;

    // ── BRIGHT 湍流：高频 FBM · 顺流方向（ustreak）高频、径向（r）低频 → 丝状 ──
    // x 轴 = 流向（高频摆动），y 轴 = 半径（慢变） → 细丝顺着转圈方向拉长
    vec2 uv_bright = vec2(ustreak * 2.0 + r * 0.6, r * 1.8 + uTime * 0.2);
    float turb = fbm(uv_bright);
    // smoothstep 拉对比 · 让亮丝更立体而非糊平
    float bright = mix(0.5, 1.25, smoothstep(0.2, 0.85, turb));

    // ── DUST LANE：慢频率 FBM + smoothstep 锐化 · 与流向错位造成垂直切割感 ──
    // 第二层 uv 故意相位偏移 + 频率更低 + 方向微调，和 bright 纹理不重合
    vec2 uv_dust = vec2(ustreak * 0.9 - r * 0.25 + 3.7, r * 0.55 + uTime * 0.05);
    float dust_raw = fbm(uv_dust);
    // 锐化边缘 · 尘带要有明确的暗区轮廓，不是渐灰
    float dust = smoothstep(0.35, 0.62, dust_raw);

    float inner_mask = smoothstep(R_INNER,         R_INNER + 0.6, r);
    float outer_mask = smoothstep(R_OUTER,         R_OUTER - 3.0, r);
    float mask       = inner_mask * outer_mask;

    float lum = ts * ts * 2.0; // HDR · 白色本身能量密 · 由 bloom 负责发光

    // dust = 1 亮 / 0 暗 · 暗区压到 0.22，亮区保持 1.0
    return tint * bright * mix(0.22, 1.0, dust) * mask * lum;
  }

  // ── main ────────────────────────────────────────────────────────────
  void main() {
    vec2 p = (gl_FragCoord.xy * 2.0 - uResolution.xy) / uResolution.y;
    // BH 画面正中 · 构图由 CSS 的浮动 glass card + vignette 控制，不在 shader 里作弊

    // lookAt 相机基（世界 up = +z，与吸积盘法线同向）
    vec3 forward = normalize(uCamTarget - uCamPos);
    vec3 right   = normalize(cross(forward, vec3(0.0, 0.0, 1.0)));
    vec3 up      = cross(right, forward);
    float fovm   = 1.0 / tan(radians(52.0) * 0.5);
    vec3 ray     = normalize(p.x * right + p.y * up + fovm * forward);

    vec3 pos = uCamPos;
    vec3 color = vec3(0.0);

    // Schwarzschild geodesic · Leapfrog in u = 1/r
    float u = 1.0 / length(pos);
    vec3  nvec = normalize(pos);
    vec3  tvec = normalize(cross(cross(nvec, ray), nvec));
    float du   = -dot(ray, nvec) / dot(ray, tvec) * u;
    float phi  = 0.0;
    float step = MAX_REVS * 2.0 * PI / float(uSteps);

    vec3 old_pos = pos;
    bool hit_horizon = false;

    for (int i = 0; i < 256; i++) {
      if (i >= uSteps) break;

      // Leapfrog
      u += du * step;
      float ddu = -u * (1.0 - 1.5 * u * u);
      du += ddu * step;
      if (u < 0.0) break;
      phi += step;
      old_pos = pos;
      pos = (cos(phi) * nvec + sin(phi) * tvec) / u;

      // 吸积盘平面 z = 0 的交叉
      if (old_pos.z * pos.z < 0.0) {
        vec3  seg = pos - old_pos;
        float t   = -old_pos.z / seg.z;
        vec3  isc = old_pos + seg * t;
        float rh  = length(isc.xy);
        if (rh > R_INNER && rh < R_OUTER) {
          // 累加（盘为发射源，多次穿越 → 多像叠加，透镜上下两像自然出现）
          color += disk_emission(isc);
        }
      }

      if (u > 1.0) { hit_horizon = true; break; } // 落入事件视界
    }

    if (!hit_horizon) {
      vec3 exit_dir = normalize(pos - old_pos);
      color += starfield(exit_dir);
    }

    // 轻度伽马 · 最终 tone mapping 交给 R3F 的 ACESFilmic + Bloom
    gl_FragColor = vec4(color, 1.0);
  }
`;

const BlackHoleMaterial = shaderMaterial(
  {
    uTime: 0,
    uResolution: new THREE.Vector2(1, 1),
    uCamPos: new THREE.Vector3(15.985, 0, 0.698),
    uCamTarget: new THREE.Vector3(0, 0, 0),
    uSteps: 200,
  },
  VERT,
  FRAG,
);

extend({ BlackHoleMaterial });

declare module "@react-three/fiber" {
  interface ThreeElements {
    blackHoleMaterial: ThreeElement<typeof BlackHoleMaterial>;
  }
}

/* ─── Scene quad ────────────────────────────────────────────────────── */
function BlackHoleQuad() {
  const matRef = useRef<THREE.ShaderMaterial & {
    uTime: number;
    uResolution: THREE.Vector2;
    uCamPos: THREE.Vector3;
    uCamTarget: THREE.Vector3;
    uSteps: number;
  }>(null!);
  const { size, viewport } = useThree();

  const camConfig = useMemo(
    () => ({
      rxy: 15.985, // 16 · cos(2.5°) · 近 edge-on 视角
      z: 0.698,    // 16 · sin(2.5°)
      period: 480, // 轨道周期 · 秒
    }),
    [],
  );

  useEffect(() => {
    if (matRef.current) {
      matRef.current.uResolution.set(
        size.width * viewport.dpr,
        size.height * viewport.dpr,
      );
    }
  }, [size.width, size.height, viewport.dpr]);

  useFrame((state) => {
    if (!matRef.current) return;
    const t = state.clock.elapsedTime;
    matRef.current.uTime = t;
    const ang = (t / camConfig.period) * Math.PI * 2.0;
    matRef.current.uCamPos.set(
      camConfig.rxy * Math.cos(ang),
      camConfig.rxy * Math.sin(ang),
      camConfig.z,
    );
  });

  return (
    <ScreenQuad>
      <blackHoleMaterial ref={matRef} key={BlackHoleMaterial.key} />
    </ScreenQuad>
  );
}

/* ─── Exported component ────────────────────────────────────────────── */
export function CosmicStageR3F() {
  return (
    <div className="cosmic" aria-hidden>
      <div className="cosmic__r3f-stage">
        <Canvas
          orthographic
          camera={{ position: [0, 0, 1], near: 0, far: 1, zoom: 1 }}
          dpr={[1, 2]}
          gl={{
            alpha: false,
            antialias: false,
            toneMapping: THREE.ACESFilmicToneMapping,
            toneMappingExposure: 0.9,
            powerPreference: "high-performance",
          }}
        >
          <color attach="background" args={["#02030a"]} />
          <BlackHoleQuad />
          <EffectComposer multisampling={0}>
            <Bloom
              luminanceThreshold={0.85}
              luminanceSmoothing={0.9}
              intensity={0.85}
              mipmapBlur
            />
          </EffectComposer>
        </Canvas>
      </div>
      <div className="cosmic__vignette" />
    </div>
  );
}
