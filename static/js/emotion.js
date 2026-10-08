// Optional, in-browser facial-expression estimates. Video frames never leave the browser.
(function () {
  const config = window.FIELDGLASS;
  if (!config) return;

  const MODEL_URL = 'https://justadudewhohacks.github.io/face-api.js/models';
  const DETECTION_INTERVAL_MS = 6000;
  const CONFIDENCE_THRESHOLD = 0.4;

  const enableBtn = document.getElementById('consent-enable');
  const continueBtn = document.getElementById('continue-without-monitoring');
  const privacyBtn = document.getElementById('review-privacy-details');
  const privacyDetails = document.getElementById('privacy-details');
  const videoEl = document.getElementById('webcam-preview');
  const titleEl = document.getElementById('consent-title');
  const subtitleEl = document.getElementById('consent-subtitle');
  const statusEl = document.getElementById('monitoring-status');

  let stream = null;
  let detectionTimer = null;
  let modelsLoaded = false;
  let detecting = false;

  function getCookie(name) {
    const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match[2]) : null;
  }

  async function loadModels() {
    if (modelsLoaded) return;
    if (!window.faceapi) throw new Error('Expression analysis service is unavailable.');
    await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
    await faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL);
    modelsLoaded = true;
  }

  async function startWebcam() {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 } });
    videoEl.srcObject = stream;
    videoEl.style.display = 'block';
    await videoEl.play();
  }

  function stopWebcam() {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
    videoEl.style.display = 'none';
    videoEl.srcObject = null;
  }

  async function saveConsent(active) {
    const response = await fetch(config.toggleConsentUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({ active }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not update monitoring consent.');
    config.consentActive = data.active;
  }

  function setStatus(message) {
    if (statusEl) statusEl.textContent = message;
  }

  function topExpression(expressions) {
    let bestLabel = 'uncertain';
    let bestScore = 0;
    Object.entries(expressions).forEach(([label, score]) => {
      if (score > bestScore) {
        bestScore = score;
        bestLabel = label;
      }
    });
    if (bestScore < CONFIDENCE_THRESHOLD) {
      return { label: 'low_confidence', confidence: bestScore };
    }
    const labels = {
      neutral: 'neutral_steady',
      happy: 'positive_expression',
      sad: 'negative_expression',
      angry: 'negative_expression',
      fearful: 'negative_expression',
      disgusted: 'negative_expression',
      surprised: 'surprise_like',
    };
    return { label: labels[bestLabel] || 'uncertain', confidence: bestScore };
  }

  async function detectOnce() {
    if (!modelsLoaded || !stream || detecting) return;
    detecting = true;
    try {
      const options = new faceapi.TinyFaceDetectorOptions({ inputSize: 224 });
      const result = await faceapi.detectSingleFace(videoEl, options).withFaceExpressions();
      const payload = result
        ? topExpression(result.expressions)
        : { label: 'no_face', confidence: 0 };

      const response = await fetch(config.recordEmotionUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({
          session_id: config.sessionId,
          label: payload.label,
          confidence: payload.confidence,
        }),
      });
      if (!response.ok) {
        setStatus('Signal update unavailable. Your class can continue without monitoring.');
        return;
      }
      const confidence = Math.round(payload.confidence * 100);
      setStatus(payload.label === 'no_face'
        ? 'Observed Data: no face detected. No expression estimate was made.'
        : `AI Interpretation: ${payload.label.replaceAll('_', ' ')} (${confidence}% confidence). Estimates do not prove internal feelings.`);
    } catch (_error) {
      setStatus('Expression analysis is unavailable. Your class can continue without monitoring.');
      if (detectionTimer) clearInterval(detectionTimer);
      detectionTimer = null;
      stopWebcam();
      try {
        await saveConsent(false);
      } catch (_consentError) {
        // Camera is stopped locally even if the network is unavailable.
      }
      config.consentActive = false;
      updateUI(false);
    } finally {
      detecting = false;
    }
  }

  async function enableMonitoring() {
    try {
      setStatus('Requesting camera permission. You can continue without monitoring.');
      await startWebcam();
      setStatus('Loading the optional expression analysis service.');
      await loadModels();
      await saveConsent(true);
      updateUI(true);
      setStatus('Camera is on. Expression patterns are estimates, not proof of internal feelings.');
      await detectOnce();
      detectionTimer = setInterval(detectOnce, DETECTION_INTERVAL_MS);
    } catch (error) {
      if (detectionTimer) clearInterval(detectionTimer);
      detectionTimer = null;
      stopWebcam();
      try {
        await saveConsent(false);
      } catch (_consentError) {
        // Camera is stopped locally even if the network is unavailable.
      }
      config.consentActive = false;
      updateUI(false);
      if (error && error.name === 'NotAllowedError') {
        setStatus('Camera permission denied. You can continue using the classroom without facial-expression monitoring.');
      } else if (error && error.name === 'NotFoundError') {
        setStatus('Camera unavailable. You can continue using the classroom without facial-expression monitoring.');
      } else {
        setStatus('Monitoring is unavailable. You can continue using the classroom without it.');
      }
    }
  }

  async function disableMonitoring() {
    if (detectionTimer) clearInterval(detectionTimer);
    detectionTimer = null;
    stopWebcam();
    config.consentActive = false;
    updateUI(false);
    try {
      await saveConsent(false);
      setStatus('Monitoring disabled. You can continue using the classroom without it.');
    } catch (_error) {
      setStatus('Camera stopped on this device, but the consent update could not reach the server.');
    }
  }

  function updateUI(active) {
    if (titleEl) titleEl.textContent = active ? 'Camera monitoring is on' : 'Optional facial-expression estimates';
    if (subtitleEl) subtitleEl.textContent = active
      ? 'Camera frames are processed in this browser and are never recorded or uploaded.'
      : 'Camera monitoring is off. You can use the classroom fully without it.';
    if (enableBtn) {
      enableBtn.disabled = active;
      enableBtn.textContent = active ? 'Monitoring Enabled' : 'I Consent & Enable Monitoring';
    }
    if (continueBtn) continueBtn.textContent = active ? 'Pause Monitoring' : 'Continue Without Monitoring';
  }

  if (enableBtn && continueBtn) {
    enableBtn.addEventListener('click', enableMonitoring);
    continueBtn.addEventListener('click', disableMonitoring);
  }
  if (privacyBtn && privacyDetails) {
    privacyBtn.addEventListener('click', () => {
      const expanded = privacyBtn.getAttribute('aria-expanded') === 'true';
      privacyBtn.setAttribute('aria-expanded', String(!expanded));
      privacyDetails.hidden = expanded;
    });
  }

  updateUI(false);
})();
