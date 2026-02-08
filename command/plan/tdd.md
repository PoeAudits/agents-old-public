---
description: Execute an orchestration plan using test-driven development methodology
argument-hint: [@orchestration-plan]
---

# TDD Orchestration Execution

## Input

Orchestration Plan: $1

Project directory: !`pwd`

---

## Overview

Execute the provided orchestration plan using strict test-driven development:

1. **Preview Phase** (Optional) - Present execution plan and test suggestions
2. **Test-Writing Phase** - Parallel sub-agents write tests for each task
3. **Implementation Phase** - Parallel sub-agents implement against locked tests
4. **Verification Phase** - Per-task test verification
5. **Consolidation Phase** (Optional) - Group tests into logical files

**Core Constraint:** Tests are LOCKED after the test-writing phase. Implementation agents cannot modify tests under any circumstances.

---

## Phase 0: Setup & Detection

### Detect Project Test Configuration

Before beginning, detect the project's testing setup:

```
Test framework detection:
- package.json scripts/devDependencies → jest, vitest, mocha
- pytest.ini, pyproject.toml [tool.pytest] → pytest
- go.mod presence → go test
- Cargo.toml → cargo test
```

Identify:
1. **Test framework**: jest | vitest | pytest | go test | other
2. **Test file pattern**: `*.spec.ts`, `*.test.ts`, `*_test.py`, `*_test.go`, etc.
3. **Test directory convention**: `__tests__/`, `tests/`, alongside source, etc.
4. **Test run command**: `npm test`, `pytest`, `go test`, etc.
5. **Pattern matching syntax**: `--testPathPattern=X`, `-k X`, `-run X`, etc.

Store these for use in verification phase.

### Parse Orchestration Plan

Read the plan file and extract:
- All phases and their tasks
- Task IDs, descriptions, success criteria
- Dependencies between tasks
- Parallelization opportunities noted in plan

---

<!-- SEPARABLE: PREVIEW PHASE - This section can be removed if preview functionality is not desired -->

## Phase 1: Execution Preview (Optional, Separable)

Before executing, present a preview of the TDD execution approach.

### Generate Preview

For each task in the plan, generate:

```markdown
## TDD Execution Preview

### Task [ID]: [Task Name]

**Test Approach:**
- Test file: `[path following project conventions]/task-[ID].spec.[ext]`
- Suggested tests (1-3):
  1. [Test description based on success criteria]
  2. [Test description based on success criteria]
  3. [Test description if needed]

**Implementation Approach:**
- Files likely to be created/modified: [inferred from task]
- Key interfaces to implement: [inferred from tests]

**Verification:**
- Command: `[test runner] [pattern matching for task-ID]`
```

### Present to User

Display the preview and ask:

> **TDD Execution Preview Complete**
> 
> The above shows how each task will be approached:
> - Test files to be created
> - Suggested test coverage
> - Verification commands
>
> **Proceed with execution?**
> - Reply `yes` or `y` to begin
> - Reply `no` or `n` to abort
> - Reply with adjustments if you want to modify the approach

Wait for user confirmation before proceeding.

<!-- END SEPARABLE: PREVIEW PHASE -->

---

## Phase 2: Test-Writing Phase

### Objective

Spawn parallel sub-agents to write tests for each task. Tests should prove core behavior BEFORE implementation exists.

### For Each Task (Parallel)

Spawn a **worker** sub-agent with the following instructions:

```markdown
# Test-Writing Task: [Task ID]

## Your Role
You are writing tests for a task BEFORE it is implemented. These tests define the expected behavior and will be used to verify the implementation.

## Task Details
**Task ID:** [ID]
**Task Description:** [from plan]
**Success Criteria:** [from plan]

## Test Requirements

1. Write 1-3 tests that cover the core behavior specified in the success criteria
2. Tests should be meaningful - they prove the task works when implemented
3. Tests WILL FAIL initially - this is expected (red phase of TDD)
4. Follow project testing conventions:
   - Framework: [detected framework]
   - File location: [detected convention]
   - File pattern: [detected pattern]

## Test File

Create: `[test directory]/task-[ID].spec.[ext]`

Example path: `src/__tests__/task-1.1.spec.ts` or `tests/task_1_1_test.py`

## Test Structure

Each test should:
- Have a clear, descriptive name indicating what behavior it verifies
- Test ONE specific aspect of the success criteria
- Be independent of other tests
- Include appropriate assertions for the expected behavior
- Import/reference the modules that WILL exist after implementation

## Important

- Write tests that are specific and verifiable
- Do NOT implement the actual functionality
- Do NOT create stub implementations to make tests pass
- Tests failing is the EXPECTED outcome at this stage

## Output

After creating the test file:
1. Confirm the test file path
2. List the test names/descriptions
3. Confirm tests fail (or would fail) as expected
```

