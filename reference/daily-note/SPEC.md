# Reference report: daily-note

| | |
|---|---|
| **Owner** | Rory Sullivan (project owner) |
| **Status** | **Stand-in.** Built by `examples/daily-investment-note`. Replace with the owner's real daily note before Gate 1. |
| **Medium** | Email (`Email`), read on a phone first |
| **Audience** | Portfolio clients and the desk, before the open |
| **Cadence** | Daily, each trading day |

## Sections

1. **The Day in Brief**: the day in two sentences of market and two of portfolio.
2. **Performance**: the portfolio's cumulative return against its benchmark over twenty sessions, a chart with its key in HTML.
3. **What Drove Returns**: the five largest contributors and three largest detractors, the rest grouped, and the portfolio as a total row.
4. **By Sector**: contribution by sector as a diverging bar chart.
5. **Positioning and the Day Ahead**: what the desk is doing and watching.

## Data inputs

- Daily returns for the portfolio and its benchmark, twenty sessions.
- Each holding's weight and return for the day, giving its contribution in basis points.
- Contribution by sector.

The stand-in's figures are fictional and live in its source. It needs the `[charts]` extra to draw its two charts.

## What it holds the roadmap to

The email medium, the 102 KB check, a phone viewport, charts from data, and a table whose figures arrive as numbers.
