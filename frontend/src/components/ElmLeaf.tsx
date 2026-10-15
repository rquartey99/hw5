// An elm leaf (New Haven is the Elm City). Colored by the season's --leaf variables.
export default function ElmLeaf({ size = 22, className }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} className={className} aria-hidden="true">
      <path
        d="M16 3c6 3 10 9 9 15-1 5.5-5 9-9 10-4-1-8-4.5-9-10C6 12 10 6 16 3z"
        fill="var(--leaf, #8fb05a)"
        stroke="var(--leaf-edge, #5d7a34)"
        strokeWidth="1.2"
      />
      <path d="M16 6v24M16 12l-5-3M16 12l5-3M16 17l-6-3M16 17l6-3M16 22l-5-2.5M16 22l5-2.5"
        stroke="var(--leaf-edge, #5d7a34)" strokeWidth="1" fill="none" strokeLinecap="round" />
    </svg>
  )
}
