import { useArgumentStore } from '../stores/argumentStore'

export function InverionDivideOverlay() {
  const { inverion_triggered, root_fallacy_id, fallacies, V_active } = useArgumentStore()
  
  if (!inverion_triggered) return null
  
  const rootFallacy = fallacies.find(f => f.id === root_fallacy_id)
  
  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.85)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      fontFamily: '"Space Grotesk", sans-serif'
    }}>
      <div style={{
        width: '80%',
        maxWidth: 600,
        padding: 32,
        background: 'linear-gradient(135deg, #1a1a1a 0%, #0a0a0f 100%)',
        border: '3px solid #dc2626',
        borderRadius: 16,
        boxShadow: '0 0 60px #dc262640'
      }}>
        <h2 style={{
          color: '#ef4444',
          fontSize: 32,
          marginBottom: 8,
          textAlign: 'center',
          textTransform: 'uppercase',
          letterSpacing: 4
        }}>
          INVERION DIVIDE
        </h2>
        
        <p style={{
          color: '#64748b',
          textAlign: 'center',
          marginBottom: 24,
          fontSize: 14
        }}>
          Structural collapse detected. Veracity fuel exhausted.
        </p>
        
        <div style={{
          background: '#0a0a0f',
          border: '1px solid #dc2626',
          borderRadius: 8,
          padding: 20,
          marginBottom: 24
        }}>
          <div style={{
            color: '#94a3b8',
            fontSize: 10,
            textTransform: 'uppercase',
            marginBottom: 8
          }}>
            Root Fallacy
          </div>
          <div style={{
            color: '#ef4444',
            fontSize: 18,
            fontWeight: 'bold',
            marginBottom: 8
          }}>
            {rootFallacy?.type ?? 'Unknown'}
          </div>
          <div style={{
            color: '#e2e8f0',
            fontSize: 14,
            fontStyle: 'italic'
          }}>
            "{rootFallacy?.claim_text ?? 'No root fallacy identified'}"
          </div>
        </div>
        
        <div style={{
          display: 'flex',
          justifyContent: 'space-around',
          marginBottom: 24
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ color: '#64748b', fontSize: 10 }}>CLAIMS</div>
            <div style={{ color: '#e2e8f0', fontSize: 24 }}>DISCONNECTED</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ color: '#64748b', fontSize: 10 }}>V_ACTIVE</div>
            <div style={{ color: '#ef4444', fontSize: 24 }}>{V_active.toFixed(2)}</div>
          </div>
        </div>
        
        <div style={{
          background: '#1a1a1a',
          borderRadius: 8,
          padding: 16,
          color: '#94a3b8',
          fontSize: 12,
          lineHeight: 1.6
        }}>
          <strong style={{ color: '#dc2626' }}>CASCADE ANALYSIS:</strong> The argument's logical structure has been permanently compromised. All data nodes have been disconnected to prevent propagation of false conclusions.
        </div>
      </div>
    </div>
  )
}