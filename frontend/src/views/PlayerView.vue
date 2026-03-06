<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const video = ref(null)
const isLoading = ref(true)
const error = ref(null)

onMounted(async () => {
  const id = route.params.id
  try {
    const data = await api.getVideoDetails(id)
    if (data.error) {
       error.value = data.error
    } else {
      video.value = data
    }
  } catch (err) {
    error.value = "Failed to load video"
    console.error(err)
  } finally {
    isLoading.value = false
  }
})

const getStreamUrl = (id) => {
  return `http://localhost:8080/api/stream/${id}`
}
</script>

<template>
  <div class="player-page">
    <div v-if="isLoading" class="loading">Loading player...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    
    <div v-else-if="video" class="player-container">
      <div class="video-wrapper">
        <video 
          controls 
          autoplay 
          :src="getStreamUrl(video.id)"
          class="main-player"
        >
          Your browser does not support HTML video.
        </video>
      </div>
      
      <div class="video-details">
        <h1 class="video-title">{{ video.title }}</h1>
        <div class="meta-row">
          <span class="date">Added {{ new Date(video.created_at).toLocaleDateString() }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.player-page {
  max-width: 1400px;
  margin: 0 auto;
}

.player-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.video-wrapper {
  width: 100%;
  aspect-ratio: 16 / 9;
  background-color: #000;
  border-radius: var(--border-radius-md);
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.main-player {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-details {
  padding: 10px 0;
}

.video-title {
  font-size: 1.5rem;
  margin-bottom: 8px;
  word-break: break-all;
}

.meta-row {
  display: flex;
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.loading, .error {
  text-align: center;
  padding: 50px;
  color: var(--text-secondary);
}

.error {
  color: var(--accent-color);
}
</style>
