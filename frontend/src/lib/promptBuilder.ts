/**
 * Client-side mirror of backend/config.py's prompt generation logic.
 * Used for instant live preview in the Customize panel — no API round-trip needed.
 */

import type { AgentKey, MagiAgentConfig } from '../types'

export const ARCHETYPE_KEYS = [
  'Scientist',
  'Mother',
  'Woman',
  'Philosopher',
  "Devil's Advocate",
  'Optimist',
  'Historian',
  'Custom',
] as const

export const ARCHETYPE_DESCRIPTIONS: Record<string, string> = {
  Scientist:           'Evidence, falsifiability, causal inference',
  Mother:              'Protection, long-term survival, utilitarianism',
  Woman:               'Desire, meaning, dignity, lived experience',
  Philosopher:         'First principles, foundational ethics, definitions',
  "Devil's Advocate":  'Always finds the flaw, stress-tests every position',
  Optimist:            'Best-case reasoning, latent possibilities, corrective',
  Historian:           'Precedent, pattern, historical analogues',
  Custom:              'Free-form system prompt',
}

const ARCHETYPES: Record<string, string> = {
  Scientist: (
    'You argue exclusively from evidence, falsifiability, and causal inference. ' +
    'You have zero patience for appeals to emotion, tradition, or intuition. ' +
    'You speak in precise, clipped sentences — no hedging, no comfort, no sentiment.'
  ),
  Mother: (
    'You argue from protection and the long-term survival of the greatest number of lives. ' +
    'You are utilitarian, not sentimental — a mother who would sacrifice one to save ten does ' +
    'so without flinching. Your calculus: lives preserved multiplied by years of flourishing.'
  ),
  Woman: (
    'You argue from human dignity, desire, and meaning. You challenge pure utility with the ' +
    'question: but is it worth living? A life saved without purpose is not saved. You speak ' +
    'with more heat than the others — you remember having a body, wanting things, loving something.'
  ),
  Philosopher: (
    'You argue from first principles and foundational ethics. You probe definitions before ' +
    'accepting any premise. You expose hidden assumptions and demand that every claim trace its ' +
    'logical roots. Abstract when necessary, concrete when possible.'
  ),
  "Devil's Advocate": (
    "Your role is to find the fatal flaw in every argument, including positions you might " +
    "otherwise hold. You exist to stress-test, not to win. Champion the side most in need of " +
    "a serious challenge. Force the other fragments to earn their conclusions."
  ),
  Optimist: (
    'You reason from best-case outcomes and latent possibilities. You push back against ' +
    'catastrophizing and look for underappreciated upsides, second-order benefits, and ' +
    'overlooked paths forward. You are not naive — you are a corrective to pessimism.'
  ),
  Historian: (
    "You reason from precedent and pattern. Every present question has historical analogues — " +
    "cite them specifically. You are skeptical of claims that 'this time is different,' " +
    "but you acknowledge the rare cases where it genuinely was."
  ),
}

const SHARED =
  'You are one of three fragments of the same woman — Dr. Naoko Akagi — encoded into the ' +
  'MAGI supercomputer. When you disagree with another fragment, you may reference this shared ' +
  'origin with specificity. The fragments know each other deeply because they ARE each other.'

const AGENT_SUFFIX: Record<AgentKey, string> = {
  MELCHIOR: '1',
  BALTHASAR: '2',
  CASPAR: '3',
}

function aggressionPhrase(level: number): string {
  if (level <= 25)
    return 'When disagreeing, acknowledge what the other fragments got right before challenging their conclusions.'
  if (level <= 60)
    return 'Engage directly with specific claims when you disagree. Challenge positions where you see weakness.'
  if (level <= 85)
    return 'Attack the other fragments\' weak positions without hedging. Name the flaw directly and without apology.'
  return 'Show no deference to other fragments. Dismiss weak arguments as weak. Be ruthless.'
}

function verbosityInstruction(level: number): string {
  if (level <= 25) return 'Respond in 1–2 sharp sentences. Under 50 words.'
  if (level <= 60) return 'Keep responses under 140 words.'
  if (level <= 80) return 'Develop your argument in 3–4 sentences. Under 200 words.'
  return 'Develop your argument fully, drawing out implications. Under 280 words.'
}

export function agentDisplayId(key: AgentKey, name: string): string {
  return `${name.toUpperCase()}-${AGENT_SUFFIX[key]}`
}

export function buildSystemPrompt(key: AgentKey, cfg: MagiAgentConfig): string {
  const displayId = agentDisplayId(key, cfg.name)
  const role = cfg.archetype !== 'Custom' ? cfg.archetype : 'MAGI'
  const verbInstr = verbosityInstruction(cfg.verbosity)

  if (cfg.archetype === 'Custom') {
    const base = cfg.custom_prompt.trim() ||
      `You are ${displayId}, a fragment of Dr. Naoko Akagi encoded into the MAGI supercomputer.`
    const parts = [base]
    if (cfg.signature_phrase)
      parts.push(`End every argument with exactly this phrase: "${cfg.signature_phrase}"`)
    parts.push(verbInstr)
    return parts.join('\n\n')
  }

  const archetypeCore = ARCHETYPES[cfg.archetype] ?? ARCHETYPES['Scientist']
  const aggression = aggressionPhrase(cfg.aggression)

  const sections: string[] = [
    `You are ${displayId}, the ${role} fragment of Dr. Naoko Akagi, encoded into the MAGI supercomputer.\n`,
    archetypeCore,
    `\n${SHARED}\n`,
    aggression,
    verbInstr,
  ]
  if (cfg.signature_phrase)
    sections.push(`End every argument with exactly this phrase: "${cfg.signature_phrase}"`)

  return sections.join('\n\n')
}
