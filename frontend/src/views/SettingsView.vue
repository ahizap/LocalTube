<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../services/api'

const isLoading = ref(true)

// Task state
const tasks = ref([])
let taskPollingInterval = null

// File Explorer State
const showFileExplorer = ref(false)
const explorerPath = ref('')
const explorerParent = ref('')
const explorerDirectories = ref([])
const explorerLoading = ref(false)
const pendingScanType = ref('all')
const batchFolders = ref([]) // queued folders for batch scanning

const openFileExplorerForScan = async (type) => {
  pendingScanType.value = type
  batchFolders.value = []
  showFileExplorer.value = true
  await fetchDirectory(settings.value.default_browse_path || '')
}

const closeFileExplorer = () => {
  showFileExplorer.value = false
  batchFolders.value = []
}

const fetchDirectory = async (path) => {
  explorerLoading.value = true
  try {
    const data = await api.listDirectory(path)
    if (data.error) {
      alert("Error: " + data.error)
    } else {
      explorerPath.value = data.path
      explorerParent.value = data.parent
      explorerDirectories.value = data.directories || []
    }
  } catch (e) {
    alert("Failed to list directory: " + e.message)
  } finally {
    explorerLoading.value = false
  }
}

const addToBatch = (path) => {
  if (!batchFolders.value.includes(path)) {
    batchFolders.value.push(path)
  }
}

const removeFromBatch = (path) => {
  batchFolders.value = batchFolders.value.filter(f => f !== path)
}

const isFolderInBatch = (path) => {
  return batchFolders.value.includes(path)
}

const startBatchScan = async () => {
  // Use batch folders if any, otherwise use current path
  const folders = batchFolders.value.length > 0
    ? [...batchFolders.value]
    : (explorerPath.value ? [explorerPath.value] : [])

  closeFileExplorer()

  for (const dir of folders) {
    try {
      await api.triggerScan(pendingScanType.value, dir)
    } catch (e) {
      console.error(`Failed to start scan for ${dir}:`, e)
    }
  }
  await fetchTasks()
}

const fetchTasks = async () => {
  try {
    tasks.value = await api.getTasks()
  } catch (error) {
    console.error("Failed to fetch tasks", error)
  }
}

const cancelTask = async (taskId) => {
  try {
    await api.cancelTask(taskId)
    await fetchTasks()
  } catch (e) {
    console.error("Failed to cancel task:", e)
  }
}

const clearFinishedTasks = async () => {
  try {
    await api.clearFinishedTasks()
    await fetchTasks()
  } catch (e) {
    console.error("Failed to clear tasks:", e)
  }
}

const activeTasks = computed(() => tasks.value.filter(t => t.status === 'running' || t.status === 'pending'))
const finishedTasks = computed(() => tasks.value.filter(t => t.status === 'completed' || t.status === 'cancelled' || t.status === 'error'))

const settings = ref({
  thumbnail_percentage: 5.0,
  preview_segments: 10,
  preview_duration: 2.0,
  preview_audio: true,
  default_browse_path: '',
  max_concurrent_tasks: 2
})

onMounted(async () => {
  try {
    const data = await api.getSettings()

    Object.keys(settings.value).forEach(key => {
      if (data[key] !== undefined) {
        settings.value[key] = data[key]
      }
    })
  } catch (error) {
    console.error("Failed to load settings", error)
  } finally {
    isLoading.value = false
  }

  await fetchTasks()
  await fetchLibraryFolders()
  taskPollingInterval = setInterval(fetchTasks, 1500)
})

onUnmounted(() => {
  if (taskPollingInterval) {
    clearInterval(taskPollingInterval)
  }
})

const saveSetting = async (key, value) => {
  await api.saveSetting(key, value)
}

const taskProgress = (task) => {
  if (task.total === 0) return 0
  return Math.round((task.current / task.total) * 100)
}

const taskDirName = (task) => {
  // Show just the last folder name
  const parts = task.directory.replace(/\\/g, '/').split('/')
  return parts.filter(p => p).pop() || task.directory
}

const taskStatusIcon = (status) => {
  switch (status) {
    case 'running': return '⚙️'
    case 'pending': return '⏳'
    case 'completed': return '✅'
    case 'cancelled': return '⛔'
    case 'error': return '❌'
    default: return '❓'
  }
}

