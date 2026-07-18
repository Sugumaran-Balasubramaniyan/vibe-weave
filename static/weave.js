(() => {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const panels = [...document.querySelectorAll('[role="tabpanel"]')];
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

  const stages = ['contracts', 'conflict', 'decision', 'worktrees', 'verified'];
  const markStage = (stage, complete = false) => {
    const index = stages.indexOf(stage);
    stages.forEach((name, position) => {
      const item = document.querySelector(`[data-weave-stage="${name}"]`);
      if (item) item.className = position < index || (complete && position === index) ? 'complete' : position === index ? 'active' : '';
    });
  };
  document.querySelectorAll('[data-decision]').forEach((button) => button.addEventListener('click', () => {
    decision = button.dataset.decision;
    document.querySelectorAll('[data-decision]').forEach((candidate) => candidate.classList.toggle('selected', candidate === button));
  }));
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  document.getElementById('run-weave-proof').addEventListener('click', async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    document.getElementById('weave-status').textContent = 'Writing a Decision Contract and preparing isolated worktrees…';
    markStage('decision'); await sleep(350); markStage('worktrees');
    try {
      const response = await fetch(`/api/v1/weave/drill?decision=${encodeURIComponent(decision)}`, {method: 'POST'});
      if (!response.ok) throw new Error('Proof service unavailable');
      const report = await response.json();
      document.getElementById('decision-contract').textContent = JSON.stringify(report.decision, null, 2);
      const verification = document.getElementById('verification-result');
      verification.innerHTML = Object.entries(report.verification).map(([name, passed]) => `<li>${passed ? '✓' : '×'} ${name.replaceAll('_', ' ')}</li>`).join('');
      document.getElementById('weave-evidence').hidden = false;
      document.getElementById('weave-status').textContent = `Resolved as ${decision}. All roles now share one authorization contract.`;
      markStage('verified', true);
    } catch (error) {
      document.getElementById('weave-status').textContent = 'The visual flow is ready, but the proof service is unavailable. Run the terminal drill to verify.';
      markStage('conflict');
    } finally { button.disabled = false; }
  });
  document.getElementById('play-walkthrough').addEventListener('click', async () => {
    const items = [...document.querySelectorAll('#walkthrough-steps li')];
    for (const item of items) { items.forEach((candidate) => candidate.classList.remove('playing')); item.classList.add('playing'); await sleep(850); }
    items.forEach((item) => item.classList.remove('playing'));
  });
})();
