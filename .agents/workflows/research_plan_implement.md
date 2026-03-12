---
description: Research, Plan, Implement Workflow (End-to-End)
---

# Research, Plan, Implement Workflow (End-to-End)

This represents a standardized methodology for tackling new features, severe bugs, or necessary project pivots. It splits agentic behavior into five distinct roles to ensure well-architected, fully tested, and result-oriented solutions.

## Communication Protocol
Agents must communicate exclusively by appending updates to strictly named markdown files. **Every single update must include the current date.** Whenever an approach or hypothesis fails, explicitly document it as "experimented but failed" detailing why.

The canonical communication files are:
- `research_log.md`
- `implementation_plan.md`
- `implementation_log.md`
- `test_report.md`
- `validation_report.md`

## The 5-Step Pipeline

1. **Invoke the Researcher:** 
   - Skill: `../.agents/skills/researcher/SKILL.md`
   - Goal: Investigate state, search the internet for relevant open-source repos, test hypotheses.
   - Output: `research_log.md`

2. **Invoke the Planner:** 
   - Skill: `../.agents/skills/planner/SKILL.md`
   - Goal: Digest research, write step-by-step instructions, define test criteria.
   - Output: `implementation_plan.md` (Requires user approval before proceeding)

3. **Invoke the Implementer:** 
   - Skill: `../.agents/skills/implementer/SKILL.md`
   - Goal: Write code strictly according to plan.
   - Output: `implementation_log.md`

4. **Invoke the Tester:**
   - Skill: `../.agents/skills/tester/SKILL.md`
   - Goal: Run automated tests (unit/integration) to verify the code executes flawlessly.
   - Output: `test_report.md` (If failed, loops back to Implementer)

5. **Invoke the Validator:**
   - Skill: `../.agents/skills/validator/SKILL.md`
   - Goal: Perform result-oriented checks. Confirm the goal is met from an end-user perspective.
   - Output: `validation_report.md` (If failed, loops back to Planner or Researcher)