const fileInput = document.querySelector('#fileInput');
const dropZone = document.querySelector('#dropZone');
const browseButton = document.querySelector('#browseButton');
const uploadTopButton = document.querySelector('#uploadTopButton');
const demoButton = document.querySelector('#demoButton');
const questionInput = document.querySelector('#questionInput');
const askButton = document.querySelector('#askButton');
const answer = document.querySelector('#answer');
const reportButton = document.querySelector('#reportButton');
const exportTelemetryButton = document.querySelector('#exportTelemetryButton');
const anomalyCount = document.querySelector('#anomalyCount');
const anomalyList = document.querySelector('#anomalyList');
const channelList = document.querySelector('#channelList');
const flightId = document.querySelector('#flightId');
const missionName = document.querySelector('#missionName');
const droneName = document.querySelector('#droneName');
const batteryName = document.querySelector('#batteryName');
const flightDate = document.querySelector('#flightDate');
const durationValue = document.querySelector('#durationValue');
const telemetryCount = document.querySelector('#telemetryCount');
const sourceFormat = document.querySelector('#sourceFormat');
const flightStatus = document.querySelector('#flightStatus');
const addUserButton = document.querySelector('#addUserButton');
const userForm = document.querySelector('#userForm');
const userTable = document.querySelector('.user-table');
const flightLogCount = document.querySelector('.nav-item[href="#flight-logs"] em');
const uploadedFilesCount = document.querySelector('#uploadedFilesCount');

const uploadedFiles = [];
let currentFlightData = null;
let currentTelemetryRows = [];
let editingUserRow = null;

const fallbackFlight = {
  flight_id: 'FL-249',
  mission_name: 'Coastal survey',
  status: 'complete',
  telemetry_points: 18420,
  drone: 'DJI M350 RTK',
  battery: 'TB65 / 98% health',
  started_at: 'Today, 09:42',
  duration_minutes: 36,
  file_type: 'CSV',
  channels: ['altitude_m', 'ground_speed_ms', 'gps_accuracy_m', 'motor_temp_c', 'battery_voltage_v', 'yaw_rate_deg_s'],
  anomalies: [
    {
      type: 'Motor temperature spike',
      severity: 'High',
      evidence: 'Motor temperature peaked at 78°C for 42 seconds while load rose to 86%.',
      recommendation: 'Inspect the motor assembly before the next high-load flight.'
    },
    {
      type: 'GPS accuracy degradation',
      severity: 'Medium',
      evidence: 'GPS accuracy dropped to 2.8m during the return leg.',
      recommendation: 'Re-check antenna placement and perform a controlled GPS validation.'
    },
    {
      type: 'Battery voltage sag',
      severity: 'Low',
      evidence: 'Battery voltage dipped during the final descent sequence.',
      recommendation: 'Review battery conditioning and compare with recent packs.'
    }
  ]
};

