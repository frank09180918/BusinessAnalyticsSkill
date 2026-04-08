# biz-analytics — Harvard Business Analytics Skill for Claude Code

A Claude Code skill that structures any business problem using Harvard's **9 core skills** framework for analytics professionals.

Invoke it with `/biz-analytics [your business question]` and get a structured analysis report every time.

---

## What It Does

Instead of free-form analysis, this skill forces every response through a disciplined framework:

1. **Classify the problem** — Which of the 4 Harvard analytics types applies?
2. **Analyze across 6 thinking dimensions** — From raw curiosity to business impact
3. **Recommend the right tools** — SQL, Python/R, or statistical software
4. **Deliver a structured output** — Insights → Visualization → Action → Limitations

---

## The Harvard Framework (Distilled)

### 4 Types of Analytics

| Type | Question It Answers |
|------|-------------------|
| Descriptive | What is happening right now? |
| Diagnostic | Why did it happen? |
| Predictive | What is likely to happen next? |
| Prescriptive | What should we do about it? |

### 6 Thinking Dimensions

- **Communicator** — Who is the audience? What format serves them best?
- **Inquisitive** — What questions haven't been asked yet? What data is missing?
- **Problem Solver** — Phenomenon → Cause → Solution, supported by statistics
- **Critical Thinker** — What are the data's limits? What should be excluded?
- **Visualizer** — Which chart type? How does a non-technical reader understand it?
- **Big Picture** — How does this finding affect revenue, cost, or market share?

---

## Installation

Copy the `biz-analytics/` folder into your Claude Code skills directory:

```bash
# macOS / Linux
cp -r biz-analytics ~/.claude/skills/

# Reload Claude Code to activate the skill
```

---

## Usage

```
/biz-analytics [describe your business problem]
```

**Examples:**

```
/biz-analytics Our e-commerce conversion rate dropped 15% last month. Find the cause and suggest fixes.

/biz-analytics We want to predict which customers will churn in the next 90 days.

/biz-analytics Compare the ROI of our last three marketing campaigns.
```

---

## Output Structure

Every analysis returns:

```
## Analysis Type
[Descriptive / Diagnostic / Predictive / Prescriptive — with reasoning]

## Key Insights
[3–5 findings, each backed by data]

## Visualization Recommendations
[Chart type + key variables]

## Action Recommendations
[Prioritized actions with estimated impact]

## Data Limitations
[Assumptions and boundaries of this analysis]
```

---

## Based On

Harvard University — *9 Skills Every Business Analytics Professional Needs*

Core principles: communicate clearly, stay curious, solve problems with logic, think critically about data quality, visualize effectively, and always connect findings to business outcomes.

---

## License

MIT
