(() => {
  let sessionForSubmission = '';
  let screenShareElapsedMs = 0;
  let screenShareStartedAt = 0;
  let pitchCameraSource = null, pitchScreenSource = null, pitchScreenStream = null;
  let pitchCompositeCanvas = null, pitchCompositeStream = null, pitchCompositeFrame = 0;
  const selectedSubmission = () => {
    const teamId = $('#participant-team')?.value;
    return submissions.find(item => item.team_id === teamId);
  };
  const setPitchStatus = (text, warning = false) => {
    const status = $('#pitch-status');
    if (status) { status.textContent = text; status.className = `status${warning ? ' review' : ''}`; }
  };
  function mountPhase2() {
    if (!apiReady || page !== 'participant') return;
    const recordingConsent = $('#record-consent')?.closest('.consent-box');
    if (recordingConsent && !$('#ai-processing-consent')) {
      recordingConsent.insertAdjacentHTML('afterend', `<label class="consent-box" style="border-color:#d8e6db"><input type="checkbox" id="ai-processing-consent"><span><b>AI processing consent:</b> I agree that JudgeX may upload this pitch and use my submitted project text, documents, and public repository to create a transcript, searchable evidence, and AI evaluation using the provider configured by this event. I can withdraw consent later. My recording will be stored privately.</span></label>`);
      const active = selectedSubmission();
      $('#ai-processing-consent').checked = Boolean(active?.ai_processing_consent_at);
    }
    const docsPanel = $('#participant-file')?.closest('.panel');
    if (docsPanel && !$('#index-evidence')) {
      docsPanel.insertAdjacentHTML('beforeend', `<button id="index-evidence" class="btn btn-primary" style="margin-top:11px;width:100%" data-action="ingest-evidence">Index project evidence</button><p class="pitch-note">Embeddings are sent to the configured AI provider only after you grant consent above.</p>`);
    }
    const pitchPanel = $('#pitch-screen')?.closest('.panel');
    if (pitchPanel && !$('#pitch-transcript-state')) {
      pitchPanel.insertAdjacentHTML('beforeend', `<section class="panel" id="pitch-transcript-state" style="margin-top:13px;padding:12px"><div class="panel-head"><div><h3>Pitch transcript</h3><p id="transcript-status">No uploaded pitch yet</p></div><button class="quiet-link" id="retry-transcription" data-action="retry-transcription" style="display:none">Transcribe →</button></div><p id="transcript-text" class="pitch-note">After you consent and upload a recording, JudgeX can create a transcript.</p><p id="pitch-demo-signals" class="pitch-note"></p><div id="pitch-claims"></div></section>`);
    }
    if (pitchPanel && !$('#pitch-question-tools')) pitchPanel.insertAdjacentHTML('beforeend', `<section class="panel" id="pitch-question-tools" style="margin-top:13px;padding:12px"><div class="panel-head"><div><h3>Pitch preparation</h3><p>Prepare for likely judge follow-up questions using your project evidence.</p></div><button class="btn btn-sm" data-action="generate-pitch-questions">Suggest questions</button></div><div id="pitch-question-list"></div></section>`);
    const active = selectedSubmission();
    if (active?.id && active.id !== sessionForSubmission) {
      sessionForSubmission = active.id;
      api(`/submissions/${active.id}/pitch-sessions`).then(sessions => {
        if (!sessions.length) return;
        const latest = sessions[0];
        pitchSessionId = latest.id;
        if (page !== 'participant' || selectedSubmission()?.id !== active.id) return;
        const label = $('#transcript-status'), text = $('#transcript-text'), retry = $('#retry-transcription');
        if (label) label.textContent = `Pitch ${latest.transcription_status} · ${latest.duration_seconds}s`;
        if (text) text.textContent = latest.transcript || 'The transcript is not ready yet.';
        const demoSignals=$('#pitch-demo-signals');if(demoSignals&&latest.demo_signals?.screen_share_detected)demoSignals.textContent=`Screen share captured for ${latest.demo_signals.screen_share_seconds} seconds. This is review context only; it does not affect a score.`;
        const claimHost=$('#pitch-claims');if(claimHost)claimHost.innerHTML=latest.claims?.length?`<h4>Claims extracted from the pitch</h4>${latest.claims.map(c=>`<div class="event-row"><div class="event-info"><b>${esc(c.kind)} · ${esc(c.text)}</b><small>“${esc(c.quote)}”</small></div></div>`).join('')}`:'';
        if (retry && ['uploaded', 'failed'].includes(latest.transcription_status)) retry.style.display = '';
        setPitchStatus(latest.transcription_status === 'completed' ? 'Transcript ready' : 'Recording on file', latest.transcription_status !== 'completed');
      }).catch(() => {});
    }
  }
  const observer = new MutationObserver(mountPhase2);
  observer.observe($('#app'), { childList: true, subtree: true });
  document.addEventListener('change', event => {
    if (event.target.id === 'participant-team') {
      sessionForSubmission = '';
      pitchSessionId = '';
      setTimeout(mountPhase2, 0);
    }
  });

  window.startPitch = async function () {
    const recordingConsent = $('#record-consent')?.checked;
    const aiConsent = $('#ai-processing-consent')?.checked;
    const submission = selectedSubmission();
    if (!submission) { toast('Save a project draft before recording a pitch'); return; }
    if (!recordingConsent || !aiConsent) { toast('Agree to both recording and AI processing before starting'); return; }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { toast('Camera recording needs a supported browser on localhost or HTTPS'); return; }
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 360 }, frameRate: { ideal: 20, max: 24 } }, audio: true });
      const consent = await api(`/submissions/${submission.id}/pitch-sessions`, { method: 'POST', body: { recording_consent: true, ai_processing_consent: true } });
      pitchSessionId = consent.id;
      screenShareElapsedMs = 0; screenShareStartedAt = 0;
      pitchCameraSource=document.createElement('video');pitchCameraSource.muted=true;pitchCameraSource.playsInline=true;pitchCameraSource.srcObject=mediaStream;await pitchCameraSource.play();
      pitchCompositeCanvas=document.createElement('canvas');pitchCompositeCanvas.width=960;pitchCompositeCanvas.height=540;
      const context=pitchCompositeCanvas.getContext('2d');
      const drawFrame=()=>{if(!context||!mediaStream)return;const cameraReady=pitchCameraSource?.readyState>=2,screenReady=pitchScreenSource?.readyState>=2;
        context.fillStyle='#101b17';context.fillRect(0,0,960,540);
        if(screenReady){context.drawImage(pitchScreenSource,0,0,960,540);if(cameraReady){const width=240,height=135;context.drawImage(pitchCameraSource,960-width-18,18,width,height);context.strokeStyle='#ffffff';context.lineWidth=3;context.strokeRect(960-width-18,18,width,height);}}
        else if(cameraReady)context.drawImage(pitchCameraSource,0,0,960,540);
        pitchCompositeFrame=requestAnimationFrame(drawFrame);};
      if(context&&pitchCompositeCanvas.captureStream){drawFrame();pitchCompositeStream=pitchCompositeCanvas.captureStream(15);mediaStream.getAudioTracks().forEach(track=>pitchCompositeStream.addTrack(track));}else pitchCompositeStream=mediaStream;
      const video = $('#camera-preview');
      video.srcObject = mediaStream; video.style.display = 'block'; $('#camera-placeholder').style.display = 'none';
      recordChunks = [];
      const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus') ? 'video/webm;codecs=vp9,opus' : 'video/webm';
      recorder = new MediaRecorder(pitchCompositeStream, { mimeType: mime, videoBitsPerSecond: 420000, audioBitsPerSecond: 48000 });
      recorder.ondataavailable = event => { if (event.data.size) recordChunks.push(event.data); };
      recorder.onstop = async () => {
        clearInterval(pitchInterval); pitchInterval = null;
        if(screenShareStartedAt){screenShareElapsedMs+=Date.now()-screenShareStartedAt;screenShareStartedAt=0;}
        const screenShareSeconds=Math.min(pitchSeconds,Math.round(screenShareElapsedMs/1000));
        const blob = new Blob(recordChunks, { type: mime });
        if (blob.size) {
          const localUrl = URL.createObjectURL(blob), download = document.createElement('a');
          download.href = localUrl; download.download = `judgex-pitch-${new Date().toISOString().slice(0,10)}.webm`; download.click();
          setTimeout(() => URL.revokeObjectURL(localUrl), 1500);
          try {
            const form = new FormData(); form.append('file', blob, 'pitch.webm');
            const uploaded=await api(`/pitch-sessions/${pitchSessionId}/recording?duration_seconds=${Math.max(1,pitchSeconds)}&screen_share_seconds=${screenShareSeconds}`, { method: 'POST', body: form });
            const demoSignals=$('#pitch-demo-signals');if(demoSignals&&uploaded.demo_signals?.screen_share_detected)demoSignals.textContent=`Screen share captured for ${uploaded.demo_signals.screen_share_seconds} seconds. This is review context only; it does not affect a score.`;
            const status = $('#transcript-status'), text = $('#transcript-text');
            if (status) status.textContent = 'Uploaded privately · requesting transcript';
            if (text) text.textContent = 'The recording is stored privately. The configured provider is processing the transcript.';
            setPitchStatus('Transcribing', true);
            const result = await api(`/pitch-sessions/${pitchSessionId}/transcribe`, { method: 'POST' });
            if (status) status.textContent = `Transcript ready · ${result.duration_seconds}s`;
            if (text) text.textContent = result.transcript || 'No speech was detected.';
            const claimHost=$('#pitch-claims');if(claimHost)claimHost.innerHTML=result.claims?.length?`<h4>Claims extracted from the pitch</h4>${result.claims.map(c=>`<div class="event-row"><div class="event-info"><b>${esc(c.kind)} · ${esc(c.text)}</b><small>“${esc(c.quote)}”</small></div></div>`).join('')}`:'';
            setPitchStatus('Transcript ready');
            toast('Pitch uploaded and transcribed');
          } catch (error) {
            const status = $('#transcript-status'), text = $('#transcript-text'), retry = $('#retry-transcription');
            if (status) status.textContent = error.message.includes('OPENAI_API_KEY') ? 'Recording stored · transcription not configured' : 'Recording stored · transcription needs attention';
            if (text) text.textContent = 'A local copy was downloaded. The private server copy can be transcribed after configuring the provider.';
            if (retry) retry.style.display = '';
            setPitchStatus('Recording saved', true);
            toast(error.message);
          }
        }
        cancelAnimationFrame(pitchCompositeFrame);pitchScreenStream?.getTracks().forEach(track=>track.stop());pitchCompositeStream?.getTracks().forEach(track=>track.stop());
        mediaStream?.getTracks().forEach(track => track.stop()); mediaStream = null;pitchScreenStream=null;pitchCompositeStream=null;pitchCameraSource=null;pitchScreenSource=null;
        if (video) { video.srcObject = null; video.style.display = 'none'; }
        if ($('#camera-placeholder')) $('#camera-placeholder').style.display = 'block';
        if ($('#record-pill')) $('#record-pill').style.display = 'none';
        $$('[data-action="pitch-start"],[data-action="pitch-screen"],[data-action="pitch-stop"]').forEach(button => button.disabled = button.dataset.action !== 'pitch-start');
      };
      recorder.start(1000); pitchSeconds = 0;
      setPitchStatus('Recording', true);
      $('#record-pill').style.display = 'inline-block';
      $$('[data-action="pitch-start"],[data-action="pitch-screen"],[data-action="pitch-stop"]').forEach(button => button.disabled = button.dataset.action !== 'pitch-screen' && button.dataset.action !== 'pitch-stop');
      pitchInterval = setInterval(() => {
        pitchSeconds++;
        const minute = String(Math.floor(pitchSeconds / 60)).padStart(2,'0'), second = String(pitchSeconds % 60).padStart(2,'0');
        if ($('#pitch-duration')) $('#pitch-duration').textContent = `${minute}:${second}`;
        if (pitchSeconds >= 420) { toast('The 7-minute pitch limit was reached'); stopPitch(); }
      }, 1000);
    } catch (error) {
      mediaStream?.getTracks().forEach(track => track.stop()); mediaStream = null;
      toast(error.message.includes('OPENAI_API_KEY') ? error.message : error.name === 'NotAllowedError' ? 'Camera or microphone permission was not granted' : error.message || 'Could not start the pitch recording');
    }
  };
  window.sharePitchScreen = async function () {
    if (!$('#record-consent')?.checked || !$('#ai-processing-consent')?.checked) { toast('Consent is required before recording or sharing your screen'); return; }
    if (!mediaStream || recorder?.state !== 'recording') { toast('Start the pitch recording before sharing your screen'); return; }
    try {
      const display = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 15 }, audio: false });
      const screenTrack = display.getVideoTracks()[0];
      pitchScreenStream?.getTracks().forEach(track=>track.stop());pitchScreenStream=display;
      pitchScreenSource=document.createElement('video');pitchScreenSource.muted=true;pitchScreenSource.playsInline=true;pitchScreenSource.srcObject=display;await pitchScreenSource.play();
      screenShareStartedAt=Date.now();
      screenTrack.onended = () => {if(screenShareStartedAt){screenShareElapsedMs+=Date.now()-screenShareStartedAt;screenShareStartedAt=0;}pitchScreenSource=null;pitchScreenStream=null;toast('Screen sharing stopped. The camera recording continues.');};
    } catch { pitchScreenStream?.getTracks().forEach(track=>track.stop());pitchScreenStream=null;pitchScreenSource=null;toast('Screen sharing was cancelled or unavailable'); }
  };

  document.addEventListener('click', async event => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'generate-pitch-questions') {
      event.preventDefault();
      const submission = selectedSubmission();
      if (!submission) { toast('Save your project before generating questions'); return; }
      if (!$('#participant-consent')?.checked) { toast('AI processing consent is required'); return; }
      const button=event.target.closest('[data-action="generate-pitch-questions"]');if(button)button.disabled=true;
      try {
        await api(`/submissions/${submission.id}/ai-processing-consent`, { method:'POST', body:{consent:true} });
        const result=await api(`/submissions/${submission.id}/pitch-questions`, {method:'POST'});
        const host=$('#pitch-question-list');if(host)host.innerHTML=result.questions.map((q,i)=>`<div class="event-row"><div class="event-info"><b>${i+1}. ${esc(q.question)}</b><small>${esc(q.why)}</small></div></div>`).join('');
      } catch (error) { toast(error.message); }
      finally { if(button)button.disabled=false; }
    }
    if (action === 'ingest-evidence') {
      event.preventDefault();
      const submission = selectedSubmission();
      if (!submission) { toast('Save a project before indexing evidence'); return; }
      const consent = $('#ai-processing-consent')?.checked;
      if (!consent) { toast('Grant AI processing consent before indexing materials'); return; }
      try {
        await api(`/submissions/${submission.id}/ai-processing-consent`, { method: 'POST', body: { consent: true } });
        const result = await api(`/submissions/${submission.id}/ingest`, { method: 'POST' });
        toast(`Indexed ${result.chunks} evidence passages from ${result.sources.join(', ')}`);
      } catch (error) { toast(error.message); }
    }
    if (action === 'retry-transcription') {
      event.preventDefault();
      if (!pitchSessionId) { toast('No pitch session is available to transcribe'); return; }
      try {
        const result = await api(`/pitch-sessions/${pitchSessionId}/transcribe`, { method: 'POST' });
        $('#transcript-status').textContent = `Transcript ready · ${result.duration_seconds}s`;
        $('#transcript-text').textContent = result.transcript || 'No speech was detected.';
        const claimHost=$('#pitch-claims');if(claimHost)claimHost.innerHTML=result.claims?.length?`<h4>Claims extracted from the pitch</h4>${result.claims.map(c=>`<div class="event-row"><div class="event-info"><b>${esc(c.kind)} · ${esc(c.text)}</b><small>“${esc(c.quote)}”</small></div></div>`).join('')}`:'';
        setPitchStatus('Transcript ready'); toast('Pitch transcribed');
      } catch (error) { toast(error.message); }
    }
  });
})();
