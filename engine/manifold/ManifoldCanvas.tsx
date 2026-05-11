import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text } from '@react-three/drei'
import * as THREE from 'three'
import { useArgumentStore, VeracityState } from '../stores/argumentStore'

const GRID_SIZE = 64

interface ManifoldMeshProps {
  V_active: number
  state: VeracityState
  fallacies: Array<{ type: string; magnitude: number; position: [number, number, number] }>
}

function ManifoldMesh({ V_active, state, fallacies }: ManifoldMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const materialRef = useRef<THREE.ShaderMaterial>(null)
  
  const { geometry, positions } = useMemo(() => {
    const geo = new THREE.PlaneGeometry(10, 10, GRID_SIZE - 1, GRID_SIZE - 1)
    const pos = geo.attributes.position.array.slice()
    return { geometry: geo, positions: pos }
  }, [])
  
  const uniforms = useMemo(() => ({
    V_active: { value: V_active },
    uTime: { value: 0 },
    uFallacyPositions: { value: new Float32Array(128) },
    uFallacyCount: { value: fallacies.length },
    uState: { value: 0 }
  }), [])
  
  const vertexShader = `
    uniform float V_active;
    uniform float uTime;
    uniform vec3 uFallacyPositions[16];
    uniform int uFallacyCount;
    uniform int uState;
    
    varying vec2 vUv;
    varying float vHeight;
    varying float vIntensity;
    
    void main() {
      vUv = uv;
      vec3 pos = position;
      
      float totalDisplacement = 0.0;
      
      for (int i = 0; i < 16; i++) {
        if (i >= uFallacyCount) break;
        float dist = distance(pos.xy, uFallacyPositions[i].xy);
        float fallMag = uFallacyPositions[i].z;
        float disp = fallMag / (dist + 0.1) * 0.5;
        
        if (uState == 1) {
          disp = -disp * 0.5;
        } else if (uState == 2) {
          disp = disp * 2.0;
        }
        
        totalDisplacement += disp;
      }
      
      pos.z += totalDisplacement;
      vHeight = pos.z;
      vIntensity = min(1.0, abs(totalDisplacement) * 0.5);
      
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `
  
  const fragmentShader = `
    uniform float V_active;
    uniform float uTime;
    uniform int uState;
    
    varying vec2 vUv;
    varying float vHeight;
    varying float vIntensity;
    
    vec3 getStateColor(float v, int state) {
      if (state == 4) {
        float noise = fract(sin(dot(vUv * 100.0, vec2(12.9898, 78.233))) * 43758.5453);
        return mix(vec3(0.1), vec3(0.86, 0.15, 0.15), noise);
      }
      
      float ignition = smoothstep(0.8, 1.0, V_active);
      vec3 glowCenter = mix(vec3(0.0, 0.96, 0.83), vec3(1.0), ignition);
      
      if (state == 0) return mix(glowCenter, vec3(0.0, 0.96, 0.83), vIntensity);
      if (state == 1) return mix(vec3(0.0, 0.96, 0.83), vec3(0.996, 0.914, 0.251), vIntensity);
      if (state == 2) return mix(vec3(0.996, 0.914, 0.251), vec3(0.937, 0.447, 0.086), vIntensity);
      if (state == 3) return vec3(0.937, 0.267, 0.267);
      return vec3(0.1);
    }
    
    void main() {
      vec3 color = getStateColor(V_active, uState);
      
      float dist = distance(vUv, vec2(0.5));
      float glow = smoothstep(0.5, 0.0, dist) * V_active;
      color = mix(color, vec3(1.0), glow * 0.5);
      
      if (uState == 3) {
        float pulse = sin(uTime * 4.0) * 0.3 + 0.7;
        color *= pulse;
      }
      
      gl_FragColor = vec4(color, 0.9);
    }
  `
  
  useFrame(({ clock }) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = clock.elapsedTime
      materialRef.current.uniforms.V_active.value = V_active
      materialRef.current.uniforms.uState.value = ['ignition', 'healthy', 'stressed', 'critical', 'divide'].indexOf(state)
    }
  })
  
  return (
    <mesh ref={meshRef} geometry={geometry} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

function FallacyMarkers({ fallacies }: { fallacies: Array<{ type: string; magnitude: number; position: [number, number, number] }> }) {
  return (
    <>
      {fallacies.map((f, i) => (
        <mesh key={i} position={[f.position[0] * 0.1, f.position[1] * 0.1, 0.5]}>
          <sphereGeometry args={[f.magnitude * 0.2, 16, 16]} />
          <meshBasicMaterial 
            color={f.magnitude > 0.7 ? '#ef4444' : f.magnitude > 0.4 ? '#f97316' : '#fee440'} 
            transparent 
            opacity={0.8}
          />
        </mesh>
      ))}
    </>
  )
}

function ClaimNodes({ claims }: { claims: Array<{ text: string; position: [number, number, number] }> }) {
  return (
    <>
      {claims.map((c, i) => (
        <group key={i} position={[c.position[0] * 0.1, c.position[2] * 0.1, 0.3]}>
          <mesh>
            <sphereGeometry args={[0.05, 12, 12]} />
            <meshStandardMaterial color="#e2e8f0" emissive="#00f5d4" emissiveIntensity={0.5} />
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
  
  return (
    <Canvas
      camera={{ position: [0, 5, 5], fov: 60 }}
      style={{ background: '#0a0a0f' }}
    >
      <ambientLight intensity={0.3} />
      <pointLight position={[0, 5, 0]} intensity={1} color={state === 'divide' ? '#dc2626' : '#00f5d4'} />
      
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