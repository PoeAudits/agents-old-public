---
description: Find bloat, dead code, and redundancy then produce a cleanup plan
---

## Project Context

Project: !`basename "$(git rev-parse --show-toplevel 2>/dev/null)"`
Root: !`git rev-parse --show-toplevel 2>/dev/null`
Languages: !`find . -maxdepth 4 -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.go' -o -name '*.rs' -o -name '*.sol' \) 2>/dev/null | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -5`
Dependency files: !`ls -1 package.json requirements.txt pyproject.toml Cargo.toml go.mod go.sum 2>/dev/null`
Top-level structure: !`ls -1`
Git status: !`git status --short | head -20`
Lines of code estimate: !`find . -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.go' -o -name '*.rs' -o -name '*.sol' \) -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/__pycache__/*' -not -path '*/vendor/*' 2>/dev/null | wc -l` source files

## Phase 0: Propose Scope and Get User Input

Based on the project context above, propose a review scope:
- Which directories contain the core source code
- Which directories to skip (generated, vendored, build output)
- Estimated scale of the review

Present the proposed scope to the user, then use the question tool to gather preferences:

**Question - Review focus:**
- header: "Focus areas"
- question: "Which areas should this review focus on?"
- multiple: true
- options:
  - Dead code (Unused functions, imports, variables, unreachable paths)
  - Redundancy (Duplicate logic, copy-paste code, unifiable patterns)
  - Complexity (Verbose functions, deep nesting, overengineering)
  - Dependency bloat (Heavy/unused deps, stdlib replacements)
  - Config/test bloat (Stale config, duplicate test setup, dead tests)

## Phase 0.5: Present Plan and Confirm

After the user selects focus areas, calculate the agent dispatch plan and present it clearly:

**Agent scaling rules:**
- 1 topic selected → 3 agents (deep dive)
- 2 topics selected → 2 agents per topic (4 total)
- 3+ topics selected → 1 agent per topic

**Present the plan like this:**

> Based on your selection of [N topic(s)], I'll dispatch **[X] seeker agents**:
>
> **[Topic 1]:**
> - Agent A: [specific focus]
> - Agent B: [specific focus]
> - (Agent C if applicable)
>
> **[Topic 2]:** (if selected)
> - Agent A: [specific focus]
> - ...
>
> Estimated time: [quick/moderate/thorough based on agent count]

**Then ask for confirmation using the question tool:**
- header: "Dispatch plan"
- question: "Proceed with this plan, or adjust?"
- options:
  - Proceed
  - Fewer agents (faster, less thorough)
  - More agents (slower, more thorough)
  - Change topics

If the user selects an adjustment option, re-calculate and present the updated plan. Loop until they confirm "Proceed".

## Phase 1: Dispatch Seeker Agents

Execute the dispatch plan confirmed in Phase 0.5. Use the `task` tool with `subagent_type: seeker` to dispatch all agents in parallel.

**Reference: Agent scaling (already presented to user)**
- 1 topic → 3 agents (A, B, C)
- 2 topics → 2 agents each (A, B)
- 3+ topics → 1 agent each (A only)

**Global seeker directives** (include in every seeker prompt):
- Respect `.gitignore` -- skip `node_modules`, `dist`, `build`, `__pycache__`, `.git`, `vendor`, and any other generated/vendored directories
- Scope to the directories agreed on in Phase 0
- Use the project context (languages, dependency files) to target searches
- Return: file path with line numbers/ranges, brief description, and estimated lines affected

---

### Topic: Dead/Unused Code

**Sub-agent A - Structural dead code:**
Find functions, methods, or classes that are never called anywhere in the codebase. Look for exported symbols never imported by other modules. Check for entire files that are never imported.

**Sub-agent B - Declaration-level dead code:**
Find variables declared but never read. Find unused imports (imported but never referenced). Find unused function parameters. Find unused class properties or instance variables.

