const fileInput = document.querySelector('#fileInput');
const dropZone = document.querySelector('#dropZone');
const browseButton = document.querySelector('#browseButton');
const uploadTopButton = document.querySelector('#uploadTopButton');
const demoButton = document.querySelector('#demoButton');
const questionInput = document.querySelector('#questionInput');
const askButton = document.querySelector('#askButton');
const answer = document.querySelector('#answer');
const reportButton = document.querySelector('#reportButton');
const addUserButton = document.querySelector('#addUserButton');
const userForm = document.querySelector('#userForm');
const userTable = document.querySelector('.user-table');

function showUploadState(fileName) {
  const title = dropZone.querySelector('h3');
  const description = dropZone.querySelector('p');
  title.textContent = 'Log ready for analysis';
  description.innerHTML = `<strong>${fileName}</strong> · telemetry mapping will begin automatically`;
  dropZone.classList.add('ready');
  demoButton.textContent = 'Analyze log  ↗';
}

function analyzeLog() {
  const title = dropZone.querySelector('h3');
  const description = dropZone.querySelector('p');
  title.textContent = 'Analysis complete';
  description.textContent = 'FL-249 · 18,420 telemetry points mapped · 2 anomalies found';
  demoButton.textContent = 'View analysis  →';
  dropZone.classList.remove('ready');
  document.querySelector('#anomalies').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function askAssistant(question) {
  const cleanQuestion = question.trim();
  if (!cleanQuestion) return;
  questionInput.value = cleanQuestion;
  answer.hidden = false;
  answer.innerHTML = '<strong>Hoverin DroneOps Assistant</strong> is checking the flight evidence...';
  window.setTimeout(() => {
    answer.innerHTML = `<strong>Evidence-based answer:</strong> ${cleanQuestion} The latest telemetry shows a stable flight profile overall. I found 2 relevant signals in FL-248: motor temperature peaked at 78°C for 42 seconds while load rose to 86%, then returned to baseline. This is flagged for inspection, not an immediate grounding. <span style="color:#879b9b">Sources: FL-248 telemetry · maintenance history · anomaly model v2.8</span>`;
  }, 420);
}

browseButton.addEventListener('click', () => fileInput.click());
uploadTopButton.addEventListener('click', () => { dropZone.scrollIntoView({ behavior: 'smooth', block: 'center' }); fileInput.click(); });
fileInput.addEventListener('change', (event) => { const [file] = event.target.files; if (file) showUploadState(file.name); });
demoButton.addEventListener('click', analyzeLog);
['dragenter', 'dragover'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.add('dragging'); }));
['dragleave', 'drop'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.remove('dragging'); }));
dropZone.addEventListener('drop', (event) => { const [file] = event.dataTransfer.files; if (file) showUploadState(file.name); });
askButton.addEventListener('click', () => askAssistant(questionInput.value));
questionInput.addEventListener('keydown', (event) => { if (event.key === 'Enter') askAssistant(questionInput.value); });
document.querySelectorAll('[data-question]').forEach((button) => button.addEventListener('click', () => askAssistant(button.dataset.question)));
reportButton.addEventListener('click', () => {
  const report = `HOVERIN DRONEOPS AI FLIGHT BRIEFING\nGenerated: ${new Date().toLocaleDateString()}\n\nFleet health: 94%\nFlights analyzed: 248\nAnomalies detected: 17\n\nPriority finding\nFL-248 motor temperature peaked at 78°C for 42 seconds while load rose to 86%. Recommendation: inspect motor assembly before next high-load flight.\n\nSources: FL-248 telemetry, maintenance history, anomaly model v2.8`;
  const blob = new Blob([report], { type: 'text/plain' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'hoverin-droneops-flight-briefing.txt';
  link.click();
  URL.revokeObjectURL(link.href);
  reportButton.innerHTML = 'Report downloaded <span>✓</span>';
});

addUserButton.addEventListener('click', () => {
  userForm.hidden = !userForm.hidden;
  addUserButton.textContent = userForm.hidden ? '+ Add user' : 'Close form';
  if (!userForm.hidden) userForm.querySelector('input').focus();
});

userForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const name = document.querySelector('#userName').value.trim();
  const email = document.querySelector('#userEmail').value.trim();
  const role = document.querySelector('#userRole').value;
  const initials = name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase();
  const row = document.createElement('div');
  row.className = 'user-row-item';
  row.innerHTML = `<span class="member-cell"><span class="avatar member-new">${initials}</span><span><strong>${name}</strong><small>${email}</small></span></span><span>${role}</span><span class="status-chip warning"><i></i> Pending</span><button class="row-arrow" aria-label="More options for ${name}">•••</button>`;
  userTable.appendChild(row);
  userForm.reset();
  userForm.hidden = true;
  addUserButton.textContent = '+ Add user';
});
