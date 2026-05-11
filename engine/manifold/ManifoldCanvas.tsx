import { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text } from '@react-three/drei'
import * as THREE from 'three'
import { useArgumentStore, VeracityState } from '../stores/argumentStore'

const NODE_COUNT = 2000
const GRID_SIZE = 64

interface ManifoldNode {
  id: number
  basePosition: [number, number, number]
  velocity: [number, number, number]
  zOffset: number
  magnitude: number
}

function SunriseColorRamp(distance: number, V_active: number): THREE.Color {
  const color = new THREE.Color()
  
  if (V_active <= 0.1) {
    color.setHex(0x880E4F)
    return color
  }
  
  if (distance < 0.2) {
    color.setHex(0xFFFFFF)
  } else if (distance < 1.5) {
    const t = (distance - 0.2) / 1.3
    color.setHex(t < 0.5 ? 0xFFF9C4 : 0xFFD54F)
  } else if (distance < 4.0) {
    const t = (distance - 1.5) / 2.5
    color.setHex(t < 0.5 ? 0xFF8F00 : 0xE65100)
  } else if (distance < 8.0) {
    const t = (distance - 4.0) / 4.0
    color.setHex(t < 0.5 ? 0x4E342E : 0x212121)
  } else {
    color.setHex(0x212121)
  }
  
  return color
}

function ManifoldMesh({ V_active, state, fallacies }: {
  V_active: number
  state: VeracityState
  fallacies: Array<{ type: string; magnitude: number; position: [number, number, number] }>
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const materialRef = useRef<THREE.ShaderMaterial>(null)
  
  const nodes = useMemo<ManifoldNode[]>(() => {
    const nodes: ManifoldNode[] = []
    const step = 10 / (GRID_SIZE - 1)
    const half = 5
    
    for (let i = 0; i < NODE_COUNT; i++) {
      const x = (i % GRID_SIZE) * step - half
      const z = Math.floor(i / GRID_SIZE) * step - half
      nodes.push({
        id: i,
        basePosition: [x, 0, z],
        velocity: [0, 0, 0],
        zOffset: 0,
        magnitude: 0
      })
    }
    return nodes
  }, [])
  
  const dummy = useMemo(() => new THREE.Object3D(), [])
  
  useFrame(({ clock }) => {
    if (!meshRef.current) return
    
    const time = clock.elapsedTime
    const isEclipse = state === 'divide' || V_active <= 0.1
    const isLocked = state === 'divide'
    
    for (let i = 0; i < NODE_COUNT; i++) {
      const node = nodes[i]
      
      let zOffset = 0
      
      for (const fallacy of fallacies) {
        const dx = node.basePosition[0] - fallacy.position[0]
        const dz = node.basePosition[2] - fallacy.position[2]
        const distance = Math.sqrt(dx * dx + dz * dz)
        
        if (distance < 0.001) continue
        
        const displacement = (fallacy.magnitude * 1.0) / (distance * distance)
        zOffset -= displacement
      }
      
      node.zOffset = zOffset
      
      const stretchY = 1.0 + Math.abs(zOffset) * 0.5
      
      dummy.position.set(
        node.basePosition[0],
        zOffset,
        node.basePosition[2]
      )
      
      dummy.rotation.set(0, 0, 0)
      
      if (Math.abs(node.velocity[0]) > 0.01 || Math.abs(node.velocity[2]) > 0.01) {
        const angle = Math.atan2(node.velocity[2], node.velocity[0])
        dummy.rotation.set(0, angle, 0)
      }
      
      dummy.scale.set(1, stretchY, 1)
      
      dummy.updateMatrix()
      meshRef.current.setMatrixAt(i, dummy.matrix)
      
      const distanceToOrigin = Math.sqrt(
        node.basePosition[0] * node.basePosition[0] + zOffset * zOffset
      )
      const color = SunriseColorRamp(distanceToOrigin, V_active)
      meshRef.current.setColorAt(i, color)
    }
    
    meshRef.current.instanceMatrix.needsUpdate = true
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true
    }
    
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = time
      materialRef.current.uniforms.uV_active.value = V_active
      materialRef.current.uniforms.uInverionLockout.value = isEclipse ? 1.0 : 0.0
      materialRef.current.uniforms.uState.value = ['ignition', 'healthy', 'stressed', 'critical', 'divide'].indexOf(state)
    }
  })
  
  const vertexShader = `
    uniform float uTime;
    uniform float uV_active;
    uniform float uInverionLockout;
    
    varying vec3 vPosition;
    varying float vDistanceToOrigin;
    varying float vIntensity;
    
    void main() {
      vec3 pos = position;
      
      float dist = length(pos);
      vDistanceToOrigin = dist;
      vIntensity = min(pos.y * 0.5 + 0.5, 1.0);
      vPosition = pos;
      
      gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(pos, 1.0);
    }
  `
  
  const fragmentShader = `
    uniform float uTime;
    uniform float uV_active;
    uniform float uInverionLockout;
    uniform int uState;
    
    varying vec3 vPosition;
    varying float vDistanceToOrigin;
    varying float vIntensity;
    
    vec3 sunriseColorRamp(float dist) {
      if (uInverionLockout > 0.5) {
        float pulse = 0.5 + 0.5 * sin(uTime * 2.0);
        return mix(vec3(0.53, 0.04, 0.31), vec3(0.4, 0.0, 0.0), pulse);
      }
      
      if (dist < 0.2) {
        return vec3(1.0, 1.0, 1.0);
      } else if (dist < 1.5) {
        float t = (dist - 0.2) / 1.3;
        return mix(vec3(1.0, 0.98, 0.77), vec3(1.0, 0.84, 0.31), t);
      } else if (dist < 4.0) {
        float t = (dist - 1.5) / 2.5;
        return mix(vec3(1.0, 0.56, 0.0), vec3(0.9, 0.32, 0.0), t);
      } else {
        float t = clamp((dist - 4.0) / 4.0, 0.0, 1.0);
        return mix(vec3(0.9, 0.32, 0.0), vec3(0.13, 0.13, 0.13), t);
      }
    }
    
    void main() {
      vec3 color = sunriseColorRamp(vDistanceToOrigin);
      
      float centerDist = length(vPosition.xy);
      if (centerDist < 0.5 && uInverionLockout < 0.5) {
        float ignition = (0.5 - centerDist) * 2.0;
        color = mix(color, vec3(1.0, 1.0, 1.0), ignition * uV_active);
      }
      
      float alpha = 0.9;
      
      gl_FragColor = vec4(color, alpha);
    }
  `
  
  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uV_active: { value: V_active },
    uInverionLockout: { value: 0.0 },
    uState: { value: 0 }
  }), [])
  
  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, NODE_COUNT]}
      frustumCulled={false}
    >
      <boxGeometry args={[0.05, 0.05, 0.05]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        side={THREE.DoubleSide}
        toneMapping={THREE.NoToneMapping}
        blending={THREE.AdditiveBlending}
      />
    </instancedMesh>
  )
}

