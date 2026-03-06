<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const router = useRouter()
const video = ref(null)
const isLoading = ref(true)
const error = ref(null)

// Video Player State
const videoElement = ref(null)
const playerWrapper = ref(null)
const isPlaying = ref(false)
const isMuted = ref(false)
const isFullscreen = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(1)

// Controls visibility state
const showControls = ref(true)
let hideControlsTimeout = null

onMounted(async () => {
  const id = route.params.id
  try {
    const data = await api.getVideoDetails(id)
    if (data.error) {
       error.value = data.error
    } else {
      video.value = data
      // Initialize hide controls timeout
      resetHideControlsTimeout()
    }
  } catch (err) {
    error.value = "Failed to load video"
    console.error(err)
  } finally {
    isLoading.value = false
  }
  
  // Listen for fullscreen changes globally (for ESC key exits, etc)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onUnmounted(() => {
  if (hideControlsTimeout) clearTimeout(hideControlsTimeout)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})

const getStreamUrl = (id) => {
  return `/api/stream/${id}`
}

// --- Player Logic ---

const togglePlay = () => {
  if (!videoElement.value) return
  if (isPlaying.value) {
    videoElement.value.pause()
  } else {
    videoElement.value.play()
  }
}

const onPlay = () => isPlaying.value = true
const onPause = () => isPlaying.value = false

const onTimeUpdate = () => {
  if (videoElement.value) {
    currentTime.value = videoElement.value.currentTime
  }
}

const onLoadedMetadata = () => {
  if (videoElement.value) {
    duration.value = videoElement.value.duration
  }
}

const seek = (e) => {
  const rect = e.currentTarget.getBoundingClientRect()
  const pos = (e.clientX - rect.left) / rect.width
  if (videoElement.value) {
    videoElement.value.currentTime = pos * duration.value
  }
}

const toggleMute = () => {
  if (videoElement.value) {
    videoElement.value.muted = !isMuted.value
    isMuted.value = videoElement.value.muted
    if (isMuted.value) volume.value = 0
    else {
      volume.value = 1
      videoElement.value.volume = 1
    }
  }
}

const setVolume = (e) => {
  const newVol = parseFloat(e.target.value)
  volume.value = newVol
  if (videoElement.value) {
    videoElement.value.volume = newVol
    isMuted.value = newVol === 0
    videoElement.value.muted = isMuted.value
  }
}

const toggleFullscreen = () => {
  if (!playerWrapper.value) return
  
  if (!document.fullscreenElement) {
    playerWrapper.value.requestFullscreen().catch(err => {
      console.error(`Error attempting to enable fullscreen: ${err.message}`)
    })
  } else {
    document.exitFullscreen()
  }
}

const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

