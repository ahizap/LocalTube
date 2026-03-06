import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import SettingsView from '../views/SettingsView.vue'
import PlayerView from '../views/PlayerView.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'home',
            component: HomeView
        },
        {
            path: '/settings',
            name: 'settings',
            component: SettingsView
        },
        {
            path: '/video/:id',
            name: 'player',
            component: PlayerView
        }
    ]
})

export default router
