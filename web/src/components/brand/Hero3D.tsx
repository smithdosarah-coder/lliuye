"use client";

import { useRef, useMemo, useEffect, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import {
  Environment,
  MeshReflectorMaterial,
  Lightformer,
  Line,
  Stars,
  Sparkles,
} from "@react-three/drei";
import {
  EffectComposer,
  Bloom,
  Vignette,
} from "@react-three/postprocessing";
import * as THREE from "three";

const SOLAR_CENTER: [number, number, number] = [1.95, 1.0, 0];

interface PlanetSpec {
  name: string;
  orbitRadius: number;
  orbitSpeed: number;
  tilt: number;
  phase: number;
  size: number;
  color: string;
  roughness?: number;
  hasRing?: boolean;
  ringColor?: string;
}

// 仿太阳系（缩放 + 艺术化）—— 颜色对应"匹配度高低"：
// 内圈 = 高匹配候选；外圈 = 远距离 look-alike
const PLANETS: PlanetSpec[] = [
  { name: "水", orbitRadius: 0.78, orbitSpeed: 0.7, tilt: 0.05, phase: 0.0, size: 0.055, color: "#9a958a", roughness: 0.85 },
  { name: "金", orbitRadius: 1.0, orbitSpeed: 0.52, tilt: -0.08, phase: 1.4, size: 0.085, color: "#d4ae78", roughness: 0.7 },
  { name: "地", orbitRadius: 1.22, orbitSpeed: 0.42, tilt: 0.1, phase: 2.7, size: 0.095, color: "#5a92c8", roughness: 0.6 },
  { name: "火", orbitRadius: 1.45, orbitSpeed: 0.34, tilt: -0.14, phase: 3.9, size: 0.07, color: "#b56850", roughness: 0.75 },
  { name: "木", orbitRadius: 1.85, orbitSpeed: 0.22, tilt: 0.06, phase: 5.0, size: 0.18, color: "#d4b088", roughness: 0.65 },
  { name: "土", orbitRadius: 2.28, orbitSpeed: 0.16, tilt: -0.2, phase: 0.8, size: 0.15, color: "#e0c890", roughness: 0.7, hasRing: true, ringColor: "#cdb284" },
  { name: "天", orbitRadius: 2.65, orbitSpeed: 0.12, tilt: 0.18, phase: 2.3, size: 0.1, color: "#9bc4d0", roughness: 0.55 },
];

const ORBIT_RINGS = PLANETS.map((p) => ({
  radius: p.orbitRadius,
  tilt: p.tilt,
  opacity: 0.06 + Math.max(0, 0.12 - p.orbitRadius * 0.04),
}));

// 生成气态巨行星条纹纹理（Jupiter/Saturn 用）
function useBandTexture(baseColor: string, accentColor: string, seed = 1) {
  const [tex, setTex] = useState<THREE.CanvasTexture | null>(null);
  useEffect(() => {
    const c = document.createElement("canvas");
    c.width = 512;
    c.height = 256;
    const ctx = c.getContext("2d")!;
    // 背景
    ctx.fillStyle = baseColor;
    ctx.fillRect(0, 0, c.width, c.height);
    // 条纹：水平分带，不同深浅
    const bands = 14;
    for (let i = 0; i < bands; i++) {
      const y = (i / bands) * c.height;
      const h = c.height / bands;
      const v = Math.sin(i * 1.7 + seed) * 0.5 + 0.5;
      ctx.fillStyle = v > 0.55 ? accentColor : baseColor;
      ctx.globalAlpha = 0.35 + v * 0.4;
      ctx.fillRect(0, y, c.width, h);
      // 扰动条纹（更像流体）
      ctx.globalAlpha = 0.18;
      for (let x = 0; x < c.width; x += 32) {
        ctx.fillStyle = v > 0.6 ? "#ffffff" : "#000000";
        ctx.fillRect(
          x,
          y + Math.sin((x + seed * 100) * 0.03) * h * 0.3,
          32,
          h * 0.4
        );
      }
    }
    ctx.globalAlpha = 1;
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    setTex(t);
    return () => t.dispose();
  }, [baseColor, accentColor, seed]);
  return tex;
}

function Planet({ spec, idx }: { spec: PlanetSpec; idx: number }) {
  const groupRef = useRef<THREE.Group>(null);
  // 仅给大行星（木/土）加条纹纹理
  const bandTex = useBandTexture(
    spec.color,
    spec.color === "#d4b088" ? "#a88258" : "#b89860",
    idx
  );
  const useBands = spec.size > 0.12;

  useFrame((state) => {
    const t = state.clock.elapsedTime * spec.orbitSpeed + spec.phase;
    const x = Math.cos(t) * spec.orbitRadius;
    const z = Math.sin(t) * spec.orbitRadius * Math.cos(spec.tilt);
    const y = Math.sin(t) * spec.orbitRadius * Math.sin(spec.tilt);
    if (groupRef.current) {
      groupRef.current.position.set(
        SOLAR_CENTER[0] + x,
        SOLAR_CENTER[1] + y,
        SOLAR_CENTER[2] + z
      );
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.45;
    }
  });
  return (
    <group ref={groupRef}>
      <mesh castShadow receiveShadow>
        <sphereGeometry args={[spec.size, 96, 96]} />
        <meshStandardMaterial
          color={useBands ? "#ffffff" : spec.color}
          map={useBands ? bandTex ?? undefined : undefined}
          roughness={spec.roughness ?? 0.7}
          metalness={0.05}
        />
      </mesh>
      {spec.hasRing && (
        <mesh rotation={[Math.PI / 2 - 0.45, 0, 0]}>
          <ringGeometry args={[spec.size * 1.55, spec.size * 2.3, 128]} />
          <meshBasicMaterial
            color={spec.ringColor ?? "#cdb284"}
            transparent
            opacity={0.55}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}
    </group>
  );
}

function OrbitRing({
  radius,
  tilt,
  opacity,
}: {
  radius: number;
  tilt: number;
  opacity: number;
}) {
  const points = useMemo(() => {
    const arr: [number, number, number][] = [];
    const segments = 128;
    for (let i = 0; i <= segments; i++) {
      const a = (i / segments) * Math.PI * 2;
      const x = Math.cos(a) * radius;
      const z = Math.sin(a) * radius * Math.cos(tilt);
      const y = Math.sin(a) * radius * Math.sin(tilt);
      arr.push([
        SOLAR_CENTER[0] + x,
        SOLAR_CENTER[1] + y,
        SOLAR_CENTER[2] + z,
      ]);
    }
    return arr;
  }, [radius, tilt]);

  return (
    <Line
      points={points}
      color="#a8b8cc"
      lineWidth={0.5}
      transparent
      opacity={opacity}
    />
  );
}

function Sun() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((s) => {
    if (ref.current) ref.current.rotation.y = s.clock.elapsedTime * 0.1;
  });
  return (
    <group position={SOLAR_CENTER}>
      {/* 主太阳 —— emissive 自发光 */}
      <mesh ref={ref}>
        <sphereGeometry args={[0.42, 64, 64]} />
        <meshBasicMaterial color="#ffd884" />
      </mesh>
      {/* 内辉 */}
      <mesh>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshBasicMaterial color="#ffb858" transparent opacity={0.32} />
      </mesh>
      {/* 外辉 */}
      <mesh>
        <sphereGeometry args={[0.62, 32, 32]} />
        <meshBasicMaterial color="#ff8a3a" transparent opacity={0.14} />
      </mesh>
      {/* 远辉 */}
      <mesh>
        <sphereGeometry args={[0.85, 32, 32]} />
        <meshBasicMaterial color="#ff6a28" transparent opacity={0.05} />
      </mesh>
      {/* 真光源 —— 照亮行星 */}
      <pointLight intensity={3.5} color="#ffe0a8" distance={10} decay={1.4} castShadow />
    </group>
  );
}

/**
 * Hero3D — Solar System for Look-alike Prospecting
 * 太阳 = 目标客户画像 / 行星 = 被发现的相似候选 / 轨道层级 = 匹配度
 */
export default function Hero3D() {
  return (
    <Canvas
      camera={{ position: [-0.3, 1.3, 5.4], fov: 34 }}
      dpr={[1, 2]}
      shadows
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 1.05,
      }}
      style={{ background: "transparent" }}
    >
      {/* 远景星空 */}
      <Stars
        radius={60}
        depth={60}
        count={3500}
        factor={3}
        saturation={0}
        fade
        speed={0.3}
      />

      {/* 近景大气粒子 —— 填满"空白" */}
      <Sparkles
        count={120}
        scale={[8, 5, 5]}
        position={[SOLAR_CENTER[0], SOLAR_CENTER[1], SOLAR_CENTER[2] + 1]}
        size={3}
        speed={0.25}
        opacity={0.7}
        color="#dae6f4"
      />
      <Sparkles
        count={60}
        scale={[10, 3, 4]}
        position={[0, 0.6, 0]}
        size={6}
        speed={0.12}
        opacity={0.35}
        color="#a8c0e0"
      />

      {/* 体积雾气 —— 水面附近 */}
      <fog attach="fog" args={["#0a1220", 4, 14]} />

      {/* 微弱环境光（让阴影面不死黑） */}
      <ambientLight intensity={0.18} color="#7a8aa0" />
      <directionalLight position={[-3, 3, 4]} intensity={0.15} color="#5c708c" />

      {/* HDR 仅用于反射地面 */}
      <Environment resolution={256} background={false}>
        <Lightformer intensity={1.5} position={[3, 5, 3]} rotation-x={-Math.PI / 2} scale={[10, 10, 1]} color="#3a4860" />
        <Lightformer intensity={2} position={SOLAR_CENTER} scale={[1.5, 1.5, 1.5]} color="#ffc880" />
      </Environment>

      <Sun />
      {ORBIT_RINGS.map((r, i) => (
        <OrbitRing key={i} {...r} />
      ))}
      {PLANETS.map((p, i) => (
        <Planet key={i} spec={p} idx={i} />
      ))}

      {/* 反射地面 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[40, 40]} />
        <MeshReflectorMaterial
          blur={[300, 100]}
          resolution={1024}
          mixBlur={1}
          mixStrength={1.5}
          mirror={0.5}
          mixContrast={1}
          color="#0a1421"
          metalness={0.4}
          roughness={0.95}
          depthScale={1.2}
          minDepthThreshold={0.4}
          maxDepthThreshold={1.4}
        />
      </mesh>

      <EffectComposer enableNormalPass={false}>
        <Bloom intensity={0.85} luminanceThreshold={0.5} luminanceSmoothing={0.4} mipmapBlur />
        <Vignette eskil={false} offset={0.18} darkness={0.85} />
      </EffectComposer>
    </Canvas>
  );
}