function FallacyMarkers({ fallacies }: { 
  fallacies: Array<{ type: string; magnitude: number; position: [number, number, number] }> 
}) {
  return (
    <>
      {fallacies.map((f, i) => (
        <mesh key={i} position={[f.position[0] * 0.1, f.position[1] * 0.1, 0.5]}>
          <sphereGeometry args={[f.magnitude * 0.2, 16, 16]} />
          <meshBasicMaterial 
            color={f.magnitude > 0.7 ? '#880E4F' : f.magnitude > 0.4 ? '#E65100' : '#FFD54F'} 
            transparent 
            opacity={0.8}
          />
        </mesh>
      ))}
    </>
  )
}

function ClaimNodes({ claims }: { 
  claims: Array<{ text: string; position: [number, number, number] }> 
}) {
  return (
    <>
      {claims.map((c, i) => (
        <group key={i} position={[c.position[0] * 0.1, c.position[2] * 0.1, 0.3]}>
          <mesh>
            <sphereGeometry args={[0.05, 12, 12]} />
            <meshStandardMaterial 
              color="#e2e8f0" 
              emissive="#FFFFFF" 
              emissiveIntensity={0.5}
            />
          </mesh>
          <Text
            position={[0, 0.15, 0]}
            fontSize={0.08}
            color="#94a3b8"
            anchorX="center"
            anchorY="bottom"
            maxWidth={1}
          >
            {c.text.slice(0, 30)}...
          </Text>
        </group>
      ))}
    </>
  )
}

export function ManifoldCanvas() {
  const { V_active, state, fallacies, claims, inverion_triggered } = useArgumentStore()
  
  const isEclipse = state === 'divide' || V_active <= 0.1
  
  return (
    <Canvas
      camera={{ position: [0, 8, 8], fov: 60 }}
      style={{ background: isEclipse ? '#0a0a0f' : '#0a0a0f' }}
      gl={{ 
        antialias: true,
        toneMapping: THREE.NoToneMapping,
        outputColorSpace: THREE.SRGBColorSpace
      }}
    >
      <ambientLight intensity={0.3} />
      <pointLight 
        position={[0, 5, 0]} 
        intensity={isEclipse ? 0.3 : 1} 
        color={isEclipse ? '#880E4F' : '#FFFFFF'} 
      />
      
      <ManifoldMesh V_active={V_active} state={state} fallacies={fallacies} />
      <FallacyMarkers fallacies={fallacies} />
      <ClaimNodes claims={claims} />
      
      <OrbitControls 
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        maxDistance={15}
        minDistance={3}
      />
    </Canvas>
  )
}