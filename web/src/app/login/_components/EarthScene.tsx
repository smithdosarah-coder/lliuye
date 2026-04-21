"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Stars } from "@react-three/drei";
import { useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * 3D 俯瞰地球 · 登录页左侧主视觉
 *
 * 构图意图（参考用户描述）：
 * - 一颗自转地球，真实大陆轮廓（程序化两层 shader：海洋 + 大陆 mask 贴花）
 * - 少数卫星按不同轨道环绕
 * - 深空背景，drei Stars 铺底
 * - 相机低俯视角 · 无控件 · autoRotate 持续旋转
 * - 无任何文字
 */

const EARTH_RADIUS = 1.0;
const EARTH_SEGMENTS = 72;
const CLOUD_RADIUS = 1.015;
const ATMOSPHERE_RADIUS = 1.06;

function buildContinentTexture(): THREE.DataTexture {
  // 程序化大陆分布 · 基于纬度带 + 大尺度 noise 模拟欧亚 / 非洲 / 美洲 / 大洋洲轮廓
  // 不用外部图片 · 避免网络 + 加载阻塞
  const size = 512;
  const data = new Uint8Array(size * size * 4);

  const continents: Array<[number, number, number]> = [
    // [lon(-180..180), lat(-90..90), radius(deg)]
    [80, 45, 55], // 欧亚
    [20, 0, 35], // 非洲
    [-90, 40, 30], // 北美
    [-60, -15, 28], // 南美
    [135, -25, 18], // 澳洲
    [30, 60, 25], // 欧洲北
    [100, -5, 15], // 东南亚
    [-40, 75, 20], // 格陵兰
    [0, -80, 28], // 南极
  ];

  for (let y = 0; y < size; y++) {
    const lat = 90 - (y / size) * 180;
    for (let x = 0; x < size; x++) {
      const lon = (x / size) * 360 - 180;
      const idx = (y * size + x) * 4;

      let landMask = 0;
      for (const [cLon, cLat, cR] of continents) {
        const dLon = Math.min(
          Math.abs(lon - cLon),
          360 - Math.abs(lon - cLon),
        );
        const dLat = Math.abs(lat - cLat);
        const d = Math.sqrt(dLon * dLon + dLat * dLat);
        const t = Math.max(0, 1 - d / cR);
        landMask = Math.max(landMask, t);
      }

      // noise 边缘 · 破除完美圆形
      const n =
        Math.sin(lon * 0.08 + lat * 0.13) * 0.14 +
        Math.sin(lon * 0.25 - lat * 0.18) * 0.08 +
        Math.cos(lon * 0.4 + lat * 0.35) * 0.05;
      landMask = Math.max(0, Math.min(1, landMask + n));

      const isLand = landMask > 0.42;

      if (isLand) {
        // 绿 → 黄 → 白 渐变（按纬度：赤道沙漠偏黄 / 中纬绿 / 高纬白）
        const absLat = Math.abs(lat);
        const green = Math.max(0, 1 - Math.abs(absLat - 40) / 50); // 中纬峰
        const desert = Math.max(0, 1 - Math.abs(absLat - 20) / 18); // 赤道带
        const snow = absLat > 62 ? Math.min(1, (absLat - 62) / 20) : 0;
        const r = Math.round(72 + green * 50 + desert * 125 + snow * 170);
        const g = Math.round(102 + green * 78 + desert * 95 + snow * 175);
        const b = Math.round(56 + green * 46 + desert * 40 + snow * 185);
        data[idx] = Math.min(255, r);
        data[idx + 1] = Math.min(255, g);
        data[idx + 2] = Math.min(255, b);
        data[idx + 3] = 255;
      } else {
        // 海洋 · 深蓝 → 浅蓝（按纬度 + 深度 noise）
        const depth =
          0.5 +
          Math.sin(lon * 0.15 + lat * 0.1) * 0.15 +
          Math.cos(lon * 0.3 + lat * 0.22) * 0.1;
        data[idx] = Math.round(10 + depth * 12);
        data[idx + 1] = Math.round(32 + depth * 48);
        data[idx + 2] = Math.round(78 + depth * 70);
        data[idx + 3] = 255;
      }
    }
  }

  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.needsUpdate = true;
  tex.anisotropy = 8;
  return tex;
}

function Earth() {
  const ref = useRef<THREE.Mesh>(null);
  const cloudRef = useRef<THREE.Mesh>(null);
  const texture = useMemo(buildContinentTexture, []);

  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.08;
    if (cloudRef.current) cloudRef.current.rotation.y += dt * 0.03;
  });

  return (
    <group rotation={[THREE.MathUtils.degToRad(23.5), 0, 0]}>
      {/* 地表 */}
      <mesh ref={ref}>
        <sphereGeometry args={[EARTH_RADIUS, EARTH_SEGMENTS, EARTH_SEGMENTS]} />
        <meshStandardMaterial
          map={texture}
          roughness={0.78}
          metalness={0.05}
        />
      </mesh>
      {/* 云层（半透明白）*/}
      <mesh ref={cloudRef}>
        <sphereGeometry args={[CLOUD_RADIUS, 48, 48]} />
        <meshStandardMaterial
          color="#ffffff"
          transparent
          opacity={0.12}
          depthWrite={false}
          roughness={1}
        />
      </mesh>
      {/* 大气辉光 */}
      <mesh>
        <sphereGeometry args={[ATMOSPHERE_RADIUS, 48, 48]} />
        <meshBasicMaterial
          color="#6ab4ff"
          transparent
          opacity={0.08}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}