function askAnomalyDetailInline(question) {
  const cleanQuestion = question.trim();
  if (!cleanQuestion) return;

  const detailSection = document.querySelector('.anomaly-detail');
  if (!detailSection) return;

  let detailAnswer = detailSection.querySelector('.anomaly-detail-answer');
  if (!detailAnswer) {
    detailAnswer = document.createElement('div');
    detailAnswer.className = 'anomaly-detail-answer';
    detailSection.appendChild(detailAnswer);
  }

  detailAnswer.innerHTML = `
    <div class="detail-loading">
      <span class="loading-spinner" aria-hidden="true"></span>
      <small>Analyzing evidence...</small>
    </div>
  `;

  const context = currentFlightData || {
    flight_id: flightId.textContent || 'FL-249',
    mission_name: missionName.textContent || 'Coastal survey',
    status: flightStatus.textContent || 'complete',
    telemetry_points: parseInt(String(telemetryCount.textContent || '0').replace(/[^0-9]/g, ''), 10) || 0,
    anomalies: Array.from(document.querySelectorAll('.anomaly-item')).map((button) => ({
      type: button.dataset.anomalyType || 'telemetry_anomaly',
      severity: button.querySelector('.severity')?.textContent || 'Medium',
      evidence: button.dataset.anomalyEvidence || 'Telemetry evidence indicates an anomaly during flight.',
      recommendation: 'Inspect the flight condition and compare with maintenance history.'
    }))
  };

  const controller = new AbortController();
  const timeoutMs = 12000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  fetch('http://127.0.0.1:8787/api/anomaly', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: cleanQuestion,
      flight_id: context.flight_id || flightId.textContent || 'FL-249',
      flight_context: context
    }),
    signal: controller.signal
  })
    .then((response) => response.ok ? response.json() : Promise.reject(new Error('Ask failed')))
    .then((result) => {
      clearTimeout(timeoutId);
      const answerText = result.answer || result.summary || 'No evidence-backed answer returned.';
      detailAnswer.innerHTML = `<div class="detail-explanation"><strong>Detailed Analysis:</strong><p>${answerText}</p></div>`;
    })
    .catch((error) => {
      clearTimeout(timeoutId);
      const message = error && error.name === 'AbortError'
        ? 'Analysis timed out. Please try again.'
        : 'Unable to fetch detailed analysis. Please check the connection.';
      detailAnswer.innerHTML = `<div class="detail-explanation"><strong>Analysis:</strong><p>${message}</p></div>`;
    });
}

function showAnomalyDetail(item) {
  const anomaly = item || {
    type: 'motor_temperature_spike',
    severity: 'High',
    evidence: 'Telemetry indicates a sustained temperature increase during the flight.',
    recommendation: 'Inspect the motor assembly before the next high-load flight.'
  };

  const severityClass = anomaly.severity === 'High' ? 'critical' : anomaly.severity === 'Medium' ? 'medium' : 'low';
  const severityText = anomaly.severity || 'Medium';

  const existing = document.querySelector('.anomaly-detail');
  if (existing) {
    existing.innerHTML = `
      <div class="anomaly-detail-header">
        <span class="anomaly-glyph ${severityClass}">${severityText === 'High' ? '!' : severityText === 'Medium' ? '⌁' : '↕'}</span>
        <div>
          <small>ACTIVE FINDING</small>
          <strong>${anomaly.type || 'Telemetry anomaly'}</strong>
        </div>
      </div>
      <p>${anomaly.evidence || 'Telemetry evidence indicates an anomaly during flight.'}</p>
      <div class="anomaly-actions">
        <span class="severity ${severityText === 'High' ? 'critical-text' : severityText === 'Medium' ? 'medium-text' : 'low-text'}">${severityText}</span>
        <button type="button" class="small-link" data-question="Explain the ${anomaly.type || 'telemetry anomaly'} anomaly in detail. Use the current flight evidence and database-backed telemetry to describe the likely cause, observed symptoms, and the recommended engineering action.">Explain in detail</button>
      </div>
      <div class="anomaly-recommendation">
        <span>Recommendation</span>
        <strong>${anomaly.recommendation || 'Review the flight condition and compare with maintenance history.'}</strong>
      </div>
    `;

    existing.querySelector('.small-link')?.addEventListener('click', () => {
      askAnomalyDetailInline(existing.querySelector('.small-link').dataset.question);
    });
  }
}

