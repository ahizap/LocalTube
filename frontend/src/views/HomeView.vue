<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../services/api'
import VideoCard from '../components/VideoCard.vue'

const videos = ref([])
const isLoading = ref(true)
let pollInterval = null

const fetchVideos = async () => {
  try {
    videos.value = await api.getVideos()
  } catch (error) {
    console.error("Failed to fetch videos:", error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchVideos()
  // Poll every 5 seconds to get updates if a scan is running in the background
  pollInterval = setInterval(fetchVideos, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="home-page">
    <div class="header-row">
      <h1>Library</h1>
      <span class="video-count" v-if="videos.length > 0">{{ videos.length }} videos</span>
    </div>

    <div v-if="isLoading" class="state-message">
      Loading videos...
    </div>
    
    <div v-else-if="videos.length === 0" class="state-message empty-state">
      <h2>No videos found</h2>
      <p>Go to settings to add a directory and trigger a scan.</p>
      <RouterLink to="/settings" class="btn-primary mt-4">Go to Settings</RouterLink>
    </div>

    <div v-else class="video-grid">
      <VideoCard 
        v-for="video in videos" 
        :key="video.id" 
        :video="video" 
      />
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
</style>
