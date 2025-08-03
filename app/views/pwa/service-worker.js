self.addEventListener("push", async (event) => {
  console.log("Push event received:", event)

  const data = await event.data.json()
  console.log("Push data:", data)

  const title = data.title
  const options = {
    body: data.body,
    icon: "/icon.png",
    data: { path: data.path }
  }

  event.waitUntil(Promise.all([ displayNotification(title, options) ]))
})

async function displayNotification(title, options) {
  console.log("Showing notification:", title, options)
  return self.registration.showNotification(title, options)
}

self.addEventListener("notificationclick", (event) => {
  event.notification.close()

  console.log("Notification click event:", event)

  const url = new URL(event.notification.data.path, self.location.origin).href
  event.waitUntil(openURL(url))
})

async function openURL(url) {
  const clients = await self.clients.matchAll({ type: "window" })
  const focused = clients.find((client) => client.focused)

  if (focused) {
    await focused.navigate(url)
  } else {
    await self.clients.openWindow(url)
  }
}
