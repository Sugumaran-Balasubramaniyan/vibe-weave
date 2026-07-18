/**
 * GlassBox Sentinel - Frontend Application
 */

class GlassBoxApp {
    constructor() {
        this.runId = null;
        this.currentRun = null;
        this.eventSource = null;
        this.pollInterval = null;
        this.selectedChoiceId = null;
        this.selectedChoiceAccepted = false;
        this.authorizationPending = false;
        this.speechSupported = "speechSynthesis" in window;
        this.elements = {
            startButton: document.getElementById("start-demo"),
            startCampaign: document.getElementById("start-campaign"),
            statusBadge: document.querySelector(".status-badge"),
            statusText: document.querySelector(".status-text"),
            entropyMeter: document.querySelector(".entropy-bar-fill"),
            entropyValue: document.querySelector(".entropy-value"),
            entropyThreshold: document.querySelector(".entropy-threshold"),
            timeline: document.querySelector(".timeline"),
            saveStateGoal: document.getElementById("save-state-goal"),
            saveStateWorked: document.getElementById("save-state-worked"),
            saveStateFailed: document.getElementById("save-state-failed"),
            saveStateBlocked: document.getElementById("save-state-blocked"),
            saveStateRecommended: document.getElementById("save-state-recommended"),
            saveStateContext: document.getElementById("save-state-context"),
            decisionTree: document.getElementById("decision-tree"),
            overrideTextarea: document.getElementById("override-text"),
            overrideButton: document.getElementById("submit-override"),
            overrideStatus: document.getElementById("override-status"),
            recoveryOptions: document.getElementById("recovery-options"),
            explainBrake: document.getElementById("explain-brake"),
            brakeExplanation: document.getElementById("brake-explanation"),
            brakeExplanationContent: document.getElementById("brake-explanation-content"),
            brakeAlert: document.getElementById("brake-alert"),
            voiceAlert: document.getElementById("voice-alert"),
            vibeSource: document.getElementById("vibe-source"),
            vibeSession: document.getElementById("vibe-session"),
            vibeHookStatus: document.getElementById("vibe-hook-status"),
            explainerSummary: document.getElementById("explainer-summary"),
            campaignPanel: document.getElementById("campaign-panel"),
            campaignStatus: document.getElementById("campaign-status"),
            attackPath: document.getElementById("attack-path"),
            minimalReproducer: document.getElementById("minimal-reproducer"),
            verifiedPolicyRepair: document.getElementById("verified-policy-repair"),
            sentinelStatus: document.getElementById("sentinel-status"),
        };
        this.setupEventListeners();
        this.updateUI();
    }

    setupEventListeners() {
        this.elements.startButton?.addEventListener("click", () => this.startDemo());
        this.elements.startCampaign?.addEventListener("click", () => this.startCampaign());
        document.querySelectorAll("[data-replay-proof]").forEach((button) => button.addEventListener("click", () => this.startCampaign()));
        this.elements.overrideButton?.addEventListener("click", () => this.authorizeRecovery());
        this.elements.explainBrake?.addEventListener("click", () => this.toggleBrakeExplanation());
        this.elements.recoveryOptions?.addEventListener("click", (event) => {
            const option = event.target.closest("[data-choice-id]");
            if (option) this.selectRecoveryChoice(option.dataset.choiceId);
        });
    }

    async startDemo() {
        return this.startScenario("db_migration_loop", "fixture");
    }

    async startCampaign() {
        return this.startScenario("immunity_compiler_campaign", "campaign");
    }

    async startScenario(scenarioId, mode) {
        this.cleanup();
        this.setStatus("running");
        if (this.elements.startButton) this.elements.startButton.disabled = true;
        if (this.elements.startCampaign) this.elements.startCampaign.disabled = true;
        if (mode === "campaign") this.showCampaignStatus("Campaign is starting; awaiting the first live evidence event.", "active");
        try {
            const response = await fetch("/api/runs", {
                method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({scenario_id: scenarioId})
            });
            const runData = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(runData.detail || "Could not create the live run");
            this.runId = runData.run_id;
            this.currentRun = runData;
            const startResponse = await fetch(`/api/runs/${this.runId}/start`, {method: "POST"});
            if (!startResponse.ok) {
                const startData = await startResponse.json().catch(() => ({}));
                throw new Error(startData.detail || "Could not start the live run");
            }
            this.updateUI();
            this.startEventStream();
        } catch (error) {
            console.error("Failed to start live run:", error);
            this.setStatus("failed");
            if (this.elements.startButton) this.elements.startButton.disabled = false;
            if (this.elements.startCampaign) this.elements.startCampaign.disabled = false;
            this.showOverrideStatus(error.message || "Failed to start live run", "error");
            if (mode === "campaign") this.showCampaignStatus(error.message || "Campaign could not start.", "error");
        }
    }

