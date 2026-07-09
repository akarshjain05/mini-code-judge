// ── Add / Edit Problem ───────────────────────────────────────────────
// ── Category dropdown (Add/Edit Problem form) ───────────────────────
const DSA_CATEGORIES = [
  'Arrays','Strings','Linked List','Stack','Queue','Hashing','Two Pointers',
  'Sliding Window','Binary Search','Sorting','Recursion','Backtracking',
  'Dynamic Programming','Greedy','Trees','Binary Tree','Binary Search Tree',
  'Heap / Priority Queue','Trie','Graphs','BFS','DFS','Topological Sort',
  'Union Find / DSU','Shortest Path','Minimum Spanning Tree','Bit Manipulation',
  'Math','Number Theory','Combinatorics','Geometry','Matrix','Simulation',
  'Divide and Conquer','Segment Tree','Fenwick Tree / BIT','String Matching',
  'Dynamic Programming on Trees','Game Theory','Bitmask DP','Prefix Sum',
  'Monotonic Stack','Monotonic Queue','Design','Interactive','Randomized',
  'Implementation','Brute Force','Constructive Algorithms','Probability',
];
let _selectedCategories = new Set();
let _catDropdownInit = false;

function initCategoryDropdown() {
  const panel = document.getElementById('catDropdownPanel');
  panel.innerHTML = DSA_CATEGORIES.map(c => `
    <label onclick="event.stopPropagation()" style="display:flex;align-items:center;gap:9px;padding:9px 12px;cursor:pointer;font-size:13px;color:var(--text)"
      onmouseover="this.style.background='var(--surface2)'" onmouseout="this.style.background='none'">
      <input type="checkbox" value="${c}" onchange="toggleCategory('${c.replace(/'/g,"\\'")}')" ${_selectedCategories.has(c)?'checked':''} style="cursor:pointer;accent-color:var(--accent)" />
      ${c}
    </label>`).join('');
  _catDropdownInit = true;
}

function toggleCatDropdown() {
  if (!_catDropdownInit) initCategoryDropdown();
  const panel = document.getElementById('catDropdownPanel');
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function toggleCategory(cat) {
  if (_selectedCategories.has(cat)) _selectedCategories.delete(cat);
  else _selectedCategories.add(cat);
  updateCatDropdownLabel();
}

function updateCatDropdownLabel() {
  const label = document.getElementById('catDropdownLabel');
  if (_selectedCategories.size === 0) {
    label.textContent = 'Select categories…';
    label.style.color = 'var(--muted)';
  } else {
    label.textContent = [..._selectedCategories].join(', ');
    label.style.color = 'var(--text)';
  }
}

function setSelectedCategories(catString) {
  _selectedCategories = new Set((catString || '').split(',').map(c => c.trim()).filter(Boolean));
  if (_catDropdownInit) initCategoryDropdown();
  updateCatDropdownLabel();
}

document.addEventListener('click', (e) => {
  const wrap = document.getElementById('catDropdownWrap');
  const panel = document.getElementById('catDropdownPanel');
  if (wrap && panel && panel.style.display === 'block' && !wrap.contains(e.target)) {
    panel.style.display = 'none';
  }
});

function editProblem(p) {
  goTo('addproblem');
  document.getElementById('editProbId').value = p.id;
  document.getElementById('probTitle').value = p.title;
  document.getElementById('probDesc').value = p.description;
  document.getElementById('probDiff').value = p.difficulty;
  setSelectedCategories(p.category);
  document.getElementById('saveProbBtn').textContent = `Update Problem #${p.id}`;
  document.getElementById('cancelEditBtn').style.display = '';
  document.getElementById('addProbCardTitle').textContent = `✏ Edit Problem #${p.id}`;
  document.getElementById('addProbOk').className = 'alert';
  document.getElementById('addProbErr').className = 'alert';
}

function cancelProblemEdit() {
  document.getElementById('editProbId').value = '';
  document.getElementById('probTitle').value = '';
  document.getElementById('probDesc').value = '';
  document.getElementById('probDiff').value = 'easy';
  setSelectedCategories('');
  document.getElementById('saveProbBtn').textContent = 'Create Problem';
  document.getElementById('cancelEditBtn').style.display = 'none';
  document.getElementById('addProbCardTitle').textContent = '📝 Problem details';
}

async function saveProblem() {
  if (!token) { openAuthModal(); return; }
  const editId  = document.getElementById('editProbId').value;
  const title   = document.getElementById('probTitle').value.trim();
  const desc    = document.getElementById('probDesc').value.trim();
  const diff    = document.getElementById('probDiff').value;
  const category = _selectedCategories.size ? [..._selectedCategories].join(', ') : null;
  const err = document.getElementById('addProbErr');
  const ok  = document.getElementById('addProbOk');
  [err, ok].forEach(e => { e.className = 'alert'; e.textContent = ''; });
  if (!title || !desc) { showAlert(err, 'Title and description are required.', 'error'); return; }

  const isEdit = !!editId;
  const url    = isEdit ? `${API}/problems/${editId}` : `${API}/problems`;
  const method = isEdit ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: desc, difficulty: diff, category }),
    });
    const data = await res.json();
    if (!res.ok) { showAlert(err, data.detail || 'Failed', 'error'); return; }
    showAlert(ok, isEdit ? `✓ Problem #${data.id} updated!` : `✓ Problem #${data.id} "${data.title}" created!`, 'success');
    if (!isEdit) document.getElementById('tcProbId').value = data.id;
    cancelProblemEdit();
    loadProblems();
  } catch(e) { showAlert(err, 'Cannot reach API.', 'error'); }
}
// ── Add Problem ────────────────────────────────────────────────────
async function addTestCase() {
  if (!token) { openAuthModal(); return; }
  const pid  = document.getElementById('tcProbId').value;
  const sin  = document.getElementById('tcStdin').value;
  const exp  = document.getElementById('tcExpected').value.trim();
  const samp = document.getElementById('tcSample').checked;
  const err  = document.getElementById('addTcErr');
  const ok   = document.getElementById('addTcOk');
  [err, ok].forEach(e => { e.className = 'alert'; e.textContent = ''; });
  if (!pid || !exp) { showAlert(err, 'Problem ID and expected output are required.', 'error'); return; }
  try {
    const res = await fetch(`${API}/problems/${pid}/test-cases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stdin: sin, expected: exp, is_sample: samp }),
    });
    const data = await res.json();
    if (!res.ok) { showAlert(err, data.detail || 'Failed', 'error'); return; }
    showAlert(ok, '✓ Test case added!', 'success');
    document.getElementById('tcStdin').value = '';
    document.getElementById('tcExpected').value = '';
  } catch(e) { showAlert(err, 'Cannot reach API.', 'error'); }
}
