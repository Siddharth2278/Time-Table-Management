const sampleRows = [
  ['Monday', ['Data Structures', 'Dr. Mehta'], ['Discrete Mathematics', 'Prof. Rao'], ['Operating Systems', 'Dr. Khan'], ['BREAK', 'Lunch'], ['Computer Networks', 'Prof. Shah']],
  ['Tuesday', ['Database Systems', 'Dr. Iyer'], ['Computer Networks', 'Prof. Shah'], ['BREAK', 'Lunch'], ['Data Structures', 'Dr. Mehta'], ['Web Engineering', 'Prof. Das']],
  ['Wednesday', ['Operating Systems', 'Dr. Khan'], ['BREAK', 'Lunch'], ['Database Systems', 'Dr. Iyer'], ['Discrete Mathematics', 'Prof. Rao'], ['Data Structures Lab', 'Lab 02']],
  ['Thursday', ['Web Engineering', 'Prof. Das'], ['Operating Systems', 'Dr. Khan'], ['Data Structures', 'Dr. Mehta'], ['BREAK', 'Lunch'], ['Database Systems', 'Dr. Iyer']],
  ['Friday', ['Discrete Mathematics', 'Prof. Rao'], ['Computer Networks', 'Prof. Shah'], ['Web Engineering', 'Prof. Das'], ['BREAK', 'Lunch'], ['Project Studio', 'Academic block']]
];

const storageKeys = { profile: 'campusgrid.profile', format: 'campusgrid.format', timetable: 'campusgrid.timetable' };
const dialog = document.querySelector('#upload-dialog');
const fileInput = document.querySelector('#format-photo');
const confirmButton = document.querySelector('#confirm-upload');
const selectedFile = document.querySelector('#selected-file');
const referencePreview = document.querySelector('#reference-preview');
const resultSection = document.querySelector('#result-section');
let formatData = JSON.parse(localStorage.getItem(storageKeys.format) || 'null');
let selectedFileData = null;

function profileValues() {
  return {
    collegeName: document.querySelector('#college-name').value.trim(),
    department: document.querySelector('#department').value.trim(),
    affiliation: document.querySelector('#affiliation').value.trim(),
    academicYear: document.querySelector('#academic-year').value,
    officeEmail: document.querySelector('#office-email').value.trim(),
    workingDays: document.querySelector('#working-days').value,
  };
}

function renderTimetable(rows = sampleRows) {
  const body = document.querySelector('#timetable-body');
  body.innerHTML = rows.map(([day, ...cells]) => `<tr><td>${day}</td>${cells.map((cell) => {
    const [subject, teacher = ''] = Array.isArray(cell) ? cell : String(cell).split('\n');
    return subject === 'BREAK'
    ? `<td class="break-cell" contenteditable="true" spellcheck="false">${teacher}</td>`
    : `<td class="${subject.includes('Lab') ? 'lab-cell' : ''}" contenteditable="true" spellcheck="false"><span class="cell-subject">${subject}</span><span class="cell-teacher">${teacher}</span></td>`;
  }).join('')}</tr>`).join('');
}

function openUploadDialog() { dialog.showModal(); }
function closeUploadDialog() { dialog.close(); }

function showProfile(profile) {
  document.querySelector('#college-name').value = profile.collegeName || '';
  document.querySelector('#department').value = profile.department || '';
  document.querySelector('#affiliation').value = profile.affiliation || '';
  document.querySelector('#academic-year').value = profile.academicYear || '2026–27';
  document.querySelector('#office-email').value = profile.officeEmail || '';
  document.querySelector('#working-days').value = profile.workingDays || 'Monday–Friday';
  document.querySelector('.college-name').textContent = (profile.collegeName || 'YOUR COLLEGE').toUpperCase();
  document.querySelector('#timetable-title').textContent = profile.department || 'Your department';
  document.querySelector('#timetable-meta').textContent = `${document.querySelector('#semester').value} · ${profile.academicYear || '2026–27'}`;
}

function setProfileMode(saved) {
  document.querySelector('#profile-panel').classList.toggle('is-hidden', saved);
  document.querySelector('#timetable-setup').classList.toggle('is-hidden', !saved);
}

function updateFormatReference() {
  if (!formatData) return;
  referencePreview.classList.remove('empty');
  referencePreview.innerHTML = `<img src="${formatData.dataUrl}" alt="Saved timetable format reference">`;
  document.querySelector('#saved-format-name').textContent = formatData.name;
  document.querySelector('#reference-description').textContent = 'This saved photo will be reused for new timetables.';
}

