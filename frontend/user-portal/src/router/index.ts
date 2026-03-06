import { createRouter, createWebHistory } from "vue-router";
import Home from "@/views/Home.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: Home,
    },
    {
      path: "/s/:token",
      name: "delivery",
      component: () => import("@/views/SkillDelivery.vue"),
    },
  ],
});

export default router;