    startEventStream() {
        if (this.eventSource) this.eventSource.close();
        if (!this.runId) return;
        this.eventSource = new EventSource(`/api/runs/${this.runId}/stream`);
        const runEventTypes = [
            "snapshot", "step", "entropy", "braked", "save_state", "tree", "status",
            "override_accepted", "recovery_selected", "recovery_rejected", "recovery_authorized",
            "campaign_preparing", "campaign_detected", "campaign_repaired", "campaign_verified",
            "resumed", "completed", "voice"
        ];
        runEventTypes.forEach((eventType) => {
            this.eventSource.addEventListener(eventType, (event) => this.handleEvent({event: eventType, data: event.data}));
        });
        this.eventSource.onmessage = (event) => {
            try { this.handleEvent(JSON.parse(event.data)); }
            catch (error) { console.error("Failed to parse SSE event:", error); }
        };
        this.eventSource.onerror = () => this.startPolling();
    }

    startPolling() {
        if (this.pollInterval) clearInterval(this.pollInterval);
        this.pollInterval = setInterval(async () => {
            if (!this.runId) return;
            try {
                const response = await fetch(`/api/runs/${this.runId}`);
                if (!response.ok) throw new Error("Run polling failed");
                this.mergeRunPayload(await response.json());
                this.updateUI();
            } catch (error) { console.error("Polling error:", error); }
        }, 500);
    }

    parseEventData(data) {
        if (typeof data !== "string") return data || {};
        try { return JSON.parse(data); } catch (_) { return {}; }
    }

    mergeRunPayload(payload) {
        if (!payload || typeof payload !== "object") return;
        // Mutation endpoints return an envelope ({message, run_id, run}); streams return a RunState.
        const run = payload.run && typeof payload.run === "object" ? payload.run : payload;
        if (run.run_id || (Array.isArray(run.steps) && run.status)) {
            this.currentRun = run;
        } else if (this.currentRun && run.meta && typeof run.meta === "object") {
            this.currentRun.meta = {...(this.currentRun.meta || {}), ...run.meta};
        }
        this.syncRecoverySelectionFromRun();
    }

    mergeCampaignPayload(eventType, payload) {
        this.mergeRunPayload(payload);
        if (!this.currentRun) return;
        const meta = this.currentRun.meta = this.currentRun.meta || {};
        const campaign = meta.campaign = {...(meta.campaign && typeof meta.campaign === "object" ? meta.campaign : {})};
        const data = payload?.campaign && typeof payload.campaign === "object" ? payload.campaign : payload || {};
        if (eventType === "attack_path") campaign.attack_path = data.attack_path ?? data.path ?? data;
        if (eventType === "minimal_reproducer") campaign.minimal_reproducer = data.minimal_reproducer ?? data.reproducer ?? data;
        if (["policy_repair", "policy_verified", "repair_verified", "campaign_repaired", "campaign_verified"].includes(eventType)) {
            campaign.verified_policy_repair = data.verified_policy_repair ?? data.policy_repair ?? data.repair ?? data;
        }
        if (eventType === "campaign_preparing") campaign.status = data.status || "running";
        ["attack_path", "minimal_reproducer", "verified_policy_repair", "status"].forEach((key) => {
            if (data[key] !== undefined) campaign[key] = data[key];
        });
    }

    campaignData() {
        const meta = this.currentRun?.meta || {};
        const campaign = meta.campaign && typeof meta.campaign === "object" ? meta.campaign : {};
        return {
            attackPath: campaign.attack_path ?? meta.attack_path ?? this.currentRun?.attack_path,
            minimalReproducer: campaign.minimal_reproducer ?? meta.minimal_reproducer ?? this.currentRun?.minimal_reproducer,
            verifiedPolicyRepair: campaign.verified_policy_repair ?? meta.verified_policy_repair ?? meta.policy_repair ?? this.currentRun?.verified_policy_repair,
            status: campaign.status ?? meta.campaign_status,
        };
    }

