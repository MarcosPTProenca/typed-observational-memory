# AGENTS.md

This file provides guidance for AI coding agents (such as OpenAI Codex) working inside this repository.

The goal of this project is to maintain a **clean, authentic machine learning portfolio website** for internship applications.

The portfolio belongs to a **BCA student learning machine learning and building projects**.

AI agents must follow these rules when modifying the repository.

---

## Project Overview

This repository contains a **React + Vite + Tailwind CSS portfolio website**.

The purpose of the website is to showcase:

* machine learning projects
* learning progress
* GitHub work
* technical curiosity

The portfolio must feel **authentic and honest**.

Avoid exaggerated claims or fake expertise.

---

## Design Philosophy

The UI design should follow these principles:

* minimal
* technical
* readable
* developer-focused

Avoid:

* flashy marketing style
* excessive animations
* exaggerated personal branding

The design should resemble **modern developer portfolios or AI dashboards**.

---

## UI Design System

### Colors

Background: `#0F172A`
Surface: `#111827`
Primary Accent: `#38BDF8`
Secondary Accent: `#22D3EE`

Text:

Primary text: `#E2E8F0`
Secondary text: `#94A3B8`

---

## Typography

Fonts used:

Headings → Space Grotesk
Body → Inter

Typography hierarchy:

* H1 → main page headlines
* H2 → section titles
* H3 → project titles

---

## Layout Structure

Homepage should contain sections in this order:

1. Hero
2. Projects
3. Skills
4. Learning Journey
5. GitHub Projects
6. Blog
7. About
8. Contact

Each section should contain:

* section title
* short description
* grid layout content

---

## Component Guidelines

Use reusable React components.

Recommended components:

* HeroSection
* ProjectCard
* ProjectDetails
* SkillCard
* TimelineItem
* GitHubCard
* BlogCard
* SectionHeader

Keep components modular and readable.

---

## Project Cards

Each ML project card should include:

* project title
* short description
* dataset used
* model used
* tools used
* GitHub link
* details link

Example format:

Titanic Survival Prediction
Dataset: Kaggle Titanic Dataset
Model: Logistic Regression
Tools: Python, Pandas, Scikit-Learn

---

## Project Detail Pages

Each project page should contain:

* Problem Statement
* Dataset Explanation
* EDA Insights
* Feature Engineering
* Model Used
* Evaluation Metrics
* Conclusion

---

## Animation Rules

Allowed animations:

* hover effects
* fade-in section reveal

Avoid heavy animations or distracting motion.

---

## Icons

Use icons from:

* Lucide Icons
  or
* Heroicons

Use icons for navigation, skills, and project cards.

---

## Responsive Design

Ensure mobile-first design.

Important:

* responsive grid layouts
* readable text on mobile
* large touch buttons
* proper spacing

---

## Performance Rules

Optimize performance:

* lazy loading images
* compressed images
* clean component structure

Avoid unnecessary dependencies.

---

## Code Style

Follow clean React practices:

* functional components
* clear folder structure
* reusable UI components

Avoid overly complex code.

---

## Content Rules

Content must remain authentic.

Do NOT claim:

* ML expertise
* professional experience not actually achieved
* research credentials not earned

Instead emphasize:

* learning progress
* experimentation
* projects built

---

## Optional Features

If technically feasible, AI agents may implement:

"Try the Model" interactive section

Example:

Titanic survival prediction input form.

If implementation becomes complex, skip this feature.

---

## Definition of Done

Changes are complete when:

* UI is clean and modern
* ML projects are clearly presented
* portfolio feels authentic
* mobile layout works well
* performance remains fast