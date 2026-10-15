// Handsome Dan-inspired bulldog sprite (original artwork, not Yale's trademarked logo).
// Moods: happy (default), sleepy (empty states / 404), thinking (chat typing), wink (greetings).

export type DanMood = 'happy' | 'sleepy' | 'thinking' | 'wink'

interface Props {
  size?: number
  mood?: DanMood
  badge?: boolean // navy circle behind Dan, for icons and avatars
  title?: string // accessible label; omit for decorative use
  className?: string
}

const INK = '#1d1d1d'
const NAVY = '#00356b'

function Eyes({ mood }: { mood: DanMood }) {
  if (mood === 'sleepy') {
    return (
      <g stroke={INK} strokeWidth="3" strokeLinecap="round" fill="none">
        <path d="M37 53 Q44 58 51 53" />
        <path d="M69 53 Q76 58 83 53" />
      </g>
    )
  }
  const lookUp = mood === 'thinking' ? -3 : 0
  return (
    <g>
      <circle cx="44" cy={52 + lookUp} r="6" fill={INK} />
      <circle cx="46" cy={50 + lookUp} r="2" fill="#fff" />
      {mood === 'wink' ? (
        <path d="M69 53 Q76 49 83 53" stroke={INK} strokeWidth="3" strokeLinecap="round" fill="none" />
      ) : (
        <>
          <circle cx="76" cy={52 + lookUp} r="6" fill={INK} />
          <circle cx="78" cy={50 + lookUp} r="2" fill="#fff" />
        </>
      )}
    </g>
  )
}

export default function Dan({ size = 48, mood = 'happy', badge = false, title, className }: Props) {
  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      className={className}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {badge && <circle cx="60" cy="60" r="60" fill={NAVY} />}
      <g transform={badge ? 'translate(9 7) scale(0.85)' : undefined}>
        {/* Collar with a "Y" tag */}
        <path d="M30 94 Q60 108 90 94 L92 104 Q60 119 28 104 Z" fill={NAVY} stroke="#fff" strokeWidth="2" />
        <circle cx="60" cy="110" r="7" fill="#f2c94c" stroke={INK} strokeWidth="1.5" />
        <path d="M57 106.5 L60 110 L63 106.5 M60 110 V114" stroke={INK} strokeWidth="1.6" fill="none" strokeLinecap="round" />

        {/* Ears */}
        <path d="M26 36 Q8 26 12 50 Q20 54 32 44 Z" fill="#b9a38c" stroke={INK} strokeWidth="2.5" strokeLinejoin="round" />
        <path d="M94 36 Q112 26 108 50 Q100 54 88 44 Z" fill="#b9a38c" stroke={INK} strokeWidth="2.5" strokeLinejoin="round" />

        {/* Head */}
        <path
          d="M60 22 C89 22 102 38 102 60 C102 82 86 97 60 97 C34 97 18 82 18 60 C18 38 31 22 60 22 Z"
          fill="#f7f2e9"
          stroke={INK}
          strokeWidth="3"
        />
        {/* Tan patch over one eye */}
        <path d="M66 42 Q78 36 88 44 Q90 58 78 60 Q68 60 66 50 Z" fill="#e6d2b5" />

        {/* Brow wrinkles */}
        <g stroke={INK} strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.75">
          <path d="M45 33 Q60 27 75 33" />
          <path d="M50 39 Q60 35 70 39" />
          {mood === 'thinking' && <path d="M68 42 Q76 38 84 41" />}
        </g>

        <Eyes mood={mood} />

        {/* Muzzle (jowls) */}
        <path
          d="M32 74 C32 61 47 59 60 65 C73 59 88 61 88 74 C88 86 75 90 60 86 C45 90 32 86 32 74 Z"
          fill="#fff"
          stroke={INK}
          strokeWidth="2.5"
        />
        {/* Nose */}
        <path d="M49 61 Q60 54 71 61 Q71 70 60 72 Q49 70 49 61 Z" fill={INK} />
        <ellipse cx="56" cy="60.5" rx="4" ry="2" fill="#fff" opacity="0.5" />
        {/* Mouth and bulldog underbite */}
        <path d="M60 72 V77" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />
        <path d="M43 80 Q60 92 77 80" stroke={INK} strokeWidth="2.5" fill={mood === 'happy' || mood === 'wink' ? '#e98a8a' : 'none'} strokeLinejoin="round" />
        <path d="M49 82 L51.5 75.5 L54 83.5 Z" fill="#fff" stroke={INK} strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M66 83.5 L68.5 75.5 L71 82 Z" fill="#fff" stroke={INK} strokeWidth="1.4" strokeLinejoin="round" />

        {/* Sleepy "z"s */}
        {mood === 'sleepy' && (
          <g fill={NAVY} fontFamily="Georgia, serif" fontWeight="700">
            <text x="92" y="24" fontSize="14">z</text>
            <text x="102" y="12" fontSize="10">z</text>
          </g>
        )}
      </g>
    </svg>
  )
}
