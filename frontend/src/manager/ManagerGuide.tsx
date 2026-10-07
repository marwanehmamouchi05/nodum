import { useState } from 'react'
import type { ManagerPage } from './model'
import { Badge, Section } from '../components/ui'

const help: Record<ManagerPage, { question: string; answer: string }[]> = {
  Overview: [{ question: 'What needs my attention?', answer: 'Read Building status and Requires attention first. Counts use only records you may see. Partial scope and unverified devices prevent a building-wide assurance. Refresh before taking a decision.' }],
  People: [{ question: 'Why is someone missing?', answer: 'People require a visible person binding and a configured affiliation in your scope. Active means their account and dated affiliation are currently active. Ask Admin to correct assignments; Manager does not create roles here.' }],
  Visitors: [{ question: 'What does a Ring arrival mean?', answer: 'The visitor-arrival simulation sends signed motion, doorbell and person signals through Ring ingestion and normalization. Review those signals, then match a scheduled visit manually. Ring does not establish visitor identity or destination and never unlocks a door.' }, { question: 'Does creating a visit grant access?', answer: 'A product visit records the host, destination and time window. Mark arrived only after verifying the visitor, within the window. It grants no physical access. Existing business appointments and temporary permissions keep their original rules.' }],
  Access: [{ question: 'What does ALLOWED mean?', answer: 'The backend evaluated a specific person and area against current physical access rules. Read the reason and time window. This evaluation sends no door command. Configured product areas need a real access integration before they can be evaluated.' }],
  Maintenance: [{ question: 'How do I resolve an issue?', answer: 'Inspect the reporter, location, priority and history. Open Update request, choose a status and add a note. Assigned needs an active visible maintenance person in the same building. Save Resolved after verifying the issue is fixed; Closed ends follow-up. Status changes do not operate hardware.' }],
  Security: [{ question: 'Is my building safe?', answer: 'Review active incidents and device concerns. Offline is a recorded operational state; Unverified means no supported observation is available. Simulation is synthetic. Neither an empty incident list nor configuration proves physical safety. Contact Admin for configuration or hardware verification.' }],
  Activity: [{ question: 'What is recorded here?', answer: 'Activity combines authorized Ring signals, visit/maintenance/announcement changes and existing access outcomes chronologically. Hidden people and locations use scoped labels. This view is an operational journal, not a complete immutable compliance audit.' }],
  Announcements: [{ question: 'Who receives an announcement?', answer: 'Select an authorized building, floor or area and Everyone, Residents or Businesses. Empty publish time publishes now; future time schedules it. Expiry must follow publication. This phase stores notices and their audience; email, push delivery and Resident/Business reading workspaces are future work.' }],
}
export function ManagerGuide({ page }: { page: ManagerPage }) {
  const [selected, setSelected] = useState(0)
  const topic = help[page][selected] || help[page][0]
  return <Section title="Nodum Guide" action={<Badge tone="blue">Local guidance</Badge>}><p>Help for {page}. Available without Bedrock. Guidance does not check or change building state.</p><div className="manager-actions">{help[page].map((t, i) => <button key={t.question} aria-pressed={selected === i} onClick={() => setSelected(i)}>{t.question}</button>)}</div><article aria-live="polite"><h3>{topic.question}</h3><p>{topic.answer}</p></article></Section>
}
