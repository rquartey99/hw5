# Design: Campus Customs Desk (agent dashboard)

**What it is:** `frontend/`, a React + Vite + TypeScript page for watching the agent team work a ticket, approving the money it wants to spend, and keeping an eye on cash. It calls the Problem 7 backend at `http://127.0.0.1:8000`; override with `VITE_API_BASE`.

**Run it:**
1. Start the backend from `backend/` with `uvicorn main:app --reload --port 8000`.
2. Start the dashboard from `frontend/` with `npm install`, then `npm run dev`.
3. Open http://localhost:5173.

## What I chose and why

### Built on Homework 4's look
| Choice | Carried from HW4 | Why |
|---|---|---|
| **Colors** | Yale navy `#00366b` (deep `#002549`), teal `#046e82` for labels and links, neutral greys `#1d1d1d` … `#f6f6f6`, gold `#f2c94c` for trim and highlights | It's the same shop, so it should feel like the same brand. Navy reads as "trusted desk," and gold marks what needs attention. |
| **Type** | Libre Baskerville serif for headings and numbers; Inter for everything else | The serif gives it a collegiate, ledger-like feel, especially on dollar amounts. Inter keeps the dense status text readable. |
| **Handsome Dan** | The same original bulldog sprite (`Dan.tsx`) | Dan is the **boss**. His mood follows the run: *sleepy* when nothing's happening, *thinking* while the team works, *winking* when the job is done. The team's leader is a face people already know from the shop site. |
| **Cards and gold trim** | White rounded cards, soft shadows, a gold line under the navy bar | Familiar and calm. It looks like a tool, not a game. |

### Seasonal vibe: late summer / move-in week
The board takes its season from the **shop's desk date**, not the computer clock. The date shown is **Mon, Aug 31, 2026**, which is move-in week in New Haven.
- **Golden-hour sky:** the navy header has a soft gold sun glow in the top-right corner, like a late-August evening on Chapel Street.
- **Elm City leaves:** New Haven is "the Elm City," and the shop's landlord is Elm City Properties. A few elm leaves drift slowly across the header. They are still green, with a couple already gold, to hint at the coming fall term. The date chip carries a leaf too.
- **Warm paper page:** the background starts as a warm off-white under the header and fades to the usual grey, so it feels sunlit rather than clinical.
- **A seasonal line in the footer:** "Boxes on Chapel Street, freshmen on Old Campus — busy week."
- **It changes with the date:** if the desk date moves, the theme follows (`season.ts`). Fall turns the leaves orange and red, winter goes icy blue, and spring brings blossom pink. No code changes are needed.

### Keeping it uncluttered
- **One screen, two columns:** tickets on the left, the selected ticket's story on the right. Nothing else competes.
- **Each agent card shows only three things:** who it is, a status dot with one line of what it's doing ("Checking the cash," "Waiting on Accounting"), and the last thing it said, cut to four lines.
- **The full conversation is folded away:** it opens while the team works so you can follow along live, then folds shut when the run ends. The short per-agent summaries take its place.
- **Approvals only appear when something is waiting**, and they sit above everything else.

## Creative touches that make it enjoyable
1. **The approval is a check you sign.** When accounting wants to pay, the card is drawn like a paper check: "Pay to the order of *Elm City Properties*," the amount in a boxed ledger figure, a memo line with the ticket and which agent asked. The button says **"Approve as Regi."** Typing your name under "Approving as" is your signature, and it's remembered next time. Spending real money should feel deliberate, and this makes the human-in-the-loop step tangible instead of a bare "OK" button.
2. **A "Resolved" stamp.** When a run finishes, the ticket card gets a green rubber stamp that thunks down at an angle. Small, satisfying, and easy to spot.
3. **The active agent glows gold.** As work moves boss → facilities → accounting, the gold outline moves with it. A breadcrumb above the cards ("Boss → Facilities → Accounting") shows the hand-offs, so delegation is visible at a glance.
4. **Dan reacts.** He dozes when the desk is quiet, furrows his brow while the team works, and winks when the job's done. He's in the header too.
5. **A balance with a conscience.** The checking balance sits top-right in a big serif figure and pops when it changes. It turns amber with a "Below $500" note when it crosses accounting's warning line, so your own shop rule is built into the display.
6. **Plain-English activity.** Tool names are translated: `get_lease` → "Pulling up the lease," `quote_bulk_discount` → "Pricing a discount." You read what the team is doing, not function calls. The raw details stay in the conversation for anyone who wants them.
7. **"Send in the team."** The main button speaks like the shop, not like an API.

## Accessibility and comfort
- Every animation (drifting leaves, pulsing dots, stamp, pop) switches off for people who prefer reduced motion.
- Status is never color alone: each dot has a text label for screen readers, and every card says its status in words.
- Navy on white and grey-700 on white meet comfortable contrast; amber warnings pair color with text.
- The layout stacks into one column on narrow screens.

## Where things live
| File | What's in it |
|---|---|
| `frontend/src/App.tsx` | Layout, polling (every 1.2 s while the team works, 4 s otherwise), start, approve and reset |
| `frontend/src/runs.ts` | Turns `/api/events` into each agent's live state, the hand-off chain and the conversation |
| `frontend/src/season.ts` | Desk date → season, label and footer line |
| `frontend/src/components/` | `AgentFloor`, `ApprovalCard` (the check), `TicketList` (with the stamp), `Summaries`, `Feed`, `Dan`, `AgentAvatar`, `ElmLeaf` |
| `frontend/src/index.css` | HW4 palette and type, plus the seasonal variables (`.season-late-summer` is the default, plus fall, winter and spring) |

Handsome Dan is original artwork inspired by Yale's mascot, not the trademarked logo (same note as Homework 4).