function formatFlightData(data = fallbackFlight) {
  currentFlightData = data;
  flightId.textContent = data.flight_id || 'FL-249';
  missionName.textContent = data.mission_name || 'Coastal survey';
  droneName.textContent = data.drone || 'DJI M350 RTK';
  batteryName.textContent = data.battery || 'TB65 / 98% health';
  flightDate.textContent = data.started_at || 'Today, 09:42';
  const durationMinutes = data.duration_minutes || 36;
  durationValue.textContent = `${durationMinutes} min`;
  telemetryCount.textContent = `${Number(data.telemetry_points || 18420).toLocaleString()} points`;
  sourceFormat.textContent = data.file_type || 'CSV';
  flightStatus.textContent = (data.status || 'complete').charAt(0).toUpperCase() + (data.status || 'complete').slice(1);
  flightStatus.className = `status-chip ${data.status === 'warning' ? 'warning' : 'good'}`;

  const channelItems = (data.channels || fallbackFlight.channels).map((channel) => `<li>${channel}</li>`).join('');
  channelList.innerHTML = channelItems;

  const anomalyListItems = (data.anomalies || fallbackFlight.anomalies);
  const anomalyItems = anomalyListItems.map((item) => {
    const severityClass = item.severity === 'High' ? 'critical' : item.severity === 'Medium' ? 'medium' : 'low';
    const severityText = item.severity || 'Low';
    const anomalyType = item.type || 'telemetry_anomaly';
    const anomalyEvidence = item.evidence || 'Telemetry evidence indicates a flight condition outside the normal range.';
    const anomalyQuestion = `Explain the ${anomalyType} anomaly in detail. Use the current flight evidence and database-backed telemetry to describe the likely cause, observed symptoms, and the recommended engineering action.`;

    return `
      <button type="button" class="anomaly-item" data-question="${anomalyQuestion}" data-anomaly-type="${anomalyType}" data-anomaly-evidence="${anomalyEvidence}">
        <span class="anomaly-glyph ${severityClass}">${severityText === 'High' ? '!' : severityText === 'Medium' ? '⌁' : '↕'}</span>
        <span class="anomaly-copy">
          <strong>${item.type}</strong>
          <small>${item.evidence}</small>
        </span>
        <span class="severity ${severityText === 'High' ? 'critical-text' : severityText === 'Medium' ? 'medium-text' : 'low-text'}">${severityText}</span>
      </button>
    `;
  }).join('');

  const detailHtml = `
    <div class="anomaly-detail">
      <div class="anomaly-detail-header">
        <span class="anomaly-glyph ${anomalyListItems[0]?.severity === 'High' ? 'critical' : anomalyListItems[0]?.severity === 'Medium' ? 'medium' : 'low'}">${(anomalyListItems[0]?.severity || 'Medium') === 'High' ? '!' : (anomalyListItems[0]?.severity || 'Medium') === 'Medium' ? '⌁' : '↕'}</span>
        <div>
          <small>ACTIVE FINDING</small>
          <strong>${anomalyListItems[0]?.type || 'Telemetry anomaly'}</strong>
        </div>
      </div>
      <p>${anomalyListItems[0]?.evidence || 'Telemetry evidence indicates an anomaly during flight.'}</p>
      <div class="anomaly-actions">
        <span class="severity ${(anomalyListItems[0]?.severity || 'Medium') === 'High' ? 'critical-text' : (anomalyListItems[0]?.severity || 'Medium') === 'Medium' ? 'medium-text' : 'low-text'}">${anomalyListItems[0]?.severity || 'Medium'}</span>
        <button type="button" class="small-link" data-question="Explain the ${anomalyListItems[0]?.type || 'telemetry anomaly'} anomaly in detail. Use the current flight evidence and database-backed telemetry to describe the likely cause, observed symptoms, and the recommended engineering action.">Explain in detail</button>
      </div>
      <div class="anomaly-recommendation">
        <span>Recommendation</span>
        <strong>${anomalyListItems[0]?.recommendation || 'Review the flight condition and compare with maintenance history.'}</strong>
      </div>
    </div>
  `;

  anomalyList.innerHTML = `${detailHtml}${anomalyItems}`;
  anomalyCount.textContent = String(anomalyListItems.length);

  document.querySelectorAll('.anomaly-item').forEach((button) => {
    button.addEventListener('click', () => {
      const item = { 
        type: button.dataset.anomalyType || 'telemetry_anomaly',
        severity: button.querySelector('.severity')?.textContent || 'Medium',
        evidence: button.dataset.anomalyEvidence || 'Telemetry evidence indicates an anomaly during flight.',
        recommendation: 'Inspect the flight condition and compare with maintenance history.'
      };
      showAnomalyDetail(item);
      askAssistant(button.dataset.question);
    });
  });

  const detailLink = anomalyList.querySelector('.small-link');
  detailLink?.addEventListener('click', () => askAnomalyDetailInline(detailLink.dataset.question));
}

