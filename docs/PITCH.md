# Vibe Weave pitch

## 30-second version

Mistral Vibe can run multiple coding agents in parallel. But parallel agents can make different assumptions about the same feature—and that is how a pull request can look correct while behaving inconsistently.

Vibe Weave fixes that coordination gap. Before agents edit code, each one writes a tiny Change Contract: what it plans to change, what it assumes, and how it will prove success. Weave compares those contracts, finds conflicts, asks one focused question, and records one shared Decision Contract.

Vibe remains the execution engine. **Vibe Weave is the semantic coordination layer that helps its agents work like one team.**

## 90-second judge version

Vibe can delegate complex coding work to multiple agents. The challenge is not only whether each agent can write code. It is whether all agents mean the same thing when they write it.

Imagine three agents adding invoice export. The frontend agent assumes any signed-in user can export. The backend agent assumes only admins can export. The test agent expects non-admins to receive a 403. Each agent is individually reasonable, but together they produce an incoherent feature.

Vibe Weave catches that disagreement before managed edits begin. Each role proposes a small Change Contract: its file scope, assumptions, public interface, and proof. Weave compares those contracts and identifies the highest-impact conflict. Here it asks one clear question: **Who may export invoices?**

The answer becomes a Decision Contract shared by every affected role. Only then do agents proceed in isolated Git worktrees and return proofs that they implemented the same behavior.

This changes the output from “three plausible patches” into **code plus the decision and evidence that made the code coherent**.

Vibe keeps orchestration, delegation, and tool execution. Vibe Weave adds a lightweight semantic checkpoint before parallel work diverges. It uses project-local agents, skills, hooks, and worktrees rather than replacing Vibe’s runtime.

## One-line close

**Vibe runs the agents. Vibe Weave makes them agree.**

## Demo bridge

“Let me show the conflict first. Then I will choose the shared authorization rule, generate the Decision Contract, and prove that all three roles converge on it.”
