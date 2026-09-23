# The question my engine refused to score

*A system for improving AI agent skills ran a real model for the first time this week. The most useful thing it did was decline to count an answer that never came.*

At 26 minutes and 38 seconds, the model gave up without answering.

The question came from LiveMathematicianBench, a set of multiple-choice problems drawn from recent research papers. The model was `qwen3.5:4b`, running on my MacBook Pro at about a token and a half per second. It had been told to think, then put a single letter inside answer tags. It thought for 3,072 tokens, hit the ceiling on how much it was allowed to write, and stopped mid-reasoning with no letter at all.

What happened next is the reason I'm writing this. The engine I've been building looked at that output and refused to do anything with it. The adapter recorded the run as truncated. The extractor found no answer and failed. The manifest that would have carried a score came back invalid, and the state machine stayed exactly where it was. Nothing moved, and no number appeared.

That can sound like a non-event. It is actually the whole point of the project.

## What the engine is for

Lifecycle, the Agentic Skills Lifecycle Engine, is an open-source attempt to answer one question honestly: when you change an AI agent's instructions, did the change help? Its core rule is blunt. No skill counts as improved unless a reproducible, controlled evaluation shows that it helps without breaking correctness or safety.

The method comes from a Google Research paper published last month, WikiSkill (Tang et al., arXiv 2608.27454). An agent attempts tasks. One model reads its failures and keeps a persistent wiki of patterns. Another reads that wiki and proposes a single change to a skill file. The change is kept only if the score on held-out validation tasks strictly beats the best score so far. If it doesn't, the skill rolls back but the wiki stays, so the next attempt starts smarter.

When I audited my implementation against the paper yesterday, I found something uncomfortable. The code matched the paper's loop closely: the sampling limits, the output formats, the strict gate, the rollback. But it had never run a model. Every result in the repository came from recorded fixtures, and one evaluation path used a scripted responder that answered correctly whenever the skill's name appeared in the prompt. The machinery was faithful and had never once turned over.

## A zero is evidence. A non-answer is not.

So this week was about making it turn over. The first live run used deliberately easy questions, and the model got them right. The baseline scored 1.0, and the engine stopped immediately, because the paper says to stop when validation is already perfect. That was the first time I saw the paper's logic act on real output instead of a fixture.

Then came the hard question and the 26-minute silence.

Most evaluation pipelines I've seen would score that run as wrong. It's the path of least resistance: no answer, no match, zero. But a zero is a claim. It says the model tried and got it wrong. That isn't what happened. The model never answered, and the difference matters when you are deciding whether a skill helped. If a skill makes the model reason longer, and longer reasoning runs out of room, a pipeline that scores silence as failure will tell you the skill made things worse when it may have made the model more careful. Scoring the silence would have manufactured evidence.

The engine didn't do that. It said, in effect, *I don't know what happened here, so I won't pretend I do.* That refusal was designed in well before this week, and this was the first time I watched it hold under real conditions.

The fix for the trial itself was one sentence added to the prompt: if you are running long, commit to your best current choice rather than run out of room. That sentence is not in the paper, so any run I label paper-comparable has to use the original wording and accept whatever truncation rate comes with it. I keep a running list of every place my implementation departs from the paper, because the day I stop tracking those is the day my comparisons stop meaning anything.

## The mistakes were mine too

The model wasn't the only thing that failed this week. I build Lifecycle with AI coding agents doing much of the implementation, and some of the failures were ours. I think they belong in the same account.

I pushed an adapter that broke one of my own architecture rules: adapters may import only the core contract module, so that no adapter can quietly fork the engine's behavior. I had run the tests next to the change, and they passed. I hadn't run the whole suite. The next automated task started by checking the baseline, found main broken, and stopped before touching anything. It was right to stop, and I'm glad it did.

Later I marked a requirement as done, that the paper's prompts ship with the package, while the files sat in a folder the package deliberately excludes. A planning agent caught it by reading the distribution tests instead of my checkbox.

And a green test run once proved nothing at all. My project configuration already told pytest to be quiet, I told it again, and the doubled flag hid the summary line. I had also piped the output through `tail`, so the exit code I recorded belonged to `tail`, not to the tests.

None of these were dramatic. Each one is the same failure as the truncated question in smaller form: something reported success, or reported a result, that the evidence didn't support. The engine is built to refuse that at the level of skills. I'm learning to refuse it at the level of my own work.

## Where it stands

The slow laptop turned out to be the least interesting obstacle. On a Colab T4, `qwen3.5:9b` generates about 25 tokens per second and reads prompts at about 200, roughly sixteen times faster than my machine. Getting there took one more fix: Colab doesn't ship `zstd`, which the current Ollama installer now needs, and the install script fails in two seconds with no visible error unless you go looking for it.

Every model role in the paper now calls a live model: the agent answering questions, the wiki maintainer, and the skill proposer reading files and traces turn by turn. Each piece has been checked on its own. The full loop on real data hasn't run yet, and I'm not going to describe results I don't have.

Every obstacle from this week, with the evidence and the commit that fixed it, is in the project's engineering journal on GitHub. The first real study runs next.

*The engine is open source at github.com/bionicbutterfly13/agentic-skills-lifecycle-engine.*