    campaignValueHtml(value, emptyMessage) {
        if (value === undefined || value === null || value === "") return `<p class="empty-state">${this.escapeHtml(emptyMessage)}</p>`;
        if (Array.isArray(value)) return `<ol class="campaign-list">${value.map((item) => `<li>${this.campaignValueHtml(item, "")}</li>`).join("")}</ol>`;
        if (typeof value === "object") {
            const entries = Object.entries(value).filter(([key]) => !["run_id", "campaign"].includes(key));
            if (!entries.length) return `<p class="empty-state">${this.escapeHtml(emptyMessage)}</p>`;
            return `<dl class="campaign-definition">${entries.map(([key, item]) => `<div><dt>${this.escapeHtml(key.replace(/_/g, " "))}</dt><dd>${this.campaignValueHtml(item, "")}</dd></div>`).join("")}</dl>`;
        }
        return this.escapeHtml(value);
    }

    showCampaignStatus(message, type = "") {
        if (!this.elements.campaignStatus) return;
        this.elements.campaignStatus.textContent = message;
        this.elements.campaignStatus.className = `campaign-status ${type}`;
    }

    updateCampaignPanels() {
        if (!this.elements.campaignPanel) return;
        const campaign = this.campaignData();
        if (this.elements.attackPath) this.elements.attackPath.innerHTML = this.campaignValueHtml(campaign.attackPath, "Waiting for an observed attack path.");
        if (this.elements.minimalReproducer) this.elements.minimalReproducer.innerHTML = this.campaignValueHtml(campaign.minimalReproducer, "The smallest safe reproducer will appear here.");
        if (this.elements.verifiedPolicyRepair) this.elements.verifiedPolicyRepair.innerHTML = this.campaignValueHtml(campaign.verifiedPolicyRepair, "Waiting for a policy repair and verification.");
        const stageValues = {
            attack: campaign.attackPath,
            reproducer: campaign.minimalReproducer,
            repair: campaign.verifiedPolicyRepair,
        };
        Object.entries(stageValues).forEach(([stage, value]) => {
            const card = this.elements.campaignPanel.querySelector(`[data-campaign-stage="${stage}"]`);
            if (card) card.classList.toggle("complete", value !== undefined && value !== null && value !== "");
        });
        const isCampaign = Boolean(campaign.status || campaign.attackPath || campaign.minimalReproducer || campaign.verifiedPolicyRepair);
        if (isCampaign) {
            const verified = campaign.verifiedPolicyRepair && typeof campaign.verifiedPolicyRepair === "object" &&
                (campaign.verifiedPolicyRepair.verified === true || campaign.verifiedPolicyRepair.status === "verified");
            this.showCampaignStatus(verified ? "Policy repair verified against the captured reproducer." : campaign.status || "Campaign evidence is streaming from the active run.", verified ? "verified" : "active");
        }
    }

    handleEvent(event) {
        const eventType = event?.event;
        const payload = this.parseEventData(event?.data);
        if (!this.currentRun) this.currentRun = {steps: [], status: "running", meta: {}};
        switch (eventType) {
            case "campaign_preparing":
            case "campaign_detected":
            case "campaign_repaired":
            case "campaign_verified":
                this.mergeCampaignPayload(eventType, payload);
                break;
            case "snapshot":
                this.mergeRunPayload(payload);
                break;
            case "step":
                this.currentRun.steps = this.currentRun.steps || [];
                this.currentRun.steps.push(payload);
                break;
            case "entropy": this.currentRun.entropy = payload; break;
            case "save_state": this.currentRun.save_state = payload; break;
            case "tree": this.currentRun.decision_tree = payload; break;
            case "status": this.currentRun.status = payload.status || this.currentRun.status; break;
            case "braked":
                this.currentRun.status = "braked";
                this.showBrakeAlert();
                if (this.speechSupported) this.speak("Agent is stuck. Human authorization required.");
                break;
            case "recovery_selected":
                this.mergeRunPayload(payload);
                this.selectedChoiceId = payload.choice_id || payload.selected_choice_id || this.selectedChoiceId;
                this.selectedChoiceAccepted = true;
                this.authorizationPending = false;
                this.showOverrideStatus("Recovery selected. Review it, then authorize the next action.", "pending");
                break;
            case "recovery_rejected":
                this.mergeRunPayload(payload);
                this.selectedChoiceAccepted = false;
                this.authorizationPending = false;
                this.showOverrideStatus(payload.detail || payload.message || "That option cannot authorize recovery.", "error");
                break;
            case "recovery_authorized":
            case "override_accepted":
                this.mergeRunPayload(payload);
                this.authorizationPending = true;
                this.selectedChoiceAccepted = false;
                this.showOverrideStatus("Authorization accepted. The verified recovery is now running.", "success");
                break;
            case "resumed": this.currentRun.status = "running_resume"; break;
            case "completed":
                this.currentRun.status = "completed";
                this.authorizationPending = false;
                this.showOverrideStatus("Recovery completed and was verified by the fixture.", "success");
                break;
            case "voice":
                if (payload.text) {
                    this.showVoiceAlert(payload.text);
                    if (this.speechSupported) this.speak(payload.text);
                }
                break;
            default:
                if (payload?.run_id) this.mergeRunPayload(payload);
        }
        this.syncRecoverySelectionFromRun();
        this.updateUI();
    }

