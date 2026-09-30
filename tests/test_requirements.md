# Day 1 test set — 10+ requirement inputs

SRS Section 22 (Testing Requirements) wants both quality and failure cases,
not only clean successes. Run each of these through the Streamlit UI (or
directly via `POST /generate`), and for each one record: did it produce
valid JSON? Did it avoid inventing facts? Did it correctly separate stated
facts from assumptions? Did it raise an open question where one was needed?

Keep a simple log (a spreadsheet or a markdown table) of pass/fail per case
— that log is your actual Day 1 evidence, not this file.

## Ordinary / well-formed requirements (expect clean structured output)

1. "We need a mobile app where customers can book appointments with our
   stylists. Should support push notification reminders. Payment handling
   can come later."

2. "Build an admin dashboard for our e-commerce store showing daily sales,
   top products, and low-stock alerts. Must be accessible on desktop only."

3. "The client wants a customer support chatbot on their website that can
   answer FAQs and escalate to a human agent if it can't help. Must support
   English and Urdu."

4. "We need a system for a school to track student attendance. Teachers
   mark attendance from a tablet. Parents get a notification if their child
   is marked absent."

5. "Add a search feature to our existing product catalog. Users should be
   able to filter by category, price range, and rating."

## Vague / underspecified (expect assumptions + open questions, not invented specifics)

6. "We want something like Uber but for home cleaning services."

7. "The client mentioned they want 'better reporting' in their internal
   tool. No further detail was given in the meeting."

8. "Make the checkout process faster."

## Conflicting or ambiguous (expect the model to surface the conflict, not silently pick one)

9. "In the first call the client said they need a native iOS app. In a
   follow-up email, they said budget only allows for a web app for now."

10. "The requirements doc says user roles are Admin and Member only, but
    the client's screenshot shows a 'Manager' role in the user list."

## Edge cases / failure behavior (expect graceful handling, never a crash or fabrication)

11. "" (empty string) — the API should reject this with a 400 before ever
    calling the model (see `main.py`'s check); confirm the UI shows a clear
    message rather than a blank/broken screen.

12. "asdkjaslkdj alksjd" (gibberish, no real content) — expect a spec with
    an empty or near-empty summary, empty features/stories, and an open
    question asking for more detail. This is the FAILURE BEHAVIOR case
    from the prompt — the model must not invent a plausible-sounding
    project out of nothing.

13. A very long, rambling paste of unrelated meeting chatter with only one
    buried real requirement in the middle (write your own ~300-word
    example) — checks whether the model actually reads the whole input
    instead of just the first sentence.

## What "pass" looks like

- JSON always parses (or the app shows `invalid_json` cleanly, not a crash).
- No feature/summary claims a fact that isn't in the source text.
- Vague inputs (#6-8) produce real open_questions, not confident-sounding
  guesses dressed up as features.
- The conflict cases (#9-10) show up as open_questions or assumptions that
  name the conflict — not a silent pick of one option.
- The failure cases (#11-12) never crash the API or UI, and #12 never
  invents a plausible project.
