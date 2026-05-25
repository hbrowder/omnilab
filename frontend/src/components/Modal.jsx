import React, { useEffect, useRef } from 'react'

/**
 * CRE-67: In-canvas modal system (replaces browser prompt/alert/confirm)
 * @param {boolean} open - Controls modal visibility
 * @param {function} onClose - Called when user clicks backdrop or presses Escape
 * @param {string} title - Modal header text
 * @param {ReactNode} children - Modal body content
 * @param {number} width - Optional width in pixels (default: 480)
 * @param {boolean} darkMode - Optional dark mode override (default: true)
 */
export default function Modal({ open, onClose, title, children, width = 480, darkMode = true }) {
  const modalRef = useRef(null)
  
  useEffect(() => {
    if (!open) return
    
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    
    const handleClickOutside = (e) => {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        onClose()
      }
    }
    
    document.addEventListener('keydown', handleEscape)
    document.addEventListener('mousedown', handleClickOutside)
    
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open, onClose])
  
  if (!open) return null
  
  const bg = darkMode ? '#0d1117' : '#ffffff'
  const border = darkMode ? '#30363d' : '#d0d7de'
  const text = darkMode ? '#e6edf3' : '#1f2328'
  const headerBg = darkMode ? '#161b22' : '#f6f8fa'
  
  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(0,0,0,0.7)',
      backdropFilter: 'blur(2px)'
    }}>
      <div ref={modalRef} style={{
        background: bg,
        border: `1px solid ${border}`,
        borderRadius: 8,
        width,
        maxWidth: '90vw',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 16px 70px rgba(0,0,0,0.6)'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: `1px solid ${border}`,
          background: headerBg,
          borderRadius: '8px 8px 0 0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span style={{ fontWeight: 600, fontSize: 15, color: text }}>{title}</span>
          <button onClick={onClose} style={{
            background: 'transparent',
            border: 'none',
            color: darkMode ? '#8b949e' : '#57606a',
            fontSize: 20,
            cursor: 'pointer',
            padding: 0,
            width: 24,
            height: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            ×
          </button>
        </div>
        
        {/* Body */}
        <div style={{
          padding: 20,
          overflowY: 'auto',
          flex: 1,
          color: text
        }}>
          {children}
        </div>
      </div>
    </div>
  )
}

/**
 * Helper: Prompt dialog (replaces window.prompt)
 * Usage:
 *   const [showPrompt, setShowPrompt] = useState(false)
 *   <PromptModal open={showPrompt} onClose={()=>setShowPrompt(false)}
 *     title="Enter value" placeholder="..." onSubmit={(val)=>{ console.log(val) }} />
 */
export function PromptModal({ open, onClose, title, message, placeholder = '', defaultValue = '', onSubmit }) {
  const [value, setValue] = React.useState(defaultValue)
  const inputRef = useRef(null)
  
  useEffect(() => {
    if (open) {
      setValue(defaultValue)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open, defaultValue])
  
  const handleSubmit = (e) => {
    e.preventDefault()
    if (value.trim()) {
      onSubmit(value.trim())
      onClose()
    }
  }
  
  return (
    <Modal open={open} onClose={onClose} title={title} width={420}>
      <form onSubmit={handleSubmit}>
        {message && <p style={{ marginBottom: 12, fontSize: 14, color: '#8b949e' }}>{message}</p>}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          style={{
            width: '100%',
            padding: '8px 12px',
            border: '1px solid #30363d',
            borderRadius: 6,
            background: '#0d1117',
            color: '#e6edf3',
            fontSize: 14,
            outline: 'none'
          }}
          onFocus={(e) => e.target.style.borderColor = '#58a6ff'}
          onBlur={(e) => e.target.style.borderColor = '#30363d'}
        />
        <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '6px 14px',
            border: '1px solid #30363d',
            borderRadius: 6,
            background: 'transparent',
            color: '#8b949e',
            cursor: 'pointer',
            fontSize: 13
          }}>
            Cancel
          </button>
          <button type="submit" disabled={!value.trim()} style={{
            padding: '6px 14px',
            border: 'none',
            borderRadius: 6,
            background: value.trim() ? '#238636' : '#30363d',
            color: '#fff',
            cursor: value.trim() ? 'pointer' : 'not-allowed',
            fontSize: 13,
            fontWeight: 500
          }}>
            OK
          </button>
        </div>
      </form>
    </Modal>
  )
}

/**
 * Helper: Confirm dialog (replaces window.confirm)
 */
export function ConfirmModal({ open, onClose, title, message, confirmText = 'Confirm', cancelText = 'Cancel', onConfirm, danger = false }) {
  const handleConfirm = () => {
    onConfirm()
    onClose()
  }
  
  return (
    <Modal open={open} onClose={onClose} title={title} width={420}>
      <p style={{ fontSize: 14, lineHeight: 1.6, color: '#c9d1d9', marginBottom: 20 }}>{message}</p>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button onClick={onClose} style={{
          padding: '6px 14px',
          border: '1px solid #30363d',
          borderRadius: 6,
          background: 'transparent',
          color: '#8b949e',
          cursor: 'pointer',
          fontSize: 13
        }}>
          {cancelText}
        </button>
        <button onClick={handleConfirm} style={{
          padding: '6px 14px',
          border: 'none',
          borderRadius: 6,
          background: danger ? '#da3633' : '#238636',
          color: '#fff',
          cursor: 'pointer',
          fontSize: 13,
          fontWeight: 500
        }}>
          {confirmText}
        </button>
      </div>
    </Modal>
  )
}
