<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import VideoCard from '../components/VideoCard.vue'

const route = useRoute()
const router = useRouter()

const videos = ref([])
const isLoading = ref(true)
const previewAudio = ref(true)
let pollInterval = null

// Pagination state
const currentPage = ref(1)
const perPage = ref(50)
const totalVideos = ref(0)
const totalPages = ref(1)

// Sort state
const sortBy = ref('created_at')
const sortOrder = ref('desc')

// Search state
const searchQuery = ref('')
let searchTimeout = null

// Per page options
const perPageOptions = [20, 50, 100, 200, 500, 1000]

// Sort options
const sortOptions = [
  { value: 'created_at', label: 'Date Added' },
  { value: 'name', label: 'Name' },
  { value: 'folder', label: 'Folder' }
]

// Computed for display
const showingFrom = computed(() => {
  if (totalVideos.value === 0) return 0
  return (currentPage.value - 1) * perPage.value + 1
})

const showingTo = computed(() => {
  return Math.min(currentPage.value * perPage.value, totalVideos.value)
})

// Initialize from URL params (only use URL if explicitly provided, otherwise keep localStorage values)
const initFromUrl = () => {
  // Only update from URL if the param is explicitly present
  if (route.query.page) {
    currentPage.value = parseInt(route.query.page) || 1
  }
  if (route.query.per_page) {
    perPage.value = parseInt(route.query.per_page) || 50
  }
  if (route.query.sort_by) {
    sortBy.value = route.query.sort_by
  }
  if (route.query.sort_order) {
    sortOrder.value = route.query.sort_order
  }
  if (route.query.search) {
    searchQuery.value = route.query.search
  }
}

// Update URL with current state
const updateUrl = () => {
  const query = {
    page: currentPage.value.toString(),
    per_page: perPage.value.toString(),
    sort_by: sortBy.value,
    sort_order: sortOrder.value
  }
  if (searchQuery.value) {
    query.search = searchQuery.value
  }
  router.replace({ query })
}

// Fetch videos with current pagination, sort, and search
const fetchVideos = async () => {
  try {
    const data = await api.getVideos(currentPage.value, perPage.value, sortBy.value, sortOrder.value, searchQuery.value)
    videos.value = data.videos || []
    totalVideos.value = data.total || 0
    totalPages.value = data.total_pages || 1
  } catch (error) {
    console.error("Failed to fetch videos:", error)
  } finally {
    isLoading.value = false
  }
}

// Navigation functions
const goToPage = (page) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  updateUrl()
  fetchVideos()
}

const nextPage = () => goToPage(currentPage.value + 1)
const prevPage = () => goToPage(currentPage.value - 1)

// Handle sort change
const onSortChange = () => {
  currentPage.value = 1 // Reset to first page when sorting changes
  updateUrl()
  fetchVideos()
}

// Handle per page change
const onPerPageChange = () => {
  currentPage.value = 1 // Reset to first page
  updateUrl()
  fetchVideos()
}

// Toggle sort order
const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  onSortChange()
}

// Handle search input with debounce
const onSearchInput = () => {
  // Clear existing timeout
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  // Debounce search - wait 300ms after user stops typing
  searchTimeout = setTimeout(() => {
    currentPage.value = 1 // Reset to first page when searching
    updateUrl()
    fetchVideos()
  }, 300)
}

// Clear search
const clearSearch = () => {
  searchQuery.value = ''
  currentPage.value = 1
  updateUrl()
  fetchVideos()
}

// Save preferences to localStorage
const savePreferences = () => {
  localStorage.setItem('videoPrefs', JSON.stringify({
    perPage: perPage.value,
    sortBy: sortBy.value,
    sortOrder: sortOrder.value
  }))
}

// Load preferences from localStorage
const loadPreferences = () => {
  const saved = localStorage.getItem('videoPrefs')
  if (saved) {
    try {
      const prefs = JSON.parse(saved)
      // Apply saved preferences (will be used if URL doesn't override)
      perPage.value = prefs.perPage || 50
      sortBy.value = prefs.sortBy || 'created_at'
      sortOrder.value = prefs.sortOrder || 'desc'
    } catch (e) {
      console.error('Failed to load preferences:', e)
    }
  }
}

// Watch for changes to save preferences
watch([perPage, sortBy, sortOrder], () => {
  savePreferences()
})

