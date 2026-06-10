# TWC Demo — Run of Show

**Length:** 15-18 minutes plus questions (Act 4 is optional — cut it if time is short)
**Setup before they walk in:** Spark running, `run_demo.sh` already launched, browser open on Tab 1, Reset demo clicked. Network disconnected.

---

## Opening (1 min)

Frame it before touching anything:

> "Everything you're about to see is running on this machine, right here, with no internet connection. Lamar's network restricts AI tools, so we built the demonstration to run fully self-contained. This is the same kind of AI agent every participant in our program builds for their own business by Friday of the training week."

Point at the green badge: **100% LOCAL — NO INTERNET**.

The fictional business: Gulf Coast Machining, a 22-person CNC machine shop in Beaumont serving the petrochemical plants. Exactly the profile of business the TWC grant serves.

## Act 1 — Chatbot vs. Agent (3 min) — Tab 1

This is the core concept of Day 1 of the curriculum.

1. Toggle to **Plain chatbot**. Ask: *"What's our lead time on custom Inconel parts right now?"*
   - It will say it has no idea. That's every generic AI tool.
2. Toggle to **Agent**. Ask the same question.
   - Point at the Agent Activity panel as it reads the pricing file: "Watch the right side. It's checking the company's actual pricing sheet before it answers. It doesn't guess."
3. Click the email chip (draft to Jenny). Show the draft appearing — written in the company's voice, from their policy file.

> Talking point: "The difference isn't a smarter chatbot. It's that the agent knows this business and can take actions."

## Act 2 — The Morning Workflow (5-6 min) — Tab 2

The wow moment. Narrate over the activity panel while it runs.

1. Show the inbox first — click a couple of emails open. "This is a normal Tuesday morning for a shop like this: a plant-down emergency, a quote request, a quality complaint, a sales pitch, a new customer, a billing question."
2. Click **Run Morning Workflow**. Narrate the steps as they fire:
   - It reads the pricing and policy files first
   - It reads every email
   - It triages: the plant-down email from Sabine River Chemical gets flagged URGENT
   - Drafts appear in the outbox one by one
3. **The detail to call out:** Sabine River's contract waives expedite fees. Watch for the agent catching that on the rush job and on the invoice question (email 6). When it does:
   > "Nobody told it that. It read the contract terms in the pricing file and applied them. That's a billing error a busy office manager misses."
4. The owner summary lands at the bottom: every email, priority, action taken, what needs a human.

> Talking point: "Thirty minutes of morning email triage just became two minutes of reviewing drafts. Every draft stays a draft — a human approves before anything sends. That's how we teach safe use."

## Act 3 — Document Analysis (3 min) — Tab 3

1. Pick **invoice-sabine-river.txt** → Analyze. The agent should flag the wrongly-charged $1,475 expedite fee against the contract waiver.
2. If time, run **safety-incident-report.txt**: it extracts the near-miss, the root causes, and the open corrective actions — relevant for every plant-adjacent SMB in our region.

## Act 4 — Quote Builder (3 min) — Tab 4

The teaching moment: **language models are bad at arithmetic.** Ask any chatbot to multiply three numbers and it will confidently get it wrong. Agents solve this by handing math to a calculator tool.

1. Click the **Sabine River plant-down** request chip. Narrate the activity panel:
   - It reads the pricing sheet
   - Every number goes through the `calculate` tool — point at the calls firing: "Watch — it never does math in its head. Each calculation is a tool call, exact every time."
   - It catches that Sabine River's contract **waives the 35% expedite fee**, and that Inconel quotes are only valid 10 days
2. The formal quote card appears on the right: line items, subtotal, total, lead time, validity.

> Talking point: "This is the lesson we teach on tools day. You don't need a smarter model to get reliable numbers — you need an agent that knows what models are bad at and uses a tool instead. A quote that used to take an hour of looking things up takes one paste."

## Close (1 min)

> "Our 5-day program takes a non-technical business owner from never having used AI to leaving with an agent like this, built for their business, on the last day. What you saw runs on $4,000 of hardware on a desk in Beaumont. The skills gap isn't the technology — it's training. That's what this partnership funds."

## If something goes sideways

- Agent stalls or rambles → click **Reset demo**, rerun. Smaller blast radius than apologizing.
- Total failure → backup video (record it during Loop 3 dry run) on the desktop.
- Question you can't answer about the model → "It's an open-weight model running through Ollama; the curriculum itself teaches claude.ai, this hardware setup is just how we demo inside Lamar's network restrictions."

## Q&A ammo

- **"Is this what trainees actually use?"** Trainees use claude.ai (cloud, $20/mo) — more capable and no hardware needed. This local rig exists for offline demos and shows the floor, not the ceiling.
- **"What about data privacy?"** Both modes covered in Module 02: the cloud platform's data settings, and this — fully local — as the maximum-privacy option for sensitive industries.
- **"How much hardware does an SMB need?"** None to start. A laptop and a browser. This box is for demonstrations.
