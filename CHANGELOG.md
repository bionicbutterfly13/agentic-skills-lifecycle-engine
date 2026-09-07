# Changelog

## 0.2.0

- Renamed the project from Askesis to Agent Skill Mastery Engine. The PyPI
  distribution name changed from `askesis-agent-skill-mastery-engine` to
  `agent-skill-mastery-engine`, the import package and CLI executable from `askesis` to
  `asme`, the default Claude Code skill directory from `~/.claude/skills/askesis` to
  `~/.claude/skills/asme`, and every `askesis.*` schema or identifier string to `asme.*`.
  Existing `askesis` imports, commands, and on-disk records that carry `askesis.*`
  schema strings are not read by this version.

## 0.1.2

- Evolution eval, paired bootstrap, eval-run and verify-packet CLI, date frontmatter
  alias. Released under the former name Askesis.