    updateUI() {
        if (!this.currentRun) { this.setStatus("idle"); this.updateLiveExplainer(); this.updateCampaignPanels(); return; }
        this.setStatus(this.currentRun.status || "running");
        this.updateTimeline();
        this.updateEntropy();
        this.updateSaveState();
        this.updateDecisionTree();
        this.updateVibeMetadata();
        this.updateOverrideConsole();
        this.updateBrakeExplanation();
        this.updateLiveExplainer();
        this.updateCampaignPanels();
        this.updateSentinelProofFlow();
    }

    updateTimeline() {
        if (!this.elements.timeline) return;
        const steps = this.currentRun?.steps || [];
        if (!steps.length) {
            this.elements.timeline.innerHTML = "<p class=\"empty-state\">No steps yet. Starting scenario...</p>";
            return;
        }
        this.elements.timeline.innerHTML = steps.map((step) => `
            <div class="timeline-item ${this.escapeHtml(step.status || "thinking")}">
                <span class="index">${this.escapeHtml(step.index)}</span>
                <span class="title">${this.escapeHtml(step.title)}</span>
                <span class="status">${this.escapeHtml(step.status)}</span>
                ${step.error_signature ? `<div class="details">Error: ${this.escapeHtml(step.error_signature)}</div>` : ""}
            </div>`).join("");
    }

    updateEntropy() {
        const entropy = this.currentRun?.entropy;
        if (!this.elements.entropyMeter || !entropy) return;
        const score = Number(entropy.score || 0);
        const threshold = Number(entropy.threshold || 0.65);
        this.elements.entropyMeter.style.width = `${Math.min(100, score * 100)}%`;
        this.elements.entropyMeter.className = `entropy-bar-fill ${score < threshold * .7 ? "low" : score < threshold ? "medium" : "high"}`;
        if (this.elements.entropyValue) {
            this.elements.entropyValue.textContent = score.toFixed(2);
            this.elements.entropyValue.className = `entropy-value${score >= threshold ? " danger" : score >= threshold * .8 ? " warning" : ""}`;
        }
        if (this.elements.entropyThreshold) this.elements.entropyThreshold.textContent = `Threshold: ${threshold}`;
    }

    safeVibeMetadata(value) {
        if (typeof value !== "string" && typeof value !== "number") return null;
        const label = String(value).trim().replace(/\s+/g, " ");
        if (!label || label.length > 120 || /(api[_ -]?key|token|secret|authorization|bearer|password)/i.test(label)) return null;
        return label;
    }

    updateVibeMetadata() {
        const meta = this.currentRun?.meta || {};
        const nested = meta.vibe && typeof meta.vibe === "object" ? meta.vibe :
            meta.vibe_metadata && typeof meta.vibe_metadata === "object" ? meta.vibe_metadata : {};
        const read = (...values) => values.map((value) => this.safeVibeMetadata(value)).find(Boolean) || null;
        const source = read(nested.source, meta.vibe_source, meta.source);
        const session = read(nested.session_label, nested.session_id, nested.session, meta.vibe_session_label, meta.vibe_session_id);
        const hookStatus = read(nested.hook_status, nested.status, meta.vibe_hook_status, meta.vibe_control);
        if (this.elements.vibeSource) this.elements.vibeSource.textContent = source || "Fixture scenario — no Vibe source metadata";
        if (this.elements.vibeSession) this.elements.vibeSession.textContent = session || "Not provided";
        if (this.elements.vibeHookStatus) this.elements.vibeHookStatus.textContent = hookStatus || (source || session ? "Metadata received" : "Not connected (fixture)");
    }

