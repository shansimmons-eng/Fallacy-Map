import { useState, useCallback } from 'react'
import { ManifoldCanvas } from './components/ManifoldCanvas'
import { VeracityMeter } from './components/VeracityMeter'
import { InverionDivideOverlay } from './components/InverionDivideOverlay'
import { useArgumentStore } from './stores/argumentStore'

function App() {
  const [inputText, setInputText] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const { 
    argumentId, 
    setArgumentId, 
    setTitle, 
    inverion_triggered,
    V_active,
    state
  } = useArgumentStore()

  const handleCreateArgument = useCallback(async () => {
    if (!inputText.trim()) return
    
    try {
      const response = await fetch('http://localhost:8000/arguments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          title: 'Argument Analysis', 
          source_text: inputText 
        })
      })
      const data = await response.json()
      setArgumentId(data.id)
      setTitle(data.title)
    } catch (error) {
      console.error('Failed to create argument:', error)
    }
  }, [inputText, setArgumentId, setTitle])

  const handleAnalyze = useCallback(async () => {
    if (!argumentId || !inputText.trim() || inverion_triggered) return
    
    setIsAnalyzing(true)
    try {
      const chunks = inputText.split(/[.!?]+/).filter(c => c.trim())
      for (const chunk of chunks) {
        const response = await fetch(`http://localhost:8000/analyze?argument_id=${argumentId}&text=${encodeURIComponent(chunk)}`, {
          method: 'POST'
        })
        if (!response.ok) break
      }
    } catch (error) {
      console.error('Analysis failed:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }, [argumentId, inputText, inverion_triggered])

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#0a0a0f',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: '"Space Grotesk", system-ui, sans-serif',
      color: '#e2e8f0'
    }}>
      <header style={{
        padding: '16px 24px',
        borderBottom: '1px solid #1a1a2e',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <h1 style={{ 
            fontSize: 20, 
            fontWeight: 'bold',
            background: 'linear-gradient(90deg, #00f5d4, #8b5cf6)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            FALLACY MAP
          </h1>
          <span style={{ color: '#64748b', fontSize: 12 }}>
            The Geography of Logic
          </span>
        </div>
        <VeracityMeter />
      </header>

      <div style={{ flex: 1, display: 'flex', position: 'relative' }}>
        <div style={{
          width: 400,
          padding: 24,
          borderRight: '1px solid #1a1a2e',
          display: 'flex',
          flexDirection: 'column',
          gap: 16
        }}>
          <div>
            <label style={{ color: '#94a3b8', fontSize: 12, marginBottom: 8, display: 'block' }}>
              TRANSCRIPT / ARGUMENT
            </label>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste argument or transcript here..."
              disabled={inverion_triggered}
              style={{
                width: '100%',
                height: 200,
                background: '#1a1a2e',
                border: '1px solid #2d2d3d',
                borderRadius: 8,
                padding: 12,
                color: '#e2e8f0',
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: 13,
                resize: 'vertical',
                outline: 'none'
              }}
            />
          </div>
          
          <div style={{ display: 'flex', gap: 12 }}>
            {!argumentId ? (
              <button
                onClick={handleCreateArgument}
                disabled={!inputText.trim()}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  background: '#8b5cf6',
                  border: 'none',
                  borderRadius: 8,
                  color: 'white',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  opacity: !inputText.trim() ? 0.5 : 1
                }}
              >
                Create Argument
              </button>
            ) : (
              <button
                onClick={handleAnalyze}
                disabled={isAnalyzing || inverion_triggered}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  background: state === 'divide' ? '#1a1a1a' : '#00f5d4',
                  border: state === 'divide' ? '2px solid #dc2626' : 'none',
                  borderRadius: 8,
                  color: state === 'divide' ? '#808080' : '#0a0a0f',
                  fontWeight: 'bold',
                  cursor: state === 'divide' ? 'not-allowed' : 'pointer',
                  opacity: isAnalyzing || inverion_triggered ? 0.5 : 1
                }}
              >
                {isAnalyzing ? 'Analyzing...' : 'Analyze'}
              </button>
            )}
          </div>

          <div style={{
            background: '#1a1a2e',
            borderRadius: 8,
            padding: 16,
            marginTop: 'auto'
          }}>
            <div style={{ color: '#64748b', fontSize: 10, marginBottom: 8 }}>
              LEGEND
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#00f5d4' }} />
                <span>Healthy Logic (V &gt; 0.8)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#fee440' }} />
                <span>Stressed (0.3 &lt; V ≤ 0.5)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ef4444' }} />
                <span>Critical (0 &lt; V ≤ 0.3)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#dc2626' }} />
                <span>Inverion Divide (V ≤ 0)</span>
              </div>
            </div>
          </div>
        </div>

        <div style={{ flex: 1, position: 'relative' }}>
          <ManifoldCanvas />
          <InverionDivideOverlay />
          
          {V_active > 0.8 && (
            <div style={{
              position: 'absolute',
              top: 20,
              left: '50%',
              transform: 'translateX(-50%)',
              padding: '8px 16px',
              background: 'rgba(0, 245, 212, 0.1)',
              border: '1px solid #00f5d4',
              borderRadius: 8,
              color: '#00f5d4',
              fontSize: 12,
              fontFamily: '"JetBrains Mono", monospace'
            }}>
              IGNITION STATE — Pure logical fuel burning
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App