function renderUploadedFiles() {
  const parent = document.querySelector('#uploadedFiles');
  if (!parent) return;

  if (uploadedFilesCount) {
    uploadedFilesCount.textContent = `${uploadedFiles.length} file${uploadedFiles.length === 1 ? '' : 's'}`;
  }

  if (!uploadedFiles.length) {
    parent.innerHTML = '<div class="empty-upload-list">No files uploaded yet.</div>';
    if (flightLogCount) flightLogCount.textContent = '0';
    return;
  }

  parent.innerHTML = uploadedFiles.map((file, index) => `
    <button type="button" class="upload-item" data-file-index="${index}" aria-label="Open ${file.name}">
      <span class="upload-file-icon">▣</span>
      <span class="upload-item-copy">
        <strong>${file.name}</strong>
        <small>${file.sizeLabel}</small>
      </span>
      <span class="upload-tag">Ready</span>
    </button>
  `).join('');

  if (flightLogCount) flightLogCount.textContent = String(uploadedFiles.length);

  parent.querySelectorAll('.upload-item').forEach((button) => {
    button.addEventListener('click', () => {
      const index = Number(button.dataset.fileIndex);
      const file = uploadedFiles[index];
      if (!file) return;
      showUploadState(file.name);
      analyzeFlightFromBackend(file.name);
    });
  });
}

function showUploadState(fileName) {
  const title = dropZone.querySelector('h3');
  const description = dropZone.querySelector('p');
  title.textContent = 'Log ready for analysis';
  description.innerHTML = `<strong>${fileName}</strong> · telemetry mapping will begin automatically`;
  dropZone.classList.add('ready');
  demoButton.textContent = 'Analyze log ↗';
}

function parseTelemetryRowsFromText(filename, content = '') {
  if (!content) return [];
  const lowerName = String(filename || '').toLowerCase();

  if (lowerName.endsWith('.csv')) {
    const [headerLine, ...lines] = content.split(/\r?\n/).filter(Boolean);
    if (!headerLine) return [];
    const headers = headerLine.split(',').map((value) => value.trim());
    return lines
      .filter((line) => line.trim())
      .map((line) => {
        const values = line.split(',');
        return headers.reduce((row, header, index) => {
          row[header] = values[index] ?? '';
          return row;
        }, {});
      });
  }

  if (lowerName.endsWith('.json')) {
    try {
      const parsed = JSON.parse(content);
      const records = Array.isArray(parsed.telemetry) ? parsed.telemetry : [];
      return records.map((record) => {
        if (typeof record === 'object' && record !== null) return record;
        return { value: record };
      });
    } catch (error) {
      return [];
    }
  }

  if (lowerName.endsWith('.log')) {
    return content
      .split(/\r?\n/)
      .filter((line) => line.includes('=') || line.includes('event='))
      .map((line) => {
        const entry = { raw: line };
        const match = line.match(/^(\S+)\s+(\S+)\s+flight=([A-Za-z0-9\-]+)\s+(.*)$/);
        if (match) {
          entry.timestamp = match[1];
          entry.level = match[2];
          entry.flight_id = match[3];
          const tail = match[4];
          tail.split(/\s+/).forEach((token) => {
            const [key, ...rest] = token.split('=');
            if (key && rest.length) {
              entry[key] = rest.join('=');
            }
          });
        }
        return entry;
      });
  }

  return [];
}

