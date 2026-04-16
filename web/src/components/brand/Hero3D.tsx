"use client";

import { Canvas } from "@react-three/fiber";
import {
  Environment,
  MeshReflectorMaterial,
  ContactShadows,
  Lightformer,
  Float,
} from "@react-three/drei";
import {
  EffectComposer,
  Bloom,
  Vignette,
} from "@react-three/postprocessing";
import * as THREE from "three";

/**
 * Hero3D —— 一比一复刻参考图美学
 * 只留三样：深蓝天（shader 管）+ 单个深色产品体 + 反光水面
 * 纯冷色调，无太阳、无行星、无粒子
 */
export default function Hero3D() {
  return (
    <Canvas
      camera={{ position: [0.2, 0.55, 4.4], fov: 32 }}
      dpr={[1, 2]}
      shadows
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 0.9,
      }}
      style={{ background: "transparent" }}
    >
      {/* HDR 环境光 —— 中性银灰色，无蓝调 */}
      <Environment resolution={256} background={false}>
        <Lightformer
          intensity={3.5}
          position={[2, 5, 3]}
          rotation-x={-Math.PI / 2.5}
          scale={[6, 6, 1]}
          color="#d8dce2"
        />
        <Lightformer
          intensity={2}
          position={[-3, 3, 2]}
          rotation-y={-Math.PI / 6}
          scale={[4, 4, 1]}
          color="#7a7e84"
        />
        <Lightformer
          intensity={1.5}
          position={[3, -2, 2]}
          scale={[3, 3, 1]}
          color="#2c2e32"
        />
      </Environment>

      <ambientLight intensity={0.15} color="#8a8c90" />
      <directionalLight
        position={[3, 4, 2]}
        intensity={0.6}
        color="#e4e6ea"
        castShadow
      />

      {/* 中心主体 —— 抛光深色金属体（类产品质感） */}
      <Float speed={0.5} floatIntensity={0.18} rotationIntensity={0.08}>
        <group position={[0, 0.72, 0]}>
          {/* 主球 */}
          <mesh castShadow>
            <sphereGeometry args={[0.62, 128, 128]} />
            <meshPhysicalMaterial
              color="#1d1f23"
              metalness={0.75}
              roughness={0.22}
              clearcoat={0.85}
              clearcoatRoughness={0.12}
              envMapIntensity={1.3}
            />
          </mesh>
        </group>
      </Float>

      {/* 水滴飞溅 —— 3 颗透明玻璃球，模拟静止水珠 */}
      <Float speed={1.3} floatIntensity={0.35} rotationIntensity={0.1}>
        <mesh position={[0.92, 1.15, 0.25]}>
          <sphereGeometry args={[0.065, 48, 48]} />
          <meshPhysicalMaterial
            color="#f0f2f5"
            metalness={0}
            roughness={0.05}
            transmission={0.95}
            thickness={0.3}
            ior={1.33}
            envMapIntensity={1.5}
          />
        </mesh>
      </Float>

      <Float speed={1.8} floatIntensity={0.4} rotationIntensity={0.08}>
        <mesh position={[-0.55, 1.05, 0.15]}>
          <sphereGeometry args={[0.042, 48, 48]} />
          <meshPhysicalMaterial
            color="#f0f2f5"
            metalness={0}
            roughness={0.05}
            transmission={0.95}
            thickness={0.2}
            ior={1.33}
          />
        </mesh>
      </Float>

      <Float speed={2.2} floatIntensity={0.3}>
        <mesh position={[0.45, 1.45, -0.1]}>
          <sphereGeometry args={[0.028, 32, 32]} />
          <meshPhysicalMaterial
            color="#f0f2f5"
            metalness={0}
            roughness={0.05}
            transmission={0.95}
            thickness={0.15}
            ior={1.33}
          />
        </mesh>
      </Float>

      {/* 底部礁石簇 —— 深黑低多边形 */}
      <mesh position={[-0.38, 0.12, 0.35]} rotation={[0.1, 0.4, 0]} castShadow>
        <dodecahedronGeometry args={[0.22]} />
        <meshStandardMaterial color="#0a0b0d" roughness={0.95} metalness={0.1} />
      </mesh>
      <mesh position={[0.35, 0.1, 0.25]} rotation={[0.2, 0.9, 0.1]} castShadow>
        <icosahedronGeometry args={[0.18]} />
        <meshStandardMaterial color="#0e0f12" roughness={0.92} metalness={0.1} />
      </mesh>
      <mesh position={[-0.05, 0.08, 0.48]} rotation={[0, 1.4, 0.15]} castShadow>
        <octahedronGeometry args={[0.1]} />
        <meshStandardMaterial color="#0c0d10" roughness={0.9} metalness={0.15} />
      </mesh>

      {/* 水面 —— 真 MeshReflectorMaterial，颜色匹配 shader bg（无缝） */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[40, 40]} />
        <MeshReflectorMaterial
          blur={[400, 120]}
          resolution={1024}
          mixBlur={1.4}
          mixStrength={1.8}
          mirror={0.7}
          mixContrast={1}
          color="#0a0b0d"
          metalness={0.6}
          roughness={0.75}
          depthScale={1.2}
          minDepthThreshold={0.4}
          maxDepthThreshold={1.4}
        />
      </mesh>

      {/* 接触阴影 */}
      <ContactShadows
        position={[0, 0.001, 0]}
        opacity={0.55}
        scale={5}
        blur={2.4}
        far={2}
      />

      {/* 体积雾 —— 远景消隐 */}
      <fog attach="fog" args={["#08090b", 5, 14]} />

      {/* 后期：极克制 bloom + 深 vignette */}
      <EffectComposer enableNormalPass={false}>
        <Bloom intensity={0.28} luminanceThreshold={0.85} mipmapBlur />
        <Vignette eskil={false} offset={0.22} darkness={0.85} />
      </EffectComposer>
    </Canvas>
  );
}