    updateSaveState() {
        const ss = this.currentRun?.save_state;
        if (!ss) {
            ["saveStateGoal", "saveStateWorked", "saveStateFailed", "saveStateBlocked", "saveStateRecommended", "saveStateContext"].forEach((id) => {
                if (this.elements[id]) this.elements[id].innerHTML = "<p class=\"empty-state\">Waiting for brake...</p>";
            });
            return;
        }
        const items = (values, className = "") => `<ul class="${className}">${(values || []).map((value) => `<li>${this.escapeHtml(value)}</li>`).join("")}</ul>`;
        if (this.elements.saveStateGoal) this.elements.saveStateGoal.innerHTML = `<strong>Goal:</strong> ${this.escapeHtml(ss.goal)}`;
        if (this.elements.saveStateWorked) this.elements.saveStateWorked.innerHTML = `<strong>Worked:</strong>${items(ss.worked)}`;
        if (this.elements.saveStateFailed) this.elements.saveStateFailed.innerHTML = `<strong>Failed:</strong>${items(ss.failed, "failed")}`;
        if (this.elements.saveStateBlocked) this.elements.saveStateBlocked.innerHTML = `<strong>Blocked on:</strong> ${this.escapeHtml(ss.blocked_on)}`;
        if (this.elements.saveStateRecommended) this.elements.saveStateRecommended.innerHTML = `<strong>Recommended:</strong>${items(ss.recommended_next_actions)}`;
        if (this.elements.saveStateContext) this.elements.saveStateContext.innerHTML = `<strong>Context:</strong> ${this.escapeHtml(ss.context_summary)}`;
    }

    updateDecisionTree() {
        if (!this.elements.decisionTree) return;
        const tree = this.currentRun?.decision_tree;
        this.elements.decisionTree.innerHTML = tree?.root ? this.renderTreeNode(tree.root, tree.highlight_path || []) :
            "<p class=\"empty-state\">Decision tree will appear on brake...</p>";
    }

    renderTreeNode(node, highlightPath) {
        const children = (node.children || []).map((child) => this.renderTreeNode(child, highlightPath)).join("");
        return `<div class="tree-node ${this.escapeHtml(node.kind || "")}${highlightPath.includes(node.id) ? " highlight" : ""}">
            <div class="node-content"><span class="label">${this.escapeHtml(node.label)}</span><span class="kind">${this.escapeHtml(node.kind)}</span></div>
            ${children ? `<div class="tree-children">${children}</div>` : ""}</div>`;
    }

    getRecoveryOptions() {
        const meta = this.currentRun?.meta || {};
        return Array.isArray(meta.recovery_options) ? meta.recovery_options : [];
    }

    syncRecoverySelectionFromRun() {
        const meta = this.currentRun?.meta || {};
        const recovery = meta.recovery && typeof meta.recovery === "object" ? meta.recovery : {};
        const selection = meta.recovery_selection && typeof meta.recovery_selection === "object"
            ? meta.recovery_selection : recovery.selection && typeof recovery.selection === "object" ? recovery.selection : {};
        const authorizedChoiceId = meta.recovery_authorized_choice_id || recovery.authorized_choice_id;
        const selected = selection.choice_id || meta.selected_recovery_choice_id || meta.recovery_selected_choice_id || recovery.selected_choice_id;
        if (authorizedChoiceId) {
            this.selectedChoiceId = authorizedChoiceId;
            this.selectedChoiceAccepted = false;
            this.authorizationPending = this.currentRun?.status !== "completed";
            return;
        }
        if (selected) {
            this.selectedChoiceId = selected;
            this.selectedChoiceAccepted = Boolean(selection.authorizing ?? true);
            this.authorizationPending = false;
            return;
        }
        this.selectedChoiceId = null;
        this.selectedChoiceAccepted = false;
        this.authorizationPending = false;
    }

    selectedRecoveryOption() {
        return this.getRecoveryOptions().find((option) => option.id === this.selectedChoiceId) || null;
    }

    updateOverrideConsole() {
        const isBraked = this.currentRun?.status === "braked";
        const options = this.getRecoveryOptions();
        const selected = this.selectedRecoveryOption();
        const canAuthorize = isBraked && Boolean(selected?.authorizing) && this.selectedChoiceAccepted && !this.authorizationPending;
        if (this.elements.overrideButton) this.elements.overrideButton.disabled = !canAuthorize;
        if (this.elements.overrideTextarea) this.elements.overrideTextarea.disabled = !isBraked || this.authorizationPending;
        if (!this.elements.recoveryOptions) return;
        if (!isBraked) {
            this.elements.recoveryOptions.innerHTML = "<p class=\"empty-state\">The guarded choices unlock only after GlassBox Sentinel brakes a run.</p>";
            return;
        }
        if (!options.length) {
            this.elements.recoveryOptions.innerHTML = "<p class=\"empty-state\">Waiting for guarded recovery options from this run. Free text cannot resume the fixture.</p>";
            return;
        }
        this.elements.recoveryOptions.innerHTML = options.map((option) => {
            const selectedClass = option.id === this.selectedChoiceId ? " selected" : "";
            const safe = Boolean(option.authorizing);
            return `<button class="recovery-choice${selectedClass}${safe ? "" : " non-authorizing"}" type="button" role="radio"
                aria-checked="${option.id === this.selectedChoiceId}" data-choice-id="${this.escapeHtml(option.id)}">
                <span class="choice-title">${this.escapeHtml(option.label)}</span>
                <span class="choice-description">${this.escapeHtml(option.description)}</span>
                ${option.evidence ? `<span class="choice-evidence">Evidence: ${this.escapeHtml(option.evidence)}</span>` : ""}
                <span class="choice-policy">${safe ? "Evidence-backed recovery" : "Cannot authorize recovery"}</span>
            </button>`;
        }).join("");
    }

