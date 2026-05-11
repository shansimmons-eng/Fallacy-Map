// Sunrise Manifold Vertex Shader
// Implements the Inverion Protocol for vertex displacement

uniform float uTime;
uniform float uV_active;
uniform float uMagnitude;
uniform int uFallacyCount;
uniform vec3 uFallacyPositions[50];
uniform float uFallacyMagnitudes[50];

varying vec3 vPosition;
varying float vDistanceToOrigin;
varying vec3 vNormal;
varying float vFallacyIntensity;

// Constants for Inverse Square displacement
const float G_CONSTANT = 1.0;
const float COHERENCE_THRESHOLD = 1.5;

void main() {
    vec3 pos = position;
    float totalDisplacement = 0.0;
    float maxIntensity = 0.0;
    
    // Apply gravity wells from fallacies (Inverse Square law)
    for (int i = 0; i < 50; i++) {
        if (i >= uFallacyCount) break;
        
        vec3 fallacyPos = uFallacyPositions[i];
        float magnitude = uFallacyMagnitudes[i];
        
        // Calculate distance to fallacy
        vec3 delta = pos - fallacyPos;
        float distance = length(delta);
        
        if (distance < 0.001) {
            distance = 0.001; // Avoid division by zero
        }
        
        // Inverse Square displacement
        float displacement = (magnitude * G_CONSTANT) / (distance * distance);
        totalDisplacement += displacement;
        
        // Track intensity for coloring
        maxIntensity = max(maxIntensity, magnitude / (distance * distance));
    }
    
    // Apply vertical displacement (Z-axis = depth/gravity)
    pos.z -= totalDisplacement;
    
    // Calculate distance to origin for color ramp
    vDistanceToOrigin = length(pos);
    vFallacyIntensity = min(maxIntensity, 10.0); // Cap for HDR
    
    // Pass through normal and position
    vNormal = normal;
    vPosition = pos;
    
    // Calculate deformed position
    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mvPosition;
}