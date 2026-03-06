<script setup>
import { RouterView, RouterLink } from 'vue-router'
import { ref } from 'vue'

const isSidebarOpen = ref(true)

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}
</script>

<template>
  <div class="app-container">
    <header class="navbar">
      <div class="navbar-left">
        <button class="menu-btn" @click="toggleSidebar">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"></path></svg>
        </button>
        <RouterLink to="/" class="logo">
          <div class="logo-icon">▶</div>
          <span class="logo-text">Tube Local</span>
        </RouterLink>
      </div>
      <div class="navbar-center">
        <!-- Search bar could go here -->
      </div>
      <div class="navbar-right">
        <!-- Profile / Add could go here -->
      </div>
    </header>

    <div class="main-layout">
      <aside class="sidebar" :class="{ 'sidebar-closed': !isSidebarOpen }">
        <nav class="sidebar-nav">
          <RouterLink to="/" class="nav-item" active-class="active">
            <span class="nav-icon">🏠</span>
            <span class="nav-text">Home</span>
          </RouterLink>
          <RouterLink to="/settings" class="nav-item" active-class="active">
            <span class="nav-icon">⚙️</span>
            <span class="nav-text">Settings</span>
          </RouterLink>
        </nav>
      </aside>
      
      <main class="content-area">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.navbar {
  height: var(--header-height);
  background-color: var(--bg-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.menu-btn {
  padding: 8px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.menu-btn:hover {
  background-color: var(--bg-secondary);
}

.logo {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.logo-icon {
  background-color: var(--accent-color);
  color: white;
  width: 28px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}

.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: var(--sidebar-width);
  background-color: var(--bg-color);
  transition: width var(--transition-fast);
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  padding-right: 12px;
}

.sidebar-closed {
  width: 72px;
}

.sidebar-closed .nav-text {
  display: none;
}

.sidebar-closed .nav-item {
  flex-direction: column;
  padding: 16px 0;
  gap: 4px;
  align-items: center;
}

.sidebar-nav {
  padding: 12px 0 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px 12px;
  border-radius: var(--border-radius-md);
  color: var(--text-primary);
  transition: background-color var(--transition-fast);
  white-space: nowrap;
}

.nav-item:hover {
  background-color: var(--bg-secondary);
}

.nav-item.active {
  background-color: var(--bg-secondary);
  font-weight: 500;
}

.nav-icon {
  font-size: 1.2rem;
  width: 24px;
  display: flex;
  justify-content: center;
}

.sidebar-closed .nav-icon {
  font-size: 1.4rem;
}

.sidebar-closed .nav-item.active {
  background-color: transparent;
}
.sidebar-closed .nav-item:hover {
  background-color: var(--bg-secondary);
}

.content-area {
  flex: 1;
  background-color: var(--bg-color);
  overflow-y: auto;
  padding: 24px;
}
</style>