    async selectRecoveryChoice(choiceId) {
        const option = this.getRecoveryOptions().find((item) => item.id === choiceId);
        if (this.currentRun?.status !== "braked" || !option) return;
        this.selectedChoiceId = choiceId;
        this.selectedChoiceAccepted = false;
        this.authorizationPending = false;
        if (!option.authorizing) {
            this.updateOverrideConsole();
            this.showOverrideStatus("This alternative is visible for comparison, but its evidence does not authorize recovery.", "error");
            return;
        }
        this.updateOverrideConsole();
        this.showOverrideStatus("Valid recovery selected. Recording selection…", "pending");
        try {
            const response = await fetch(`/api/runs/${this.runId}/override`, {
                method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({choice_id: choiceId, rationale: this.elements.overrideTextarea?.value.trim() || undefined})
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || "Recovery selection was rejected");
            this.mergeRunPayload(payload);
            this.selectedChoiceAccepted = true;
            this.showOverrideStatus("Recovery selected. Click Authorize Selected Recovery to continue.", "pending");
        } catch (error) {
            this.selectedChoiceAccepted = false;
            this.showOverrideStatus(error.message || "Recovery selection failed", "error");
        }
        this.updateUI();
    }

    async authorizeRecovery() {
        const option = this.selectedRecoveryOption();
        if (!this.runId || this.currentRun?.status !== "braked" || !option?.authorizing || !this.selectedChoiceAccepted) {
            this.showOverrideStatus("Select a valid evidence-backed recovery before authorizing it.", "error");
            return;
        }
        this.authorizationPending = true;
        this.updateOverrideConsole();
        try {
            const response = await fetch(`/api/runs/${this.runId}/override/authorize`, {method: "POST"});
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || "Authorization was rejected");
            this.mergeRunPayload(payload);
            this.selectedChoiceAccepted = false;
            this.showOverrideStatus("Authorization accepted. The recovery path is running.", "success");
        } catch (error) {
            this.authorizationPending = false;
            this.showOverrideStatus(error.message || "Authorization failed", "error");
        }
        this.updateUI();
    }

    toggleBrakeExplanation() {
        const panel = this.elements.brakeExplanation;
        if (!panel) return;
        panel.hidden = !panel.hidden;
        this.elements.explainBrake?.setAttribute("aria-expanded", String(!panel.hidden));
    }

    repeatedSignatures() {
        const counts = new Map();
        (this.currentRun?.steps || []).forEach((step) => {
            if (step.error_signature) counts.set(step.error_signature, (counts.get(step.error_signature) || 0) + 1);
        });
        return [...counts.entries()].filter(([, count]) => count > 1);
    }

    updateBrakeExplanation() {
        const target = this.elements.brakeExplanationContent;
        if (!target) return;
        const ss = this.currentRun?.save_state;
        const entropy = this.currentRun?.entropy || {};
        const repeats = this.repeatedSignatures();
        if (!ss && !repeats.length && this.currentRun?.status !== "braked") {
            target.innerHTML = "<p>Loop evidence will appear here when the run brakes.</p>";
            return;
        }
        const reasons = Array.isArray(entropy.reasons) ? entropy.reasons :
            Object.entries(entropy.components || {}).filter(([, value]) => Number(value) > 0).map(([name, value]) => `${name}: ${value}`);
        target.innerHTML = `
            <p><strong>Brake state:</strong> ${this.escapeHtml(this.currentRun?.status === "braked" ? "The fixture is held; no recovery can run without authorization." : "This saved explanation is retained after recovery.")}</p>
            ${repeats.length ? `<p><strong>Repeated signature:</strong> ${repeats.map(([signature, count]) => `${this.escapeHtml(signature)} (${count} times)`).join(", ")}</p>` : ""}
            ${reasons.length ? `<p><strong>Loop Risk evidence:</strong></p><ul>${reasons.map((reason) => `<li>${this.escapeHtml(reason)}</li>`).join("")}</ul>` : ""}
            ${ss?.blocked_on ? `<p><strong>Blocked on:</strong> ${this.escapeHtml(ss.blocked_on)}</p>` : ""}
            ${ss?.recommended_next_actions?.length ? `<p><strong>Recorded safe next action:</strong> ${this.escapeHtml(ss.recommended_next_actions[0])}</p>` : ""}`;
    }