type SatelliteProps = {
  radius: number;
  speed: number;
  inclination: number; // radians
  phase: number;
  size: number;
};

function Satellite({ radius, speed, inclination, phase, size }: SatelliteProps) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    const t = clock.getElapsedTime() * speed + phase;
    groupRef.current.position.set(
      Math.cos(t) * radius,
      Math.sin(t) * radius * Math.sin(inclination),
      Math.sin(t) * radius * Math.cos(inclination),
    );
  });

  return (
    <group ref={groupRef}>
      <mesh>
        <boxGeometry args={[size, size * 0.4, size * 0.4]} />
        <meshStandardMaterial
          color="#e4e7ec"
          metalness={0.6}
          roughness={0.35}
          emissive="#9cc7ff"
          emissiveIntensity={0.12}
        />
      </mesh>
      {/* solar panels */}
      <mesh position={[0, 0, -size * 0.9]}>
        <boxGeometry args={[size * 0.15, size * 0.7, size * 1.2]} />
        <meshStandardMaterial color="#1a3a6e" metalness={0.7} roughness={0.4} />
      </mesh>
      <mesh position={[0, 0, size * 0.9]}>
        <boxGeometry args={[size * 0.15, size * 0.7, size * 1.2]} />
        <meshStandardMaterial color="#1a3a6e" metalness={0.7} roughness={0.4} />
      </mesh>
    </group>
  );
}

function OrbitRing({
  radius,
  inclination,
}: {
  radius: number;
  inclination: number;
}) {
  const points = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const seg = 96;
    for (let i = 0; i <= seg; i++) {
      const t = (i / seg) * Math.PI * 2;
      pts.push(
        new THREE.Vector3(
          Math.cos(t) * radius,
          Math.sin(t) * radius * Math.sin(inclination),
          Math.sin(t) * radius * Math.cos(inclination),
        ),
      );
    }
    return pts;
  }, [radius, inclination]);

  const geometry = useMemo(
    () => new THREE.BufferGeometry().setFromPoints(points),
    [points],
  );

  return (
    <line>
      <primitive object={geometry} attach="geometry" />
      <lineBasicMaterial color="#6ab4ff" transparent opacity={0.18} />
    </line>
  );
}

export default function EarthScene() {
  const orbits: SatelliteProps[] = [
    { radius: 1.55, speed: 0.6, inclination: 0.2, phase: 0, size: 0.05 },
    { radius: 1.8, speed: 0.42, inclination: 0.9, phase: 1.7, size: 0.04 },
    { radius: 2.1, speed: 0.3, inclination: -0.4, phase: 3.2, size: 0.045 },
    { radius: 1.9, speed: 0.5, inclination: 1.35, phase: 4.8, size: 0.035 },
  ];

  return (
    <Canvas
      camera={{ position: [0, 0.55, 3.4], fov: 38 }}
      dpr={[1, 2]}
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 1.1,
      }}
      style={{ background: "transparent" }}
    >
      {/* 星空 */}
      <Stars
        radius={60}
        depth={40}
        count={3000}
        factor={3}
        saturation={0}
        fade
        speed={0.6}
      />

      {/* 日光侧光 · 偏侧以产生昼夜边界 */}
      <directionalLight position={[5, 2.5, 3]} intensity={1.8} color="#fff2dc" />
      <ambientLight intensity={0.32} color="#3a4e78" />
      {/* 地球夜侧补一点冷光 · 避免纯黑 */}
      <directionalLight
        position={[-4, -1, -2]}
        intensity={0.22}
        color="#5878b0"
      />

      <Earth />

      {/* 轨道线 + 卫星 */}
      {orbits.map((o, i) => (
        <OrbitRing key={`ring-${i}`} radius={o.radius} inclination={o.inclination} />
      ))}
      {orbits.map((o, i) => (
        <Satellite key={`sat-${i}`} {...o} />
      ))}
    </Canvas>
  );
}