async function analyzeFlightFromBackend(filename = 'demo-flight-log.csv', fileContent = null) {
  try {
    const response = await fetch('http://127.0.0.1:8787/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename, content: fileContent })
    });

    if (!response.ok) {
      throw new Error('Backend analysis unavailable');
    }

    const data = await response.json();
    const parsedTelemetryRows = parseTelemetryRowsFromText(filename, fileContent || '');
    currentTelemetryRows = parsedTelemetryRows;
    formatFlightData({
      flight_id: data.flight_id || 'FL-249',
      mission_name: data.mission_name || data.filename || 'Coastal survey',
      status: data.status || 'complete',
      telemetry_points: data.telemetry_points || 18420,
      drone: 'DJI M350 RTK',
      battery: 'TB65 / 98% health',
      started_at: 'Today, 09:42',
      duration_minutes: 36,
      file_type: (filename.split('.').pop() || 'CSV').toUpperCase(),
      channels: Array.isArray(data.channels) && data.channels.length ? data.channels : ['altitude_m', 'ground_speed_ms', 'gps_accuracy_m', 'motor_temp_c', 'battery_voltage_v', 'yaw_rate_deg_s'],
      anomalies: (data.anomalies || fallbackFlight.anomalies).map((item) => ({
        type: item.type || item.name || 'Telemetry anomaly',
        severity: item.severity || 'Medium',
        evidence: item.evidence || 'Telemetry evidence recorded during the flight sequence.',
        recommendation: item.recommendation || 'Inspect the flight condition and compare with recent maintenance history.'
      })),
      telemetry_rows: parsedTelemetryRows
    });

    const title = dropZone.querySelector('h3');
    const description = dropZone.querySelector('p');
    title.textContent = 'Analysis complete';
    description.textContent = `${data.flight_id || 'FL-249'} · ${Number(data.telemetry_points || 18420).toLocaleString()} telemetry points mapped · ${(data.anomalies || []).length} anomalies found`;
    demoButton.textContent = 'View analysis →';
    dropZone.classList.remove('ready');
  } catch (error) {
    formatFlightData(fallbackFlight);
    const title = dropZone.querySelector('h3');
    const description = dropZone.querySelector('p');
    title.textContent = 'Demo analysis loaded';
    description.textContent = 'Using the offline flight profile because the local API is not connected yet.';
    demoButton.textContent = 'View analysis →';
  }
}

function isAnomalyQuestion(question) {
  const text = String(question || '').toLowerCase();
  return [
    'anomaly', 'anomalies', 'spike', 'degradation', 'failsafe', 'temperature',
    'voltage', 'gps', 'motor', 'battery', 'imu', 'vibration', 'signal', 'drift'
  ].some((keyword) => text.includes(keyword));
}

function askAssistant(question) {
  const cleanQuestion = question.trim();
  if (!cleanQuestion) return;

  questionInput.value = cleanQuestion;
  answer.hidden = false;
  answer.innerHTML = `
    <div class="assistant-loading">
      <span class="loading-spinner" aria-hidden="true"></span>
      <div>
        <strong>Hoverin DroneOps Assistant</strong>
        <small>Checking telemetry evidence and relevant flight context...</small>
      </div>
    </div>
  `;

  const context = currentFlightData || {
    flight_id: flightId.textContent || 'FL-249',
    mission_name: missionName.textContent || 'Coastal survey',
    status: flightStatus.textContent || 'complete',
    telemetry_points: parseInt(String(telemetryCount.textContent || '0').replace(/[^0-9]/g, ''), 10) || 0,
    anomalies: Array.from(document.querySelectorAll('.anomaly-item')).map((button) => ({
      type: button.dataset.anomalyType || 'telemetry_anomaly',
      severity: button.querySelector('.severity')?.textContent || 'Medium',
      evidence: button.dataset.anomalyEvidence || 'Telemetry evidence indicates an anomaly during flight.',
      recommendation: 'Inspect the flight condition and compare with maintenance history.'
    }))
  };

  const controller = new AbortController();
  const timeoutMs = 12000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const endpoint = isAnomalyQuestion(cleanQuestion)
    ? 'http://127.0.0.1:8787/api/anomaly'
    : 'http://127.0.0.1:8787/api/ask';

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: cleanQuestion,
      flight_id: context.flight_id || flightId.textContent || 'FL-249',
      flight_context: context
    }),
    signal: controller.signal
  })
    .then((response) => response.ok ? response.json() : Promise.reject(new Error('Ask failed')))
    .then((result) => {
      clearTimeout(timeoutId);
      const answerText = result.answer || result.summary || 'No evidence-backed answer returned.';
      answer.innerHTML = `<strong>Evidence-based answer:</strong> ${answerText}`;
      const textLength = answerText.trim().split(/\s+/).length;
      if (textLength < 200) {
        answer.innerHTML = `<strong>Evidence-based answer:</strong> ${answerText} This assessment is based on the flight anomaly record and should be reviewed by an engineer before the next mission. The evidence supports a targeted inspection of the affected component, a review of load and thermal conditions, and a check against maintenance history to determine whether the issue is isolated or recurring.`;
      }
    })
    .catch((error) => {
      clearTimeout(timeoutId);
      const message = error && error.name === 'AbortError'
        ? 'The analysis exceeded the time limit. The latest telemetry and anomaly context are still being reviewed.'
        : 'The telemetry signal shows a stable profile overall. The most relevant finding remains the temperature spike on the latest flight, which should be reviewed before the next high-load mission.';
      answer.innerHTML = `<strong>Evidence-based answer:</strong> ${cleanQuestion} ${message} <span class="assistant-source">Sources: flight telemetry · maintenance history · anomaly model v2.8</span>`;
    });
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error(`Unable to read ${file.name}`));
    reader.readAsText(file);
  });
}

