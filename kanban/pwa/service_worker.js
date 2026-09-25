// Kanban.fun service worker: Web Push notifications and click-through.
self.addEventListener("install", () => self.skipWaiting())
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()))

self.addEventListener("push", (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { title: "Kanban.fun", body: event.data ? event.data.text() : "" }
  }
  const title = data.title || "Kanban.fun"
  const options = {
    body: data.body || "",
    icon: "/static/icons/icon.png",
    data: { path: data.path || "/" },
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener("notificationclick", (event) => {
  event.notification.close()
  const url = new URL(event.notification.data.path, self.location.origin).href
  event.waitUntil(openURL(url))
})

async function openURL(url) {
  const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true })
  const focused = clients.find((client) => client.focused)
  if (focused) {
    await focused.navigate(url)
    return focused.focus()
  }
  return self.clients.openWindow(url)
}
