# A zero is a claim. My AI evaluation engine refused to make one.

This week a model spent 26 minutes on a math question and never answered. The system I'm building refused to score it, and that refusal is the most useful result I've had so far.

Some context. I'm building Lifecycle, an open-source engine that tests whether a change to an AI agent's instructions actually helps. It implements WikiSkill, a method Google Research published in August (arXiv 2608.27454): the agent attempts tasks, one model studies the failures and keeps a wiki of patterns, another proposes a single change to a skill, and the change survives only if it strictly beats the best validation score so far.

On Tuesday I audited my code against the paper. The structure matched closely. But it had never run a real model. Every result in the repository came from recorded fixtures.

So I connected it to one.

**The first run** used easy questions. The model scored 1.0, and the engine stopped at once, because the paper says to stop when validation is already perfect.

**The second run** used a research-level question from LiveMathematicianBench. The model, running on my laptop at about 1.5 tokens per second, reasoned for 3,072 tokens, hit its output limit, and stopped without choosing an answer.

Most pipelines would score that as wrong. No answer, no match, zero.

But a zero says the model tried and failed. That isn't what happened. If a new skill makes a model reason more carefully, and careful reasoning runs out of room, counting the silence as failure tells you the skill hurt when you don't actually know that.

The engine marked the run as truncated, found no answer to extract, declared the result invalid, and refused to advance. No number was produced, because no honest number existed.

Three things I'm taking from the week:

**1. Measure before you plan.** I estimated my laptop's speed from memory and was off by a factor that changed the plan. On a Colab T4 GPU, a 9-billion-parameter model ran about sixteen times faster than the smaller model on my machine. One timed request settled it.

**2. Track every deviation from the method you claim to follow.** I added one sentence to the prompt telling the model to commit to an answer before running out of room. It's not in the paper, so it's logged, and any run I call paper-comparable uses the original wording.

**3. The same rule applies to my own work.** An adapter I shipped broke an architecture rule because I ran only the nearby tests, not the whole suite. I marked a requirement done before checking the shipped artifact. A green test run once proved nothing because the exit code I recorded belonged to the wrong command. Each time, something reported success that the evidence didn't support.

That's the failure the engine exists to catch, at every level.

The full loop hasn't run on real data yet, and I won't describe results I don't have. Every obstacle, with the evidence and the fix, is in the project's public engineering journal.

If you evaluate AI systems: how does your pipeline score a response that never finished?

github.com/bionicbutterfly13/agentic-skills-lifecycle-engine