function generateTimetable() {
  const profile = JSON.parse(localStorage.getItem(storageKeys.profile) || 'null');
  if (!profile) return showToast('Save the college profile before generating.');
  if (!formatData) return openUploadDialog();
  const semester = document.querySelector('#semester').value;
  const section = document.querySelector('#section').value.trim() || 'A';
  const saved = JSON.parse(localStorage.getItem(storageKeys.timetable) || 'null');
  document.querySelector('#timetable-title').textContent = profile.department;
  document.querySelector('#timetable-meta').textContent = `${semester} · Section ${section} · ${profile.academicYear}`;
  renderTimetable(saved?.rows || sampleRows);
  resultSection.classList.add('has-result');
  resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  showToast(saved ? 'Saved timetable reopened for editing.' : 'Timetable generated. You can edit each cell.');
}

document.querySelector('#save-profile-button').addEventListener('click', () => {
  const profile = profileValues();
  if (Object.values(profile).some((value) => !value)) return showToast('Complete every profile field first.');
  localStorage.setItem(storageKeys.profile, JSON.stringify(profile));
  showProfile(profile);
  setProfileMode(true);
  showToast('College profile saved on this PC.');
});

document.querySelector('#create-new-button').addEventListener('click', () => {
  const profile = JSON.parse(localStorage.getItem(storageKeys.profile) || 'null');
  if (!profile) return document.querySelector('#profile-panel').scrollIntoView({ behavior: 'smooth' });
  setProfileMode(true);
  document.querySelector('#timetable-setup').scrollIntoView({ behavior: 'smooth', block: 'center' });
  showToast('New timetable ready for this department.');
});
document.querySelector('#generate-button').addEventListener('click', generateTimetable);

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.addEventListener('load', () => {
    selectedFileData = { name: file.name, dataUrl: reader.result };
    document.querySelector('#file-name').textContent = file.name;
    selectedFile.hidden = false;
    confirmButton.disabled = false;
  });
  reader.readAsDataURL(file);
});

confirmButton.addEventListener('click', () => {
  formatData = selectedFileData;
  localStorage.setItem(storageKeys.format, JSON.stringify(formatData));
  selectedFileData = null;
  updateFormatReference();
  closeUploadDialog();
  generateTimetable();
});

document.querySelector('#remove-file').addEventListener('click', () => {
  fileInput.value = '';
  selectedFile.hidden = true;
  confirmButton.disabled = true;
  selectedFileData = null;
});
document.querySelector('#change-format-button').addEventListener('click', openUploadDialog);
document.querySelector('#close-dialog').addEventListener('click', closeUploadDialog);
document.querySelector('#cancel-upload').addEventListener('click', closeUploadDialog);
document.querySelector('#print-button').addEventListener('click', () => window.print());
document.querySelector('#save-timetable-button').addEventListener('click', () => {
  const rows = [...document.querySelectorAll('#timetable-body tr')].map((row) => [...row.querySelectorAll('td')].map((cell, index) => {
    if (index === 0) return cell.innerText.trim();
    const lines = cell.innerText.trim().split('\n');
    return [lines[0] || '', lines.slice(1).join(' ')];
  }));
  localStorage.setItem(storageKeys.timetable, JSON.stringify({ rows, savedAt: new Date().toISOString() }));
  showToast('Timetable changes saved on this PC.');
});
document.querySelector('#new-button').addEventListener('click', () => {
  document.querySelector('#timetable-setup').scrollIntoView({ behavior: 'smooth', block: 'center' });
  showToast('Create another timetable for this department.');
});

const dropZone = document.querySelector('#drop-zone');
['dragenter', 'dragover'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.add('dragging'); }));
['dragleave', 'drop'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.remove('dragging'); }));
dropZone.addEventListener('drop', (event) => { fileInput.files = event.dataTransfer.files; fileInput.dispatchEvent(new Event('change')); });

function showToast(message) {
  const toast = document.querySelector('#toast');
  toast.textContent = message;
  toast.classList.add('show');
  window.setTimeout(() => toast.classList.remove('show'), 3500);
}

const savedProfile = JSON.parse(localStorage.getItem(storageKeys.profile) || 'null');
if (savedProfile) { showProfile(savedProfile); setProfileMode(true); }
updateFormatReference();
renderTimetable();
