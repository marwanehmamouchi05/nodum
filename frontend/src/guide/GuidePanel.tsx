import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Page } from '../pages/shared'
import { Badge } from '../components/ui'
import { Icon } from '../components/Icon'
import { topics, pageHelp } from './topics'
import { answerQuestion, nextSteps, pageSuggestions, topicById } from './matching'

export function GuidePanel({ initialPage, entryTopic, navigate }: {
  initialPage: Page; entryTopic?: string; navigate: (page: Page) => void
}) {
  const [page, setPage] = useState(initialPage)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(() => ({ matched: true, topic: entryTopic ? topicById(entryTopic, initialPage) : nextSteps(initialPage) }))
  function search(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setAnswer(answerQuestion(question, page))
  }
  return <section className="guide-panel" aria-labelledby="guide-title">
    <div className="section-heading"><div><h2 id="guide-title">Nodum Guide</h2><p>Built-in setup and workflow help. No AI request, network call or building action.</p></div><Badge tone="blue">Local guidance</Badge></div>
    <div className="guide-context"><label>Help for this section<select value={page} onChange={e => {
      const next = e.target.value as Page
      setPage(next); setAnswer({ matched: true, topic: nextSteps(next) })
    }}>{Object.keys(pageHelp).map(name => <option key={name} value={name}>{name}</option>)}</select></label><p>{pageHelp[page].summary}</p></div>
    <div className="guide-layout"><div className="guide-questions"><h3>Suggested questions</h3>{pageSuggestions(page).map(topic => <button key={topic.id} aria-pressed={answer.topic.id === topic.id} onClick={() => setAnswer({ matched: true, topic })}>{topic.question}<Icon name="arrow" size={15} /></button>)}<details><summary>All help topics ({topics.length})</summary>{topics.map(topic => <button key={topic.id} onClick={() => setAnswer({ matched: true, topic })}>{topic.question}</button>)}</details></div>
      <div className="guide-content"><form onSubmit={search} className="guide-search"><label htmlFor="guide-question">Find local help</label><div><input id="guide-question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="For example: Ring account not linked" maxLength={300} required /><button type="submit">Find guidance</button></div><small>Matches maintained topics. This is not an AI chat.</small></form>
        <article className="guide-answer" aria-live="polite" aria-atomic="true"><Badge>{answer.matched ? 'Built-in help' : 'Choose a help topic'}</Badge><h3>{answer.topic.question}</h3><p>{answer.topic.summary}</p><ol>{answer.topic.steps.map(step => <li key={step}>{step}</li>)}</ol><div className="guide-links">{answer.topic.links.map(link => <button key={link.page} onClick={() => navigate(link.page)}>{link.label}<Icon name="arrow" size={15} /></button>)}</div><p className="fine">Guidance only. No system state has been checked or changed by Nodum Guide.</p></article>
      </div></div>
  </section>
}
