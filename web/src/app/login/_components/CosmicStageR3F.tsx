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
 * F4 v2 (V4 plan · 2026-05-01 · per da030a1 brief) · 视觉对齐 awwwards-2022 5 点:
 *   · #1 吸积盘色温梯度 紫→红→橙→白 (替 v1 single champagne · disk T = lerp(3000, 15000, r→inner))
 *   · #2 重力透镜弯曲 (上下双道光环 · ✅ 现有 Schwarzschild geodesic photon ring · MAX_REVS 3.5)
 *   · #3 chromatic aberration 星点 (RGB 通道屏 uv 偏移 · 距 center 越远偏移越大)
 *   · #4 film grain noise overlay (hash21 高频噪声 + uTime 飞动 · 0.04 强度)
 *   · #5 event horizon shadow (✅ 现有 hit_horizon → black 中心倒梯形 distortion 由 geodesic 自然产生)
 *
 * Nolan 艺术版规则（为视觉对称刻意关掉的物理）：
 *   · Doppler shift · 否则迎面蓝白 / 背面暗红刺眼
 *   · Relativistic beaming · 否则一侧亮度 ~100×
 *   · 引力红移颜色映射 · 仅保留几何弯曲
 *
 * 关键参数（以史瓦西半径 rs 为单位）：
 *   · 事件视界 r_h = 1 rs
 *   · 吸积盘 3 rs → 15 rs（物理上 ISCO = 3 rs；DNEG paint-swatch 9.26 M→18.70 M）
 *   · F4 v2 盘温梯度: 内缘 15000 K (蓝紫) · 外缘 3000 K (红橙) · 黑体真实物理 + awwwards 美学
 *   · 盘色处理 = blackbody temp2rgb(T(r)) × FBM dust-lane (替 v1 champagne 单色)
 *   · MAX_REVS 3.5 / uSteps 280 · 足以出现 2 阶 photon ring 无层切割
 *   · 相机距 14.5 rs · 倾角 2.5°（Gargantua 近 edge-on · 盘成水平扁带 + 上方薄帽 + 下方 Einstein 月牙）
 *   · 背景：near-black + 稀疏星场（haze 压到 0.001，去银河尘带 sin 带感）
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

  // ── 程序化星场 · 深空近黑底 · 稀疏星点（2026-04-21 用户要"真实宇宙的深邃"） ──
  // F4 v2 (2026-05-01 · iter 2) · PM brief #3 verbatim "chromatic aberration starfield"
  //   星点 RGB 三通道分别 sample dir + 微偏移 → 红绿蓝色散星 (rim 透镜畸变样)
  //   偏移量与星点距 cell center 距相关 · cell 边缘色散最强 (镜头边缘畸变规律)
  vec3 starfield(vec3 dir) {
    // 三通道 dir 略偏 (RGB chromatic aberration) · 偏移轴线 dir.xz 螺旋方向
    // 偏移强度 0.0018 = 边缘星点视觉可见红绿色散 · 不破中心精度
    vec3 dirR = normalize(dir + vec3( 0.0018, 0.0,  0.0009));
    vec3 dirB = normalize(dir + vec3(-0.0018, 0.0, -0.0009));
    vec3 col = vec3(0.0);

    for (int CH = 0; CH < 3; CH++) {
      // 通道 0=R · 1=G · 2=B · 用对应 dir variant
      vec3 d = (CH == 0) ? dirR : (CH == 2) ? dirB : dir;
      vec2 uv = vec2(atan(d.y, d.x) / (2.0 * PI) + 0.5,
                     asin(clamp(d.z, -1.0, 1.0)) / PI + 0.5);
      for (int L = 0; L < 2; L++) {
        float scale = 380.0 + float(L) * 220.0;
        vec2 g    = uv * scale;
        vec2 cell = floor(g);
        float h   = hash21(cell + float(L) * 17.19);
        float th  = 0.9986 - float(L) * 0.0008;
        if (h > th) {
          vec2 local = fract(g) - 0.5 -
            (vec2(hash21(cell + 3.7), hash21(cell + 7.1)) - 0.5) * 0.5;
          float dist = length(local);
          float b = smoothstep(0.10, 0.0, dist) * (0.4 + 0.6 * hash21(cell + 11.3));
          float T = 3000.0 + hash21(cell + 13.7) * 9000.0;
          vec3 starCol = temp2rgb(T) * b * (1.0 - float(L) * 0.3);
          // 仅取对应通道 · 三 dir variant 三通道叠加 = 真 chromatic aberration
          if (CH == 0) col.r += starCol.r;
          else if (CH == 1) col.g += starCol.g;
          else              col.b += starCol.b;
        }
      }
    }
    // 极暗 ambient · 读作黑
    col += vec3(0.0008, 0.001, 0.0022);
    return col;
  }

  // ── 程序化吸积盘（盘面 z=0）· FBM 湍流 + dust-lane · Hubble 摄影风 ──
  //
  // v7（2026-04-22）· 根治 atan phi branch-cut seam：
  //   旧版用 phi = atan(y, x) 作为 uv 坐标 → phi 在 -x 轴从 +π 跳 -π，
  //   fbm(ustreak, r) 沿 -x 径向产生不连续"割裂光带"。
  //   改法：把湍流采样坐标整体搬到 Keplerian 反卷 q-frame
  //         q(x,y,t) = rot(-omega(r)) · (x,y)
  //   q 是 (x,y,t) 的 C¹ 连续函数（omega 只依赖 r，rotation matrix 连续），
  //   丝状感由 omega(r) ∝ r^(-3/2) 的径向强剪切自然浮现（相邻 r 反卷角不同
  //   → 切线向拉伸 noise 特征），不再需要 phi。
  vec3 disk_emission(vec3 p) {
    float r = length(p.xy);

    // ── F4 v2 (2026-05-01 · iter 2) 色温梯度 紫→红→橙→白 ──
    // PM brief #1 verbatim · iter 1 (22b12c4) tsRaw=pow(0.75) 集中中高温 · 外缘没真红
    // iter 2: tsRaw 改 smoothstep(R_OUTER, R_INNER, r) · linear remap 真展开全段
    //   r=R_OUTER (15) → tsRaw=0 → diskT=2800K (深红橙)
    //   r=10 → tsRaw=0.42 → diskT=10000K (黄白)
    //   r=R_INNER (3) → tsRaw=1 → diskT=21000K (蓝紫)
    // 4 段色温阶: 2800→6000→12000→21000 · 视觉真"紫→红→橙→白"全段
    float tsRaw  = smoothstep(R_OUTER, R_INNER, r);
    float diskT  = mix(2800.0, 21000.0, tsRaw);    // 外缘红 → 内缘紫 (黑体真物理)
    vec3  bbColor = temp2rgb(diskT);
    // 径向亮度 0.40→1.25：外缘更暗 · 内边更亮 (HDR 源头 · iter 2 加强 Bloom 拾光)
    float tintLift = mix(0.40, 1.25, tsRaw);
    vec3  tint     = bbColor * tintLift;

    // Keplerian 反卷：omega 只依赖 r，rotation matrix 全处处连续
    float omega = uTime * 0.35 * pow(R_INNER / max(r, R_INNER), 1.5);
    float co    = cos(-omega);
    float so    = sin(-omega);
    vec2  q     = vec2(co * p.x - so * p.y, so * p.x + co * p.y);

    // ── BRIGHT 湍流：scale 2.4→1.6 让斑块更大，配合 omega 剪切拉成丝 ──
    vec2  uv_bright = q * 1.6 + vec2(uTime * 0.08, uTime * 0.05);
    float turb      = fbm(uv_bright);
    float bright    = mix(0.5, 1.25, smoothstep(0.2, 0.85, turb));

    // ── DUST LANE 锐化（v9）：阈值 (0.35,0.62)→(0.40,0.55) 暗带锐利，
    //    暗区最暗 0.18→0.08 更深 → 参考图 dust 明显分层 ──
    vec2  uv_dust   = q * 0.55 + vec2(3.7 + uTime * 0.015, uTime * 0.012);
    float dust_raw  = fbm(uv_dust);
    float dust      = smoothstep(0.40, 0.55, dust_raw);

    // 软边 mask · 内外各拉宽（2026-04-21 修红框右上"层切"）
    // 内边 0.6 → 1.4 rs，外边 3.0 → 5.0 rs，消除 photon ring 与直接像 R_OUTER 硬切
    float inner_mask = smoothstep(R_INNER,         R_INNER + 1.4, r);
    float outer_mask = smoothstep(R_OUTER,         R_OUTER - 5.0, r);
    float mask       = inner_mask * outer_mask;

    float lum = tsRaw * tsRaw * 2.0; // HDR · 亮度能量密 · 由 bloom 负责发光

    // dust = 1 亮 / 0 暗 · 暗区从 0.18 压至 0.08（更接近参考图深黑褐 dust lane）
    return tint * bright * mix(0.08, 1.0, dust) * mask * lum;
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

    // ── F4 v2 (2026-05-01) #3 · chromatic aberration ──
    // 镜头畸变样 RGB 分离 · 距画面 center 越远色散越强 (边缘最明显)
    // 不二次 ray cast (成本太高) · post-process 通道增益 trick
    float ca = length(p) * 0.022; // 0.022 = 边缘 ~5% 增益
    color.r *= 1.0 + ca * 0.45;
    color.g *= 1.0 + ca * 0.05;
    color.b *= 1.0 - ca * 0.35;

    // ── F4 v2 (2026-05-01) #4 · film grain noise overlay ──
    // hash21 高频噪声 + uTime 飞动 · 0.04 强度 (老电影颗粒感 · 不抢主体)
    float grain = hash21(gl_FragCoord.xy + uTime * 60.0) * 0.04 - 0.02;
    color += vec3(grain);

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
    uSteps: 280,
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
      /* 2026-04-23 · visual-v3/P7 · Codex "更大" 指令 · 相机拉近 16 → 14.5 rs
         视觉占比 ~+10% · 仍在 3-15 rs 盘面外安全距离 · 倾角保持 2.5° */
      rxy: 14.5 * Math.cos((2.5 * Math.PI) / 180), // ≈ 14.486
      z:   14.5 * Math.sin((2.5 * Math.PI) / 180), // ≈ 0.633
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
            /* 2026-04-23 · visual-v3/P7 · Codex 电影化指令
               toneMappingExposure 0.82 → 0.74 · 亮部更锐 · 深处更深 · 不发雾 */
            toneMappingExposure: 0.74,
            powerPreference: "high-performance",
          }}
        >
          <color attach="background" args={["#010106"]} />
          <BlackHoleQuad />
          <EffectComposer multisampling={0}>
            {/* F4 v2 (2026-05-01 · iter 2) · awwwards 色彩感强化
                threshold 0.95 → 0.85 (中段色温也拾 bloom · 紫蓝光真出来)
                intensity 0.26 → 0.42 (色彩晕开更显 · 不抢主体)
                · 配合 disk 色温梯度 2800K-21000K 全段展开 · 紫红橙白真渲 */}
            <Bloom
              luminanceThreshold={0.85}
              luminanceSmoothing={0.85}
              intensity={0.42}
              mipmapBlur
            />
          </EffectComposer>
        </Canvas>
      </div>
      <div className="cosmic__vignette" />
    </div>
  );
}