onMounted(async () => {
  // Load saved preferences first
  loadPreferences()

  // Then initialize from URL (URL params override localStorage)
  initFromUrl()

  // Update URL to reflect current state (for bookmarking)
  updateUrl()

  // Fetch the preview_audio setting
  try {
    const settings = await api.getSettings()
    previewAudio.value = settings.preview_audio !== undefined ? settings.preview_audio : true
  } catch (e) {
    console.error("Failed to load settings:", e)
  }

  fetchVideos()
  pollInterval = setInterval(fetchVideos, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  if (searchTimeout) clearTimeout(searchTimeout)
})
</script>

<template>
  <div class="home-page">
    <div class="header-row">
      <h1>Library</h1>
      <span class="video-count" v-if="totalVideos > 0">{{ totalVideos }} videos</span>
    </div>
  
    <!-- Search Bar -->
    <div class="search-bar">
      <div class="search-input-wrapper">
        <span class="search-icon">🔍</span>
        <input
          type="text"
          v-model="searchQuery"
          @input="onSearchInput"
          placeholder="Search videos by filename..."
          class="search-input"
        />
        <button
          v-if="searchQuery"
          class="clear-search-btn"
          @click="clearSearch"
          title="Clear search"
        >✕</button>
      </div>
    </div>
  
    <!-- Top Pagination & Sort Controls -->
    <div class="controls-bar" v-if="!isLoading && videos.length > 0">
      <div class="sort-controls">
        <label>Sort by:</label>
        <select v-model="sortBy" @change="onSortChange" class="select-input">
          <option v-for="opt in sortOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <button 
          class="sort-order-btn" 
          @click="toggleSortOrder" 
          :title="sortOrder === 'asc' ? 'Ascending' : 'Descending'"
        >
          {{ sortOrder === 'asc' ? '↑' : '↓' }}
        </button>
      </div>
      
      <div class="per-page-controls">
        <label>Per page:</label>
        <select v-model="perPage" @change="onPerPageChange" class="select-input">
          <option v-for="opt in perPageOptions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
      </div>
      
      <div class="pagination-controls">
        <button 
          class="page-btn" 
          @click="prevPage" 
          :disabled="currentPage <= 1"
          :class="{ disabled: currentPage <= 1 }"
        >
          ← Prev
        </button>
        <span class="page-info">
          Page {{ currentPage }} of {{ totalPages }}
          <span class="showing-info">(showing {{ showingFrom }}-{{ showingTo }})</span>
        </span>
        <button 
          class="page-btn" 
          @click="nextPage" 
          :disabled="currentPage >= totalPages"
          :class="{ disabled: currentPage >= totalPages }"
        >
          Next →
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="state-message">
      Loading videos...
    </div>

    <div v-else-if="videos.length === 0" class="state-message empty-state">
      <h2>No videos found</h2>
      <p>Go to settings to add a directory and trigger a scan.</p>
      <RouterLink to="/settings" class="btn-primary mt-4">Go to Settings</RouterLink>
    </div>

    <div v-else>
      <div class="video-grid">
        <VideoCard
          v-for="video in videos"
          :key="video.id"
          :video="video"
          :preview-audio="previewAudio"
        />
      </div>
      
      <!-- Bottom Pagination Controls -->
      <div class="controls-bar bottom-controls" v-if="videos.length > 0">
        <div class="pagination-controls">
          <button 
            class="page-btn" 
            @click="prevPage" 
            :disabled="currentPage <= 1"
            :class="{ disabled: currentPage <= 1 }"
          >
            ← Prev
          </button>
          <span class="page-info">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <button 
            class="page-btn" 
            @click="nextPage" 
            :disabled="currentPage >= totalPages"
            :class="{ disabled: currentPage >= totalPages }"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}

.header-row {
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 24px;
}

h1 {
  font-size: 1.5rem;
}

.video-count {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* Search Bar */
.search-bar {
  margin-bottom: 24px;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  max-width: 500px;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 1rem;
  color: var(--text-secondary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 12px 40px;
  border-radius: var(--border-radius-md);
  font-size: 1rem;
  transition: border-color 0.2s;
}

.search-input::placeholder {
  color: var(--text-secondary);
}

.search-input:focus {
  outline: none;
  border-color: var(--accent-color);
}

.clear-search-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: var(--text-secondary);
  padding: 4px 8px;
  cursor: pointer;
  font-size: 1rem;
  border-radius: 50%;
  transition: all 0.15s;
}

.clear-search-btn:hover {
  color: var(--text-primary);
  background-color: var(--border-color);
}

.controls-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
  padding: 12px 16px;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--border-color);
}

.bottom-controls {
  margin-top: 32px;
  margin-bottom: 24px;
  justify-content: center;
}

.sort-controls,
.per-page-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sort-controls label,
.per-page-controls label {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.select-input {
  background-color: var(--bg-color);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 8px 12px;
  border-radius: var(--border-radius-md);
  font-size: 0.9rem;
  cursor: pointer;
}

.select-input:focus {
  outline: none;
  border-color: var(--accent-color);
}

.sort-order-btn {
  background-color: var(--bg-color);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  width: 36px;
  height: 36px;
  border-radius: var(--border-radius-md);
  cursor: pointer;
  font-size: 1.1rem;
  transition: all 0.15s;
}

.sort-order-btn:hover {
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.page-btn {
  background-color: var(--bg-color);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 8px 16px;
  border-radius: var(--border-radius-md);
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.15s;
}

.page-btn:hover:not(.disabled) {
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.page-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.showing-info {
  font-size: 0.85rem;
  color: var(--text-secondary);
  opacity: 0.8;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  column-gap: 16px;
  row-gap: 32px;
}

@media (min-width: 1200px) {
  .video-grid {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  }
}

.state-message {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.empty-state h2 {
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-state p {
  margin-bottom: 24px;
}

.btn-primary {
  display: inline-block;
  background-color: var(--accent-color);
  color: white;
  padding: 10px 20px;
  border-radius: var(--border-radius-md);
  font-weight: 500;
  transition: all var(--transition-fast);
}

.btn-primary:hover {
  background-color: var(--accent-hover);
}

.mt-4 {
  margin-top: 16px;
}

@media (max-width: 768px) {
  .controls-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .pagination-controls {
    margin-left: 0;
    justify-content: center;
  }
  
  .sort-controls,
  .per-page-controls {
    justify-content: center;
  }
}
</style>