const formatTime = (timeInSeconds) => {
  if (isNaN(timeInSeconds)) return '0:00'
  const maxMins = Math.floor(timeInSeconds / 60)
  const secs = Math.floor(timeInSeconds % 60)
  const hrs = Math.floor(maxMins / 60)
  const mins = maxMins % 60
  
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// --- Interaction Logic ---

const handleMouseMove = () => {
  showControls.value = true
  playerWrapper.value?.classList.remove('hide-cursor')
  resetHideControlsTimeout()
}

const resetHideControlsTimeout = () => {
  if (hideControlsTimeout) clearTimeout(hideControlsTimeout)
  hideControlsTimeout = setTimeout(() => {
    if (isPlaying.value) {
      showControls.value = false
      playerWrapper.value?.classList.add('hide-cursor')
    }
  }, 2500)
}

const goBack = () => {
  router.push('/')
}
</script>

<template>
  <div class="player-page">
    <div class="header-nav">
      <button class="btn-back" @click="goBack">
        <span class="icon">←</span> Back to Library
      </button>
    </div>

    <div v-if="isLoading" class="loading">Loading player...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    
    <div v-else-if="video" class="player-container">
      <div 
        class="video-wrapper" 
        ref="playerWrapper"
        @mousemove="handleMouseMove"
        @mouseleave="showControls = false"
      >
        <video 
          ref="videoElement"
          autoplay 
          :src="getStreamUrl(video.id)"
          class="main-player"
          @click="togglePlay"
          @play="onPlay"
          @pause="onPause"
          @timeupdate="onTimeUpdate"
          @loadedmetadata="onLoadedMetadata"
        >
          Your browser does not support HTML video.
        </video>
        
        <!-- Center Play/Pause Overlay Component -->
        <div class="center-play-overlay" v-show="!isPlaying && duration > 0" @click="togglePlay">
           <div class="play-icon-large">▶</div>
        </div>

        <!-- Custom Controls Bar -->
        <div class="controls-overlay" :class="{ 'visible': showControls || !isPlaying }">
          
          <!-- Progress Bar -->
          <div class="progress-bar-container" @click="seek">
            <div class="progress-bar-bg">
              <div 
                class="progress-bar-fill" 
                :style="{ width: `${(currentTime / duration) * 100 || 0}%` }"
              ></div>
            </div>
          </div>
          
          <div class="controls-main-row">
            <div class="controls-left">
              <button class="control-btn" @click="togglePlay" :title="isPlaying ? 'Pause' : 'Play'">
                <span class="icon">{{ isPlaying ? '⏸' : '▶' }}</span>
              </button>
              
              <div class="volume-container">
                <button class="control-btn" @click="toggleMute" :title="isMuted ? 'Unmute' : 'Mute'">
                  <span class="icon">{{ isMuted || volume === 0 ? '🔇' : (volume < 0.5 ? '🔉' : '🔊') }}</span>
                </button>
                <input 
                  type="range" 
                  min="0" max="1" step="0.05" 
                  :value="volume" 
                  @input="setVolume"
                  class="volume-slider"
                >
              </div>

              <span class="time-display">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
            </div>
            
            <div class="controls-right">
              <button class="control-btn" @click="toggleFullscreen" :title="isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'">
                <span class="icon">{{ isFullscreen ? '🗗' : '🖵' }}</span>
              </button>
            </div>
          </div>
        </div>
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

.header-nav {
  margin-bottom: 20px;
}

.btn-back {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--border-radius-md);
  transition: all var(--transition-fast);
}

.btn-back:hover {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
}

.player-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.video-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background-color: #000;
  border-radius: var(--border-radius-md);
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0,0,0,0.6);
  display: flex;
  justify-content: center;
  align-items: center;
}

.video-wrapper.hide-cursor {
  cursor: none;
}

.main-player {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* Center Play Button Overlay */
.center-play-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  background-color: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  pointer-events: none; /* Let clicks pass through to video */
  backdrop-filter: blur(4px);
  transition: transform 0.2s ease, opacity 0.2s ease;
  z-index: 10;
}

.play-icon-large {
  font-size: 32px;
  color: white;
  margin-left: 6px; /* visually center play triangle */
}

/* Custom Controls Bar */
.controls-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(0deg, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.4) 70%, transparent 100%);
  padding: 24px 24px 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 20;
}

.controls-overlay.visible {
  opacity: 1;
}

/* Progress Bar */
.progress-bar-container {
  width: 100%;
  height: 12px;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.progress-bar-bg {
  width: 100%;
  height: 4px;
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
  transition: height 0.2s ease;
}

.progress-bar-container:hover .progress-bar-bg {
  height: 6px;
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--accent-color);
  position: absolute;
  left: 0;
  top: 0;
  border-radius: 2px;
}

/* Main Control Buttons Row */
.controls-main-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.controls-left, .controls-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.control-btn {
  background: transparent;
  border: none;
  color: white;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  min-height: 32px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.control-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.volume-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.volume-slider {
  width: 0;
  opacity: 0;
  transition: width 0.3s ease, opacity 0.3s ease;
  cursor: pointer;
}

/* Expanding volume slider on hover over the container */
.volume-container:hover .volume-slider {
  width: 80px;
  opacity: 1;
}

.time-display {
  color: white;
  font-size: 0.9rem;
  font-variant-numeric: tabular-nums;
  margin-left: 8px;
  user-select: none;
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
