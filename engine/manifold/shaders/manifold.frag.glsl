// Sunrise Manifold Fragment Shader
// Implements the Inverion Sunrise Color-Ramp for Veracity visualization

uniform float uTime;
uniform float uV_active;
uniform float uInverionLockout;

varying vec3 vPosition;
varying float vDistanceToOrigin;
varying vec3 vNormal;
varying float vFallacyIntensity;

// Sunrise Color Ramp function
vec3 sunriseColorRamp(float dist) {
    // Distance 0.0-0.2: Blinding White (#FFFFFF) - Ignition
    if (dist < 0.2) {
        return vec3(1.0, 1.0, 1.0);
    }
    
    // Distance 0.2-1.5: Pale Goldenrod (#FFF9C4) to Morning Amber (#FFD54F)
    if (dist < 1.5) {
        float t = (dist - 0.2) / 1.3;
        return mix(vec3(1.0, 0.98, 0.77), vec3(1.0, 0.84, 0.31), t);
    }
    
    // Distance 1.5-4.0: Vibrant Orange (#FF8F00) to Deep Burnt Orange (#E65100)
    if (dist < 4.0) {
        float t = (dist - 1.5) / 2.5;
        return mix(vec3(1.0, 0.56, 0.0), vec3(0.9, 0.32, 0.0), t);
    }
    
    // Distance 4.0-8.0: Shadow Brown (#4E342E) to Deep Void (#212121)
    if (dist < 8.0) {
        float t = (dist - 4.0) / 4.0;
        return mix(vec3(0.9, 0.32, 0.0), vec3(0.26, 0.2, 0.18), t);
    }
    
    // Distance 8.0+: Near black
    return vec3(0.13, 0.13, 0.13);
}

// Eclipse colors for Inverion Lockout
vec3 eclipseColor(float dist, float time) {
    // Deep indigo (#880E4F) / shadow crimson with monochrome
    float pulse = 0.5 + 0.5 * sin(time * 2.0);
    vec3 indigo = vec3(0.53, 0.04, 0.31);  // #880E4F
    vec3 crimson = vec3(0.4, 0.0, 0.0);
    
    return mix(indigo, crimson, pulse);
}

void main() {
    vec3 color;
    float alpha = 1.0;
    float glow = 0.0;
    
    // Check for Inverion Lockout state
    if (uInverionLockout > 0.5) {
        // Eclipse Mode: Total structural failure
        color = eclipseColor(vDistanceToOrigin, uTime);
        glow = 0.0;
    } else {
        // Normal Sunrise Mode
        
        // Get base color from distance ramp
        color = sunriseColorRamp(vDistanceToOrigin);
        
        // Calculate center glow (Ignition effect)
        float centerDist = length(vPosition.xy);
        if (centerDist < 0.5) {
            // Core Ignition: Overdrive R,G,B for white-hot effect
            float ignition = (0.5 - centerDist) * 2.0;
            color = mix(color, vec3(1.0, 1.0, 1.0), ignition * uV_active);
            glow = ignition * uV_active;
        }
        
        // Apply fallacy intensity as brightness boost
        color += vec3(vFallacyIntensity * 0.2);
        
        // Clamp to prevent over-bright (but allow HDR breakthrough)
        // color = min(color, vec3(1.5));
    }
    
    // Simple lighting (fake sun from above)
    vec3 lightDir = normalize(vec3(0.0, 0.0, 1.0));
    float diffuse = max(dot(vNormal, lightDir), 0.0);
    color *= (0.5 + 0.5 * diffuse);
    
    // Add bloom/glow effect
    if (glow > 0.0) {
        color += vec3(glow * 0.3);
    }
    
    gl_FragColor = vec4(color, alpha);
}