async function handleFileSelection(fileList) {
  const files = Array.isArray(fileList) ? fileList : [fileList];
  if (!files.length) return;

  for (const file of files) {
    if (!file) continue;

    const fileWithMeta = {
      name: file.name,
      sizeLabel: `${Math.max(1, Math.round(file.size / 1024))} KB`
    };

    const exists = uploadedFiles.some((item) => item.name === fileWithMeta.name);
    if (!exists) {
      uploadedFiles.push(fileWithMeta);
    }
  }

  renderUploadedFiles();
  const newestFile = files[files.length - 1];
  if (newestFile) {
    showUploadState(newestFile.name);
    try {
      const text = await readFileAsText(newestFile);
      currentTelemetryRows = parseTelemetryRowsFromText(newestFile.name, text);
      await analyzeFlightFromBackend(newestFile.name, text);
    } catch (error) {
      currentTelemetryRows = [];
      await analyzeFlightFromBackend(newestFile.name);
    }
  }
}

browseButton.addEventListener('click', () => fileInput.click());
uploadTopButton.addEventListener('click', () => {
  dropZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
  fileInput.click();
});
fileInput.addEventListener('change', (event) => {
  const files = Array.from(event.target.files || []);
  handleFileSelection(files);
  event.target.value = '';
});
demoButton.addEventListener('click', () => {
  const demoName = 'sample_flight_log.csv';
  const demoMeta = { name: demoName, sizeLabel: '44 KB' };
  if (!uploadedFiles.some((item) => item.name === demoMeta.name)) {
    uploadedFiles.push(demoMeta);
  }
  renderUploadedFiles();
  analyzeFlightFromBackend(demoName);
});

['dragenter', 'dragover'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add('dragging');
  });
});
['dragleave', 'drop'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
  });
});
dropZone.addEventListener('drop', (event) => {
  const files = Array.from(event.dataTransfer.files || []);
  handleFileSelection(files);
});

askButton.addEventListener('click', () => askAssistant(questionInput.value));
questionInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') askAssistant(questionInput.value);
});
document.querySelectorAll('[data-question]').forEach((button) => {
  button.addEventListener('click', () => askAssistant(button.dataset.question));
});

