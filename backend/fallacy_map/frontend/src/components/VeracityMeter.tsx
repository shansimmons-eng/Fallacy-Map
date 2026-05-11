import { useArgumentStore } from '../stores/argumentStore'

const STATE_COLORS = {
  ignition: { bg: '#00f5d4', text: '#0a0a0f', glow: '#ffffff' },
  healthy: { bg: '#00f5d4', text: '#0a0a0f', glow: '#00f5d4' },
  stressed: { bg: '#fee440', text: '#0a0a0f', glow: '#fee440' },
  critical: { bg: '#ef4444', text: '#ffffff', glow: '#dc2626' },
  divide: { bg: '#1a1a1a', text: '#808080', glow: '#dc2626' }
} as const

export function VeracityMeter() {
  const { V_active, state, inverion_triggered, bypass_count } = useArgumentStore()
  
  const colors = STATE_COLORS[state]
  const percentage = Math.max(0, V_active * 100)
  
  return (
    <div style={{
      position: 'absolute',
      top: 20,
      right: 20,
      padding: '16px 24px',
      background: 'rgba(10, 10, 15, 0.9)',
      border: `2px solid ${colors.bg}`,
      borderRadius: 8,
      fontFamily: '"JetBrains Mono", monospace',
      minWidth: 200,
      boxShadow: `0 0 20px ${colors.glow}40`
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8
      }}>
        <span style={{ color: '#94a3b8', fontSize: 12 }}>VERACITY</span>
        <span style={{ 
          color: colors.bg, 
          fontSize: 14,
          fontWeight: 'bold',
          textTransform: 'uppercase'
        }}>{state}</span>
      </div>
      
      <div style={{
        height: 8,
        background: '#1a1a2e',
        borderRadius: 4,
        overflow: 'hidden',
        marginBottom: 8
      }}>
        <div style={{
          height: '100%',
          width: `${percentage}%`,
          background: `linear-gradient(90deg, ${colors.bg}, ${colors.glow})`,
          transition: 'width 0.3s ease, background 0.3s ease',
          boxShadow: `0 0 10px ${colors.glow}`
        }} />
      </div>
      
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span style={{ color: colors.bg, fontSize: 24, fontWeight: 'bold' }}>
          {(V_active * 100).toFixed(1)}%
        </span>
        <span style={{ color: '#64748b', fontSize: 10 }}>
          Vc=1.0
        </span>
      </div>
      
      {bypass_count > 0 && (
        <div style={{
          marginTop: 8,
          padding: '4px 8px',
          background: '#fee44020',
          border: '1px solid #fee440',
          borderRadius: 4,
          color: '#fee440',
          fontSize: 10
        }}>
          BYPASS x{bypass_count}
        </div>
      )}
      
      {inverion_triggered && (
        <div style={{
          marginTop: 8,
          padding: '8px 12px',
          background: '#dc262620',
          border: '2px solid #dc2626',
          borderRadius: 4,
          color: '#ef4444',
          fontSize: 11,
          textAlign: 'center',
          animation: 'pulse 1s infinite'
        }}>
          INVERION DIVIDE
        </div>
      )}
    </div>
  )
}