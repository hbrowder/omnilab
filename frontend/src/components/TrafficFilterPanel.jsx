import React, { useState, useEffect } from 'react'

/**
 * CRE-68: Traffic Filter Panel
 * 
 * Displays a sidebar panel with traffic filter controls for the active lab.
 * Filters can be toggled on/off, created, edited, and deleted.
 * Each filter has:
 *  - Title (user-friendly name)
 *  - Expression (tcpdump/BPF syntax)
 *  - Color (for visual flow indication)
 *  - Timeout (flash duration in ms)
 *  - Enabled state (on/off toggle)
 *  - Priority (higher = rendered first)
 */

export default function TrafficFilterPanel({ labId, darkMode, onClose, wsConnected, packetCounts, wsError }) {
  const [filters, setFilters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingFilter, setEditingFilter] = useState(null)

  // Form state for create/edit
  const [formData, setFormData] = useState({
    title: '',
    expr: '',
    color: '#00ff00',
    timeout: 5000,
    enabled: true,
    priority: 0
  })

  // Theme colors
  const bg = darkMode ? '#1e293b' : '#f8fafc'
  const panelBg = darkMode ? '#0f172a' : '#ffffff'
  const border = darkMode ? '#334155' : '#e2e8f0'
  const text = darkMode ? '#f1f5f9' : '#1e293b'
  const textMuted = darkMode ? '#94a3b8' : '#64748b'
  const inputBg = darkMode ? '#1e293b' : '#ffffff'
  const buttonBg = darkMode ? '#3b82f6' : '#3b82f6'
  const buttonHoverBg = darkMode ? '#2563eb' : '#2563eb'
  const toggleOnBg = '#10b981'
  const toggleOffBg = darkMode ? '#475569' : '#cbd5e1'

  // Load filters on mount
  useEffect(() => {
    loadFilters()
  }, [labId])

  const loadFilters = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/api/labs/${labId}/filters`)
      if (!response.ok) throw new Error('Failed to load filters')
      const data = await response.json()
      setFilters(data)
    } catch (err) {
      setError(err.message)
      console.error('Failed to load filters:', err)
    } finally {
      setLoading(false)
    }
  }

  const createFilter = async () => {
    try {
      const response = await fetch(`/api/labs/${labId}/filters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      if (!response.ok) throw new Error('Failed to create filter')
      await loadFilters()
      resetForm()
      setShowCreateForm(false)
    } catch (err) {
      setError(err.message)
      console.error('Failed to create filter:', err)
    }
  }

  const updateFilter = async (filterId, updates) => {
    try {
      const response = await fetch(`/api/labs/${labId}/filters/${filterId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      if (!response.ok) throw new Error('Failed to update filter')
      await loadFilters()
      if (editingFilter?.id === filterId) {
        setEditingFilter(null)
        resetForm()
      }
    } catch (err) {
      setError(err.message)
      console.error('Failed to update filter:', err)
    }
  }

  const deleteFilter = async (filterId) => {
    if (!confirm('Delete this filter?')) return
    try {
      const response = await fetch(`/api/labs/${labId}/filters/${filterId}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to delete filter')
      await loadFilters()
    } catch (err) {
      setError(err.message)
      console.error('Failed to delete filter:', err)
    }
  }

  const toggleFilter = async (filter) => {
    await updateFilter(filter.id, { enabled: !filter.enabled })
  }

  const startEdit = (filter) => {
    setEditingFilter(filter)
    setFormData({
      title: filter.title,
      expr: filter.expr,
      color: filter.color,
      timeout: filter.timeout,
      enabled: filter.enabled,
      priority: filter.priority
    })
    setShowCreateForm(false)
  }

  const saveEdit = async () => {
    if (!editingFilter) return
    await updateFilter(editingFilter.id, formData)
  }

  const resetForm = () => {
    setFormData({
      title: '',
      expr: '',
      color: '#00ff00',
      timeout: 5000,
      enabled: true,
      priority: 0
    })
    setEditingFilter(null)
  }

  const cancelEdit = () => {
    resetForm()
    setShowCreateForm(false)
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: 380,
      height: '100%',
      background: panelBg,
      borderLeft: `1px solid ${border}`,
      display: 'flex',
      flexDirection: 'column',
      fontFamily: 'sans-serif',
      zIndex: 1000,
      boxShadow: '-4px 0 12px rgba(0,0,0,0.1)'
    }}>
      
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: `1px solid ${border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <h2 style={{
          margin: 0,
          fontSize: 18,
          fontWeight: 600,
          color: text,
          display: 'flex',
          alignItems: 'center',
          gap: 10
        }}>
          Traffic Filters
          {/* WebSocket status indicator */}
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 12,
            fontWeight: 400,
            color: wsConnected ? '#10b981' : '#ef4444',
            background: wsConnected ? (darkMode ? '#064e3b' : '#d1fae5') : (darkMode ? '#7f1d1d' : '#fee2e2'),
            padding: '3px 8px',
            borderRadius: 12
          }}>
            <span style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: wsConnected ? '#10b981' : '#ef4444',
              animation: wsConnected ? 'pulse 2s ease-in-out infinite' : 'none'
            }}/>
            {wsConnected ? 'Live' : 'Offline'}
          </span>
        </h2>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            fontSize: 24,
            color: textMuted,
            cursor: 'pointer',
            padding: 4,
            lineHeight: 1
          }}
          title="Close panel"
        >×</button>
      </div>

      {/* Error banner - shows both API errors and WebSocket errors */}
      {(error || wsError) && (
        <div style={{
          padding: '12px 20px',
          background: darkMode ? '#7f1d1d' : '#fef2f2',
          borderBottom: `1px solid ${darkMode ? '#991b1b' : '#fecaca'}`,
          color: darkMode ? '#fca5a5' : '#dc2626',
          fontSize: 13,
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8
        }}>
          <span>⚠</span>
          <div style={{ flex: 1 }}>
            {error && <div>{error}</div>}
            {wsError && <div style={{ marginTop: error ? 6 : 0 }}>{wsError}</div>}
          </div>
        </div>
      )}

      {/* Filter List */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px 20px'
      }}>
        {loading ? (
          <div style={{ color: textMuted, fontSize: 14, textAlign: 'center', padding: '40px 0' }}>
            Loading filters...
          </div>
        ) : filters.length === 0 ? (
          <div style={{ color: textMuted, fontSize: 14, textAlign: 'center', padding: '40px 20px' }}>
            No filters yet. Click "Add Filter" to create one.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {filters.map(filter => (
              <div key={filter.id} style={{
                padding: 12,
                background: inputBg,
                border: `1px solid ${border}`,
                borderRadius: 6,
                display: 'flex',
                flexDirection: 'column',
                gap: 8
              }}>
                
                {/* Filter header: title + toggle */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {/* Toggle switch */}
                  <button
                    onClick={() => toggleFilter(filter)}
                    style={{
                      width: 44,
                      height: 24,
                      borderRadius: 12,
                      background: filter.enabled ? toggleOnBg : toggleOffBg,
                      border: 'none',
                      cursor: 'pointer',
                      position: 'relative',
                      transition: 'background 0.2s',
                      flexShrink: 0
                    }}
                    title={filter.enabled ? 'Disable filter' : 'Enable filter'}
                  >
                    <div style={{
                      width: 18,
                      height: 18,
                      borderRadius: '50%',
                      background: '#ffffff',
                      position: 'absolute',
                      top: 3,
                      left: filter.enabled ? 23 : 3,
                      transition: 'left 0.2s'
                    }} />
                  </button>

                  {/* Color swatch */}
                  <div style={{
                    width: 24,
                    height: 24,
                    borderRadius: 4,
                    background: filter.color,
                    border: `1px solid ${border}`,
                    flexShrink: 0
                  }} title={`Color: ${filter.color}`} />

                  {/* Title */}
                  <span style={{
                    flex: 1,
                    fontSize: 14,
                    fontWeight: 600,
                    color: text,
                    opacity: filter.enabled ? 1 : 0.5
                  }}>{filter.title}</span>

                  {/* Actions */}
                  <button
                    onClick={() => startEdit(filter)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: textMuted,
                      cursor: 'pointer',
                      fontSize: 16,
                      padding: 4
                    }}
                    title="Edit filter"
                  >✎</button>
                  <button
                    onClick={() => deleteFilter(filter.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#dc2626',
                      cursor: 'pointer',
                      fontSize: 16,
                      padding: 4
                    }}
                    title="Delete filter"
                  >🗑</button>
                </div>

                {/* Expression */}
                <div style={{
                  fontSize: 12,
                  fontFamily: 'monospace',
                  color: textMuted,
                  background: bg,
                  padding: '6px 8px',
                  borderRadius: 4,
                  border: `1px solid ${border}`,
                  opacity: filter.enabled ? 1 : 0.5
                }}>{filter.expr}</div>

                {/* Metadata */}
                <div style={{
                  fontSize: 11,
                  color: textMuted,
                  display: 'flex',
                  gap: 12,
                  opacity: filter.enabled ? 1 : 0.5,
                  alignItems: 'center'
                }}>
                  <span>Timeout: {filter.timeout}ms</span>
                  <span>Priority: {filter.priority}</span>
                  {/* Packet count (CRE-68 Phase 3) */}
                  {filter.enabled && packetCounts && packetCounts[filter.id] !== undefined && (
                    <span style={{
                      marginLeft: 'auto',
                      fontWeight: 600,
                      color: filter.color,
                      fontSize: 12,
                      background: darkMode ? 'rgba(0,0,0,0.3)' : 'rgba(255,255,255,0.8)',
                      padding: '2px 8px',
                      borderRadius: 10,
                      border: `1px solid ${filter.color}`
                    }}>
                      📊 {packetCounts[filter.id]} packets
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Form */}
      {(showCreateForm || editingFilter) && (
        <div style={{
          padding: '16px 20px',
          borderTop: `2px solid ${border}`,
          background: inputBg
        }}>
          <h3 style={{
            margin: '0 0 12px 0',
            fontSize: 15,
            fontWeight: 600,
            color: text
          }}>{editingFilter ? 'Edit Filter' : 'New Filter'}</h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* Title */}
            <input
              type="text"
              placeholder="Filter title (e.g., BGP Traffic)"
              value={formData.title}
              onChange={e => setFormData(p => ({ ...p, title: e.target.value }))}
              style={{
                padding: '8px 10px',
                fontSize: 13,
                border: `1px solid ${border}`,
                borderRadius: 4,
                background: inputBg,
                color: text
              }}
            />

            {/* Expression */}
            <input
              type="text"
              placeholder="Expression (e.g., tcp port 179)"
              value={formData.expr}
              onChange={e => setFormData(p => ({ ...p, expr: e.target.value }))}
              style={{
                padding: '8px 10px',
                fontSize: 13,
                fontFamily: 'monospace',
                border: `1px solid ${border}`,
                borderRadius: 4,
                background: inputBg,
                color: text
              }}
            />

            {/* Color + Timeout */}
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 11, color: textMuted, display: 'block', marginBottom: 4 }}>Color</label>
                <input
                  type="color"
                  value={formData.color}
                  onChange={e => setFormData(p => ({ ...p, color: e.target.value }))}
                  style={{
                    width: '100%',
                    height: 32,
                    border: `1px solid ${border}`,
                    borderRadius: 4,
                    cursor: 'pointer'
                  }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 11, color: textMuted, display: 'block', marginBottom: 4 }}>Timeout (ms)</label>
                <input
                  type="number"
                  value={formData.timeout}
                  onChange={e => setFormData(p => ({ ...p, timeout: parseInt(e.target.value) || 5000 }))}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    fontSize: 13,
                    border: `1px solid ${border}`,
                    borderRadius: 4,
                    background: inputBg,
                    color: text
                  }}
                />
              </div>
            </div>

            {/* Priority */}
            <div>
              <label style={{ fontSize: 11, color: textMuted, display: 'block', marginBottom: 4 }}>Priority (higher = first)</label>
              <input
                type="number"
                value={formData.priority}
                onChange={e => setFormData(p => ({ ...p, priority: parseInt(e.target.value) || 0 }))}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  fontSize: 13,
                  border: `1px solid ${border}`,
                  borderRadius: 4,
                  background: inputBg,
                  color: text
                }}
              />
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <button
                onClick={editingFilter ? saveEdit : createFilter}
                disabled={!formData.title || !formData.expr}
                style={{
                  flex: 1,
                  padding: '8px 16px',
                  fontSize: 13,
                  fontWeight: 600,
                  background: buttonBg,
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: 4,
                  cursor: formData.title && formData.expr ? 'pointer' : 'not-allowed',
                  opacity: formData.title && formData.expr ? 1 : 0.5
                }}
              >{editingFilter ? 'Save Changes' : 'Create Filter'}</button>
              <button
                onClick={cancelEdit}
                style={{
                  padding: '8px 16px',
                  fontSize: 13,
                  fontWeight: 600,
                  background: 'transparent',
                  color: textMuted,
                  border: `1px solid ${border}`,
                  borderRadius: 4,
                  cursor: 'pointer'
                }}
              >Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Filter Button */}
      {!showCreateForm && !editingFilter && (
        <div style={{
          padding: '16px 20px',
          borderTop: `1px solid ${border}`
        }}>
          <button
            onClick={() => setShowCreateForm(true)}
            style={{
              width: '100%',
              padding: '10px 16px',
              fontSize: 14,
              fontWeight: 600,
              background: buttonBg,
              color: '#ffffff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8
            }}
          >
            <span style={{ fontSize: 18 }}>+</span>
            Add Filter
          </button>
        </div>
      )}
    </div>
  )
}
