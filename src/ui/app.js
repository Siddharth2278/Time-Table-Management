const sampleRows = [
  ['Monday', ['Data Structures', 'Dr. Mehta'], ['Discrete Mathematics', 'Prof. Rao'], ['Operating Systems', 'Dr. Khan'], ['BREAK', 'Lunch'], ['Computer Networks', 'Prof. Shah']],
  ['Tuesday', ['Database Systems', 'Dr. Iyer'], ['Computer Networks', 'Prof. Shah'], ['BREAK', 'Lunch'], ['Data Structures', 'Dr. Mehta'], ['Web Engineering', 'Prof. Das']],
  ['Wednesday', ['Operating Systems', 'Dr. Khan'], ['BREAK', 'Lunch'], ['Database Systems', 'Dr. Iyer'], ['Discrete Mathematics', 'Prof. Rao'], ['Data Structures Lab', 'Lab 02']],
  ['Thursday', ['Web Engineering', 'Prof. Das'], ['Operating Systems', 'Dr. Khan'], ['Data Structures', 'Dr. Mehta'], ['BREAK', 'Lunch'], ['Database Systems', 'Dr. Iyer']],
  ['Friday', ['Discrete Mathematics', 'Prof. Rao'], ['Computer Networks', 'Prof. Shah'], ['Web Engineering', 'Prof. Das'], ['BREAK', 'Lunch'], ['Project Studio', 'Academic block']]
];

const dialog = document.querySelector('#upload-dialog');
const fileInput = document.querySelector('#format-photo');
const confirmButton = document.querySelector('#confirm-upload');
const selectedFile = document.querySelector('#selected-file');
const referencePreview = document.querySelector('#reference-preview');
const resultSection = document.querySelector('#result-section');
let selectedImageUrl = '';

function renderTimetable() {
  const body = document.querySelector('#timetable-body');
  body.innerHTML = sampleRows.map(([day, ...cells]) => `<tr><td>${day}</td>${cells.map(([subject, teacher]) => subject === 'BREAK'
    ? `<td class="break-cell">${teacher}</td>`
    : `<td class="${subject.includes('Lab') ? 'lab-cell' : ''}"><span class="cell-subject">${subject}</span><span class="cell-teacher">${teacher}</span></td>`).join('')}</tr>`).join('');
}

function openUploadDialog() { dialog.showModal(); }
function closeUploadDialog() { dialog.close(); }

document.querySelector('#generate-button').addEventListener('click', () => {
  if (!selectedImageUrl) openUploadDialog();
  else generateTimetable();
});

function generateTimetable() {
  const semester = document.querySelector('#semester').value;
  const year = document.querySelector('#academic-year').value;
  const department = document.querySelector('#department').value;
  document.querySelector('#timetable-title').textContent = department;
  document.querySelector('#timetable-meta').textContent = `${semester} · ${year}`;
  renderTimetable();
  resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  showToast('Timetable generated in your selected format.');
}

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;
  selectedImageUrl = URL.createObjectURL(file);
  document.querySelector('#file-name').textContent = file.name;
  selectedFile.hidden = false;
  confirmButton.disabled = false;
});

confirmButton.addEventListener('click', () => {
  referencePreview.classList.remove('empty');
  referencePreview.innerHTML = `<img src="${selectedImageUrl}" alt="Uploaded timetable format reference">`;
  closeUploadDialog();
  generateTimetable();
});

document.querySelector('#remove-file').addEventListener('click', () => {
  fileInput.value = '';
  selectedFile.hidden = true;
  confirmButton.disabled = true;
  selectedImageUrl = '';
});
document.querySelector('#close-dialog').addEventListener('click', closeUploadDialog);
document.querySelector('#cancel-upload').addEventListener('click', closeUploadDialog);
document.querySelector('#print-button').addEventListener('click', () => window.print());
document.querySelector('#new-button').addEventListener('click', () => {
  selectedImageUrl = '';
  fileInput.value = '';
  selectedFile.hidden = true;
  confirmButton.disabled = true;
  referencePreview.className = 'reference-preview empty';
  referencePreview.innerHTML = '<span class="upload-symbol">+</span><span>No photo uploaded</span>';
  window.scrollTo({ top: 0, behavior: 'smooth' });
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

renderTimetable();