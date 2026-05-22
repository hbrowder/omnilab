/**
 * FirstRunWizard.jsx — 5-step initial setup wizard (CRE-16)
 *
 * Step 1: Welcome
 * Step 2: Admin password (with strength meter)
 * Step 3: Telemetry opt-in (defaults OFF — privacy-first)
 * Step 4: License key (optional — Pro now or skip)
 * Step 5: Done — quick-wins list, "Go to Dashboard"
 *
 * Talks to CRE-15 backend:
 *   GET  /api/system/first-run            -> {complete: bool}
 *   POST /api/system/first-run/complete   -> {password, telemetry, license_key?}
 *
 * Routing contract: this lives at /setup and is the destination App.jsx redirects
 * to when the backend reports `complete: false`. On success, it navigates to "/".
 */
import React, { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { completeFirstRun } from '../utils/api'

const STEPS = ['Welcome', 'Password', 'Telemetry', 'License', 'Done']

/** Rough password-strength heuristic.
 *  Returns {score: 0..4, label, color}. Score 0=very weak, 4=strong.
 *  Intentionally generous — we're not gatekeeping, we're nudging. */
function scorePassword(pw) {
  if (!pw) return { score: 0, label: 'Enter a password', color: '#374151' }
  let s = 0
  if (pw.length >= 8)  s++
  if (pw.length >= 12) s++
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++
  if (/\d/.test(pw))   s++
  if (/[^A-Za-z0-9]/.test(pw)) s++
  s = Math.min(s, 4)
  const labels = ['Very weak', 'Weak', 'Fair', 'Good', 'Strong']
  const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#10b981']
  return { score: s, label: labels[s], color: colors[s] }
}

const card = {
  background: '#161a24',
  border: '1px solid #232735',
  borderRadius: 14,
  padding: '32px 36px',
  width: 'min(560px, 92vw)',
  boxShadow: '0 8px 30px rgba(0,0,0,.35)',
  color: '#e6e8ee',
}
const btnBase = {
  padding: '11px 22px',
  borderRadius: 10,
  border: 'none',
  fontWeight: 600,
  fontSize: 15,
  cursor: 'pointer',
  fontFamily: 'inherit',
}
const btnPrimary = {
  ...btnBase,
  background: 'linear-gradient(135deg, #7c5cff 0%, #2cd4d9 100%)',
  color: '#0b0d12',
}
const btnGhost = {
  ...btnBase,
  background: '#11141c',
  color: '#e6e8ee',
  border: '1px solid #232735',
}
const inputStyle = {
  width: '100%',
  padding: '11px 14px',
  borderRadius: 10,
  background: '#11141c',
  border: '1px solid #232735',
  color: '#e6e8ee',
  fontSize: 15,
  fontFamily: 'inherit',
  outline: 'none',
}

function Stepper({ step }) {
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 24, justifyContent: 'center', flexWrap: 'wrap', rowGap: 12 }}>
      {STEPS.map((s, i) => {
        const active = i === step
        const done = i < step
        return (
          <div key={s} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            color: active ? '#e6e8ee' : done ? '#9aa3b6' : '#4a5163',
            fontSize: 13,
          }}>
            <div style={{
              width: 24, height: 24, borderRadius: '50%',
              background: done ? '#7c5cff' : active ? 'transparent' : 'transparent',
              border: active ? '2px solid #7c5cff' : done ? '2px solid #7c5cff' : '2px solid #232735',
              color: done ? '#0b0d12' : active ? '#e6e8ee' : '#4a5163',
              display: 'grid', placeItems: 'center',
              fontSize: 12, fontWeight: 700,
            }}>{done ? '✓' : i + 1}</div>
            <span>{s}</span>
            {i < STEPS.length - 1 && (
              <div style={{
                width: 20, height: 1,
                background: i < step ? '#7c5cff' : '#232735',
              }}/>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function FirstRunWizard({ onComplete }) {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [telemetry, setTelemetry] = useState(false)
  const [licenseKey, setLicenseKey] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  // Server's license activation result — { activated, plan|error }
  const [licenseResult, setLicenseResult] = useState(null)

  const strength = useMemo(() => scorePassword(password), [password])
  const passwordOk =
    password.length >= 8 &&
    password.length <= 72 && // bcrypt input cap; backend rejects > 72 bytes
    password === confirm

  const next = () => { setError(null); setStep(s => Math.min(s + 1, STEPS.length - 1)) }
  const back = () => { setError(null); setStep(s => Math.max(s - 1, 0)) }

  async function submit({ skipLicense }) {
    setError(null)
    setSubmitting(true)
    try {
      const body = {
        password,
        telemetry,
        ...(skipLicense || !licenseKey.trim() ? {} : { license_key: licenseKey.trim() }),
      }
      const r = await completeFirstRun(body)
      setLicenseResult(r.data?.license ?? null)
      setStep(4) // Done
    } catch (e) {
      const detail =
        e?.response?.data?.detail ||
        e?.message ||
        'Setup failed — please try again.'
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setSubmitting(false)
    }
  }

  function goToDashboard() {
    if (typeof onComplete === 'function') onComplete()
    navigate('/')
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0b0d12',
      display: 'grid',
      placeItems: 'center',
      padding: 24,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif',
    }}>
      <div style={card}>
        <Stepper step={step} />

        {/* ---------------- Step 1: Welcome ---------------- */}
        {step === 0 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <div style={{
                width: 44, height: 44, borderRadius: 12,
                background: 'linear-gradient(135deg, #7c5cff, #2cd4d9)',
              }}/>
              <h1 style={{ margin: 0, fontSize: 24 }}>Welcome to OmniLab</h1>
            </div>
            <p style={{ color: '#9aa3b6', lineHeight: 1.65 }}>
              You're 60 seconds from your first lab. We'll set up an admin password,
              your privacy preferences, and (optionally) activate a Pro license. You
              can change all of these later from <strong>Settings</strong>.
            </p>
            <div style={{ marginTop: 28, display: 'flex', justifyContent: 'flex-end' }}>
              <button style={btnPrimary} onClick={next} aria-label="Start setup">Let's go →</button>
            </div>
          </div>
        )}

        {/* ---------------- Step 2: Password ---------------- */}
        {step === 1 && (
          <div>
            <h2 style={{ marginTop: 0 }}>Set your admin password</h2>
            <p style={{ color: '#9aa3b6' }}>
              This replaces the default <code style={{
                background: '#11141c', padding: '1px 6px', borderRadius: 4,
              }}>admin / admin</code> credential. 8–72 characters; passphrases beat clever passwords.
            </p>

            <label style={{ display: 'block', fontSize: 13, color: '#9aa3b6', marginTop: 18, marginBottom: 6 }}>
              New password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              style={inputStyle}
              placeholder="correct horse battery staple"
              aria-describedby="pw-strength"
            />

            {/* Strength meter */}
            <div id="pw-strength" style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                flex: 1, height: 6, borderRadius: 3, background: '#11141c', overflow: 'hidden',
              }}>
                <div style={{
                  width: `${(strength.score / 4) * 100}%`,
                  height: '100%',
                  background: strength.color,
                  transition: 'width .2s ease, background .2s ease',
                }}/>
              </div>
              <span style={{ fontSize: 12, color: strength.color, minWidth: 70, textAlign: 'right' }}>
                {strength.label}
              </span>
            </div>

            <label style={{ display: 'block', fontSize: 13, color: '#9aa3b6', marginTop: 18, marginBottom: 6 }}>
              Confirm password
            </label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              style={{
                ...inputStyle,
                borderColor: confirm && confirm !== password ? '#ef4444' : '#232735',
              }}
              placeholder="Re-type to confirm"
            />
            {confirm && confirm !== password && (
              <div style={{ fontSize: 12, color: '#ef4444', marginTop: 6 }}>Passwords don't match.</div>
            )}
            {password.length > 72 && (
              <div style={{ fontSize: 12, color: '#ef4444', marginTop: 6 }}>
                Password is too long (max 72 characters).
              </div>
            )}

            <div style={{ marginTop: 28, display: 'flex', justifyContent: 'space-between' }}>
              <button style={btnGhost} onClick={back}>← Back</button>
              <button style={{ ...btnPrimary, opacity: passwordOk ? 1 : 0.5, cursor: passwordOk ? 'pointer' : 'not-allowed' }}
                      disabled={!passwordOk}
                      onClick={next}>Continue →</button>
            </div>
          </div>
        )}

        {/* ---------------- Step 3: Telemetry ---------------- */}
        {step === 2 && (
          <div>
            <h2 style={{ marginTop: 0 }}>Telemetry</h2>
            <p style={{ color: '#9aa3b6' }}>
              OmniLab is self-hosted and does not phone home by default.
              Opt in only if you'd like to share anonymous usage counts to help us prioritize features.
            </p>

            <div style={{
              marginTop: 18, display: 'flex', gap: 10, padding: 16,
              background: '#11141c', border: '1px solid #232735', borderRadius: 10,
            }}>
              <input
                type="checkbox"
                id="telemetry-opt-in"
                checked={telemetry}
                onChange={(e) => setTelemetry(e.target.checked)}
                style={{ marginTop: 3, accentColor: '#7c5cff' }}
              />
              <label htmlFor="telemetry-opt-in" style={{ cursor: 'pointer' }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Share anonymous usage stats</div>
                <div style={{ fontSize: 13, color: '#9aa3b6', lineHeight: 1.55 }}>
                  Counts of labs created, template deploys, and feature toggles. No node configs, no
                  network captures, no IP addresses. You can turn this off anytime in Settings.
                </div>
              </label>
            </div>

            <div style={{ marginTop: 12, fontSize: 12, color: '#6b7280' }}>
              Default: <strong style={{ color: '#9aa3b6' }}>off</strong>. Your choice now is just a
              starting point — toggle it from Settings whenever.
            </div>

            <div style={{ marginTop: 28, display: 'flex', justifyContent: 'space-between' }}>
              <button style={btnGhost} onClick={back}>← Back</button>
              <button style={btnPrimary} onClick={next}>Continue →</button>
            </div>
          </div>
        )}

        {/* ---------------- Step 4: License ---------------- */}
        {step === 3 && (
          <div>
            <h2 style={{ marginTop: 0 }}>Activate a Pro license (optional)</h2>
            <p style={{ color: '#9aa3b6' }}>
              Have a license key? Paste it now and unlock multi-user, scheduled backups,
              and priority patches. No key? Skip — Free is fully functional and you can
              upgrade from Settings whenever.
            </p>

            <label style={{ display: 'block', fontSize: 13, color: '#9aa3b6', marginTop: 18, marginBottom: 6 }}>
              License key
            </label>
            <input
              type="text"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              placeholder="OMNI-XXXX-XXXX-XXXX-XXXX"
              style={{ ...inputStyle, fontFamily: '"JetBrains Mono", "SF Mono", monospace' }}
              autoComplete="off"
              autoCapitalize="characters"
            />

            {error && (
              <div style={{ marginTop: 12, padding: 10, background: 'rgba(239,68,68,.1)',
                            border: '1px solid rgba(239,68,68,.35)', borderRadius: 8,
                            color: '#fca5a5', fontSize: 13 }}>
                {error}
              </div>
            )}

            <div style={{ marginTop: 28, display: 'flex', justifyContent: 'space-between' }}>
              <button style={btnGhost} onClick={back} disabled={submitting}>← Back</button>
              <div style={{ display: 'flex', gap: 10 }}>
                <button style={btnGhost} onClick={() => submit({ skipLicense: true })} disabled={submitting}>
                  Skip
                </button>
                <button style={{ ...btnPrimary, opacity: submitting ? 0.6 : 1 }}
                        onClick={() => submit({ skipLicense: false })}
                        disabled={submitting}>
                  {submitting ? 'Saving…' : 'Activate & finish →'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ---------------- Step 5: Done ---------------- */}
        {step === 4 && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 18 }}>
              <div style={{
                width: 56, height: 56, borderRadius: '50%',
                background: 'linear-gradient(135deg, #10b981, #2cd4d9)',
                margin: '0 auto 14px', display: 'grid', placeItems: 'center',
                fontSize: 28, color: '#0b0d12', fontWeight: 700,
              }}>✓</div>
              <h2 style={{ margin: 0 }}>You're all set</h2>
              <p style={{ color: '#9aa3b6', marginTop: 6 }}>
                OmniLab is ready. Here's where to go next:
              </p>
            </div>

            {licenseResult && (
              <div style={{
                margin: '0 0 18px',
                padding: 12,
                background: licenseResult.activated ? 'rgba(16,185,129,.1)' : 'rgba(245,158,11,.1)',
                border: `1px solid ${licenseResult.activated ? 'rgba(16,185,129,.35)' : 'rgba(245,158,11,.35)'}`,
                borderRadius: 8,
                fontSize: 13,
                color: licenseResult.activated ? '#86efac' : '#fcd34d',
              }}>
                {licenseResult.activated
                  ? <>License activated — you're on the <strong>{licenseResult.plan}</strong> plan.</>
                  : <>License didn't take: {licenseResult.error}. You can try again from Settings.</>}
              </div>
            )}

            <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 14, lineHeight: 1.8 }}>
              <li>📦 <strong>Templates</strong> — one-click deploy a Wazuh SOC, K8s cluster, or LLM lab</li>
              <li>🎨 <strong>New lab</strong> — drag-and-drop your own multi-VM topology</li>
              <li>📚 <strong>Docs</strong> — full REST API reference is at <code>/docs</code> on this host</li>
              <li>⚙️ <strong>Settings</strong> — change password, telemetry, or activate a license later</li>
            </ul>

            <div style={{ marginTop: 28, display: 'flex', justifyContent: 'center' }}>
              <button style={btnPrimary} onClick={goToDashboard}>Go to Dashboard →</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