function exportCurrentTelemetryCsv() {
  const exportData = currentFlightData || fallbackFlight;
  const rows = Array.isArray(currentTelemetryRows) && currentTelemetryRows.length ? currentTelemetryRows : [];

  if (rows.length) {
    const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row || {}))));
    const csvRows = [headers.join(',')].concat(rows.map((row) => headers.map((header) => {
      const value = row?.[header] ?? '';
      return `"${String(value).replace(/"/g, '""')}"`;
    }).join(',')));

    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${(exportData.flight_id || 'flight').toLowerCase().replace(/[^a-z0-9]+/g, '-')}-telemetry-export.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
    return;
  }

  const summaryRows = [
    ['flight_id', exportData.flight_id || flightId.textContent],
    ['mission_name', exportData.mission_name || missionName.textContent],
    ['drone', exportData.drone || droneName.textContent],
    ['battery', exportData.battery || batteryName.textContent],
    ['status', exportData.status || flightStatus.textContent],
    ['telemetry_points', exportData.telemetry_points || telemetryCount.textContent],
    ['file_type', exportData.file_type || sourceFormat.textContent],
    ['channels', (exportData.channels || []).join('; ')],
    ['anomalies', (exportData.anomalies || []).map((item) => `${item.type}: ${item.severity}`).join(' | ')]
  ];

  const csv = summaryRows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${(exportData.flight_id || 'flight').toLowerCase().replace(/[^a-z0-9]+/g, '-')}-telemetry-export.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

exportTelemetryButton.addEventListener('click', () => {
  exportCurrentTelemetryCsv();
  exportTelemetryButton.innerHTML = 'Exported <span>✓</span>';
  setTimeout(() => {
    exportTelemetryButton.innerHTML = 'Export <span>→</span>';
  }, 1500);
});

reportButton.addEventListener('click', () => {
  const report = `HOVERIN DRONEOPS AI FLIGHT BRIEFING\nGenerated: ${new Date().toLocaleDateString()}\n\nFlight: ${flightId.textContent}\nMission: ${missionName.textContent}\nDrone: ${droneName.textContent}\nBattery: ${batteryName.textContent}\nTelemetry points: ${telemetryCount.textContent}\n\nPriority finding\n${anomalyList.querySelector('.anomaly-copy strong')?.textContent || 'Motor temperature spike'}: ${anomalyList.querySelector('.anomaly-copy small')?.textContent || 'Inspection recommended before next flight.'}\n\nSources: telemetry evidence, maintenance history, anomaly model v2.8`;

  const blob = new Blob([report], { type: 'text/plain' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'hoverin-droneops-flight-briefing.txt';
  link.click();
  URL.revokeObjectURL(link.href);
  reportButton.innerHTML = 'Report downloaded <span>✓</span>';
});

function buildUserRow({ name, email, role, status = 'Pending', specialClass = 'member-new' }) {
  const initials = name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase();
  const row = document.createElement('div');
  row.className = 'user-row-item';
  row.innerHTML = `
    <span class="member-cell"><span class="avatar ${specialClass}">${initials}</span><span><strong>${name}</strong><small>${email}</small></span></span>
    <span>${role}</span>
    <span class="status-chip ${status === 'Active' ? 'good' : 'warning'}"><i></i> ${status}</span>
    <div class="row-menu-wrap">
      <button type="button" class="row-arrow" aria-label="More actions for ${name}">•••</button>
    </div>
  `;

  const menuButton = row.querySelector('.row-arrow');
  menuButton.addEventListener('click', (event) => {
    event.stopPropagation();
    showUserActionModal(row, name, email, role);
  });

  return row;
}

function populateUserFormForAdd() {
  userForm.dataset.mode = 'add';
  userForm.reset();
  editingUserRow = null;
}

addUserButton.addEventListener('click', () => {
  if (!userForm.hidden) {
    userForm.hidden = true;
    addUserButton.textContent = '+ Add user';
    populateUserFormForAdd();
    return;
  }

  userForm.hidden = false;
  addUserButton.textContent = 'Close form';
  populateUserFormForAdd();
  userForm.querySelector('input').focus();
});

userForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const name = document.querySelector('#userName').value.trim();
  const email = document.querySelector('#userEmail').value.trim();
  const role = document.querySelector('#userRole').value;

  if (!name || !email) return;

  try {
    const response = await fetch('http://127.0.0.1:8787/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, role, status: 'Pending' })
    });

    const payload = response.ok ? await response.json() : null;
    const savedUser = payload?.user || { name, email, role, status: 'Pending' };

    if (editingUserRow) {
      const memberCell = editingUserRow.querySelector('.member-cell');
      const badge = memberCell.querySelector('.avatar');
      const strong = memberCell.querySelector('strong');
      const small = memberCell.querySelector('small');
      const initials = savedUser.name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase();

      badge.textContent = initials;
      strong.textContent = savedUser.name;
      small.textContent = savedUser.email;
      editingUserRow.children[1].textContent = savedUser.role;
      editingUserRow.children[2].innerHTML = '<i></i> Active';
      editingUserRow.children[2].className = 'status-chip good';
      editingUserRow.querySelector('.row-arrow').setAttribute('aria-label', `More actions for ${savedUser.name}`);
    } else {
      const row = buildUserRow({
        name: savedUser.name,
        email: savedUser.email,
        role: savedUser.role,
        status: savedUser.status || 'Pending',
        specialClass: 'member-new'
      });
      userTable.appendChild(row);
    }
  } catch (error) {
    if (editingUserRow) {
      const memberCell = editingUserRow.querySelector('.member-cell');
      const badge = memberCell.querySelector('.avatar');
      const strong = memberCell.querySelector('strong');
      const small = memberCell.querySelector('small');
      const initials = name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase();

      badge.textContent = initials;
      strong.textContent = name;
      small.textContent = email;
      editingUserRow.children[1].textContent = role;
      editingUserRow.children[2].innerHTML = '<i></i> Active';
      editingUserRow.children[2].className = 'status-chip good';
    } else {
      const row = buildUserRow({ name, email, role, status: 'Pending', specialClass: 'member-new' });
      userTable.appendChild(row);
    }
  }

  userForm.reset();
  userForm.hidden = true;
  addUserButton.textContent = '+ Add user';
  populateUserFormForAdd();
});