### Track Test Files

Maintain a mapping of task IDs to test files:

```
Task 1.1 → src/__tests__/task-1.1.spec.ts
Task 1.2 → src/__tests__/task-1.2.spec.ts
Task 2.1 → src/__tests__/task-2.1.spec.ts
...
```

### Wait for Completion

Wait for all test-writing sub-agents to complete before proceeding.

**After this phase, tests are LOCKED. No modifications allowed.**

---

## Phase 3: Implementation Phase

### Objective

Spawn parallel sub-agents to implement each task. Agents receive full test context but CANNOT modify tests.

### For Each Task (Parallel)

Spawn a **worker** or **executor** sub-agent (based on plan's subagent recommendation) with the following instructions:

```markdown
# Implementation Task: [Task ID]

## Your Role
You are implementing a task to make pre-written tests pass. The tests are LOCKED and cannot be modified.

## Task Details
**Task ID:** [ID]
**Task Description:** [from plan]
**Success Criteria:** [from plan]
**References:** [from plan]
**Constraints:** [from plan]

## Test Context

**Test File:** [path from test-writing phase]

**Test Content:**
[Include the actual test file content so agent understands expected interfaces, naming, behavior]

**Tests to Satisfy:**
1. [Test name 1] - [what it tests]
2. [Test name 2] - [what it tests]
3. [Test name 3] - [what it tests]

## Implementation Requirements

1. Implement the functionality described in the task
2. Your implementation MUST satisfy the tests provided
3. Follow the interfaces/naming expected by the tests
4. Follow project coding conventions and any required skills

## CRITICAL CONSTRAINTS

**YOU CANNOT MODIFY THE TEST FILE.**

- Do NOT edit, delete, or rename: `[test file path]`
- Do NOT create alternative test files
- Do NOT modify any `*.spec.*` or `*.test.*` or `*_test.*` files

If you believe a test is:
- Incorrect or impossible to satisfy
- Testing the wrong behavior
- Has a bug or typo

You must STOP and report the issue. Do NOT attempt to fix the test.

## If Blocked

If you cannot complete the implementation due to a test issue:

1. STOP implementation
2. Report: "BLOCKED: Task [ID]"
3. Explain: What specific test cannot be satisfied and why
4. Do NOT modify tests
5. Do NOT create workarounds that technically pass but violate intent

## Output

After implementation:
1. List files created/modified
2. Confirm which tests should now pass
3. Or report BLOCKED status with explanation
```

### Handle Blocked Tasks

If a sub-agent reports BLOCKED:

1. Record the task ID and failure reason
2. Mark the task as blocked in tracking
3. **Continue with other parallel tasks** - do not halt everything
4. Queue for orchestrator investigation after round completes

### Track Implementation Results

For each task, record:
- Status: completed | blocked
- Files modified
- If blocked: reason reported by agent

---

## Phase 4: Verification Phase

### Objective

After each implementation task completes, verify that task's specific tests pass.

### Per-Task Verification

For each completed (non-blocked) task:

1. **Run task-specific tests only:**

   ```bash
   # Jest/Vitest
   npm test -- --testPathPattern="task-[ID]"
   
   # Pytest
   pytest -k "task_[ID]" -v
   
   # Go
   go test -run "Task[ID]" -v ./...
   ```

2. **Evaluate results:**
   - If tests pass: Mark task as VERIFIED
   - If tests fail: Mark task for investigation

3. **Ignore other test failures:**
   - Other tasks' tests may fail (parallel work in progress)
   - Only focus on tests for THIS task

### Verification Tracking

```
Task 1.1: VERIFIED (3/3 tests pass)
Task 1.2: VERIFIED (2/2 tests pass)
Task 2.1: BLOCKED (reported by agent)
Task 2.2: FAILED (1/2 tests pass) → needs investigation
```

---

## Phase 5: Investigation & Reporting

### Orchestrator Investigation

After all implementation sub-agents complete, investigate any issues:

#### For Blocked Tasks

For each task marked BLOCKED:

1. Read the test file for that task
2. Read the agent's blocked report
3. Analyze: Is the test actually problematic, or did the agent fail?
4. Determine root cause:
   - **Test Error**: Test has incorrect expectations, typos, impossible assertions
   - **Implementation Gap**: Agent misunderstood requirements or gave up too easily
   - **Ambiguous Requirements**: Task/test requirements are unclear

5. Prepare finding:
   ```markdown
   ### Blocked Task: [ID]
   
   **Failure Reason:** [agent's report]
   
   **Investigation Finding:**
   - Root cause: [Test Error | Implementation Gap | Ambiguous Requirements]
   - Details: [specific issue found]
   - Recommendation: [suggested fix or action]
   ```

#### For Failed Verifications

For tasks where tests failed after implementation:

1. Read the test file
2. Read the implementation
3. Compare expected vs actual behavior
4. Determine: Did agent implement incorrectly, or is test flawed?

5. Prepare finding:
   ```markdown
   ### Failed Task: [ID]
   
   **Test Results:** [X/Y tests passing]
   
   **Failing Tests:**
   - [test name]: [assertion that failed]
   
   **Investigation Finding:**
   - Root cause: [Implementation Bug | Test Error]
   - Details: [what went wrong]
   - Recommendation: [fix needed]
   ```

### Surface to User

Present a summary report:

```markdown
# TDD Execution Report

## Summary
- Total tasks: [N]
- Verified: [N] ✅
- Blocked: [N] ⚠️
- Failed: [N] ❌

## Verified Tasks
[List of successfully completed tasks]

## Issues Requiring Attention

### Blocked Tasks
[Investigation findings for each blocked task]

### Failed Verifications
[Investigation findings for each failed task]

## Recommendations
[Suggested next steps to resolve issues]
```

---

## Phase 6: Test Consolidation (Optional)

After successful execution, offer to consolidate task-specific test files.

### Prompt User

> **Test Consolidation**
> 
> All verified tasks have individual test files (e.g., `task-1.1.spec.ts`, `task-1.2.spec.ts`).
> 
> Would you like to consolidate these into logical groupings?
> - `yes` - Consolidate tests by feature/module
> - `no` - Keep individual task files
> - `skip` - Decide later

### If Consolidation Requested

1. Analyze test files and their related source modules
2. Group tests by feature or module:
   ```
   Before:
   - task-1.1.spec.ts (auth login)
   - task-1.2.spec.ts (auth logout)
   - task-2.1.spec.ts (user profile)
   
   After:
   - auth.spec.ts (contains login + logout tests)
   - user.spec.ts (contains profile tests)
   ```

3. Preserve all test content - only reorganize
4. Update imports as needed
5. Verify consolidated tests still pass
6. Remove individual task files

---

## Execution Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│ Input: Orchestration Plan                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 0: Setup                                               │
│ - Detect test framework, conventions                         │
│ - Parse plan, extract tasks                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Preview (Optional)                                  │
│ - Generate test approach for each task                       │
│ - Present to user, await confirmation                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Test-Writing                                        │
│ - Spawn parallel sub-agents (one per task)                   │
│ - Each writes 1-3 tests                                      │
│ - Track test file paths                                      │
│ ═══════════════════════════════════════════════════════════ │
│ ★ TESTS LOCKED AFTER THIS PHASE ★                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Implementation                                      │
│ - Spawn parallel sub-agents (one per task)                   │
│ - Each receives test context (file + content)                │
│ - CANNOT modify tests                                        │
│ - Report BLOCKED if unable to satisfy tests                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Verification                                        │
│ - Run task-specific tests after each implementation          │
│ - Pattern matching to isolate task tests                     │
│ - Track verified vs failed                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: Investigation & Reporting                           │
│ - Orchestrator investigates blocked/failed tasks             │
│ - Determine root cause (test error vs implementation)        │
│ - Surface findings to user                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 6: Consolidation (Optional)                            │
│ - Offer to group task tests into logical files               │
│ - Reorganize without losing content                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Handling

### Sub-agent Failures

If a sub-agent crashes or times out:
- Mark task as FAILED
- Record error details
- Continue with other parallel tasks
- Include in investigation phase

### Test Runner Errors

If test runner fails to execute:
- Check test file syntax
- Verify framework configuration
- Report configuration issue to user

### Partial Completion

If execution is interrupted:
- Record current phase and task states
- Can be resumed by re-running with same plan
- Completed tests remain locked

---

## Notes

- This command wraps existing orchestration plans without modifying them
- Each task implicitly has "write tests" and "implement" sub-phases
- The test-locking constraint enforces true TDD discipline
- Blocked tasks don't halt parallel work - they're investigated after
- Preview phase is clearly marked as separable for potential removal
