# AI Prompts — Homework 5

A record of the prompts I typed to complete each problem.

---

## Problem 2

**Prompt:**
> okay now for problem 2: Study the Campus Customs database
> open the campus_customs.db file and examine every table and its fields. copy the original file to data/campus_customs_new.db and make sure that every subsequent problem updates the working copy and not the original. in the new.db, study the 3 open tickets and and examine how they link to other tables. note this in output/harness.md. also in the harness, for each table list the fields and a sentence or two on why that table matters for the agents

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 3

**Prompt:**
> okay now for problem 3: Build the MCP server
> write an mcp server in mcp_server/ using FastMCP. this is what will talk to data/campus_customs_new.db. no need to connect/run it at this point. for now create 3 tools that will help solve the tickets in the db. keep names for these tools clear and distinct. ONLY USE INFO IN THE DATABASE. update the harness with the 3 mcp tools and for each tool include the table it reads, which ticket it helps unlock (101, 102, 103), and a sentence on why that tool is the right one for the ticket. finally add a short mcp_server/README.md file that explains what the mcp server is for, which db file it uses, and the 3 tools it has

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 4

**Prompt:**
> okay now for problem 4: Add the MCP server to vibe coder and test each tool
> add the mcp server to this project so that you can call the tools created in the problem before. save the connection json text in .mcp.json at the project root. once you're directly connected with the tools, test each of the 3 mcp tools. save the evidence to output/mcp_smoke.json. for every tool include:
> the prompt the vibe coder was asked
> the tool name
> the tool output (must match values in campus_customs_new.db)

**Follow-up prompt (if needed):**
> I restarted the session and the campus-customs MCP server is connected. continue problem 4: call each of the 3 tools directly and save output/mcp_smoke.json

**Why the first prompt didn't work:**
Claude Code only loads servers from .mcp.json when a session starts, so the new campus-customs tools couldn't be called until the app was restarted.

---

## Problem 5

