(() => {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const panels = [...document.querySelectorAll('[role="tabpanel"]')];
  const stages = ['contracts', 'conflict', 'decision', 'worktrees', 'verified'];
  let decision = 'admin_only';

  const selectTab = (target, focus = false) => {
    if (!document.getElementById(`panel-${target}`)) return;
    tabs.forEach((tab) => tab.setAttribute('aria-selected', String(tab.dataset.tab === target)));
    panels.forEach((panel) => { panel.hidden = panel.id !== `panel-${target}`; });
    history.replaceState(null, '', `#${target}`);
    window.scrollTo({top: 0, behavior: 'smooth'});
    if (focus) document.getElementById(`tab-${target}`).focus();
  };
  tabs.forEach((tab) => tab.addEventListener('click', () => selectTab(tab.dataset.tab, true)));
  document.querySelectorAll('[data-open-tab]').forEach((button) => button.addEventListener('click', () => selectTab(button.dataset.openTab, true)));
  window.addEventListener('hashchange', () => selectTab(location.hash.slice(1) || 'overview'));
  selectTab(location.hash.slice(1) || 'overview');

  const detailByStage = {
    contracts: 'Three roles declare their intended change, contract, and proof.',
    conflict: 'Two incompatible authorization meanings were found.',
    decision: 'A Decision Contract records one answer for every affected role.',
    worktrees: 'Each role receives an isolated Git worktree after convergence.',
    verified: 'The shared policy and required proofs are checked together.',
  };
  const markStage = (stage, outcome = 'running') => {
    const index = stages.indexOf(stage);
    stages.forEach((name, position) => {
      const item = document.querySelector(`[data-weave-stage="${name}"]`);
      const diagram = document.querySelector(`[data-diagram-step="${name}"]`);
      const className = position < index || (position === index && outcome === 'success') ? 'complete' : position === index ? outcome === 'failure' ? 'failed' : 'active' : '';
      if (item) item.className = className;
      if (diagram) diagram.className = `diagram-step ${className}`;
      const detail = item?.querySelector('small');
      if (detail && position === index) detail.textContent = detailByStage[name];
    });
  };
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const status = document.getElementById('weave-status');
  const runButton = document.getElementById('run-weave-proof');
  const evidence = document.getElementById('weave-evidence');

  document.querySelectorAll('[data-decision]').forEach((button) => button.addEventListener('click', () => {
    decision = button.dataset.decision;
    document.querySelectorAll('[data-decision]').forEach((candidate) => candidate.classList.toggle('selected', candidate === button));
    status.textContent = `Selected ${decision}. Resolve & prove will test this policy against every declared proof.`;
  }));
  runButton.addEventListener('click', async () => {
    runButton.disabled = true;
    evidence.hidden = true;
    status.textContent = 'Step 3 of 5: recording the shared Decision Contract…';
    markStage('decision'); await sleep(500);
    status.textContent = 'Step 4 of 5: creating three disposable, isolated Git worktrees…';
    markStage('worktrees'); await sleep(500);
    try {
      const response = await fetch(`/api/v1/weave/drill?decision=${encodeURIComponent(decision)}`, {method: 'POST'});
      if (!response.ok) throw new Error(`Proof service returned ${response.status}`);
      const report = await response.json();
      document.getElementById('decision-contract').textContent = JSON.stringify(report.decision, null, 2);
      document.getElementById('verification-result').innerHTML = Object.entries(report.verification)
        .map(([name, passed]) => `<li class="${passed ? 'pass' : 'fail'}"><b>${passed ? 'PASS' : 'FAIL'}</b> ${name.replaceAll('_', ' ')}</li>`).join('');
      evidence.hidden = false;
      if (report.verification.passed) {
        status.textContent = `Step 5 of 5: verified. ${decision} aligns every role and all required proofs pass.`;
        markStage('verified', 'success');
      } else {
        status.textContent = `Proof deliberately failed: ${decision} does not satisfy the authorization policy. Choose “Admins only” to complete the safe route.`;
        markStage('verified', 'failure');
      }
    } catch (error) {
      status.textContent = `Proof service unavailable (${error.message}). The contract remains unresolved; no managed edit is released.`;
      markStage('conflict', 'failure');
    } finally { runButton.disabled = false; }
  });
  document.getElementById('play-walkthrough').addEventListener('click', async () => {
    const items = [...document.querySelectorAll('#walkthrough-steps li')];
    for (const item of items) { items.forEach((candidate) => candidate.classList.remove('playing')); item.classList.add('playing'); await sleep(850); }
    items.forEach((item) => item.classList.remove('playing'));
  });
})();
