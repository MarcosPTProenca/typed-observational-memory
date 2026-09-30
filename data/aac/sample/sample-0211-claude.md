# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LaTeX-based academic syllabus for POLS 531: Causal Inference for Political Science at UIUC. Single-file design (`syllabus.tex`) with automatic date calculation for semester reuse.

## Build Commands

```bash
make            # Compile syllabus.pdf (runs pdflatex twice)
make view       # Compile and open PDF
make clean      # Remove build artifacts and PDF
```

Requires pdflatex (TeX Live/MacTeX/MiKTeX).

## Key Customization Points in syllabus.tex

- **First class date** (line 56): `\newcommand{\firstclassdate}{20/01/2026}` — DD/MM/YYYY format. All weekly dates auto-calculate from this.
- **Color scheme** (lines 23-25): Illinois Navy Blue `{19, 41, 75}` and Orange `{232, 74, 39}`
- **Instructor info** (lines 102-111): Course information table
- **Course schedule**: Uses `\weekheading{title}` macro for each week

## Week Heading System

The `\weekheading{title}` macro creates subsection headings with auto-numbered weeks:
- Week numbers and dates auto-increment together
- Example: `\weekheading{Introduction}` produces "Week 1: 20 January 2026 -- Introduction"

**To reorder topics**: Just move the entire `\weekheading` block; week numbers adjust automatically.

**To handle breaks**: Simply add a week for the break:
```latex
\weekheading{No Class --- Spring Break}
```
This will show the correct week number and date for the break week.