**Prompt:**
> okay now time for problem 5: Build the agent team and grow the mcp tools
> build the agentic team for Campus Customs using pydanticai. the different agents are
> boss
> inventory
> accounting
> facilities
> customer service
> include prompts, models, and agent loops so they can delegate work to each other w full connectivity
> put agent prompts in backend/prompts/ and make one file per agent. put data types in backend/models.py, and the agent files in backend/ (organization doesn't matter as long as 5 agent roles are clear)
> use PORTKEY_API_KEY and ONLY gpt-6-luna for every agent
> I'll write each prompt w shop rules the agents need in my own words so remind me of that
> add any tools the agents need to the mcp server so they can work on open tickets. shop facts come from the mcp server over campus_customs_new.db (don't invent anything new)
> wire agents so they append to output/audit_trail.json as they run: for each agent-loop step, record enough to audit later. append to this file; don't wipe it each run
> in the harness, list each agent and each mcp tool (including the ones added in this problem) along w which table the tool uses. also add a brief safety section: guardrails a real business would have when agents touch real customers and real money, plus limits that keep token use in check
> update mcp_server/README.md so the tool list matches what we have now

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 6

**Prompt:**
> lets do problem 6: Plan the three tickets
> build output/desk_tickets.html which will be a page i can double click with one tab per ticket (101, 102, 103). also add empty Cash and Reflection tabs for later problems (you can just add a pretty "Coming soon" note for now)
> on each ticket create an Expected section that includes:
> who the boss should call first and why
> all the agent delegations I expect
> which mcp tools i expect that run to use
> I will fill in this section for each ticket in my own words, but help me figure out what to write

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 7

**Prompt:**
> okay now for problem 7: Backend routes
> in backend/main.py use FastAPI and add routes  that do the following:
> return 3 tickets and whether each is open or resolved
> take a ticket id  and run my agent team on that ticket
> return recent agent events so the board can refresh
> approve payment/purchase after human clicks approve
> return current checking balance from cash_accounts
> reset database to original values when i want to try a fresh run
> from the backend/ folder, the server should start with: "uvicorn main:app --reload --port 8000"
> in the harness, list each route in one line (what URL / what it does)

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 8

**Prompt:**
> for problem 8: agent dashboard
> build frontend dashboard in frontend/ with react + vite + typescript. the page should call the routes i built in problem 7. the board should have:
> list all 3 tickets
> let me pick 1 ticket and have agent team start on it
> show each agent and what they're doing / saying while ticket runs
> mark ticket as resolved when run finishes
> show short summary of what each agent did on ticket
> let human approve pay / purchase when asked
> show checking balance
> please make dashboard look good. base it off design choices in hw4 + a seasonal vibe so it matches what the date shows but don't make things look too cluttered
> frontend should talk to backend at server specified in previous problem. on backend allow vite page origin so browser is allowed to call those routes
> finally write output/design.md with what i chose for the dashboard look and why, including creative choices that make it feel special and something humans would enjoy using

**Follow-up prompt (if needed):**
> wait please use ports 8000 and 5173. add that to the second section in ai_prompts

**Why the first prompt didn't work:**
Claude tested the dashboard on temporary ports (8765 and 4173) instead of the backend and Vite ports set in Problem 7 (8000 and 5173).

---

## Problem 9

**Prompt:**
> okay now for problem 9: Resolve the tickets
> reset the working database. note the starting balance (should be 3400) then run all 3 tickets until each is resolved. open the webpage so I can see all of this happening. next open output/desk_tickets.html and on each tab fill out an Actual section from this run: which agents worked, what they delegated, and which tools they used. keep the Expected section from problem 6 so the two can be compared. on the Cash tab  of desk_tickets.html, itemize the money based on:
> starting balance (after the reset)
> for each ticket: how cash changed when that ticket resolved, and why (which pay/purchase, $ amount)
> ending checking balance, which must match cash_accounts in the working database.
> please please ensure that the cash math is correct
> also save: 
> output/resolved_tickets.json which shows for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
> output/resolved_board.html which is a page i can double click with a screenshot of my react board for each resolved ticket
> append real runs to output/audit_trail.json and finish the harness so it covers tables, mcp tools, the 5 agents, api routes, the dashboard, and safety rules

**Follow-up prompt (if needed):**
> wait is is possible to reset the working database and redo everything? i think i messed up
>
> I'll press Send in the team on the board myself, one ticket at a time, and approve checks as they show up. tell me when to start and watch for each run to finish.
>
> wait sorry you start them

**Why the first prompt didn't work:**
In the first pass both Regi (on the board) and Claude started ticket runs, so ticket 101 ran twice; before that, accounting hadn't queued rent because Claude's role text in its prompt predated the approval queue. So the database was reset and Claude reran the three tickets one at a time.

---

## Problem 10

**Prompt:**
> okay problem 10: Reflection
> in output/desk_tickets.html fill out the Reflection tab my answers to the following questions:
>
> 1. How would you evaluate the performance of the agents on each ticket and why?
>
> I think that for ticket 102 (rent), the agents did an excellent job in both assessing and solving the problem, completing the process in about the same manner I expected them to. However, for tickets 101 and 103, I don't think they did well at all. For ticket 101, the customer_service agent didn't reach out to Tauhid to check if he wanted the shirt in another size. And in ticket 103, no agent reached out to me to see if there was an alternative method.
>
> 2. For each ticket, how did the Actual compare to the Expected plan you wrote earlier?
>
> For ticket 101,  agents were called in the order I expected. However, the customer_service agent did not prompt me to reply to Tauhid at all. I did not account for this. For ticket 102, the agents were more efficient than I expected, with the Boss immediately calling Accounting to pay for rent, completely bypassing Facilities. Other than that, the problem was resolved in the manner I expected. For ticket 103, I mistakenly believed Inventory wouldn't be called, so I predicted one too few many agent calls. But as with ticket 101, I was disappointed that there was no prompting about a need for human intervention.
>
> 3. What would have been simpler as one agent with tools -- and why?
>
> I think for problems this small, just having a single agent solve everything would have been more efficient. The problems would have been resolved much faster as there would be no need to fill other agents in on context.
>
> 4. Describe 3 new problem Campus Customs might face that this agent could solve with the tools you built.
>
> Invoices related to facilities
> Questions about inventory alternatives
> Day to day management of employees
>
> 5. Describe 3 new problems Campus Customs might face that this agent team could not solve with the tools you built, and explain the tools and agents you would need to solve them.
>
> Interactions with future collaborators (brand partnerships, etc.) -- would need to empower Customer_service agent to speak with humans
> Site maintenance -- would need to create another agent that was solely focused on that
> Employee management -- agents are not equipped to figure out how salaries affect cash. Would need to create another agent for HR purposes, or give Accounting agent tools to access employee salaries

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 11

**Prompt:**
> now for problem 11: Submit to GitHub
> do the equivalent thing you did for hw4 here. make sure what's pushed has the following organization:
> hw5/
> AI_prompts.md
> requirements.txt
> .env.example
> .gitignore
> .mcp.json
> README.md
> data/
> campus_customs.db (inside data/)
> campus_customs_new.db (inside data/)
> mcp_server/
> server.py (inside mcp_server/)
> README.md (inside mcp_server/)
> frontend/
> backend/
> main.py (inside backend/)
> models.py (inside backend/)
> prompts/ (inside backend/)
> boss.md (inside prompts/)
> inventory.md (inside prompts/)
> accounting.md (inside prompts/)
> facilities.md (inside prompts/)
> customer_service.md (inside prompts/)
> output/
> harness.md (inside output/)
> mcp_smoke.json (inside output/)
> desk_tickets.html (inside output/)
> design.md (inside output/)
> resolved_tickets.json (inside output/)
> resolved_board.html (inside output/)
> audit_trail.json (inside output/)
> github_url.txt (inside output/)
> README should explain to copy original DB to working one when clean run is needed, start MCP server, start FastAPI backend, start React board, reset DB before full 3-ticket run
> any questions?

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---