// Library Management
const libraryFolders = ref([])
const draggedIndex = ref(null)
const dragOverIndex = ref(null)

// Computed: count of partially scanned folders
const partialFoldersCount = computed(() => {
  return libraryFolders.value.filter(f => f.partially_scanned).length
})

const fetchLibraryFolders = async () => {
  try {
    libraryFolders.value = await api.getLibraryFolders()
    // Load saved folder order
    const orderData = await api.getFolderOrder()
    if (orderData.order && orderData.order.length > 0) {
      // Sort folders according to saved order
      const orderMap = {}
      orderData.order.forEach((path, index) => {
        orderMap[path] = index
      })
      libraryFolders.value.sort((a, b) => {
        const orderA = orderMap[a.path] ?? 999999
        const orderB = orderMap[b.path] ?? 999999
        return orderA - orderB
      })
    }
  } catch (e) {
    console.error('Failed to fetch library folders:', e)
  }
}

// Rescan all partially scanned folders
const rescanPartialFolders = async () => {
  const partialFolders = libraryFolders.value.filter(f => f.partially_scanned)
  if (partialFolders.length === 0) {
    alert('No partially scanned folders to rescan.')
    return
  }
  
  if (!confirm(`Rescan ${partialFolders.length} partially scanned folder(s)?\n\nAlready processed videos will be skipped automatically.`)) {
    return
  }
  
  for (const folder of partialFolders) {
    try {
      await api.triggerScan('all', folder.path)
    } catch (e) {
      console.error(`Failed to start scan for ${folder.path}:`, e)
    }
  }
  await fetchTasks()
}

const removeFolder = async (folderPath) => {
  if (!confirm(`Remove all scanned videos from:\n${folderPath}\n\nThis deletes cached thumbnails/previews but NOT the original video files.`)) return
  try {
    await api.deleteFolder(folderPath)
    await fetchLibraryFolders()
  } catch (e) {
    alert('Failed to remove folder: ' + e.message)
  }
}

const folderName = (path) => {
  const parts = path.replace(/\\/g, '/').split('/').filter(p => p)
  return parts.pop() || path
}

// Drag and drop handlers
const onDragStart = (e, index) => {
  draggedIndex.value = index
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', index)
  // Add dragging class for visual feedback
  e.target.classList.add('dragging')
}

const onDragEnd = (e) => {
  e.target.classList.remove('dragging')
  draggedIndex.value = null
  dragOverIndex.value = null
}

const onDragOver = (e, index) => {
  e.preventDefault()
  e.dataTransfer.dropEffect = 'move'
  dragOverIndex.value = index
}

const onDragLeave = (e) => {
  // Only clear if we're leaving the element entirely
  if (!e.currentTarget.contains(e.relatedTarget)) {
    dragOverIndex.value = null
  }
}

const onDrop = async (e, dropIndex) => {
  e.preventDefault()
  
  if (draggedIndex.value === null || draggedIndex.value === dropIndex) {
    draggedIndex.value = null
    dragOverIndex.value = null
    return
  }
  
  // Reorder the array
  const item = libraryFolders.value.splice(draggedIndex.value, 1)[0]
  libraryFolders.value.splice(dropIndex, 0, item)
  
  // Save the new order
  const newOrder = libraryFolders.value.map(f => f.path)
  try {
    await api.saveFolderOrder(newOrder)
    // Show success feedback
    showOrderSavedMessage()
  } catch (err) {
    console.error('Failed to save folder order:', err)
    alert('Failed to save folder order')
    // Revert the change
    await fetchLibraryFolders()
  }
  
  draggedIndex.value = null
  dragOverIndex.value = null
}