    updateLiveExplainer() {
        const run = this.currentRun;
        const stages = {
            action: {active: Boolean(run?.steps?.length), done: Boolean(run?.steps?.length), detail: run?.steps?.length ? `${run.steps.length} observed action${run.steps.length === 1 ? "" : "s"}` : "Waiting for run"},
            loop: {active: this.repeatedSignatures().length > 0, done: run?.status === "braked" || run?.status === "completed", detail: this.repeatedSignatures().length ? this.repeatedSignatures().map(([signature, count]) => `${signature} ×${count}`).join(", ") : "No repeated signature yet"},
            brake: {active: run?.status === "braked", done: Boolean(run?.save_state) && run?.status !== "braked", detail: run?.status === "braked" ? "Held with an auditable save state" : run?.save_state ? "State compressed for recovery" : "Brake not triggered"},
            authorization: {active: run?.status === "braked", done: this.authorizationPending || run?.status === "running_resume" || run?.status === "completed", detail: this.authorizationPending ? "Authorized; recovery in progress" : this.selectedChoiceAccepted ? "Selected; explicit authorization required" : this.selectedRecoveryOption() ? "Choice needs validation" : "No recovery selected"},
            verify: {active: run?.status === "running_resume", done: run?.status === "completed", detail: run?.status === "completed" ? "Fixture recovery completed" : run?.status === "running_resume" ? "Verifying recovery actions" : "Awaiting recovery"},
        };
        Object.entries(stages).forEach(([name, state]) => {
            const node = document.querySelector(`[data-explainer-stage="${name}"]`);
            const detail = document.getElementById(`explainer-${name}-detail`);
            if (!node) return;
            node.classList.toggle("active", state.active);
            node.classList.toggle("complete", state.done);
            if (detail) detail.textContent = state.detail;
        });
        if (this.elements.explainerSummary) {
            this.elements.explainerSummary.textContent = !run ? "Start the fixture to trace its control loop." :
                run.status === "braked" ? "GlassBox Sentinel stopped the run at a safe boundary; a human must authorize a supported recovery." :
                run.status === "completed" ? "Recovery completed with the selected, evidence-backed action." : "The diagram follows the same live run state as the timeline.";
        }
    }

    showBrakeAlert() { this.elements.brakeAlert?.classList.add("visible"); }

    showOverrideStatus(message, type) {
        if (!this.elements.overrideStatus) return;
        this.elements.overrideStatus.textContent = message;
        this.elements.overrideStatus.className = `override-status ${type} visible`;
    }

    showVoiceAlert(text) {
        if (!this.elements.voiceAlert) return;
        this.elements.voiceAlert.textContent = `Voice: ${text}`;
        this.elements.voiceAlert.classList.add("visible");
    }

    setStatus(status) {
        if (!this.elements.statusBadge || !this.elements.statusText) return;
        this.elements.statusBadge.className = `status-badge ${status}`;
        this.elements.statusBadge.textContent = String(status).toUpperCase();
        const labels = {
            idle: "Idle - Ready to start", running: "Running - Executing steps", braked: "Braked - Awaiting guarded recovery",
            running_resume: "Running (recovery) - Verifying selected action", completed: "Completed - Recovery verified", failed: "Failed - Error occurred"
        };
        this.elements.statusText.textContent = labels[status] || status;
    }

    speak(text) {
        if (!this.speechSupported) return;
        try { window.speechSynthesis.speak(new SpeechSynthesisUtterance(text)); }
        catch (error) { console.error("Speech synthesis error:", error); }
    }

    escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text === undefined || text === null ? "" : String(text);
        return div.innerHTML;
    }

    cleanup() {
        if (this.eventSource) this.eventSource.close();
        if (this.pollInterval) clearInterval(this.pollInterval);
        this.eventSource = null;
        this.pollInterval = null;
        this.runId = null;
        this.currentRun = null;
        this.selectedChoiceId = null;
        this.selectedChoiceAccepted = false;
        this.authorizationPending = false;
        if (this.elements.startButton) this.elements.startButton.disabled = false;
        if (this.elements.startCampaign) this.elements.startCampaign.disabled = false;
        if (this.elements.overrideTextarea) {
            this.elements.overrideTextarea.value = "";
            this.elements.overrideTextarea.disabled = true;
        }
        if (this.elements.overrideButton) this.elements.overrideButton.disabled = true;
        if (this.elements.overrideStatus) {
            this.elements.overrideStatus.textContent = "";
            this.elements.overrideStatus.className = "override-status";
        }
        if (this.elements.recoveryOptions) this.elements.recoveryOptions.innerHTML =
            "<p class=\"empty-state\">Recovery options appear when the brake captures its save state.</p>";
        if (this.elements.timeline) this.elements.timeline.innerHTML =
            "<p class=\"empty-state\">Click “Start Demo Run” to begin</p>";
        if (this.elements.entropyMeter) {
            this.elements.entropyMeter.style.width = "0%";
            this.elements.entropyMeter.className = "entropy-bar-fill low";
        }
        if (this.elements.entropyValue) this.elements.entropyValue.textContent = "0.00";
        if (this.elements.entropyThreshold) this.elements.entropyThreshold.textContent = "Threshold: 0.65";
        ["saveStateGoal", "saveStateWorked", "saveStateFailed", "saveStateBlocked", "saveStateRecommended", "saveStateContext"].forEach((id) => {
            if (this.elements[id]) this.elements[id].innerHTML = "<p class=\"empty-state\">Waiting for brake...</p>";
        });
        if (this.elements.decisionTree) this.elements.decisionTree.innerHTML =
            "<p class=\"empty-state\">Decision tree will appear on brake...</p>";
        this.elements.brakeAlert?.classList.remove("visible");
        this.elements.voiceAlert?.classList.remove("visible");
        if (this.elements.voiceAlert) this.elements.voiceAlert.textContent = "";
        if (this.elements.brakeExplanation) this.elements.brakeExplanation.hidden = true;
        this.elements.explainBrake?.setAttribute("aria-expanded", "false");
        this.updateVibeMetadata();
        this.setStatus("idle");
        this.updateLiveExplainer();
        this.updateCampaignPanels();
        this.updateSentinelProofFlow();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.glassBoxApp = new GlassBoxApp();
});


const HUB_HASHES = {
    overview: "#overview",
    proof: "#proof",
    architecture: "#architecture",
    vibe: "#vibe",
    trust: "#trust",
};

function activateHubTab(tabName, updateHash = false, moveFocus = false) {
    const target = HUB_HASHES[tabName] ? tabName : "overview";
    const tabs = document.querySelectorAll("[role=tab][data-tab]");
    const panels = document.querySelectorAll("[role=tabpanel]");

    if (!tabs.length || !panels.length) return;

    tabs.forEach((tab) => {
        const selected = tab.dataset.tab === target;
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
    });
    panels.forEach((panel) => {
        panel.hidden = panel.id !== `panel-${target}`;
    });

    window.scrollTo({top: 0, behavior: updateHash ? "smooth" : "auto"});

    if (moveFocus) {
        document.getElementById(`tab-${target}`).focus();
    }

    if (updateHash && window.location.hash !== HUB_HASHES[target]) {
        window.location.hash = HUB_HASHES[target];
    }
}

function initializeHubTabs() {
    const tabs = Array.from(document.querySelectorAll("[role=tab][data-tab]"));
    if (!tabs.length) return;

    const tabFromHash = window.location.hash.slice(1);
    activateHubTab(HUB_HASHES[tabFromHash] ? tabFromHash : "overview");

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => activateHubTab(tab.dataset.tab, true));
        tab.addEventListener("keydown", (event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            const current = tabs.indexOf(tab);
            const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 :
                (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
            tabs[next].focus();
            activateHubTab(tabs[next].dataset.tab, true);
        });
    });

    document.querySelectorAll("[data-open-tab]").forEach((control) => {
        control.addEventListener("click", () => activateHubTab(control.dataset.openTab, true, true));
    });

    window.addEventListener("hashchange", () => {
        const tabFromHash = window.location.hash.slice(1);
        activateHubTab(HUB_HASHES[tabFromHash] ? tabFromHash : "overview");
    });
}

document.addEventListener("DOMContentLoaded", initializeHubTabs);