**Sub-agent C - Unreachable and commented code:**
Find unreachable code paths (after return/throw, impossible conditions). Find large commented-out code blocks (not explanatory comments). Find dead branches in conditionals that can never execute.

---

### Topic: Redundant Implementations

**Sub-agent A - Intra-file duplication:**
Find duplicate logic within the same file. Look for copy-pasted code blocks, repeated patterns in adjacent functions, and logic that could be extracted into a helper.

**Sub-agent B - Cross-file duplication:**
Find duplicate logic across different files/modules. Look for utility functions reimplemented in multiple places, identical validation logic, and repeated error handling patterns.

**Sub-agent C - Unifiable patterns:**
Find near-identical implementations that differ only slightly. Look for functions doing the same thing with minor variations that could be unified with parameters, or repeated patterns that suggest a missing abstraction.

---

### Topic: Verbose/Overcomplicated Code

**Sub-agent A - Nesting and conditionals:**
Find functions with deep nesting (4+ levels). Find complex boolean expressions that are hard to read. Find excessive if/else chains that could be simplified. Find nested ternaries.

**Sub-agent B - Size and parameters:**
Find functions exceeding 50 lines. Find functions with 5+ parameters. Find classes with too many methods or too many responsibilities (god objects). Find files that are excessively long.

**Sub-agent C - Overengineering:**
Find premature abstractions (interfaces with single implementations, factories that create one thing). Find long method chains. Find overly generic code solving problems that don't exist. Find unnecessary indirection layers.

---

### Topic: Import/Dependency Bloat

**Sub-agent A - Heavy dependencies for trivial use:**
Analyze dependencies and find heavy packages used for trivial tasks (e.g., lodash for a single function). Quantify: what functions are actually used from each dependency?

**Sub-agent B - Redundant dependencies:**
Find multiple libraries doing the same thing (e.g., moment + dayjs, axios + fetch wrapper). Find dependencies that overlap significantly in functionality.

**Sub-agent C - Unused and replaceable:**
Find dependencies that are imported but barely used (< 3 call sites). Find dependencies easily replaceable with stdlib or built-in language features. Check if dev dependencies are mistakenly in production.

---

### Topic: Configuration/Test Bloat

**Sub-agent A - Stale configuration:**
Find configuration files with unused or outdated settings. Find environment variables defined but never read. Find build/CI config for features that no longer exist.

**Sub-agent B - Test setup duplication:**
Find duplicate test setup/teardown across test files. Find repeated mock definitions. Find test utilities reimplemented instead of shared. Find excessive beforeEach/afterEach boilerplate.

**Sub-agent C - Weak tests:**
Find tests that don't assert anything meaningful. Find tests with only existence checks but no behavior verification. Find tests that are commented out or skipped indefinitely. Find tests that always pass regardless of implementation.

## Phase 2: Compile Findings

After all seeker agents return:

1. Consolidate findings into a single report grouped by category
2. For each issue, document:
   - Exact file path and line numbers
   - Brief description
   - **Impact score** (1-10): Weight by lines of code affected, how central the code is (imported by many vs leaf), and whether it's in a hot path
   - **Frequency**: How many times the pattern repeats across the codebase
   - **Fix effort** estimate: lines to change, files touched, risk of regression
3. Sort issues by impact score descending within each category
4. Produce a summary table: total issues found, total estimated lines of dead/redundant code, breakdown by category

## Phase 3: Create Improvement Plan

Craft a cleanup plan based on the compiled findings:

1. Rank all issues by `impact / effort` ratio (highest value fixes first)
2. Group related fixes into batches (e.g., "remove all unused imports" is one batch)
3. For each batch:
   - Files affected
   - Approach (without writing code)
   - Risk assessment and what to test after
   - Expected lines removed or simplified
4. Organize batches into phases: quick wins first, then medium effort, then deep refactors


Present a summary to the user with the report file path and highest-impact findings.
