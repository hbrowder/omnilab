import React, { useState } from 'react'

/**
 * CRE-64: Drawing Tools (Container Boxes)
 * Toolbar for adding visual annotations to the canvas:
 * - Rectangles (container boxes)
 * - Circles/Ellipses
 * - Text labels
 * 
 * Based on EVE-NG textobjects (base64-encoded HTML/SVG with absolute positioning)
 */

const TOOLS = [
  { id: 'select', icon: '👆', label: 'Select' },
  { id: 'rectangle', icon: '▭', label: 'Rectangle' },
  { id: 'circle', icon: '●', label: 'Circle' },
  { id: 'text', icon: 'T', label: 'Text' }
]

const COLORS = [
  { value: 'rgba(88,166,255,0.3)', label: 'Blue' },
  { value: 'rgba(35,134,54,0.3)', label: 'Green' },
  { value: 'rgba(218,54,51,0.3)', label: 'Red' },
  { value: 'rgba(255,191,0,0.3)', label: 'Yellow' },
  { value: 'rgba(163,113,247,0.3)', label: 'Purple' },
  { value: 'rgba(139,148,158,0.3)', label: 'Gray' }
]

const STROKES = [
  { value: 'rgba(88,166,255,1)', label: 'Blue' },
  { value: 'rgba(35,134,54,1)', label: 'Green' },
  { value: 'rgba(218,54,51,1)', label: 'Red' },
  { value: 'rgba(255,191,0,1)', label: 'Yellow' },
  { value: 'rgba(163,113,247,1)', label: 'Purple' },
  { value: 'rgba(139,148,158,1)', label: 'Gray' }
]

export default function DrawingToolbar({ activeTool, onToolChange, fillColor, strokeColor, onFillChange, onStrokeChange }) {
  const [expanded, setExpanded] = useState(false)
  
  return (
    <div style={{
      position: 'absolute',
      top: 60,
      left: 12,
      background: '#161b22',
      border: '1px solid #30363d',
      borderRadius: 8,
      padding: 8,
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      zIndex: 100,
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
    }}>
      {/* Tool Buttons */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {TOOLS.map(tool => (
          <button
            key={tool.id}
            onClick={() => onToolChange(tool.id)}
            title={tool.label}
            style={{
              width: 36,
              height: 36,
              background: activeTool === tool.id ? '#238636' : 'transparent',
              border: activeTool === tool.id ? '1px solid #2ea043' : '1px solid #30363d',
              borderRadius: 6,
              color: '#e6edf3',
              fontSize: 16,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.1s'
            }}
            onMouseEnter={(e) => {
              if (activeTool !== tool.id) e.target.style.borderColor = '#58a6ff'
            }}
            onMouseLeave={(e) => {
              if (activeTool !== tool.id) e.target.style.borderColor = '#30363d'
            }}
          >
            {tool.icon}
          </button>
        ))}
      </div>
      
      {/* Divider */}
      {activeTool !== 'select' && (
        <>
          <div style={{ height: 1, background: '#30363d' }} />
          
          {/* Color Picker Toggle */}
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              width: 36,
              height: 36,
              background: 'transparent',
              border: '1px solid #30363d',
              borderRadius: 6,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16
            }}
            title="Colors"
          >
            🎨
          </button>
        </>
      )}
      
      {/* Color Pickers (Expanded) */}
      {expanded && activeTool !== 'select' && (
        <div style={{
          position: 'absolute',
          left: 52,
          top: 0,
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: 8,
          padding: 12,
          minWidth: 180,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        }}>
          {/* Fill Color */}
          {activeTool !== 'text' && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 6, fontWeight: 600 }}>Fill</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                {COLORS.map(color => (
                  <button
                    key={color.value}
                    onClick={() => onFillChange(color.value)}
                    title={color.label}
                    style={{
                      width: 32,
                      height: 32,
                      background: color.value,
                      border: fillColor === color.value ? '2px solid #58a6ff' : '1px solid #30363d',
                      borderRadius: 6,
                      cursor: 'pointer'
                    }}
                  />
                ))}
              </div>
            </div>
          )}
          
          {/* Stroke Color */}
          <div>
            <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 6, fontWeight: 600 }}>Stroke</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
              {STROKES.map(color => (
                <button
                  key={color.value}
                  onClick={() => onStrokeChange(color.value)}
                  title={color.label}
                  style={{
                    width: 32,
                    height: 32,
                    background: color.value,
                    border: strokeColor === color.value ? '2px solid #58a6ff' : '1px solid #30363d',
                    borderRadius: 6,
                    cursor: 'pointer'
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
