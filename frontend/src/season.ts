// The board takes its season from the shop's desk date (cash_accounts.date), not the computer's clock.

export type SeasonKey = 'late-summer' | 'fall' | 'winter' | 'spring' | 'summer'

export interface Season {
  key: SeasonKey
  label: string
  greeting: string
}

export function seasonFor(isoDate: string | undefined): Season {
  const d = isoDate ? new Date(`${isoDate}T12:00:00`) : new Date()
  const m = d.getMonth() + 1
  const day = d.getDate()
  const md = m * 100 + day
  if (md >= 815 && md <= 921) {
    const moveIn = md >= 825 && md <= 907
    return {
      key: 'late-summer',
      label: moveIn ? 'Move-in week' : 'Late summer',
      greeting: moveIn ? 'Boxes on Chapel Street, freshmen on Old Campus — busy week.' : 'Golden afternoons on the Green.',
    }
  }
  if (md >= 922 && md <= 1220) return { key: 'fall', label: 'Fall term', greeting: 'Elm leaves turning on Hillhouse.' }
  if (md >= 1221 || md <= 319) return { key: 'winter', label: 'Winter', greeting: 'Cocoa weather in the Elm City.' }
  if (md >= 320 && md <= 614) return { key: 'spring', label: 'Spring term', greeting: 'Magnolias out on Cross Campus.' }
  return { key: 'summer', label: 'Summer', greeting: 'Quiet summer on campus.' }
}

export function formatDeskDate(isoDate: string | undefined): string {
  if (!isoDate) return '—'
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
}