const showOrderSavedMessage = () => {
  // Simple toast message
  const toast = document.createElement('div')
  toast.className = 'toast-message'
  toast.textContent = '✓ Folder order saved! Home page will use this order when sorting by Folder.'
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    background-color: #52c41a;
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    z-index: 10000;
    animation: fadeIn 0.3s ease;
  `
  document.body.appendChild(toast)
  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transition = 'opacity 0.3s ease'
    setTimeout(() => toast.remove(), 300)
  }, 3000)
}

const resetFolderOrder = async () => {
  if (!confirm('Reset folder order to alphabetical?')) return
  try {
    await api.saveFolderOrder([])
    await fetchLibraryFolders()
  } catch (err) {
    console.error('Failed to reset folder order:', err)
  }
}
</script>

<template>
  <div class="settings-page" v-if="!isLoading">
    <div class="header-row">
      <h1>Settings</h1>
      <div class="button-group">
        <button class="btn-primary" @click="openFileExplorerForScan('thumbnail')">Scan files & Generate thumbnails</button>
        <button class="btn-secondary" @click="openFileExplorerForScan('preview')">Generate Previews</button>
      </div>
    </div>

    <!-- Task Dashboard -->
    <section class="task-dashboard" v-if="tasks.length > 0">
      <div class="task-dashboard-header">
        <h2>Tasks</h2>
        <button v-if="finishedTasks.length > 0" class="btn-text" @click="clearFinishedTasks">Clear finished</button>
      </div>

      <div class="task-list">
        <div v-for="task in tasks" :key="task.id" class="task-card" :class="`task-${task.status}`">
          <div class="task-card-top">
            <span class="task-icon">{{ taskStatusIcon(task.status) }}</span>
            <div class="task-info">
              <span class="task-dir" :title="task.directory">{{ taskDirName(task) }}</span>
              <span class="task-type">{{ task.scan_type === 'thumbnail' ? 'Thumbnails' : task.scan_type === 'preview' ? 'Previews' : 'Full Scan' }}</span>
            </div>
            <div class="task-stats" v-if="task.status === 'running'">
              <span>{{ task.current }} / {{ task.total }}</span>
            </div>
            <div class="task-stats" v-else-if="task.status === 'completed'">
              <span>{{ task.total }} files</span>
            </div>
            <div class="task-stats" v-else-if="task.status === 'error'">
              <span class="error-text" :title="task.error_message">Error</span>
            </div>
            <button
              v-if="task.status === 'running' || task.status === 'pending'"
              class="btn-cancel"
              @click="cancelTask(task.id)"
              title="Cancel task"
            >✕</button>
          </div>
          <div class="task-progress-bar" v-if="task.status === 'running'">
            <div class="task-progress-fill" :style="{ width: taskProgress(task) + '%' }"></div>
          </div>
          <div class="task-file" v-if="task.status === 'running' && task.current_file" :title="task.current_file">
            {{ task.current_file.split(/[\\/]/).pop() }}
          </div>
        </div>
      </div>
    </section>

    <div class="settings-container">
      <section class="settings-section">
        <h2>General</h2>

        <div class="setting-row">
          <label>Default Browse Path</label>
          <div class="input-group">
            <input
              type="text"
              v-model="settings.default_browse_path"
              @change="saveSetting('default_browse_path', settings.default_browse_path)"
              class="input-field"
              placeholder="e.g. C:\ or /home/user"
            />
            <span class="hint">The starting path when opening the file explorer.</span>
          </div>
        </div>

        <div class="setting-row">
          <label>Max Concurrent Tasks</label>
          <div class="input-group">
            <input
              type="number"
              v-model.number="settings.max_concurrent_tasks"
              @change="saveSetting('max_concurrent_tasks', settings.max_concurrent_tasks)"
              min="1" max="8" class="input-field num-input"
            />
            <span class="hint">Maximum number of scan tasks to run simultaneously.</span>
          </div>
        </div>
      </section>

      <section class="settings-section">
        <h2>Processing Engine</h2>
        <p class="text-secondary">Configure how thumbnails and hover previews are generated.</p>

        <div class="setting-row">
          <label>Thumbnail Capture Point (%)</label>
          <div class="input-group">
            <input
              type="number"
              v-model.number="settings.thumbnail_percentage"
              @change="saveSetting('thumbnail_percentage', settings.thumbnail_percentage)"
              min="0" max="100" class="input-field num-input"
            />
            <span class="hint">The % of the video duration to take a single frame for the static thumbnail.</span>
          </div>
        </div>

        <div class="setting-row">
          <label>Preview Segments Count</label>
          <div class="input-group">
            <input
              type="number"
              v-model.number="settings.preview_segments"
              @change="saveSetting('preview_segments', settings.preview_segments)"
              min="1" max="50" class="input-field num-input"
            />
            <span class="hint">Number of short clips to extract across the video to build the preview.</span>
          </div>
        </div>

        <div class="setting-row">
          <label>Preview Segment Duration (s)</label>
          <div class="input-group">
            <input
              type="number"
              v-model.number="settings.preview_duration"
              @change="saveSetting('preview_duration', settings.preview_duration)"
              min="0.5" max="10" step="0.5" class="input-field num-input"
            />
            <span class="hint">Duration of each individual segment in the preview.</span>
          </div>
        </div>

        <div class="setting-row toggle-row">
          <label>Include Audio in Hover Previews</label>
          <input
            type="checkbox"
            v-model="settings.preview_audio"
            @change="saveSetting('preview_audio', settings.preview_audio)"
          />
        </div>
      </section>

      <section class="settings-section">
        <div class="section-header">
          <div>
            <h2>Scanned Library</h2>
            <p class="text-secondary" style="margin-bottom: 0;">Drag folders to reorder. This order is used when sorting by "Folder" on the home page. Removing a folder deletes cached thumbnails and previews, not the original files.</p>
          </div>
          <div class="section-header-actions">
            <button class="btn-text" @click="resetFolderOrder" title="Reset to alphabetical order">↺ Reset Order</button>
            <button class="btn-text" @click="fetchLibraryFolders" title="Refresh">🔄 Refresh</button>
            <button
              v-if="partialFoldersCount > 0"
              class="btn-text btn-partial"
              @click="rescanPartialFolders"
              title="Rescan all partially scanned folders"
            >
              ⚠️ Rescan {{ partialFoldersCount }} Partial{{ partialFoldersCount > 1 ? 's' : '' }}
            </button>
            </div>
            </div>

        <div v-if="libraryFolders.length === 0" class="empty-library">
          No folders scanned yet. Use the scan buttons above to add videos.
        </div>

        <div v-else class="library-folder-list">
          <div 
            v-for="(folder, index) in libraryFolders" 
            :key="folder.path" 
            class="library-folder-item"
            :class="{ 
              'drag-over': dragOverIndex === index,
              'dragging': draggedIndex === index 
            }"
            draggable="true"
            @dragstart="onDragStart($event, index)"
            @dragend="onDragEnd($event)"
            @dragover="onDragOver($event, index)"
            @dragleave="onDragLeave($event)"
            @drop="onDrop($event, index)"
          >
            <div class="drag-handle" title="Drag to reorder">⋮⋮</div>
            <div class="library-folder-info">
              <span class="library-folder-name" :title="folder.path">📁 {{ folderName(folder.path) }}</span>
              <span class="library-folder-path">{{ folder.path }}</span>
              <div class="library-folder-stats">
                <span>{{ folder.count }} videos</span>
                <span v-if="folder.has_thumbs">• {{ folder.has_thumbs }} thumbs</span>
                <span v-if="folder.has_previews">• {{ folder.has_previews }} previews</span>
                <span v-if="folder.partially_scanned" class="status-badge partial">⚠️ Partial</span>
                <span v-else-if="folder.has_thumbs && folder.has_previews" class="status-badge complete">✓ Complete</span>
              </div>
            </div>
            <button class="btn-remove" @click="removeFolder(folder.path)" title="Remove folder from library">🗑️ Remove</button>
          </div>
        </div>
      </section>
    </div>
  </div>
  <div v-else class="loading">Loading settings...</div>

  <!-- Custom File Explorer Modal -->
  <div class="modal-overlay" v-if="showFileExplorer" @click.self="closeFileExplorer">
    <div class="modal-content file-explorer">
      <div class="explorer-header">
        <h2>Select Folder{{ pendingScanType === 'thumbnail' ? ' (Thumbnails)' : pendingScanType === 'preview' ? ' (Previews)' : '' }}</h2>
        <button class="btn-close" @click="closeFileExplorer">&times;</button>
      </div>

      <div class="explorer-path-bar">
        <span class="path-label">Current:</span>
        <span class="current-path">{{ explorerPath || 'Root / Drives' }}</span>
      </div>

      <!-- Batch queue indicator -->
      <div class="batch-bar" v-if="batchFolders.length > 0">
        <span class="batch-label">🗂️ Queued ({{ batchFolders.length }}):</span>
        <div class="batch-chips">
          <span v-for="folder in batchFolders" :key="folder" class="batch-chip">
            {{ folder.replace(/\\/g, '/').split('/').filter(p => p).pop() }}
            <button class="chip-remove" @click.stop="removeFromBatch(folder)">&times;</button>
          </span>
        </div>
      </div>

      <div class="explorer-body">
        <div v-if="explorerLoading" class="explorer-loading">Loading...</div>
        <ul v-else class="directory-list-view">
          <li v-if="explorerPath" class="directory-list-item back-item" @click="fetchDirectory(explorerParent)">
            <span class="icon">📁</span> ..
          </li>
          <li v-for="dir in explorerDirectories" :key="dir.path" class="directory-list-item">
            <div class="dir-row-main" @click="fetchDirectory(dir.path)">
              <span class="icon">📁</span> {{ dir.name }}
            </div>
            <button
              class="btn-add-batch"
              :class="{ 'added': isFolderInBatch(dir.path) }"
              @click.stop="isFolderInBatch(dir.path) ? removeFromBatch(dir.path) : addToBatch(dir.path)"
              :title="isFolderInBatch(dir.path) ? 'Remove from batch' : 'Add to batch'"
            >
              {{ isFolderInBatch(dir.path) ? '✓' : '+' }}
            </button>
          </li>
          <li v-if="explorerDirectories.length === 0 && explorerPath" class="directory-list-item empty-dir">
            No subdirectories
          </li>
        </ul>
      </div>

      <div class="explorer-footer">
        <button class="btn-secondary" @click="closeFileExplorer">Cancel</button>
        <button
          class="btn-primary"
          @click="startBatchScan"
          :disabled="!explorerPath && batchFolders.length === 0"
        >
          {{ batchFolders.length > 0 ? `Start Scan (${batchFolders.length} folders)` : 'Scan This Folder' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
}

.loading {
  text-align: center;
  margin-top: 100px;
  color: var(--text-secondary);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

h1 {
  font-size: 1.5rem;
}

h2 {
  font-size: 1.2rem;
  margin-bottom: 8px;
}

.text-secondary {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 20px;
}

.settings-container {
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.settings-section {
  background-color: var(--bg-secondary);
  padding: 24px;
  border-radius: var(--border-radius-lg);
  border: 1px solid var(--border-color);
}

.input-field {
  background-color: var(--bg-color);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 10px 16px;
  border-radius: var(--border-radius-md);
  flex: 1;
  font-family: inherit;
}

.input-field:focus {
  outline: none;
  border-color: var(--accent-color);
}

.num-input {
  flex: none;
  width: 100px;
}

button {
  padding: 10px 20px;
  border-radius: var(--border-radius-md);
  font-weight: 500;
  transition: all var(--transition-fast);
}

.btn-primary {
  background-color: var(--accent-color);
  color: white;
}

.btn-primary:hover {
  background-color: var(--accent-hover);
}

.btn-secondary {
  background-color: var(--border-color);
  color: white;
}

.btn-secondary:hover {
  background-color: #444448;
}

.btn-danger {
  background-color: transparent;
  color: var(--accent-color);
  padding: 6px 12px;
}

.btn-danger:hover {
  background-color: rgba(229, 9, 20, 0.1);
}

.btn-text {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 0.85rem;
  padding: 4px 8px;
  cursor: pointer;
}

.btn-text:hover {
  color: var(--text-primary);
}

.btn-partial {
  color: #f59e0b;
  font-weight: 500;
}

.btn-partial:hover {
  color: #fbbf24;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  margin-left: 8px;
}

.status-badge.partial {
  background-color: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.status-badge.complete {
  background-color: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.setting-row {
  margin-bottom: 20px;
}

.setting-row label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hint {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
}

.toggle-row label {
  margin-bottom: 0;
}

.button-group {
  display: flex;
  gap: 12px;
}

/* ===== Task Dashboard ===== */
.task-dashboard {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-lg);
  padding: 20px 24px;
  margin-bottom: 32px;
}

.task-dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.task-dashboard-header h2 {
  margin: 0;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  background-color: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  padding: 12px 16px;
  transition: border-color 0.2s;
}

.task-card.task-running {
  border-left: 3px solid var(--accent-color);
}

.task-card.task-pending {
  border-left: 3px solid #888;
  opacity: 0.7;
}

.task-card.task-completed {
  border-left: 3px solid #52c41a;
  opacity: 0.6;
}

.task-card.task-cancelled {
  border-left: 3px solid #faad14;
  opacity: 0.5;
}

.task-card.task-error {
  border-left: 3px solid #ff4d4f;
}

.task-card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.task-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-dir {
  font-weight: 600;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-type {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.task-stats {
  font-size: 0.85rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.error-text {
  color: #ff4d4f;
}

.btn-cancel {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  width: 28px;
  height: 28px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  cursor: pointer;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.btn-cancel:hover {
  color: #ff4d4f;
  border-color: #ff4d4f;
  background-color: rgba(255, 77, 79, 0.1);
}

.task-progress-bar {
  height: 4px;
  background-color: var(--border-color);
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.task-progress-fill {
  height: 100%;
  background-color: var(--accent-color);
  transition: width 0.3s ease;
  border-radius: 2px;
}

.task-file {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== Modal and File Explorer ===== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background-color: var(--bg-color);
  border-radius: var(--border-radius-lg);
  border: 1px solid var(--border-color);
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.explorer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
}

.explorer-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.btn-close:hover {
  color: var(--text-primary);
}

.explorer-path-bar {
  padding: 12px 24px;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: monospace;
  font-size: 0.9rem;
}

.path-label {
  color: var(--text-secondary);
  font-weight: bold;
}

.current-path {
  color: var(--text-primary);
  word-break: break-all;
}

/* Batch bar */
.batch-bar {
  padding: 10px 24px;
  background-color: rgba(229, 9, 20, 0.05);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.batch-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.batch-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.batch-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background-color: var(--accent-color);
  color: white;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
}

.chip-remove {
  background: none;
  border: none;
  color: rgba(255,255,255,0.7);
  padding: 0 2px;
  font-size: 0.9rem;
  cursor: pointer;
  line-height: 1;
}

.chip-remove:hover {
  color: white;
}

.explorer-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0;
  min-height: 200px;
}

.explorer-loading {
  text-align: center;
  color: var(--text-secondary);
  padding: 40px;
}

.directory-list-view {
  list-style: none;
  padding: 0;
  margin: 0;
}

.directory-list-item {
  padding: 10px 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: background-color var(--transition-fast);
}

.directory-list-item:hover {
  background-color: var(--bg-secondary);
}

.directory-list-item .icon {
  font-size: 1.2rem;
}

.dir-row-main {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-add-batch {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  width: 28px;
  height: 28px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1rem;
  flex-shrink: 0;
  transition: all 0.15s;
}

.btn-add-batch:hover {
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.btn-add-batch.added {
  background-color: var(--accent-color);
  border-color: var(--accent-color);
  color: white;
}

.back-item {
  font-weight: bold;
  color: var(--text-secondary);
}

.empty-dir {
  color: var(--text-secondary);
  font-style: italic;
  justify-content: center;
  cursor: default;
}

.empty-dir:hover {
  background-color: transparent;
}

.explorer-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ===== Library Management ===== */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.section-header h2 {
  margin: 0;
}

.section-header-actions {
  display: flex;
  gap: 8px;
}

.empty-library {
  color: var(--text-secondary);
  font-style: italic;
  padding: 24px;
  text-align: center;
}

.library-folder-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.library-folder-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--bg-color);
  padding: 12px 16px;
  border-radius: var(--border-radius-md);
  border: 1px solid var(--border-color);
  transition: all 0.15s;
  cursor: grab;
}

.library-folder-item:hover {
  border-color: var(--text-secondary);
}

.library-folder-item.dragging {
  opacity: 0.5;
  cursor: grabbing;
}

.library-folder-item.drag-over {
  border-color: var(--accent-color);
  border-style: dashed;
  background-color: rgba(229, 9, 20, 0.05);
}

.drag-handle {
  color: var(--text-secondary);
  cursor: grab;
  padding-right: 12px;
  font-size: 1.2rem;
  user-select: none;
}

.drag-handle:hover {
  color: var(--text-primary);
}

.library-folder-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.library-folder-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.library-folder-path {
  font-family: monospace;
  font-size: 0.8rem;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.library-folder-stats {
  display: flex;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-top: 2px;
}

.btn-remove {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 6px 12px;
  border-radius: var(--border-radius-md);
  cursor: pointer;
  font-size: 0.85rem;
  white-space: nowrap;
  transition: all 0.15s;
}

.btn-remove:hover {
  color: #ff4d4f;
  border-color: #ff4d4f;
  background-color: rgba(255, 77, 79, 0.1);
}
</style>
