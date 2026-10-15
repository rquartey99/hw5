// Round badge for each agent. The boss is Handsome Dan (from Homework 4); teammates get a simple line icon.
import type { ReactNode } from 'react'
import type { AgentName } from '../types'
import Dan, { type DanMood } from './Dan'

const ICONS: Record<Exclude<AgentName, 'boss'>, ReactNode> = {
  // box
  inventory: (
    <>
      <path d="M5 8.5 12 5l7 3.5v7L12 19l-7-3.5z" />
      <path d="M5 8.5 12 12l7-3.5M12 12v7" />
    </>
  ),
  // coin stack
  accounting: (
    <>
      <ellipse cx="12" cy="7" rx="6" ry="2.5" />
      <path d="M6 7v4c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V7M6 11v4c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5v-4" />
    </>
  ),
  // storefront with awning
  facilities: (
    <>
      <path d="M4 9.5 5.5 5h13L20 9.5" />
      <path d="M4 9.5c0 1.2 1 2 2 2s2-.8 2-2c0 1.2 1 2 2 2s2-.8 2-2c0 1.2 1 2 2 2s2-.8 2-2c0 1.2 1 2 2 2s2-.8 2-2" />
      <path d="M5.5 11.5V19h13v-7.5M10 19v-4.5h4V19" />
    </>
  ),
  // speech bubble
  customer_service: (
    <>
      <path d="M5 6.5h14v9H11l-4 3v-3H5z" />
      <path d="M8.5 10h7M8.5 12.5h4.5" />
    </>
  ),
}

interface Props {
  agent: AgentName
  size?: number
  mood?: DanMood
}

export default function AgentAvatar({ agent, size = 44, mood = 'happy' }: Props) {
  if (agent === 'boss') {
    return <Dan size={size} mood={mood} badge className="avatar" />
  }
  return (
    <span className={`avatar avatar-${agent}`} style={{ width: size, height: size }} aria-hidden="true">
      <svg viewBox="0 0 24 24" width={size * 0.56} height={size * 0.56} fill="none" stroke="currentColor"
        strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        {ICONS[agent]}
      </svg>
    </span>
  )
}
