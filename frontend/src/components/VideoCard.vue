<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  video: {
    type: Object,
    required: true
  },
  previewAudio: {
    type: Boolean,
    default: true
  }
})

const router = useRouter()
const isHovered = ref(false)
const videoPlayer = ref(null)

const formattedDuration = computed(() => {
  if (!props.video.duration) return '0:00'
  const maxMins = Math.floor(props.video.duration / 60)
  const secs = Math.floor(props.video.duration % 60)
  return `${maxMins}:${secs.toString().padStart(2, '0')}`
})

const handleMouseEnter = () => {
  isHovered.value = true
  if (videoPlayer.value && props.video.preview_path) {
    videoPlayer.value.currentTime = 0
    if (props.previewAudio) {
      videoPlayer.value.muted = false
      videoPlayer.value.play().catch(e => {
        // Browser blocked unmuted autoplay — fall back to muted
        videoPlayer.value.muted = true
        videoPlayer.value.play().catch(() => {})
      })
    } else {
      videoPlayer.value.muted = true
      videoPlayer.value.play().catch(() => {})
    }
  }
}

const handleMouseLeave = () => {
  isHovered.value = false
  if (videoPlayer.value) {
    videoPlayer.value.pause()
  }
}

const navigateToPlayer = () => {
  router.push(`/video/${props.video.id}`)
}

// Convert backend API relative path to absolute URL
const getMediaUrl = (path) => {
  if (!path) return ''
  // Use relative path — the Vite proxy (dev) or reverse proxy (prod) will forward to backend
  return path
}

</script>

<template>
  <div 
    class="video-card" 
    @mouseenter="handleMouseEnter" 
    @mouseleave="handleMouseLeave"
    @click="navigateToPlayer"
  >
    <div class="thumbnail-container">
      <!-- Static Thumbnail -->
      <img 
        v-show="!isHovered || !video.preview_path"
        :src="getMediaUrl(video.thumbnail_path)" 
        class="thumbnail" 
        alt="Video thumbnail"
        @error="$event.target.src='data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'100%\' height=\'100%\'><rect width=\'100%\' height=\'100%\' fill=\'%23333\'/><text x=\'50%\' y=\'50%\' fill=\'%23fff\' text-anchor=\'middle\' dy=\'.3em\'>No Thumbnail</text></svg>'"
      />
      
      <!-- Video Preview -->
      <video
        v-show="isHovered && video.preview_path"
        ref="videoPlayer"
        :src="getMediaUrl(video.preview_path)"
        class="preview-video"
        loop
        playsinline
      ></video>
      
      <div class="duration-badge">{{ formattedDuration }}</div>
    </div>
    
    <div class="video-info">
      <h3 class="video-title" :title="video.title">
        {{ video.title }}
      </h3>
      <p class="video-meta">Added {{ new Date(video.created_at).toLocaleDateString() }}</p>
    </div>
  </div>
</template>

<style scoped>
.video-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: transform var(--transition-fast);
}

.video-card:hover {
  transform: scale(1.02);
}

.thumbnail-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: var(--border-radius-md);
  overflow: hidden;
  background-color: var(--bg-secondary);
}

.thumbnail, .preview-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  position: absolute;
  top: 0;
  left: 0;
}

.duration-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.5px;
  z-index: 2;
}

.video-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 4px;
}

.video-title {
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}

.video-meta {
  font-size: 0.85rem;
  color: var(--text-secondary);
}
</style>
