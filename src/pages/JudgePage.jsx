import React, { useState } from 'react';

export default function JudgePage({ onNavigateTab, onNavigateIssue, onNavigateXRay }) {
  const [currentStep, setCurrentStep] = useState(1);

  const STEPS = [
    {
      num: 1,
      title: 'Prism Stream: Ingestion, Ejection & Translation',
      tab: 'stream',
      desc: 'Watch reviews flow in as white light. Bot reviews are rejected with reason codes; Hinglish phrases morph into clean English.',
      actionLabel: 'Go to Prism Stream →',
      action: () => onNavigateTab('stream'),
    },
    {
      num: 2,
      title: 'Review X-Ray: Word Highlights & Trust Cascade',
      tab: 'xray',
      desc: 'Inspect review REV-98214: Rating is 4.5 stars despite crushed packaging. Classified as MIXED polarity with G1-G6 trust gate audit.',
      actionLabel: 'Open Review X-Ray →',
      action: () => onNavigateXRay('REV-98214'),
    },
    {
      num: 3,
      title: 'Forensic Lead-Time Timeline: +15 Days Ahead',
      tab: 'timeline',
      desc: 'Timeline snaps Batch B-0716 capsule on Day 4 across Amazon, Flipkart, and Brand Direct. Public rating remains 4.4 while returns surge later at Day 19.',
      actionLabel: 'View Forensic Timeline →',
      action: () => onNavigateTab('timeline'),
    },
    {
      num: 4,
      title: 'Confidence Waterfall: Deconstructed Scoring',
      tab: 'issues',
      desc: 'Inspect Issue ISS-0716: See how Frequency, Density, Consistency, and Temporal terms stack together without black-box opacity.',
      actionLabel: 'Inspect Confidence Waterfall →',
      action: () => onNavigateIssue('ISS-0716'),
    },
    {
      num: 5,
      title: 'Closed-Loop Verification Survey: Confidence Mover',
      tab: 'investigations',
      desc: 'Automated survey asks 3 consented reviewers for confirmation. Replies arrive, and confidence visibly moves from 0.68 (Monitor) to 0.84 (Act).',
      actionLabel: 'View Survey Thread →',
      action: () => onNavigateTab('investigations'),
    },
    {
      num: 6,
      title: 'Comparison Engine: Version Impact Proof',
      tab: 'compare',
      desc: 'Version comparison lens tests v1.0 (old box) vs. v2.0 (reinforced box), proving a statistically verified 78% relative reduction in packaging complaints.',
      actionLabel: 'Run Version Comparison →',
      action: () => onNavigateTab('compare'),
    },
    {
      num: 7,
      title: 'Render Architecture & Source Health',
      tab: 'sources',
      desc: 'Examine Render Workflows durability, task retries, zero-mock policy, and live telemetry across all 6 simulated sites.',
      actionLabel: 'Inspect Source Health →',
      action: () => onNavigateTab('sources'),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-gradient-to-r from-zinc-200 to-white text-zinc-950 font-mono">
              Evaluator Fast-Track
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white tracking-wide">
            Judge Mode (90-Second Guided Path)
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            A step-by-step evaluation tour through PRISM's primary technical innovations
          </p>
        </div>

        <div className="text-xs font-mono text-zinc-200 font-semibold px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700">
          Step {currentStep} of {STEPS.length}
        </div>
      </div>

      {/* Stepper Grid */}
      <div className="space-y-4">
        {STEPS.map((step) => {
          const isActive = currentStep === step.num;
          return (
            <div
              key={step.num}
              onClick={() => setCurrentStep(step.num)}
              className={`p-5 rounded-2xl border transition-all cursor-pointer ${
                isActive
                  ? 'bg-[#22242d] border-zinc-500 shadow-xl shadow-black/30'
                  : 'bg-[#1c1d24] border-zinc-800 hover:border-zinc-700 opacity-80 hover:opacity-100'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold tracking-tight text-sm shrink-0 ${
                      isActive
                        ? 'bg-white text-zinc-950 shadow-md'
                        : 'bg-zinc-800 text-zinc-300'
                    }`}
                  >
                    {step.num}
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white mb-1">{step.title}</h2>
                    <p className="text-xs text-zinc-300 leading-relaxed max-w-2xl">{step.desc}</p>
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    step.action();
                  }}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                    isActive
                      ? 'bg-white hover:bg-zinc-200 text-zinc-950 shadow-md font-bold hover:scale-105'
                      : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700'
                  }`}
                >
                  {step.actionLabel}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
