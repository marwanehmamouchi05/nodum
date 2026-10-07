import type { Page } from '../pages/shared'
import { topics, pageHelp } from './topics.ts'
import type { GuideTopic } from './topics.ts'

function normalize(question: string) {
  return question.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

export function nextSteps(page: Page): GuideTopic {
  return { id: 'next', question: `What should I do next on ${page}?`,
    summary: pageHelp[page].summary, steps: pageHelp[page].next,
    links: [{ page, label: `Open ${page}` }], aliases: [], matchGroups: [] }
}

export function topicById(id: string, page: Page): GuideTopic {
  return topics.find(topic => topic.id === id) || nextSteps(page)
}

export function pageSuggestions(page: Page): readonly GuideTopic[] {
  return [nextSteps(page), ...pageHelp[page].suggestions.map(id => topicById(id, page))]
}

export function answerQuestion(question: string, page: Page): { matched: boolean; topic: GuideTopic } {
  const text = normalize(question)
  const contains = (phrase: string) => (` ${text} `).includes(` ${normalize(phrase)} `)
  if (['next', 'current page', 'this page', 'what now'].some(contains)) {
    return { matched: true, topic: nextSteps(page) }
  }
  const exact = topics.find(topic => [topic.question, ...topic.aliases].some(alias => normalize(alias) === text))
  if (exact) return { matched: true, topic: exact }

  let best: GuideTopic | undefined
  let score = 0
  for (const topic of topics) {
    for (const group of topic.matchGroups) {
      if (group.length > score && group.every(contains)) { best = topic; score = group.length }
    }
  }
  if (best) return { matched: true, topic: best }
  return { matched: false, topic: { id: 'unknown', question: 'No matching help topic',
    summary: 'Nodum Guide has maintained help for setup and building workflows. It does not infer live state, run commands or answer every question.',
    steps: ['Choose a suggested question or browse all help topics.', 'For operational work, open the relevant section and use its existing controls. Guide has not submitted or changed anything.'],
    links: [{ page: 'Overview', label: 'Open Overview' }], aliases: [], matchGroups: [] } }
}