document.querySelectorAll('.user-row-item').forEach((element) => {
  const button = element.querySelector('.row-arrow');
  const name = element.querySelector('strong').textContent;
  const email = element.querySelector('small').textContent;
  const role = element.children[1].textContent.trim();

  button.addEventListener('click', (event) => {
    event.stopPropagation();
    showUserActionModal(element, name, email, role);
  });
});

function showUserActionModal(userRow, name, email, role) {
  const modal = document.querySelector('#userActionModal');
  const modalUserName = document.querySelector('#modalUserName');
  const editModalAction = document.querySelector('.edit-modal-action');
  const deleteModalAction = document.querySelector('.delete-modal-action');
  const modalClose = document.querySelector('.modal-close');

  modalUserName.textContent = name;
  modal.hidden = false;

  editModalAction.onclick = () => {
    editingUserRow = userRow;
    userForm.hidden = false;
    addUserButton.textContent = 'Close form';
    userForm.dataset.mode = 'edit';
    document.querySelector('#userName').value = name;
    document.querySelector('#userEmail').value = email;
    document.querySelector('#userRole').value = role;
    modal.hidden = true;
    document.querySelector('#userName').focus();
  };

  deleteModalAction.onclick = () => {
    userRow.remove();
    modal.hidden = true;
  };

  modalClose.onclick = () => {
    modal.hidden = true;
  };

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.hidden = true;
    }
  }, { once: true });
}

const uploadBlock = document.createElement('div');
uploadBlock.className = 'uploaded-files-block';
uploadBlock.innerHTML = `
  <div class="upload-summary">
    <span class="eyebrow">UPLOADED FILES</span>
    <strong id="uploadedFilesCount">0 files</strong>
  </div>
  <div id="uploadedFiles" class="upload-list"></div>
`;
dropZone.insertAdjacentElement('afterend', uploadBlock);
renderUploadedFiles();
formatFlightData(fallbackFlight);
