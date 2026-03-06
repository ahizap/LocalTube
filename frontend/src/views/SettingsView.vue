<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../services/api'

const directories = ref([])
const newDirectory = ref('')
const isLoading = ref(true)

const scanProgress = ref({
  status: 'idle',
  total: 0,
  current: 0,
  current_file: ''
})
let scanPollingInterval = null

// File Explorer State
const showFileExplorer = ref(false)
const explorerPath = ref('')
const explorerParent = ref('')
const explorerDirectories = ref([])
const explorerLoading = ref(false)

const openFileExplorer = async () => {
  showFileExplorer.value = true
  await fetchDirectory(settings.value.default_browse_path || '')
}

const closeFileExplorer = () => {
  showFileExplorer.value = false
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

const selectExplorerPath = () => {
  newDirectory.value = explorerPath.value
  closeFileExplorer()
}

const checkScanProgress = async () => {
  try {
    const data = await api.getScanProgress()
    scanProgress.value = data
  } catch (error) {
    console.error("Failed to fetch scan progress", error)
  }
}

const settings = ref({
  thumbnail_percentage: 5.0,
  preview_segments: 10,
  preview_duration: 2.0,
  preview_audio: true,
  skip_scanned: true,
  default_browse_path: ''
})

onMounted(async () => {
  try {
    const data = await api.getSettings()
    directories.value = data.directories || []
    
    // Merge existing settings
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

  await checkScanProgress()
  scanPollingInterval = setInterval(checkScanProgress, 2000)
})

onUnmounted(() => {
  if (scanPollingInterval) {
    clearInterval(scanPollingInterval)
  }
})

const addDirectory = async () => {
  if (!newDirectory.value) return
  
  if (!directories.value.includes(newDirectory.value)) {
    const updated = [...directories.value, newDirectory.value];
    await api.saveSetting('directories', updated)
    directories.value = updated
  }
  newDirectory.value = ''
}

const removeDirectory = async (dir) => {
  const updated = directories.value.filter(d => d !== dir)
  await api.saveSetting('directories', updated)
  directories.value = updated
}

const saveSetting = async (key, value) => {
  await api.saveSetting(key, value)
}

const triggerScan = async (type = 'all') => {
  try {
    await api.triggerScan(type)
    await checkScanProgress()
  } catch (e) {
    alert("Failed to start scan: " + e.message)
  }
}

const cancelScan = async () => {
  try {
    await api.cancelScan()
    await checkScanProgress()
  } catch (e) {
    alert("Failed to cancel scan: " + e.message)
  }
}

</script>

<template>
  <div class="settings-page" v-if="!isLoading">
    <div class="header-row">
      <h1>Settings</h1>
      
      <div v-if="scanProgress.status === 'scanning'" class="scan-progress-container">
        <div class="scan-info">
          <span>Scanning... {{ scanProgress.current }} / {{ scanProgress.total }} files</span>
          <span class="scan-file" :title="scanProgress.current_file">{{ scanProgress.current_file.split(/[\\/]/).pop() || 'Loading...' }}</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" :style="{ width: `${scanProgress.total > 0 ? (scanProgress.current / scanProgress.total) * 100 : 0}%` }"></div>
        </div>
        <button class="btn-danger" @click="cancelScan">Cancel</button>
      </div>

      <div v-else-if="scanProgress.status === 'error'" class="scan-error">
        Error: {{ scanProgress.current_file }}
        <button class="btn-primary" @click="triggerScan('all')" style="margin-left: 10px;">Retry Scan</button>
      </div>

      <div v-else class="button-group">
        <button class="btn-primary" @click="triggerScan('thumbnail')">Scan files & Generate thumbnails</button>
        <button class="btn-secondary" @click="triggerScan('preview')">Generate Previews</button>
      </div>
    </div>
    
    <div class="settings-container">
      <section class="settings-section">
        <h2>Directories</h2>
        <p class="text-secondary">Manage folders where application looks for videos.</p>
        
        <div class="directory-list" v-if="directories.length > 0">
          <div v-for="dir in directories" :key="dir" class="dir-item">
            <span class="dir-path">{{ dir }}</span>
            <button class="btn-danger" @click="removeDirectory(dir)">Remove</button>
          </div>
        </div>
        
        <form @submit.prevent="addDirectory" class="add-dir-form">
          <input 
            type="text" 
            v-model="newDirectory" 
            placeholder="Absolute path to folder (e.g. C:\Videos or /home/user/videos)"
            class="input-field"
          />
          <button type="button" class="btn-secondary" @click="openFileExplorer">Browse...</button>
          <button type="submit" class="btn-primary">Add Folder</button>
        </form>
      </section>

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
            <span class="hint">The starting path when clicking "Browse...".</span>
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
        
        <div class="setting-row toggle-row" style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-color);">
          <label>Skip Already Scanned Files</label>
          <input 
            type="checkbox" 
            v-model="settings.skip_scanned" 
            @change="saveSetting('skip_scanned', settings.skip_scanned)"
          />
        </div>
      </section>
    </div>
  </div>
  <div v-else class="loading">Loading settings...</div>

  <!-- Custom File Explorer Modal -->
  <div class="modal-overlay" v-if="showFileExplorer" @click.self="closeFileExplorer">
    <div class="modal-content file-explorer">
      <div class="explorer-header">
        <h2>Select Folder</h2>
        <button class="btn-close" @click="closeFileExplorer">&times;</button>
      </div>
      
      <div class="explorer-path-bar">
        <span class="path-label">Current:</span>
        <span class="current-path">{{ explorerPath || 'Root / Drives' }}</span>
      </div>

      <div class="explorer-body">
        <div v-if="explorerLoading" class="explorer-loading">Loading...</div>
        <ul v-else class="directory-list-view">
          <li v-if="explorerPath" class="directory-list-item back-item" @click="fetchDirectory(explorerParent)">
            <span class="icon">📁</span> ..
          </li>
          <li v-for="dir in explorerDirectories" :key="dir.path" class="directory-list-item" @click="fetchDirectory(dir.path)">
            <span class="icon">📁</span> {{ dir.name }}
          </li>
          <li v-if="explorerDirectories.length === 0 && explorerPath" class="directory-list-item empty-dir">
            No subdirectories
          </li>
        </ul>
      </div>

      <div class="explorer-footer">
        <button class="btn-secondary" @click="closeFileExplorer">Cancel</button>
        <button class="btn-primary" @click="selectExplorerPath" :disabled="!explorerPath">Select This Folder</button>
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

.directory-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.dir-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--bg-color);
  padding: 10px 16px;
  border-radius: var(--border-radius-md);
  border: 1px solid var(--border-color);
}

.dir-path {
  font-family: monospace;
  word-break: break-all;
}

.add-dir-form {
  display: flex;
  gap: 12px;
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

.scan-progress-container {
  display: flex;
  align-items: center;
  gap: 16px;
  background-color: var(--bg-secondary);
  padding: 12px 20px;
  border-radius: var(--border-radius-md);
  margin-left: auto;
  border: 1px solid var(--border-color);
}

.scan-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.9rem;
}

.scan-file {
  font-size: 0.8rem;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 250px;
}

.progress-bar-bg {
  width: 150px;
  height: 8px;
  background-color: var(--bg-color);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--accent-color);
  transition: width 0.3s ease;
}

.scan-error {
  color: #ff4d4f;
  display: flex;
  align-items: center;
}

.button-group {
  display: flex;
  gap: 12px;
}

/* Modal and File Explorer Styles */
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
</style>
